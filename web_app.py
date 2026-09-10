import os
import csv
import json
import streamlit as st
import pandas as pd
import subprocess

# Set page configuration
st.set_page_config(page_title="Cyber Threat Pipeline Dashboard", layout="wide")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

st.title("🛡️ Cyber Threat Dataset Pipeline (Theme 8)")
st.markdown("Веб-интерфейс для управления пайплайном сбора и аудита датасета по киберугрозам (HARMFUL_INFLUENCE).")

# Sidebar navigation
page = st.sidebar.selectbox("Навигация", ["Дашборд и Аудит", "Обозреватель данных", "Настройки"])

if page == "Дашборд и Аудит":
    st.header("Статус пайплайна")
    
    # Run audit logic
    if st.button("🚀 Запустить финальный аудит"):
        with st.spinner("Выполняется проверка артефактов..."):
            try:
                result = subprocess.run(
                    ["python", "run.py"], 
                    cwd=ROOT_DIR, 
                    capture_output=True, 
                    text=True,
                    check=True
                )
                st.success("Аудит успешно завершен!")
                st.code(result.stdout, language="markdown")
            except subprocess.CalledProcessError as e:
                st.error("Ошибка при запуске аудита!")
                st.code(e.output, language="markdown")

    st.subheader("Метрики разметки")
    try:
        annotations = pd.read_csv(os.path.join(ROOT_DIR, "07_manual_100", "manual_annotations.csv"))
        counts = annotations['annotation'].value_counts()
        
        col1, col2, col3, col4 = st.columns(4)
        total = len(annotations)
        col1.metric("Всего размечено", total)
        col2.metric("TARGET_THREAT", f"{(counts.get('TARGET_THREAT', 0) / total) * 100:.1f}%" if total else "0%")
        col3.metric("NORMAL", f"{(counts.get('NORMAL', 0) / total) * 100:.1f}%" if total else "0%")
        col4.metric("UNCERTAIN", f"{(counts.get('UNCERTAIN', 0) / total) * 100:.1f}%" if total else "0%")
        
        st.bar_chart(counts)
    except FileNotFoundError:
        st.warning("Файл manual_annotations.csv не найден.")

elif page == "Обозреватель данных":
    st.header("Обозреватель собранных данных")
    
    data_files = {
        "Ключевые слова": os.path.join(ROOT_DIR, "01_keywords", "keywords_approved.csv"),
        "Источники": os.path.join(ROOT_DIR, "02_sources", "sources_approved.csv"),
        "Кандидаты (Диалоги)": os.path.join(ROOT_DIR, "06_candidates", "candidates.csv"),
        "Ручная выборка": os.path.join(ROOT_DIR, "07_manual_100", "manual_sample_100.csv"),
    }
    
    selected_file = st.selectbox("Выберите таблицу для просмотра:", list(data_files.keys()))
    file_path = data_files[selected_file]
    
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        st.dataframe(df, use_container_width=True)
    else:
        st.error(f"Файл не найден: {file_path}")

elif page == "Настройки":
    st.header("Конфигурация пайплайна")
    config_path = os.path.join(ROOT_DIR, "config.yaml")
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config_text = f.read()
        st.text_area("config.yaml", config_text, height=300)
    else:
        st.warning("Файл конфигурации не найден.")
