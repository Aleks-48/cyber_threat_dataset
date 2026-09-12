import os
import streamlit as st
import pandas as pd
import subprocess
import plotly.express as px
import numpy as np

# Настройка страницы
st.set_page_config(page_title="Cyber Threat Pipeline Dashboard", layout="wide", page_icon="🛡️")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

st.title("🛡️ Cyber Threat Dataset Pipeline (Theme 8)")
st.markdown("Продвинутый дашборд аналитики и управления пайплайном по сбору киберугроз (HARMFUL_INFLUENCE).")

# Боковое меню
page = st.sidebar.radio("Навигация", ["📊 Дашборд и Аналитика", "🤖 Сравнение ML-моделей", "📁 Обозреватель данных", "⚙️ Статус и Аудит"])

# Вспомогательная функция для чтения данных
@st.cache_data
def load_data(filename):
    path = os.path.join(ROOT_DIR, filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

if page == "📊 Дашборд и Аналитика":
    st.header("Глобальная аналитика угроз")
    
    annotations = load_data(os.path.join("07_manual_100", "manual_annotations.csv"))
    candidates = load_data(os.path.join("06_candidates", "candidates.csv"))
    
    if not annotations.empty and not candidates.empty:
        col1, col2, col3, col4 = st.columns(4)
        total = len(annotations)
        target_rate = (annotations['annotation'] == 'TARGET_THREAT').mean() * 100
        uncertain_rate = (annotations['annotation'] == 'UNCERTAIN').mean() * 100
        
        col1.metric("Собрано диалогов", f"{len(candidates):,}")
        col2.metric("Размечено экспертами", total)
        col3.metric("Доля TARGET_THREAT", f"{target_rate:.1f}%", delta="Норма > 70%" if target_rate >= 70 else "Критично", delta_color="normal" if target_rate >= 70 else "inverse")
        col4.metric("Доля UNCERTAIN", f"{uncertain_rate:.1f}%", delta="Норма < 15%" if uncertain_rate <= 15 else "Критично", delta_color="inverse" if uncertain_rate <= 15 else "normal")
        
        st.divider()
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Распределение классов угрозы")
            fig_pie = px.pie(
                annotations, 
                names='annotation', 
                color='annotation',
                color_discrete_map={
                    'TARGET_THREAT': '#ef4444',
                    'OTHER_THREAT': '#f97316',
                    'NORMAL': '#22c55e',
                    'UNCERTAIN': '#94a3b8'
                },
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            st.subheader("Подвиды угроз в датасете")
            subtype_counts = candidates['target_subtype'].value_counts().reset_index()
            subtype_counts.columns = ['target_subtype', 'count']
            fig_bar = px.bar(
                subtype_counts, 
                y='target_subtype', 
                x='count', 
                orientation='h',
                color='count',
                color_continuous_scale='Reds'
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.divider()
        st.subheader("🗺️ География выявленных угроз (OSINT Оценка)")
        st.markdown("Тепловая карта активности профилей (симуляция распределения по регионам КЗ/РФ на основе открытых данных).")
        geo_data = pd.DataFrame(np.random.randn(200, 2) / [2.0, 2.0] + [51.1, 71.4], columns=['lat', 'lon'])
        geo_data2 = pd.DataFrame(np.random.randn(100, 2) / [3.0, 3.0] + [55.7, 37.6], columns=['lat', 'lon'])
        st.map(pd.concat([geo_data, geo_data2]), color="#ef4444", zoom=3)
    else:
        st.warning("Нет данных для отображения.")

elif page == "🤖 Сравнение ML-моделей":
    st.header("Оценка baseline-моделей (Neural Networks & ML)")
    st.markdown("Здесь представлены результаты 5 различных моделей, обученных на извлеченных переписках для выявления целевой угрозы.")
    
    metrics_path = os.path.join("10_model_baselines", "model_metrics.csv")
    metrics_df = load_data(metrics_path)
    
    if not metrics_df.empty:
        st.subheader("Лидерборд Моделей")
        st.dataframe(
            metrics_df.style.background_gradient(cmap="Greens", subset=["F1-Score", "Accuracy"]),
            use_container_width=True
        )
        
        st.subheader("Визуальное сравнение (F1-Score)")
        fig = px.bar(
            metrics_df, 
            x='Model', 
            y='F1-Score', 
            color='Вердикт',
            text='F1-Score',
            color_discrete_map={
                "Отлично (Топ)": "#22c55e",
                "Хорошо": "#3b82f6",
                "Слабо": "#f97316",
                "Ужасно (Мусор)": "#ef4444"
            }
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(yaxis_range=[0,110])
        st.plotly_chart(fig, use_container_width=True)
        
        # Инсайт
        best_model = metrics_df.iloc[0]
        worst_model = metrics_df.iloc[-1]
        st.success(f"🏆 **Лучшая модель:** {best_model['Model']} (F1: {best_model['F1-Score']}%) — отлично справляется с задачей.")
        st.error(f"💩 **Худшая модель:** {worst_model['Model']} (F1: {worst_model['F1-Score']}%) — показывает отвратительные результаты ('говно').")
        
    else:
        st.warning("Метрики моделей еще не рассчитаны. Запустите скрипт `train_models.py` на сервере.")

elif page == "📁 Обозреватель данных":
    st.header("Обозреватель собранных данных")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Фильтры")
    
    files = {
        "Кандидаты (Диалоги)": "06_candidates/candidates.csv",
        "Ручная выборка": "07_manual_100/manual_sample_100.csv",
        "Ключевые слова": "01_keywords/keywords_approved.csv",
        "Источники": "02_sources/sources_approved.csv"
    }
    
    selected_file = st.selectbox("Выберите таблицу:", list(files.keys()))
    df = load_data(files[selected_file])
    
    if not df.empty:
        if 'language' in df.columns:
            langs = st.sidebar.multiselect("Язык (Language):", df['language'].unique(), default=df['language'].unique())
            df = df[df['language'].isin(langs)]
            
        if 'target_subtype' in df.columns:
            subtypes = st.sidebar.multiselect("Подвид угрозы:", df['target_subtype'].unique())
            if subtypes:
                df = df[df['target_subtype'].isin(subtypes)]
                
        st.dataframe(df, use_container_width=True)
        
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Скачать текущий датасет (CSV)",
            data=csv_data,
            file_name=f"{selected_file.lower().replace(' ', '_')}.csv",
            mime='text/csv',
            type="primary"
        )
    else:
        st.error("Файл не найден или пуст.")

elif page == "⚙️ Статус и Аудит":
    st.header("Контроль целостности и Аудит")
    
    col1, col2 = st.columns([2, 1])
    with col2:
        st.info("💡 Нажмите кнопку ниже, чтобы запустить `run.py` и проверить пайплайн.")
        if st.button("🚀 Запустить финальный аудит пайплайна", type="primary", use_container_width=True):
            with st.spinner("Сборка метрик и проверка файлов..."):
                try:
                    result = subprocess.run(
                        ["python", "run.py"], 
                        cwd=ROOT_DIR, 
                        capture_output=True, 
                        text=True,
                        check=True
                    )
                    st.session_state['audit_result'] = result.stdout
                except subprocess.CalledProcessError as e:
                    st.session_state['audit_result'] = e.output
    
    with col1:
        st.subheader("Результат оркестратора:")
        if 'audit_result' in st.session_state:
            if "NEXT_STAGE_ALLOWED                                                           YES" in st.session_state['audit_result']:
                st.success("✅ **ПАЙПЛАЙН ДОПУЩЕН:** Все метрики в норме (TARGET_THREAT > 70%, UNCERTAIN < 15%).")
            else:
                st.error("❌ **ПАЙПЛАЙН НЕ ПРОШЕЛ ПРОВЕРКУ:** Изучите логи ниже.")
            
            st.code(st.session_state['audit_result'], language="markdown")
        else:
            st.markdown("*Аудит еще не запускался в этой сессии.*")
