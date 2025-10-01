# Mini-CRM — задачи MVP (2025-09-28)

## TODO
- [ ] Выполнить прогоны `first10` и `batch`, подготовить отчёты и обновить индекс
- [ ] Обновить `main_new.py` (режимы interactive/test/full-pipeline/async-*) с новым конвейером
- [ ] Настроить экспорт в Google Sheets и локальный CSV/XLSX fallback по `10_GOOGLE_SHEETS_INTERIM.md`
- [ ] Реализовать минимальный FastAPI + React PWA (поиск, карточки, реестр КП, модерация, просмотр письма, напоминания)
- [ ] Добавить backlog-задачу на сохранение `.eml` в fetcher
- [ ] Реализовать запись результатов в `crm.db` (DAO + миграция)

## IN-PROGRESS
- [x] Исправление JSON Schema валидатора для обработки ключей с подчеркиваниями от Replicate LLM
- [ ] Подготовка отчётов и артефактов после каждого этапа (см. `memory-bank/reports/plan_mini_crm_mvp_2025-09-28.md`)

## DONE
- [x] **КРИТИЧЕСКИЙ ПРОРЫВ:** Исправлен парсер JSON для Replicate LLM - теперь успешно извлекаются данные из писем (см. `memory-bank/reports/implementation_json_parser_fix_2025-09-28.md`)
- [x] Временно отключено кэширование в `src/core/extractor.py` для получения свежих результатов от LLM
- [x] Добавлен специальный фикс `_fix_replicate_spaces()` для обработки JSON с лишними пробелами
- [x] Унифицированы пути загрузки конфигурации и обновлены модули (`src/config/paths.py`, `advanced_email_fetcher`, экспортеры)
- [x] Превратить `api_pipeline_validator.py` в тонкий слой над `main_new.py`, добавить режимы `first10|batch|range|dry-run` (см. `memory-bank/reports/implementation_api_pipeline_validator_refactor_2025-09-28.md`)
- [x] Реализованы нормализация, scoring и fuzzy-дедуп по `11_DEDUP_ENRICH_RULES.md` с переиспользованием модулей `src/postprocessing`
- [x] Рефакторинг `src/core/extractor.py` и валидаторов под новый JSON-шаблон с `role_in_message`, `interactions[]`, фильтрацией КП`
- [x] Обновлён промпт `prompts/unified_contact_extraction_structured.txt` согласно `09_PROMPTS_AND_VALIDATION.md`
- [x] Реализован санитайзер валидатора и рефакторинг постпроцессинга (см. `memory-bank/reports/implementation_postprocessing_sanitizer_2025-10-01.md`)
- [x] Типизация строковых полей и фикса `simplified` стратегии (см. `memory-bank/reports/implementation_simplified_phone_sanitizer_2025-10-01.md`)
- [x] Создан план работ `memory-bank/reports/plan_mini_crm_mvp_2025-09-28.md`
