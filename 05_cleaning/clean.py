"""Basic validation, exact-text deduplication and heuristic anonymization."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from anonymize import anonymize_text


def clean_records(records):
    seen_ids, seen_texts, result = set(), {}, []
    for row in records:
        identifier = row["dialogue_id"]
        text = row["text"].strip()
        if identifier in seen_ids:
            raise ValueError(f"Duplicate dialogue_id: {identifier}")
        seen_ids.add(identifier)
        if not text:
            continue
        safe_text = anonymize_text(text)
        key = safe_text.casefold()
        if key in seen_texts and seen_texts[key] != row["target_subtype"]:
            raise ValueError(f"Conflicting subtypes for repeated text: {identifier}")
        if key in seen_texts:
            continue
        seen_texts[key] = row["target_subtype"]
        result.append({
            "dialogue_id": identifier,
            "target_subtype": row["target_subtype"],
            "source_id": row["source_id"],
            "text": safe_text,
            "language": row["language"],
        })
    return result


def clean_file(input_path, output_path):
    with Path(input_path).open(encoding="utf-8") as source:
        records = [json.loads(line) for line in source if line.strip()]
    result = clean_records(records)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(
            out, fieldnames=["dialogue_id", "target_subtype", "source_id", "text", "language"]
        )
        writer.writeheader()
        writer.writerows(result)
    return len(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(clean_file(arguments.input, arguments.output))
