"""Create a deterministic proposed sample without rewriting annotated records."""
import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRENT = ROOT / "07_manual_100/manual_sample_100.csv"


def generate_sample(seed=42, output=None):
    destination = Path(output) if output else ROOT / "07_manual_100/manual_sample_candidate.csv"
    if destination.resolve() == CURRENT.resolve():
        raise ValueError("Refusing to overwrite the annotated sample")
    with (ROOT / "06_candidates/candidates.csv").open(encoding="utf-8", newline="") as src:
        candidates = list(csv.DictReader(src))
    grouped = defaultdict(list)
    for row in candidates:
        grouped[row["target_subtype"]].append(row)
    randomizer = random.Random(seed)
    sample = []
    for subtype in sorted(grouped):
        rows = sorted(grouped[subtype], key=lambda row: row["dialogue_id"])
        if len(rows) < 100:
            raise ValueError(f"Too few candidates for {subtype}")
        sample.extend(randomizer.sample(rows, 100))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=candidates[0].keys())
        writer.writeheader()
        writer.writerows(sample)
    return sample


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    generate_sample(args.seed, args.output)
