# Модель данных (PostgreSQL через Supabase)

**Дата обновления:** 2025-06-10  
**Статус:** Актуально для PostgreSQL 15+ (Supabase)

## Таблицы (основные)

### users
- **id** SERIAL PRIMARY KEY
- **role** VARCHAR(20) CHECK (role IN ('admin', 'editor'))
- **email** VARCHAR(320) UNIQUE NOT NULL
- **password_hash** VARCHAR(255)
- **display_name** VARCHAR(200)
- **created_at** TIMESTAMP DEFAULT NOW()

### organizations
- **id** SERIAL PRIMARY KEY
- **gid** UUID UNIQUE — глобальный идентификатор для дедупликации (из data/llm_results)
- **name** VARCHAR(500) NOT NULL
- **inn** VARCHAR(20)
- **website** VARCHAR(500)
- **city** VARCHAR(200)
- **address** TEXT
- **created_at** TIMESTAMP DEFAULT NOW()
- **updated_at** TIMESTAMP DEFAULT NOW()
- **UNIQUE** (name, inn) WHERE inn IS NOT NULL — частичный уникальный индекс
- **INDEX** idx_organizations_city ON (city)
- **INDEX** idx_organizations_inn ON (inn)
- **INDEX** idx_organizations_gid ON (gid)

### organization_emails
- **id** SERIAL PRIMARY KEY
- **organization_id** INTEGER REFERENCES organizations(id) ON DELETE CASCADE
- **email** VARCHAR(320) NOT NULL
- **is_primary** BOOLEAN DEFAULT FALSE
- **UNIQUE** (email)
- **INDEX** idx_org_emails_org ON (organization_id)

### organization_phones
- **id** SERIAL PRIMARY KEY
- **organization_id** INTEGER REFERENCES organizations(id) ON DELETE CASCADE
- **e164** VARCHAR(20) — нормализованный формат E.164
- **raw** VARCHAR(50) — исходный формат
- **type** VARCHAR(20) DEFAULT 'main' CHECK (type IN ('main', 'office', 'fax', 'other'))
- **UNIQUE** (e164)
- **INDEX** idx_org_phones_org ON (organization_id)

### contacts
- **id** SERIAL PRIMARY KEY
- **gid** UUID UNIQUE — глобальный идентификатор для дедупликации (из data/llm_results)
- **organization_id** INTEGER REFERENCES organizations(id) ON DELETE SET NULL
- **full_name** VARCHAR(500) NOT NULL
- **position** VARCHAR(300)
- **city** VARCHAR(200)
- **address** TEXT
- **notes** TEXT
- **confidence** DECIMAL(3,2) DEFAULT 1.00
- **created_at** TIMESTAMP DEFAULT NOW()
- **updated_at** TIMESTAMP DEFAULT NOW()
- **INDEX** idx_contacts_organization ON (organization_id)
- **INDEX** idx_contacts_city ON (city)
- **INDEX** idx_contacts_gid ON (gid)
- **INDEX** idx_contacts_name_trgm ON (full_name) USING gin (full_name gin_trgm_ops) — для fuzzy search

### contact_emails
- **id** SERIAL PRIMARY KEY
- **contact_id** INTEGER REFERENCES contacts(id) ON DELETE CASCADE
- **email** VARCHAR(320) NOT NULL
- **is_primary** BOOLEAN DEFAULT FALSE
- **UNIQUE** (email)
- **INDEX** idx_contact_emails_contact ON (contact_id)

### contact_phones
- **id** SERIAL PRIMARY KEY
- **contact_id** INTEGER REFERENCES contacts(id) ON DELETE CASCADE
- **e164** VARCHAR(20) — нормализованный формат E.164
- **raw** VARCHAR(50) — исходный формат
- **type** VARCHAR(20) DEFAULT 'other' CHECK (type IN ('main', 'work', 'mobile', 'fax', 'other'))
- **UNIQUE** (e164)
- **INDEX** idx_contact_phones_contact ON (contact_id)

