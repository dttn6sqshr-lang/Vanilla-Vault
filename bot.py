import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
from datetime import datetime
import asyncio

# ---------------------
# Load environment & bot
# ---------------------
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------
# Data storage
# ---------------------
# In-memory dictionary; replace with database for persistence
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
        title=f"🍰 {target.display_name}'s Reviews",
        description=f"Total Reviews: **{count}**",
        color=0xFFD8F0
    )
    if timestamps:
        last_review = timestamps[-1].strftime("%Y-%m-%d %H:%M UTC")
        embed.add_field(name="Last Review", value=last_review, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mystats", description="Check your review stats")
async def mystats(interaction: discord.Interaction):
    count, timestamps = get_user_stats(interaction.user.id)
    embed = discord.Embed(
        title=f"🍦 Your Vanilla Vault Stats",
        description=f"Total Reviews: **{count}**",
        color=0xFFD8F0
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
            desc += f"{i}. **{member.display_name}** - {data['count']} reviews\n"
    if not desc:
        desc = "No reviews yet!"
    embed = discord.Embed(
        title="🍭 Vanilla Vault Leaderboard",
        description=desc,
        color=0xFFD8F0
    )
    await interaction.response.send_message(embed=embed)

# ---------------------
# Add Review Command (for staff or automation)
# ---------------------
@bot.tree.command(name="addreview", description="Add a review to a user")
@app_commands.describe(user="The user to add a review to")
async def addreview(interaction: discord.Interaction, user: discord.Member):
    # Optional: restrict to staff roles
    # if not any(role.name in ["Staff", "Admin"] for role in interaction.user.roles):
    #     return await interaction.response.send_message("No permission.", ephemeral=True)

    count, timestamp = record_review(user.id)

    # Send pastel embed confirmation
    embed = discord.Embed(
        title="🍦 Vanilla Vault Update",
        description=f"Added a review for **{user.display_name}**!\nTotal Reviews: **{count}**",
        color=0xFFD8F0
    )
    embed.set_footer(text=f"Reviewed by {interaction.user.display_name} | {timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
    await interaction.response.send_message(embed=embed)

    # Audit log
    log = get_log_channel(interaction.guild)
    if log:
        log_embed = discord.Embed(
            title="📜 Review Log",
            color=0xFFD8F0
        )
        log_embed.add_field(name="User", value=user.name, inline=True)
        log_embed.add_field(name="Staff", value=interaction.user.name, inline=True)
        log_embed.add_field(name="Total Reviews", value=count, inline=False)
        log_embed.set_footer(text=f"Time: {timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
        await log.send(embed=log_embed)

# ---------------------
# Ready Event
# ---------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Vanilla Vault Bot Ready as {bot.user}")

bot.run(TOKEN)