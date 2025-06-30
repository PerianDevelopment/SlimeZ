import os
import json
import csv
import discord
import asyncio

# Bot config
TOKEN = os.environ['DISCORD_BOT_TOKEN']
CHANNEL_ID = int(os.environ['DISCORD_CHANNEL_ID'])
CSV_PATH   = "eggs.csv"

# Load all emoji & role IDs from CSV
EGG_DATA = {}
with open(CSV_PATH, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        name = row["EggName"]
        EGG_DATA[name] = {
            "emoji_id": row.get("EmojiID", "").strip(),
            "role_id":  row.get("RoleID",  "").strip()
        }

# Build lookup maps
emoji_map = {}
role_map  = {}
for name, data in EGG_DATA.items():
    if data["emoji_id"]:
        emoji_map[name] = f"<:{name}:{data['emoji_id']}>"
    if data["role_id"]:
        role_map[name]  = data["role_id"]

# Fallback emoji from CSV’s “Unknown” row
unknown_emoji = emoji_map.get("Unknown", "")

# Initialize Discord client
intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    # Load shop.json
    with open("shop.json", "r") as f:
        shop_data = json.load(f)
    eggs      = shop_data.get("current_shop", [])
    timestamp = shop_data.get("generated_at", "unknown time")

    # Deduplicate for role pings
    seen = set()
    unique_eggs = []
    for egg in eggs:
        if egg not in seen:
            seen.add(egg)
            unique_eggs.append(egg)

    # Build mentions
    mentions = []
    for egg in unique_eggs:
        role_id = role_map.get(egg)
        if role_id:
            mentions.append(f"<@&{role_id}>")

    # Build the shop list with emojis
    lines = []
    for egg in eggs:
        em = emoji_map.get(egg, unknown_emoji)
        lines.append(f"{em} {egg} Egg")
    egg_list_md = "\n".join(lines)

    # Compose and send
    mention_line = " ".join(mentions)
    content = (
        f"🥚 **Egg Shop Refresh!**\n\n"
        f"{egg_list_md}\n\n"
        f"{mention_line}"
    )
    
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Error: Could not find channel with ID {CHANNEL_ID}")
        await client.close()
        return
        
    msg = await channel.send(content)

    for emoji in ("🥳", "😒"):
        await msg.add_reaction(emoji)

    await client.close()

if __name__ == "__main__":
    asyncio.run(client.start(TOKEN))
