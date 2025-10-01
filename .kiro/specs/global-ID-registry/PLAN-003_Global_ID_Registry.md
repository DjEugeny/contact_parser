
# PLAN-003: Global ID Registry (без БД, с плавной миграцией в MySQL)

**Цель:** ввести стабильные глобальные идентификаторы (GID) для организаций и контактов уже сейчас, при файловом хранилище JSON, с последующей бесшовной миграцией в MySQL.  
**Результат:** у каждой организации и каждого контакта будет детерминированный публичный `gid` (UUIDv5/ULID), который **не меняется** при повторных прогонах, реимпортах, дедупликации или переносе в БД.

---

## 1) Принципы и термины

- **GID (Global ID)** — стабильный публичный идентификатор, используем **UUIDv5** (или ULID). Рекомендуем **UUIDv5** из детерминированного канонического ключа сущности (см. ниже).
- **NID (Numeric ID)** — внутренний автоинкремент в БД (появится после MySQL). Наружу его не светим, используется для FK/индексов.
- **Канонический ключ** — кортеж нормализованных признаков, по которому однозначно вычисляется `gid`. Ключ детерминирован, не зависит от порядка обработки файлов.
- **Реестр** — тонкий слой поверх папки с JSON: два JSONL‑файла (`organizations.jsonl`, `contacts.jsonl`) + in‑memory индексы при старте пайплайна.

---

## 2) Канонические ключи (canonical keys)

### 2.1 Организация (по убыванию надёжности)
1. `ИНН` (строго 10 или 12 цифр, без пробелов/текстов).
2. `website_domain` (e2LD: привести домен к нижнему регистру, удалить схемы/пути, привести к punycode; для `corp.dna-technology.ru` берём `dna-technology.ru`).
3. `(official_name_norm, city_norm)` — название без юр‑суффиксов (ООО/АО/ПАО/ИП/ФБУЗ/ФГБУ/ГБУЗ и т.п.), один пробел между словами, lower; город через единый справочник `city_registry`.
4. `(email_domain)` — если сайта нет, но есть корпоративный домен email (с теми же правилами e2LD/punycode).
5. Fallback: `(hash(name_norm + city_norm))` — как крайняя мера.

> Если впоследствии появляется более сильный признак, **gid не меняем**: новый ключ добавляется в `aliases`, а в `postprocessing_metadata.gid_assigned` фиксируем `match_rule="upgrade"`.

**Примеры ключей**:  
`("ORG","INN","7701234567")`  
`("ORG","DOMAIN","dna-technology.ru")`  
`("ORG","NAME_CITY","dnk-tekhnologiya","moskva")`

### 2.2 Контакт (заякорен на организацию)
1. `(org_gid, email_lower)` — лучший уникатор.
2. `(org_gid, phone_e164)` — если почты нет.
3. `(org_gid, name_norm, position_norm)` — когда нет ни почты, ни телефона (слабый ключ, но детерминированный).

**Примеры ключей**:  
`("CONTACT", "ORG_GID", "s.voronova@dna-technology.ru")`  
`("CONTACT", "ORG_GID", "+79001234567")`  
`("CONTACT", "ORG_GID", "voronova-svetlana","vedushchiy-menedzher")`

---

## 3) Формат «реестра» (без БД)

- Папка: `./registry/`
  - `organizations.jsonl` — по одной записи в строке:
    ```json
    {"gid":"<uuid>","key":["ORG","INN","7701234567"],"aliases":[["ORG","DOMAIN","dna-technology.ru"]],"created_at":"2025-10-01T12:00:00Z","deleted":false}
    ```
  - `contacts.jsonl` — аналогичная структура:
    ```json
    {"gid":"<uuid>","key":["CONTACT","<org_gid>","s.voronova@dna-technology.ru"],"aliases":[],"created_at":"2025-10-01T12:00:00Z","deleted":false}
    ```
- **Индексы при старте**: 
  - `key_index: dict[key_tuple] -> gid`
  - `gid_index: dict[gid] -> record`
  - Дополнительно: `aliases_index` (каждый alias мапится на тот же `gid`)
- **File‑lock** при записи (на Windows — `msvcrt.locking`, на Unix — `fcntl.flock`). Перед append выполняем `reload -> reconcile -> append`, чтобы подхватывать изменения других процессов. Для блокировок используем отдельные файлы `organizations.lock` / `contacts.lock`, не блокируя весь каталог.

---

## 4) UUID‑пространства имён (namespaces)

Для воспроизводимости зафиксировать два константных пространства имён:
```python
ORG_NS = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
CONTACT_NS = UUID("11111111-2222-3333-4444-555555555555")
```
> *Замените на собственные зафиксированные UUID один раз и больше не меняйте.*  
`gid = uuid5(ORG_NS, repr(org_key_tuple))` и `gid = uuid5(CONTACT_NS, repr(contact_key_tuple))`.

---

## 5) Нормализация признаков (канонизация)

