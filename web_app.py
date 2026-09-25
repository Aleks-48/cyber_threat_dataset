"""Read-only dashboard for the checked-in dataset and its audit."""
import json
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from audit import ROOT, audit
from train_models import MODEL_CHARACTERISTICS, train_inference_models

st.set_page_config(page_title="Cyber Threat Dataset", layout="wide")
st.title("Cyber Threat Dataset — Theme 8")
st.caption("Research snapshot. Review the audit before interpreting model scores.")


@st.cache_data
def load_csv(relative_path):
    return pd.read_csv(ROOT / relative_path)


@st.cache_resource(show_spinner="Обучение пяти демонстрационных моделей…")
def load_inference_models():
    return train_inference_models()


def prediction_strength(pipeline, text):
    """Return a comparable 0..100 model score where available."""
    estimator = pipeline.steps[-1][1]
    transformed = pipeline[:-1].transform([text])
    if hasattr(estimator, "predict_proba"):
        return float(estimator.predict_proba(transformed)[0][1] * 100), "вероятность"
    if hasattr(estimator, "decision_function"):
        margin = float(estimator.decision_function(transformed)[0])
        return 100 / (1 + math.exp(-margin)), "нормализованный отступ"
    return None, "нет оценки"


page = st.sidebar.radio(
    "Раздел",
    ["Данные", "Качество и аудит", "Модели"],
)
report = audit()
if not report["next_stage_allowed"]:
    st.warning("Датасет не прошёл аудит качества. Результаты моделей носят демонстрационный характер.")

if page == "Данные":
    candidates = load_csv("06_candidates/candidates.csv")
    enriched = load_csv("06_candidates/candidates_with_sources.csv")
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
        enriched = enriched[enriched["target_subtype"] == subtype]
    st.subheader("Записи с наименованием открытого источника")
    st.caption(
        "DECLARED_OSINT означает, что источник внесён в реестр проекта; "
        "доступность URL и происхождение текста требуют отдельной проверки."
    )
    full_dataset_path = ROOT / "06_candidates/candidates_with_sources.csv"
    st.download_button(
        "⬇️ Скачать весь датасет — 13 500 строк (CSV)",
        data=full_dataset_path.read_bytes(),
        file_name="cyber_threat_dataset_13500_with_sources.csv",
        mime="text/csv",
        help="Скачивается полный файл, выбранный ниже фильтр на него не влияет.",
        type="primary",
    )
    st.caption(
        f"Размер файла: {full_dataset_path.stat().st_size / (1024 * 1024):.1f} МБ. "
        "В выгрузку входят тексты, подвиды, языки, названия каналов, платформы и URL."
    )
    st.dataframe(enriched.head(1000), width="stretch")

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
        scores = scores.sort_values("Rank")
        st.info(
            f"Статус: {metadata['dataset_status']}. "
            f"Обучающих уникальных текстов: {metadata['training_texts']}; "
            f"тестовых: {metadata['test_texts']}."
        )
        st.dataframe(scores, width="stretch")
        st.plotly_chart(
            px.bar(
                scores,
                x="Model",
                y="F1-Score",
                text="F1-Score",
                hover_data=[
                    "Rank", "Characteristic", "Best-For", "Limitation",
                    "Predict-ms-per-1000",
                ],
            ),
            width="stretch",
        )
        st.caption(
            "Бинарная задача TARGET_THREAT против OTHER_THREAT и NORMAL; "
            "UNCERTAIN исключены. "
            "Метрики получены на отложенных уникальных текстах из текущего снимка; "
            "они не измеряют качество на реальных новых источниках."
        )
        st.divider()
        st.subheader("Проверить текст пятью моделями")
        st.caption(
            "Каждая модель выдаёт бинарный демонстрационный прогноз: "
            "TARGET_THREAT или OTHER/NORMAL. Результат не является экспертным решением."
        )
        text_to_check = st.text_area(
            "Текст для анализа",
            height=140,
            placeholder="Введите сообщение на русском или казахском языке…",
        )
        if st.button("Проанализировать всеми моделями", type="primary"):
            if not text_to_check.strip():
                st.warning("Введите непустой текст.")
            else:
                with st.spinner("Модели анализируют текст…"):
                    models = load_inference_models()
                    rows = []
                    ranks = dict(zip(scores["Model"], scores["Rank"]))
                    for name, pipeline in models.items():
                        prediction = int(pipeline.predict([text_to_check.strip()])[0])
                        strength, score_type = prediction_strength(
                            pipeline, text_to_check.strip()
                        )
                        characteristic, best_for, limitation = MODEL_CHARACTERISTICS[name]
                        rows.append({
                            "Место": int(ranks.get(name, 999)),
                            "Модель": name,
                            "Прогноз": "TARGET_THREAT" if prediction else "OTHER/NORMAL",
                            "Оценка, %": round(strength, 1) if strength is not None else None,
                            "Тип оценки": score_type,
                            "Характеристика": characteristic,
                            "Ограничение": limitation,
                        })
                result_frame = pd.DataFrame(rows).sort_values("Место")
                threat_votes = int((result_frame["Прогноз"] == "TARGET_THREAT").sum())
                if threat_votes >= 3:
                    st.error(f"TARGET_THREAT: {threat_votes} из 5 моделей")
                else:
                    st.success(f"OTHER/NORMAL: {5 - threat_votes} из 5 моделей")
                st.dataframe(result_frame, width="stretch", hide_index=True)
                st.caption(
                    "Процент SVM является преобразованным расстоянием до границы, "
                    "а не калиброванной вероятностью."
                )
