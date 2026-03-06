import discord
from discord.ext import commands
from discord import app_commands
import os
from datetime import datetime

# ---------------------
# Bot setup
# ---------------------
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Needed to read messages
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------
# Data storage
# ---------------------
# In-memory dictionary; replace with persistent database if desired
reviews_db = {}  # {user_id: {"count": int, "timestamps": [datetime]}}

# ---------------------
# Helper Functions
# ---------------------
def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name="ᐢᗜᐢ﹑logs！﹒")

def record_review(user_id):
    now = datetime.utcnow()
    if user_id not in reviews_db:
        reviews_db[user_id] = {"count": 1, "timestamps": [now]}
    else:
        reviews_db[user_id]["count"] += 1
        reviews_db[user_id]["timestamps"].append(now)
    return reviews_db[user_id]["count"], now

def get_user_stats(user_id):
    if user_id not in reviews_db:
        return 0, []
    return reviews_db[user_id]["count"], reviews_db[user_id]["timestamps"]

def get_leaderboard(top=10):
    sorted_users = sorted(reviews_db.items(), key=lambda x: x[1]["count"], reverse=True)
    return sorted_users[:top]

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
# Automatic review tracking
# ---------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Only count messages in the review channel
    if message.channel.name == "✿﹒⤷﹒﹒﹒reviews":
        user_id = message.author.id
        count, timestamp = record_review(user_id)

        # Audit log embed
        log_channel = get_log_channel(message.guild)
        if log_channel:
            log_embed = discord.Embed(
                title="︶︶⊹︶ Review Submitted",
                description=f"{message.author.display_name} submitted a review",
                color=0x1b1c23
            )
            await log_channel.send(embed=log_embed)

# ---------------------
# Bot ready
# ---------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Vanilla Vault Bot Ready as {bot.user}")

bot.run(TOKEN)