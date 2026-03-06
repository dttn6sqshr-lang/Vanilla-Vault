import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from datetime import datetime
import random

# ---------------------
# Bot setup
# ---------------------
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------
# Data storage
# ---------------------
reviews_db = {}  # {user_id: {"count": int, "timestamps": [datetime], "reviews": [dict]}}
review_counter = 0  # Unique review IDs
daily_counter = 0   # Daily reviews

# ---------------------
# Helper functions
# ---------------------
def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name="ᐢᗜᐢ﹑logs！﹒")

def assign_rarity():
    roll = random.randint(1,100)
    if roll <= 70:
        return "Common"
    elif roll <= 95:
        return "Rare"
    else:
        return "Legendary"

def record_review(user_id, notes):
    global review_counter, daily_counter
    review_counter += 1
    daily_counter += 1
    now = datetime.utcnow()
    rarity = assign_rarity()
    review_data = {
        "id": review_counter,
        "timestamp": now,
        "notes": notes,
        "rarity": rarity
    }

    if user_id not in reviews_db:
        reviews_db[user_id] = {"count": 1, "timestamps": [now], "reviews": [review_data]}
    else:
        reviews_db[user_id]["count"] += 1
        reviews_db[user_id]["timestamps"].append(now)
        reviews_db[user_id]["reviews"].append(review_data)

    return review_data, daily_counter

def get_user_stats(user_id):
    if user_id not in reviews_db:
        return 0, []
    return reviews_db[user_id]["count"], reviews_db[user_id]["timestamps"]

def get_leaderboard(top=10):
    sorted_users = sorted(reviews_db.items(), key=lambda x: x[1]["count"], reverse=True)
    return sorted_users[:top]

# ---------------------
# Event: Review tracking
# ---------------------
@bot.event
async def on_message(message):
    global daily_counter
    if message.author.bot:
        return

    if message.channel.name == "✿﹒⤷﹒﹒﹒reviews":
        # Basic verification: notes length
        lines = message.content.splitlines()
        notes_line = ""
        for line in lines:
            if line.lower().startswith("<:ptc_brownheart3") or "**Notes**" in line:
                notes_line = line
                break
        notes = notes_line.split(":",1)[1].strip() if ":" in notes_line else "No notes"

        if len(notes) < 15:
            await message.add_reaction("❌")
            return  # Ignore short reviews

        # Record review
        review_data, daily_count = record_review(message.author.id, notes)

        # Add mascot reaction
        try:
            await message.add_reaction("<:CC_Mascotlove:1479289149616947251>")
        except:
            pass

        # Audit log
        log_channel = get_log_channel(message.guild)
        if log_channel:
            hour = review_data["timestamp"].hour
            embed = discord.Embed(
                title="︶︶⊹︶ Review Submitted",
                description=f"Review ID: #{review_data['id']}\n"
                            f"User: {message.author.display_name}\n"
                            f"Rarity: {review_data['rarity']}\n"
                            f"Timestamp: {review_data['timestamp'].strftime('%Y-%m-%d %H:%M UTC')}\n"
                            f"Heatmap: {hour}:00-{hour+1}:00 UTC\n"
                            f"Notes: {review_data['notes']}\n"
                            f"Bot Status: Total Reviews Today: {daily_count}",
                color=0x1b1c23
            )
            await log_channel.send(embed=embed)

# ---------------------
# Slash Commands
# ---------------------
@bot.tree.command(name="reviews", description="Check a user's total reviews")
@app_commands.describe(user="The user to check")
async def reviews(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    count, timestamps = get_user_stats(target.id)
    embed = discord.Embed(
        title="═══✱ Vanilla Vault Stats ✱═══",
        description=f"{target.display_name} has submitted **{count}** reviews",
        color=0x1b1c23
    )
    if timestamps:
        last_review = timestamps[-1].strftime("%Y-%m-%d %H:%M UTC")
        embed.add_field(name="Last Review", value=last_review, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mystats", description="Check your review stats")
async def mystats(interaction: discord.Interaction):
    count, timestamps = get_user_stats(interaction.user.id)
    embed = discord.Embed(
        title="═══✱ Vanilla Vault Stats ✱═══",
        description=f"{interaction.user.display_name} has submitted **{count}** reviews",
        color=0x1b1c23
    )
    if timestamps:
        last_review = timestamps[-1].strftime("%Y-%m-%d %H:%M UTC")
        embed.add_field(name="Last Review", value=last_review, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="Show top reviewers")
async def leaderboard(interaction: discord.Interaction):
    top_users = get_leaderboard()
    desc = ""
    for i, (user_id, data) in enumerate(top_users, start=1):
        member = interaction.guild.get_member(user_id)
        if member:
            desc += f"{i}. {member.display_name} — {data['count']} reviews\n"
    if not desc:
        desc = "No reviews yet!"
    embed = discord.Embed(
        title="𝐕𝐀𝐍𝐈𝐋𝐋𝐀 𝐕𝐀𝐔𝐋𝐓 𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃",
        description=desc,
        color=0x1b1c23
    )
    await interaction.response.send_message(embed=embed)

# ---------------------
# Daily counter reset (optional)
# ---------------------
@tasks.loop(hours=24)
async def reset_daily_counter():
    global daily_counter
    daily_counter = 0

@bot.event
async def on_ready():
    await bot.tree.sync()
    reset_daily_counter.start()
    print(f"Vanilla Vault Bot Ready as {bot.user}")

bot.run(TOKEN)