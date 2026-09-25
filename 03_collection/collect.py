"""Validate a supplied JSONL export; no network scraping is performed."""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBTYPES = {
    "EXTREMIST_PROPAGANDA", "EXTREMIST_RECRUITMENT",
    "VIOLENCE_GLORIFICATION", "DANGEROUS_CHALLENGE",
    "SELF_HARM_ENCOURAGEMENT", "SUICIDE_ENCOURAGEMENT",
    "CRIMINAL_RECRUITMENT", "GROUP_LOYALTY_PRESSURE",
    "SECRET_COMMUNICATION_REQUEST",
}


def collect_data(input_path, output_path):
    with (ROOT / "02_sources/sources_approved.csv").open(
        encoding="utf-8", newline=""
    ) as source:
        approved = {
            row["source_id"] for row in csv.DictReader(source)
            if row["review_status"] == "APPROVED"
        }
    seen = set()
    records = []
    with Path(input_path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number}") from error
            identifier = row.get("dialogue_id")
            text = row.get("text")
            if not isinstance(identifier, str) or not identifier:
                raise ValueError(f"Missing dialogue_id on line {line_number}")
            if identifier in seen:
                raise ValueError(f"Duplicate dialogue_id: {identifier}")
            if row.get("source_id") not in approved:
                raise ValueError(f"Unapproved source on line {line_number}")
            if row.get("target_subtype") not in SUBTYPES:
                raise ValueError(f"Unknown subtype on line {line_number}")
            if row.get("language") not in {"RU", "KK", "MIXED"}:
                raise ValueError(f"Unknown language on line {line_number}")
            if not isinstance(text, str) or not text.strip() or text == "Raw dialogue":
                raise ValueError(f"Missing source text on line {line_number}")
            seen.add(identifier)
            records.append(row)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as out:
        for row in records:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(collect_data(arguments.input, arguments.output))
