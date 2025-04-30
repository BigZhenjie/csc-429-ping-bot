import lightbulb
import os
from dotenv import load_dotenv
import asyncio
import hikari
import socket
import time
from keep_alive import keep_alive
from backup import Backup
load_dotenv()

keep_alive()

bot = lightbulb.BotApp(
    token=os.getenv("BOT_TOKEN"),
    prefix="!")

CHECK_INTERVAL = 60  # seconds
IP_TO_PING = os.getenv("SERVER_IP")
PING_CHANNEL_ID = os.getenv("PING_CHANNEL_ID")
BACKUP_CHANNEL_ID = os.getenv("BACKUP_CHANNEL_ID")

# Ports discovered on the server
PORTS_TO_MONITOR = [22, 80, 443]

# Map ports to service names for better reporting
PORT_SERVICES = {
    22: "SSH",
    80: "HTTP Website",
    443: "HTTPS Website",
}

backup_system = Backup(
    backup_dir="backups",
    max_backups=7, 
    ssh_host=os.getenv("SSH_HOST", IP_TO_PING),  # Default to monitored IP if not specified
    ssh_port=int(os.getenv("SSH_PORT", "22")),
    ssh_username=os.getenv("SSH_USERNAME"),
    ssh_key_passphrase=os.getenv("SSH_KEY_PASSPHRASE")
)

async def check_port(host, port, timeout=2):
    """Check if a specific port is open"""
    try:
        return await asyncio.to_thread(_check_socket, host, port, timeout)
    except Exception as e:
        print(f"Error checking port {port}: {e}")
        return False

def _check_socket(host, port, timeout):
    """Helper function to perform socket connection"""
    try:
        # Use context manager to ensure socket is always closed properly
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_obj:
            socket_obj.settimeout(timeout)
            result = socket_obj.connect_ex((host, port))
            return result == 0  # Return True if connection succeeded
    except socket.error as e:
        print(f"Socket error on {host}:{port} - {e}")
        return False
    except Exception as e:
        print(f"Unexpected error checking {host}:{port} - {e}")
        return False

@bot.listen(hikari.StartedEvent)
async def on_start(_):
    print(f"Starting monitoring for {IP_TO_PING} on ports: {', '.join(map(str, PORTS_TO_MONITOR))}")
    
    # Keep track of port states
    port_states = {port: None for port in PORTS_TO_MONITOR}
    
    async def monitor_ports():
        while True:
            # Check all ports in parallel
            tasks = {port: check_port(IP_TO_PING, port) for port in PORTS_TO_MONITOR}
            
            # Wait for all checks to complete
            for port, task in tasks.items():
                service_name = PORT_SERVICES.get(port, f"Port {port}")
                try:
                    is_up = await task
                    
                    # First check - initialize state
                    if port_states[port] is None:
                        port_states[port] = is_up
                        print(f"{service_name} initial state: {'UP' if is_up else 'DOWN'}")
                        continue
                    
                    # Alert on state change from up to down
                    if port_states[port] and not is_up:
                        print(f"ALERT: {service_name} went DOWN!")
                        await bot.rest.create_message(
                            PING_CHANNEL_ID,
                            content=f"@everyone ⚠️ {service_name} on {IP_TO_PING} is DOWN!"
                        )
                        port_states[port] = False
                    
                    # Log recovery
                    elif not port_states[port] and is_up:
                        print(f"{service_name} recovered and is now UP")
                        await bot.rest.create_message(
                            PING_CHANNEL_ID,
                            content=f"{service_name} on {IP_TO_PING} is back online"
                        )
                        port_states[port] = True
                        
                except Exception as e:
                    print(f"Error in monitor task for {service_name}: {e}")
            
            await asyncio.sleep(CHECK_INTERVAL)
    
    asyncio.create_task(monitor_ports())

@bot.command
@lightbulb.command("ping", "checks status of all monitored ports")
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: lightbulb.Context) -> None:
    try:
        # IMMEDIATELY acknowledge the interaction before doing anything else
        await ctx.respond("Checking port statuses...", flags=hikari.MessageFlag.EPHEMERAL)
        
        # Check all ports in parallel
        port_tasks = {}
        for port in PORTS_TO_MONITOR:
            port_tasks[port] = asyncio.create_task(check_port(IP_TO_PING, port, timeout=1))
        
        # Wait for all checks to complete (with a reasonable total timeout)
        try:
            # Set a max total wait time of 10 seconds
            done, pending = await asyncio.wait(port_tasks.values(), timeout=10)
            
            # Cancel any pending tasks
            for p in pending:
                p.cancel()
        except Exception as e:
            await ctx.respond(f"Error checking ports: {str(e)}")
            return
        
        # Process results
        up_ports = 0
        down_ports = 0
        status_messages = []
        
        # Map results back to their ports
        port_results = {}
        for port, task in port_tasks.items():
            try:
                if task.done():
                    port_results[port] = task.result()
                else:
                    # If task didn't complete in time, mark port as down
                    port_results[port] = False
            except Exception:
                # Handle any exceptions during task execution
                port_results[port] = False
        
        # Generate status messages
        for port in PORTS_TO_MONITOR:
            service_name = PORT_SERVICES.get(port, f"Port {port}")
            is_up = port_results.get(port, False)
            
            if is_up:
                status = "✅ UP"
                up_ports += 1
            else:
                status = "❌ DOWN"
                down_ports += 1
                
            status_messages.append(f"{service_name}: {status}")
        
        # Create a summary header
        if down_ports == 0:
            header = f"🟢 All services on {IP_TO_PING} are operational"
        elif down_ports == len(PORTS_TO_MONITOR):
            header = f"🔴 All services on {IP_TO_PING} are down!"
        else:
            header = f"🟡 {down_ports}/{len(PORTS_TO_MONITOR)} services on {IP_TO_PING} are down"
        
        # Combine header and status messages
        result = f"{header}\n\n" + "\n".join(status_messages)
        
        # Send the final response as a follow-up
        await ctx.respond(result)
    except Exception as e:
        print(f"Error in ping command: {e}")
        # Try to send a message if possible
        try:
            await ctx.respond(f"An error occurred: {str(e)}")
        except:
            pass

