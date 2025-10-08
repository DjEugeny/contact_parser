# 🔧 План исправлений Mini-CRM в Orchids
**Дата:** 08.10.2025, 18:30 (обновлено)  
**Текущий статус:** MVP 90% готов  
**Лимиты:** 1 refill остался (100k tokens)  
**Стратегия:** 1 финальный промпт для завершения MVP до 100%

---

## ✅ REQUEST FINAL — ВЫПОЛНЕНО (частично)

**Что было сделано:**

✅ **Выполнено полностью:**
- Email опциональный в форме контакта
- Нормализация телефонов при редактировании
- Кнопка "Добавить организацию" создана
- Дашборд улучшен (4+2 виджета, компактный дизайн)

⚠️ **Выполнено частично:**
- Связи КП-Организации (FK добавлены, но данные не совпадают)
- Сайты кликабельные (иконка есть, но нужен Command+Click)
- Статус "Не задан" (добавлен, но не сохраняется)

❌ **Не работает:**
- Телефоны не сохраняются при создании контакта
- Если телефона нет в существующей карточке контакта, то добавление его при редактировании не удаётся, как если бы телефон добавляли при создании контакта. А если телефон уже имеется, то отредактировать его можно корректно.
- Копирование ИНН не работает


---

## 📋 REQUEST FINAL-2 — ИСПРАВЛЕНИЕ БАГОВ

**Цель:** Исправить 6 критичных багов для достижения MVP 100%

### 🎯 Что делаем:

**ПРИОРИТЕТ 1: КРИТИЧНЫЕ БАГИ (блокируют работу)**

1. **❌ КРИТИЧНО: Телефоны не сохраняются при создании контакта**
   - Нормализация работает при редактировании
   - НО при создании нового контакта телефоны вообще не попадают в contact_phones
   - Нужно исправить API запрос или backend обработку

2. **⚠️ Исправить связи КП-Организации**
   - ✅ FK добавлены (end_user_org_id, intermediary_org_id)
   - ❌ Только 1 организация линкуется (неверное название)
   - ❌ Организации в КП не совпадают с /organizations
   - Решение: обновить моковые данные КП с реальными названиями организаций из таблицы organizations

3. **❌ Сайты требуют Command+Click**
   - ✅ Иконка внешней ссылки добавлена
   - ❌ Обычный клик не работает, нужен Command+Click
   - Исправить: обычный клик должен открывать в новой вкладке

4. **❌ Копирование ИНН не работает**
   - Показывает "Ошибка копирования ИНН" или "Ошибка копирования"
   - ИНН не попадает в буфер обмена
   - Проверить navigator.clipboard.writeText()

5. **❌ Статус "Не задан" не сохраняется**
   - ✅ Статус добавлен в dropdown и фильтр
   - ❌ При изменении: "Ошибка изменения статуса" (/offers)
   - ❌ В карточке КП: статус меняется на секунду, возвращается к прежнему
   - ❌ Toast "Статус обновлен", но изменения не сохраняются в БД
   - Проверить API endpoint для обновления статуса

**ПРИОРИТЕТ 2: МЕЛКИЕ ИСПРАВЛЕНИЯ**

6. **⚠️ Несоответствие счётчиков контактов**
   - Dashboard виджет: 33 контакта
   - Страница /contacts: 31 контакт
   - Синхронизировать данные

### 📝 Промпт для Orchids (REQUEST FINAL-2):

