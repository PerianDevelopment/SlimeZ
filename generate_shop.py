import csv
import json
import sys
import hashlib
import random
import time
from datetime import datetime, timezone, timedelta
import os

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

def create_seed_from_secret_and_time(secret_key, dt):
    # dt is a datetime rounded to 5-min mark
    time_component = dt.strftime("%Y-%m-%dT%H:%M")
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

def round_down_to_5min(dt):
    return dt - timedelta(minutes=dt.minute % 5, seconds=dt.second, microseconds=dt.microsecond)

def wait_until_next_5min_mark():
    now = datetime.now(timezone.utc)
    next_minute = (now.minute - now.minute % 5) + 5
    if next_minute >= 60:
        next_hour = (now.hour + 1) % 24
        next_minute = 0
        next_time = now.replace(hour=next_hour, minute=next_minute, second=0, microsecond=0)
        if now.hour == 23:
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

    now = datetime.now(timezone.utc)
    now_5min = round_down_to_5min(now)

    # Attempt to load existing shop.json if exists
    existing_data = None
    if os.path.isfile("shop.json"):
        try:
            with open("shop.json", "r") as f:
                existing_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load existing shop.json: {e}")

    existing_generated_at = None
    existing_next_shop = None
    if existing_data:
        try:
            existing_generated_at = datetime.fromisoformat(existing_data.get("generated_at").replace("Z", "+00:00"))
            existing_next_shop = existing_data.get("next_shop")
        except Exception as e:
            print(f"Warning: Failed to parse existing generated_at or next_shop: {e}")

    if existing_generated_at and existing_next_shop:
        diff = now_5min - existing_generated_at
        if timedelta(0) <= diff < timedelta(minutes=5):
            print("Using existing next_shop as current_shop, generating new next_shop.")
            current_shop = existing_next_shop
            next_seed_time = now_5min + timedelta(minutes=5)
            next_seed = create_seed_from_secret_and_time(secret_key, next_seed_time)
            rng = random.Random(next_seed)
            next_shop = weighted_choice_with_replacement(eggs, 3, rng)
            generated_at = now_5min
        else:
            print("Existing shop is old or in the past, generating two new shops.")
            seed_current = create_seed_from_secret_and_time(secret_key, now_5min)
            rng_current = random.Random(seed_current)
            current_shop = weighted_choice_with_replacement(eggs, 3, rng_current)

            seed_next = create_seed_from_secret_and_time(secret_key, now_5min + timedelta(minutes=5))
            rng_next = random.Random(seed_next)
            next_shop = weighted_choice_with_replacement(eggs, 3, rng_next)

            generated_at = now_5min
    else:
        print("No existing shop found, generating two new shops.")
        seed_current = create_seed_from_secret_and_time(secret_key, now_5min)
        rng_current = random.Random(seed_current)
        current_shop = weighted_choice_with_replacement(eggs, 3, rng_current)

        seed_next = create_seed_from_secret_and_time(secret_key, now_5min + timedelta(minutes=5))
        rng_next = random.Random(seed_next)
        next_shop = weighted_choice_with_replacement(eggs, 3, rng_next)

        generated_at = now_5min

    # Wait until next 5-min mark before saving shop.json
    wait_until_next_5min_mark()

    output = {
        "generated_at": generated_at.isoformat() + "Z",
        "current_shop": current_shop,
        "next_shop": next_shop
    }

    with open("shop.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Shop generated at {generated_at.isoformat()}Z")
    print(f"Current shop: {current_shop}")
    print(f"Next shop: {next_shop}")

if __name__ == "__main__":
    main()
