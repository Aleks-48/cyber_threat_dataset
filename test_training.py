from audit import read_csv
from train_models import labeled_unique_texts


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
