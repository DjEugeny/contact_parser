# Requirements — Simplified Strategy Phone Sanitizer Fix

1. **Sanitizer enhancements (`src/core/validator.py`)**
   - `contacts[].phones[]`: гарантировать, что ключи `number`, `formatted`, `normalized`, `original`, `extension` сохраняются строками (`str(value)` + trim).
   - `contacts[]`: привести строковые поля (`name`, `position`, `email`, `city`, `address`, `role_in_message`) к строкам; пустые / None оставить `None`.
   - `organizations[]`: список `phones` и `emails` — массив строк (обрезать пробелы); `city`/`address`/`website` → строки.
   - `commercial_offers[].equipment_items[]`: поля `name`, `model`, `article`, `vat` → строки.
   - `interactions[]`: `summary`, `message_subject`, `message_date`, `message_id_hint` → строки; `participants.actor`/`audience` элементы → строки.
   - Логировать количество конверсий (например, `sanitizer.converted_to_string`).

2. **PostProcessor safety (`src/postprocessing/postprocessor.py`)**
   - При обработке контактов и organizations дополнительно приводить потенциально числовые строки через `as_text` (например, `contact['name']`, `interaction['summary']`, `offer['comments']`).
   - Удостовериться, что по пути `simplified` и `fallback` Conversions дают строку.

3. **Telemetry**
   - В `postprocessing_metadata.sanitizer` добавлять `converted_to_string` с количеством полей, приведённых к строке.

4. **Тесты**
   - Юнит-тест санитайзера: вход с `phones: [{'number': 89031234567}]` → после валидации `number` — строка.
   - Юнит-тест postprocessor: контакт с int-номером обрабатывается без исключений.
   - Интеграционный smoke (письмо `email_016_...6360137e.json`) — проходит без падений на `simplified`.

5. **Документация**
   - Обновить `.kiro/specs/postprocessing-sanitizer/design.md` / PLAN-002 (пометка о типизации полей).

