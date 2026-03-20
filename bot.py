import discord
from discord.ext import commands, tasks
import os, json, random, asyncio
from datetime import datetime
from dotenv import load_dotenv

# ---------------------
# CONFIG
# ---------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("⚠️ Discord token not found! Set DISCORD_TOKEN in environment variables or .env file.")

REVIEW_CHANNEL = "✿﹒⤷﹒﹒﹒reviews"
ANNOUNCE_CHANNEL = "—﹒⩇⩇﹒announce"
PING_ROLE_ID = 1474602306149290187
REVIEW_COOLDOWN = 20

# COLORS
SOFT = 0xF8E1E7
CREAM = 0xFFF6F0
GOLD = 0xFFD700

DATA_FILE = "reviews_archive.json"

# ---------------------
# BOT SETUP
# ---------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------
# LOAD DATA
# ---------------------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"reviews": [], "chefs": {}, "users": {}}

review_counter = len(data["reviews"])
cooldowns = {}

# ---------------------
# UTILS
# ---------------------
def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def rep(avg):
    if avg < 3: return "Needs Improvement"
    if avg < 4: return "Good Chef"
    if avg < 4.6: return "Trusted Chef"
    if avg < 4.9: return "Elite Chef"
    return "Legendary Chef"

def chef_stats(cid):
    return data["chefs"].get(str(cid), {
        "total_reviews": 0,
        "average_rating": 0,
        "reputation": "N/A",
        "announced": False
    })

def update_chef(cid, rating):
    c = data["chefs"].get(str(cid), {"total_reviews":0,"sum":0, "announced": False})
    c["total_reviews"] += 1
    c["sum"] += rating
    c["average_rating"] = round(c["sum"]/c["total_reviews"],2)
    c["reputation"] = rep(c["average_rating"])
    data["chefs"][str(cid)] = c
    return c

def update_streak(uid):
    today = datetime.utcnow().date()
    u = data["users"].get(str(uid), {"last":None,"streak":0})
    if u["last"]:
        last = datetime.fromisoformat(u["last"]).date()
        if (today - last).days == 1:
            u["streak"] += 1
        elif last != today:
            u["streak"] = 1
    else:
        u["streak"] = 1
    u["last"] = datetime.utcnow().isoformat()
    data["users"][str(uid)] = u
    return u

def parse_rating(msg):
    for line in msg.splitlines():
        if "rating" in line.lower():
            try:
                return float(line.split(":")[1].split("/")[0])
            except:
                pass
    return 5

# ---------------------
# ANNOUNCEMENTS
# ---------------------
async def announce(guild, member, stats):
    ch = discord.utils.get(guild.text_channels, name=ANNOUNCE_CHANNEL)
    role = guild.get_role(PING_ROLE_ID)
    if not ch:
        return

    # buildup animation
    for line in [
        "** **",
        "ㅤsomething is shifting within the vault…",
        "ㅤa creation has caught attention…",
        "ㅤand now… it’s undeniable ✧"
    ]:
        await ch.send(line)
        await asyncio.sleep(1.2)

    name = member.display_name
    if stats["average_rating"] >= 9:
        name = f"✧･ﾟ: *✧･ﾟ:* {name} *:･ﾟ✧*:･ﾟ✧"

    msg = (
        "** **\n"
        "ㅤ࣭ ㅤㅤׂ ㅤ ㅤˑㅤ  ㅤ۟ ㅤ₊\n"
        "        __vanilla vault spotlight__\n\n"
        "-# ⟢   **a new top chef emerges**   ⸝⸝\n"
        "-# ┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
        f"                **{name}**\n\n"
        f"-# <:emoji_39:1483249281237254326> `Rating` : `{stats['average_rating']}/10`\n"
        f"-# <:emoji_39:1483249281237254326> `Reviews` : `{stats['total_reviews']}`\n"
        f"-# <:emoji_39:1483249281237254326> `Reputation` : `{stats['reputation']}`"
    )

    if role:
        await ch.send(role.mention)
    await ch.send(msg)

# ---------------------
# FEATURED DAILY CHEF
# ---------------------
@tasks.loop(hours=24)
async def featured():
    await bot.wait_until_ready()
    if not data["chefs"]:
        return
    guild = bot.guilds[0]
    cid = random.choice(list(data["chefs"].keys()))
    member = guild.get_member(int(cid))
    if member:
        await announce(guild, member, chef_stats(cid))

