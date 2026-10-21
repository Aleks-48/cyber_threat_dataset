# Cyber Threat Dataset - reproducible Russian ML experiment

This repository currently contains a reproducible **Russian obscene-language classification experiment** using the source dataset's original `decent` / `obscene` labels. It is a narrow language-moderation task, not a classifier for harmful influence, cyber threats, or the project's nine target subtypes. The five systems are conventional scikit-learn ML models, not LLMs.

## Verified target-corpus status

The requested 13,500 unique, relevant harmful-influence messages are **not complete**. The audit verified **0 / 13,500** target messages. The historic table contains 13,500 rows but only 297 exact unique strings; a placeholder appears in the raw snapshot, and the audit detected near duplicates. Do not treat these rows or unrelated reviews as completed target data. See [`analysis/target_corpus_status.json`](analysis/target_corpus_status.json) and [`analysis/FINAL_AUDIT.md`](analysis/FINAL_AUDIT.md).

## Separate Russian experiment

- Source: [MCA Workshop - Toxic comments, Mendeley Data](https://data.mendeley.com/datasets/fktgy52645/1), DOI `10.17632/fktgy52645.1`, CC BY 4.0 as recorded in the source manifest.
- Task: predict the source's original `decent` / `obscene` labels.
- Cleaned corpus: 3,700 unique rows after exact and near-duplicate filtering.
- Train / validation / test: 2,241 / 728 / 731; test was held out before model selection.
- Test macro F1: Logistic Regression 0.716; Multinomial Naive Bayes 0.488; LinearSVC 0.730; Random Forest 0.735; MLP 0.530. Per-class scores and confusion matrices are in [`analysis/experiments/ru_obscene_ml/metrics.json`](analysis/experiments/ru_obscene_ml/metrics.json).
- Audit, source attribution, license details, seed, package versions, and limitations: [`analysis/experiments/ru_obscene_ml/audit.json`](analysis/experiments/ru_obscene_ml/audit.json) and [`analysis/external_sources/MCA_Russian_Toxic_Comments/source_manifest.json`](analysis/external_sources/MCA_Russian_Toxic_Comments/source_manifest.json).

## Run the dashboard locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run web_app.py
```

The dashboard displays aggregate experiment results and the target-data audit. No raw comments, row-level predictions, fitted models, or local corpus files are needed by the dashboard.

## Reproduce the experiment

The source file is downloaded from Mendeley only when requested. Verify the dataset's terms before reuse and preserve its attribution. The downloader records provenance; training writes row-level artifacts locally, which are excluded from Git by `.gitignore`.

```bash
pip install -r requirements-train.txt
python download_mca_dataset.py
python train_ru_obscene_ml.py
```

Training requires the original dataset file in the documented local input location; this repository intentionally does not redistribute raw comments. Do not commit raw data, row-level predictions, identifiers, credentials, or model binaries.

## Validation

Run the artifact checks with `python -m pytest -q tests`. Results apply only to this dataset, split, and binary label task; they do not establish performance for the nine harmful-influence subtypes.

