PLAN-004: Org/End-User INN Enrichment (MVP: DaData-first, FNS = подтверждение позже; с кешем)

Цель: быстро и безопасно обогащать ИНН для всех организаций из писем (поставщик, посредник, конечный пользователь и т.д.) в режиме MVP:

первичный источник — DaData (кандидаты и авто-принятие по высоким порогам);

ФНС (ЕГРЮЛ/ЕГРИП) — только для подтверждения в следующей итерации (см. PLAN-005), либо вручную через UI;

обязательный кеш запросов, чтобы не тратить лимиты провайдера.

Контекст: GID уже назначается (PLAN-003), схема валидации жёсткая (additionalProperties:false), метаданные пишутся в postprocessing_metadata. Обогащение не должно ломать схему: в organizations[] добавляем только поле inn, всё служебное — в postprocessing_metadata.enrichment.org_inn.

0) Принципы MVP

DaData-first: в онлайне используем только DaData как источник кандидатов/ИНН.

Два порога:
auto-accept — высокий скор и единственный кандидат;
needs_review — средний скор или несколько кандидатов (ИНН в карточку не пишем).

Кеш обязан быть включён: и позитивный (нашли ИНН), и негативный (ничего не нашли). TTL настраиваем.

FNS=OFF в онлайне: подтверждение через ФНС будет запускаться батчем позже (см. PLAN-005).

Один ИНН на GID: ИНН хранится в карточке организации (по gid) и переиспользуется везде.

Никаких служебных полей в organizations[]: только inn. Остальное — в метаданные.

1) Где встраивать в пайплайн (MVP)

Порядок стадий:
sanitize → org dedup → фильтр «ценных» контактов → assign gid → org_inn_enrichment (DaData + cache only) → backfill/enrich → нормализация → кросс-ссылки → телеметрия.

Если у организации уже есть валидный ИНН (контрольная сумма/длина 10/12) — шаг пропускаем.

2) Конфигурация (пример)
org_inn_enrichment:
  enabled: true
  auto_accept_threshold: 0.85
  review_threshold: 0.65
  write_inn_on_auto_accept: true     # писать ИНН сразу при auto-accept
  providers:
    dadata:
      enabled: true
      api_key: "${DADATA_API_KEY}"
      timeout_ms: 3000
    fns:
      mode: "off"                    # off | online_confirm | batch_confirm
      timeout_ms: 6000
    rusprofile:
      enabled: false                 # опционально; можно включить позже
  cache:
    path: "registry/inn_cache.jsonl"
    negative_ttl_minutes: 60         # негативные результаты кешируем кратко
    positive_ttl_days: 180
  overrides_path: "registry/inn_overrides.yml"
  legal:
    allow_ip_inn: true
    store_personal_data: "minimal"

3) Нормализация и ключи поиска

name_norm: убрать юр-формы (ООО/АО/ПАО/ИП/ФБУЗ/ФГБУ/ГБУЗ и др.), кавычки/пунктуацию, сжать пробелы, lower.

city_norm: трим + словарь синонимов/ошибок.

address_norm: по возможности улица/дом (без корп./офиса).

domain/email_domain: e2LD, lower, punycode.
Запрос к провайдеру: (name_norm, city_norm, address_norm?, domain?).

4) Алгоритм (per-organization, MVP)

Skip-rule: если org.inn валиден — пропустить.

Overrides: поиск по inn_overrides.yml (ключ: org_gid и/или name_norm+city_norm). Если найдено → применить (decision=override, confidence=1.0, source=local).

Cache: проверяем inn_cache.jsonl:
• Позитив: вернуть ИНН и метаданные из кеша.
• Негатив (не найдено ранее) и TTL не истёк → reject без внешних запросов.

DaData: запрос → собрать кандидатов (inn, ogrn, name, address, opf, region).

Нормализация кандидатов: привести имя/адрес, снять дубли (по ИНН).

Скоинг: по совпадениям name_norm, city/region, address, domain/email, opf.

Принятие:
• auto-accept: max_score ≥ auto_accept_threshold и ровно один валидный ИНН → пишем organizations[].inn;
• needs_review: review_threshold ≤ max_score < auto_accept_threshold или несколько кандидатов → ИНН не пишем, создаём ревью-таск;
• reject: ниже порога → не пишем.

Кеширование:
• Успешные auto-accept → позитивный кеш (с source=dadata, score, checked_at).
• reject → негативный кеш с коротким TTL.
• needs_review → не кешируем как позитив; сохраняем кандидатов в метаданные.

FNS (MVP): не вызываем в онлайне (настройка fns.mode=off). Подтверждение — батчем по PLAN-005.

5) postprocessing_metadata (формат)
"postprocessing_metadata": {
  "enrichment": {
    "org_inn": {
      "<org_gid>": {
        "decision": "auto_accept | needs_review | reject | override | skipped",
        "inn": "7701234567",
        "confidence": 0.91,
        "source": "dadata | local | cache",
        "method": "name_city_search | domain_match",
        "score": 0.91,
        "candidates": [
          {"inn":"7701234567","name":"ООО «Название»","city":"Москва","opf":"ООО","score":0.91,"provider":"dadata"}
        ],
        "checked_at": "2025-10-02T10:10:00Z",
        "auto_accept_threshold": 0.85,
        "review_threshold": 0.65,
        "cache_hit": false
      }
    }
  }
}


Важно: это метаданные. В organizations[] добавляем только inn при auto-accept или override.

6) Кеш и оверрайды

registry/inn_cache.jsonl (append-only):

{"key":["ООО название","москва","example.ru"],"inn":"7701234567","source":"dadata","score":0.91,"checked_at":"2025-10-02T10:10:00Z","ttl_days":180}
{"key":["ооо одноимёнка","москва"],"inn":null,"source":"dadata","score":0.58,"checked_at":"2025-10-02T10:10:00Z","ttl_minutes":60}


registry/inn_overrides.yml (ручные подтверждения):

org_overrides:
  - org_gid: "58a4...10e3"
    inn: "7723537840"
    reason: "ручное подтверждение"
    confirmed_by: "user@srv"
    confirmed_at: "2025-10-02T10:20:00Z"

7) UI / Review-поток (MVP)

Для needs_review формируем задания с топ-кандидатами (название/адрес/ИНН, ссылка на карточку агрегатора).

Кнопки: Принять (записать inn), Отклонить, Выбрать другой.

Принятие → запись в organizations[].inn + inn_overrides.yml + метаданные.

Позднее (PLAN-005) добавится «Подтвердить по ФНС» для спорных записей.

8) Тест-план

Юнит: нормализация, контрольная сумма ИНН, скоринг, кеш (positive/negative), чтение overrides.
Интеграция:

org без ИНН → одиночный кандидат с высоким скором → auto-accept и запись inn;

несколько кандидатов/средний скор → needs_review;

плохой сигнал → reject;

повторный прогон → попадание в кеш, без внешних вызовов.
Регресс: обогащение не добавляет лишних полей в organizations[] (валидация ОК).

9) DoD (готовность MVP)

В JSON появляется organizations[].inn только при auto-accept/override.

Ведётся postprocessing_metadata.enrichment.org_inn с полным следом.

Кеш и overrides работают; повторные прогоны детерминированы.

FNS на онлайне выключен; подтверждение вынесено в батч (PLAN-005).

Производительность: негативный кеш резко снижает лишние запросы.