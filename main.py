import lightbulb
import os
from dotenv import load_dotenv
import asyncio
import hikari
import socket
import time
from keep_alive import keep_alive

load_dotenv()

keep_alive()

bot = lightbulb.BotApp(
    token=os.getenv("BOT_TOKEN"),
    prefix="!")

CHECK_INTERVAL = 60  # seconds
IP_TO_PING = "147.182.252.85"
CHANNEL_ID = 1361883740724264990

# Ports discovered on the server
PORTS_TO_MONITOR = [22, 53, 80, 443, 5000]

# Map ports to service names for better reporting
PORT_SERVICES = {
    22: "SSH",
    53: "DNS",
    80: "HTTP Website",
    443: "HTTPS Website",
    5000: "Gunicorn Application"
}

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
                    
                    # Handle state changes as you're already doing
                    # ...
                except Exception as e:
                    print(f"Error in monitor task for {service_name}: {e}")
            
            await asyncio.sleep(CHECK_INTERVAL)
    
    asyncio.create_task(monitor_ports())

@bot.command
@lightbulb.command("ping", "checks status of all monitored ports")
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: lightbulb.Context) -> None:
    # Defer the response to avoid timeout
    await ctx.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    
    # Check all ports in parallel instead of sequentially
    tasks = {port: check_port(IP_TO_PING, port, timeout=1) for port in PORTS_TO_MONITOR}
    results = {}
    
    # Wait for all checks to complete (with a reasonable total timeout)
    try:
        # Set a max total wait time of 10 seconds
        done, pending = await asyncio.wait(tasks.values(), timeout=10)
        
        # Cancel any pending tasks
        for p in pending:
            p.cancel()
    except Exception as e:
        await ctx.edit_last_response(f"Error checking ports: {str(e)}")
        return
    
    # Process results
    up_ports = 0
    down_ports = 0
    status_messages = []
    
    # Map results back to their ports
    port_results = {}
    for port, task in tasks.items():
        if task.done():
            port_results[port] = task.result()
        else:
            # If task didn't complete in time, mark port as down
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
    await ctx.edit_last_response(result)

bot.run()