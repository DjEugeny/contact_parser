## 🧭 Описание
Этот документ содержит все рабочие промпты AI:  
- финальный **мастер‑промпт** (генерация проекта, UI, базы, дизайна),  
- и четыре **follow‑up промпта** для донастройки.  
В конце приведены рекомендации по загрузке оставшихся CSV‑сидов.

---

## 🧱 1. Мастер‑промпт
> **Цель:** Сгенерировать Mini‑CRM (Supabase/Postgres, React+Vite, Tailwind, shadcn/ui).  
> Источник данных — готовые JSON/CSV после постпроцессинга. Внутри приложения AI не используется.

---

###  📌 Вложения
02_REQUIREMENTS.md
06_SEARCH_AND_INDEXING.md
07_FRONTEND_UI.md
README_postprocessing.md

Cид CSV (8 файлов):
organizations.csv
contacts.csv
phone_numbers.csv
email_threads.csv
emails.csv
commercial_offers.csv
commercial_offer_items.csv
interactions.csv

---

### 🗂️ Навигация (Sidebar)
- Дашборд
- Входящие/Треды
- Письма
- Контакты
- Организации
- Коммерческие предложения
- Вложения
- Факты (Evidence)
- Модерация
- Сохранённые виды
- Настройки

---

### 🎨 Дизайн/тема
- Референс: [пример из Dribbble]
- Основной акцент: #2862F6 (синий)
- Вторичные: серые нейтральные, success → #22C55E, warning → #F59E0B, danger → #EF4444
- Карточки: мягкие тени, радиус 14–16px
- Таблицы: компактные, с переключателем density, чип-фильтры, hover-состояния
- Типографика: body 16, small 14, caption 12
- Поддержка тёмной темы

---

### 📑 Страницы и UX
- Дашборд: строка глобального поиска; «истекающие КП за 14 дней» (таблица); последние изменения; модерационный inbox
- Контакты/Организации (списки): фильтры (ФИО/телефон/email/город/организация/ИНН), сортировки, сохранённые виды (CRUD)
- Карточка Организации: реквизиты (название/сайт/город/адрес/ИНН), вкладки «Контакты | История | КП», action-кнопки
- Карточка Контакта: ФИО/должность/компания/телефоны/email/город; лента взаимодействий (role_in_message), связанные КП
- Входящие/Треды → Письма: список тредов; просмотр ленты писем. Кнопка «Открыть письмо»: если eml_path задан и enable_eml_storage=true → скачай .eml из Storage; иначе — показать JSON (body_text, участники, вложения). Отображать Message-ID, «Скачать JSON»
- Вложения: таблица; ссылка на файл в Storage; превью первых 500 символов из extracted_text_path (OCR в облаке не делаем)
- Факты (Evidence): список фактов (тип: адрес/город/организация/телефон/email/ИНН/сайт/продукт) с фильтрами; кнопка «Привязать» к org/contact
- Модерация: очередь сомнительных сущностей из постпроцессинга («Объединить/Создать/Игнорировать»)
- Настройки: флаг enable_eml_storage (по умолчанию выключен), локализация (RU), дефолтные напоминания по КП: 14 дней

---

## 🗄️ База данных (Supabase/Postgres)

### 🏛️ Архитектурные принципы
- 🚫 **Без ENUM** → используем справочники или `text+CHECK`
- 🔍 **Индексы** по полям поиска (email/phone/city/inn/domain), датам писем/КП

### 📋 Структура таблиц

#### 🏢 Организации
```sql
organizations(
  id, name, inn, inn_validated, inn_source, domain,
  website, city, address, created_at, updated_at
)
```

#### 👥 Контакты
```sql
contacts(
  id, organization_id, full_name, position, email,
  email_normalized, email_valid, city, address,
  created_at, updated_at
)
```

#### 📞 Телефоны
```sql
phone_numbers(
  id, contact_id, organization_id, type, number_e164,
  extension, original, is_primary
)
```

#### 📧 Email-треды
```sql
email_threads(
  id, subject, first_message_at, last_message_at,
  organization_id, contact_id
)
```

