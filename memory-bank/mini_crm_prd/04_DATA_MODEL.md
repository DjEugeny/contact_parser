# Модель данных (MySQL 8)

## Таблицы (основные)
### users
- id (PK), role ENUM('admin','editor'), email UNIQUE, password_hash?, display_name

### organizations
- id (PK), name, inn, website, city, address, created_at, updated_at
- UNIQUE (name, inn) NULLS DISTINCT
- INDEX city, inn

### contacts
- id (PK), organization_id (FK), full_name, position, city, address, notes, confidence DECIMAL(3,2), created_at, updated_at
- INDEX (organization_id), INDEX (city), FULLTEXT(full_name) optional

### contact_emails
- id, contact_id (FK), email, is_primary BOOL, UNIQUE(email)

### contact_phones
- id, contact_id (FK), e164, raw, type ENUM('main','work','mobile','fax','other'), UNIQUE(e164)

### emails
- id (PK), message_id UNIQUE, imap_uid, imap_folder, from_addr, to_addrs JSON, cc_addrs JSON, subject, date, path_json, path_eml, has_attachments BOOL
- INDEX (date), INDEX (from_addr)

### attachments
- id (PK), email_id (FK), filename, mime, size_bytes, path_file, ocr_text_path, has_text BOOL, checksum
- INDEX (email_id)

### interactions
- id (PK), contact_id (FK), organization_id (FK), email_id (FK), when_at DATETIME, role ENUM('sender','recipient','requested_quote','sent_quote','complaint','info_request','other'), summary TEXT
- INDEX (contact_id), INDEX (organization_id), INDEX (when_at)

### commercial_offers
- id (PK), organization_id (FK), end_user, end_user_inn, intermediary, offer_number, offer_date DATE, offer_type ENUM('Приборы','Наборы','Другое'), payment_terms, delivery_time, delivery_terms, valid_until DATE, total_cost DECIMAL(18,2), comments, source_email_id (FK), status ENUM('на_рассмотрении','согласовано','закрыто','отклонено') DEFAULT 'на_рассмотрении'
- INDEX (organization_id), INDEX (valid_until), INDEX (offer_date), INDEX (status)

### commercial_offer_items
- id (PK), offer_id (FK), name, model, article, quantity INT, unit_price DECIMAL(18,2), vat VARCHAR(8), total_price DECIMAL(18,2)

### reminders
- id (PK), offer_id (FK), remind_at DATETIME, sent_at DATETIME NULL, note

### moderation_queue
- id (PK), entity_type ENUM('contact','organization','offer'), entity_payload JSON, reason, confidence DECIMAL(3,2), created_at

## Ключевые индексы
- contacts(email via contact_emails.email), contacts(phone via contact_phones.e164), organizations(inn), organizations(city), offers(valid_until, status).
