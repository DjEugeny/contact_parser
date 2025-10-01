# Requirements — Postprocessing Sanitizer & Refactor

1. **Guardrails в промпте**
   - Обновить `prompts/unified_contact_extraction_structured.txt`: запрет на `organizations[].confidence`.
2. **Sanitize-слой в валидаторе**
   - Реализовать `sanitize_payload` с whitelists по уровням.
   - Поддержать вложенные коллекции (phones, equipment_items, participants).
   - Записывать массив `removed_props` в `postprocessing_metadata.sanitizer` с полями `path`, `key`, `value_preview` (обрезка/маскирование для больших и чувствительных значений).
3. **Утилиты конверсии в PostProcessor**
   - Добавить функции безопасной конверсии (`as_text`, `as_int`, `as_float`, `as_bool`, `as_list`, `safe_regex_sub`).
   - Использовать их во всех местах, где ранее была ручная обработка/regex над произвольными типами.
4. **Backfill и provenance**
   - Поддерживать мягкий backfill города/адреса только для пустых полей.
   - Фиксировать источник подстановки в `postprocessing_metadata.provenance`.
5. **Enum/Date/Price нормализация**
   - Нормализовать статусы взаимодействий и коммерческих предложений.
   - Переводить даты к ISO или `None`.
   - Пересчитывать `total_price`, если `unit_price * quantity` расходится.
6. **Fallback/Resilient fixes**
   - Убрать прямые regex над int/None; использовать безопасные утилиты.
   - Прокинуть ошибки fallback в метаданные, не роняя пайплайн.
7. **Телеметрия**
   - Логировать количество удалённых полей и срабатываний backfill.
8. **Регрессии/DoD**
   - Проблемные письма 023/024 проходят без ошибок.
   - Автотесты для санитайзера и утилит.
   - Smoke-прогон (минимум 5 писем) показывает корректную работу.
   - Обновить документацию (`09_PROMPTS_AND_VALIDATION.md`) и версию процессинга.