### emails
- **id** SERIAL PRIMARY KEY
- **message_id** VARCHAR(500) UNIQUE NOT NULL
- **imap_uid** VARCHAR(100)
- **imap_folder** VARCHAR(200)
- **from_addr** VARCHAR(320)
- **to_addrs** JSONB — массив адресов получателей
- **cc_addrs** JSONB — массив адресов в копии
- **subject** TEXT
- **date** TIMESTAMP
- **path_json** TEXT — путь к JSON файлу письма
- **path_eml** TEXT — путь к EML файлу (опционально)
- **has_attachments** BOOLEAN DEFAULT FALSE
- **created_at** TIMESTAMP DEFAULT NOW()
- **INDEX** idx_emails_date ON (date)
- **INDEX** idx_emails_from ON (from_addr)
- **INDEX** idx_emails_message_id ON (message_id)

### attachments
- **id** SERIAL PRIMARY KEY
- **email_id** INTEGER REFERENCES emails(id) ON DELETE CASCADE
- **filename** VARCHAR(500)
- **mime** VARCHAR(200)
- **size_bytes** BIGINT
- **path_file** TEXT — путь к файлу вложения
- **ocr_text_path** TEXT — путь к извлеченному тексту
- **has_text** BOOLEAN DEFAULT FALSE
- **checksum** VARCHAR(64) — SHA256 для дедупликации
- **INDEX** idx_attachments_email ON (email_id)
- **INDEX** idx_attachments_checksum ON (checksum)

### interactions
- **id** SERIAL PRIMARY KEY
- **contact_id** INTEGER REFERENCES contacts(id) ON DELETE CASCADE
- **organization_id** INTEGER REFERENCES organizations(id) ON DELETE CASCADE
- **email_id** INTEGER REFERENCES emails(id) ON DELETE SET NULL
- **when_at** TIMESTAMP NOT NULL
- **role** VARCHAR(50) CHECK (role IN ('sender', 'recipient', 'requested_quote', 'sent_quote', 'complaint', 'info_request', 'clarification', 'other'))
- **summary** TEXT
- **message_id_hint** VARCHAR(500) — для дедупликации взаимодействий
- **created_at** TIMESTAMP DEFAULT NOW()
- **INDEX** idx_interactions_contact ON (contact_id)
- **INDEX** idx_interactions_organization ON (organization_id)
- **INDEX** idx_interactions_when ON (when_at)
- **INDEX** idx_interactions_message_id ON (message_id_hint)

### commercial_offers
- **id** SERIAL PRIMARY KEY
- **organization_id** INTEGER REFERENCES organizations(id) ON DELETE SET NULL
- **end_user** VARCHAR(500)
- **end_user_inn** VARCHAR(20)
- **intermediary** VARCHAR(500)
- **offer_number** VARCHAR(100)
- **offer_date** DATE
- **offer_type** VARCHAR(50) CHECK (offer_type IN ('Приборы', 'Наборы', 'Другое'))
- **payment_terms** TEXT
- **delivery_time** VARCHAR(200)
- **delivery_terms** TEXT
- **valid_until** DATE
- **total_cost** DECIMAL(18,2)
- **comments** TEXT
- **source_email_id** INTEGER REFERENCES emails(id) ON DELETE SET NULL
- **status** VARCHAR(50) DEFAULT 'на_рассмотрении' CHECK (status IN ('на_рассмотрении', 'согласовано', 'закрыто', 'отклонено'))
- **created_at** TIMESTAMP DEFAULT NOW()
- **updated_at** TIMESTAMP DEFAULT NOW()
- **INDEX** idx_offers_organization ON (organization_id)
- **INDEX** idx_offers_valid_until ON (valid_until)
- **INDEX** idx_offers_date ON (offer_date)
- **INDEX** idx_offers_status ON (status)

