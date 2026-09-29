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
    sources = load_csv("02_sources/sources_approved.csv")
    annotations = load_csv("07_manual_100/manual_annotations.csv")
    total_count = len(candidates)
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
    st.subheader("Данные набора")
    st.metric("Всего записей в датасете", f"{total_count:,}".replace(",", " "))
    subtype = st.selectbox("Фильтр по подвиду", ["Все"] + sorted(candidates["target_subtype"].unique()))
    source_columns = sources[["source_id", "source_name", "platform", "url"]].rename(
        columns={"url": "source_url"}
    )
    full_table = candidates.merge(
        source_columns, on="source_id", how="left", validate="many_to_one"
    )
    table = full_table if subtype == "Все" else full_table[full_table["target_subtype"] == subtype]
    st.caption(
        f"В таблице: {len(table):,} из {total_count:,} записей. "
        "Ограничения в 1 000 строк нет; выбранный фильтр меняет только таблицу."
    )
    st.download_button(
        "Скачать все 13 500 записей CSV",
        data=full_table.to_csv(index=False).encode("utf-8-sig"),
        file_name="cyber_threat_dataset_13500.csv",
        mime="text/csv",
        type="primary",
    )
    st.dataframe(
        table,
        width="stretch",
        height=760,
        hide_index=True,
    )

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
        st.info("Метрики ещё не рассчитаны. Запустите train_models.py и опубликуйте результаты.")
    else:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        scores = pd.read_csv(scores_path)
        st.subheader("Пять открытых моделей: оценка от 0 до 5")
        st.info(
            f"Статус: {metadata['dataset_status']}. "
            f"Всего уникальных размеченных текстов: {metadata['unique_labeled_texts']}; "
            f"Обучающих уникальных текстов: {metadata['training_texts']}; "
            f"тестовых: {metadata['test_texts']}."
        )
        st.caption(
            "Все пять моделей — открытые алгоритмы scikit-learn, обученные локально "
            "на этом наборе. Они не являются пятью внешними сервисами или "
            "предобученными большими языковыми моделями."
        )
        st.dataframe(
            scores,
            width="stretch",
            hide_index=True,
            column_config={
                "Открытый исходный код": st.column_config.LinkColumn(
                    "Исходный код и документация"
                ),
            },
        )
        st.plotly_chart(
            px.bar(
                scores,
                x="Model",
                y="Оценка 0–5",
                text="Оценка 0–5",
                range_y=[0, 5],
            ),
            width="stretch",
        )
        st.caption(
            "Оценка = F1 (%) / 20; равные F1 делят одно место. "
            "Бинарная задача TARGET_THREAT против OTHER_THREAT и NORMAL; "
            "UNCERTAIN исключены. "
            "Метрики получены на отложенных уникальных текстах из текущего снимка; "
            "шаблонное сходство и провал аудита не позволяют достоверно ранжировать "
            "модели по работе на реальных новых источниках."
        )
        predictions_path = ROOT / "10_model_baselines/model_predictions.csv"
        if predictions_path.exists():
            predictions = load_csv("10_model_baselines/model_predictions.csv")
            model_names = scores["Model"].tolist()
            if len(predictions) == metadata.get("analyzed_dataset_rows") and all(
                name in predictions.columns for name in model_names
            ):
                st.subheader("Анализ всех записей")
                st.caption(
                    "Каждая из пяти моделей обработала все строки датасета. "
                    "Прогноз 1 означает TARGET_THREAT; это автоматическая оценка, "
                    "а не ручная разметка или проверенный факт."
                )
                st.metric("Обработано каждой моделью", f"{len(predictions):,}".replace(",", " "))
                summary = pd.DataFrame({
                    "Модель": model_names,
                    "Прогноз 1": [int(predictions[name].sum()) for name in model_names],
                    "Прогноз 0": [int((predictions[name] == 0).sum()) for name in model_names],
                })
                st.dataframe(summary, width="stretch", hide_index=True)
                candidates = load_csv("06_candidates/candidates.csv")
                sources = load_csv("02_sources/sources_approved.csv")
                enriched = candidates.merge(
                    predictions.drop(columns="source_id"),
                    on="dialogue_id",
                    how="left",
                    validate="one_to_one",
                ).merge(
                    sources[["source_id", "source_name", "platform", "url"]].rename(
                        columns={"url": "source_url"}
                    ),
                    on="source_id",
                    how="left",
                    validate="many_to_one",
                )
                st.download_button(
                    "Скачать все записи с прогнозами пяти моделей CSV",
                    data=enriched.to_csv(index=False).encode("utf-8-sig"),
                    file_name="cyber_threat_dataset_13500_five_model_predictions.csv",
                    mime="text/csv",
                )
                selected_model = st.selectbox("Модель для анализа по каналам", model_names)
                by_source = (
                    enriched.groupby(["source_name", "platform"], dropna=False)
                    .agg(Записей=("dialogue_id", "size"), Прогнозов_1=(selected_model, "sum"))
                    .reset_index()
                    .sort_values("Записей", ascending=False)
                )
                st.dataframe(by_source, width="stretch", hide_index=True)
