
# PLAN-001: Классификатор e-mail и очистка `organizations[].emails` от персональных адресов

**Цель:** в `organizations[].emails` хранить только общие/ролеовые/департаментные ящики; персональные адреса сотрудников (даже на корпоративном домене) должны оставаться на уровне `contacts[]` и не «липнуть» к организации.

---

## Контекст
В письмах встречаются адреса вида `s.voronova@dna-technology.ru`, `o.isaev@dna-technology.ru` и пр. Сейчас такие адреса попадают в `organizations[].emails`, что даёт шум и мешает поиску/аналитике.

---

## Область работ / файлы
- Новый модуль: `email_classifier.py` — классификация ящиков.
- Конфигурация: `org_profile.yml` — внутренние домены, известные префиксы общих/тех.ящиков, алиасы групп.
- `postprocessor.py` — вызов классификатора и фильтрация/демоут адресов на уровне организации, лог в метаданные.
- `organization_deduplicator.py` — при merge организаций **не возвращать** персональные адреса в `org.emails`.
- `diagnostic_enricher.py` — отчёт/метрики по типам ящиков.

---

## Технические требования

### 1) `email_classifier.py`
```python
from enum import Enum
import re

class MailboxType(str, Enum):
    PERSONAL_INTERNAL = "personal_internal"
    PERSONAL_EXTERNAL = "personal_external"
    SHARED_ORG       = "shared_org"
    DEPARTMENT       = "department"
    GROUP_ALIAS      = "group_alias"
    TECHNICAL        = "technical"
    UNKNOWN          = "unknown"

def classify_mailbox(address: str, display_name: str | None, corp_domains: set[str], cfg: dict) -> MailboxType:
    """
    address: 'local@domain'
    display_name: 'ФИО/название' (может быть None)
    corp_domains: {'dna-technology.ru', ...}
    cfg: конфиг с префиксами и суффиксами (см. org_profile.yml)
    """
    # 1) Разбор домена/локала
    # 2) Если домен корпоративный:
    #    - first.last / i.lastname / транслитерированное ФИО → PERSONAL_INTERNAL
    #    - локал в списке SHARED/DEPT → SHARED_ORG/DEPARTMENT
    #    - 'noreply', 'robot' → TECHNICAL
    #    - '-all', '.team' → GROUP_ALIAS
    # 3) Внешний домен: по display_name/паттернам → PERSONAL_EXTERNAL, иначе UNKNOWN
```
- Поддержать расширение правил через `org_profile.yml` без релиза кода.

### 2) Конфиг `org_profile.yml`
```yaml
internal_domains:
  - dna-technology.ru

shared_mailboxes_prefixes:
  - info
  - sales
  - support
  - service
  - office
  - pr
  - hr
  - it
  - help
  - warranty
  - billing
  - finance
  - accounting
  - buh
  - kadr
  - zakup
  - zakupki
  - tender
  - torgi
  - sklad
  - omts
  - marketing

technical_prefixes:
  - noreply
  - no-reply
  - robot
  - do-not-reply

group_alias_suffixes:
  - -all
  - .all
  - -team
  - .team
```

### 3) Интеграция в `postprocessor.py`
- Флаги:
  ```python
  self.keep_only_shared_org_emails = True
  self.demote_personal_org_emails_to_contacts = True
  self.classify_using_config_path = "org_profile.yml"
  ```
- Для каждого `organizations[].emails`:
  1) Классифицировать через `classify_mailbox(...)`.
  2) **Оставлять** только типы: `SHARED_ORG`, `DEPARTMENT`, `TECHNICAL`, `GROUP_ALIAS`.
  3) Персональные `PERSONAL_INTERNAL`/`PERSONAL_EXTERNAL` — **удалять** из `org.emails`.
  4) Если `demote_personal_org_emails_to_contacts=True` и в `contacts[]` уже есть запись с таким email и данным `organization_id` — ничего не делать; если нет — **не создавать** новый контакт автоматически (MVP), но логировать событие в карантин.

- Метаданные:
  ```json
  postprocessing_metadata.email_classification = {
    "org_id": {
      "kept": ["info@...", "torgi@..."],
      "removed": ["s.voronova@..."],
      "removed_types": {"s.voronova@...":"personal_internal"}
    }
  }
  ```

### 4) `organization_deduplicator.py`
- При объединении организаций игнорировать e‑mail’ы, классифицированные как персональные, чтобы они не возвращались в `org.emails` после merge.

### 5) Диагностика (`diagnostic_enricher.py`)
- Счётчики по типам: `count_by_mailbox_type` глобально и по организациям.
- `removed_from_org_emails` — список адресов, которые исключили, с типами.

---

## Тест‑план

### Юнит
- `info@dna-technology.ru` → `SHARED_ORG` (остаётся в org.emails).
- `torgi@dna-technology.ru` → `SHARED_ORG` (остаётся).
- `s.voronova@dna-technology.ru`, `o.isaev@dna-technology.ru` → `PERSONAL_INTERNAL` (удаляется из org.emails).
- `all@dna-technology.ru`/`sales-team@dna-technology.ru` → `GROUP_ALIAS`/`DEPARTMENT` (остаётся).
- Внешний личный `ivan.petrov@gmail.com` → `PERSONAL_EXTERNAL` (не должен попасть в org.emails).

### Интеграция
- После dedup организаций персональные адреса не возвращаются в `org.emails`.
- Метаданные `email_classification` заполнены.

---

## Definition of Done
- В итоговом JSON `organizations[].emails` не содержит персональных адресов сотрудников.
- Классификация управляется через конфиг без правки кода.
- Диагностика видит, сколько и какие адреса исключили.

---


