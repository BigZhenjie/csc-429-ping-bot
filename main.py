import lightbulb
import os
from dotenv import load_dotenv
import platform
import asyncio
import hikari


load_dotenv()

bot = lightbulb.BotApp(
    token=os.getenv("BOT_TOKEN"),
    prefix="!")

CHECK_INTERVAL = 300  # seconds
IP_TO_PING = "159.89.226.167"
CHANNEL_ID=1361883740724264990
async def ping_ip_once():
    param = "-n" if platform.system().lower() == "windows" else "-c"

    process = await asyncio.create_subprocess_exec(
        "ping", param, "1", IP_TO_PING,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    returncode = await process.wait()
    if returncode == 0:
        return True
    else:
        return False

            
@bot.command
@lightbulb.command("ping", "checks if the bot is alive")
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: lightbulb.Context) -> None:
    result = ""
    if await ping_ip_once():
        result = f"{IP_TO_PING} still up and running!"
    else:
        result = f"{IP_TO_PING} is down!"
    await ctx.respond(result)



@bot.listen(hikari.StartedEvent)
async def on_start(_):
    async def ping_ip():
        param = "-n" if platform.system().lower() == "windows" else "-c"
        while True:
            process = await asyncio.create_subprocess_exec(
                "ping", param, "1", IP_TO_PING,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            returncode = await process.wait()
            if returncode == 0:
                print(f"{IP_TO_PING} is up and running!")
            else:
                print(f"{IP_TO_PING} is down!")
                await bot.rest.create_message(
                    CHANNEL_ID,
                    content="@everyone ⚠️ Server is down!"
                    )
            await asyncio.sleep(CHECK_INTERVAL)
    asyncio.create_task(ping_ip())

bot.run()