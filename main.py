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
IP_TO_PING = "159.89.226.167"
CHANNEL_ID = 1361883740724264990
port = 4000

async def is_host_up(host, port=22, timeout=2):
    """Check if host is up by attempting a socket connection"""
    try:
        # Use asyncio to run socket operations in a thread pool
        return await asyncio.to_thread(_check_socket, host, port, timeout)
    except Exception as e:
        print(f"Error checking host: {e}")
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
@lightbulb.command("ping", "checks if the bot is alive")
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: lightbulb.Context) -> None:
    result = ""
    if await is_host_up(IP_TO_PING):
        result = f"{IP_TO_PING} still up and running!"
    else:
        result = f"{IP_TO_PING} is down!"
    await ctx.respond(result)

@bot.listen(hikari.StartedEvent)
async def on_start(_):
    async def check_server_status():
        while True:
            is_up = await is_host_up(IP_TO_PING)
            if is_up:
                print(f"{IP_TO_PING} is up and running!")
            else:
                print(f"{IP_TO_PING} is down!")
                await bot.rest.create_message(
                    CHANNEL_ID,
                    content="@everyone ⚠️ Server is down!"
                )
            await asyncio.sleep(CHECK_INTERVAL)
    asyncio.create_task(check_server_status())

bot.run()