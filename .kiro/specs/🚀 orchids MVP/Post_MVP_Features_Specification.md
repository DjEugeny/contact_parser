
# Создаем ТЗ для скрытых разделов (Post-MVP фичи)

post_mvp_spec = """# 📋 Техническое задание: Post-MVP фичи Mini-CRM
**Версия:** 1.0  
**Дата:** 05.10.2025  
**Статус:** Для реализации после завершения MVP

---

## 🎯 ОБЗОР

Эти функции **скрыты для MVP** (заглушки), но их нужно реализовать в версии 2.0 для полноценной работы CRM.

---

## 📎 РАЗДЕЛ 1: ВЛОЖЕНИЯ (/attachments)

### Назначение:
Централизованный реестр всех файлов, полученных из писем (PDF, DOCX, XLSX, JPG, и т.д.)

### Функциональность:

#### 1.1 Список вложений
- **Представление:** таблица или grid-карточки
- **Колонки:**
  - Название файла (filename)
  - Тип (icon по MIME type: 📄 PDF, 📊 Excel, 📝 Word, 🖼️ Image)
  - Размер (human-readable: 2.3 MB)
  - Источник (из какого письма, link to /emails/:id)
  - Дата получения (extracted_at)
  - Контакт (отправитель, link to contact)
  - Организация (link to org)

#### 1.2 Фильтры:
- По типу файла (PDF, Excel, Word, Images, Other)
- По дате получения (date range)
- По контакту (dropdown)
- По организации (dropdown)
- По размеру (< 1 MB, 1-10 MB, > 10 MB)

#### 1.3 Поиск:
- По названию файла
- По содержимому (если есть text extraction)

#### 1.4 Действия:
- **Превью:** для PDF, изображений — inline preview
- **Скачать:** кнопка download
- **Открыть письмо:** переход в /emails/:id (источник)
- **Удалить:** soft delete (mark as deleted, не физическое удаление)

#### 1.5 Детальная карточка вложения (/attachments/:id):
- Filename, size, type, MIME type
- Preview (если возможно)
- Metadata: date, source email, contact, organization
- Related attachments (другие файлы из того же письма)
- Button: Download, View in email, Delete

### Структура БД:

```sql
CREATE TABLE attachments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT NOT NULL,
  mime_type TEXT,
  file_size INTEGER, -- bytes
  file_path TEXT, -- path to stored file (local or S3)
  file_url TEXT, -- URL if stored remotely
  email_id INTEGER, -- FK to interactions (which email)
  contact_id INTEGER, -- FK to contacts (sender)
  organization_id INTEGER, -- FK to organizations
  extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_deleted BOOLEAN DEFAULT FALSE,
  user_notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (email_id) REFERENCES interactions(id),
  FOREIGN KEY (contact_id) REFERENCES contacts(id),
  FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE INDEX idx_attachments_email ON attachments(email_id);
CREATE INDEX idx_attachments_contact ON attachments(contact_id);
CREATE INDEX idx_attachments_org ON attachments(organization_id);
```

### Источник данных:
- При обработке писем через Python скрипт:
  1. Извлечь attachments из .eml файла
  2. Сохранить файлы локально или в S3
  3. INSERT в таблицу `attachments` с metadata

### Приоритет: **Высокий** (нужен для работы с КП в PDF)

---

## 🗂️ РАЗДЕЛ 2: ФАКТЫ (/facts)

### Назначение:
Автоматически извлечённые факты из переписки (цены, сроки, условия, требования)

### Функциональность:

#### 2.1 Список фактов
- **Представление:** карточки с группировкой по типам
- **Типы фактов:**
  - 💰 Цены (price quotes)
  - 📅 Сроки (deadlines, delivery dates)
  - 📋 Требования (requirements, specifications)
  - ⚠️ Проблемы (complaints, issues)
  - ✅ Решения (resolutions, agreements)
  - 📊 Метрики (KPIs, volumes, quantities)

#### 2.2 Карточка факта:
- **Заголовок:** краткое описание (auto-generated or user-editable)
- **Текст:** extracted fact text
- **Контекст:** snippet from source email
- **Metadata:**
  - Тип факта (badge с иконкой)
  - Источник (link to email)
  - Дата извлечения
  - Контакт
  - Организация
  - Confidence score (0-1)
- **Связи:**
  - Связанное КП (if relevant)
  - Связанная организация
  - Связанный контакт

#### 2.3 Фильтры:
- По типу факта
- По дате
- По контакту
- По организации
- По confidence score (> 0.95, 0.8-0.95, < 0.8)

#### 2.4 Действия:
- **Редактировать:** изменить описание, тип, связи
- **Подтвердить:** set confidence = 1.0
- **Отклонить:** mark as irrelevant
- **Добавить к КП:** link to commercial offer
- **Удалить**

### Структура БД:

```sql
CREATE TABLE facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fact_type TEXT NOT NULL, -- 'price', 'deadline', 'requirement', 'issue', 'resolution', 'metric'
  title TEXT, -- short description
  fact_text TEXT NOT NULL, -- extracted fact
  context_text TEXT, -- surrounding text for context
  confidence REAL DEFAULT 0.9, -- 0-1
  email_id INTEGER, -- source email
  contact_id INTEGER,
  organization_id INTEGER,
  offer_id INTEGER, -- linked commercial offer (if relevant)
  extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_confirmed BOOLEAN DEFAULT FALSE,
  is_relevant BOOLEAN DEFAULT TRUE,
  user_notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (email_id) REFERENCES interactions(id),
  FOREIGN KEY (contact_id) REFERENCES contacts(id),
  FOREIGN KEY (organization_id) REFERENCES organizations(id),
  FOREIGN KEY (offer_id) REFERENCES commercial_offers(id)
);

CREATE INDEX idx_facts_type ON facts(fact_type);
CREATE INDEX idx_facts_email ON facts(email_id);
CREATE INDEX idx_facts_org ON facts(organization_id);
CREATE INDEX idx_facts_offer ON facts(offer_id);
```

### Источник данных:
- LLM обработка писем с промптом:
  ```
  Extract key business facts from this email:
  - Prices mentioned (with context: what product, when, for whom)
  - Deadlines (delivery dates, payment terms, validity periods)
  - Requirements (technical specs, quantities, certifications)
  - Issues/complaints
  - Resolutions/agreements
  
  Output format: JSON array of facts with type, text, context
  ```

### Приоритет: **Средний** (полезно, но не критично для MVP)

---

## 🔖 РАЗДЕЛ 3: СОХРАНЁННЫЕ ВИДЫ (/saved-views)

### Назначение:
Сохранение настроек фильтров и сортировок для быстрого доступа

### Функциональность:

#### 3.1 Что сохраняется:
- **Представление:** grid или table
- **Фильтры:** все активные фильтры (город, организация, дата, и т.д.)
- **Сортировка:** поле и направление (ASC/DESC)
- **Страница:** контакты, организации, КП, письма
- **Название:** user-defined (например, "Контакты из Москвы с низким confidence")

#### 3.2 Список сохранённых видов
- **Представление:** карточки или список
- **Карточка вида:**
  - Название (user-editable)
  - Иконка по типу страницы (👤 контакты, 🏢 организации, 📄 КП, 📧 письма)
  - Описание (auto-generated: "Москва, confidence < 0.9, сортировка по дате")
  - Дата создания
  - Кол-во записей (текущее)
  - Кнопка "Применить"

#### 3.3 Создание вида:
- На странице контактов/организаций/КП/писем:
  - Настроить фильтры и сортировку
  - Нажать кнопку "Сохранить вид" (📌 icon)
  - Modal:
    • Название* (text input)
    • Описание (optional textarea)
    • Сделать по умолчанию (checkbox)
  - Save → добавить в /saved-views

#### 3.4 Применение вида:
- Клик на карточку вида → navigate to page with filters applied
- Или: dropdown в header страницы "Применить вид" → выбрать из списка

#### 3.5 Управление:
- **Переименовать**
- **Редактировать** (изменить фильтры)
- **Установить по умолчанию** (auto-apply при открытии страницы)
- **Удалить**

### Структура БД:

```sql
CREATE TABLE saved_views (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  page TEXT NOT NULL, -- 'contacts', 'organizations', 'offers', 'emails'
  filters JSON, -- serialized filter object: {"city": "Москва", "confidence_min": 0.9}
  sort_field TEXT, -- 'name', 'created_at', etc
  sort_direction TEXT, -- 'ASC', 'DESC'
  view_type TEXT, -- 'grid', 'table'
  is_default BOOLEAN DEFAULT FALSE,
  user_id INTEGER, -- if multi-user system
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_saved_views_page ON saved_views(page);
CREATE INDEX idx_saved_views_user ON saved_views(user_id);
```

### Приоритет: **Низкий** (nice-to-have, не критично)

---

## 🔐 РАЗДЕЛ 4: АВТОРИЗАЦИЯ (Authentication)

### Назначение:
Защита данных, разграничение доступа

### Функциональность:

#### 4.1 Методы входа:
- **Email + Password** (базовый)
- **Google Sign-In** (OAuth)
- **Microsoft Sign-In** (опционально)

#### 4.2 Страницы:
- **/login:** форма входа
- **/register:** регистрация (если нужна)
- **/forgot-password:** восстановление пароля

#### 4.3 Роли (если multi-user):
- **Admin:** полный доступ
- **User:** просмотр + редактирование своих данных
- **Viewer:** только просмотр

#### 4.4 Защита роутов:
- Все страницы требуют аутентификации
- Redirect to /login если не залогинен

### Технологии:
- **Orchids Auth** (встроенная система)
- Или **Clerk.com** (рекомендуется для production)
- Или **NextAuth.js** (если React)

### Приоритет: **Низкий для MVP**, **Высокий для Production**

---

## 📱 РАЗДЕЛ 5: АДАПТИВНЫЙ ДИЗАЙН (Responsive)

### Назначение:
Работа на планшетах и смартфонах

### Breakpoints:
- **Desktop:** ≥ 1024px (текущий)
- **Tablet:** 768px - 1023px
- **Mobile:** < 768px

### Адаптация:

#### 5.1 Mobile (< 768px):
- **Sidebar:** скрыть, показать burger menu (☰)
- **Tables:** конвертировать в cards
- **Grid:** 1 колонка
- **Фильтры:** collapsible panel
- **Формы:** full-width inputs

#### 5.2 Tablet (768-1023px):
- **Sidebar:** collapsible (показать/скрыть)
- **Grid:** 2 колонки
- **Tables:** сохранить, убрать некритичные колонки

#### 5.3 Touch optimization:
- Увеличить размер кнопок (min 44x44px)
- Добавить swipe gestures (опционально)

### Приоритет: **Средний** (важно для удобства, но не блокирующее)

---

## 📊 РАЗДЕЛ 6: АНАЛИТИКА И ОТЧЁТЫ (/analytics)

### Назначение:
Визуализация данных, выявление трендов

### Дашборды:

#### 6.1 Общая аналитика:
- **Динамика контактов:** график добавления по месяцам
- **Топ организации:** по кол-ву контактов, по сумме КП
- **География:** карта или таблица по городам
- **Confidence score:** распределение (гистограмма)

#### 6.2 Аналитика КП:
- **Конверсия:** отправлено → принято (funnel chart)
- **Средний чек:** по месяцам
- **Топ клиенты:** по сумме КП
- **Срок принятия:** от отправки до принятия (avg days)

#### 6.3 Аналитика переписки:
- **Активность:** кол-во писем по месяцам
- **Топ контакты:** по кол-ву писем
- **Response time:** среднее время ответа

### Экспорт:
- **PDF:** отчёты для печати
- **Excel:** таблицы для анализа
- **CSV:** raw data export

### Приоритет: **Низкий для MVP**, **Средний для Production**

---

## 🔔 РАЗДЕЛ 7: УВЕДОМЛЕНИЯ (Notifications)

### Назначение:
Напоминания о важных событиях

### Типы уведомлений:

#### 7.1 Внутри приложения (in-app):
- 🔔 Истекает срок КП (за X дней до valid_until)
- 📧 Новое письмо получено
- ⚠️ Новый контакт с низким confidence (требует проверки)
- ✅ Статус КП изменён

#### 7.2 Email-уведомления:
- Ежедневный digest (утром):
  • КП с истекающим сроком сегодня
  • Новые контакты с низким confidence
  • Новые письма (count)

#### 7.3 Push-уведомления (если PWA):
- Критичные события

### Настройки (в /settings):
- Включить/выключить по типам
- Частота email digest (ежедневно, еженедельно, никогда)
- Порог напоминания КП (за сколько дней)

### Приоритет: **Низкий для MVP**, **Средний для Production**

---

## 🔄 РАЗДЕЛ 8: СИНХРОНИЗАЦИЯ ПИСЕМ (Email Sync)

### Назначение:
Автоматическая загрузка новых писем из почтового ящика

### Функциональность:

#### 8.1 Настройка подключения (в /settings):
- **IMAP Settings:**
  - Host (imap.gmail.com)
  - Port (993)
  - Username (email)
  - Password or App Password
  - Folder to sync (INBOX)
- **Частота синхронизации:**
  - Вручную
  - Каждый час
  - Каждые 6 часов
  - Раз в день
- **Фильтры:**
  - Синхронизировать только письма с определёнными отправителями
  - Или с ключевыми словами в теме

#### 8.2 Процесс синхронизации:
1. Подключиться к IMAP
2. Fetch UNSEEN emails
3. Скачать .eml файлы
4. Обработать через LLM:
   - Извлечь контакты
   - Извлечь организации
   - Извлечь КП (из PDF вложений)
   - Извлечь факты
5. INSERT в БД
6. Mark email as SEEN

#### 8.3 Мониторинг:
- Последняя синхронизация (timestamp)
- Кол-во обработанных писем
- Ошибки (если есть)
- Логи (для отладки)

### Технологии:
- **Backend:** Python IMAP client (imaplib)
- **LLM:** OpenAI API, Anthropic Claude, или локальная модель
- **Queue:** Celery (для фоновой обработки)

### Приоритет: **Высокий для Production** (ключевая автоматизация)

---

## 🗄️ РАЗДЕЛ 9: ЭКСПОРТ И БЭКАПЫ

### Функциональность:

#### 9.1 Экспорт данных (в /settings):
- **Формат:**
  - CSV (для Excel)
  - JSON (для миграции)
  - SQL dump (для восстановления)
- **Выбор таблиц:**
  - Все данные
  - Только контакты
  - Только организации
  - и т.д.

#### 9.2 Автоматические бэкапы:
- **Частота:** ежедневно в 3:00 AM
- **Хранение:** локально или S3
- **Retention:** 30 дней
- **Восстановление:** через UI (upload backup file)

### Приоритет: **Высокий для Production** (защита от потери данных)

---

## 📋 ИТОГОВАЯ ТАБЛИЦА ПРИОРИТЕТОВ

| Раздел | Приоритет | Сложность | Время разработки | Зависимости |
|--------|-----------|-----------|------------------|-------------|
| **Вложения** | 🔴 Высокий | Средняя | 5-7 дней | Email sync |
| **Факты** | 🟠 Средний | Высокая (LLM) | 10-15 дней | Email sync, LLM integration |
| **Сохранённые виды** | 🟡 Низкий | Низкая | 2-3 дня | Нет |
| **Авторизация** | 🟢 Низкий (MVP), 🔴 Высокий (Prod) | Средняя | 3-5 дней | Auth provider (Clerk/NextAuth) |
| **Адаптивный дизайн** | 🟠 Средний | Средняя | 5-7 дней | Нет |
| **Аналитика** | 🟡 Низкий | Средняя | 7-10 дней | Charting library |
| **Уведомления** | 🟡 Низкий | Средняя | 5-7 дней | Email service (Resend/SendGrid) |
| **Email Sync** | 🔴 Высокий | Высокая | 10-15 дней | IMAP, LLM, Queue |
| **Экспорт/Бэкапы** | 🟠 Средний | Низкая | 3-5 дней | Storage (S3 or local) |

---

## 🚀 РЕКОМЕНДУЕМАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ РЕАЛИЗАЦИИ

### Фаза 2 (Post-MVP):
1. **Email Sync** — автоматизация ключевого процесса
2. **Вложения** — работа с PDF КП
3. **Авторизация** — безопасность

### Фаза 3 (Enhanced):
4. **Адаптивный дизайн** — доступность с мобильных
5. **Экспорт/Бэкапы** — защита данных
6. **Уведомления** — автоматизация напоминаний

### Фаза 4 (Advanced):
7. **Факты** — интеллектуальный анализ
8. **Аналитика** — визуализация данных
9. **Сохранённые виды** — удобство работы

---

**Итого:** ~50-70 дней разработки для полного функционала (Post-MVP)

---

## 📝 ЗАКЛЮЧЕНИЕ

Эти функции сделают Mini-CRM **полноценной системой** для управления B2B перепиской и клиентами. Но для **MVP достаточно базового функционала**, реализованного в Orchids Request 2-4.

**Рекомендация:** Запустите MVP, соберите feedback от пользователей, затем приоритизируйте Post-MVP фичи по реальным потребностям.
"""