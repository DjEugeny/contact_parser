# Архитектура системы

## Компоненты
- **advanced_email_fetcher.py** — импорт по IMAP, сохранение JSON писем и вложений.
- **ocr_processor.py** — локальные экстракторы + Google Vision fallback.
- **extractor** — LLM‑оркестратор: формирование промпта, валидация JSON, нормализация, присвоение ID.
- **normalizer/deduper** — консолидация, фуззи‑мэтч, модерационный инбокс.
- **API** (FastAPI, Python) — REST/HTTP для фронтенда и интеграций, генерация XLSX.
- **Worker** (Celery/RQ) — очереди задач: импорт, OCR, LLM, дедуп, напоминания.
- **DB** (MySQL 8) — хранилище сущностей и индексов.
- **Storage** — папки `emails/` (JSON/EML) и `attachments/` на VPS.
- **Web** (React + PWA) — интерфейс: поиск, карточки, реестр КП, модерация.

## Схема (ASCII)
```
IMAP → fetcher ─┬→ emails/*.json
                └→ attachments/*

attachments/* → ocr_processor → texts/*
emails+texts → extractor(LLM) → strict JSON → validator → normalizer/deduper
                                           └→ moderation inbox (low confidence)

DB(MySQL) ←─────────────── normalizer/deduper
API(FastAPI) ⇄ Web(PWA React)
Worker(Celery/RQ) ⇄ Jobs (daily sync, reminders)
```

## Импорт и синхронизация
- **Backfill**: пакетами по дате (например, месяцами), начиная с новых к старым (для быстрых первых результатов).  
- **Инкрементально**: ежедневный cron (UTC 02:00) — выборка писем за прошедший день.
- Хранить `UID`/`Message-ID` для идемпотентности.

## Секреты/конфиг
- `.env`: IMAP_HOST, IMAP_USER, IMAP_PASS, DB_URL, GOOGLE_VISION_KEY, LLM_API_KEYS…
- Конфиги фильтров (JSON/YAML): blacklist отправителей/тем, whitelist типов вложений.

## Технологии (рекомендации)
- Python 3.11, FastAPI, SQLAlchemy, Alembic, Pydantic, Celery + Redis (опционально RQ).
- React + Vite, TanStack Router/Query, Tailwind, PWA (Workbox).
- Контейнеризация: Docker Compose (api, worker, db, redis, web, nginx).

## Альтернативы и почему не сейчас
- Postgres вместо MySQL — удобнее JSON/FTS, но для заданных поисков MySQL достаточен.
- Meilisearch — можно добавить позже для «живого» поиска, сейчас хватит SQL+индексы.
