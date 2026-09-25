"""Exploratory baselines on distinct annotated texts.

The current snapshot is a demo dataset. Scores do not estimate real-world
performance until provenance and diversity checks pass.
"""
import csv
import json
from collections import Counter
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.svm import LinearSVC

from audit import ROOT, audit, read_csv

OUTPUT = ROOT / "10_model_baselines"
SEED = 42


def labeled_unique_texts():
    candidates = {r["dialogue_id"]: r for r in read_csv("06_candidates/candidates.csv")}
    labels = read_csv("07_manual_100/manual_annotations.csv")
    unique = {}
    for row in labels:
        if row["annotation"] == "UNCERTAIN":
            continue
        candidate = candidates[row["dialogue_id"]]
        text = candidate["text"].strip()
        key = text.casefold()
        label = int(row["annotation"] == "TARGET_THREAT")
        if key in unique and unique[key][1] != label:
            raise ValueError(f"Conflicting labels for identical text: {row['dialogue_id']}")
        unique[key] = (text, label)
    return list(unique.values())


def train_and_evaluate():
    rows = labeled_unique_texts()
    texts = [text for text, _ in rows]
    labels = [label for _, label in rows]
    if len(rows) < 20 or min(Counter(labels).values()) < 5:
        raise ValueError("Not enough distinct labeled examples for a holdout")
    train_text, test_text, train_y, test_y = train_test_split(
        texts, labels, test_size=0.2, random_state=SEED, stratify=labels
    )
    assert not set(train_text) & set(test_text)
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=SEED),
        "Naive Bayes": MultinomialNB(),
        "Support Vector Machine (SVM)": LinearSVC(random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=SEED),
        "Neural Network (MLP)": MLPClassifier(
            hidden_layer_sizes=(32,), max_iter=300, random_state=SEED
        ),
    }
    results = []
    for name, estimator in models.items():
        pipeline = make_pipeline(
            TfidfVectorizer(max_features=1000, ngram_range=(1, 2)), estimator
        )
        pipeline.fit(train_text, train_y)
        predictions = pipeline.predict(test_text)
        results.append({
            "Model": name,
            "Accuracy": round(100 * accuracy_score(test_y, predictions), 2),
            "Precision": round(100 * precision_score(test_y, predictions, zero_division=0), 2),
            "Recall": round(100 * recall_score(test_y, predictions, zero_division=0), 2),
            "F1-Score": round(100 * f1_score(test_y, predictions, zero_division=0), 2),
        })
    results.sort(key=lambda row: row["F1-Score"], reverse=True)
    OUTPUT.mkdir(exist_ok=True)
    with (OUTPUT / "model_metrics.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    report = audit()
    metadata = {
        "task": "Binary TARGET_THREAT vs OTHER_THREAT and NORMAL; UNCERTAIN excluded",
        "dataset_status": "DEMO_ONLY" if not report["next_stage_allowed"] else "AUDIT_PASSED",
        "unique_labeled_texts": len(rows),
        "training_texts": len(train_text),
        "test_texts": len(test_text),
        "random_seed": SEED,
        "split": "Stratified holdout after exact-text deduplication",
        "blocking_reasons": report["blocking_reasons"],
    }
    (OUTPUT / "evaluation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return results, metadata


if __name__ == "__main__":
    scores, info = train_and_evaluate()
    print(json.dumps({"results": scores, "metadata": info}, ensure_ascii=False, indent=2))
