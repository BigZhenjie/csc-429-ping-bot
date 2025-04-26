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
        socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_obj.settimeout(timeout)
        result = socket_obj.connect_ex((host, port))
        socket_obj.close()
        return result == 0  # Return True if connection succeeded
    except:
        return False

@bot.command
@lightbulb.command("ports", "shows status of all monitored ports")
@lightbulb.implements(lightbulb.SlashCommand)
async def ports(ctx: lightbulb.Context) -> None:
    status_messages = []
    
    for port in PORTS_TO_MONITOR:
        service_name = PORT_SERVICES.get(port, f"Port {port}")
        is_up = await check_port(IP_TO_PING, port)
        
        status = "✅ UP" if is_up else "❌ DOWN"
        status_messages.append(f"{service_name}: {status}")
    
    await ctx.respond("\n".join(status_messages))

@bot.command
@lightbulb.command("ping", "checks if the server is alive")
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: lightbulb.Context) -> None:
    # Check all important services
    statuses = []
    for port in PORTS_TO_MONITOR:
        service_name = PORT_SERVICES.get(port, f"Port {port}")
        is_up = await check_port(IP_TO_PING, port)
        if not is_up:
            statuses.append(f"{service_name}: DOWN")
    
    if not statuses:
        result = f"{IP_TO_PING} - All services are up and running!"
    else:
        result = f"{IP_TO_PING} - Issues detected:\n" + "\n".join(statuses)
    await ctx.respond(result)

@bot.listen(hikari.StartedEvent)
async def on_start(_):
    print(f"Starting monitoring for {IP_TO_PING} on ports: {', '.join(map(str, PORTS_TO_MONITOR))}")
    
    # Keep track of port states
    port_states = {port: None for port in PORTS_TO_MONITOR}
    
    async def monitor_ports():
        while True:
            for port in PORTS_TO_MONITOR:
                service_name = PORT_SERVICES.get(port, f"Port {port}")
                is_up = await check_port(IP_TO_PING, port)
                
                # First check - initialize state
                if port_states[port] is None:
                    port_states[port] = is_up
                    print(f"{service_name} is {'UP' if is_up else 'DOWN'}")
                    continue
                
                # Alert on state change from up to down
                if port_states[port] and not is_up:
                    print(f"ALERT: {service_name} went DOWN!")
                    await bot.rest.create_message(
                        CHANNEL_ID,
                        content=f"@everyone ⚠️ {service_name} on {IP_TO_PING} is DOWN!"
                    )
                    port_states[port] = False
                
                # Log recovery
                elif not port_states[port] and is_up:
                    print(f"{service_name} recovered and is now UP")
                    await bot.rest.create_message(
                        CHANNEL_ID,
                        content=f"{service_name} on {IP_TO_PING} is back online"
                    )
                    port_states[port] = True
            
            await asyncio.sleep(CHECK_INTERVAL)
    
    asyncio.create_task(monitor_ports())

bot.run()