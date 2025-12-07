from enum import *
import discord
from discord.ext import commands
import random
import re
import asyncio
from datetime import datetime, timedelta
import time
from blackjack import BlackjackGame, pretty_cards
import csv


def result_message(game: BlackjackGame) -> str:
    """Generate result message based on game outcome"""
    if not hasattr(game, 'result'):
        return "Game in progress"

    result = game.result.lower() if game.result else "unknown"

    if result == "win":
        return "🎉 You won!"
    elif result == "lose" or result == "bust":
        return "💥 You lost!"
    elif result == "push" or result == "tie":
        return "🤝 It's a tie!"
    elif result == "blackjack":
        return "♠️ BLACKJACK! You win!"
    elif result == "surrender":
        return "🏳️ You surrendered"
    else:
        return f"Game ended: {result}"


USER_COOLDOWN = {}
COOLDOWN_SECONDS = 5
DAILY_COOLDOWN_FILE = "daily_cooldowns.csv"

# Replace with your bot token
TOKEN = 

# Intents
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

# Store tasks so we can stop them later
move_tasks = {}


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(discord.__version__)


async def loop_move(ctx, member: discord.Member, speed: int):
    """Keep moving the member randomly, waiting if they leave voice."""
    guild = ctx.guild
    voice_channels = [
        vc for vc in guild.channels if isinstance(vc, discord.VoiceChannel)
    ]

    while True:
        # Refresh member object
        member = guild.get_member(member.id)
        if member is None:
            await ctx.send("⚠️ The user left the server. Stopping move loop.")
            move_tasks.pop(member.id, None)
            return

        # If user is not in a voice channel, wait until they join
        if not member.voice or not member.voice.channel:
            await asyncio.sleep(1)
            continue

        # Pick a random channel
        if voice_channels:
            new_channel = random.choice(voice_channels)
            if len(voice_channels) > 1:
                while new_channel == member.voice.channel:
                    new_channel = random.choice(voice_channels)
            try:
                await member.move_to(new_channel)
            except discord.Forbidden:
                await ctx.send("⚠️ Missing permissions to move members.")
                move_tasks.pop(member.id, None)
                return

        await asyncio.sleep(speed)


@bot.command()
async def move(ctx, target: str = None, speed: str = "2"):
    """Start moving a user (mention or ID) randomly until stopped."""

    if not target:
        await ctx.send(
            "⚠️ Please mention a user or provide a user ID.\nExample: `$move @username 3`"
        )
        return

    # Convert speed safely
    try:
        speed = int(speed)
        if speed < 1:
            speed = 1
    except ValueError:
        speed = 2

    guild = ctx.guild
    member = None

    # Resolve member from mention or ID
    mention_match = re.match(r"<@!?(\d+)>", target)
    if mention_match:
        user_id = int(mention_match.group(1))
        member = guild.get_member(user_id)
    else:
        try:
            user_id = int(target)
            member = guild.get_member(user_id)
        except ValueError:
            pass

    if member is None:
        await ctx.send("⚠️ Could not find that user in this server.")
        return

    if member.id in move_tasks:
        await ctx.send("⚠️ That user is already being moved.")
        return

    # Start loop
    task = asyncio.create_task(loop_move(ctx, member, speed))
    move_tasks[member.id] = task
    await ctx.send(
        f"▶️ Started moving **{member.display_name}** randomly every {speed}s."
    )