```
Critical bug fixes to complete Mini-CRM MVP (90% → 100%):

PRIORITY 1: CRITICAL BUGS (must fix for MVP 100%)

1. FIX PHONES NOT SAVING when creating new contact:

Current status:
✅ Email is now optional (FIXED)
✅ Phone normalization works in EDIT contact form (FIXED)
❌ Phones DON'T SAVE when CREATING new contact (CRITICAL BUG)

The problem:
- Phone normalization logic exists and works correctly in edit form (src/app/contacts/[id]/page.tsx)
- Same logic exists in create form (src/app/contacts/page.tsx)
- BUT phones are not being saved to contact_phones table when creating new contact
- Possible causes:
  • API request not sending phones array
  • Backend not processing phones array
  • INSERT into contact_phones table failing silently

Required fix:
A) Debug and fix phone saving in create contact form:
- Check if phones array is being sent in API request body
- Verify API endpoint receives and processes phones array
- Ensure INSERT into contact_phones table is executed
- Add error logging to identify where it fails

B) Test cases that should work after fix:
- Create contact with phone 89137081290 → should save as +7 (913) 708-12-90
- Create contact with phone 9137081290 → should save as +7 (913) 708-12-90
- Create contact with phone +79137081290 → should save as +7 (913) 708-12-90
- Create contact with multiple phones → all should save
- Create contact without phone → should save contact without error

C) Verify normalization is applied:
- Display format: +7 (913) 708-12-90 (in number field)
- Normalized format: 79137081290 (in normalized field, digits only)

IMPORTANT: The normalization logic already works in edit form, so copy the same approach to create form's API handling.

2. FIX commercial offers to organizations linking:

Current status:
✅ FK columns added (end_user_org_id, intermediary_org_id)
✅ Migration executed
✅ КП tab appears in organization card
❌ Only 1 organization links (wrong name)
❌ Organization names in offers don't match /organizations page

The problem:
- Mock data in commercial_offers uses organization names that don't exist in organizations table
- Example: offer has "ООО Техносфера" but organizations table has "Техносфера ООО"
- Need to update mock data to use EXACT names from organizations table

Required fix:
A) Update commercial_offers mock data:
- Get list of actual organization names from organizations table
- Update end_user and intermediary fields in commercial_offers to use these exact names
- Re-run migration to set FK relationships
- Ensure at least 10-15 offers have valid organization links

B) Verify display logic works:
- In /offers table: organization names should be clickable links
- In /offers/:id card: both end_user and intermediary should link to org cards
- In organization card: КП tab should show all related offers

3. FIX organization websites - remove Command+Click requirement:

Current status:
✅ External link icon added
✅ Works in all locations (grid, table, card)
❌ Still requires Command+Click to open

The problem:
- Link has target="_blank" but regular click doesn't work
- User must use Command+Click (Mac) or Ctrl+Click (Windows)

Required fix:
- Ensure onClick handler doesn't prevent default behavior
- Remove any event.preventDefault() or event.stopPropagation() on link
- Test: regular click should open website in new tab without modifier keys

4. FIX INN copy button:

Current status:
❌ Shows "Ошибка копирования ИНН" (organization card)
❌ Shows "Ошибка копирования" (organization list)
❌ INN not copied to clipboard

The problem:
- navigator.clipboard.writeText() might be failing
- Possible causes:
  • HTTPS required for clipboard API
  • Permission denied
  • INN value is null/undefined
  • Async/await not handled correctly

Required fix:
A) Debug clipboard API:
- Check if navigator.clipboard is available
- Add try-catch with detailed error logging
- Verify INN value exists before copying

B) Add fallback method:
- If clipboard API fails, use document.execCommand('copy')
- Create temporary textarea, select text, execute copy command

C) Test cases:
- Copy INN from organization card → should work
- Copy INN from organization list (grid view) → should work
- Copy INN from organization list (table view) → should work

5. FIX "Не задан" status not saving:

Current status:
✅ Status added to dropdown and filter
✅ Color: light gray (correct)
❌ Status change shows "Ошибка изменения статуса" on /offers page
❌ In offer card: status changes for 1 second, then reverts
❌ Toast shows "Статус обновлен" but changes don't persist in database

The problem:
- Frontend sends status update request
- Backend might not recognize "not_set" or "Не задан" value
- Database UPDATE fails silently
- Frontend shows optimistic update, then reverts on refresh

Required fix:
A) Check backend API endpoint for status update:
- Verify it accepts "not_set" as valid status value
- Add "not_set" to status enum/validation
- Ensure database column allows this value

B) Check database schema:
- commercial_offers.status column should allow "not_set"
- If using ENUM, add "not_set" to allowed values
- If using CHECK constraint, update to include "not_set"

C) Test status update:
- Change status to "Не задан" on /offers page → should save
- Change status to "Не задан" in offer card → should save
- Filter by "Не задан" status → should show offers with this status
- Assign "Не задан" to 2-3 existing offers for testing

6. FIX contact count mismatch:

Current issue:
- Dashboard widget shows: 33 contacts
- /contacts page shows: 31 contacts
- Data mismatch

Required fix:
- Check query for dashboard widget count
- Check query for /contacts page count
- Ensure both use same data source (contacts table)
- Possible causes:
  • Dashboard counts deleted contacts
  • Dashboard includes contacts without organization
  • Different WHERE clauses
- Synchronize to show same count (31 or 33, whichever is correct)

NOTES:
- All text in Russian
- Use existing design system (Tailwind CSS, #2862F6 accent)
- Add toast notifications for all actions (success/error)
- Validate all forms before submit
- Handle errors gracefully with user-friendly messages
- Test all changes on desktop (mobile not required for MVP)

IMPLEMENTATION ORDER:
1. Fix phones not saving when creating contact (CRITICAL)
2. Expand organization form with email/phones + add mock data
3. Fix offers-organizations linking (update mock data with real org names)
4. Fix website links (remove Command+Click requirement)
5. Fix INN copy button (debug clipboard API + add fallback)
6. Fix "Не задан" status not saving (backend + database)
7. Fix contact count mismatch (synchronize queries)

After completion, MVP will be 100% ready! 🚀
```