# ---------------------
# REVIEW TRACKING
# ---------------------
@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    await bot.process_commands(msg)  # important!

    if msg.channel.name != REVIEW_CHANNEL:
        return

    now = datetime.utcnow().timestamp()
    uid = msg.author.id

    if uid in cooldowns:
        left = int(cooldowns[uid] - now)
        if left > 0:
            await msg.reply(f"⏳ wait {left}s")
            return

    cooldowns[uid] = now + REVIEW_COOLDOWN

    chef_id = None
    notes = "No notes"

    for l in msg.content.splitlines():
        if "chef" in l.lower():
            try:
                chef_id = int(''.join(filter(str.isdigit, l)))
            except ValueError:
                chef_id = None
        if "notes" in l.lower():
            parts = l.split(":")
            if len(parts) > 1:
                notes = parts[1].strip()

    if not chef_id:
        await msg.add_reaction("❌")
        return

    member = msg.guild.get_member(chef_id)
    if not member:
        await msg.add_reaction("❌")
        return

    rating = parse_rating(msg.content)

    global review_counter
    review_counter += 1

    data["reviews"].append({
        "id": review_counter,
        "user_id": uid,
        "chef_id": chef_id,
        "rating": rating,
        "notes": notes,
        "time": datetime.utcnow().isoformat()
    })

    stats = update_chef(chef_id, rating)
    update_streak(uid)
    save()

    await msg.add_reaction("<:CC_Mascotlove:1479289149616947251>")

    # top chef trigger
    if stats["average_rating"] >= 9 and not stats.get("announced"):
        stats["announced"] = True
        data["chefs"][str(chef_id)] = stats
        save()
        await announce(msg.guild, member, stats)

# ---------------------
# CHEF STATS COMMAND
# ---------------------
@bot.tree.command(name="chefstats")
async def chefstats_cmd(interaction: discord.Interaction, chef: discord.Member):
    stats = chef_stats(chef.id)
    name = chef.display_name
    if stats["average_rating"] >= 9:
        name = f"✧･ﾟ: *✧･ﾟ:* {name} *:･ﾟ✧*:･ﾟ✧"

    desc = (
        "** **\n"
        "<:emoji_39:1483249281237254326> — ** Chef **\n"
        f"﹒{name}\n\n"
        "<:emoji_39:1483249281237254326> — ** Rating **\n"
        f"﹒`{stats['average_rating']}/10`\n\n"
        "<:emoji_39:1483249281237254326> — ** Reviews **\n"
        f"﹒`{stats['total_reviews']}`\n\n"
        "<:emoji_39:1483249281237254326> — ** Reputation **\n"
        f"﹒{stats['reputation']}"
    )

    embed = discord.Embed(
        title="୨୧ ﹒chef dossier",
        description=desc,
        color=CREAM if stats["average_rating"] < 9 else GOLD
    )

    await interaction.response.send_message(embed=embed)

# ---------------------
# REVIEWS PROFILE COMMAND
# ---------------------
@bot.tree.command(name="reviews")
async def reviews_cmd(interaction: discord.Interaction, user: discord.Member = None):
    target = user or interaction.user
    reviews = [r for r in data["reviews"] if r["user_id"] == target.id]

    count = len(reviews)
    last = "no entries"

    if reviews:
        last = datetime.fromisoformat(reviews[-1]["time"]).strftime("%b %d • %H:%M UTC")

    streak = data["users"].get(str(target.id), {}).get("streak", 0)

    title = "new reviewer"
    if count >= 100: title = "master critic"
    elif count >= 50: title = "critic"
    elif count >= 10: title = "taster"

    desc = (
        "** **\n"
        f"        **{target.display_name}**\n"
        f"        ﹒{title}\n\n"
        "        ┈┈┈┈┈┈┈┈\n\n"
        "<:emoji_39:1483249281237254326> — ** activity **\n"
        f"﹒reviews: `{count}`\n"
        f"﹒streak: `{streak} days`\n\n"
        "<:emoji_39:1483249281237254326> — ** latest **\n"
        f"﹒{last}\n\n"
        "        ┈┈┈┈┈┈┈┈"
    )

    embed = discord.Embed(description=desc, color=SOFT)
    embed.set_thumbnail(url=target.display_avatar.url)

    await interaction.response.send_message(embed=embed)

# ---------------------
# READY
# ---------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    featured.start()
    print(f"Vanilla Vault Bot Ready as {bot.user}")

bot.run(TOKEN)