# Дизайн решений

## Архитектурный контекст
- Основной конвейер: LLM → PostProcessor → DataNormalizer → Validator.
- Для прозрачности источников используем `postprocessing_metadata` (уже допускает произвольные поля).

## Компоненты
1. **PostProcessor**
   - Добавить флаги конфигурации `backfill_city_from_org` и `backfill_address_from_org` с чтением из env/конфига (если доступно, иначе значения по умолчанию).
   - Вставить этап `_backfill_contact_city_address` между дедупликацией контактов и нормализацией.
   - Возвращать обновлённый список контактов и словарь provenance.
   - Мержить provenance в `processed_result['postprocessing_metadata']`.

2. **Метаданные**
   - Структура `postprocessing_metadata` будет расширена блоком `provenance = {'contacts': {contact_id: {...}}}`.
   - Для каждого контакта фиксируем `city_source`/`address_source` со значением `org_fallback`.

3. **DataNormalizer / Validator**
   - Без изменений логики: normalizer просто приводит уже обновлённые поля; схема контактов не меняется.

4. **Документация UI**
   - В `memory-bank/mini_crm_prd/07_FRONTEND_UI.md` описать отображение бейджа источника.

## Поток данных
1. LLM выдаёт контакты без HQ-адресов (уже обновлённый промпт).
2. PostProcessor:
   - Дедуплицирует контакты и организации.
   - Запускает `_backfill_contact_city_address`:
     - Только пустые значения.
     - Город по умолчанию включён, адрес — нет.
   - Возвращает изменённые контакты и provenance.
3. Обогащение/нормализация работает поверх обновлённых данных.
4. В итоговом `processed_result` в `postprocessing_metadata` видно происхождение.

## Альтернативы
- Перенести provenance в сами контакты (отказано: нарушает schema).
- Делать backfill в DataNormalizer (отказано: требуется контроль и метаданные до нормализации).

## Валидация и тестирование
- Добавить unit-тесты на `_backfill_contact_city_address` (A–E сценарии).
- Добавить интеграционный тест PostProcessor (mock organizations/contacts).
- Прогнать существующие тесты постпроцессора и валидатора.
