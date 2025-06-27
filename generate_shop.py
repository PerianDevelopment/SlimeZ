import csv
import json
import sys
import hashlib
import random
from datetime import datetime, timezone

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

def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_shop.py <secret_key> <eggs.csv>")
        sys.exit(1)

    secret_key = sys.argv[1]
    csv_path = sys.argv[2]

    eggs = load_eggs(csv_path)
    seed = create_seed_from_secret_and_time(secret_key)
    rng = random.Random(seed)

    shop = weighted_choice_with_replacement(eggs, 5, rng)
    timestamp = datetime.now(timezone.utc).isoformat()

    output = {
        "generated_at": timestamp,
        "shop": shop
    }

    with open("shop.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Shop generated at {timestamp} and saved to shop.json")

if __name__ == "__main__":
    main()
