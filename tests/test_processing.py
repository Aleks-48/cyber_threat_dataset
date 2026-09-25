import json
import runpy
from pathlib import Path

import pytest

from audit import ROOT


def test_collector_rejects_placeholder_and_unapproved_source(tmp_path):
    collect = runpy.run_path(str(ROOT / "03_collection/collect.py"))["collect_data"]
    source, output = tmp_path / "input.jsonl", tmp_path / "output.jsonl"
    row = {
        "dialogue_id": "test-1", "target_subtype": "DANGEROUS_CHALLENGE",
        "source_id": "SRC_000001", "language": "RU", "text": "Raw dialogue",
    }
    source.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing source text"):
        collect(source, output)
    assert not output.exists()
    row["text"] = "Test text"
    row["source_id"] = "UNKNOWN"
    source.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unapproved source"):
        collect(source, output)


def test_cleaner_masks_pii_and_removes_exact_text_duplicates():
    clean = runpy.run_path(str(ROOT / "05_cleaning/clean.py"))["clean_records"]
    base = {
        "target_subtype": "DANGEROUS_CHALLENGE", "source_id": "SRC_000001",
        "language": "RU", "text": "Write to a@example.org or +7 777 123 45 67",
    }
    result = clean([{**base, "dialogue_id": "1"}, {**base, "dialogue_id": "2"}])
    assert len(result) == 1
    assert "[EMAIL]" in result[0]["text"]
    assert "[PHONE]" in result[0]["text"]
    assert "a@example.org" not in result[0]["text"]
    with pytest.raises(ValueError, match="Conflicting subtypes"):
        clean([
            {**base, "dialogue_id": "1"},
            {**base, "dialogue_id": "2", "target_subtype": "SUICIDE_ENCOURAGEMENT"},
        ])
