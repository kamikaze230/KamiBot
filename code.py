import discord
import asyncio

TOKEN = 'MTM3MjEyMjY3NzY5NDgyODYyNQ.GCwyYi.0q3OK5TrRIZ0AZutypTyqGXvl1cDWALNpbBxQI'  # Replace this with your regenerated bot token
CHANNEL_ID = 1075677623931387964  # Replace with your channel ID

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Required to read message content

client = discord.Client(intents=intents)

class Bot(discord.Client):

    async def send_messages(self):
        await client.wait_until_ready()
        channel = client.get_channel(CHANNEL_ID)
        if channel is None:
            print("Channel not found!")
            return
    
        
        msg = input("You: ")
        await channel.send(msg)
        await self.close()
    
    
    @client.event
    async def on_ready(self):
        print(f'Logged in as {client.user}')
        print("Type your message below (type 'exit' to quit):")
        asyncio.create_task(self.send_messages())
        
    

client = Bot(intents=intents)

# Remplace "VOTRE_TOKEN_ICI" par le token de ton bot
client.run(
    "MTM3MjEyMjY3NzY5NDgyODYyNQ.GCwyYi.0q3OK5TrRIZ0AZutypTyqGXvl1cDWALNpbBxQI")
