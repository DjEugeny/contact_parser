# План работ

- [x] Добавить параметры `backfill_city_from_org` и `backfill_address_from_org` в `PostProcessor` (init + конфиг).
- [x] Реализовать `_backfill_contact_city_address` по описанным правилам (city по умолчанию, address выключен).
- [x] Включить этап backfill в `process_llm_response`, возвращать обновлённые контакты и `provenance` в `postprocessing_metadata`.
- [x] Обновить `07_FRONTEND_UI.md`: описать отображение бейджа источника для города/адреса.
- [x] Написать/обновить тесты (unit + интеграция) на сценарии A–E.
