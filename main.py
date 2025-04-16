import hikari
import os
from dotenv import load_dotenv

load_dotenv()

bot = hikari.GatewayBot(token=os.getenv("BOT_TOKEN"))

@bot.listen()
async def ping(event: hikari.GuildMessageCreateEvent) -> None:
    if not event.is_human:
        return
    
    me = bot.get_me()
    
    if me.id in event.message.user_mentions_ids:
        await event.message.respond("Pong!")
        
bot.run()