#### ✉️ Письма
```sql
emails(
  id, thread_id, message_id, in_reply_to, from_address,
  from_name, sent_at, subject, body_text, raw_headers,
  json_path, eml_path
)
```

#### 👥 Получатели писем
```sql
email_recipients(
  id, email_id, role, address, display_name, contact_id
)
```

#### 📎 Вложения
```sql
attachments(
  id, email_id, filename, mime_type, size_bytes,
  storage_path, created_at
)
```

#### 📄 Текст вложений
```sql
attachment_texts(
  attachment_id, extracted_text_path, extracted_at,
  source_ocr_engine
)
```

#### 🔍 Факты (Evidence)
```sql
evidence(
  id, source_type, source_id, entity_type, value,
  confidence, linked_organization_id, linked_contact_id
)
```

#### 💼 Коммерческие предложения
```sql
commercial_offers(
  id, offer_number, offer_date, end_user_org_name,
  end_user_inn, intermediary_org_name, payment_terms,
  delivery_time, delivery_terms, valid_until, total_cost,
  comments, status_code
)
```

#### 📦 Позиции КП
```sql
commercial_offer_items(
  id, offer_id, name, model, article, quantity,
  unit_price, total_price, vat
)
```

#### 🔄 Взаимодействия
```sql
interactions(
  id, email_id, contact_id, organization_id,
  interaction_type, role_in_message, message_subject,
  message_date, human_note, confidence, attachments
)
```

#### 🏷️ Теги и связи
```sql
tags, tag_links, saved_views(user_id, entity, title, query_json)
```

#### 🔍 Очередь модерации
```sql
moderation_queue(
  id, entity_type, payload, confidence, status, reason
)
```

### 🚀 Индексы производительности

```sql
-- Письма
CREATE INDEX idx_emails_sent_at ON emails(sent_at);
CREATE INDEX idx_emails_message_id ON emails(message_id);

-- Контакты
CREATE INDEX idx_contacts_email_normalized ON contacts(email_normalized);

-- Телефоны
CREATE INDEX idx_phone_numbers_e164 ON phone_numbers(number_e164);

-- Организации
CREATE INDEX idx_organizations_inn ON organizations(inn);
CREATE INDEX idx_organizations_name_lower ON organizations(lower(name));

-- Коммерческие предложения
CREATE INDEX idx_commercial_offers_dates ON commercial_offers(valid_until, offer_date);
```

---

## 📞 Телефоны — правила UI

### 🎯 Отображение
- 📱 Основной формат: `number_e164`
- 🔗 При наличии `extension` → добавлять `(доб. {extension})`
- 📞 Click-to-call: `tel:{number_e164}`; при поддержке → `;ext={extension}`, иначе через запятую
- 📝 `original` — только для аудита

---

## 🧾 ИНН-валидация

### 📋 Правила валидации
- 🔢 **10 цифр** — юрлицо (1 контрольная)
- 🔢 **12 цифр** — ИП/физлицо (2 контрольные)

### ⚠️ Возможные ошибки
- ❌ «Неверная длина»
- ❌ «Неверная контрольная сумма»

### 🔐 Двойная проверка
- 🖥️ **Клиент**: JS-валидация в формах
- 🌐 **Сервер**: Edge Function с установкой `inn_validated=true` при успехе

---

## 📦 Storage

### 📁 Структура бакетов

| Бакет | Назначение | Описание |
|-------|------------|----------|
| 📎 `attachments` | Файлы | Оригинальные вложения писем |
| 📄 `texts` | Распознанный текст | `.txt` файлы после OCR |
| 📧 `emails` | Письма | `.eml` файлы (скрываются при `enable_eml_storage=false`) |

---

## 📥 Импорт сидов

### 📊 Поддерживаемые сущности
- 🏢 `organizations`
- 👥 `contacts`
- 📞 `phone_numbers`
- 📧 `email_threads`
- ✉️ `emails`
- 💼 `commercial_offers`
- 📦 `commercial_offer_items`
- 🔄 `interactions`

