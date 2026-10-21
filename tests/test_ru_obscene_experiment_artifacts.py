import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "experiments" / "ru_obscene_ml"


def test_experiment_audit_and_metrics_are_complete():
    audit = json.loads((OUT / "audit.json").read_text(encoding="utf-8"))
    metrics = json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))
    assert audit["experiment_status"] == "COMPLETE_SEPARATE_TASK_NOT_HARMFUL_INFLUENCE"
    assert audit["usable_unique_rows_after_filters"] == sum(
        row["rows"] for row in audit["split_counts_by_labels"].values()
    )
    assert audit["near_duplicate_pairs_in_final_pool"] == 0
    assert audit["excluded_record_count"] == audit["raw_row_count"] - audit["usable_unique_rows_after_filters"]
    assert sum(audit["excluded_rows_by_reason"].values()) == audit["excluded_record_count"]
    assert audit["test_split_created_before_model_fitting"] is True
    assert audit["hyperparameter_tuning"].startswith("none;")
    assert set(metrics["models"]) == {
        "Logistic Regression", "MultinomialNB", "LinearSVC", "RandomForest", "MLP"
    }
    assert audit["prediction_file_contains_text"] is False


def test_public_tree_excludes_row_level_and_raw_data():
    assert not (OUT / "split_assignments.csv").exists()
    assert not (OUT / "predictions.csv").exists()
    assert not (OUT / "excluded_rows.csv").exists()
    assert not (OUT / "near_duplicate_pairs.csv").exists()
    assert not (ROOT / "analysis" / "external_sources" / "MCA_Russian_Toxic_Comments" / "raw").exists()

def test_confusion_matrices_match_supports_and_dashboard_is_text_free():
    metrics = json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))
    for model in metrics["models"].values():
        for split in ("validation", "test"):
            result = model[split]
            assert sum(map(sum, result["confusion_matrix"])) == result["n"]
            assert sum(v["support"] for v in result["class_metrics"].values()) == result["n"]
            assert all(0 <= v["f1"] <= 1 for v in result["class_metrics"].values())
    app = (ROOT / "app.py").read_text(encoding="utf-8").casefold()
    assert "download_button" not in app
    assert "raw/combined.csv" not in app
    assert "dataframe(" in app  # Aggregate tables only; no source-message loader is present.

