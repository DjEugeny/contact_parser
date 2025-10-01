# TECHNICAL_SPECIFICATION — Техническое задание (обновлено кратко)

## Архитектура и стек
- ETL: **EmailFetcher → OCR → LLM → Postprocess → SQLite → API → Frontend**.
- **SQLite** на MVP, миграция на **Postgres** возможна без изменения моделей домена.
- **Backend:** FastAPI; **Frontend:** React (PWA).

## Схема БД (SQLite)
- `organizations(id, name, inn, website, city, address, created_at)`  
- `contacts(id, name, organization_id, position, email, created_at)`  
- `contact_phones(id, contact_id, phone_type, phone_number)` — массив телефонов переносится сюда.  
- `commercial_offers(id, offer_number, offer_date, valid_until, total_cost, status, end_user_id, intermediary_id, source_message_id)`  
- `interactions(id, contact_id, organization_id, interaction_type, interaction_date, summary, source_message_id, created_at)`

## API (FastAPI, минимальный набор)
- `GET /search?q=&city=&inn=&email=&phone=` — общий поиск.  
- `GET /contacts/{id}` / `GET /organizations/{id}` — карточки.  
- `GET /commercial_offers?status=&date_from=&date_to=` — реестр КП.  
- `POST /contacts/{id}/notes` — заметка.  
- `POST /moderation/accept|reject` — действия по Inbox.

## Конвейер
- Переиспользуем существующие **fetcher/OCR**, обновляем **Extractor** под единый промпт и новую схему, добавляем постобработку/SQLite‑writer.

## Database Migration Considerations

Для обеспечения лёгкой миграции с MySQL на PostgreSQL создан отдельный документ:  
[15_DB_MIGRATION_SAFE_SCHEMA.md](15_DB_MIGRATION_SAFE_SCHEMA.md).

Документ содержит:
- рекомендации по выбору типов данных;
- правила задания ключей и индексов;
- запреты на использование MySQL-специфичных возможностей;
- рекомендации по миграции и будущим расширениям (JSONB, FTS, pg_trgm).

Соблюдение этих правил гарантирует, что при переходе на PostgreSQL архитектура и код потребуют минимальных изменений.