@bot.command
@lightbulb.command("backup", "Create and send a backup of the website files")
@lightbulb.implements(lightbulb.SlashCommand)
async def backup_website(ctx: lightbulb.Context) -> None:
    """Create and send a backup of the website files"""
    try:
        # Acknowledge the interaction immediately
        await ctx.respond("Starting website backup process... This may take some time.", flags=hikari.MessageFlag.EPHEMERAL)
        
        # Get the backup channel
        backup_channel = BACKUP_CHANNEL_ID if BACKUP_CHANNEL_ID else ctx.channel_id
        
        # Create a message in the backup channel
        message = await bot.rest.create_message(
            backup_channel,
            f"Creating website backup, requested by {ctx.author.username}... Please wait."
        )
        
        # Run the backup in a non-blocking way
        def create_backup():
            try:
                return backup_system.create_backup()
            except Exception as e:
                print(f"Error creating backup: {e}")
                return None
        
        # Run the CPU-intensive backup creation in a thread pool
        backup_path = await asyncio.to_thread(create_backup)
        
        if not backup_path:
            await bot.rest.create_message(
                backup_channel,
                f"Failed to create backup. Check server logs for details."
            )
            return
        
        # Check if file size is under Discord's limit (25MB)
        file_size = os.path.getsize(backup_path) / (1024 * 1024)  # in MB
        if file_size > 25:
            await bot.rest.create_message(
                backup_channel,
                f"Backup file is too large ({file_size:.2f}MB) to send directly."
            )
            return
        
        # Send the backup file
        with open(backup_path, "rb") as f:
            await bot.rest.create_message(
                backup_channel,
                f"Website backup created on {time.strftime('%Y-%m-%d %H:%M:%S')}:",
                attachment=hikari.Bytes(f.read(), f"website_backup_{time.strftime('%Y%m%d_%H%M%S')}.zip")
            )
        
        # Confirm completion
        await ctx.respond("Backup completed successfully!", flags=hikari.MessageFlag.EPHEMERAL)
        
    except Exception as e:
        print(f"Error in backup command: {e}")
        # Try to send a message if possible
        try:
            await ctx.respond(f"An error occurred during backup: {str(e)}")
        except:
            pass

# Optional: Add scheduled backups
@bot.listen(hikari.StartedEvent)
async def setup_scheduled_backups(_):
    # Schedule backups - for example, daily at midnight
    backup_interval_hours = int(os.getenv("BACKUP_INTERVAL_HOURS", "12"))  # Default to daily
    
    async def scheduled_backup():
        while True:
            await asyncio.sleep(backup_interval_hours * 3600)  # Convert hours to seconds
            
            try:
                print(f"Running scheduled backup")
                
                # Get the backup channel
                backup_channel = BACKUP_CHANNEL_ID
                
                if not backup_channel:
                    print("No backup channel configured, skipping scheduled backup")
                    continue
                
                # Create a message in the backup channel
                message = await bot.rest.create_message(
                    backup_channel,
                    f"Running scheduled website backup..."
                )
                
                # Create the backup
                backup_path = await asyncio.to_thread(backup_system.create_backup)
                
                if not backup_path:
                    await bot.rest.create_message(
                        backup_channel,
                        "Failed to create scheduled backup. Check server logs for details."
                    )
                    continue
                
                # Check if file size is under Discord's limit (25MB)
                file_size = os.path.getsize(backup_path) / (1024 * 1024)  # in MB
                if file_size > 25:
                    await bot.rest.create_message(
                        backup_channel,
                        f"Scheduled backup file is too large ({file_size:.2f}MB) to send directly."
                    )
                    continue
                
                # Send the backup file
                with open(backup_path, "rb") as f:
                    await bot.rest.create_message(
                        backup_channel,
                        f"Scheduled website backup created on {time.strftime('%Y-%m-%d %H:%M:%S')}:",
                        attachment=hikari.Bytes(f.read(), f"website_backup_{time.strftime('%Y%m%d_%H%M%S')}.zip")
                    )
                    
            except Exception as e:
                print(f"Error during scheduled backup: {e}")
                # Start scheduled backup task if enabled

    if os.getenv("ENABLE_SCHEDULED_BACKUPS", "false").lower() == "true":
        asyncio.create_task(scheduled_backup())
        print(f"Scheduled backups enabled, running every {backup_interval_hours} hours")
bot.run()