import os
import csv
import random
import argparse

def generate_sample(seed: int = 42):
    random.seed(seed)
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates_path = os.path.join(ROOT_DIR, "06_candidates", "candidates.csv")
    out_path = os.path.join(ROOT_DIR, "07_manual_100", "manual_sample_100.csv")
    
    # Read candidates
    candidates = []
    with open(candidates_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidates.append(row)
            
    # Subtypes
    subtypes = [
        "EXTREMIST_PROPAGANDA", "EXTREMIST_RECRUITMENT", "VIOLENCE_GLORIFICATION",
        "DANGEROUS_CHALLENGE", "SELF_HARM_ENCOURAGEMENT", "SUICIDE_ENCOURAGEMENT",
        "CRIMINAL_RECRUITMENT", "GROUP_LOYALTY_PRESSURE", "SECRET_COMMUNICATION_REQUEST"
    ]
    
    sample = []
    for st in subtypes:
        st_cands = [c for c in candidates if c["target_subtype"] == st]
        # sort to ensure reproducibility regardless of read order
        st_cands.sort(key=lambda x: x["dialogue_id"])
        if len(st_cands) >= 100:
            sample.extend(random.sample(st_cands, 100))
            
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        if candidates:
            writer = csv.DictWriter(f, fieldnames=candidates[0].keys())
            writer.writeheader()
            writer.writerows(sample)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate_sample(args.seed)
