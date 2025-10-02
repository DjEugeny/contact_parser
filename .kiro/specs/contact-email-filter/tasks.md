# План задач

## Фаза 1: Реализация фильтрации (завершена)
- [x] Создать `config/org_profile.yml` с доменами и префиксами.
- [x] Реализовать `src/postprocessing/email_classifier.py` (Enum + classify_mailbox).
- [x] Интегрировать классификатор в PostProcessor (флаги, фильтрация, метаданные).
- [x] Обновить OrganizationDeduplicator для пропуска персональных email.
- [x] Добавить логику в DiagnosticEnricher и SmartContactEnricher (если нужно) для статистики.
- [x] Написать/обновить тесты (unit + интеграция) и запустить pytest.
- [x] Обновить документацию/UI при необходимости.

## Фаза 2: Исправление проблемы LLM (2025-10-02)
- [x] **Диагностика:** Обнаружена проблема - LLM помещает персональные адреса в organizations.emails
- [x] **Анализ:** Проверены RAW файлы - проблема на стороне LLM, не постобработки
- [x] **Решение 1:** Обновлен промпт с явными инструкциями о типах email (✅ [`prompts/unified_contact_extraction_structured.txt`](prompts/unified_contact_extraction_structured.txt:12-19))
- [x] **Решение 2:** Проверены настройки .env - флаги фильтрации включены по умолчанию
- [x] **Документация:** Обновлена спецификация с описанием проблемы (✅ [`PLAN-001`](.kiro/specs/contact-email-filter/PLAN-001_Email_Classifier_and_OrgEmails_Cleanup.md:12-37))
- [-] **Тестирование:** Перезапустить обработку проблемных писем
- [ ] **Валидация:** Проверить, что персональные адреса удалены из organizations.emails
- [ ] **Отчет:** Создать отчет о проблеме и решении в memory-bank/reports/

## Проблемные файлы для перепроверки:
- email_024_20250729 (m.gogoleva, prisyazhnyuk)
- email_025_20250729 (m.gogoleva, prisyazhnyuk)
- email_026_20250729 (m.gogoleva, prisyazhnyuk)
