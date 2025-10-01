# Дизайн: классификация и фильтрация email ящиков

## Архитектура
- Новый модуль `src/postprocessing/email_classifier.py` с классами/функциями для классификации почтовых адресов.
- Конфигурация `config/org_profile.yml` содержит корпоративные домены и префиксы.
- PostProcessor вызывает классификатор перед финальной сборкой результата, управляется флагами.
- OrganizationDeduplicator фильтрует персональные email при объединении организаций.
- DiagnosticEnricher собирает статистику/логи классификации.

## Компоненты
1. **email_classifier.py**
   - Enum `MailboxType`.
   - Функция `classify_mailbox(address, display_name, corp_domains, cfg)`; возвращает `MailboxType`.
   - Поддержка паттернов: shared/department/technical/group_alias, ФИО-детектор для персональных.

2. **Конфиг org_profile.yml**
   - `internal_domains`.
   - `shared_mailboxes_prefixes`, `technical_prefixes`, `group_alias_suffixes`.
   - Можно расширять без правок кода.

3. **PostProcessor**
   - Флаги: `keep_only_shared_org_emails`, `demote_personal_org_emails_to_contacts`, `email_classifier_config_path`.
   - Этап: очистка `organizations[].emails`, формирование `provenance`/`email_classification`.
   - Перенос персональных email не создаёт новых контактов, но логирует удалённые.

4. **OrganizationDeduplicator**
   - При слиянии проверяет тип почты, персональные не добавляет.

5. **DiagnosticEnricher**
   - Метод получает статистику классификатора: `count_by_type`, `removed_from_org`, `kept`.

6. **Интеграция**
   - SmartContactEnricher может использовать классификатор для внутреннего лога (без изменения API).

## Поток данных
LLM → PostProcessor (дедуп) → классификация email → фильтрация/лог → обогащение → нормализация → финальный результат.

## Исключённые альтернативы
- Полный автосоздание контактов для каждого почтового адреса (отложено).
- Изменение JSON Schema (запрещено).

## Тестирование
- Unit: `email_classifier`, логика PostProcessor.
- Интеграция: проверка JSON результата и `postprocessing_metadata`.
- Диагностика: сверка подсчитанных типов.

