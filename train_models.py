"""Exploratory baselines on distinct annotated texts.

The current snapshot is a demo dataset. Scores do not estimate real-world
performance until provenance and diversity checks pass.
"""
import csv
import json
import time
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

MODEL_CHARACTERISTICS = {
    "Logistic Regression": (
        "Быстрая линейная модель с понятными весами признаков",
        "Прозрачный baseline и быстрый массовый анализ",
        "Слабо учитывает сложные нелинейные связи",
    ),
    "Naive Bayes": (
        "Очень быстрый вероятностный классификатор текста",
        "Дешёвый первичный фильтр больших потоков",
        "Предполагает независимость признаков и хуже понимает контекст",
    ),
    "Support Vector Machine (SVM)": (
        "Сильная линейная модель для разреженных текстовых признаков",
        "Точный классический baseline на текстах",
        "Не выдаёт вероятность без дополнительной калибровки",
    ),
    "Random Forest": (
        "Ансамбль деревьев с нелинейными решениями",
        "Смешанные табличные и текстовые признаки",
        "Тяжелее и менее естественен для разреженного TF-IDF",
    ),
    "Neural Network (MLP)": (
        "Нейросеть для нелинейных зависимостей",
        "Эксперименты после накопления разнообразных данных",
        "Требует больше данных и вычислений, сложнее объясняется",
    ),
}


def model_estimators():
    """Return fresh instances of all five baseline estimators."""
    return {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=SEED),
        "Naive Bayes": MultinomialNB(),
        "Support Vector Machine (SVM)": LinearSVC(random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=SEED),
        "Neural Network (MLP)": MLPClassifier(
            hidden_layer_sizes=(32,), max_iter=300, random_state=SEED
        ),
    }


def train_inference_models():
    """Fit all baselines on every distinct decisively labelled example.

    This is used by the Streamlit demo for interactive predictions. Evaluation
    continues to use a separate holdout split in ``train_and_evaluate``.
    """
    rows = labeled_unique_texts()
    texts = [text for text, _ in rows]
    labels = [label for _, label in rows]
    fitted = {}
    for name, estimator in model_estimators().items():
        pipeline = make_pipeline(
            TfidfVectorizer(max_features=1000, ngram_range=(1, 2)), estimator
        )
        pipeline.fit(texts, labels)
        fitted[name] = pipeline
    return fitted


def export_enriched_candidates():
    """Join all 13,500 candidates to their declared open-source registry rows."""
    candidates = read_csv("06_candidates/candidates.csv")
    sources = {
        row["source_id"]: row for row in read_csv("02_sources/sources_approved.csv")
    }
    output_path = ROOT / "06_candidates/candidates_with_sources.csv"
    fields = [
        "dialogue_id", "target_subtype", "source_id", "source_name",
        "platform", "source_url", "source_description", "source_registry_status",
        "text", "language",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for candidate in candidates:
            source = sources[candidate["source_id"]]
            writer.writerow({
                **candidate,
                "source_name": source["source_name"],
                "platform": source["platform"],
                "source_url": source["url"],
                "source_description": source["description"],
                "source_registry_status": "DECLARED_OSINT",
            })
    return output_path, len(candidates)


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
    models = model_estimators()
    results = []
    for name, estimator in models.items():
        pipeline = make_pipeline(
            TfidfVectorizer(max_features=1000, ngram_range=(1, 2)), estimator
        )
        fit_started = time.perf_counter()
        pipeline.fit(train_text, train_y)
        fit_seconds = time.perf_counter() - fit_started
        predict_started = time.perf_counter()
        predictions = pipeline.predict(test_text)
        predict_seconds = time.perf_counter() - predict_started
        characteristic, best_for, limitation = MODEL_CHARACTERISTICS[name]
        results.append({
            "Model": name,
            "Accuracy": round(100 * accuracy_score(test_y, predictions), 2),
            "Precision": round(100 * precision_score(test_y, predictions, zero_division=0), 2),
            "Recall": round(100 * recall_score(test_y, predictions, zero_division=0), 2),
            "F1-Score": round(100 * f1_score(test_y, predictions, zero_division=0), 2),
            "Fit-Seconds": round(fit_seconds, 4),
            "Predict-ms-per-1000": round(
                1000 * predict_seconds / len(test_text) * 1000, 2
            ),
            "Characteristic": characteristic,
            "Best-For": best_for,
            "Limitation": limitation,
        })
    results.sort(key=lambda row: (
        -row["F1-Score"], -row["Accuracy"], -row["Recall"],
        row["Predict-ms-per-1000"], row["Fit-Seconds"],
    ))
    for rank, result in enumerate(results, 1):
        result["Rank"] = rank
        result["Ranking-Basis"] = (
            "F1, Accuracy, Recall, затем скорость предсказания и обучения"
        )
    result_fields = [
        "Rank", "Model", "Accuracy", "Precision", "Recall", "F1-Score",
        "Fit-Seconds", "Predict-ms-per-1000", "Characteristic", "Best-For",
        "Limitation", "Ranking-Basis",
    ]
    OUTPUT.mkdir(exist_ok=True)
    with (OUTPUT / "model_metrics.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=result_fields)
        writer.writeheader()
        writer.writerows(results)
    enriched_path, enriched_count = export_enriched_candidates()
    report = audit()
    metadata = {
        "task": "Binary TARGET_THREAT vs OTHER_THREAT and NORMAL; UNCERTAIN excluded",
        "dataset_status": "DEMO_ONLY" if not report["next_stage_allowed"] else "AUDIT_PASSED",
        "unique_labeled_texts": len(rows),
        "training_texts": len(train_text),
        "test_texts": len(test_text),
        "random_seed": SEED,
        "split": "Stratified holdout after exact-text deduplication",
        "ranking_basis": "F1, Accuracy, Recall, prediction speed, training speed",
        "enriched_candidate_file": str(enriched_path.relative_to(ROOT)),
        "enriched_candidate_count": enriched_count,
        "source_registry_note": (
            "Channel names and URLs come from sources_approved.csv. "
            "DECLARED_OSINT means listed as open, not independently verified."
        ),
        "blocking_reasons": report["blocking_reasons"],
    }
    (OUTPUT / "evaluation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return results, metadata


if __name__ == "__main__":
    scores, info = train_and_evaluate()
    print(json.dumps({"results": scores, "metadata": info}, ensure_ascii=False, indent=2))
