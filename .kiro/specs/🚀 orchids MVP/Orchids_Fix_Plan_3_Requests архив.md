# 🔧 План исправлений Mini-CRM в Orchids
**Дата:** 05.10.2025  
**Лимиты:** 3 refills осталось (по 100k tokens каждый)  
**Стратегия:** 3 больших промпта для завершения MVP

---

## 📋 REQUEST 2 (Приоритет 1) — КРИТИЧЕСКИЕ БАГИ + SEED DATA

**Цель:** Исправить блокирующие баги, заполнить пустые таблицы, создать недостающие страницы

### 🎯 Что делаем:

1. **Заполнить пустые таблицы seed data**
   - contact_emails (0 → 25+ записей)
   - contact_phones (0 → 15+ записей)
   - commercial_offer_items (0 → 40+ позиций для 20 КП)
   - interactions (0 → 50+ взаимодействий)

2. **Исправить формы создания**
   - Кнопка "Добавить контакт" → рабочая форма с полями:
     • Имя*, Должность, Организация (dropdown), Город
     • Email (можно добавить несколько), Телефон (с выбором типа)
     • Заметки
   - Кнопка "Добавить организацию" → рабочая форма:
     • Название*, ИНН, Сайт, Город, Адрес, Заметки

3. **Создать карточку КП (/offers/:id)**
   - Основная информация: номер, дата, срок действия, статус (editable dropdown)
   - Блок "Стороны": Конечный потребитель (link to org), Посредник (link to org)
   - Таблица позиций из commercial_offer_items:
     Columns: №, Название, Модель, Артикул, Кол-во, Цена за ед., Сумма, НДС
   - Footer: "ИТОГО: {total_cost} ₽" (bold, large)
   - Блок "Заметки" (editable)

4. **Создать страницу Модерация (/moderation)**
   - Раздел A: "Контакты с низким confidence" (WHERE confidence < 0.95)
     • Карточки контактов с кнопками:
       [✅ Принять] (set confidence = 1.0)
       [✏️ Редактировать]
       [❌ Удалить]
   - Раздел B: "Проверка ИНН организаций" (WHERE inn IS NULL OR inn = '')
     • Карточки организаций с:
       Input "ИНН:" (10-12 digits)
       Mock suggestions (top-3 кандидата)
       [✅ Принять], [❌ Отклонить]

5. **Создать страницу Настройки (/settings)**
   - Секция "Уведомления":
     • Input: "Напоминать о КП за сколько дней" (default 14)
   - Секция "Хранение данных":
     • Toggle: "Сохранять .eml файлы" (MVP: только UI)
   - Секция "Профиль":
     • Input: "Имя"
     • Display: "Email" (read-only)
     • Badge: "Роль: User"

### 📝 Промпт для Orchids:

