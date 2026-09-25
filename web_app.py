"""Read-only dashboard for the checked-in dataset and its audit."""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from audit import ROOT, audit

st.set_page_config(page_title="Cyber Threat Dataset", layout="wide")
st.title("Cyber Threat Dataset — Theme 8")
st.caption("Research snapshot. Review the audit before interpreting model scores.")


@st.cache_data
def load_csv(relative_path):
    return pd.read_csv(ROOT / relative_path)


page = st.sidebar.radio(
    "Раздел",
    ["Данные", "Качество и аудит", "Модели"],
)
report = audit()
if not report["next_stage_allowed"]:
    st.warning("Датасет не прошёл аудит качества. Результаты моделей носят демонстрационный характер.")

if page == "Данные":
    candidates = load_csv("06_candidates/candidates.csv")
    annotations = load_csv("07_manual_100/manual_annotations.csv")
    a, b, c, d = st.columns(4)
    a.metric("Записей", report["candidate_count"])
    b.metric("Уникальных текстов", report["unique_text_count"])
    c.metric("Размечено", report["annotation_count"])
    d.metric("Повторы текста", f"{report['duplicate_text_rate']:.1%}")
    left, right = st.columns(2)
    with left:
        counts = (
            candidates.groupby("target_subtype").size().reset_index(name="count")
        )
        st.plotly_chart(
            px.bar(counts, x="count", y="target_subtype", orientation="h"),
            width="stretch",
        )
    with right:
        labels = annotations.groupby("annotation").size().reset_index(name="count")
        st.plotly_chart(
            px.bar(labels, x="annotation", y="count"), width="stretch"
        )
    st.caption("Частоты относятся к строкам файла, а не к независимым диалогам.")
    subtype = st.selectbox("Подвид", ["Все"] + sorted(candidates["target_subtype"].unique()))
    if subtype != "Все":
        candidates = candidates[candidates["target_subtype"] == subtype]
    st.dataframe(candidates.head(1000), width="stretch")

elif page == "Качество и аудит":
    if st.button("Пересчитать и сохранить аудит"):
        subprocess.run([sys.executable, str(ROOT / "run.py")], cwd=ROOT, check=True)
        st.success("Аудит обновлён")
    st.metric("TARGET_THREAT", f"{report['target_threat_rate']:.1%}")
    st.metric("UNCERTAIN", f"{report['uncertain_rate']:.1%}")
    st.metric("Тексты, совпавшие с сырым снимком", report["raw_matching_text_count"])
    st.metric("Тексты с разными языковыми метками", report["inconsistent_language_texts"])
    if report["blocking_reasons"]:
        st.error("Переход к следующему этапу запрещён:")
        for reason in report["blocking_reasons"]:
            st.write(f"• {reason}")
    else:
        st.success("Все настроенные проверки пройдены")
    st.json(report)

else:
    metadata_path = ROOT / "10_model_baselines/evaluation_metadata.json"
    scores_path = ROOT / "10_model_baselines/model_metrics.csv"
    if not metadata_path.exists() or not scores_path.exists():
        st.info("Метрики ещё не рассчитаны. Запустите train_models.py.")
    else:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        scores = pd.read_csv(scores_path)
        st.info(
            f"Статус: {metadata['dataset_status']}. "
            f"Обучающих уникальных текстов: {metadata['training_texts']}; "
            f"тестовых: {metadata['test_texts']}."
        )
        st.dataframe(scores, width="stretch")
        st.plotly_chart(
            px.bar(scores, x="Model", y="F1-Score", text="F1-Score"),
            width="stretch",
        )
        st.caption(
            "Бинарная задача TARGET_THREAT против OTHER_THREAT и NORMAL; "
            "UNCERTAIN исключены. "
            "Метрики получены на отложенных уникальных текстах из текущего снимка; "
            "они не измеряют качество на реальных новых источниках."
        )
