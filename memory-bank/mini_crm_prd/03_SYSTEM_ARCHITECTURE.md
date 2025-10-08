# Архитектура системы

## Компоненты
- **advanced_email_fetcher.py** — импорт по IMAP, сохранение JSON писем и вложений.
- **ocr_processor.py** — локальные экстракторы + Google Vision fallback.
- **extractor** — LLM‑оркестратор: формирование промпта, валидация JSON, нормализация, присвоение ID.
- **normalizer/deduper** — консолидация, фуззи‑мэтч, модерационный инбокс.
- **API** (FastAPI, Python) — REST/HTTP для фронтенда и интеграций.
- **Worker** (Celery/RQ) — очереди задач: импорт, OCR, LLM, дедуп, напоминания.
- **DB** (PostgreSQL через Supabase) — хранилище сущностей и индексов, бесплатный тариф.
Для подробных правил проектирования схемы см. документ [15_DB_MIGRATION_SAFE_SCHEMA.md](15_DB_MIGRATION_SAFE_SCHEMA.md).
Для интеграции с Supabase см. документ [16_SUPABASE_INTEGRATION.md](16_SUPABASE_INTEGRATION.md).
- **Storage** — папки `data/llm_results/` (обработанные JSON), `emails/` (JSON/EML) и `attachments/`.
- **Web** (React + PWA в Orchids.app) — интерфейс: поиск, карточки, реестр КП, модерация.

## Схема (ASCII)
```
IMAP → fetcher ─┬→ emails/*.json
                └→ attachments/*

attachments/* → ocr_processor → texts/*
emails+texts → extractor(LLM) → strict JSON → validator → normalizer/deduper
                                           └→ moderation inbox (low confidence)

DB(PostgreSQL/Supabase) ←─────────────── normalizer/deduper
                        ←─────────────── data/llm_results migration script

API(FastAPI) ⇄ Web(PWA React в Orchids.app)
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
- PostgreSQL через Supabase (бесплатный тариф), supabase-py для интеграции.
- React + Vite, TanStack Router/Query, Tailwind, PWA (Workbox) — разработка в Orchids.app.
- Контейнеризация: Docker Compose (api, worker, redis) или облачные платформы.

## Альтернативы и варианты размещения
- Локальный запуск (macOS) с ручным/автоматическим запуском через cron/launchd.
- Облачное размещение: Railway, Render, Fly.io, DigitalOcean App Platform, AWS Lambda + EventBridge.
- Подробнее см. [17_DEPLOYMENT_OPTIONS.md](17_DEPLOYMENT_OPTIONS.md).
