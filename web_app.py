"""Privacy-safe dashboard for the audited Russian experiment and target-data status."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
RU = ROOT / "analysis" / "experiments" / "ru_obscene_ml"


# Russian display labels; source keys and stored experiment artifacts stay unchanged.
SECTION_LABELS = {"Russian ML experiment": "Эксперимент с русскоязычными текстами", "Target corpus status": "Состояние целевого корпуса"}
SPLIT_LABELS = {"validation": "Валидационная", "test": "Тестовая"}
MODEL_LABELS = {
    "Logistic Regression": "Логистическая регрессия",
    "MultinomialNB": "Мультиномиальный наивный Байес (MultinomialNB)",
    "LinearSVC": "Линейный метод опорных векторов (LinearSVC)",
    "RandomForest": "Случайный лес (RandomForest)",
    "MLP": "Многослойный перцептрон (MLP)",
}
COLUMN_LABELS = {
    "Model (scikit-learn ML)": "Модель (машинное обучение, scikit-learn)",
    "Split": "Выборка", "Macro F1": "Макро F1",
    "F1 decent": "F1: без нецензурной лексики",
    "F1 obscene": "F1: с нецензурной лексикой", "N": "Число примеров",
}
TEXT_LABELS = {
    "This measures the author's source label for obscene-language presence, not broad toxicity, harmful influence, or the nine target subtypes.": "Оценивается исходная авторская метка наличия нецензурной лексики, а не токсичность в целом, вредоносное влияние или девять целевых подтипов.",
    "The dataset is a small, potentially class-imbalanced workshop corpus with VK source posts; results may not generalize beyond it.": "Датасет — небольшой учебный корпус с исходными публикациями из VK и возможным дисбалансом классов; результаты могут не обобщаться за его пределами.",
    "Regex filtering only catches obvious direct identifiers; it is not full anonymization or privacy review.": "Фильтрация регулярными выражениями выявляет только очевидные прямые идентификаторы; она не заменяет полную анонимизацию или проверку конфиденциальности.",
    "Near-duplicate detection is approximate and uses nearest-neighbor surface-form similarity; it may miss semantic paraphrases.": "Выявление близких дубликатов приблизительное и основано на сходстве текстовой формы методом ближайших соседей; смысловые перефразирования могут остаться незамеченными.",
    "Class labels are inherited from the source and not independently re-annotated.": "Метки классов унаследованы от источника; независимая повторная разметка не проводилась.",
    "The original target table contains 13,500 rows but only 297 exact unique strings and 221 detected near-duplicate pairs; the raw snapshot repeats the placeholder 'Raw dialogue', and none of the raw rows match candidate text. Existing approved-source records lack license/terms evidence. No target harmful-influence message is verified.": "Исходная целевая таблица содержит 13,500 строк, но лишь 297 уникальных строк при точном сравнении; обнаружена 221 пара близких дубликатов. В исходном снимке повторяется заглушка 'Raw dialogue', и ни одна исходная строка не совпадает с текстом кандидатов. Для существующих записей одобренных источников нет подтверждения лицензий и условий использования. Ни одно целевое сообщение о вредоносном влиянии не подтверждено.",
}


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


st.set_page_config(page_title="Cyber Threat Dataset — аудит", layout="wide")
st.title("Cyber Threat Dataset — воспроизводимое исследование")
st.caption("Агрегированные результаты без раскрытия личных данных. Панель не загружает и не показывает исходные сообщения.")
page = st.sidebar.radio("Раздел", ["Russian ML experiment", "Target corpus status"], format_func=SECTION_LABELS.get)

if page == "Russian ML experiment":
    audit = read_json(RU / "audit.json")
    metrics = read_json(RU / "metrics.json")
    st.header("Классификация русскоязычных текстов по наличию нецензурной лексики")
    st.markdown(
        "Источник: [MCA Workshop - Toxic comments](https://data.mendeley.com/datasets/fktgy52645/1), "
        "DOI `10.17632/fktgy52645.1`; в манифесте источника указана лицензия CC BY 4.0. "
        "Модели предсказывают исходные метки `decent` (без нецензурной лексики) / `obscene` (с нецензурной лексикой). Это не "
        "классификатор вредоносного влияния или киберугроз. Пять систем — модели машинного обучения scikit-learn, а не большие языковые модели (LLM)."
    )
    a, b, c, d = st.columns(4)
    a.metric("Уникальные строки после фильтрации", f"{audit['usable_unique_rows_after_filters']:,}")
    b.metric("Обучение / валидация / тест", " / ".join(
        str(audit["split_counts_by_labels"][part]["rows"]) for part in ("train", "validation", "test")
    ))
    c.metric("Пары близких дубликатов в итоговой выборке", str(audit["near_duplicate_pairs_in_final_pool"]))
    d.metric("Начальное значение генератора случайных чисел", str(audit["random_seed"]))
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
    st.subheader("Метрики на валидационной и отложенной тестовой выборках")
    display_frame = frame.replace({"Model (scikit-learn ML)": MODEL_LABELS, "Split": SPLIT_LABELS})
    st.dataframe(display_frame.style.format({"Macro F1": "{:.3f}", "F1 decent": "{:.3f}", "F1 obscene": "{:.3f}"}), hide_index=True, width="stretch", column_config=COLUMN_LABELS)
    st.plotly_chart(px.bar(display_frame[frame["Split"] == "test"], x="Model (scikit-learn ML)", y="Macro F1", title="Макро F1 на отложенной тестовой выборке", labels=COLUMN_LABELS), width="stretch")
    model = st.selectbox("Модель для матрицы ошибок", list(metrics["models"]), format_func=MODEL_LABELS.get)
    split = st.radio("Выборка для матрицы ошибок", ["validation", "test"], horizontal=True, format_func=SPLIT_LABELS.get)
    result = metrics["models"][model][split]
    matrix = pd.DataFrame(result["confusion_matrix"], index=["Истинный класс: без нецензурной лексики", "Истинный класс: с нецензурной лексикой"], columns=["Прогноз: без нецензурной лексики", "Прогноз: с нецензурной лексикой"])
    st.dataframe(matrix, width="stretch")
    st.caption(f"Время обучения и прогнозирования: {audit['total_elapsed_seconds']:.1f} с. Отложенная тестовая выборка не использовалась для настройки моделей.")
    with st.expander("Методика и ограничения"):
        st.write("Версии пакетов, предобработка, формирование выборок и полный перечень ограничений описаны в JSON-файле аудита. Задача этого корпуса уже, чем распознавание токсичности в целом. Небольшой тестовый набор не подтверждает качество работы в реальных условиях.")
        for item in audit["limitations"]:
            st.write(f"- {TEXT_LABELS.get(item, item)}")

else:
    status = read_json(ROOT / "analysis" / "target_corpus_status.json")
    st.header("Запрошенный корпус сообщений о вредоносном влиянии")
    st.error(f"Проверенные сообщения, соответствующие целевой задаче: {status['verified_target_messages']} / {status['required_target_messages']}")
    st.write(TEXT_LABELS.get(status["reason"], status["reason"]))
    st.info("Запрошенный целевой корпус из 13,500 сообщений не завершён. Отдельные эксперименты с источниками и кандидаты для сравнения с меткой NORMAL не засчитываются в подтипы вредоносного влияния.")
    st.write("Результаты аудита решений по источникам и недостающие условия завершения приведены в `analysis/FINAL_AUDIT.md`.")

