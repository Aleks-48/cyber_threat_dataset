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
MODEL_INFO = {
    "Logistic Regression": {
        "description": "Линейная модель: оценивает вклад слов и словосочетаний.",
        "limitation": "Зависит от качества разметки и словаря; хуже переносится на новые формулировки.",
        "source": "https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html",
    },
    "Naive Bayes": {
        "description": "Вероятностный классификатор частот слов.",
        "limitation": "Предполагает условную независимость признаков и плохо учитывает контекст.",
        "source": "https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.MultinomialNB.html",
    },
    "Support Vector Machine (SVM)": {
        "description": "Линейная разделяющая граница для TF-IDF признаков.",
        "limitation": "Не понимает смысл текста без признаков, которых нет в обучении.",
        "source": "https://scikit-learn.org/stable/modules/generated/sklearn.svm.LinearSVC.html",
    },
    "Random Forest": {
        "description": "Ансамбль деревьев решений по текстовым признакам.",
        "limitation": "Разреженный высокоразмерный TF-IDF может ограничивать обобщение.",
        "source": "https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html",
    },
    "Neural Network (MLP)": {
        "description": "Небольшая нейросеть поверх TF-IDF признаков.",
        "limitation": "На маленькой разметке легко переобучается; это не большая языковая модель.",
        "source": "https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html",
    },
}


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
    candidates = read_csv("06_candidates/candidates.csv")
    prediction_rows = [
        {"dialogue_id": row["dialogue_id"], "source_id": row["source_id"]}
        for row in candidates
    ]
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
        all_predictions = pipeline.predict([row["text"] for row in candidates])
        for candidate_row, prediction in zip(prediction_rows, all_predictions):
            candidate_row[name] = int(prediction)
        results.append({
            "Model": name,
            "Accuracy": round(100 * accuracy_score(test_y, predictions), 2),
            "Precision": round(100 * precision_score(test_y, predictions, zero_division=0), 2),
            "Recall": round(100 * recall_score(test_y, predictions, zero_division=0), 2),
            "F1-Score": round(100 * f1_score(test_y, predictions, zero_division=0), 2),
        })
    results.sort(key=lambda row: (-row["F1-Score"], -row["Recall"], row["Model"]))
    for row in results:
        row["Оценка 0–5"] = round(row["F1-Score"] / 20, 2)
        row["Место"] = 1 + sum(
            other["F1-Score"] > row["F1-Score"] for other in results
        )
        row["Что делает"] = MODEL_INFO[row["Model"]]["description"]
        row["Ограничение"] = MODEL_INFO[row["Model"]]["limitation"]
        row["Открытый исходный код"] = MODEL_INFO[row["Model"]]["source"]
    OUTPUT.mkdir(exist_ok=True)
    with (OUTPUT / "model_metrics.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    with (OUTPUT / "model_predictions.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(prediction_rows[0]))
        writer.writeheader()
        writer.writerows(prediction_rows)
    report = audit()
    metadata = {
        "task": "Binary TARGET_THREAT vs OTHER_THREAT and NORMAL; UNCERTAIN excluded",
        "dataset_status": "DEMO_ONLY" if not report["next_stage_allowed"] else "AUDIT_PASSED",
        "unique_labeled_texts": len(rows),
        "training_texts": len(train_text),
        "test_texts": len(test_text),
        "analyzed_dataset_rows": len(prediction_rows),
        "prediction_label_1": "TARGET_THREAT (exploratory prediction, not a verified annotation)",
        "random_seed": SEED,
        "split": "Stratified holdout after exact-text deduplication",
        "rating_method": "0–5 = F1 percentage / 20; equal F1 scores share a place",
        "model_library": "scikit-learn (open source); models trained locally on this dataset",
        "interpretation": "Exploratory only; template similarity and failed audit prevent real-world ranking",
        "blocking_reasons": report["blocking_reasons"],
    }
    (OUTPUT / "evaluation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return results, metadata


if __name__ == "__main__":
    scores, info = train_and_evaluate()
    print(json.dumps({"results": scores, "metadata": info}, ensure_ascii=False, indent=2))
