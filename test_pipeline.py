import os
import csv
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_approved_keywords_coverage():
    kw_path = os.path.join(ROOT_DIR, "01_keywords", "keywords_approved.csv")
    subtypes = set([
        "EXTREMIST_PROPAGANDA", "EXTREMIST_RECRUITMENT", "VIOLENCE_GLORIFICATION",
        "DANGEROUS_CHALLENGE", "SELF_HARM_ENCOURAGEMENT", "SUICIDE_ENCOURAGEMENT",
        "CRIMINAL_RECRUITMENT", "GROUP_LOYALTY_PRESSURE", "SECRET_COMMUNICATION_REQUEST"
    ])
    
    coverage = {st: {"RU": 0, "KK": 0} for st in subtypes}
    
    with open(kw_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["review_status"] == "APPROVED" and row["target_subtype"] in coverage:
                lang = row["language"]
                if lang in coverage[row["target_subtype"]]:
                    coverage[row["target_subtype"]][lang] += 1
                    
    for st in subtypes:
        assert coverage[st]["RU"] >= 1, f"Missing RU keyword for {st}"
        assert coverage[st]["KK"] >= 1, f"Missing KK keyword for {st}"

def test_unique_dialogue_ids():
    cand_path = os.path.join(ROOT_DIR, "06_candidates", "candidates.csv")
    ids = []
    with open(cand_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.append(row["dialogue_id"])
    
    assert len(ids) == len(set(ids)), "Duplicate dialogue_ids found in candidates.csv"

def test_source_referential_integrity():
    cand_path = os.path.join(ROOT_DIR, "06_candidates", "candidates.csv")
    src_path = os.path.join(ROOT_DIR, "02_sources", "sources_approved.csv")
    
    approved_sources = set()
    with open(src_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["review_status"] == "APPROVED":
                approved_sources.add(row["source_id"])
                
    with open(cand_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assert row["source_id"] in approved_sources, f"Source ID {row['source_id']} not in approved sources"
