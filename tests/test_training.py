from audit import read_csv
from train_models import (
    export_enriched_candidates,
    labeled_unique_texts,
    train_inference_models,
)


def test_training_uses_distinct_decisively_labeled_texts():
    rows = labeled_unique_texts()
    texts = [text.casefold() for text, _ in rows]
    assert len(texts) == len(set(texts))
    candidates = {row["dialogue_id"]: row for row in read_csv("06_candidates/candidates.csv")}
    uncertain = {
        candidates[row["dialogue_id"]]["text"].strip().casefold()
        for row in read_csv("07_manual_100/manual_annotations.csv")
        if row["annotation"] == "UNCERTAIN"
    }
    assert not set(texts) & uncertain


def test_enriched_export_keeps_all_candidates_and_source_names():
    path, count = export_enriched_candidates()
    rows = read_csv(str(path.relative_to(path.parent.parent)))
    assert count == 13500
    assert len(rows) == 13500
    assert all(row["source_name"] for row in rows)
    assert all(row["platform"] for row in rows)
    assert all(row["source_registry_status"] == "DECLARED_OSINT" for row in rows)


def test_streamlit_can_train_and_run_all_five_models():
    models = train_inference_models()
    assert len(models) == 5
    for pipeline in models.values():
        assert int(pipeline.predict(["Проверочный текст"])[0]) in {0, 1}
