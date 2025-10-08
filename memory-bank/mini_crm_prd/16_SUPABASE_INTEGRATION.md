# 16_SUPABASE_INTEGRATION — Интеграция с PostgreSQL через Supabase

**Дата:** 2025-06-10  
**Статус:** Актуально

## 1. Обзор

Проект использует PostgreSQL через платформу Supabase (бесплатный тариф) вместо локальной SQLite базы данных. Это обеспечивает:
- Облачное хранилище данных с автоматическими бэкапами
- Готовый REST API и Realtime subscriptions
- Встроенную аутентификацию (опционально)
- Возможность доступа к данным из веб-приложения в Orchids.app

## 2. Настройка Supabase

### 2.1. Создание проекта
1. Зарегистрироваться на https://supabase.com
2. Создать новый проект (выбрать регион ближе к вашему местоположению)
3. Дождаться инициализации проекта (~2 минуты)
4. Сохранить учетные данные:
   - `Project URL` (например: https://xxxxx.supabase.co)
   - `API Key` (anon/public key)
   - `Service Role Key` (для серверных операций)
   - `Database Password` (для прямого подключения через PostgreSQL)

### 2.2. Параметры подключения
Supabase предоставляет несколько способов подключения:

**Вариант 1: Через Supabase Python Client (рекомендуется для простых операций)**
```python
from supabase import create_client, Client

url = "https://xxxxx.supabase.co"
key = "your-anon-key"
supabase: Client = create_client(url, key)
```

**Вариант 2: Через psycopg2 (для более сложных операций)**
```python
from sqlalchemy import create_engine

DATABASE_URL = "postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres"
engine = create_engine(DATABASE_URL)
```

### 2.3. Переменные окружения (.env)
```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...
SUPABASE_DB_PASSWORD=your-db-password

# Для прямого подключения PostgreSQL
DATABASE_URL=postgresql://postgres:${SUPABASE_DB_PASSWORD}@db.xxxxx.supabase.co:5432/postgres
```

## 3. Применение схемы БД
### 3.1. Создание таблиц
Используйте SQL Editor в Supabase Dashboard или миграции Alembic.

Через Supabase Dashboard:

1. Перейти в SQL Editor
2. Скопировать SQL из раздела 3.2
3. Выполнить запрос

Через Alembic (рекомендуется для версионирования):
```bash
# Инициализация Alembic
alembic init alembic

# Создание миграции
alembic revision --autogenerate -m "Initial schema"

# Применение миграции
alembic upgrade head
```

### 3.2. SQL схема (базовая версия)
-- Организации
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    inn VARCHAR(20),
    website VARCHAR(500),
    city VARCHAR(200),
    address TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, inn)
);

CREATE INDEX idx_organizations_city ON organizations(city);
CREATE INDEX idx_organizations_inn ON organizations(inn);

-- Контакты
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    full_name VARCHAR(500) NOT NULL,
    position VARCHAR(300),
    city VARCHAR(200),
    address TEXT,
    notes TEXT,
    confidence DECIMAL(3,2) DEFAULT 1.00,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_contacts_organization ON contacts(organization_id);
CREATE INDEX idx_contacts_city ON contacts(city);

-- Email контактов
CREATE TABLE contact_emails (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    email VARCHAR(320) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    UNIQUE(email)
);

CREATE INDEX idx_contact_emails_contact ON contact_emails(contact_id);

-- Телефоны контактов
CREATE TABLE contact_phones (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    e164 VARCHAR(20),
    raw VARCHAR(50),
    type VARCHAR(20) DEFAULT 'other',
    UNIQUE(e164)
);

CREATE INDEX idx_contact_phones_contact ON contact_phones(contact_id);

-- Письма
CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(500) UNIQUE NOT NULL,
    imap_uid VARCHAR(100),
    imap_folder VARCHAR(200),
    from_addr VARCHAR(320),
    to_addrs JSONB,
    cc_addrs JSONB,
    subject TEXT,
    date TIMESTAMP,
    path_json TEXT,
    path_eml TEXT,
    has_attachments BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_emails_date ON emails(date);
CREATE INDEX idx_emails_from ON emails(from_addr);
CREATE INDEX idx_emails_message_id ON emails(message_id);

-- Вложения
CREATE TABLE attachments (
    id SERIAL PRIMARY KEY,
    email_id INTEGER REFERENCES emails(id) ON DELETE CASCADE,
    filename VARCHAR(500),
    mime VARCHAR(200),
    size_bytes BIGINT,
    path_file TEXT,
    ocr_text_path TEXT,
    has_text BOOLEAN DEFAULT FALSE,
    checksum VARCHAR(64)
);

