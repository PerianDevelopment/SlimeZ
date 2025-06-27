import csv
import json
import sys
import hashlib
import random
import time
from datetime import datetime, timezone, timedelta

def load_eggs(csv_path):
    eggs = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            eggs.append({
                "name": row["EggName"],
                "chance": float(row["PullChance"])
            })
    return eggs

def create_seed_from_secret_and_time(secret_key):
    now = datetime.now(timezone.utc)
    # Round down to nearest 5 minutes
    rounded_minute = now.minute - (now.minute % 5)
    time_component = now.strftime(f"%Y-%m-%dT%H:{rounded_minute:02d}")
    combined = f"{secret_key}:{time_component}"
    h = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    seed_int = int(h, 16) % (2**32)
    return seed_int

def weighted_choice_with_replacement(eggs, n, rng):
    choices = []
    weights = [egg["chance"] for egg in eggs]
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]
    for _ in range(n):
        r = rng.random()
        cumulative = 0
        for egg, w in zip(eggs, normalized_weights):
            cumulative += w
            if r < cumulative:
                choices.append(egg["name"])
                break
    return choices

def wait_until_next_5min_mark():
    now = datetime.now(timezone.utc)
    # Calculate next 5-min mark
    next_minute = (now.minute - now.minute % 5) + 5
    if next_minute >= 60:
        next_hour = now.hour + 1
        next_minute = 0
        next_time = now.replace(hour=next_hour % 24, minute=next_minute, second=0, microsecond=0)
        # If hour rolls over, adjust day accordingly
        if next_hour >= 24:
            next_time += timedelta(days=1)
    else:
        next_time = now.replace(minute=next_minute, second=0, microsecond=0)
    wait_seconds = (next_time - now).total_seconds()
    if wait_seconds > 0:
        print(f"Waiting {wait_seconds:.1f} seconds until next 5-min mark ({next_time.isoformat()})")
        time.sleep(wait_seconds)
    else:
        print("Already at or past 5-min mark, not waiting.")

def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_shop.py <secret_key> <eggs.csv>")
        sys.exit(1)

    secret_key = sys.argv[1]
    csv_path = sys.argv[2]

    eggs = load_eggs(csv_path)

    # Generate shop immediately using seed based on current rounded 5-min time
    seed = create_seed_from_secret_and_time(secret_key)
    rng = random.Random(seed)
    shop = weighted_choice_with_replacement(eggs, 5, rng)

    # Wait until next 5-minute mark before writing file
    wait_until_next_5min_mark()

    timestamp = datetime.now(timezone.utc).isoformat()

    output = {
        "generated_at": timestamp,
        "shop": shop
    }

    with open("shop.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Shop generated earlier, but shop.json updated at {timestamp}")

if __name__ == "__main__":
    main()
