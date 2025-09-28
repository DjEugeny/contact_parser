# API Pipeline Validator (обновлённые режимы)

> **Mini-CRM / Mini Pipeline** – тонкий слой над `ContactExtractor`, собранный для проверки end-to-end конвейера перед переходом на `main_new.py`.

## 🎯 Назначение
- Сквозной прогон цепочки **Email → OCR → LLM → PostProcessing** на локальном датасете.
- Генерация артефактов в формате JSON/Markdown для экспресс-проверки результатов.
- Подготовка данных для дальнейшей загрузки в `crm.db` и Google Sheets.
- Отчётность и контроль качества перед переключением на полноценный пайплайн (`main_new.py`).

## 🚀 Основные режимы CLI
```bash
python api_pipeline_validator.py --mode first10
python api_pipeline_validator.py --mode batch --date 2025-07-29 --count 20
python api_pipeline_validator.py --mode range --start 2025-05-01 --end 2025-05-05
python api_pipeline_validator.py --mode batch --date 2025-07-29 --count 10 --dry-run
```

Параметры:
- `--mode`: `first10` (тестовая выборка), `batch` (N писем за дату), `range` (диапазон дат).
- `--date`: дата в формате `YYYY-MM-DD` (для режима `batch`).
- `--count`: лимит обработанных писем (по умолчанию 10).
- `--start`, `--end`: границы диапазона (для режима `range`).
- `--dry-run`: отключает запись в БД (оставляет только артефакты).

## 🧱 Архитектура (тонкий слой)
```
ProcessedEmailLoader → OCR Manager → ContactExtractor (LLM)
                                ↘ PostProcessor (нормализация/дедуп/обогащение)
                                   ↘ ReportGenerator (JSON/Markdown + summary)
```

- **Email загрузка**: `ProcessedEmailLoader` читает JSON из `data/emails/YYYY-MM-DD/email_*.json`.
- **OCR**: `get_ocr_manager()` извлекает текст вложений, если в `attachments[].content` нет готового текста.
- **LLM-извлечение**: `ContactExtractor.create_extractor(test_mode=False)` с промптом `unified_contact_extraction_structured.txt`.
- **Постобработка**: встроенный `PostProcessor` реализует правила `11_DEDUP_ENRICH_RULES.md`.
- **Отчётность**: новый `src/reporting/report_generator.py` сохраняет пару артефактов на письмо + агрегированный summary по запуску.

## 📦 Артефакты
После каждого запуска формируются:
- `data/llm_results/YYYY-MM-DD/` – директория запуска (создаётся автоматически).
  - `<slug>_<run>_<timestamp>_raw.json` – сырой ответ LLM (из `raw_llm_result`).
  - `<slug>_<run>_<timestamp>_processed.json` – постобработанный результат (готовый для записи в БД).
  - `<slug>_<run>_<timestamp>.md` – Markdown-отчёт по письму (метаданные, summary, таблицы организаций/контактов/КП/интеракций).
  - `_summary_<run>.json|md` – сводка запуска (агрегированная статистика, ссылки на отчёты).
  - `index.md` – консолидированный индекс всех запусков по дате (обновляется автоматически).
- `memory-bank/reports/index.md` – дополняется ссылкой на свежую сводку (для хронологии экспериментов).
- Логи процессов записываются через `CentralizedLogger` (`data/logs/pipeline.log`, `data/logs/errors.log`).

## ✅ Валидация & Логика успеха
- `ReportGenerator` считывает флаг `success` из результата; если поля пустые, но ошибок нет – считается успешным, однако итоговый отчёт выделяет пустые секции.
- Сводка отражает количество найденных `organizations`, `contacts`, `commercial_offers`, `interactions` и время прогонов.
- При ошибках генератор фиксирует их в `failures[]`, а Markdown отчёт маркирует блок **Диагностика**.

## 🔄 Idempotency & Fallbacks
- Имена артефактов включают `run_id` и `timestamp`, поэтому повторные запуски не перезаписывают существующие файлы.
- У записи артефактов есть fallback-директория `data/llm_results/_failed_reports/` на случай ошибок записи.
- OCR-пайплайн использует готовый текст, а при необходимости автоматически вызывает `get_ocr_manager()`.

## 🧪 Порядок запуска MVP
1. `--mode first10` – проверяем промпт/валидацию на эталонной выборке (`memory-bank/test_dataset_10_emails.md`).
2. `--mode batch` – масштабируемся на 20+ писем (контроль качества и дедуп правил).
3. `--mode range` – прогон нескольких дней подряд, получаем consolidated summary.
4. После стабилизации включаем запись в `crm.db` (см. ниже TO-DO) и переходим к `main_new.py` (`full-pipeline`, `async-*`).

## ⚠️ Текущие TODO
- Реализовать модуль записи в SQLite (`crm.db`) с отражением таблиц: `organizations`, `contacts`, `contact_phones`, `commercial_offers`, `interactions`, `moderation_inbox`.
- Интегрировать экспорт в Google Sheets (по `10_GOOGLE_SHEETS_INTERIM.md`).
- Добавить автотесты для `ReportGenerator` и smoke-тесты режимов `first10`/`batch`.
- Подключить Inbox/Moderation поток после внедрения scoring.

## 🔗 Полезные ссылки
- PRD / требования: `memory-bank/mini_crm_prd/`
- Обновлённый промпт: `prompts/unified_contact_extraction_structured.txt`
- PostProcessing: `src/postprocessing/postprocessor.py`
- Отчётность: `src/reporting/report_generator.py`
- Основной пайплайн: `src/main_new.py`
