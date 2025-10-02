# PLAN-004 · Checklist задач

## 1. Детектор конфликтов телефонов
- [x] Реализовать `resolve_phone_conflicts` в PostProcessor.
- [x] Добавить веса (город/домен/контакты) и логику перераспределения.
- [x] Прописать `phone_conflicts` в `postprocessing_metadata`.

## 2. Конфигурация и overrides
- [x] Расширить health-check (`scripts/check_registry_health.py`) отчётом по телефонам.
- [x] Поддержать `phone_overrides` в registry/overrides (парсинг + применение).

## 3. Промпт
- [x] Обновить `prompts/unified_contact_extraction_structured.txt` новым правилом и примером HQ-адреса/телефона.

## 4. Тесты
- [x] Юнит-тесты для `resolve_phone_conflicts` (решённый, нерешённый, override).
- [x] Интеграционный тест на письмах 018/019 с проверкой `phone_conflicts`.

## 5. Документация/метаданные
- [x] Описать новый блок в `PLAN-003_Global_ID_Registry.md` / README.
- [x] Обновить DevOps-инструкции (как смотреть конфликты, добавлять overrides).

