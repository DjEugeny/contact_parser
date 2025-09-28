# 12_API_PIPELINE_VALIDATOR — Техническое задание на тестовый раннер

## Назначение
Скрипт для **сквозного теста**: загрузка писем → OCR → LLM → постобработка → запись в SQLite → (опционально) экспорт в Sheets. Используется для итеративной отладки промптов/правил и оценки качества.

## CLI
```
python api_pipeline_validator.py --mode first10 --date 2025-05-05
python api_pipeline_validator.py --mode batch --count 20 --date 2025-05-05
python api_pipeline_validator.py --mode range --start 2025-05-05 --end 2025-05-12
python api_pipeline_validator.py --dry-run
```
- `--dry-run` — выполняет всё до записи в БД, сохраняет промежуточные JSON в `data/llm_results/...`

## Логика
1. **Загрузка писем/вложений** (reuse существующего fetcher; фильтры/блэк‑листы уже есть).  
2. **OCR** (reuse существующего модуля).  
3. **LLM** (обновлённый промпт) → сохранить сырой JSON.  
4. **Валидация/нормализация/дедуп/обогащение** (см. `11_DEDUP_ENRICH_RULES.md`).  
5. **SQLite** (`crm.db`): вставка/обновление `organizations`, `contacts`, `contact_phones`, `commercial_offers`, `interactions`.  
6. **Отчёт**: суммарная статистика + список сомнительных в Inbox.

## Выходные артефакты
- `crm.db` — центральная БД.  
- `data/llm_results/DATE/*.json` — сырые ответы.
- `data/llm_results/DATE/*.md` — отчёты по каждому письму для быстрого просмотра результатов.    
- Логи: `data/logs/pipeline_*.log` (ошибки/предупреждения/время).

## Примечания по реализации
- Потокобезопасное авто‑назначение **глобальных organization_id**.  
- Повторяемые запуски не должны плодить дубли (idempotency).  
- Параллелизация LLM‑вызовов после стабилизации качества.


## Связь с main_new.py (тонкий слой и хендовер)
- `api_pipeline_validator.py` — **тонкий слой** над конвейером `main_new.py`: переиспользует его функции и DI, добавляя CLI-режимы `first10/batch/range` и артефакты (crm.db, llm_results, Inbox).
- После успешных итераций на тестовом наборе переключаемся на **основной запуск через `main_new.py`** (режимы `interactive/test/full-pipeline/async-*`).
- Требование: общая бизнес-логика извлечения/валидации/дедупа должна жить в отдельных модулях, чтобы не дублировать код между `api_pipeline_validator.py` и `main_new.py`.
