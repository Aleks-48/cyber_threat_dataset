"""Train five fixed sklearn baselines on Mendeley Russian obscene-language labels.

The experiment predicts only the dataset's original `decent`/`obscene` label.
It does not model general toxicity, harmful influence, or any target subtype.
Raw text is read locally and never written to predictions or dashboard artifacts.
"""
from __future__ import annotations
import csv, hashlib, io, json, re, time, unicodedata, warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "analysis" / "external_sources" / "MCA_Russian_Toxic_Comments" / "raw" / "combined.csv"
OUT = ROOT / "analysis" / "experiments" / "ru_obscene_ml"
SOURCE_SHA256 = "6636a1195a683407e6ce6734430e0713d2b71b6b391a18490e7c1c9c68575b53"
SOURCE_BYTES = 1_579_284
DOI = "10.17632/fktgy52645.1"
DATASET_URL = "https://data.mendeley.com/datasets/fktgy52645/1"
LICENSE = "CC BY 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
SEED = 42
CLASSES = ("decent", "obscene")
NEAR_THRESHOLD = 0.90

PII_PATTERNS = {
    "email": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "url": re.compile(r"(?i)\b(?:https?://|www\.)\S+"),
    "phone_like": re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"),
    "public_handle": re.compile(r"(?<!\w)@[A-Za-z0-9_]{2,}"),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def source_group_hash(source: str, record_id: str) -> str:
    key = source.strip() or f"missing-source:{record_id}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


def load_raw() -> tuple[list[dict[str, str]], str]:
    payload = RAW.read_bytes()
    if len(payload) != SOURCE_BYTES or sha256_bytes(payload) != SOURCE_SHA256:
        raise ValueError("Mendeley raw file size/SHA-256 does not match public file metadata")
    decoded = payload.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(decoded, newline="")))
    required = {"source", "message", "decent", "moral", "person"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Unexpected CSV schema; columns={list(rows[0]) if rows else []}")
    return rows, sha256_bytes(payload)


def classify_near_duplicates(items: list[dict[str, str]]):
    texts = [row["text"] for row in items]
    matrix = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=2,
                             max_features=100_000, sublinear_tf=True).fit_transform(texts)
    neighbor_count = min(6, len(items))
    distances, indices = __import__("sklearn.neighbors", fromlist=["NearestNeighbors"]).NearestNeighbors(
        metric="cosine", algorithm="brute", n_neighbors=neighbor_count, n_jobs=-1
    ).fit(matrix).kneighbors(matrix)
    parent = list(range(len(items)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    pairs = {}
    for i, (ds, js) in enumerate(zip(distances, indices)):
        for distance, j in zip(ds, js):
            j = int(j)
            similarity = 1.0 - float(distance)
            if j == i or similarity < NEAR_THRESHOLD:
                continue
            a, b = sorted((i, j))
            pairs[(a, b)] = max(pairs.get((a, b), 0.0), similarity)
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
    groups = defaultdict(list)
    for i in range(len(items)):
        groups[find(i)].append(i)
    return groups, pairs


def choose_group_split(y, groups):
    y = np.asarray(y)
    groups = np.asarray(groups)
    candidates = []
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    for trainval_i, test_i in outer.split(np.zeros(len(y)), y, groups):
        if set(y[test_i]) != set(CLASSES) or set(y[trainval_i]) != set(CLASSES):
            continue
        frac = len(test_i) / len(y)
        if not 0.12 <= frac <= 0.30:
            continue
        candidates.append((abs(frac - 0.20), trainval_i, test_i))
    if not candidates:
        raise ValueError("Cannot make grouped test split with both original classes")
    _, trainval_i, test_i = min(candidates, key=lambda x: x[0])

    local_y = y[trainval_i]
    local_groups = groups[trainval_i]
    candidates = []
    inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=SEED + 1)
    for train_i, val_i in inner.split(np.zeros(len(local_y)), local_y, local_groups):
        if set(local_y[val_i]) != set(CLASSES) or set(local_y[train_i]) != set(CLASSES):
            continue
        frac = len(val_i) / len(trainval_i)
        if not 0.10 <= frac <= 0.30:
            continue
        candidates.append((abs(frac - 0.1875), train_i, val_i))
    if not candidates:
        raise ValueError("Cannot make grouped validation split with both original classes")
    _, train_local, val_local = min(candidates, key=lambda x: x[0])
    train_i = trainval_i[train_local]
    val_i = trainval_i[val_local]
    if set(groups[train_i]) & set(groups[val_i]) or set(groups[train_i]) & set(groups[test_i]) or set(groups[val_i]) & set(groups[test_i]):
        raise AssertionError("Source post groups leaked across train/validation/test")
    return list(train_i), list(val_i), list(test_i)


def score_split(y_true, y_pred):
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASSES, zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES)
    return {
        "n": len(y_true),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(np.mean(precision)),
        "recall_macro": float(np.mean(recall)),
        "f1_macro": float(f1_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)),
        "class_metrics": {
            label: {"precision": float(precision[i]), "recall": float(recall[i]),
                    "f1": float(f1[i]), "support": int(support[i])}
            for i, label in enumerate(CLASSES)
        },
        "confusion_matrix_labels_order": list(CLASSES),
        "confusion_matrix": cm.astype(int).tolist(),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    wall_start = time.perf_counter()
    raw_rows, raw_hash = load_raw()
    raw_label_counts = Counter((r.get("decent") or "").strip() for r in raw_rows)
    exclusions = []
    pii_flag_counts = Counter()
    eligible = []
    for i, row in enumerate(raw_rows):
        record_id = (row.get("") or str(i)).strip()
        text = (row.get("message") or "").strip()
        label = (row.get("decent") or "").strip()
        source = (row.get("source") or "").strip()
        if not text:
            exclusions.append({"record_id": record_id, "reason": "empty_message", "text_sha256": ""})
            continue
        if label not in CLASSES:
            exclusions.append({"record_id": record_id, "reason": "unmarked_or_out_of_scope_original_label", "text_sha256": hashlib.sha256(norm(text).encode()).hexdigest()})
            continue
        flags = [name for name, pattern in PII_PATTERNS.items() if pattern.search(text)]
        if flags:
            for flag in flags:
                pii_flag_counts[flag] += 1
            exclusions.append({"record_id": record_id, "reason": "direct_identifier_pattern:" + ";".join(flags), "text_sha256": hashlib.sha256(norm(text).encode()).hexdigest()})
            continue
        ntext = norm(text)
        if not ntext:
            exclusions.append({"record_id": record_id, "reason": "empty_after_normalization", "text_sha256": ""})
            continue
        eligible.append({
            "record_id": record_id, "text": text, "normalized_text": ntext,
            "original_label": label, "source_group_hash": source_group_hash(source, record_id),
            "text_sha256": hashlib.sha256(ntext.encode("utf-8")).hexdigest(),
        })

    # Exact dedup uses normalized original `message` only, never the class label.
    by_text = defaultdict(list)
    for row in eligible:
        by_text[row["normalized_text"]].append(row)
    exact_duplicate_text_groups = 0
    exact_duplicate_rows_removed = 0
    exact_conflict_groups = 0
    deduped = []
    for rows in by_text.values():
        labels = {row["original_label"] for row in rows}
        if len(rows) > 1:
            exact_duplicate_text_groups += 1
            exact_duplicate_rows_removed += len(rows) - 1
        if len(labels) > 1:
            exact_conflict_groups += 1
            for row in rows:
                exclusions.append({"record_id": row["record_id"], "reason": "exact_text_conflicting_original_label", "text_sha256": row["text_sha256"]})
            continue
        keep = min(rows, key=lambda row: (row["text_sha256"], row["record_id"]))
        deduped.append(keep)
        for row in rows:
            if row is not keep:
                exclusions.append({"record_id": row["record_id"], "reason": "exact_duplicate_text_only", "text_sha256": row["text_sha256"]})

    final = list(deduped)
    near_conflict_groups = 0
    near_removed = 0
    near_rounds = 0
    near_pairs_initial = 0
    near_pair_records = []
    while True:
        near_groups, near_pairs = classify_near_duplicates(final)
        if near_rounds == 0:
            near_pairs_initial = len(near_pairs)
        if not near_pairs:
            break
        near_rounds += 1
        if near_rounds > 10:
            raise RuntimeError("Near-duplicate filtering did not converge after 10 rounds")
        for (a, b), similarity in sorted(near_pairs.items()):
            left, right = final[a], final[b]
            near_pair_records.append({
                "left_record_id": left["record_id"],
                "right_record_id": right["record_id"],
                "similarity": f"{similarity:.6f}",
                "same_source_group": left["source_group_hash"] == right["source_group_hash"],
                "round": near_rounds,
            })
        remove_indices = set()
        remove_reason = {}
        for members in near_groups.values():
            if len(members) < 2:
                continue
            member_labels = {final[i]["original_label"] for i in members}
            if len(member_labels) > 1:
                near_conflict_groups += 1
                chosen = set()
                reason = "near_duplicate_label_conflict_group_removed"
            else:
                chosen = {min(members, key=lambda i: (final[i]["text_sha256"], final[i]["record_id"]))}
                reason = "near_duplicate_group_representative_only"
            for i in members:
                if i not in chosen:
                    remove_indices.add(i)
                    remove_reason[i] = reason
        if not remove_indices:
            raise RuntimeError("Near-duplicate pairs found, but no rows selected for removal")
        near_removed += len(remove_indices)
        for i in sorted(remove_indices):
            row = final[i]
            exclusions.append({"record_id": row["record_id"], "reason": remove_reason[i], "text_sha256": row["text_sha256"]})
        final = [row for i, row in enumerate(final) if i not in remove_indices]
    if classify_near_duplicates(final)[1]:
        raise AssertionError("Near-duplicate pairs remain after filtering")
    if len({row["normalized_text"] for row in final}) != len(final):
        raise AssertionError("Exact duplicate texts remain")

    y = [row["original_label"] for row in final]
    source_groups = [row["source_group_hash"] for row in final]
    if set(y) != set(CLASSES):
        raise ValueError(f"Expected both original labels after cleaning; got {Counter(y)}")
    train_i, val_i, test_i = choose_group_split(y, source_groups)
    split_by_i = {i: "train" for i in train_i}
    split_by_i.update({i: "validation" for i in val_i})
    split_by_i.update({i: "test" for i in test_i})
    split_counts = {name: {"rows": sum(split_by_i[i] == name for i in range(len(final))),
                           "labels": dict(Counter(y[i] for i in range(len(final)) if split_by_i[i] == name)),
                           "source_groups": len({source_groups[i] for i in range(len(final)) if split_by_i[i] == name})}
                    for name in ("train", "validation", "test")}

    # All settings below are fixed in source before reading validation/test scores; no tuning is run.
    (OUT / "models").mkdir(parents=True, exist_ok=True)
    model_specs = {
        "Logistic Regression": (LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
                                {"max_iter": 1000, "class_weight": "balanced", "random_state": SEED}),
        "MultinomialNB": (MultinomialNB(alpha=1.0), {"alpha": 1.0}),
        "LinearSVC": (LinearSVC(C=1.0, class_weight="balanced", random_state=SEED),
                      {"C": 1.0, "class_weight": "balanced", "random_state": SEED}),
        "RandomForest": (RandomForestClassifier(n_estimators=200, min_samples_leaf=2,
                                                  class_weight="balanced_subsample", n_jobs=1, random_state=SEED),
                         {"n_estimators": 200, "min_samples_leaf": 2, "class_weight": "balanced_subsample", "n_jobs": 1, "random_state": SEED}),
        "MLP": (MLPClassifier(hidden_layer_sizes=(64,), alpha=1e-4, max_iter=250,
                               early_stopping=True, validation_fraction=0.1, n_iter_no_change=20,
                               random_state=SEED),
                {"hidden_layer_sizes": [64], "alpha": 1e-4, "max_iter": 250,
                 "early_stopping": True, "validation_fraction": 0.1, "n_iter_no_change": 20,
                 "random_state": SEED}),
    }
    vectorizer_config = {"class": "TfidfVectorizer", "ngram_range": [1, 2], "min_df": 2,
                         "max_features": 15000, "sublinear_tf": True}
    texts = [row["text"] for row in final]
    metrics = {"experiment": "ru_obscene_language_original_decent_vs_obscene",
               "class_order": list(CLASSES), "models": {}}
    predictions = []
    warning_messages = []
    model_seconds = {}
    train_texts = [texts[i] for i in train_i]
    train_labels = [y[i] for i in train_i]
    for name, (estimator, params) in model_specs.items():
        t0 = time.perf_counter()
        pipeline = make_pipeline(TfidfVectorizer(ngram_range=(1,2), min_df=2,
                                                 max_features=15000, sublinear_tf=True), estimator)
        with warnings.catch_warnings(record=True) as seen_warnings:
            warnings.simplefilter("always")
            pipeline.fit(train_texts, train_labels)
        warning_messages.extend(f"{name}: {str(w.message)}" for w in seen_warnings)
        scores = {"validation": {}, "test": {}}
        for split_name, indexes in (("validation", val_i), ("test", test_i)):
            y_true = [y[i] for i in indexes]
            pred = pipeline.predict([texts[i] for i in indexes]).tolist()
            scores[split_name] = score_split(y_true, pred)
            for i, predicted in zip(indexes, pred):
                predictions.append({"record_id": final[i]["record_id"], "source_group_hash": source_groups[i],
                                   "split": split_name, "model": name,
                                   "original_label": y[i], "prediction": predicted})
        model_seconds[name] = round(time.perf_counter() - t0, 4)
        metrics["models"][name] = {"parameters": params, "fit_predict_seconds": model_seconds[name], **scores}
        joblib.dump(pipeline, OUT / "models" / f"{name.lower().replace(' ', '_')}.joblib")

    # Writes contain IDs, labels, hashes and aggregate metrics, never raw message text or VK URLs.
    with (OUT / "predictions.csv").open("w", encoding="utf-8", newline="") as f:
        fields = list(predictions[0]) if predictions else ["record_id", "source_group_hash", "split", "model", "original_label", "prediction"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(predictions)
    split_rows = [{"record_id": row["record_id"], "source_group_hash": row["source_group_hash"],
                   "split": split_by_i[i], "original_label": row["original_label"],
                   "normalized_text_sha256": row["text_sha256"]}
                  for i, row in enumerate(final)]
    with (OUT / "split_assignments.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(split_rows[0])); w.writeheader(); w.writerows(split_rows)
    with (OUT / "excluded_rows.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["record_id", "reason", "text_sha256"]); w.writeheader(); w.writerows(exclusions)
    with (OUT / "near_duplicate_pairs.csv").open("w", encoding="utf-8", newline="") as f:
        fields = ["left_record_id", "right_record_id", "similarity", "same_source_group", "round"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(near_pair_records)
    (OUT / "metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    finished = datetime.now(timezone.utc)
    exclusion_reason_counts = Counter(entry["reason"].split(":", 1)[0] for entry in exclusions)
    audit = {
        "experiment_status":"COMPLETE_SEPARATE_TASK_NOT_HARMFUL_INFLUENCE",
        "task":"binary prediction of the source's original decent/obscene label; narrower than general toxicity",
        "dataset_title":"MCA Workshop - Toxic comments",
        "dataset_doi":DOI,
        "dataset_url":DATASET_URL,
        "license":LICENSE,
        "license_url":LICENSE_URL,
        "raw_file_sha256":raw_hash,
        "raw_file_bytes":SOURCE_BYTES,
        "raw_row_count":len(raw_rows),
        "raw_original_decent_label_counts":dict(raw_label_counts),
        "model_input_field":"message",
        "original_label_field":"decent",
        "original_class_names":{"decent":"decent (source label)","obscene":"obscene (source label; positive class for interpretation only)"},
        "original_other_annotation_fields_preserved_in_raw_only":["moral","person","sex","text","source"],
        "exact_dedup_key":"NFKC(casefold(original message), whitespace-collapsed) only; original label is not part of the key",
        "exact_duplicate_text_groups":exact_duplicate_text_groups,
        "exact_duplicate_rows_removed":exact_duplicate_rows_removed,
        "exact_text_label_conflict_groups_removed":exact_conflict_groups,
        "near_duplicate_method":"char TF-IDF 3-5 grams, nearest five neighbors, cosine >= 0.90; connected components removed to one representative; groups with original-label conflict excluded",
        "near_duplicate_threshold":NEAR_THRESHOLD,
        "near_duplicate_pair_count_detected_initial":near_pairs_initial,
        "near_duplicate_pair_occurrences_seen_across_rounds":len(near_pair_records),
        "near_duplicate_removal_rounds":near_rounds,
        "near_duplicate_rows_removed":near_removed,
        "near_duplicate_pairs_in_final_pool":0,
        "near_duplicate_conflict_groups_removed":near_conflict_groups,
        "direct_identifier_filter":"regex screen on message text for email, URL, phone-like string, and @handle; not full anonymization",
        "direct_identifier_pattern_counts":dict(pii_flag_counts),
        "excluded_record_count":len(exclusions),
        "excluded_rows_by_reason":dict(exclusion_reason_counts),
        "usable_unique_rows_after_filters":len(final),
        "original_label_counts_after_filters":dict(Counter(y)),
        "split_counts_by_labels":split_counts,
        "split_method":"two-stage StratifiedGroupKFold; source post URLs are groups, no post group crosses train/validation/test",
        "test_split_created_before_model_fitting":True,
        "hyperparameter_tuning":"none; all five model and vectorizer settings fixed before model fitting; test scores are held-out evaluation",
        "random_seed":SEED,
        "vectorizer":vectorizer_config,
        "library_versions":{"python":__import__("sys").version.split()[0],"scikit_learn":sklearn.__version__,"numpy":np.__version__,"scipy":scipy.__version__},
        "run_started_utc":started.isoformat(),
        "run_finished_utc":finished.isoformat(),
        "total_elapsed_seconds":round(time.perf_counter()-wall_start,4),
        "per_model_seconds":model_seconds,
        "warnings":warning_messages,
        "prediction_file_contains_text":False,
        "dashboard_displays_raw_text":False,
        "limitations":[
            "This measures the author's source label for obscene-language presence, not broad toxicity, harmful influence, or the nine target subtypes.",
            "The dataset is a small, potentially class-imbalanced workshop corpus with VK source posts; results may not generalize beyond it.",
            "Regex filtering only catches obvious direct identifiers; it is not full anonymization or privacy review.",
            "Near-duplicate detection is approximate and uses nearest-neighbor surface-form similarity; it may miss semantic paraphrases.",
            "Class labels are inherited from the source and not independently re-annotated.",
        ],
    }
    (OUT / "audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":audit["experiment_status"],"raw_rows":len(raw_rows),"usable_unique_rows":len(final),
                      "class_counts":dict(Counter(y)),"split_counts":split_counts,
                      "near_pairs_detected_initial":near_pairs_initial,"near_pairs_seen":len(near_pair_records),
                      "near_removal_rounds":near_rounds,"near_pairs_in_final_pool":0,"near_rows_removed":near_removed,
                      "metrics_file":"analysis/experiments/ru_obscene_ml/metrics.json"},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()

