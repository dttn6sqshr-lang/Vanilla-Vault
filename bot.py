import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from datetime import datetime
import random
import re

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = False

bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------
# DATABASES
# ----------------------

reviews_db = {}
chef_db = {}

review_counter = 0
daily_counter = 0

REVIEW_CHANNEL = "✿﹒⤷﹒﹒﹒reviews"
LOG_CHANNEL = "ᐢᗜᐢ﹑logs！﹒"

# ----------------------
# HELPERS
# ----------------------

def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name=LOG_CHANNEL)

def assign_rarity():
    roll = random.randint(1,100)
    if roll <= 70:
        return "Common"
    elif roll <= 95:
        return "Rare"
    else:
        return "Legendary"

# ----------------------
# RATING DETECTION
# ----------------------

def detect_rating(content):

    for line in content.splitlines():

        if "rating" in line.lower():

            stars = line.count("⭐") + line.count("<:PTC_star2")

            if stars > 0:
                return float(stars)

            match = re.search(r'(\d+(\.\d+)?)/(\d+)', line)
            if match:
                score = float(match.group(1))
                total = float(match.group(3))
                return (score / total) * 5

            match = re.search(r'(\d+)%', line)
            if match:
                percent = float(match.group(1))
                return (percent / 100) * 5

    return None

# ----------------------
# CHEF DETECTION
# ----------------------

def detect_chef(content):

    for line in content.splitlines():

        if "chef" in line.lower():

            match = re.search(r'<@!?(\d+)>', line)

            if match:
                return int(match.group(1))

    return None

# ----------------------
# USER REVIEW RECORD
# ----------------------

def record_review(user_id):

    global review_counter
    global daily_counter

    review_counter += 1
    daily_counter += 1

    now = datetime.utcnow()

    if user_id not in reviews_db:
        reviews_db[user_id] = {
            "count": 1,
            "timestamps": [now]
        }
    else:
        reviews_db[user_id]["count"] += 1
        reviews_db[user_id]["timestamps"].append(now)

    return review_counter, now

# ----------------------
# MESSAGE LISTENER
# ----------------------

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.name != REVIEW_CHANNEL:
        return

    review_id, timestamp = record_review(message.author.id)

    rarity = assign_rarity()

    content = message.content

    rating = detect_rating(content)
    chef_id = detect_chef(content)

    # ----------------------
    # CHEF DATABASE
    # ----------------------

    if chef_id:

        if chef_id not in chef_db:

            chef_db[chef_id] = {
                "reviews": 0,
                "total_rating": 0
            }

        chef_db[chef_id]["reviews"] += 1

        if rating:
            chef_db[chef_id]["total_rating"] += rating

    # ----------------------
    # ADD MASCOT REACTION
    # ----------------------

    try:
        await message.add_reaction("<:CC_Mascotlove:1479289149616947251>")
    except:
        pass

    # ----------------------
    # AUDIT LOG
    # ----------------------

    log_channel = get_log_channel(message.guild)

    if log_channel:

        hour = timestamp.hour

        chef_text = "Unknown"
        if chef_id:
            chef_member = message.guild.get_member(chef_id)
            if chef_member:
                chef_text = chef_member.display_name

        rating_text = "None"
        if rating:
            rating_text = f"{rating:.2f} / 5"

        embed = discord.Embed(
            title="︶︶⊹︶ Vanilla Vault Review Logged",
            description=
            f"Review ID: **#{review_id}**\n"
            f"User: {message.author.display_name}\n"
            f"Chef: {chef_text}\n"
            f"Rating: {rating_text}\n"
            f"Rarity: {rarity}\n"
            f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Heatmap Hour: {hour}:00 - {hour+1}:00\n"
            f"Reviews Today: {daily_counter}",
            color=0x1b1c23
        )

        await log_channel.send(embed=embed)

# ----------------------
# USER REVIEW STATS
# ----------------------

@bot.tree.command(name="reviews", description="Check user reviews")
async def reviews(interaction: discord.Interaction, user: discord.Member=None):

    target = user or interaction.user

    count = reviews_db.get(target.id, {}).get("count", 0)

    embed = discord.Embed(
        title="═══✱ Vanilla Vault Reviews ✱═══",
        description=f"{target.display_name} has submitted **{count}** reviews",
        color=0x1b1c23
    )

    await interaction.response.send_message(embed=embed)

# ----------------------
# REVIEW LEADERBOARD
# ----------------------

@bot.tree.command(name="leaderboard", description="Top reviewers")
async def leaderboard(interaction: discord.Interaction):

    sorted_users = sorted(
        reviews_db.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )

    desc = ""

    for i,(user_id,data) in enumerate(sorted_users[:10], start=1):

        member = interaction.guild.get_member(user_id)

        if member:
            desc += f"{i}. {member.display_name} — {data['count']} reviews\n"

    if desc == "":
        desc = "No reviews yet."

    embed = discord.Embed(
        title="𝐕𝐀𝐍𝐈𝐋𝐋𝐀 𝐕𝐀𝐔𝐋𝐓 𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃",
        description=desc,
        color=0x1b1c23
    )

    await interaction.response.send_message(embed=embed)

# ----------------------
# CHEF LEADERBOARD
# ----------------------

@bot.tree.command(name="chefleaderboard", description="Top chefs by rating")
async def chefleaderboard(interaction: discord.Interaction):

    ranking = []

    for chef_id,data in chef_db.items():

        if data["reviews"] == 0:
            continue

        avg = data["total_rating"] / data["reviews"]

        ranking.append((chef_id,avg,data["reviews"]))

    ranking.sort(key=lambda x: x[1], reverse=True)

    desc = ""

    for i,(chef_id,avg,reviews) in enumerate(ranking[:10], start=1):

        member = interaction.guild.get_member(chef_id)

        if member:
            desc += f"{i}. {member.display_name} — ⭐ {avg:.2f} ({reviews} reviews)\n"

    if desc == "":
        desc = "No chefs reviewed yet."

    embed = discord.Embed(
        title="𝐕𝐀𝐍𝐈𝐋𝐋𝐀 𝐕𝐀𝐔𝐋𝐓 𝐂𝐇𝐄𝐅 𝐑𝐀𝐓𝐈𝐍𝐆𝐒",
        description=desc,
        color=0x1b1c23
    )

    await interaction.response.send_message(embed=embed)

# ----------------------
# DAILY RESET
# ----------------------

@tasks.loop(hours=24)
async def reset_daily():

    global daily_counter

    daily_counter = 0

# ----------------------
# READY
# ----------------------

@bot.event
async def on_ready():

    await bot.tree.sync()

    reset_daily.start()

    print(f"Vanilla Vault running as {bot.user}")

bot.run(TOKEN)