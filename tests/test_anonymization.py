import os
import csv
import re
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_pii_anonymization_strict():
    cand_path = os.path.join(ROOT_DIR, "06_candidates", "candidates.csv")
    
    with open(cand_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row["text"]
            # Check for phone numbers (+7...)
            assert not re.search(r'\+7[\s\-\(]*\d{3}', text), f"PII phone found in {row['dialogue_id']}"
            # Check for URL
            assert not re.search(r'https?://\S+', text), f"PII URL found in {row['dialogue_id']}"
            # Check for username
            assert not re.search(r'@\w+', text), f"PII username found in {row['dialogue_id']}"