```
Critical fixes and missing pages for Mini-CRM:

PRIORITY 1: FILL EMPTY TABLES WITH SEED DATA

1. Add seed data to empty tables:

A) contact_emails (0 rows → 25+ rows):
- Link emails to existing contacts (id 1-25)
- Format: email, is_primary (true/false)
- Example data:
  INSERT INTO contact_emails (contact_id, email, is_primary) VALUES
  (1, 'petrov@technosphere.ru', true),
  (2, 'zaitsev@industrial.ru', true),
  (3, 'fedorov@stroyinvest.ru', true),
  ...

B) contact_phones (0 rows → 15+ rows):
- Link phones to contacts
- Types: 'mobile', 'office', 'main', 'fax', 'other'
- Format: number (+7 xxx xxx-xx-xx), normalized (7xxxxxxxxxx), extension (if office)
- Example:
  INSERT INTO contact_phones (contact_id, type, number, normalized, extension) VALUES
  (1, 'mobile', '+7 (915) 252-22-43', '79152522243', NULL),
  (1, 'office', '+7 (495) 640-17-71', '74956401771', '2026'),
  ...

C) commercial_offer_items (0 rows → 40+ rows):
- Link to existing 20 offers
- 2-5 items per offer
- Format: offer_id, name, model, article, quantity, unit_price, total_price, vat
- Example equipment names:
  • Амплфикатор ДТ-322
  • Центрифуга МиниСпин МС-6000
  • Термостат ТС-80М
  • Шейкер ШВ-2
  • Дозатор пипеточный ДП-100
- Example:
  INSERT INTO commercial_offer_items (...) VALUES
  (1, 'Амплфикатор ДТ-322', 'ДТ-322', 'F-322', 5, 450000, 2250000, '20%'),
  (1, 'Центрифуга МиниСпин', 'МС-6000', 'C-600', 2, 175000, 350000, '20%'),
  ...

D) interactions (0 rows → 50+ rows):
- Link to contacts and organizations
- Fields: contact_id, organization_id, message_subject, message_date, role_in_message, summary, human_note
- role_in_message values: 'sender', 'recipient', 'cc', 'sent_quote', 'requested_quote'
- Example:
  INSERT INTO interactions (...) VALUES
  (1, 1, 'Коммерческое предложение на поставку реагентов', '2025-07-29 14:30:00', 'sender', 'Отправлено КП на реагенты', 'Петров отправил КП на 2.5М руб'),
  (2, 1, 'Запрос информации о наборах', '2025-07-15 10:20:00', 'recipient', 'Получен запрос', 'Клиент запросил цены на наборы ПЦ '),
  ...

PRIORITY 2: FIX CREATE FORMS

2. Fix "Добавить контакт" button:
- Open modal with form fields:
  • Name* (text input, required)
  • Position (text input)
  • Organization (dropdown from organizations table)
  • City (text input)
  • Emails (dynamic list, add/remove, mark primary)
  • Phones (dynamic list with type selector: mobile/office/main/fax/other, number input)
  • User notes (textarea)
- On submit: INSERT into contacts, contact_emails, contact_phones
- Show success toast: "Контакт добавлен ✓"
- Redirect to new contact card or refresh list

3. Fix "Добавить организацию" button:
- Open modal with form:
  • Name* (required)
  • INN (10 or 12 digits, optional)
  • Website (URL, optional)
  • City
  • Address (textarea)
  • User notes (textarea)
- On submit: INSERT into organizations
- Toast: "Организация добавлена ✓"

PRIORITY 3: CREATE OFFER CARD PAGE

4. Build /offers/:id page:
- Fetch offer by id with related items:
  SELECT * FROM commercial_offers WHERE id = :id
  SELECT * FROM commercial_offer_items WHERE offer_id = :id
- Layout:
  • Header: offer_number (large), offer_date, valid_until (with expiry badge)
  • Status: editable dropdown (sent/accepted/rejected/expired) with save button
  • Section "Стороны":
    - Конечный потребитель: end_user (if matches org name → link to /organizations/:id)
    - ИНН конечного потребителя: end_user_inn
    - Посредник: intermediary (if matches → link)
  • Section "Позиции оборудования":
    - Table with columns: №, Название, Модель, Артикул, Кол-во, Цена за ед., Сумма, НДС
    - Footer row: "ИТОГО: {total_cost} ₽" (format: 3 152 100 ₽)
  • Section "Заметки": editable textarea (save button)
- Make entire row in /offers table clickable (not just number)

PRIORITY 4: CREATE MODERATION PAGE

5. Build /moderation page with two sections:

A) "Контакты с низким confidence":
- Query: SELECT * FROM contacts WHERE confidence < 0.95 ORDER BY confidence ASC
- Display: cards with name, position, organization, email, confidence %
- Buttons per card:
  • [✅ Принять]: UPDATE contacts SET confidence = 1.0 WHERE id = X
  • [✏️ Редактировать]: open edit form
  • [❌ Удалить]: DELETE (with confirmation)

B) "Проверка ИНН организаций":
- Query: SELECT * FROM organizations WHERE inn IS NULL OR inn = ''
- Display: cards with name, city, website
- Per card:
  • Input "ИНН:" (validate 10 or 12 digits)
  • Mock suggestions (hardcoded for MVP):
    Example: "ООО Техносфера | ИНН: 7736570901 | Москва"
  • Buttons:
    [✅ Принять]: UPDATE organizations SET inn = '{input_value}'
    [❌ Отклонить]: skip

PRIORITY 5: CREATE SETTINGS PAGE

6. Build /settings page:

Sections:
A) "Уведомления":
- Label: "Напоминать о КП за сколько дней до истечения срока:"
- Input: number (default 14)
- Save button: UPDATE settings SET notification_days = X WHERE user_id = current_user

B) "Хранение данных":
- Toggle: "Сохранять .eml файлы"
- Note: "(Функция в разработке)"
- Save button: UPDATE settings SET save_eml_files = X

C) "Профиль":
- Input: "Имя:" (editable)
- Display: "Email:" (read-only, from auth or mock)
- Badge: "Роль: User" (static for MVP)

NOTES:
- All UI text in Russian
- Use existing design style (clean, modern, #2862F6 accent)
- Add toast notifications for all actions
- Validate forms before submit
- Handle errors gracefully

Please implement in order: 1 → 2 → 3 → 4 → 5
```