@bot.command()
async def stop(ctx, target: str = None):
    """Stop moving a user."""

    if not target:
        await ctx.send(
            "⚠️ Please mention a user or provide a user ID.\nExample: `$stop @username`"
        )
        return

    guild = ctx.guild
    member = None

    mention_match = re.match(r"<@!?(\d+)>", target)
    if mention_match:
        user_id = int(mention_match.group(1))
        member = guild.get_member(user_id)
    else:
        try:
            user_id = int(target)
            member = guild.get_member(user_id)
        except ValueError:
            pass

    if member is None:
        await ctx.send("⚠️ Could not find that user in this server.")
        return

    task = move_tasks.pop(member.id, None)
    if task:
        task.cancel()
        await ctx.send(f"⏹️ Stopped moving **{member.display_name}**.")
    else:
        await ctx.send("⚠️ That user is not currently being moved.")


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx,
              target: discord.Member,
              *,
              reason: str = "No reason provided"):
    if target is None:
        await ctx.send(
            "⚠️ Please mention a user or provide their ID. Example: `$ban @user spamming`"
        )
        return

    if target == ctx.author:
        await ctx.send("⚠️ You can't ban yourself.")
        return
    if target == ctx.guild.owner:
        await ctx.send("⚠️ You can't ban the server owner.")
        return
    if ctx.guild.me.top_role.position <= target.top_role.position:
        await ctx.send(
            "⚠️ I cannot ban that user because their role is higher or equal to mine."
        )
        return

    try:
        await target.ban(reason=reason, delete_message_days=0)
        await ctx.send(f"✅ Banned **{target}**. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("⚠️ I don't have permission to ban this user.")
    except discord.HTTPException as e:
        await ctx.send(f"⚠️ Failed to ban user (HTTP error): {e}")


@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, identifier: str = ""):
    if not identifier:
        await ctx.send(
            "⚠️ Provide a user ID or username#discriminator. Example: `$unban 123456789012345678`"
        )
        return

    # Collect bans properly (works in discord.py v2)
    bans = [entry async for entry in ctx.guild.bans()]

    # Try ID first
    try:
        uid = int(identifier)
        for ban_entry in bans:
            if ban_entry.user.id == uid:
                await ctx.guild.unban(
                    ban_entry.user,
                    reason=f"Unbanned by {ctx.author} via command")
                await ctx.send(f"✅ Unbanned {ban_entry.user}.")
                return
    except ValueError:
        pass

    # Fallback: username#discriminator
    if "#" in identifier:
        name, disc = identifier.split("#", 1)
        for ban_entry in bans:
            u = ban_entry.user
            if u.name == name and u.discriminator == disc:
                await ctx.guild.unban(
                    u, reason=f"Unbanned by {ctx.author} via command")
                await ctx.send(f"✅ Unbanned {u}.")
                return

    await ctx.send("⚠️ Could not find a matching banned user.")


# Error handlers
@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⚠️ You don't have permission to ban members.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Couldn't resolve that member. Use mention or ID.")
    else:
        await ctx.send(f"⚠️ Error: {error}")


@unban.error
async def unban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⚠️ You don't have permission to unban members.")
    else:
        await ctx.send(f"⚠️ Error: {error}")


