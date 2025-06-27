import os
import json
import discord
import asyncio

# Load configuration from environment
TOKEN = os.environ['DISCORD_BOT_TOKEN']
CHANNEL_ID = int(os.environ['DISCORD_CHANNEL_ID'])

# Environment-variable names for egg-role mappings
ROLE_ENV_MAP = {
    "Slime":    "ROLE_SLIMEEGG",
    "Rock":     "ROLE_ROCKEGG",
    "Bismuth":  "ROLE_BISMUTHEGG",
    "Magma":    "ROLE_MAGMAEGG"
}

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    # Load shop data
    with open("shop.json", "r") as f:
        data = json.load(f)
    eggs = data.get("shop", [])
    timestamp = data.get("generated_at", "unknown time")

    # Deduplicate while preserving order
    seen = set()
    unique_eggs = []
    for egg in eggs:
        if egg not in seen:
            seen.add(egg)
            unique_eggs.append(egg)

    # Build mentions / names
    mentions = []
    for egg in unique_eggs:
        env_var = ROLE_ENV_MAP.get(egg)
        role_id = os.environ.get(env_var) if env_var else None
        if role_id:
            mentions.append(f"<@&{role_id}>")
        else:
            mentions.append(f"{egg} Egg")

    # Compose message
    egg_list_md = "\n".join(f"- {egg}" for egg in eggs)
    mention_line = " ".join(mentions) if mentions else ""
    content = (
        f"{mention_line}"
        f"🛒 **New Egg Shop**\n"
        f"{egg_list_md}\n\n"
    )

    # Send and react
    channel = client.get_channel(CHANNEL_ID)
    msg = await channel.send(content)
    for emoji in ("👍", "😐", "👎"):
        await msg.add_reaction(emoji)

    await client.close()

if __name__ == "__main__":
    asyncio.run(client.start(TOKEN))