---

## 📋 REQUEST 3 (Приоритет 2) — УЛУЧШЕНИЕ UX + НОВЫЕ ФИЧИ

**Цель:** Исправить UX баги, добавить table view, создать страницу Писем

### 🎯 Что делаем:

1. **Исправить поиск (case-insensitive)**
   - Работает с любым регистром: "петров", "Петров", "ПЕТРОВ"

2. **Каскадные фильтры**
   - Фильтр по городу "Екатеринбург" → фильтр по организациям показывает только организации из Екатеринбурга

3. **Сделать сайты кликабельными**
   - В списке организаций: клик на сайт → открыть в новой вкладке
   - В карточке организации: клик на сайт → открыть в новой вкладке
   - Icon: 🗗 рядом с URL

4. **Добавить кнопку копирования ИНН**
   - Icon 📋 рядом с ИНН
   - Клик → скопировать только цифры в clipboard
   - Toast: "ИНН скопирован ✓"

5. **Сделать всю строку КП кликабельной**
   - Не только номер, но вся строка → переход в /offers/:id
   - Cursor: pointer на hover

6. **Добавить table view для контактов и организаций**
   - Toggle button: Grid ⊞ / Table ☰
   - Table columns для контактов: Имя, Должность, Организация, Город, Email, Телефон, Confidence, Дата добавления
   - Table columns для организаций: Название, ИНН, Сайт, Город, Контакты (count), КП (count), Дата добавления

7. **Добавить фильтр по дате добавления контактов**
   - Date range picker: "От" / "До"
   - Фильтр по created_at

8. **Сделать виджеты на Dashboard кликабельными**
   - Клик на "Организации: 15" → /organizations
   - Клик на "Контакты: 25" → /contacts
   - Клик на "КП: 20" → /offers
   - Клик на "КП с истекающим сроком" → /offers?filter=expiring

9. **Удалить виджет "Конверсия"**
   - Заменить на виджет "КП с истекающим сроком" (если его еще нет)

10. **Удалить виджет "Модерация" с Dashboard**
    - Оставить только в sidebar меню

11. **Создать страницу Письма (/emails)**
    - Список писем из таблицы interactions
    - Table columns: Дата, От кого (contact), Тема (message_subject), Роль (role_in_message), Организация
    - Фильтры: по контакту, по организации, по дате, по роли
    - Клик на строку → /emails/:id

12. **Создать карточку Письма (/emails/:id)**
    - Fetch interaction by id + related contact + organization
    - Layout:
      • Header: message_subject, message_date
      • From: contact name (link to contact card)
      • To: organization name (link to org card)
      • Role: role_in_message (в русском: "Отправитель", "Получатель", etc)
      • Section "Бизнес-резюме": human_note (if exists) else summary
      • Section "Детали письма": email_json (formatted JSON viewer or collapsed)
      • Section "Вложения": list attachments from email_json (if any)
      • Button: "Скачать .eml файл" (if available)

### 📝 Промпт для Orchids:

```
UX improvements and new Email page for Mini-CRM:

PRIORITY 1: FIX UX BUGS

1. Make search case-insensitive:
- Current: search only works with exact case ("Петров" works, "петров" doesn't)
- Fix: use LOWER() or ILIKE/LIKE with case-insensitive flag
- Apply to: contacts search, organizations search, offers search

2. Fix cascading filters:
- Current: filter by city "Екатеринбург" → filter by organization still shows ALL organizations
- Fix: when city filter is active, organization dropdown should show only organizations from that city
- Apply to: Contacts page filters

3. Make organization websites clickable:
- In organizations list: click on website → open in new tab (target="_blank")
- In organization card: click on website → open in new tab
- Add icon 🗗 next to URL
- Style: blue underline on hover

4. Add copy button for INN:
- Icon 📋 next to INN field
- On click: copy INN digits to clipboard (navigator.clipboard.writeText)
- Show toast: "ИНН скопирован ✓"

5. Make entire offer row clickable:
- Current: only offer_number (blue text) is clickable
- Fix: entire row should navigate to /offers/:id
- Cursor: pointer on hover
- Keep offer_number blue for visual indication

PRIORITY 2: ADD TABLE VIEW

6. Add table view toggle for Contacts:
- Button in top-right: Grid ⊞ / Table ☰
- Table columns: Имя, Должность, Организация, Город, Email, Телефон, Confidence, Дата добавления
- Same filters and sorting as grid view
- Click row → navigate to contact card

7. Add table view toggle for Organizations:
- Button: Grid ⊞ / Table ☰
- Columns: Название, ИНН, Сайт, Город, Контакты (count from contacts table), КП (count), Дата добавления
- Click row → navigate to org card

8. Add date range filter for Contacts:
- Filter: "Дата добавления"
- Date range picker: "От" / "До"
- Filter by created_at field

PRIORITY 3: IMPROVE DASHBOARD

9. Make Dashboard widgets clickable:
- "Организации: 15" → navigate to /organizations
- "Контакты: 25" → /contacts
- "КП: 20" → /offers
- "КП с истекающим сроком" widget → /offers?filter=expiring
- Add cursor: pointer on hover

10. Remove "Конверсия" widget:
- This metric doesn't make sense for CRM
- Replace with "КП с истекающим сроком" widget (if not already present)

11. Remove "Модерация" widget from Dashboard:
- Keep only in sidebar menu
- Dashboard should be cleaner

PRIORITY 4: CREATE EMAILS PAGE

12. Build /emails page (new!):
- This page lists all email interactions from interactions table
- Add to sidebar menu: 📧 "Письма" (under "Основное" section, after "КП")
- Table view with columns:
  • Дата (message_date, format: DD.MM.YYYY HH:mm)
  • От кого (contact.name, link to contact)
  • Тема (message_subject)
  • Роль (role_in_message in Russian, see mapping below)
  • Организация (organization.name, link to org)
- Filters:
  • По контакту (dropdown)
  • По организации (dropdown)
  • По дате (date range)
  • По роли (dropdown: Отправитель, Получатель, В копии, etc)
- Sort: default by message_date DESC (newest first)
- Click row → navigate to /emails/:id

Role mapping (role_in_message → Russian):
- sender → "Отправитель"
- recipient → "Получатель"
- cc → "В копии"
- sent_quote → "Отправил КП"
- requested_quote → "Запросил КП"
- follow_up → "Напоминание"
- clarification → "Уточнение"
- complaint → "Рекламация"
- info_request → "Запрос информации"
- invoice_sent → "Счёт отправлен"
- invoice_paid → "Счёт оплачен"
- contract_sent → "Договор отправлен"
- contract_signed → "Договор подписан"
- delivery → "Поставка/доставка"
- support → "Поддержка"
- other → "Другое"

13. Build /emails/:id page (email card):
- Fetch interaction by id
- JOIN contact and organization tables
- Layout:
  • Header: message_subject (large text)
  • Meta info:
    - Дата: message_date (format: DD MMMM YYYY, HH:mm)
    - От: contact.name (link to /contacts/:id)
    - Организация: organization.name (link to /organizations/:id)
    - Роль: role_in_message (Russian label with icon)
  • Section "Бизнес-резюме":
    - Display human_note (if not null and not empty)
    - Else display summary
    - Style: highlighted box with icon 💼
  • Section "Детали письма":
    - Display email_json in formatted JSON viewer (collapsible)
    - Or parse and show: From, To, CC, Subject, Body (plain text or HTML preview)
  • Section "Вложения":
    - Parse attachments from email_json (if any)
    - List: filename, size, type
    - Button per file: "Скачать" (if available)
  • Button: "Скачать .eml файл" (if eml file is stored)
    - For MVP: can be disabled with tooltip "В разработке"

NOTES:
- All text in Russian
- Use consistent design style
- Add loading states for data fetching
- Handle empty states ("Нет писем" if interactions table is empty)

Implement in order: 1-5 → 6-8 → 9-11 → 12-13
```

---

## 📋 REQUEST 4 (Приоритет 3) — ЗАГЛУШКИ + POLISH + СВЯЗИ

**Цель:** Добавить заглушки для скрытых разделов, исправить связи КП с организациями, UI polish

### 🎯 Что делаем:

1. **Добавить заглушки для скрытых разделов**
   - Страница /attachments (Вложения):
     • Заголовок: "Вложения"
     • Иконка 📎
     • Текст: "Этот раздел находится в разработке. Скоро здесь можно будет просматривать все файлы из писем."
     • Button: "Вернуться на главную" → /
   - Страница /facts (Факты):
     • Заголовок: "Факты"
     • Иконка 🗂️
     • Текст: "Раздел для автоматически извлечённых фактов из переписки. Ожидайте в следующей версии."
   - Страница /saved-views (Сохранённые виды):
     • Заголовок: "Сохранённые виды"
     • Иконка 🔖
     • Текст: "Здесь вы сможете сохранять настройки фильтров и сортировок для быстрого доступа."

2. **Исправить связи КП с организациями**
   - Проблема: поля end_user и intermediary — просто текст, нет FK
   - Решение: добавить поля end_user_org_id и intermediary_org_id (FK к organizations)
   - При отображении КП:
     • Если end_user_org_id не null → показать как ссылку на /organizations/:id
     • Иначе показать end_user как текст
   - Обновить счётчик "КП (X)" в карточке организации:
     • COUNT WHERE end_user_org_id = org.id OR intermediary_org_id = org.id

3. **Обогатить моковые данные связями**
   - Для существующих 20 КП:
     • Найти соответствия end_user с organizations.name
     • Установить end_user_org_id
   - Пример SQL:
     UPDATE commercial_offers 
     SET end_user_org_id = (SELECT id FROM organizations WHERE name = commercial_offers.end_user)
     WHERE end_user IN (SELECT name FROM organizations);

4. **UI Polish (мелкие улучшения)**
   - Добавить loading skeletons для всех списков
   - Добавить empty states:
     • "Нет контактов" (если список пустой)
     • "Нет организаций"
     • "Нет писем"
   - Добавить confirmation dialogs для delete actions
   - Добавить success/error toasts для всех операций
   - Проверить все тексты на русском (исправить опечатки)

5. **Скрыть/отключить кнопку "Создать КП"**
   - Для MVP это не нужно (КП загружаются из писем)
   - Вариант 1: скрыть кнопку
   - Вариант 2: disabled с tooltip "Доступно в следующей версии"

6. **Добавить сортировку для организаций (от А до Я / от Я до А)**
   - Как в контактах: кнопка для переключения направления сортировки

7. **Добавить счётчик КП в карточках организаций (в списке)**
   - Под "1 контактов" добавить "X КП"
   - Запрос: COUNT commercial_offers WHERE end_user_org_id = org.id OR intermediary_org_id = org.id

### 📝 Промпт для Orchids:

```
Final polish and placeholders for Mini-CRM:

PRIORITY 1: ADD PLACEHOLDERS FOR HIDDEN SECTIONS

1. Create placeholder pages:

A) /attachments (Вложения):
- Add to sidebar: 📎 "Вложения" (under "Данные" section)
- Page content:
  • Icon: 📎 (large)
  • Title: "Вложения"
  • Text: "Этот раздел находится в разработке. Скоро здесь можно будет просматривать все файлы из писем."
  • Button: "Вернуться на главную" → navigate to /

B) /facts (Факты):
- Add to sidebar: 🗂️ "Факты" (under "Данные" section)
- Page content:
  • Icon: 🗂️
  • Title: "Факты"
  • Text: "Раздел для автоматически извлечённых фактов из переписки. Ожидайте в следующей версии."
  • Button: "Вернуться на главную"

C) /saved-views (Сохранённые виды):
- Add to sidebar: 🔖 "Сохранённые виды" (under "Система" section)
- Page content:
  • Icon: 🔖
  • Title: "Сохранённые виды"
  • Text: "Здесь вы сможете сохранять настройки фильтров и сортировок для быстрого доступа."
  • Button: "Вернуться на главную"

Style: clean, centered content, light gray text, professional look

PRIORITY 2: FIX OFFERS-ORGANIZATIONS RELATIONSHIP

2. Add foreign keys to commercial_offers table:
- Add columns:
  • end_user_org_id INTEGER (foreign key to organizations.id, nullable)
  • intermediary_org_id INTEGER (foreign key to organizations.id, nullable)
- Keep existing end_user and intermediary text fields for fallback

3. Migrate existing data:
- For each offer, try to match end_user/intermediary text with organizations.name
- If match found, set end_user_org_id / intermediary_org_id
- SQL example:
  UPDATE commercial_offers 
  SET end_user_org_id = (
    SELECT id FROM organizations 
    WHERE name = commercial_offers.end_user
  )
  WHERE end_user IN (SELECT name FROM organizations);

4. Update offer display logic:
- In /offers table: if end_user_org_id exists, show as link to /organizations/:id
- In /offers/:id card: 
  • If end_user_org_id exists: "Конечный потребитель: [ORG_NAME]" (link)
  • Else: show end_user text (no link)
- Same for intermediary

5. Update organization card:
- Tab "КП (X)": count offers WHERE end_user_org_id = org.id OR intermediary_org_id = org.id
- Display list of related offers with links

6. Add offer count to organization cards (in list view):
- Under "X контактов" add "X КП"
- Count: SELECT COUNT(*) FROM commercial_offers WHERE end_user_org_id = ? OR intermediary_org_id = ?

PRIORITY 3: UI POLISH

7. Add loading states:
- Show skeleton loaders while fetching:
  • Contact list
  • Organization list
  • Offer list
  • Email list
  • Card pages
- Use placeholder cards/rows with shimmer effect

8. Add empty states:
- When no data:
  • Contacts: "Нет контактов. Добавьте первый контакт." + button "Добавить"
  • Organizations: "Нет организаций. Добавьте первую организацию."
  • Offers: "Нет коммерческих предложений."
  • Emails: "Нет писем. Письма появятся после загрузки из почтового ящика."
- Style: centered, icon, text, action button

9. Add confirmation dialogs:
- Before delete operations:
  • "Удалить контакт [NAME]? Это действие нельзя отменить."
  • Buttons: "Отмена" / "Удалить" (red)
- Before other destructive actions

10. Add toast notifications for all actions:
- Success toasts:
  • "Контакт добавлен ✓"
  • "Организация обновлена ✓"
  • "Заметки сохранены ✓"
  • "ИНН скопирован ✓"
  • "Статус изменён ✓"
- Error toasts:
  • "Ошибка: не удалось сохранить"
  • "Ошибка: проверьте поля формы"
- Position: top-right, auto-hide after 3 seconds

11. Fix all Russian text:
- Check for typos and inconsistencies
- Ensure all UI elements are in Russian
- Consistent terminology:
  • "КП" (not "Предложение")
  • "Контакты" (not "Люди")
  • "Организации" (not "Компании")

PRIORITY 4: HIDE/DISABLE CREATE OFFER BUTTON

12. Handle "Создать КП" button:
- For MVP, offers are imported from emails, not created manually
- Option A: Hide button completely
- Option B: Show button but disabled with tooltip "Доступно в следующей версии"
- Choose option B for better UX

PRIORITY 5: ADD SORT TOGGLE FOR ORGANIZATIONS

13. Add sort direction toggle for Organizations:
- Similar to Contacts page
- Button: ↑↓ or А→Я / Я→А
- Toggle between ASC/DESC for name sort

NOTES:
- Test all pages after changes
- Ensure responsive design still works
- Check that all links navigate correctly
- Verify database constraints don't break existing functionality

Implement in order: 1 → 2-6 → 7-11 → 12-13
```

---

## 📊 ИТОГОВЫЙ ПЛАН (SUMMARY)

| Request | Приоритет | Задачи | Токены (примерно) | Результат |
|---------|-----------|--------|-------------------|-----------|
| **Request 2** | 🔴 Критично | Seed data + формы + КП card + Модерация + Настройки | ~35k | MVP 85% |
| **Request 3** | 🟡 Важно | UX баги + Table view + Страница Писем | ~30k | MVP 95% |
| **Request 4** | 🟢 Доработка | Заглушки + связи КП-Организации + Polish | ~25k | MVP 100% ✅ |

**Итого:** 3 refill (3 дня работы)

---

## 🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После выполнения всех 3 запросов:

### ✅ Полный MVP:
- 9 страниц (Dashboard, Контакты, Организации, КП, Письма, Модерация, Настройки + 3 заглушки)
- Все таблицы заполнены seed data
- Формы создания работают
- Карточки детализации для всех сущностей
- Рабочие фильтры и поиск
- Table view для списков
- Связи между КП и организациями
- UI polish (toasts, loading, empty states)

### 📈 Прогресс:
- **Текущий:** 70% MVP
- **После Request 2:** 85% MVP
- **После Request 3:** 95% MVP
- **После Request 4:** 100% MVP ✅

### 🚀 Готово к:
- Экспорту в GitHub
- Локальной доработке в IDE
- Интеграции с вашим Python скриптом обработки писем
- Демонстрации заказчику

---

**Следующий шаг:** Скопировать промпт из REQUEST 2 и отправить в Orchids!