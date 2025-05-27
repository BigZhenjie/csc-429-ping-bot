import lightbulb
import os
from dotenv import load_dotenv
import asyncio
import hikari
import time
from keep_alive import keep_alive
from backup import Backup
from monitor import ServerMonitor
from patch_update import PatchUpdate
import aiohttp
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

patch_update = PatchUpdate(
    ssh_host=os.getenv("SSH_HOST", IP_TO_PING),
    ssh_port=int(os.getenv("SSH_PORT", "22")),
    ssh_username=os.getenv("SSH_USERNAME"),
    ssh_key_passphrase=os.getenv("SSH_KEY_PASSPHRASE")
)

# Initialize server monitor
server_monitor = ServerMonitor(
    ip_address=IP_TO_PING,
    ports_to_monitor=PORTS_TO_MONITOR,
    check_interval=CHECK_INTERVAL,
    port_services=PORT_SERVICES,
    api_endpoint="https://team08.csc429.io/submit-transaction",
    patch = patch_update
)

@bot.listen(hikari.StartedEvent)
async def on_start(_):
    # Start the monitoring task
    asyncio.create_task(server_monitor.monitor_ports(bot, PING_CHANNEL_ID))

@bot.command
@lightbulb.command("ping", "checks status of all monitored ports")
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: lightbulb.Context) -> None:
    try:
        # IMMEDIATELY acknowledge the interaction before doing anything else
        await ctx.respond("Checking port statuses...", flags=hikari.MessageFlag.EPHEMERAL)
        
        # Use the server monitor to check all ports
        result = await server_monitor.check_all_ports(timeout=1)
        
        # Combine header and status messages
        response = f"{result['header']}\n\n" + "\n".join(result['status_messages'])
        
        # Send the final response as a follow-up
        await ctx.respond(response)
    except Exception as e:
        print(f"Error in ping command: {e}")
        # Try to send a message if possible
        try:
            await ctx.respond(f"An error occurred: {str(e)}")
        except:
            pass


@bot.command
@lightbulb.command("patch", "Run patch update to fix broken paths")
@lightbulb.implements(lightbulb.SlashCommand)
async def patch_command(ctx: lightbulb.Context) -> None:
    try:
        # Acknowledge the interaction immediately
        await ctx.respond("Running patch update... This may take a moment.", flags=hikari.MessageFlag.EPHEMERAL)
        def run_patch():
            try:
                return patch_update.modify_file()
            except Exception as e:
                print(f"Error running patch update: {e}")
                return False
        success = await asyncio.to_thread(run_patch)
        if success:
            await ctx.respond("✅ Attempting Endpoint Patch!")
            # Restart the service after successful patch
            def restart_service():
                try:
                    return patch_update.restart_service()
                except Exception as e:
                    print(f"Error restarting service: {e}")
                    return False
            restart_success = await asyncio.to_thread(restart_service)
            if restart_success:
                await ctx.respond("🔄 Service restarted successfully!")
            else:
                await ctx.respond("⚠️ Patch completed but service restart failed.")
        else:
            await ctx.respond("❌ Patch update failed")

    except Exception as e:
        print(f"Error in patch command: {e}")
        # Try to send a message if possible
        try:
            await ctx.respond(f"An error occurred during patch update: {str(e)}")
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