- **ИНН**: оставить только цифры; длина 10/12, иначе игнорировать как ключ.
- **Домены**: вырезать схему (`http(s)://`), путь/параметры; нижний регистр; punycode; привести к e2LD (example.co.uk → example.co.uk; foo.bar.ru → bar.ru, если так решите в правилах).
- **Названия организаций**: убрать юр‑формы (ООО, АО, ПАО, ИП, ФБУЗ, ФГБУ, ГБУЗ, ЗАО, ОАО), кавычки/скобки, пунктуацию; зафиксировать словарь замен; оставить один пробел; `lower`.
- **Города**: трим, unicode‑нормализация, словарь синонимов/опечаток (Новокузнецк↔Новокузнецк).
- **Имя/должность контакта**: трим/сжать пробелы/нижний регистр; убрать точки в инициалах; дефисы сохранить.
- **Email**: `lower().strip()`; для ключа использовать ровно местную часть+домен.
- **Телефон**: хранить как есть, но для ключа — нормализовать в E.164 (только цифры + префикс страны).

---

## 6) Алгоритм resolve (псевдокод)

```python
def resolve_org(org_obj):  # dict из итогового JSON письма (после дедупа)
    key = build_org_key(org_obj)          # кортеж
    gid = key_index.get(key)
    if gid: return gid

    # нет точного ключа — ищем по алиасам (например, домен/название-город)
    for alias in build_possible_org_aliases(org_obj):
        gid = key_index.get(alias)
        if gid:
            # привяжем новый ключ как alias к найденному gid
            append_alias(gid, key)
            return gid

    # новая организация — генерируем gid
    gid = uuid5(ORG_NS, repr(key))
    append_record("organizations.jsonl", {"gid": gid, "key": list(key), "aliases": [], "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
    key_index[key] = gid
    gid_index[gid] = {"gid": gid, "key": list(key), "aliases": []}
    return gid
```

```python
def resolve_contact(contact_obj, org_gid):
    key = build_contact_key(contact_obj, org_gid)
    gid = key_index.get(key)
    if gid: return gid

    for alias in build_possible_contact_aliases(contact_obj, org_gid):
        gid = key_index.get(alias)
        if gid:
            append_alias(gid, key)
            return gid

    gid = uuid5(CONTACT_NS, repr(key))
    append_record("contacts.jsonl", {"gid": gid, "key": list(key), "aliases": [], "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
    key_index[key] = gid
    gid_index[gid] = {"gid": gid, "key": list(key), "aliases": []}
    return gid
```

> `resolve_org` / `resolve_contact` возвращают не только `gid`, но и служебные поля (`match_rule`, `key_tuple`, `alias_added`). Это позволяет PostProcessor писать диагностический лог и формировать `postprocessing_metadata.gid_assigned/gid_conflicts` без дополнительного анализа.

**Правило alias:** если позднее приходят новые, более сильные признаки, не меняем `gid`, а добавляем новый `key_tuple` в `aliases` того же `gid`.

---

## 7) Встраивание в текущий пайплайн

Позиция: **сразу после** дедупликации организаций и фильтрации «ценных» контактов и **до** backfill/enrich/нормализации.

1. Построить `org_gid` для каждой организации итогового JSON.
2. Построить `contact_gid` для каждого контакта (используя `org_gid`).
3. Записать `gid` в объекты:
   ```json
   "organizations": [{"organization_id":1, "gid":"<uuid>", ...}]
   "contacts": [{"contact_id":1, "organization_id":1, "gid":"<uuid>", ...}]
   ```
4. В `postprocessing_metadata.gid_assigned` писать список назначений: `{gid, match_rule, key_tuple, alias_added}`.
5. В UI и внешние интеграции отдавать **только** `gid` как публичный идентификатор.

---

## 8) Конфликты и ручные оверрайды

- **Конфликт совпадений** (разные организации совпали по слабому ключу):
  - Не менять `gid`, зафиксировать коллизию в `postprocessing_metadata.gid_conflicts`.
  - Добавить запись в `overrides.yml` в формате:
    ```yaml
    org_overrides:
      - key: ["ORG","NAME_CITY","dnk-tekhnologiya","moskva"]
        gid: "fixed-uuid-here"
    ```
  - На старте подгружать `overrides` и применять до вычислений.
  - При конфликте между override и существующей записью реестра используем override, а столкновение фиксируем в `postprocessing_metadata.gid_conflicts` (`existing_gid`, `override_gid`, `key`).
- **Слияние организаций** (решение менеджера):
  - Добавить alias из «лишнего» ключа к целевому `gid`; опционально пометить старый `gid` как `deleted:true`.

---

## 9) Производительность и конкуренция

- Индексы держать в памяти, JSONL дописывать «хвостом» (append‑only).
- При массовой обработке файлов — один менеджер реестра с очередью событий.
- Локи на запись файлов registry (flock/msvcrt) и атомарные rename при свалке на диск.

---

## 10) Миграция в MySQL (позже)

