import discord
import asyncio

TOKEN = 'MTM3MjEyMjY3NzY5NDgyODYyNQ.GCwyYi.0q3OK5TrRIZ0AZutypTyqGXvl1cDWALNpbBxQI'  # Replace this with your regenerated bot token
CHANNEL_ID = 1075677623931387964  # Replace with your channel ID

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Required to read message content

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print("Type your message below (type 'exit' to quit):")
    asyncio.create_task(dernier("!ping"))

async def dernier(msg):
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print("Channel not found!")
        return
    
    messages = []
    async for message in channel.history(limit=10):
        messages.append(f"{message.author}: {message.content}")
    
    for msg in reversed(messages):
        print(msg)
    
    

@client.event
async def on_message(message):
    # Ignore les messages du bot lui-mÃªme
    if message.channel.id != CHANNEL_ID:
        return

    # Affiche dans le terminal
    print(f"[{message.channel}] {message.author}: {message.content}")


# Remplace "VOTRE_TOKEN_ICI" par le token de ton bot
client.run(
    "MTM3MjEyMjY3NzY5NDgyODYyNQ.GCwyYi.0q3OK5TrRIZ0AZutypTyqGXvl1cDWALNpbBxQI")