---

## � ИТОUГОВЫЙ ПЛАН

| Приоритет | Задачи | Результат |
|-----------|--------|-----------|
| **Приоритет 1** | 3 критичных бага | MVP 85% → 95% |
| **Приоритет 2** | 4 улучшения UX | MVP 95% → 100% ✅ |

**Итого:** 1 большой промпт для завершения MVP

---

## 🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После выполнения всех исправлений:

### ✅ Полный MVP 100%:
- Телефоны сохраняются при создании контактов
- Формы организаций с email/телефонами
- Связи КП-Организации работают корректно
- Сайты открываются обычным кликом
- Копирование ИНН работает
- Статус "Не задан" сохраняется
- Счётчики синхронизированы

### 📈 Прогресс:
- **После REQUEST FINAL:** 90% MVP
- **После REQUEST FINAL-2:** 100% MVP ✅

### 🚀 Готово к:
- Экспорту в GitHub
- Локальной доработке в IDE
- Интеграции с Python скриптом обработки писем
- Демонстрации заказчику
- Продуктивному использованию

---

## 🟡 ПРИОРИТЕТ 3 (опционально, можно отложить)

Эти задачи не критичны для MVP и могут быть реализованы позже:

8. **Каскадные фильтры**
   - Фильтр по городу влияет на фильтр по организациям
   - Улучшает UX, но не блокирует работу

9. **Фильтр по дате добавления контактов**
   - Date range picker для фильтрации по created_at
   - Полезно для больших баз данных
   - Фильтр по городу "Екатеринбург" → фильтр по организациям показывает только организации из Екатеринбурга

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

### 🎯 Что делаем:

1. **UI Polish (мелкие улучшения)**
   - Добавить loading skeletons для всех списков
   - Добавить empty states:
     • "Нет контактов" (если список пустой)
     • "Нет организаций"
     • "Нет писем"
   - Добавить confirmation dialogs для delete actions
   - Добавить success/error toasts для всех операций
   - Проверить все тексты на русском (исправить опечатки)


### 📝 Промпт для Orchids:

```
Final polish and placeholders for Mini-CRM:

1. Add loading states:
- Show skeleton loaders while fetching:
  • Contact list
  • Organization list
  • Offer list
  • Email list
  • Card pages
- Use placeholder cards/rows with shimmer effect

2. Add empty states:
- When no data:
  • Contacts: "Нет контактов. Добавьте первый контакт." + button "Добавить"
  • Organizations: "Нет организаций. Добавьте первую организацию."
  • Offers: "Нет коммерческих предложений."
  • Emails: "Нет писем. Письма появятся после загрузки из почтового ящика."
- Style: centered, icon, text, action button

3. Add confirmation dialogs:
- Before delete operations:
  • "Удалить контакт [NAME]? Это действие нельзя отменить."
  • Buttons: "Отмена" / "Удалить" (red)
- Before other destructive actions

4. Add toast notifications for all actions:
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

5. Fix all Russian text:
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

## 📊 ИТОГОВЫЙ ПЛАН

| Запрос | Статус | Задачи | Результат |
|--------|--------|--------|-----------|
| **REQUEST FINAL** | ✅ Частично | 7 задач (4 выполнено, 3 частично) | MVP 85% → 90% |
| **REQUEST FINAL-2** | 🔄 В работе | 7 критичных багов | MVP 90% → 100% ✅ |

**Итого:** 2 больших промпта для завершения MVP

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