### 🔄 Процесс импорта
1. 📤 Загрузить прилагаемые CSV
2. 🔄 Пересчитать `email_threads.first/last_message_at`
3. ✅ Проверить целостность связей

---

## 🔐 Доступ

### 🔑 Аутентификация
- 🌐 **Google** OAuth
- 📧 **Email + пароль**

### 👥 Роли
- 👑 **admin** — полный доступ
- 👤 **user** — чтение/запись

### 🛡️ Безопасность
- 🚫 **RLS выключен** (упрощённая модель)

---

## 📊 Покажи по завершении

### 🎯 Артефакты для демонстрации

| Компонент | Описание |
|-----------|----------|
| 📈 **ERD** | Диаграмма сущностей и связей |
| 🔄 **Миграции** | SQL-скрипты создания структуры |
| 📋 **Таблицы и индексы** | Готовая схема БД |
| 🖥️ **Страницы и формы** | UI компоненты |
- 📤 **Импорт-утилиты** | Инструменты загрузки данных |
| 📦 **Настроенные buckets** | Структура хранилища |


---

# 💡 Обнови приложение без пересоздания схемы.

## ⚙️ ИНН‑валидатор

> Добавить JS‑валидатор ИНН в формы организаций и КП.  
> Алгоритм:  
> • 10 цифр — 1 контрольная (вес [2,4,10,3,5,9,4,6,8])  
> • 12 цифр — 2 контрольные (веса [7,2,4,10,3,5,9,4,6,8] и [3,7,2,4,10,3,5,9,4,6,8])  
> • Ошибки: «Неверная длина» / «Неверная контрольная сумма»  
> • Повторить проверку на сервере (edge function), при успехе ставить `inn_validated=true`  

---

## 📥 Импорт CSV/JSON

> Создать страницы импорта для таблиц:  
> `organizations`, `contacts`, `phone_numbers`, `email_threads`, `emails`,  
> `commercial_offers`, `commercial_offer_items`, `interactions`.  
> Настроить маппинг колонок по именам из CSV.  
> После импорта пересчитывать `email_threads.first/last_message_at` и показывать тост‑уведомление.

---

## 🧩 Модерация

> Страница `Модерация`: таблица `moderation_queue` (status: open/merged/created/ignored).  
> Колонки: `entity_type`, `confidence`, `reason`, `payload` (свёрнутый diff).  
> Действия: кнопки «Объединить», «Создать», «Игнорировать» вызывают server actions и пишут лог в `moderation_logs`.

---

## ✉️ Переключатель EML‑хранилища

> В настройках добавить флаг `enable_eml_storage` (bool, default false).  
> Если `false` → скрывать все действия с `.eml`, не пытаться читать `eml_path`.  
> Если `true` → разрешить загрузку и просмотр `.eml` из bucket `emails`.

---

## 📊 Рекомендации по CSV‑сидам

Мы уже загрузили в Lovable первые файлы:
- ✅ `organizations.csv`  
- ✅ `contacts.csv`  
- ✅ `phone_numbers.csv`  
- ✅ `commercial_offers.csv`  
- ✅ `commercial_offer_items.csv`  

Осталось загрузить следующие сиды (через **Database → Add Data** или страницу `/import`):

| Приоритет | Файл | Назначение |
|-----------:|------|------------|
| 🔹 1 | `email_threads.csv` | Цепочки писем (связи с email_id) |
| 🔹 2 | `emails.csv` | Сами письма, `thread_id`, `subject`, `sent_at` |
| 🔹 3 | `interactions.csv` | Лента взаимодействий контактов и организаций |

> После загрузки этих трёх файлов:  
> - Проверь связность `thread_id` в emails и interactions.  
> - В `Dashboard` появятся данные о последних письмах и контактах.  
> - Можно перейти к модерации и добавлению evidence при необходимости.

---

## 💄 Косметика
Оставить стиль/палитру без изменений (акцент #2862F6), таблицы — компактные/hover, чип-фильтры; текстовые метки статусов КП — русские: «Отправлено», «Принято», «Отклонено», «Истекло».






