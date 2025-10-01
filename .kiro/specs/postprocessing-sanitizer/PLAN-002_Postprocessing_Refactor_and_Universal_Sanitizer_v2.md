
# PLAN-001 (v2): Рефакторинг постпроцессинга + универсальная «обвязка» защиты от LLM-артефактов
**Статус:** актуальная версия. 

**Цель:** стабилизировать пайплайн на любом ответе LLM: убрать падения валидации и типовые ошибки в simplified/fallback, ввести управляемый backfill города/адреса контактов (только для пустых полей) и прозрачную телеметрию.

---

## Контекст и симптомы

- Валидация упала на двух файлах из партии (остальные 18 прошли):
  - `email_023_20250729_20250729_dna-technology_ru_a49e5653.json`
  - `email_024_20250729_20250729_dna-technology_ru_14c595b2.json`
- Из лога видно две проблемы:
  1) LLM добавил поле `confidence` в объект **организации** → JSON Schema с `additionalProperties: false` падает с ошибкой `Additional properties are not allowed ('confidence' was unexpected)`.
  2) В simplified/fallback-ветке применяется `re.sub`/regex к значению **типа int**, из-за чего падаем на `expected string or bytes-like object, got 'int'`.

> Источники: лог `api_pipeline_validator_20251001_180331_unknown.log` и содержимое JSON для двух писем.

### Гипотеза

- Почему только эти 2 файла? В них модель сгенерировала организационный confidence (для НГКПЦ и ФБУЗ ЦГиЭ в РХ с ИНН), тогда как в остальных письмах — нет.
- Вероятная триггер-логика LLM: когда встречает «явные реквизиты» (ИНН, точное наименование, явный end user), она добавляет «уверенность» на уровне организации — хотя в промпте мы это не просили.
- Автокорректор умеет править типы, но не чистит «лишние поля» — потому «Additional properties…» не починился.

---

## Область работ / файлы
Важно! Возможно указал не все файлы, которые нужно рефакторить. Проверить и дополнить, если нужно.
- `unified_contact_extraction_structured.txt` — промпт для LLM-модели.
- `validator.py` — предвалидационная очистка (whitelist), лог снятых полей.
- `postprocessor.py` — утилиты типов (`as_text/as_list/...`), порядок стадий, backfill города/адреса, нормализация enum/дат/чисел, кросс‑ссылки, телеметрия.
- `diagnostic_enricher.py` — лёгкая интеграция метрик (по желанию).
- `smart_contact_enricher.py` / `organization_deduplicator.py` — **без изменений** в логике (проверить совместимость по порядку вызовов).

---

## Технические требования

### 0) Небольшая правка промпта (guardrails)
В блок правил добавить одно предложение:  
> Запрещено добавлять поле `confidence` в `organizations[]`. Поле `confidence` допустимо только в `contacts[]` и `interactions[]`. Если сомневаешься — не добавляй.

(Это снижает частоту ошибок от LLM; окончательно проблему закрывают пункты 1–2 ниже.)

### 1) Предвалидационная очистка («санитайзер») в `validator.py`
- Перед jsonschema прогонять payload через `sanitize_payload(p: dict) -> dict`.
- Уровни очистки: **root**, **organizations[]**, **contacts[]**, **contacts[].phones[]**, **commercial_offers[]**, **equipment_items[]**, **interactions[]**, **interactions[].participants**.
- Белые списки ключей держать в словаре `ALLOWED`. Всё неизвестное — удалять.
- В `postprocessing_metadata.sanitizer.removed_props` писать массив объектов с полями `path`, `key`, `value_preview` (строки обрезаем до ≈120 символов, числа оставляем как есть, для крупных/чувствительных структур — маркер `"<redacted>"`).
- Санитайзер должен приводить строковые поля (телефоны, summary, КП, participants и т.п.) к строковому типу и фиксировать счётчик `converted_to_string` в `postprocessing_metadata.sanitizer`.
- Внутренности `postprocessing_metadata` **не** чистить (passthrough), чтобы не ломать метрики/отчёты.

### 2) Универсальные утилиты типов и безопасные regex в `postprocessor.py`
Добавить и использовать повсеместно:
```python
def as_text(x): 
    return "" if x is None else (x if isinstance(x, str) else str(x))
def as_int(x):
    try: return int(x)
    except: return None
def as_float(x):
    try: return float(x)
    except: return None
def as_list(x):
    if x is None: return []
    return x if isinstance(x, list) else [x]
```
- Любые `re.sub/search/findall` — только на `as_text(...)`.
- Поля‑массивы (`emails`, `phones`, `key_points`, `attachments`, `equipment_items`, `participants.audience`) — через `as_list(...)`.

