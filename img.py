import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Required to read message content
CHANNEL_ID = 1075677623931387964

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    asyncio.create_task(sendimage())


@bot.event
async def sendimage():
    channel = bot.get_channel(CHANNEL_ID)
    with open("cpt2.png", "rb") as f:
        picture = discord.File(f)
        await channel.send("imagine je joue à ça" , file=picture)
        print("done")


bot.run(  "MTM3MjEyMjY3NzY5NDgyODYyNQ.GCwyYi.0q3OK5TrRIZ0AZutypTyqGXvl1cDWALNpbBxQI")