CREATE INDEX idx_attachments_email ON attachments(email_id);

-- Взаимодействия
CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    email_id INTEGER REFERENCES emails(id) ON DELETE SET NULL,
    when_at TIMESTAMP NOT NULL,
    role VARCHAR(50),
    summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_interactions_contact ON interactions(contact_id);
CREATE INDEX idx_interactions_organization ON interactions(organization_id);
CREATE INDEX idx_interactions_when ON interactions(when_at);

-- Коммерческие предложения
CREATE TABLE commercial_offers (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    end_user VARCHAR(500),
    end_user_inn VARCHAR(20),
    intermediary VARCHAR(500),
    offer_number VARCHAR(100),
    offer_date DATE,
    offer_type VARCHAR(50),
    payment_terms TEXT,
    delivery_time VARCHAR(200),
    delivery_terms TEXT,
    valid_until DATE,
    total_cost DECIMAL(18,2),
    comments TEXT,
    source_email_id INTEGER REFERENCES emails(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'на_рассмотрении',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_offers_organization ON commercial_offers(organization_id);
CREATE INDEX idx_offers_valid_until ON commercial_offers(valid_until);
CREATE INDEX idx_offers_date ON commercial_offers(offer_date);
CREATE INDEX idx_offers_status ON commercial_offers(status);

-- Позиции КП
CREATE TABLE commercial_offer_items (
    id SERIAL PRIMARY KEY,
    offer_id INTEGER REFERENCES commercial_offers(id) ON DELETE CASCADE,
    name VARCHAR(500),
    model VARCHAR(200),
    article VARCHAR(200),
    quantity INTEGER,
    unit_price DECIMAL(18,2),
    vat VARCHAR(8),
    total_price DECIMAL(18,2)
);

CREATE INDEX idx_offer_items_offer ON commercial_offer_items(offer_id);

-- Напоминания
CREATE TABLE reminders (
    id SERIAL PRIMARY KEY,
    offer_id INTEGER REFERENCES commercial_offers(id) ON DELETE CASCADE,
    remind_at TIMESTAMP NOT NULL,
    sent_at TIMESTAMP,
    note TEXT
);

CREATE INDEX idx_reminders_remind_at ON reminders(remind_at);

-- Очередь модерации
CREATE TABLE moderation_queue (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_payload JSONB NOT NULL,
    reason TEXT,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_moderation_created ON moderation_queue(created_at);

## 4. Миграция данных из data/llm_results
### 4.1. Структура данных в llm_results
Файлы в data/llm_results/YYYY-MM-DD/ содержат:

- email_NNN_*_processed.json — результаты обработки LLM для каждого письма
- _summary_*.json — сводные отчеты по батчу
- reports/*.md — markdown отчеты для просмотра

### 4.2. Скрипт миграции (migrate_llm_results_to_supabase.py)
Основные шаги:

1. Сканировать директорию data/llm_results/
2. Для каждого *_processed.json:
- Прочитать JSON
- Извлечь organizations, contacts, commercial_offers
- Применить валидацию и нормализацию
- Выполнить дедупликацию (проверка по inn, email, phone)
- Записать в Supabase
3. Логировать результаты и ошибки

Пример структуры скрипта:
import os
import json
from pathlib import Path
from supabase import create_client
from datetime import datetime

# Инициализация Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def migrate_llm_results(results_dir="data/llm_results"):
    """Миграция всех обработанных JSON файлов в Supabase"""
    
    processed_files = []
    errors = []
    
    # Сканирование директорий по датам
    for date_dir in Path(results_dir).iterdir():
        if not date_dir.is_dir():
            continue
            
        # Обработка файлов
        for json_file in date_dir.glob("email_*_processed.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Обработка организаций
                for org in data.get('organizations', []):
                    upsert_organization(org)
                
                # Обработка контактов
                for contact in data.get('contacts', []):
                    upsert_contact(contact)
                
                # Обработка КП
                for offer in data.get('commercial_offers', []):
                    upsert_commercial_offer(offer)
                
                processed_files.append(str(json_file))
                
            except Exception as e:
                errors.append({"file": str(json_file), "error": str(e)})
    
    return {
        "processed": len(processed_files),
        "errors": len(errors),
        "error_details": errors
    }

def upsert_organization(org_data):
    """Вставка или обновление организации с дедупликацией"""
    
    # Проверка существования по ИНН
    if org_data.get('inn'):
        existing = supabase.table('organizations')\
            .select('id')\
            .eq('inn', org_data['inn'])\
            .execute()
        
        if existing.data:
            # Обновление существующей
            supabase.table('organizations')\
                .update(org_data)\
                .eq('id', existing.data[0]['id'])\
                .execute()
            return existing.data[0]['id']
    
    # Вставка новой
    result = supabase.table('organizations').insert(org_data).execute()
    return result.data[0]['id']

def upsert_contact(contact_data):
    """Вставка или обновление контакта с дедупликацией"""
    
    # Проверка существования по email
    emails = contact_data.pop('emails', [])
    if emails:
        existing = supabase.table('contact_emails')\
            .select('contact_id')\
            .eq('email', emails[0])\
            .execute()
        
        if existing.data:
            # Обновление существующего
            contact_id = existing.data[0]['contact_id']
            supabase.table('contacts')\
                .update(contact_data)\
                .eq('id', contact_id)\
                .execute()
            return contact_id
    
    # Вставка нового контакта
    result = supabase.table('contacts').insert(contact_data).execute()
    contact_id = result.data[0]['id']
    
    # Вставка emails
    for email in emails:
        supabase.table('contact_emails').insert({
            'contact_id': contact_id,
            'email': email,
            'is_primary': emails.index(email) == 0
        }).execute()
    
    return contact_id

def upsert_commercial_offer(offer_data):
    """Вставка КП"""
    
    items = offer_data.pop('items', [])
    
    # Вставка КП
    result = supabase.table('commercial_offers').insert(offer_data).execute()
    offer_id = result.data[0]['id']
    
    # Вставка позиций
    for item in items:
        item['offer_id'] = offer_id
        supabase.table('commercial_offer_items').insert(item).execute()
    
    return offer_id

if __name__ == "__main__":
    print("Начало миграции данных из data/llm_results...")
    result = migrate_llm_results()
    print(f"Обработано файлов: {result['processed']}")
    print(f"Ошибок: {result['errors']}")
    if result['errors'] > 0:
        print("Детали ошибок:", json.dumps(result['error_details'], indent=2))

### 4.3. Запуск миграции
```bash
# Установка зависимостей
pip install supabase

# Проверка переменных окружения
source .env

# Запуск миграции
python migrate_llm_results_to_supabase.py
```

## 5. Интеграция в конвейер обработки
### 5.1. Обновление api_pipeline_validator.py

Заменить SQLite writer на Supabase writer:
from supabase import create_client
import os

class SupabaseWriter:
    def __init__(self):
        self.client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )
    
    def write_email_results(self, email_data, llm_results):
        """Запись результатов обработки письма в Supabase"""
        
        # Сохранение письма
        email_record = self.client.table('emails').insert({
            'message_id': email_data['message_id'],
            'from_addr': email_data['from'],
            'subject': email_data['subject'],
            'date': email_data['date'],
            'path_json': email_data['json_path'],
            # ... другие поля
        }).execute()
        
        email_id = email_record.data[0]['id']
        
        # Сохранение организаций, контактов, КП
        for org in llm_results.get('organizations', []):
            org_id = self.upsert_organization(org)
            
        for contact in llm_results.get('contacts', []):
            contact_id = self.upsert_contact(contact)
            
            # Создание interaction
            self.client.table('interactions').insert({
                'contact_id': contact_id,
                'email_id': email_id,
                'when_at': email_data['date'],
                'role': contact.get('role_in_message', 'other')
            }).execute()
        
        return email_id

## 6. Бесплатный тариф Supabase — ограничения

- Database size: 500 MB
- Bandwidth: 5 GB/месяц
- API requests: Unlimited (с rate limiting)
- Storage: 1 GB
- Realtime connections: 200 одновременных

Для проекта с ~19,000 писем это должно быть достаточно на начальном этапе.

## 7. Мониторинг и бэкапы

### 7.1. Встроенные бэкапы Supabase

Supabase автоматически создает ежедневные бэкапы (доступны 7 дней на бесплатном тарифе).

### 7.2. Ручной экспорт

```bash
# Экспорт через pg_dump
pg_dump "postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres" > backup.sql

# Или через Supabase CLI
supabase db dump -f backup.sql
```

## 8. Следующие шаги

- ✅ Создать проект в Supabase
- ✅ Применить SQL схему
- ✅ Настроить переменные окружения
- ⏳ Создать и запустить скрипт миграции данных
- ⏳ Обновить api_pipeline_validator.py для записи в Supabase
- ⏳ Протестировать конвейер с новыми данными
- ⏳ Настроить автоматический запуск (см. 17_DEPLOYMENT_OPTIONS.md)

