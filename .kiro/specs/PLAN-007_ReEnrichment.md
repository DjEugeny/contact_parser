
# PLAN-007: Batch Re‑Enrichment & FNS Confirmation (после MVP)

**Цель:** после запуска MVP (DaData-first) массово подтвердить/дополнить ИНН через **ФНС** и довычистить спорные случаи. Работает как офлайн‑задача поверх уже сохранённых результатов (JSON‑папка или БД).

---

## 0) Когда запускать
- Когда накопились организации с `needs_review` или `inn=null`.  
- Когда появились доступы/квоты ФНС.  
- Периодически (ночью/по расписанию) для догонки качества.

---

## 1) Источники данных
- **Если БД уже есть:** читаем `organizations` по `gid` с `inn IS NULL` или `enrichment.status IN ('needs_review','reject')`.  
- **Если только JSON‑папка:** обходим файлы, собираем уникальные `org_gid` и их признаки; читаем метаданные `postprocessing_metadata.enrichment.org_inn`.

---

## 2) Алгоритм батча
1) Сформировать очередь `org_gid` к обработке:
   - `inn IS NULL`,  
   - либо `last_decision in {'needs_review','reject'}`,  
   - либо «подтвердить auto‑accept от DaData» (по конфиг‑флагу).
2) Для каждого `org_gid`:
   - Проверить **overrides** → если есть → применить.  
   - Проверить **кеш** (positive/negative) → при актуальном результате пропустить.  
   - **DaData (опционально):** обновить кандидатов (если с момента MVP прошёл TTL).  
   - **ФНС (обязательно):**  
     • если есть кандидаты с ИНН → запрос карточки/проверка существования по ИНН;  
     • если ИНН нет → поиск по названию/адресу → кандидаты → сверка.  
   - Скоинг/решение:  
     • `confirmed` (ФНС подтвердила единственного кандидата) → записать `inn`, `decision=confirmed`, `source=fns`;  
     • `needs_review` (несколько или средний скор) → задача в UI;  
     • `reject` (ничего достоверного) → негативный кеш + лог причин.  
   - Обновить **кеш** (positive/negative) и **метаданные**.
3) Соблюдать лимиты/таймауты/бэкофф.

---

## 3) Конфигурация
```yaml
re_enrichment:
  enabled: true
  sources:
    fns:
      enabled: true            # основной подтверждающий источник
      timeout_ms: 6000
    dadata:
      refresh_candidates: true # обновлять кандидатов при истёкшем TTL
      timeout_ms: 3000
  cache:
    use_existing: true
    update_positive: true
    update_negative: true
  selection:
    include_autoaccept_from_mvp: false  # при true — подтвердим и их по ФНС
    only_null_inn: false                # при true — обрабатываем только пустые
  io:
    input: "json_folder | database"
    write_mode: "in_place | sidecar"    # переписывать файлы или писать рядом
  concurrency:
    workers: 4
    rate_limit_per_source_per_minute:
      fns: 30
      dadata: 120
```

---

## 4) Запись результатов
- **JSON‑хранилище:** при `write_mode=in_place` дописываем `organizations[].inn` и `postprocessing_metadata` в файлы; при `sidecar` — пишем отдельный JSONL/CSV маппинг `{org_gid -> inn, provenance}`.  
- **БД:** обновляем `organizations.inn`, логируем в таблицу `org_inn_audit` (`org_gid`, `source`, `decision`, `score`, `checked_at`, `raw_ref`).

---

## 5) Метаданные и аудит
В `postprocessing_metadata.enrichment.org_inn[org_gid]` добавляем новые события:  
- `decision: confirmed | reject | needs_review`,  
- `source: fns_integration | fns_public`,  
- `link/ref`: идентификатор запроса или ссылка на карточку,  
- `previous_decision`: какое было на этапе MVP,  
- `attempt`: номер попытки батча.

---

## 6) Тест‑план
- Батч обрабатывает только целевые организации (по селектору).  
- FNS подтверждает `auto-accept` → статус `confirmed`, `inn` обновлён/оставлен как есть.  
- Спорные случаи → `needs_review` с корректным набором кандидатов.  
- Отрицательные результаты кешируются на короткий срок.  
- Повторный запуск батча идемпотентен (по `gid` + кеш).  
- Валидация JSON не падает (служебные поля — только в метаданные).

---

## 7) DoD
- Массовое подтверждение по ФНС выполнено без превышения лимитов.  
- Все `inn=null` или `needs_review` корректно обработаны.  
- Аудит и кеш обновлены; повторные запуски не создают дублей.  
- UI‑очередь ревью содержит только действительно спорные кейсы.
