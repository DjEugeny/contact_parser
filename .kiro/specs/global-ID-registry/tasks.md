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
- [ ] Интеграция: партия писем → `gid` везде, повторный прогон → те же `gid`, сценарий с overrides и конфликтами.

## 6. Документация
- [ ] Обновить README/спецификацию: правила построения ключей, формат overrides, структура `postprocessing_metadata`.
- [ ] Добавить раздел «Миграция в MySQL» (upsert по `gid`, заполнение `alias` таблиц).

## 7. DevOps/операционное
- [ ] Добавить задачи в мониторинг: контроль размеров registry, наличие lock‑файлов, частоту `gid_conflicts`.
- [ ] Подготовить процедуру резервного копирования `registry/*.jsonl`.
