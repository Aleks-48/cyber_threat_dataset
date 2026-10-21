# Data provenance and audit

## Scope and result

The requested target is exactly 13,500 real, relevant, unique messages for nine harmful-influence subtypes, with defensible provenance and labels. This copy does **not** contain that target corpus. The original candidate table has 13,500 rows but just 297 exact distinct text strings, 221 near-duplicate pairs at `SequenceMatcher >= 0.88`, and only 197 connected text groups. The raw snapshot has 13,500 rows containing the literal `Raw dialogue`; none exactly matches a candidate text. The approved-source table has 44 entries but no license/terms field. Therefore **0 target-threat messages are currently verified**.

Subtype frequencies are no longer quota-balanced: the project config now requires representation only, while the exact 13,500 total, exact-text uniqueness, and zero detected near-duplicate pairs remain required.

## Licensed comparison candidates

A separate 13,500-row candidate pool was prepared from author-published KazSAnDRA score-classification (SC) train, validation, and test splits. The authors describe it as 180,064 customer reviews across appstore, bookstore, mapping, and marketplace domains, and the paper states the dataset is released under CC BY 4.0. Source: [repository](https://github.com/IS2AI/KazSAnDRA), [dataset paper and license statement](https://arxiv.org/abs/2403.19335), [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/).

Only `06_sc_train_ib.zip`, `09_sc_valid.zip`, and `10_sc_test.zip` were used; oversampled ROS and the PC/SC overlapping subsets were excluded. The downloaded files' GitHub blob SHAs match the API metadata; SHA-256 hashes and sizes are in `analysis/external_sources/KazSAnDRA/source_manifest.json`. The raw ZIP files remain separate from derived candidates.

The preparation script deduplicates by normalized original text only (NFKC, casefold, collapsed whitespace), never by text plus score. It preserves original 0-4 label, corresponding 1-5 sentiment score, domain, source split, custom ID, text, cleaned text, source URL, license, commit, and normalized-text hash. It retains source split proportions exactly at 10,800 train / 1,350 validation / 1,350 test and selects records deterministically with seed 42.

Across the three source splits there are 175,158 raw rows and 172,264 eligible global unique text records after within- and cross-split deduplication and exclusion of records matching direct email/URL/phone-like/@handle patterns. The direct-identifier screen excluded 501 unique records; its pattern counts can overlap, and this heuristic is not full anonymization. There were 715 cross-split exact text duplicates with differing source sentiment labels; because dedup is text-only, these are removed rather than retained under separate scores.

For selection, character TF-IDF (3-5 grams) nearest-five-neighbor cosine similarity at 0.90 flagged 20 candidate pairs over two replacement rounds. The final 13,500 candidate texts have 13,500 distinct normalized texts and zero pairs found by this check. It is a surface-form review heuristic, not exhaustive semantic paraphrase detection. The full decision record is `analysis/candidate_pools/kazsandra_candidate_report.json`; flagged pair endpoints are recorded in `kazsandra_removed_near_duplicate_pairs.csv`.

Every exported row is `safety_label=UNREVIEWED`, `review_status=CANDIDATE_ONLY`, and described as a **possible NORMAL comparison-pool candidate**. Sentiment is not safety. These review messages do not count toward the nine target subtypes and are not used to train the target-threat baselines.

## Other source checks

- [psytechlab self-harm / anti-self-harm dataset](https://huggingface.co/datasets/psytechlab/presuisidal_antisuisidal_dataset-master): the public card states MIT, Russian, 57,810 total records with a 43.6k train split. It contains mental-health self-reports and clinical/psychological categories, not encouragement of harm to another person. It is excluded from threat labels and from this candidate pool.
- [TextDetox multilingual toxicity](https://huggingface.co/datasets/textdetox/multilingual_toxicity_dataset): the compilation card states OpenRAIL++ and describes Russian source corpora obtained from Kaggle. The card's license does not establish rights for those upstream comment sources; no data was downloaded or used.
- Farabi Content Moderation and Safety remains gated and was not accessed.
- Qorgau is prompt material rather than real dialogues and is excluded.
- IvanFed/russian-toxic-comments-multilabel has conflicting license claims relative to its underlying source and was excluded pending rights clarification.

## Baselines

Five reproducible models were trained from the existing 166 unique non-UNCERTAIN manually labeled texts in the upstream project: Logistic Regression, Multinomial Naive Bayes, LinearSVC, Random Forest, and MLP. These are classical scikit-learn models, not LLMs. A two-stage `StratifiedGroupKFold` split keeps near-duplicate groups separate (99 train / 34 validation / 33 test; seed 42). Current metrics, exact run configuration, package versions, predictions, and split assignments are in `analysis/models/`.

Validation F1 / test F1: LR 53.7% / 96.0%; MNB 46.7% / 91.7%; LinearSVC 63.6% / 100%; Random Forest 63.6% / 100%; MLP 61.9% / 100%. The test set has only 33 items and the source corpus fails provenance/uniqueness audits, so these results are exploratory and cannot be presented as real-world performance. No classifier was trained from KazSAnDRA sentiment or from self-harm self-reports.

## Reproduction and limitations

Run `prepare_kazsandra_candidates.py` to verify source blob hashes and regenerate the separate candidate pool, then run `quality_audit.py`, `audit.py`, `train_grouped_baselines.py`, and `pytest -q`. The upstream target corpus audit remains blocked by the defects above. Further progress toward 13,500 verified target messages requires additional permitted, provenance-documented sources that actually contain relevant harmful-influence content, plus independent human review and subtype labels. The 13,500 KazSAnDRA candidates do not satisfy that requirement.