### 10.1 Схема таблиц
- `organizations (id BIGINT PK, gid CHAR(36) UNIQUE, inn VARCHAR(12) UNIQUE NULL, website_domain VARCHAR(255) UNIQUE NULL, name_norm, city_norm, created_at, updated_at)`
- `contacts (id BIGINT PK, gid CHAR(36) UNIQUE, org_id BIGINT FK, email_lower, phone_e164, name_norm, position_norm, created_at, updated_at)`
- `org_aliases (org_id FK, key_tuple JSON/TEXT)`
- `contact_aliases (contact_id FK, key_tuple JSON/TEXT)`
- Индексы: `UNIQUE(org_id, email_lower)`, `UNIQUE(org_id, phone_e164)`

### 10.2 Процедура миграции
1. Прочитать `registry/*.jsonl` → **upsert** в БД по `gid`.
2. Заполнить NID (`id`) автоинкрементом, проставить FK по `gid`.
3. В пайплайне продолжать публиковать `gid` (публичный), а внутри использовать `id` для связей/скорости.

---

## 11) Безопасность/конфиденциальность
- В реестре хранить только то, что необходимо для идентификации (не дублировать «богатые» персональные данные).
- Логи конфликтов/решений хранить в `postprocessing_metadata`, а не в самом реестре.

---

## 12) Определение готовности (DoD)
- Повторный прогон тех же писем выдаёт те же `gid` для одних и тех же сущностей.
- Разные письма, описывающие одну и ту же организацию/контакт, получают одинаковый `gid`.
- Появление новых, более сильных признаков **не меняет** `gid`, а добавляет alias.
- В JSON‑результатах появляются поля `organizations[].gid` и `contacts[].gid`.
- Есть `registry/*jsonl`, `overrides.yml` и метаданные `gid_assigned/gid_conflicts` (с `match_rule`, `key_tuple`, `alias_added`, `conflict_reason`).
- Регрессы зелёные; производительность не деградировала критично.

---

## 13) Мини‑скелет кода (Python)

```python
import uuid, time, json, os
from hashlib import sha256
from pathlib import Path

ORG_NS = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
CONTACT_NS = uuid.UUID("11111111-2222-3333-4444-555555555555")

def uuidv5(ns, key_tuple):
    return str(uuid.uuid5(ns, repr(key_tuple)))

def norm_inn(x): ...
def norm_domain(x): ...
def norm_name(x): ...
def norm_city(x): ...
def norm_email(x): return (x or "").strip().lower()
def norm_e164(x): ...

def org_key(o):
    inn = norm_inn(o.get("inn"))
    if inn: return ("ORG","INN", inn)
    dom = norm_domain(o.get("website"))
    if dom: return ("ORG","DOMAIN", dom)
    name, city = norm_name(o.get("name","")), norm_city(o.get("city",""))
    if name and city: return ("ORG","NAME_CITY", name, city)
    edom = norm_domain(o.get("email_domain"))
    if edom: return ("ORG","EMAIL_DOMAIN", edom)
    return ("ORG","FALLBACK", sha256((name+city).encode()).hexdigest()[:16])

def contact_key(c, org_gid):
    mail = norm_email(c.get("email"))
    if mail: return ("CONTACT", org_gid, mail)
    phones = c.get("phones") or []
    for ph in phones:
        e164 = norm_e164(ph.get("number"))
        if e164: return ("CONTACT", org_gid, e164)
    name = norm_name(c.get("name",""))
    pos  = norm_name(c.get("position",""))
    return ("CONTACT", org_gid, name, pos)

class JsonlRegistry:
    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.org_file = self.path / "organizations.jsonl"
        self.cnt_file = self.path / "contacts.jsonl"
        self.key_index = {}
        self.gid_index = {}
        self._load()

    def _load(self):
        for fp in [self.org_file, self.cnt_file]:
            if not fp.exists(): continue
            with fp.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    rec = json.loads(line)
                    gid = rec["gid"]
                    key = tuple(rec["key"])
                    self.key_index[key] = gid
                    self.gid_index[gid] = rec
                    for alias in rec.get("aliases") or []:
                        self.key_index[tuple(alias)] = gid

    def _append(self, fp, rec):
        with fp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def resolve_org(self, o):
        key = org_key(o)
        gid = self.key_index.get(key)
        if gid: return gid
        gid = uuidv5(ORG_NS, key)
        rec = {"gid": gid, "key": list(key), "aliases": [], "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
        self._append(self.org_file, rec)
        self.key_index[key] = gid
        self.gid_index[gid] = rec
        return gid

    def resolve_contact(self, c, org_gid):
        key = contact_key(c, org_gid)
        gid = self.key_index.get(key)
        if gid: return gid
        gid = uuidv5(CONTACT_NS, key)
        rec = {"gid": gid, "key": list(key), "aliases": [], "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
        self._append(self.cnt_file, rec)
        self.key_index[key] = gid
        self.gid_index[gid] = rec
        return gid
```
