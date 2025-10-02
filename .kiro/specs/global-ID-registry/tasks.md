# PLAN-003 · Checklist задач

## 1. Каркас реестра
- [x] Создать пакет `registry/` с JSONL‑файлами `organizations.jsonl`, `contacts.jsonl` (append‑only).
- [x] Реализовать `JsonlRegistry` с индексами `key_index`, `gid_index`, `aliases_index` и отдельными lock‑файлами (`organizations.lock` / `contacts.lock`).
- [x] Добавить механизмы `reload -> reconcile -> append` при записи и логику file-lock (flock/msvcrt).

## 2. Нормализация и ключи
- [x] Реализовать утилиты нормализации: `norm_inn`, `norm_domain` (e2LD + punycode), `norm_name`, `norm_city`, `norm_email`, `norm_e164`.
- [x] Построить функции `build_org_key` / `build_contact_key` с приоритетами из плана (ИНН → домен → имя+город → email_domain → fallback). 
- [x] Зафиксировать UUID‑пространства имен `ORG_NS`, `CONTACT_NS` и helper `uuidv5(ns, key_tuple)`.

## 3. API реестра
- [x] `resolve_org` / `resolve_contact` должны возвращать структуру `{gid, match_rule, key_tuple, alias_added}` и поддерживать alias‑обновления.
- [x] Реализовать `append_alias(gid, key_tuple)` и обработку `overrides.yml` (приоритет overrides + логирование конфликтов).

## 4. Интеграция в PostProcessor
- [x] Встроить реестр после дедупликации организаций / фильтрации контактов, до backfill/enrich.
- [x] Проставлять `gid` в `organizations[]` и `contacts[]` финального JSON.
- [x] Заполнять `postprocessing_metadata.gid_assigned` / `gid_conflicts` (включая `match_rule`, `key_tuple`, `alias_added`, `conflict_reason`).

## 5. Тестирование
- [x] Юнит‑тесты: стабильность `gid`, совпадение сущностей из разных писем, деградация признаков → alias, ИНН/домен.
- [x] Интеграция: партия писем → `gid` везде, повторный прогон → те же `gid`, сценарий с overrides и конфликтами.
- [x] Проверка идемпотентности пользователем на реальных данных.

## 6. Документация
- [x] Обновить README/спецификацию: правила построения ключей, формат overrides, структура `postprocessing_metadata`.
- [x] Добавить раздел «Миграция в MySQL» (upsert по `gid`, заполнение `alias` таблиц).
- [x] Создать example файл overrides.yml с пояснениями.

## 7. DevOps/операционное
- [x] Добавить задачи в мониторинг: контроль размеров registry, наличие lock‑файлов, частоту `gid_conflicts`.
- [x] Подготовить процедуру резервного копирования `registry/*.jsonl`.
- [x] Создать скрипты: check_registry_health.py, backup_registry.py.

## 8. Дополнительно выполнено
- [x] Создан комплексный интеграционный тест (tests/integration/test_global_id_integration.py).
- [x] Полная документация с примерами использования (src/registry/README.md).
- [x] Автоматизированные скрипты мониторинга и бэкапа.

---

## ✅ Статус: ЗАВЕРШЕНО

**Дата завершения:** 2025-10-02  
**Версия:** 1.0.0

### Основные артефакты:
- `src/registry/global_registry.py` — реализация
- `src/registry/README.md` — документация
- `src/registry/overrides.yml.example` — пример конфигурации
- `tests/test_global_id_registry.py` — юнит-тесты
- `tests/integration/test_global_id_integration.py` — интеграционные тесты
- `scripts/check_registry_health.py` — мониторинг
- `scripts/backup_registry.py` — бэкапы

### Проверено:
✅ Идемпотентность (повторные прогоны)  
✅ Cross-email дедупликация  
✅ Метаданные gid в JSON результатах  
✅ Система приоритетов ключей  
✅ Механизм aliases  
✅ Overrides и конфликты  

### Готово к продакшену:
- ✅ Все тесты проходят
- ✅ Документация полная
- ✅ Мониторинг настроен
- ✅ Процедуры бэкапа готовы
