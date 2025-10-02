# Requirements — Phone Ownership Disambiguation

1. **Название телефона → организация**
   - Реализовать `resolve_phone_conflicts(organizations, contacts) -> (organizations, metadata)` в PostProcessor.
   - Эвристики:
     * `city_weight`: код города номера (по маске `+7 (383)` → сверяем с `org.city`).
     * `domain_weight`: домен e-mail контактов/организации.
     * `contact_weight`: если номер привязан к контактам с `organization_id=X`.
   - Побеждает организация с максимальным весом > остальных (задать порог, напр. `weight >= sum(others) + 0.1`).

2. **Метаданные**
   - Записывать конфликты в `processed_result['postprocessing_metadata']['phone_conflicts']` с деталями (`phone`, `resolved`, `kept_gid`, `removed_gids`, `reason`).
   - Для нерешённых выводить `status="unresolved"`.

3. **Промпт**
   - Добавить правило в `prompts/unified_contact_extraction_structured.txt` и пример, запрещающий перенос HQ-номеров в чужие организации.

4. **Overrides**
   - Расширить `GlobalIDRegistry`/health-check: поддержка `phone_overrides` (YAML), фиксация override в отчётах.
   - Отчёт `check_registry_health` должен показывать телефоны с множественными владельцами.

5. **Тесты**
   - Юнит: почтовые и телефонные сценарии (A/B/C — перенос, нерешённый, override).
   - Интеграция: примеры 018/019 → телефон остаётся у «МЕД КОНГРЕСС».

