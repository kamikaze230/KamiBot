import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import ctypes.util

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.guilds = True

# Charger manuellement Opus si besoin
if not discord.opus.is_loaded():
    try:
        discord.opus._load_default()
    except (AttributeError, RuntimeError):
        try:
            opus_path = ctypes.util.find_library('opus')
            if opus_path:
                discord.opus.load_opus(opus_path)
            else:
                raise RuntimeError("❌ Impossible de trouver la bibliothèque Opus.")
        except Exception as e:
            print(f"Error loading opus: {e}")
            raise RuntimeError("❌ Failed to load opus library. Voice features may not work.")

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"🟢 Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")

@bot.tree.command(name="liste_vocaux", description="Affiche la liste des membres dans les salons vocaux")
async def liste_vocaux(interaction: discord.Interaction):
    guild = interaction.guild
    message = ""
    for channel in guild.voice_channels:
        if channel.members:
            message += f"🔊 **{channel.name}** ({len(channel.members)} membres):\n"
            for member in channel.members:
                message += f" - {member.display_name}\n"
        else:
            message += f"🔇 **{channel.name}** (vide)\n"
    await interaction.response.send_message(message or "Aucun salon vocal trouvé.", ephemeral=True)

@bot.tree.command(name="troll", description="Rejoint le vocal de l'utilisateur et joue un son")
@app_commands.describe(user="La personne à troller")
async def troll(interaction: discord.Interaction, user: discord.Member):
    voice_channel = user.voice.channel if user.voice else None
    if not voice_channel:
        await interaction.response.send_message(f"❌ {user.display_name} n'est pas dans un salon vocal.", ephemeral=True)
        return

    await interaction.response.send_message(f"😈 Trolling {user.display_name}...", ephemeral=True)

    try:
        vc = await voice_channel.connect()
    except discord.ClientException:
        await interaction.followup.send("⚠️ Je suis déjà dans un salon vocal !", ephemeral=True)
        return

    try:
        if not os.path.isfile("voice.mp3"):
            await interaction.followup.send("❌ Fichier son introuvable !", ephemeral=True)
            await vc.disconnect()
            return

        try:
            audio_source = discord.FFmpegPCMAudio(
                source="voice.mp3",
                options='-hide_banner -loglevel error -nostdin'
            )
            vc.play(audio_source)
            await asyncio.sleep(1)  # Donne le temps à la lecture de démarrer
        except Exception as e:
            print(f"Failed to play audio: {e}")
            raise e

    except Exception as e:
        print(f"Error playing audio: {e}")
        await interaction.followup.send("❌ Error playing audio", ephemeral=True)
        await vc.disconnect()
        return

    while vc.is_playing():
        await asyncio.sleep(1)

    await vc.disconnect()

# Remplace le token par une variable d'environnement si possible
bot.run("MTM3MjEyMjY3NzY5NDgyODYyNQ.GCwyYi.0q3OK5TrRIZ0AZutypTyqGXvl1cDWALNpbBxQI")
