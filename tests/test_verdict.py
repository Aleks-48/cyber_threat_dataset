import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from audit import ROOT, audit, config


def test_sample_reproducibility_without_overwriting_annotations(tmp_path):
    script = ROOT / "07_manual_100/create_sample.py"
    checked_in = ROOT / "07_manual_100/manual_sample_100.csv"
    before = hashlib.sha256(checked_in.read_bytes()).digest()
    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    for output in (first, second):
        subprocess.run(
            [sys.executable, str(script), "--seed", "42", "--output", str(output)],
            check=True,
        )
    assert first.read_bytes() == second.read_bytes()
    assert hashlib.sha256(checked_in.read_bytes()).digest() == before


def test_raw_data_hash_matches_recorded_snapshot():
    protocol = json.loads(
        (ROOT / "03_collection/collection_protocol.json").read_text(encoding="utf-8")
    )
    raw_hash = hashlib.sha256(
        (ROOT / "04_raw_data/raw_harvest_snapshot.jsonl").read_bytes()
    ).hexdigest()
    assert raw_hash == protocol["raw_data_hash"]


def test_audit_blocks_unsubstantiated_repeated_snapshot():
    report = audit()
    assert report["candidate_count"] == 13500
    assert report["unique_text_count"] == 297
    assert report["raw_matching_text_count"] == 0
    assert report["target_threat_rate"] == round(652 / 900, 4)
    assert not report["next_stage_allowed"]
    assert any("Raw snapshot" in reason for reason in report["blocking_reasons"])


def test_audit_uses_configured_threshold(monkeypatch):
    original = config()
    original["thresholds"]["target_threat_rate_min"] = 0.8
    monkeypatch.setattr("audit.config", lambda: original)
    assert "TARGET_THREAT rate below threshold" in audit()["blocking_reasons"]
