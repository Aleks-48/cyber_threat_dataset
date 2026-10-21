"""Privacy-safe dashboard for the audited Russian experiment and target-data status."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
RU = ROOT / "analysis" / "experiments" / "ru_obscene_ml"


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


st.set_page_config(page_title="Cyber Threat Dataset Audit", layout="wide")
st.title("Cyber Threat Dataset - reproducible research")
st.caption("Privacy-safe aggregate results. This dashboard does not load or display source messages.")
page = st.sidebar.radio("Section", ["Russian ML experiment", "Target corpus status"])

if page == "Russian ML experiment":
    audit = read_json(RU / "audit.json")
    metrics = read_json(RU / "metrics.json")
    st.header("Russian obscene-language classification")
    st.markdown(
        "Source: [MCA Workshop - Toxic comments](https://data.mendeley.com/datasets/fktgy52645/1), "
        "DOI `10.17632/fktgy52645.1`; the source manifest records CC BY 4.0. "
        "This predicts the source's original `decent` / `obscene` labels. It is not a "
        "harmful-influence or cyber-threat classifier. The five systems are scikit-learn ML models, not LLMs."
    )
    a, b, c, d = st.columns(4)
    a.metric("Unique rows after filters", f"{audit['usable_unique_rows_after_filters']:,}")
    b.metric("Train / validation / test", " / ".join(
        str(audit["split_counts_by_labels"][part]["rows"]) for part in ("train", "validation", "test")
    ))
    c.metric("Near-duplicate pairs in final pool", str(audit["near_duplicate_pairs_in_final_pool"]))
    d.metric("Random seed", str(audit["random_seed"]))
    rows = []
    for model, results in metrics["models"].items():
        for split in ("validation", "test"):
            result = results[split]
            rows.append({
                "Model (scikit-learn ML)": model,
                "Split": split,
                "Macro F1": result["f1_macro"],
                "F1 decent": result["class_metrics"]["decent"]["f1"],
                "F1 obscene": result["class_metrics"]["obscene"]["f1"],
                "N": result["n"],
            })
    frame = pd.DataFrame(rows)
    st.subheader("Validation and held-out test metrics")
    st.dataframe(frame.style.format({"Macro F1": "{:.3f}", "F1 decent": "{:.3f}", "F1 obscene": "{:.3f}"}), hide_index=True, width="stretch")
    st.plotly_chart(px.bar(frame[frame["Split"] == "test"], x="Model (scikit-learn ML)", y="Macro F1", title="Held-out test macro F1"), width="stretch")
    model = st.selectbox("Confusion matrix model", list(metrics["models"]))
    split = st.radio("Confusion matrix split", ["validation", "test"], horizontal=True)
    result = metrics["models"][model][split]
    matrix = pd.DataFrame(result["confusion_matrix"], index=["true decent", "true obscene"], columns=["predicted decent", "predicted obscene"])
    st.dataframe(matrix, width="stretch")
    st.caption(f"Fit and predict time: {audit['total_elapsed_seconds']:.1f} seconds. No tuning used the held-out test split.")
    with st.expander("Method and limitations"):
        st.write("Read the audit JSON for package versions, preprocessing, split construction, and complete limitations. The corpus task is narrower than general toxicity. A small benchmark does not establish real-world performance.")
        for item in audit["limitations"]:
            st.write(f"- {item}")

else:
    status = read_json(ROOT / "analysis" / "target_corpus_status.json")
    st.header("Requested harmful-influence corpus")
    st.error(f"Verified relevant target messages: {status['verified_target_messages']} / {status['required_target_messages']}")
    st.write(status["reason"])
    st.info("The requested 13,500-message target corpus is unfinished. Separate source experiments and NORMAL comparison candidates do not count toward its harmful-influence subtypes.")
    st.write("See `analysis/FINAL_AUDIT.md` for audited source decisions and the missing conditions for completion.")

