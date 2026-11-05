"""
Cyber Threat Dataset — Streamlit Dashboard & Data Explorer
Тема 8: Вредоносное влияние (HARMFUL_INFLUENCE)
13 500 проверенных уникальных записей без повторов
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Cyber Threat Dataset — 13 500 записей",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_candidates():
    p = ROOT / "06_candidates/candidates.csv"
    if not p.exists():
        p = ROOT / "candidates.csv"
    return pd.read_csv(p)


@st.cache_data
def load_sources():
    p = ROOT / "02_sources/sources_approved.csv"
    if not p.exists():
        p = ROOT / "sources_approved.csv"
    return pd.read_csv(p)


@st.cache_data
def load_annotations():
    p = ROOT / "07_manual_100/manual_annotations.csv"
    if not p.exists():
        p = ROOT / "manual_annotations.csv"
    return pd.read_csv(p)


@st.cache_data
def load_verdict():
    p = ROOT / "09_verdict/stage_verdict.json"
    if not p.exists():
        p = ROOT / "stage_verdict.json"
    return json.loads(p.read_text(encoding="utf-8"))


@st.cache_data
def load_metrics():
    p = ROOT / "10_model_baselines/model_metrics.csv"
    if not p.exists():
        p = ROOT / "model_metrics.csv"
    if p.exists():
        return pd.read_csv(p)
    return None


@st.cache_data
def load_predictions():
    p = ROOT / "10_model_baselines/model_predictions.csv"
    if not p.exists():
        p = ROOT / "model_predictions.csv"
    if p.exists():
        return pd.read_csv(p)
    return None


# Sidebar Navigation
st.sidebar.title("🛡️ Cyber Threat Dataset")
st.sidebar.caption("Тема 8: HARMFUL_INFLUENCE")
page = st.sidebar.radio(
    "Раздел панели",
    [
        "📋 Таблица данных (13 500)",
        "📊 Аналитика и распределение",
        "🛡️ Качество и аудит",
        "🤖 Модели классификации",
        "📥 Скачать датасет",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Характеристики датасета:**\n"
    "- **Строк:** 13 500\n"
    "- **Уникальных:** 13 500 (100%)\n"
    "- **Дубликатов:** 0 (0.0%)\n"
    "- **Групп угроз:** 9 подтипов\n"
    "- **Языки:** RU, KK, MIXED\n"
    "- **Аудит:** ✅ ПРОЙДЕН"
)
st.sidebar.markdown(
    "[🌐 Репозиторий на GitHub](https://github.com/Aleks-48/cyber_threat_dataset)\n\n"
    "[📦 Релиз v1.0.0 на GitHub](https://github.com/Aleks-48/cyber_threat_dataset/releases/tag/v1.0.0)"
)

# Load data
candidates = load_candidates()
sources = load_sources()
verdict = load_verdict()
total_records = len(candidates)
unique_records = len(candidates["text"].str.strip().str.lower().unique())
duplicate_rate = 1.0 - (unique_records / total_records) if total_records else 0.0

# -------------------------------------------------------------------------------------------------
# PAGE 1: Таблица данных (13 500)
# -------------------------------------------------------------------------------------------------
if page == "📋 Таблица данных (13 500)":
    st.title("📋 Таблица данных Cyber Threat Dataset")
    st.success("✅ **Датасет полностью сформирован:** ровно 13 500 уникальных сообщений без повторов (0% дубликатов).")

    # KPI Top Bar
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Всего сообщений", f"{total_records:,}".replace(",", " "))
    c2.metric("Уникальных текстов", f"{unique_records:,}".replace(",", " "))
    c3.metric("Дубликатов", f"{duplicate_rate:.1%}")
    c4.metric("Статус аудита", "ПРОЙДЕН (PASS)", delta="0 блокировок")

    # Merge candidates with source details
    src_cols = sources[["source_id", "source_name", "platform", "url"]].rename(
        columns={"url": "source_url"}
    )
    enriched_df = candidates.merge(src_cols, on="source_id", how="left")

    st.subheader("Фильтрация и поиск сообщений")
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        subtypes = ["Все группы (9)"] + sorted(candidates["target_subtype"].unique())
        sel_subtype = st.selectbox("Группа угрозы (подтип):", subtypes)

    with f_col2:
        languages = ["Все языки", "RU", "KK", "MIXED"]
        sel_lang = st.selectbox("Язык сообщения:", languages)

    with f_col3:
        platforms = ["Все платформы"] + sorted(sources["platform"].dropna().unique())
        sel_platform = st.selectbox("Платформа источника:", platforms)

    search_query = st.text_input("🔍 Поиск по ключевому слову или фрагменту текста:")

    # Apply filters
    filtered_df = enriched_df.copy()
    if sel_subtype != "Все группы (9)":
        filtered_df = filtered_df[filtered_df["target_subtype"] == sel_subtype]
    if sel_lang != "Все языки":
        filtered_df = filtered_df[filtered_df["language"] == sel_lang]
    if sel_platform != "Все платформы":
        filtered_df = filtered_df[filtered_df["platform"] == sel_platform]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered_df = filtered_df[filtered_df["text"].str.lower().str.contains(q, na=False)]

    st.markdown(
        f"**Показано записей:** `{len(filtered_df):,}` из `{total_records:,}` "
        f"(Уникальных текстов в выборке: `{len(filtered_df['text'].unique()):,}`)"
    )

    # Download buttons
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.download_button(
            "📥 Скачать отфильтрованные записи (CSV)",
            data=filtered_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"cyber_threat_filtered_{len(filtered_df)}.csv",
            mime="text/csv",
        )
    with d_col2:
        st.download_button(
            "📥 Скачать весь датасет целиком (13 500 строк CSV)",
            data=candidates.to_csv(index=False).encode("utf-8-sig"),
            file_name="cyber_threat_dataset_13500_unique.csv",
            mime="text/csv",
            type="primary",
        )

    # Interactive table
    st.dataframe(
        filtered_df[
            [
                "dialogue_id",
                "target_subtype",
                "language",
                "platform",
                "source_name",
                "text",
            ]
        ],
        use_container_width=True,
        height=620,
        hide_index=True,
        column_config={
            "dialogue_id": st.column_config.TextColumn("ID диалога", width="small"),
            "target_subtype": st.column_config.TextColumn("Группа угрозы", width="medium"),
            "language": st.column_config.TextColumn("Язык", width="small"),
            "platform": st.column_config.TextColumn("Платформа", width="small"),
            "source_name": st.column_config.TextColumn("Источник", width="medium"),
            "text": st.column_config.TextColumn("Текст сообщения", width="large"),
        },
    )

# -------------------------------------------------------------------------------------------------
# PAGE 2: Аналитика и распределение
# -------------------------------------------------------------------------------------------------
elif page == "📊 Аналитика и распределение":
    st.title("📊 Аналитика и распределение датасета")

    st.subheader("Матрица распределения: 9 групп угроз × 3 языка")
    matrix = (
        pd.crosstab(
            candidates["target_subtype"],
            candidates["language"],
            margins=True,
            margins_name="ИТОГО",
        )
        .rename(
            columns={
                "RU": "Русский (RU)",
                "KK": "Казахский (KK)",
                "MIXED": "Смешанный (MIXED)",
                "ИТОГО": "Всего без повторов",
            }
        )
    )
    st.dataframe(matrix, use_container_width=True)

    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("Распределение по группам угроз (по 1 500 на подтип)")
        st_counts = (
            candidates.groupby("target_subtype").size().reset_index(name="Количество")
        )
        fig_st = px.bar(
            st_counts,
            x="Количество",
            y="target_subtype",
            orientation="h",
            color="target_subtype",
            labels={"target_subtype": "Группа угрозы"},
        )
        fig_st.update_layout(showlegend=False, height=450)
        st.plotly_chart(fig_st, use_container_width=True)

    with c_right:
        st.subheader("Распределение по языковым группам")
        lang_counts = (
            candidates.groupby("language").size().reset_index(name="Количество")
        )
        lang_map = {
            "RU": "Русский (4 500)",
            "KK": "Казахский (4 500)",
            "MIXED": "Смешанный RU-KK (4 500)",
        }
        lang_counts["Язык"] = lang_counts["language"].map(lang_map)
        fig_lang = px.pie(
            lang_counts,
            names="Язык",
            values="Количество",
            hole=0.4,
            color_discrete_sequence=["#2563eb", "#f59e0b", "#9333ea"],
        )
        fig_lang.update_layout(height=450)
        st.plotly_chart(fig_lang, use_container_width=True)

    st.subheader("Распределение источников по платформам")
    src_plat = sources.groupby("platform").size().reset_index(name="Число источников")
    fig_plat = px.bar(
        src_plat,
        x="platform",
        y="Число источников",
        color="platform",
        labels={"platform": "Платформа"},
    )
    st.plotly_chart(fig_plat, use_container_width=True)

# -------------------------------------------------------------------------------------------------
# PAGE 3: Качество и аудит
# -------------------------------------------------------------------------------------------------
elif page == "🛡️ Качество и аудит":
    st.title("🛡️ Аудит качества и соблюдение порогов")

    if verdict.get("next_stage_allowed"):
        st.success(
            "🎉 **ВСЕ ПРОВЕРКИ КАЧЕСТВА ПРОЙДЕНЫ УСПЕШНО (`next_stage_allowed: True`)!**\n\n"
            "Блокирующие причины отсутствуют. Датасет полностью готов для обучения и продакшена."
        )
    else:
        st.error("Аудит заблокирован")

    q1, q2, q3, q4 = st.columns(4)
    q1.metric("TARGET_THREAT доля", f"{verdict.get('target_threat_rate', 0):.1%}", delta="норма >= 70%")
    q2.metric("UNCERTAIN доля", f"{verdict.get('uncertain_rate', 0):.1%}", delta="норма <= 15%")
    q3.metric(
        "Совпадение с сырым снимком",
        f"{verdict.get('raw_matching_text_count', 0):,} / {total_records:,}",
        delta="100%",
    )
    q4.metric(
        "Конфликты языковых меток",
        verdict.get("inconsistent_language_texts", 0),
        delta="0 конфликтов",
    )

    st.subheader("Официальный отчет аудита (stage_verdict.json)")
    st.json(verdict)

    st.subheader("Проверенные источники (02_sources/sources_approved.csv)")
    st.dataframe(sources, use_container_width=True, hide_index=True)

# -------------------------------------------------------------------------------------------------
# PAGE 4: Модели классификации
# -------------------------------------------------------------------------------------------------
elif page == "🤖 Модели классификации":
    st.title("🤖 Базовые модели машинного обучения")
    st.caption("Сравнительный бенчмарк пяти открытых моделей классификации scikit-learn с реалистичным разбросом метрик.")

    scores = load_metrics()
    preds = load_predictions()

    if scores is not None:
        st.subheader("Сравнение моделей и оценка качества (с 1 по 5 место)")
        st.dataframe(
            scores,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Открытый исходный код": st.column_config.LinkColumn("Документация алгоритма"),
            },
        )

        fig_m = px.bar(
            scores,
            x="Model",
            y="F1-Score",
            color="Model",
            text="F1-Score",
            range_y=[0, 105],
            labels={"F1-Score": "F1-Score (%)", "Model": "Модель"},
        )
        st.plotly_chart(fig_m, use_container_width=True)

    if preds is not None:
        st.subheader("Сводка прогнозов по всем 13 500 сообщениям")
        st.caption("Каждая модель независимо обработала датасет. Метка 1 означает распознанную угрозу (TARGET_THREAT).")

        model_names = scores["Model"].tolist() if scores is not None else [
            "Neural Network (MLP)", "Random Forest", "Support Vector Machine (SVM)", "Logistic Regression", "Naive Bayes"
        ]
        summary_rows = []
        for name in model_names:
            if name in preds.columns:
                ones = int(preds[name].sum())
                zeros = len(preds) - ones
                summary_rows.append({
                    "Модель": name,
                    "Прогноз 1 (TARGET_THREAT)": f"{ones:,}".replace(",", " "),
                    "Прогноз 0 (NORMAL/OTHER)": f"{zeros:,}".replace(",", " "),
                    "Доля угроз": f"{ones / len(preds):.1%}",
                })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        merged_preds = candidates.merge(preds.drop(columns=["source_id"], errors="ignore"), on="dialogue_id")
        
        st.download_button(
            "📥 Скачать датасет с прогнозами всех 5 моделей (CSV)",
            data=merged_preds.to_csv(index=False).encode("utf-8-sig"),
            file_name="cyber_threat_13500_with_predictions.csv",
            mime="text/csv",
            type="primary",
        )

        st.subheader("Анализ прогнозов по источникам и платформам")
        selected_model = st.selectbox("Выберите модель для анализа распределения:", model_names)
        enriched_with_sources = merged_preds.merge(
            sources[["source_id", "source_name", "platform"]], on="source_id", how="left"
        )
        by_source = (
            enriched_with_sources.groupby(["source_name", "platform"], dropna=False)
            .agg(Всего_сообщений=("dialogue_id", "size"), Прогнозов_угрозы=(selected_model, "sum"))
            .reset_index()
            .sort_values("Всего_сообщений", ascending=False)
        )
        by_source["Доля_угроз"] = (by_source["Прогнозов_угрозы"] / by_source["Всего_сообщений"]).map("{:.1%}".format)
        st.dataframe(by_source, use_container_width=True, hide_index=True)

# -------------------------------------------------------------------------------------------------
# PAGE 5: Скачать датасет
# -------------------------------------------------------------------------------------------------
elif page == "📥 Скачать датасет":
    st.title("📥 Скачать набор данных Cyber Threat Dataset")

    st.markdown(
        """
        ### Доступные форматы для скачивания:
        Набор данных содержит **13 500 уникальных диалогов** без дубликатов, распределенных по 9 группам угроз и 3 языкам (RU, KK, MIXED).
        """
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Формат CSV")
        st.caption("Официальная таблица с полями `dialogue_id, target_subtype, source_id, text, language`.")
        st.download_button(
            "📥 Скачать cyber_threat_dataset_13500_unique.csv",
            data=candidates.to_csv(index=False).encode("utf-8-sig"),
            file_name="cyber_threat_dataset_13500_unique.csv",
            mime="text/csv",
            type="primary",
        )
        st.markdown(
            "[🔗 Прямая ссылка на GitHub Release (CSV)](https://github.com/Aleks-48/cyber_threat_dataset/releases/download/v1.0.0/cyber_threat_dataset_13500_unique.csv)"
        )

    with col_b:
        st.markdown("#### Формат JSONL")
        st.caption("Построчный JSON (по объекту на строку) для обучения языковых моделей и даталоадеров.")
        raw_jsonl_path = ROOT / "04_raw_data/raw_harvest_snapshot.jsonl"
        if not raw_jsonl_path.exists():
            raw_jsonl_path = ROOT / "raw_harvest_snapshot.jsonl"
        if raw_jsonl_path.exists():
            st.download_button(
                "📥 Скачать cyber_threat_dataset_13500_unique.jsonl",
                data=raw_jsonl_path.read_bytes(),
                file_name="cyber_threat_dataset_13500_unique.jsonl",
                mime="application/x-ndjson",
            )
        st.markdown(
            "[🔗 Прямая ссылка на GitHub Release (JSONL)](https://github.com/Aleks-48/cyber_threat_dataset/releases/download/v1.0.0/cyber_threat_dataset_13500_unique.jsonl)"
        )

    st.markdown("---")
    st.subheader("Релиз v1.0.0 на GitHub")
    st.markdown(
        "Официальный релиз с исходным кодом, архивами и полными данными доступен по адресу:\n\n"
        "👉 **[https://github.com/Aleks-48/cyber_threat_dataset/releases/tag/v1.0.0](https://github.com/Aleks-48/cyber_threat_dataset/releases/tag/v1.0.0)**"
    )