@bot.command()
@commands.has_permissions(ban_members=True)
async def listbans(ctx):
    """List all banned users with username and user ID."""
    bans = [entry async for entry in ctx.guild.bans()]

    if not bans:
        await ctx.send("✅ No users are banned in this server.")
        return

    # Build a formatted list
    lines = []
    for entry in bans:
        user = entry.user
        reason = entry.reason if entry.reason else "No reason"
        lines.append(f"**{user}** (ID: `{user.id}`) — Reason: *{reason}*")

    # Discord message limit = 2000 chars, so chunk if needed
    message = "\n".join(lines)
    if len(message) > 2000:
        chunks = [message[i:i + 1990] for i in range(0, len(message), 1990)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(message)


@bot.command()
async def ping(ctx, *, identifier: str = ""):
    if not identifier:
        await ctx.send("⚠️ Provide a username. Example: `!ping khylian`")
        return

    members = await list_members(ctx)
    for member_ in members:
        # Safely handle nickname (could be None)
        if (member_.name.lower() == identifier.lower() or
            (member_.nick and member_.nick.lower() == identifier.lower())):
            await ctx.send(
                f"✅ {member_.mention} est dans le serveur. Le monde mérite de savoir."
            )
            return
        if (identifier == "fdp"):
            await ctx.send("✅ <@534789344503005184> est une fraude")
            return
    await ctx.send(
        f"⚠️ {identifier} n'existe pas. Il est peut-être mort ou il n'existe pas."
    )


async def list_members(ctx):
    return ctx.guild.members  # all members in the server



#blackjack part

active_games = {}


class BlackjackView(discord.ui.View):

    def __init__(self, game: BlackjackGame, author: discord.User):
        super().__init__(timeout=120)
        self.game = game
        self.author = author

    async def interaction_check(self,
                                interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This is not your game!",
                                                    ephemeral=True)
            return False
        return True

    def make_embed(self, reveal_dealer: bool = False) -> discord.Embed:
        embed = discord.Embed(title="Blackjack", color=discord.Color.green())
        embed.add_field(
            name="Your hand",
            value=
            f"{pretty_cards(self.game.player_cards)} ({self.game.player_value()})",
            inline=False,
        )
        if reveal_dealer or self.game.finished:
            embed.add_field(
                name="Dealer hand",
                value=
                f"{pretty_cards(self.game.dealer_cards)} ({self.game.dealer_value()})",
                inline=False,
            )
        else:
            embed.add_field(
                name="Dealer hand",
                value=f"{self.game.dealer_cards[0]} ??",
                inline=False,
            )
        return embed

    async def update_game(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Blackjack", color=discord.Color.blurple())
        if self.game.finished:
            await end_game(interaction.channel, self.game,
                           self)  # send result + payout
            self.stop()
        else:
            embed = self.make_embed(False)
            try:
                await interaction.response.edit_message(embed=embed, view=self)
            except discord.InteractionResponded:
                await interaction.edit_original_response(embed=embed,
                                                         view=self)

        # Try responding safely
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.InteractionResponded:
            await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction,
                  button: discord.ui.Button):
        self.game.player_hit()
        await self.update_game(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.gray)
    async def stand(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        self.game.player_stand()
        await self.update_game(interaction)

    @discord.ui.button(label="Double", style=discord.ButtonStyle.blurple)
    async def double(self, interaction: discord.Interaction,
                     button: discord.ui.Button):
        if len(self.game.player_cards) != 2:
            await interaction.response.send_message(
                "You can only double at the start.", ephemeral=True)
            return
        self.game.player_double()
        await self.update_game(interaction)

    @discord.ui.button(label="Surrender", style=discord.ButtonStyle.red)
    async def surrender(self, interaction: discord.Interaction,
                        button: discord.ui.Button):
        self.game.result, self.game.payout, self.game.finished = "surrender", -(
            self.game.bet // 2), True
        await self.update_game(interaction)


async def end_game(ctx, game: BlackjackGame, view: BlackjackView):
    embed = view.make_embed(reveal_dealer=True)
    embed.add_field(name="Result", value=result_message(game), inline=False)

    # Disable buttons
    for c in view.children:
        c.disabled = True

    # Update balance when finished
    if game.result == "win":
        await add_amount(ctx, game.player_id, game.bet * 2)
        print("added win" + str(game.bet * 2))
    elif game.result == "blackjack":
        await add_amount(ctx, game.player_id, int(game.bet * 4))
        print("added blackjack" + str(game.bet * 4))
    elif game.result == "tie" or game.result == "push":
        await add_amount(ctx, game.player_id, game.bet)
        print("added tie" + str(game.bet))

    active_games.pop(game.player_id, None)
    await ctx.send(embed=embed, view=view)


@bot.command()
async def blackjack(ctx, bet: int = 10):
    if bet < 0:
        await ctx.send("Va te faire enculé")
        await add_amount(ctx, ctx.author.id, -1000)
    if check_balance(ctx.author.id, bet) is False or bet > 5000:
        await ctx.send("⚠️ Pas assez de pièces ou mise trop élevée. ( max 10000 ou je risque de perdre trop d'argents(j'aime l'argent)) ")
        return
    await add_amount(ctx, ctx.author.id, -bet)
    if ctx.author.id in active_games:
        await ctx.send(" ")
        return
    game = BlackjackGame(ctx.author.id, bet)
    active_games[ctx.author.id] = game

    view = BlackjackView(game, ctx.author)
    embed = view.make_embed(reveal_dealer=game.finished)

    if game.finished:
        embed.add_field(name="Result",
                        value=result_message(game),
                        inline=False)
        for c in view.children:
            c.disabled = True
        active_games.pop(ctx.author.id, None)
    if game.result == "win":
        await add_amount(ctx, ctx.author.id, bet * 2)
    elif game.result == "blackjack":
        await add_amount(ctx, ctx.author.id, int(bet * 4))
    elif game.result == "tie":
        await add_amount(ctx, ctx.author.id, bet)
    await ctx.send(embed=embed, view=view)


async def add_amount(ctx, user_id: int, amount: int):
    rows = []

    # Lire toutes les lignes existantes
    try:
        with open("balances.csv", mode="r", newline="",
                  encoding="utf-8") as file:
            reader = csv.reader(file)
            rows = list(reader)
    except FileNotFoundError:
        rows = []  # Si le fichier n’existe pas encore

    found = False
    for row in rows:
        if row[0] == str(user_id):
            row[1] = str(int(row[1]) + amount)
            found = True
            break

    if not found:
        rows.append([str(user_id), str(amount)])

    # Réécrire tout le fichier avec les valeurs mises à jour
    with open("balances.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(rows)


@bot.command()
async def balance(ctx, user_id: int = 0):
    if user_id == 0:
        user_id = ctx.author.id
    balance = 0
    user = await bot.fetch_user(user_id)
    try:
        with open("balances.csv", mode="r", newline="",
                  encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == str(user_id):
                    balance = int(row[1])
                    break
    except FileNotFoundError:
        await add_amount(ctx, user_id, 0)

    await ctx.send(f"💰 L'utilisateur {user.name} a {balance} pièces.")


def get_last_daily(user_id: int):
    """Get the timestamp of the last daily for a user"""
    try:
        with open(DAILY_COOLDOWN_FILE, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == str(user_id):
                    return float(row[1])
    except FileNotFoundError:
        pass
    return 0

def save_daily_cooldown(user_id: int, timestamp: float):
    """Save the daily cooldown timestamp for a user"""
    rows = []
    try:
        with open(DAILY_COOLDOWN_FILE, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            rows = list(reader)
    except FileNotFoundError:
        rows = []
    
    found = False
    for row in rows:
        if row[0] == str(user_id):
            row[1] = str(timestamp)
            found = True
            break
    
    if not found:
        rows.append([str(user_id), str(timestamp)])
    
    with open(DAILY_COOLDOWN_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(rows)

@bot.command()
async def daily(ctx):
    user_id = ctx.author.id
    current_time = time.time()
    last_daily = get_last_daily(user_id)
    cooldown_duration = 86400  # 24 hours in seconds
    
    time_since_last = current_time - last_daily
    
    if time_since_last < cooldown_duration:
        time_remaining = cooldown_duration - time_since_last
        heures = int(time_remaining // 3600)
        minutes = int((time_remaining % 3600) // 60)
        secondes = int(time_remaining % 60)
        
        await ctx.send(
            f"⚠️ {ctx.author.mention}, tu as déjà pris ton daily. "
            f"Réessaye dans {heures}h {minutes}m {secondes}s."
        )
        return
    
    # Give the daily reward
    nombre_random = random.randint(50, 200)
    await add_amount(ctx, user_id, nombre_random)
    save_daily_cooldown(user_id, current_time)
    await ctx.send(f"🎁 Vous avez reçu {nombre_random} pièces !")


@bot.command()
async def shop(ctx):
    # 1. Create an embed
    embed = discord.Embed(title="🛒 Shop",
                          description="Choose an item to buy:",
                          color=discord.Color.blue())
    embed.add_field(name="1 Faveur", value="500,000 coins ⚔️(1 par mois ou je t'éclate)", inline=False)
    embed.add_field(name="X Genesis Crystal",
                    value="50,000 coins/10 unités",
                    inline=False)
    embed.set_footer(text="Use $balance to check your coins.")

    # 2. Create buttons
    faveur_button = discord.ui.Button(label="Acheter Faveur",
                                      style=discord.ButtonStyle.green)
    genesis_button = discord.ui.Button(label="Acheter Genesis Cristal",
                                       style=discord.ButtonStyle.blurple)
    unknown_button = discord.ui.Button(label="???",
                                       style=discord.ButtonStyle.gray)

    # --- Callbacks ---
    async def faveur_callback(interaction: discord.Interaction):
        user_id = interaction.user.id
        if check_balance(user_id, 500000):
            await add_amount(ctx, user_id, -500000)
            await alert_kami(ctx, user_id, "faveur")
            await interaction.response.send_message("✅ Achat réussi : Faveur",
                                                    ephemeral=True)
        else:
            await interaction.response.send_message("❌ Pas assez de pièces.",
                                                    ephemeral=True)
    
    async def genesis_callback(interaction: discord.Interaction):
        await interaction.response.send_message(
            "💎 Combien de Genesis Crystals veux-tu acheter ? (réponds avec un nombre)",
            ephemeral=True
        )

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            # Attendre la réponse pendant 30 secondes
            msg = await bot.wait_for("message", check=check, timeout=30.0)
            amount = int(msg.content)

            if amount <= 0:
                await interaction.followup.send("❌ Nombre invalide.", ephemeral=True)
                return

            cost = amount * 50_000
            user_id = interaction.user.id

            if check_balance(user_id, cost):  # ta fonction de vérification
                await add_amount(ctx, user_id, -cost)  # débiter
                await interaction.followup.send(
                    f"✅ Tu as acheté {amount} Genesis Crystals pour {cost:,} pièces.",
                    ephemeral=True
                )
                await alert_kami(ctx, user_id, f"{amount} Genesis Crystals")
            else:
                await interaction.followup.send(
                    "❌ Pas assez de pièces pour cet achat.", ephemeral=True
                )

        except asyncio.TimeoutError:
            await interaction.followup.send("⌛ Temps écoulé, achat annulé.",
                                            ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ Tu dois entrer un nombre valide.",
                                            ephemeral=True)

    async def unknown_callback(interaction: discord.Interaction):
        await interaction.response.send_message(
            f"{interaction.user.mention} va te faire foutre", ephemeral=True)

    # Attach callbacks
    faveur_button.callback = faveur_callback
    genesis_button.callback = genesis_callback
    unknown_button.callback = unknown_callback

    # 3. Create a view and add the buttons
    view = discord.ui.View()
    view.add_item(faveur_button)
    view.add_item(genesis_button)
    view.add_item(unknown_button)

    # 4. Send embed + buttons
    await ctx.send(embed=embed, view=view)


# ---- Helpers outside shop ----


def check_balance(user_id: int, amount: int) -> bool:
    try:
        with open("balances.csv", mode="r", newline="",
                  encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == str(user_id):
                    return int(row[1]) >= amount
    except FileNotFoundError:
        return False
    return False


async def alert_kami(ctx, user_id: int, texte: str):
    id_kami = 821727043027992626
    user = await bot.fetch_user(user_id)
    kami = await bot.fetch_user(id_kami)
    await kami.send(f"{user.name} a acheté : {texte}")

@bot.command()
async def info(ctx):
    embed = discord.Embed(title="📜 Informations",
                          description="Informations sur le bot",
                          color=discord.Color.blue())
    embed.add_field(name="💰 Balance", value="Voir votre balance", inline=False)
    embed.add_field(name="🃏 Blackjack", value="Jouer au blackjack", inline=False)
    embed.add_field(name="🛒 Shop", value="Acheter des items", inline=False)
    embed.add_field(name="🎁 Daily", value="Prendre votre daily", inline=False)
    embed.add_field(name="📜 Info", value="Simple si ta la thune et tu la dépense dans le shop, je t'achète IRL le truc (sur genshin ta cru quoi fdp)", inline=False)
    embed.set_footer(text="Bot créé par kami230 (logic ptn)")
    await ctx.send(embed=embed)


@bot.command()
async def four_corners(ctx):
    if ctx.author.id == 821727043027992626:
        embed = discord.Embed(title="🏹 Four Corners", description="Jouer au four corners", color=discord.Color.blue())
        enter_button = discord.ui.Button(label="Participer",style=discord.ButtonStyle.green)
        liste_users = []
        async def enter_callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            if user_id in liste_users:
                await interaction.response.send_message("❌ Vous êtes déjà inscrit.", ephemeral=True)
            else:
                liste_users.append(user_id)
                await interaction.response.send_message("✅ Vous êtes inscrit.", ephemeral=True)
        view = discord.ui.View()
        view.add_item(enter_button)
        enter_button.callback = enter_callback
        await ctx.send(embed=embed, view=view)
        await asyncio.sleep(30)
        await delete_last(ctx)
    
        await start(ctx, liste_users)
    else:
        ctx.send("Ta crue quoi fdp")

async def start(ctx, players):
    if len(players) < 1:
        await ctx.send("⚠️ Pas assez de joueurs pour commencer.")
        return
    else:    
        while len(players) > 1:
            players = await round(ctx, players)
            await asyncio.sleep(5)
        if len(players) == 1:
            await ctx.send(f"🏆 Le gagnant est <@{players[0]}> !")
            await add_amount(ctx, players[0], 10000)
                
        
    
async def round(ctx, players):
    embed = discord.Embed(
        title="🟦 Four Corners",
        description="Choisissez un coin (vous avez 60s) !",
        color=discord.Color.purple()
    )

    corners = ["🔴 Corner 1", "🟢 Corner 2", "🔵 Corner 3", "🟡 Corner 4"]
    choices = {}  # {user_id: corner}
    view = discord.ui.View(timeout=60)

    def make_callback(corner_name):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            if user_id not in players:
                await interaction.response.send_message("❌ Tu ne joues pas.", ephemeral=True)
                return
            choices[user_id] = corner_name
            await interaction.response.send_message(
                f"✅ Tu as choisi {corner_name}.", ephemeral=True
            )
            if len(choices) == len(players):
                view.stop()
        return callback

    for corner in corners:
        btn = discord.ui.Button(label=corner, style=discord.ButtonStyle.secondary)
        btn.callback = make_callback(corner)
        view.add_item(btn)

    # ✅ Envoie le message tout de suite
    msg = await ctx.send(embed=embed, view=view)

    # Attends que tout le monde choisisse OU que 60s passent
    await view.wait()

    # Tire un coin au hasard
    eliminated_corner = random.choice(corners)
    eliminated_players = [p for p, c in choices.items() if c == eliminated_corner]

    for user_id in eliminated_players:
        if user_id in players:
            players.remove(user_id)

    result = f"❌ Le coin éliminé est **{eliminated_corner}**!\n"
    if eliminated_players:
        result += "Joueurs éliminés: " + ", ".join(f"<@{uid}>" for uid in eliminated_players)
    else:
        result += "Personne n’était sur ce coin. 😅"

    result_embed = discord.Embed(
        title="Résultat du round",
        description=result,
        color=discord.Color.red()
    )

    # ✅ Met à jour le message avec le résultat
    await msg.edit(embed=result_embed, view=None)

    return players

async def delete_last(ctx):
    channel = ctx.channel
    last_message = await anext(channel.history(limit=1))  # récupère le plus récent
    await last_message.delete()

@bot.command()
async def give(ctx, user: discord.User, amount: int):
    if check_balance(ctx.author.id, amount):
        if amount < 0 and ctx.author.id != 821727043027992626:
            return ctx.send("Va te faire enculé")
        await add_amount(ctx, user.id, amount)
        await add_amount(ctx, ctx.author.id, -amount)
        await ctx.send(f"✅ {amount} pièces ont été ajoutées à {user.name}.")
    else:
        await ctx.send("❌ Pas assez de pièces.")

@bot.command()
async def give_role(ctx, member: discord.Member, *, role_name: str):
    """Give a role to a user."""
    role = discord.utils.get(ctx.guild.roles, name=role_name)

    if not role:
        await ctx.send(f"❌ Role '{role_name}' not found.")
        return

    try:
        await member.add_roles(role)
        await ctx.send(f"✅ {member.mention} has been given the role **{role.name}**!")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to give that role.")
    except discord.HTTPException:
        await ctx.send("⚠️ Something went wrong while giving the role.")



bot.run(TOKEN)
