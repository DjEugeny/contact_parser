# Global ID Registry (GID) — Документация

## 📋 Обзор

Global ID Registry — система детерминированных глобальных идентификаторов для организаций и контактов в проекте Mini-CRM. Обеспечивает стабильность идентификаторов при повторных прогонах, реимпортах и последующей миграции в MySQL.

## 🎯 Ключевые принципы

- **Детерминированность**: Один и тот же объект всегда получает один и тот же `gid`
- **Стабильность**: `gid` не меняется при появлении новых признаков (добавляются aliases)
- **Публичность**: `gid` используется во всех внешних интеграциях и API
- **Приоритеты ключей**: ИНН > домен > название+город > email_domain > fallback

## 🏗️ Архитектура

### Структура реестра

```
src/registry/
├── organizations.jsonl      # Реестр организаций (append-only)
├── contacts.jsonl           # Реестр контактов (append-only)
├── organizations.lock       # Lock-файл для organizations.jsonl
├── contacts.lock            # Lock-файл для contacts.jsonl
├── overrides.yml            # Ручные переопределения (опционально)
└── global_registry.py       # Основная логика
```

### Формат записи (JSONL)

**Событие создания организации:**
```json
{
  "event": "create",
  "gid": "58a49494-b44e-5b2f-9263-0ce9005f10e3",
  "key": ["ORG", "DOMAIN", "dna-technology.ru"],
  "aliases": [
    ["ORG", "INN", "7723537840"],
    ["ORG", "NAME_CITY", "днк-технология", "москва"]
  ],
  "created_at": "2025-10-02T03:30:38Z",
  "source": "new"
}
```

**Событие добавления alias:**
```json
{
  "event": "alias",
  "gid": "58a49494-b44e-5b2f-9263-0ce9005f10e3",
  "alias": ["ORG", "EMAIL_DOMAIN", "dna-technology.ru"],
  "created_at": "2025-10-02T03:33:03Z"
}
```

## 🔑 Канонические ключи

### Организации (приоритет сверху вниз)

1. **ИНН** — `["ORG", "INN", "7723537840"]`
   - Только цифры, длина 10 или 12
   - Самый надёжный идентификатор

2. **Домен (e2LD)** — `["ORG", "DOMAIN", "dna-technology.ru"]`
   - Приводится к effective 2nd-level domain (corp.dna-technology.ru → dna-technology.ru)
   - Нижний регистр, punycode для IDN

3. **Название + Город** — `["ORG", "NAME_CITY", "днк-технология", "москва"]`
   - Название: без юр.форм (ООО/АО/ПАО/ИП), нижний регистр
   - Город: нормализация через справочник

4. **Email домен** — `["ORG", "EMAIL_DOMAIN", "dna-technology.ru"]`
   - Если нет website, но есть корпоративные email

5. **Fallback** — `["ORG", "FALLBACK", "bdf7a3c4b01845b1"]`
   - SHA256 hash первых 16 символов от (name_norm + city_norm)

### Контакты (привязаны к организации)

1. **Email** — `["CONTACT", "EMAIL", "<org_gid>", "m.gogoleva@dna-technology.ru"]`
   - Лучший уникатор для контакта

2. **Телефон (E.164)** — `["CONTACT", "PHONE", "<org_gid>", "+79951293976"]`
   - Нормализация: 8 → +7, удаление разделителей

3. **Имя + Должность** — `["CONTACT", "NAME_POSITION", "<org_gid>", "воронова светлана", "представитель"]`
   - Слабый ключ, но детерминированный

## 💻 Использование

### Базовый пример

```python
from src.registry import GlobalIDRegistry

# Инициализация
registry = GlobalIDRegistry()

# Резолв организации
org = {
    "name": "ООО ДНК-Технология",
    "inn": "7723537840",
    "website": "https://dna-technology.ru",
    "city": "Москва",
    "emails": ["info@dna-technology.ru"]
}

result = registry.resolve_organization(org)
print(f"GID: {result.gid}")
print(f"Match rule: {result.match_rule}")  # "INN"
print(f"Key: {result.key_tuple}")
print(f"Alias added: {result.alias_added}")

# Резолв контакта
contact = {
    "name": "Гоголева Мария",
    "email": "m.gogoleva@dna-technology.ru",
    "phones": [{"number": "+7(495) 640-17-71"}]
}

contact_result = registry.resolve_contact(contact, org_gid=result.gid)
print(f"Contact GID: {contact_result.gid}")
```

