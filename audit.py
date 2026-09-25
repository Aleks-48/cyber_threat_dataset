"""Checks for the checked-in Theme 8 snapshot."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBTYPES = (
    "EXTREMIST_PROPAGANDA", "EXTREMIST_RECRUITMENT", "VIOLENCE_GLORIFICATION",
    "DANGEROUS_CHALLENGE", "SELF_HARM_ENCOURAGEMENT", "SUICIDE_ENCOURAGEMENT",
    "CRIMINAL_RECRUITMENT", "GROUP_LOYALTY_PRESSURE", "SECRET_COMMUNICATION_REQUEST",
)
LABELS = {"TARGET_THREAT", "OTHER_THREAT", "NORMAL", "UNCERTAIN"}


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def config():
    """Read the simple scalar mappings used in config.yaml without extra dependencies."""
    result, parent = {}, None
    for original in (ROOT / "config.yaml").read_text(encoding="utf-8").splitlines():
        line = original.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        key, value = line.strip().split(":", 1)
        if line.startswith("  "):
            result[parent][key] = float(value) if "." in value else int(value)
        elif value.strip():
            result[key] = float(value) if "." in value else int(value)
            parent = None
        else:
            result[key], parent = {}, key
    return result


def audit():
    cfg = config()
    candidates = read_csv("06_candidates/candidates.csv")
    sample = read_csv("07_manual_100/manual_sample_100.csv")
    annotations = read_csv("07_manual_100/manual_annotations.csv")
    keywords = read_csv("01_keywords/keywords_approved.csv")
    sources = read_csv("02_sources/sources_approved.csv")
    reasons = []

    def check(ok, reason):
        if not ok:
            reasons.append(reason)

    ids = [r["dialogue_id"] for r in candidates]
    by_id = {r["dialogue_id"]: r for r in candidates}
    sample_ids = [r["dialogue_id"] for r in sample]
    annotation_ids = [r["dialogue_id"] for r in annotations]
    source_ids = {r["source_id"] for r in sources if r["review_status"] == "APPROVED"}
    approved_keywords = [r for r in keywords if r["review_status"] == "APPROVED"]
    check(len(ids) == len(set(ids)), "Duplicate candidate IDs")
    check(len(sample_ids) == len(set(sample_ids)), "Duplicate sample IDs")
    check(len(annotation_ids) == len(set(annotation_ids)), "Duplicate annotation IDs")
    check(set(sample_ids) == set(annotation_ids), "Sample and annotations differ")
    check(all(r["source_id"] in source_ids for r in candidates),
          "Candidates reference unapproved sources")
    check(all(r["annotation"] in LABELS for r in annotations), "Unknown annotations")
    check(all(r["dialogue_id"] in by_id and
              r["target_subtype"] == by_id[r["dialogue_id"]]["target_subtype"]
              for r in annotations), "Annotation subtype mismatch")
    check(all(r["dialogue_id"] in by_id and
              r["text"] == by_id[r["dialogue_id"]]["text"] for r in sample),
          "Sample text differs from candidates")

    subtype_counts = Counter(r["target_subtype"] for r in candidates)
    sample_counts = Counter(r["target_subtype"] for r in sample)
    unique_by_subtype = {s: len({r["text"].strip().casefold()
                                 for r in candidates if r["target_subtype"] == s})
                         for s in SUBTYPES}
    for subtype in SUBTYPES:
        check(subtype_counts[subtype] >= cfg["quotas"]["min_candidates_per_subtype"],
              f"Candidate quota not reached: {subtype}")
        check(sample_counts[subtype] == cfg["quotas"]["manual_sample_size"],
              f"Sample quota not reached: {subtype}")
        check(unique_by_subtype[subtype] >=
              cfg["thresholds"]["min_unique_texts_per_subtype"],
              f"Too few unique texts: {subtype}")
        for language in ("RU", "KK"):
            check(any(r["target_subtype"] == subtype and r["language"] == language
                      for r in approved_keywords),
                  f"Missing approved {language} keyword: {subtype}")

    labels = Counter(r["annotation"] for r in annotations)
    total = len(annotations)
    target_rate = labels["TARGET_THREAT"] / total if total else 0
    uncertain_rate = labels["UNCERTAIN"] / total if total else 1
    check(target_rate >= cfg["thresholds"]["target_threat_rate_min"],
          "TARGET_THREAT rate below threshold")
    check(uncertain_rate <= cfg["thresholds"]["uncertain_rate_max"],
          "UNCERTAIN rate above threshold")
    unique_texts = len({r["text"].strip().casefold() for r in candidates})
    duplicate_rate = 1 - unique_texts / len(candidates) if candidates else 1
    check(duplicate_rate <= cfg["thresholds"]["duplicate_rate_max"],
          "Duplicate text rate above threshold")

    protocol = json.loads(
        (ROOT / "03_collection/collection_protocol.json").read_text(encoding="utf-8")
    )
    for name, key in (
        ("04_raw_data/raw_harvest_snapshot.jsonl", "raw_data_hash"),
        ("01_keywords/keywords_approved.csv", "keywords_hash"),
        ("02_sources/sources_approved.csv", "sources_hash"),
    ):
        digest = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        check(digest == protocol.get(key), f"Missing or incorrect {key}")
    raw_text = {}
    with (ROOT / "04_raw_data/raw_harvest_snapshot.jsonl").open(encoding="utf-8") as src:
        for line in src:
            row = json.loads(line)
            raw_text[row["dialogue_id"]] = row.get("text", "")
    raw_matches = sum(raw_text.get(r["dialogue_id"]) == r["text"]
                      for r in candidates)
    check(raw_matches == len(candidates),
          "Raw snapshot does not substantiate candidate text")
    languages = defaultdict(set)
    for row in candidates:
        languages[row["text"].strip().casefold()].add(row["language"])
    language_conflicts = sum(len(value) > 1 for value in languages.values())
    check(language_conflicts == 0, "Identical texts have conflicting language labels")
    return {
        "approved_keywords": len(approved_keywords),
        "approved_sources": len(source_ids),
        "candidate_count": len(candidates),
        "candidate_counts_by_subtype": dict(subtype_counts),
        "unique_text_count": unique_texts,
        "unique_texts_by_subtype": unique_by_subtype,
        "duplicate_text_rate": round(duplicate_rate, 4),
        "sample_count": len(sample),
        "annotation_count": total,
        "annotation_counts": dict(labels),
        "target_threat_rate": round(target_rate, 4),
        "uncertain_rate": round(uncertain_rate, 4),
        "raw_matching_text_count": raw_matches,
        "inconsistent_language_texts": language_conflicts,
        "next_stage_allowed": not reasons,
        "blocking_reasons": reasons,
    }


def save_report(report):
    (ROOT / "09_verdict/stage_verdict.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    report = audit()
    save_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
