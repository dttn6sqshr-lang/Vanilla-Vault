import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from datetime import datetime
import random
import json

# ---------------------
# Bot setup
# ---------------------
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------
# Data storage
# ---------------------
DATA_FILE = "reviews_archive.json"

# Load existing data if exists
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        archive_data = json.load(f)
else:
    archive_data = {
        "reviews": [],  # list of all reviews
        "chefs": {}     # chef_id: stats
    }

review_counter = len(archive_data["reviews"])  # Unique review ID

# ---------------------
# Helper functions
# ---------------------
def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name="ᐢᗜᐢ﹑logs！﹒")

def save_archive():
    with open(DATA_FILE, "w") as f:
        json.dump(archive_data, f, indent=4, default=str)

def assign_reputation(average_rating):
    if average_rating < 3.0:
        return "Needs Improvement"
    elif average_rating < 4.0:
        return "Good Chef"
    elif average_rating < 4.6:
        return "Trusted Chef"
    elif average_rating < 4.9:
        return "Elite Chef"
    else:
        return "Legendary Chef"

def update_chef_stats(chef_id, rating):
    chef_data = archive_data["chefs"].get(str(chef_id), {"total_reviews": 0, "sum_ratings": 0})
    chef_data["total_reviews"] += 1
    chef_data["sum_ratings"] = chef_data.get("sum_ratings",0) + rating
    chef_data["average_rating"] = round(chef_data["sum_ratings"] / chef_data["total_reviews"], 2)
    chef_data["reputation"] = assign_reputation(chef_data["average_rating"])
    archive_data["chefs"][str(chef_id)] = chef_data

def parse_rating(content):
    """
    Looks for 'Rating: X/10' or 'Rating: 5' style in review message.
    Defaults to 5 if not found.
    """
    lines = content.splitlines()
    for line in lines:
        line = line.lower()
        if "rating" in line:
            parts = line.split(":")
            if len(parts) > 1:
                value = parts[1].strip().split("/")[0]
                try:
                    rating = float(value)
                    return max(min(rating, 10), 0)
                except:
                    continue
    return 5  # Default rating

def record_review(user, chef, rating, notes):
    global review_counter
    review_counter += 1
    now = datetime.utcnow()
    review_entry = {
        "id": review_counter,
        "user_id": user.id,
        "user_name": user.display_name,
        "chef_id": chef.id,
        "chef_name": chef.display_name,
        "rating": rating,
        "notes": notes,
        "timestamp": now.isoformat()
    }
    archive_data["reviews"].append(review_entry)
    update_chef_stats(chef.id, rating)
    save_archive()
    return review_entry

def get_chef_stats(chef_id):
    return archive_data["chefs"].get(str(chef_id), {"total_reviews":0, "average_rating":0, "reputation":"N/A"})

def get_chef_leaderboard(top=10):
    sorted_chefs = sorted(
        archive_data["chefs"].items(),
        key=lambda x: x[1]["average_rating"],
        reverse=True
    )
    return sorted_chefs[:top]

# ---------------------
# Event: Review Tracking
# ---------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.name == "✿﹒⤷﹒﹒﹒reviews":
        lines = message.content.splitlines()
        chef_mention = None
        notes = "No notes"
        for line in lines:
            if "chef" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    chef_mention = parts[1].strip()
            elif "notes" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    notes = parts[1].strip()
        if not chef_mention:
            await message.add_reaction("❌")
            return
        # Extract user ID from mention
        chef_id = int(''.join(filter(str.isdigit, chef_mention)))
        chef_member = message.guild.get_member(chef_id)
        if not chef_member:
            await message.add_reaction("❌")
            return
        rating = parse_rating(message.content)
        review_entry = record_review(message.author, chef_member, rating, notes)
        # Add reaction
        try:
            await message.add_reaction("<:CC_Mascotlove:1479289149616947251>")
        except:
            pass
        # Audit log
        log_channel = get_log_channel(message.guild)
        if log_channel:
            hour = datetime.fromisoformat(review_entry["timestamp"]).hour
            embed = discord.Embed(
                title=f"︶︶⊹︶ Review Submitted by {message.author.display_name}",
                description=f"Review ID: #{review_entry['id']}\n"
                            f"Chef: {chef_member.display_name}\n"
                            f"Rating: {rating}/10\n"
                            f"Notes: {notes}\n"
                            f"Hour (UTC): {hour}:00-{hour+1}:00\n"
                            f"Chef Reputation: {get_chef_stats(chef_member.id)['reputation']}",
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
    user_reviews = [r for r in archive_data["reviews"] if r["user_id"]==target.id]
    count = len(user_reviews)
    embed = discord.Embed(
        title="═══✱ Vanilla Vault Stats ✱═══",
        description=f"{target.display_name} has submitted **{count}** reviews",
        color=0x1b1c23
    )
    if user_reviews:
        last_review = user_reviews[-1]["timestamp"]
        embed.add_field(name="Last Review", value=last_review, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="chefstats", description="View stats for a chef")
@app_commands.describe(chef="The chef to check")
async def chefstats(interaction: discord.Interaction, chef: discord.Member):
    stats = get_chef_stats(chef.id)
    embed = discord.Embed(
        title=f"═══✱ Chef Stats: {chef.display_name} ✱═══",
        description=f"Total Reviews: {stats['total_reviews']}\n"
                    f"Average Rating: {stats['average_rating']}/10\n"
                    f"Reputation: {stats['reputation']}",
        color=0x1b1c23
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="chefleaderboard", description="Show top chefs by rating")
async def chefleaderboard(interaction: discord.Interaction):
    top_chefs = get_chef_leaderboard()
    desc = ""
    for i, (chef_id, data) in enumerate(top_chefs, start=1):
        member = interaction.guild.get_member(int(chef_id))
        if member:
            desc += f"{i}. {member.display_name} — {data['average_rating']}/10 ⭐ ({data['total_reviews']} reviews)\n"
    if not desc:
        desc = "No chefs yet!"
    embed = discord.Embed(
        title="═══✱ Vanilla Vault Chef Leaderboard ✱═══",
        description=desc,
        color=0x1b1c23
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="archive", description="Export all reviews in JSON")
async def archive(interaction: discord.Interaction):
    if os.path.exists(DATA_FILE):
        file = discord.File(DATA_FILE, filename="reviews_archive.json")
        await interaction.response.send_message("Here’s the full review archive:", file=file)
    else:
        await interaction.response.send_message("No archive available yet.")

# ---------------------
# Bot ready
# ---------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Vanilla Vault Bot Ready as {bot.user}")

bot.run(TOKEN)