### Интеграция в PostProcessor

Реестр автоматически интегрирован в `PostProcessor`:

```python
from src.postprocessing.postprocessor import PostProcessor

postprocessor = PostProcessor()
llm_result = {...}  # Результат от LLM

processed = postprocessor.process_llm_response(llm_result)

# Проверка результата
for org in processed["organizations"]:
    print(f"Org: {org['name']}, GID: {org['gid']}")

for contact in processed["contacts"]:
    print(f"Contact: {contact['name']}, GID: {contact['gid']}")

# Метаданные
gid_meta = processed["postprocessing_metadata"]["gid"]
print(f"Assigned: {len(gid_meta['assigned'])} entities")
print(f"Conflicts: {len(gid_meta['conflicts'])} conflicts")
```

## ⚙️ Конфигурация

### Overrides (ручные переопределения)

Создайте файл `src/registry/overrides.yml`:

```yaml
org_overrides:
  - key: ["ORG", "NAME_CITY", "агрохим", "казань"]
    gid: "25eab71a-64f5-5bdb-a3e6-0f9667ab4b3d"
    comment: "Разделение с Агрохим Москва"

contact_overrides:
  - key: ["CONTACT", "EMAIL", "58a49494-...", "test@example.com"]
    gid: "custom-gid-12345"
```

### Phone Overrides (расширение для PLAN-004)
Для фиксации принадлежности телефонов организациям (против LLM-ошибок дублирования HQ-номеров).

**Файл:** `src/registry/phone_overrides.yml`

**Формат:**
```yaml
phone_overrides:
  - number: "+73833802104"  # Нормализованный E.164
    owner_gid: "org_med_congress"  # GID организации-владельца
    comment: "Телефон МЕД КОНГРЕСС, не дублировать в ДНК-Технология"
  - number: "+74951234567"
    owner_gid: "org_dnk_tech"
    comment: "HQ ДНК-Технология"
```

**Применение:** Автоматически в PostProcessor._resolve_phone_conflicts. Приоритет выше эвристик. Конфликты логируются в metadata.phone_conflicts с reason="override".

**Мониторинг:** `python scripts/check_registry_health.py` — проверяет дубли номеров, валидность GID.

При конфликте между override и существующим `gid`:
- Приоритет у override
- Конфликт фиксируется в `postprocessing_metadata.gid.conflicts`

### Переменные окружения

```bash
# Путь к реестру (по умолчанию: src/registry/)
REGISTRY_DIR=/path/to/registry

# Путь к overrides (по умолчанию: src/registry/overrides.yml)
OVERRIDES_PATH=/path/to/overrides.yml
```

## 📊 Метаданные в результате

Структура `postprocessing_metadata.gid`:

```json
{
  "gid": {
    "assigned": [
      {
        "entity": "organization",
        "local_id": 1,
        "gid": "58a49494-b44e-5b2f-9263-0ce9005f10e3",
        "match_rule": "DOMAIN",
        "key_tuple": ["ORG", "DOMAIN", "dna-technology.ru"],
        "alias_added": true,
        "source": "registry"
      },
      {
        "entity": "contact",
        "local_id": 101,
        "organization_id": 1,
        "organization_gid": "58a49494-...",
        "gid": "a3ac53de-6e12-5e5e-8cbc-2a8a1714c631",
        "match_rule": "EMAIL",
        "key_tuple": ["CONTACT", "EMAIL", "58a49494-...", "m.gogoleva@dna-technology.ru"],
        "alias_added": false,
        "source": "new"
      }
    ],
    "conflicts": []
  }
}
```

## 🔧 Нормализация данных

### Правила нормализации