### commercial_offer_items
- **id** SERIAL PRIMARY KEY
- **offer_id** INTEGER REFERENCES commercial_offers(id) ON DELETE CASCADE
- **name** VARCHAR(500)
- **model** VARCHAR(200)
- **article** VARCHAR(200)
- **quantity** INTEGER
- **unit_price** DECIMAL(18,2)
- **vat** VARCHAR(8)
- **total_price** DECIMAL(18,2)
- **INDEX** idx_offer_items_offer ON (offer_id)

### reminders
- **id** SERIAL PRIMARY KEY
- **offer_id** INTEGER REFERENCES commercial_offers(id) ON DELETE CASCADE
- **remind_at** TIMESTAMP NOT NULL
- **sent_at** TIMESTAMP
- **note** TEXT
- **INDEX** idx_reminders_remind_at ON (remind_at)
- **INDEX** idx_reminders_offer ON (offer_id)

### moderation_queue
- **id** SERIAL PRIMARY KEY
- **entity_type** VARCHAR(50) CHECK (entity_type IN ('contact', 'organization', 'offer'))
- **entity_payload** JSONB NOT NULL
- **reason** TEXT
- **confidence** DECIMAL(3,2)
- **created_at** TIMESTAMP DEFAULT NOW()
- **INDEX** idx_moderation_created ON (created_at)
- **INDEX** idx_moderation_type ON (entity_type)

## Ключевые индексы и оптимизации

### Индексы для быстрого поиска
- **organizations.gid** — для дедупликации при синхронизации
- **contacts.gid** — для дедупликации при синхронизации
- **contact_emails.email** — для поиска контактов по email
- **contact_phones.e164** — для поиска контактов по телефону
- **organizations.inn** — для поиска организаций по ИНН
- **organizations.city** — для фильтрации по городу
- **commercial_offers.valid_until** — для напоминаний об истекающих КП
- **interactions.message_id_hint** — для дедупликации взаимодействий

### Полнотекстовый поиск (опционально)
Для fuzzy search по именам контактов можно использовать расширение `pg_trgm`:

```sql
-- Включение расширения
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Создание GIN индекса для триграмного поиска
CREATE INDEX idx_contacts_name_trgm ON contacts USING gin (full_name gin_trgm_ops);

-- Пример поиска с опечатками
SELECT * FROM contacts WHERE full_name % 'Воронова';  -- найдет "Воронова", "Воронов" и т.д.
```

## Отличия от MySQL

### 1. ENUM типы
В PostgreSQL ENUM нужно создавать явно или использовать CHECK constraints:

```sql
-- Вариант 1: CHECK constraint (используется в схеме выше)
ALTER TABLE users ADD CONSTRAINT check_role CHECK (role IN ('admin', 'editor'));

-- Вариант 2: CREATE TYPE (альтернатива)
CREATE TYPE user_role AS ENUM ('admin', 'editor');
ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::user_role;
```

### 2. UNIQUE с NULL
В MySQL: `UNIQUE (name, inn) NULLS DISTINCT`  
В PostgreSQL: `UNIQUE (name, inn) WHERE inn IS NOT NULL` (частичный индекс)

### 3. JSON vs JSONB
PostgreSQL использует **JSONB** (бинарный JSON) вместо JSON:
- Быстрее для запросов
- Поддержка индексов GIN
- Автоматическая валидация

### 4. AUTO_INCREMENT vs SERIAL
MySQL: `id INT AUTO_INCREMENT`  
PostgreSQL: `id SERIAL` (эквивалент `INTEGER NOT NULL DEFAULT nextval('sequence')`)

### 5. DATETIME vs TIMESTAMP
MySQL: `DATETIME`  
PostgreSQL: `TIMESTAMP` или `TIMESTAMP WITH TIME ZONE` (рекомендуется)

## SQL для создания схемы

Полный SQL для создания всех таблиц см. в документе [16_SUPABASE_INTEGRATION.md](16_SUPABASE_INTEGRATION.md), раздел 3.2.

## Миграция данных

Для миграции существующих данных из `data/llm_results/` в PostgreSQL см. документ [18_DATA_SYNC_AND_DEDUPLICATION.md](18_DATA_SYNC_AND_DEDUPLICATION.md).
