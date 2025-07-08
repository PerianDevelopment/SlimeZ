import csv
import json
import time
import hashlib
import random
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

# --- Configuration ---
SHOP_SIZE = 3
OUTPUT_FILENAME = "shop.json"
TIME_INTERVAL_MINUTES = 5

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# --- Data Structures ---
@dataclass(frozen=True)
class Egg:
    """Represents an egg with a name and pull chance."""
    name: str
    chance: float

@dataclass
class ShopState:
    """Represents the generated state of the shop."""
    generated_at: datetime
    current_shop: List[str]
    next_shop: List[str]

    def to_dict(self) -> dict:
        """Serializes the state to a dictionary for JSON output."""
        return {
            "generated_at": self.generated_at.isoformat().replace("+00:00", "Z"),
            "current_shop": self.current_shop,
            "next_shop": self.next_shop,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Optional['ShopState']:
        """Deserializes a dictionary into a ShopState object."""
        try:
            generated_at_str = data["generated_at"].replace("Z", "+00:00")
            return cls(
                generated_at=datetime.fromisoformat(generated_at_str),
                current_shop=data["current_shop"],
                next_shop=data["next_shop"],
            )
        except (KeyError, TypeError, ValueError) as e:
            logging.warning(f"Could not parse existing shop data: {e}")
            return None

# --- Core Logic Class ---
class ShopGenerator:
    """
    Handles the logic for deterministically generating shop inventories
    based on a secret key and time.
    """
    def __init__(self, secret_key: str, eggs: List[Egg]):
        if not eggs:
            raise ValueError("Egg list cannot be empty.")
        self.secret_key = secret_key
        self.eggs = eggs
        self.egg_names = [egg.name for egg in self.eggs]
        self.egg_weights = [egg.chance for egg in self.eggs]

    def _create_seed(self, dt: datetime) -> int:
        """Creates a deterministic integer seed from a secret key and timestamp."""
        time_str = dt.strftime("%Y-%m-%dT%H:%M")
        combined = f"{self.secret_key}:{time_str}".encode("utf-8")
        h = hashlib.sha256(combined).hexdigest()
        return int(h, 16)

    def _generate_shop_inventory(self, seed_dt: datetime) -> List[str]:
        """Generates a list of eggs for a specific time using a deterministic seed."""
        seed = self._create_seed(seed_dt)
        rng = random.Random(seed)
        # Use the highly optimized random.choices for weighted selection
        return rng.choices(self.egg_names, weights=self.egg_weights, k=SHOP_SIZE)

    def generate_shops_for_time(self, current_time_slot: datetime) -> ShopState:
        """Generates the current and next shop inventories."""
        logging.info(f"Generating new shops for time slot: {current_time_slot.isoformat()}")
        current_shop = self._generate_shop_inventory(current_time_slot)
        
        next_time_slot = current_time_slot + timedelta(minutes=TIME_INTERVAL_MINUTES)
        next_shop = self._generate_shop_inventory(next_time_slot)
        
        return ShopState(
            generated_at=current_time_slot,
            current_shop=current_shop,
            next_shop=next_shop
        )

# --- Helper & Utility Functions ---
def load_eggs_from_csv(csv_path: Path) -> List[Egg]:
    """Loads egg definitions from a CSV file."""
    eggs = []
    try:
        with csv_path.open(newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader, 1):
                try:
                    eggs.append(Egg(name=row["EggName"], chance=float(row["PullChance"])))
                except (KeyError, ValueError) as e:
                    logging.warning(f"Skipping malformed row {i} in {csv_path}: {e}")
        logging.info(f"Successfully loaded {len(eggs)} eggs from {csv_path}.")
        return eggs
    except FileNotFoundError:
        logging.critical(f"Error: Egg CSV file not found at {csv_path}")
        raise
    except Exception as e:
        logging.critical(f"An unexpected error occurred while reading {csv_path}: {e}")
        raise

def get_current_time_slot() -> datetime:
    """Rounds the current UTC time down to the nearest 5-minute interval."""
    now_utc = datetime.now(timezone.utc)
    return now_utc - timedelta(
        minutes=now_utc.minute % TIME_INTERVAL_MINUTES,
        seconds=now_utc.second,
        microseconds=now_utc.microsecond,
    )

def wait_for_next_interval(current_time_slot: datetime):
    """Waits precisely until the start of the next time interval."""
    next_interval_start = current_time_slot + timedelta(minutes=TIME_INTERVAL_MINUTES)
    now_utc = datetime.now(timezone.utc)
    wait_seconds = (next_interval_start - now_utc).total_seconds()

    if wait_seconds > 0:
        logging.info(
            f"Waiting {wait_seconds:.2f} seconds until the next interval at "
            f"{next_interval_start.isoformat()}"
        )
        time.sleep(wait_seconds)
    else:
        logging.info("Time slot has already passed; not waiting.")

# --- Main Execution ---
def main():
    """Main function to parse arguments and run the shop generation logic."""
    parser = argparse.ArgumentParser(
        description="Deterministically generate a game shop inventory.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("secret_key", help="The secret key for deterministic generation.")
    parser.add_argument("csv_path", type=Path, help="Path to the eggs CSV file.")
    parser.add_argument(
        "--output", type=Path, default=Path(OUTPUT_FILENAME), help="Path for the output JSON file."
    )
    args = parser.parse_args()

    try:
        eggs = load_eggs_from_csv(args.csv_path)
    except (FileNotFoundError, ValueError):
        return  # Exit if egg loading fails

    generator = ShopGenerator(args.secret_key, eggs)
    current_time_slot = get_current_time_slot()
    
    # Load previous state if it exists and is valid
    existing_state: Optional[ShopState] = None
    if args.output.exists():
        with args.output.open("r") as f:
            existing_state = ShopState.from_dict(json.load(f))

    # Determine the final state to be written
    if existing_state and existing_state.generated_at == current_time_slot:
        logging.info("Shop data is already up-to-date for the current time slot. No action needed.")
        final_state = existing_state
    else:
        final_state = generator.generate_shops_for_time(current_time_slot)

    # Wait until the precise moment to update the shop file
    wait_for_next_interval(current_time_slot)

    # Write the new shop data
    with args.output.open("w") as f:
        json.dump(final_state.to_dict(), f, indent=2)
    
    logging.info(f"Successfully wrote new shop data to {args.output}")
    logging.info(f"Current Shop: {final_state.current_shop}")
    logging.info(f"Next Shop: {final_state.next_shop}")

if __name__ == "__main__":
    main()