| Поле | Правила |
|------|---------|
| ИНН | Только цифры, длина 10/12 |
| Домены | e2LD, lowercase, punycode |
| Названия орг | Без юр.форм, lowercase, один пробел |
| Города | Справочник синонимов, lowercase |
| Email | Lowercase, trim |
| Телефоны | E.164 формат (+7...) |
| Имена/должности | Lowercase, trim, без точек |

### Примеры нормализации

```python
# ИНН
"7723 537 840" → "7723537840"

# Домен
"https://corp.dna-technology.ru/products" → "dna-technology.ru"

# Название
"ООО \"ДНК-Технология\"" → "днк-технология"

# Телефон
"8 (495) 640-17-71" → "+74956401771"
```

## 🚀 Миграция в MySQL

### Схема таблиц

```sql
CREATE TABLE organizations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    gid CHAR(36) UNIQUE NOT NULL,
    inn VARCHAR(12) UNIQUE NULL,
    website_domain VARCHAR(255) UNIQUE NULL,
    name_norm VARCHAR(500),
    city_norm VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_inn (inn),
    INDEX idx_domain (website_domain),
    INDEX idx_name_city (name_norm, city_norm)
);

CREATE TABLE contacts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    gid CHAR(36) UNIQUE NOT NULL,
    org_id BIGINT NOT NULL,
    email_lower VARCHAR(255),
    phone_e164 VARCHAR(20),
    name_norm VARCHAR(500),
    position_norm VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (org_id) REFERENCES organizations(id),
    UNIQUE KEY unique_org_email (org_id, email_lower),
    UNIQUE KEY unique_org_phone (org_id, phone_e164),
    INDEX idx_email (email_lower),
    INDEX idx_phone (phone_e164)
);

CREATE TABLE org_aliases (
    org_id BIGINT NOT NULL,
    key_tuple JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (org_id) REFERENCES organizations(id),
    INDEX idx_org (org_id)
);

CREATE TABLE contact_aliases (
    contact_id BIGINT NOT NULL,
    key_tuple JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    INDEX idx_contact (contact_id)
);
```

### Процедура миграции

```python
# 1. Загрузка данных из JSONL
registry = GlobalIDRegistry()

# 2. Upsert в MySQL по gid
for gid, record in registry.gid_index.items():
    # INSERT ... ON DUPLICATE KEY UPDATE по gid
    pass

# 3. После миграции: публичный gid, внутренний id (NID)
```

## 📈 Мониторинг

### Метрики для отслеживания

- Размер `organizations.jsonl` / `contacts.jsonl`
- Количество записей в реестре
- Частота конфликтов в `gid_conflicts`
- Наличие lock-файлов (могут остаться при крэше)

### Скрипт проверки

```bash
python scripts/check_registry_health.py
```

## 🔄 Бэкапы

### Автоматический бэкап

```bash
# Ежедневный бэкап (добавить в cron)
0 2 * * * /usr/bin/python /path/to/scripts/backup_registry.py
```

### Ручной бэкап

```bash
cp src/registry/organizations.jsonl src/registry/organizations.jsonl.backup
cp src/registry/contacts.jsonl src/registry/contacts.jsonl.backup
```

## ❓ FAQ

**Q: Что делать, если gid изменился после повторного прогона?**
A: Это баг. Проверьте, что:
1. Нормализация данных идентична
2. Порядок признаков организации не изменился
3. Реестр не был пересоздан

**Q: Как объединить два разных gid в один?**
A: Используйте `overrides.yml` — укажите один gid для обоих ключей.

**Q: Можно ли удалить запись из реестра?**
A: Нет, реестр append-only. Для "удаления" используйте поле `deleted: true` (не реализовано в текущей версии).

**Q: Как проверить, какие ключи привязаны к gid?**
A: `registry.get_all_keys_for_gid(gid)` или просмотрите JSONL файл.

## 📚 Дополнительно

- Спецификация: `.kiro/specs/global-ID-registry/PLAN-003_Global_ID_Registry.md`
- Тесты: `tests/test_global_id_registry.py`, `tests/integration/test_global_id_integration.py`
- Пример overrides: `src/registry/overrides.yml.example`

---

**Версия:** 1.0.0  
**Дата:** 2025-10-02  
**Автор:** Mini-CRM Team