### 3) Нормализация enum’ов и дат
- `interaction_type`, `role_in_message`: привести к lowercase, синонимы/опечатки → канон; неизвестное → `other`.
- Лог правок: `postprocessing_metadata.normalizer.enums_fixes`.
- Даты: принимать `DD.MM.YYYY`, `DD/MM/YYYY`, `YYYY-MM-DD`, ISO с временем; на выходе — ISO (`YYYY-MM-DD` или `YYYY-MM-DDTHH:MM:SS±hh:mm`). Не парсится → `null`, лог `...dates_invalid`.

### 4) Числовые поля (КП)
- Приводить `quantity`, `unit_price`, `total_price`, `total_cost` к числами (`None` при неуспехе).
- Если `quantity*unit_price != total_price` (с округлением) — пересчитывать `total_price`, лог `...price_mismatch`.
- Все числа ≥ 0.

### 5) Кросс‑ссылки/целостность
- Гарантировать, что `contacts[].organization_id`/`interactions[].organization_id` указывают на существующие `organizations[].organization_id`.
- Если организаций одна — auto‑attach; иначе неконсистентные сущности удалять, лог `...crosslink_fixes`.

### 6) Управляемый backfill города/адреса из организации (только для пустых полей)
- Флаги в `PostProcessor.__init__`:
  ```python
  self.backfill_city_from_org = True        # ВКЛ по умолчанию
  self.backfill_address_from_org = False    # ВЫКЛ по умолчанию
  ```
- Реализовать метод:
  ```python
  def _backfill_contact_city_address(self, contacts: list[dict], organizations: dict[int, dict]) -> tuple[list[dict], dict]:
      \"\"\"Возвращает (обновлённые контакты, provenance: {contact_id: {city_source/address_source: 'org_fallback'}}). 
      Подставляет значения только если у контакта поле пустое и флаг включён. Уже заполненные LLM значения не перезаписывает.\"\"\"
  ```
- Вызов **после** дедупа и фильтрации «ценных» контактов, **до** финальной нормализации.
- Не перезаписывать уже заполненные LLM значения.
- Прозрачность: писать источники в `postprocessing_metadata.provenance.contacts[contact_id]`.

### 7) Безопасный simplified/fallback
- Все входы в regex и текстовые фильтры завернуть в `as_text(...)`.
- Любые исключения — не падать пайплайном, логировать в `postprocessing_metadata.errors[]` (`path`, `exception`, `sample`).

### 8) Телеметрия/метрики
- В `postprocessing_metadata.stats` копить счётчики: `removed_props_count`, `enum_fixes_count`, `dates_invalid_count`, `price_mismatch_count`, `crosslink_fixes_count`, `backfill_city_count`, `backfill_address_count`.
- Краткий строковый отчёт для лога.

### 9) Порядок стадий (важно сохранить)
1) sanitize (validator) →  
2) org dedup →  
3) фильтрация «ценных» контактов →  
4) backfill city/address →  
5) enricher’ы →  
6) нормализация типов/enum/дат/чисел →  
7) проверка кросс‑ссылок →  
8) телеметрия/метаданные.

---

## Тест‑план

### Юнит‑тесты
- Санитайзер удаляет `organizations[].confidence` и любые неизвестные поля на заявленных уровнях.
- `as_text/as_list` корректно приводят типы (int/None/str/list).
- Enum‑нормализатор: «SENT_QUOTE», «Sent-Quote», «отправил кп» → `sent_quote`.
- Даты в разных форматах → ISO; мусор → `null`.
- Числа: корректная конверсия и пересчёт `total_price` при несоответствии.

### Интеграция/регресс
- Два проблемных файла проходят пайплайн без ошибок.
- Пустой `city` у контакта + `org.city="Москва"` → подставился (provenance).
- `city="Новокузнецк"` у контакта → не перезаписался.
- «Скаляр вместо массива» (`attachments: "file.pdf"`) → превращается в список.
- Исключения в fallback не валят пайплайн, а пишутся в метаданные.

---

## Definition of Done
- Все файлы партии, включая два проблемных, проходят без ошибок.
- Лишние поля не ломают валидацию и логируются в `removed_props`.
- Fallback устойчив к типам.
- Backfill работает только для пустых полей и отражён в provenance.
- Собирается телеметрия качества.
- Версия процессинга повышена (например, `1.3.0`); `09_PROMPTS_AND_VALIDATION.md` дополнен разделом «Универсальная предвалидация и нормализация».
