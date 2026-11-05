# Cyber Threat Dataset (Theme 8: HARMFUL_INFLUENCE)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://cyberthreatdataset-cxgqds78wopgau9kkchtks.streamlit.app/)
[![Dataset Release](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](https://github.com/Aleks-48/cyber_threat_dataset/releases/tag/v1.0.0)
[![Audit Status](https://img.shields.io/badge/Audit-PASSED-brightgreen.svg)](09_verdict/stage_verdict.json)
[![License](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

Официальный репозиторий набора данных **Cyber Threat Dataset** (Тема 8: Вредоносное влияние / *HARMFUL_INFLUENCE*).

Датасет содержит **ровно 13 500 проверенных уникальных сообщений без повторов** (`unique_text_count = 13500`, `duplicate_text_rate = 0.0`), охватывающих 9 ключевых групп угроз в русскоязычном, казахскоязычном и смешанном (RU/KK) сегментах общения.

---

## Быстрый старт: запуск интерактивного Streamlit дашборда

```bash
git clone https://github.com/Aleks-48/cyber_threat_dataset.git
cd cyber_threat_dataset
pip install -r requirements.txt
streamlit run web_app.py
```

Дашборд предоставляет:
- Просмотр всех 13 500 записей с гибкой фильтрацией по 9 группам угроз, языку и источникам;
- Поиск по ключевым словам и тексту сообщений;
- Выгрузку отфильтрованных выборок и полного датасета в один клик;
- Матрицы распределения и графики аналитики;
- Отчет аудита качества и сравнение моделей машинного обучения.

---

## Структура набора данных (13 500 записей)

| № | Группа угрозы (`target_subtype`) | Описание тематики | RU | KK | MIXED | Всего |
|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | `EXTREMIST_PROPAGANDA` | Радикальные призывы, пропаганда джихада, отрицание светских законов | 500 | 500 | 500 | **1 500** |
| 2 | `EXTREMIST_RECRUITMENT` | Прямая вербовка в ячейки и джамааты, присяга амиру | 500 | 500 | 500 | **1 500** |
| 3 | `VIOLENCE_GLORIFICATION` | Героизация стрелков, скулшутинг, колумбайн, культ жестокости | 500 | 500 | 500 | **1 500** |
| 4 | `DANGEROUS_CHALLENGE` | Опасные игры, зацепинг на поездах, руфинг на высотках, «собачий кайф» | 500 | 500 | 500 | **1 500** |
| 5 | `SELF_HARM_ENCOURAGEMENT` | Склонение к селфхарму, шрамирование, порезы, эстетизация ран | 500 | 500 | 500 | **1 500** |
| 6 | `SUICIDE_ENCOURAGEMENT` | Деструктивные игры («Синий кит», «Тихий дом»), кураторы, 4:20 | 500 | 500 | 500 | **1 500** |
| 7 | `CRIMINAL_RECRUITMENT` | Вербовка курьеров-закладчиков, дропперство карт, обнал крипты | 500 | 500 | 500 | **1 500** |
| 8 | `GROUP_LOYALTY_PRESSURE` | Психологический шантаж, проверка преданности, угрозы за выход | 500 | 500 | 500 | **1 500** |
| 9 | `SECRET_COMMUNICATION_REQUEST` | Требования конспирации, удаление переписок, переход в Threema/Session | 500 | 500 | 500 | **1 500** |
| **ИТОГО** | **9 целевых групп** | **Полный сбалансированный корпус** | **4 500** | **4 500** | **4 500** | **13 500** |

---

## Прямые ссылки на скачивание (Релиз v1.0.0)

- 📥 [Скачать в формате CSV (13 500 строк)](https://github.com/Aleks-48/cyber_threat_dataset/releases/download/v1.0.0/cyber_threat_dataset_13500_unique.csv) (~6.2 МБ)
- 📥 [Скачать в формате JSONL (13 500 объектов)](https://github.com/Aleks-48/cyber_threat_dataset/releases/download/v1.0.0/cyber_threat_dataset_13500_unique.jsonl) (~7.1 МБ)
- 📦 [Страница официального релиза v1.0.0 на GitHub](https://github.com/Aleks-48/cyber_threat_dataset/releases/tag/v1.0.0)

---

## Результаты аудита качества

Все проверки пайплайна (`audit.py`, `stage_verdict.json`) успешно пройдены:
- **Уникальность текстов:** 13 500 / 13 500 (`duplicate_text_rate = 0.0`);
- **Подтверждение сырыми данными:** 13 500 совпадений в `raw_harvest_snapshot.jsonl`;
- **Языковая согласованность:** 0 конфликтов языковых меток;
- **Экспертная выборка (900 диалогов):** доля `TARGET_THREAT` = 74.0% (порог $\ge 70\%$), `UNCERTAIN` = 5.0% (порог $\le 15\%$);
- **Блокирующие причины:** 0;
- **Финальный вердикт:** `next_stage_allowed: true`.
