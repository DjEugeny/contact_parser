# Google Contacts Enrichment

Модули для обогащения Google Contacts данными из Mini-CRM (IMAP-отправители + реестр контактов).

## Обзор

Конвейер берёт email/FИО из `data/senders_cache.json` (результат IMAP-сканирования + реестр), сопоставляет их с существующими Google Contacts через People API, добавляет недостающие email и создаёт новые контакты.

## Архитектура

```
senders_cache.json (IMAP + реестр)
          │
          ▼
  ┌─────────────────┐
  │ google_contacts │  ── OAuth → Google People API
  │   _enrich.py    │  ── dry-run / --enrich
  └─────────────────┘
          │
          ├── matched → updateContact (добавить email)
          │
          └── unmatched ──→ new_contacts.json
                              │
                              ▼
                    create_missing_contacts.py --create
                              │
                              ▼
                         Google Contacts (новые)
```

## Основные модули

### 1. `scripts/google_contacts_enrich.py` — мэтчинг и обогащение

**Назначение**: Сопоставляет IMAP-отправителей с Google Contacts и добавляет недостающие email.

**Ключевые функции**:
- `extract_google_contact_info()` — парсит Google-контакт (familyName/givenName + `displayName`-fallback)
- `match_senders_to_google()` — многоуровневый мэтчинг: exact_fio → translit → last_first_only → last_name_only
- `enrich_google_contacts()` — dry-run или реальное обновление через `updateContact`

**Уровни мэтчинга**:
| Уровень | Описание | Безопасность |
|---------|----------|--------------|
| `exact_fio` | Полное совпадение Ф+И+О | 🟢 Высокая |
| `translit_fio` | Транслит (Ivanov ↔ Иванов) | 🟢 Высокая |
| `last_first_only` | Фамилия + имя (без отчества) | 🟡 Средняя |
| `last_name_only` | Только фамилия | 🔴 Низкая — требует ручной проверки |

**CLI**:
```bash
# Сухой прогон
python scripts/google_contacts_enrich.py --dry-run

# Точечный enrich (5 контактов, только точные ФИО)
python scripts/google_contacts_enrich.py --enrich --limit=5 --match-types=exact_fio

# Полный enrich (уровни 1-3)
python scripts/google_contacts_enrich.py --enrich --match-types=exact_fio,translit_fio,last_first_only

# Все уровни включая last_name_only — только после ручной проверки
python scripts/google_contacts_enrich.py --enrich --match-types=exact_fio,translit_fio,last_first_only,last_name_only
```

**Выходные данные**:
- `data/match_results.json` — результаты мэтчинга (matched, unmatched_senders, unmatched_google)

---

### 2. `scripts/match_report.py` — генерация отчёта

**Назначение**: Создаёт Markdown-отчёт из `match_results.json` для ручной проверки.

**Формат**: Таблицы с сортировкой:
1. Приоритетные контакты `dna-technology.ru`
2. Остальные `dna-technology.ru`
3. Все остальные (HTML-таблица для надёжности рендеринга)

**CLI**:
```bash
python scripts/match_report.py
```

**Выходные данные**:
- `data/match_report.md`

---

### 3. `scripts/normalize_google_names.py` — нормализация ФИО

**Назначение**: Приводит `familyName/givenName/middleName` в Google Contacts к единому формату `Фамилия Имя Отчество` на основе данных из `senders_cache.json`.

**Логика**: Обновляет только при явно перепутанных полях или пустых фамилиях/именах. Организации пропускаются.

**CLI**:
```bash
# Просмотр
python scripts/normalize_google_names.py --dry-run

# Обновление
python scripts/normalize_google_names.py --update
```

---

### 4. `scripts/create_missing_contacts.py` — создание новых контактов

**Назначение**: Генерирует JSON-шаблон из unmatched-отправителей и создаёт новые контакты в Google.

**CLI**:
```bash
# Генерация шаблона (с фильтрацией дублей по Google API)
python scripts/create_missing_contacts.py --template

# Создание контактов из new_contacts.json
python scripts/create_missing_contacts.py --create
```

**Файлы данных**:
- `data/new_contacts.template.json` — сырой шаблон
- `data/new_contacts.json` — отредактированный шаблон (пользователь правит руками)
- `data/new_contacts_report.json` — отчёт после создания

---

### 5. `scripts/enrich_and_normalize.py` — **основной скрипт** обогащения + нормализации

**Назначение**: Объединяет обогащение email и нормализацию ФИО в один проход. Это основной скрипт для работы с Google Contacts.

**Логика**: Для каждого Google Contact, найденного по email в `senders_cache.json`:
- Добавляет недостающий email
- Исправляет familyName/givenName (при перепутанных или пустых полях)
- Добавляет middleName (отчество) при пустом поле или только капитализации
- Пропускает организации

**CLI**:
```bash
python scripts/enrich_and_normalize.py --dry-run
python scripts/enrich_and_normalize.py --update
```

### 6. `scripts/google_auth_setup.py` — OAuth-авторизация

**Назначение**: Первая настройка OAuth 2.0 для Google People API.

**CLI**:
```bash
python scripts/google_auth_setup.py
```

**Требует**:
- `config/google_credentials.json` — OAuth Client ID из Google Cloud Console
- Создаёт `config/google_token.json` — токен доступа

---

## Файлы данных

| Файл | Назначение |
|------|-----------|
| `data/senders_cache.json` | Источник: email + name_parts (last, first, middle) |
| `data/match_results.json` | Результат мэтчинга (matched / unmatched) |
| `data/match_report.md` | Markdown-отчёт для ручной проверки |
| `data/new_contacts.template.json` | Автогенерируемый шаблон |
| `data/new_contacts.json` | Отредактированный шаблон для создания |
| `data/new_contacts_report.json` | Отчёт об успешности создания |
| `config/google_credentials.json` | OAuth Client ID (не коммитить!) |
| `config/google_token.json` | OAuth токен (не коммитить!) |

## Зависимости

```
google-auth-oauthlib
google-auth
google-api-python-client
```

Добавлены в `requirements.txt`.

## Типичный рабочий процесс

```bash
# 1. Авторизация (один раз)
python scripts/google_auth_setup.py

# 2. Сухой прогон
python scripts/google_contacts_enrich.py --dry-run

# 3. Отчёт для сверки
python scripts/match_report.py
# → открыть data/match_report.md, проверить 🔴 last_name_only

# 4. Нормализация имён в Google (опционально)
python scripts/normalize_google_names.py --update

# 5. Точечный enrich
python scripts/google_contacts_enrich.py --enrich --limit=5 --match-types=exact_fio

# 6. Проверка на телефоне (Aquamail / Google Contacts)

# 7. Полный enrich (без last_name_only)
python scripts/google_contacts_enrich.py --enrich --match-types=exact_fio,translit_fio,last_first_only

# 7а. Альтернатива: обогащение + нормализация ФИО в одном скрипте
python scripts/enrich_and_normalize.py --update

# 8. Создание недостающих контактов
python scripts/create_missing_contacts.py --template
# → правим data/new_contacts.json
python scripts/create_missing_contacts.py --create
```

## Интеграция в основной проект

Для встраивания в пайплайн Mini-CRM:

1. **Импортировать** `google_contacts_enrich.py` как модуль:
   ```python
   from scripts.google_contacts_enrich import match_senders_to_google, enrich_google_contacts
   ```

2. **Вызывать** после извлечения senders:
   ```python
   senders = load_senders()  # из senders_cache.json
   google = load_google_contacts(service)
   matched, unmatched = match_senders_to_google(senders, google)
   ```

3. **Переиспользовать** `normalize_google_names.py` как отдельный шаг очистки.

4. **Переиспользовать** `create_missing_contacts.py` для массового создания.

### 7. `scripts/google_contacts_dedup.py` — дедупликация контактов

**Назначение**: Находит и объединяет дубликаты Google Contacts (одинаковые Фамилия+Имя).

**Логика**: Группирует по familyName+givenName, фильтрует реальные дубли (общий email/телефон или пустой дубль), мастер-контакт = с наибольшим числом данных.

**CLI**:
```bash
# Отчёт о дублях (dry-run)
python scripts/google_contacts_dedup.py

# Объединить все дубли
python scripts/google_contacts_dedup.py --merge --all

# Resume после краша
python scripts/google_contacts_dedup.py --merge --all --skip=50
```

**Результат**: 304 группы объединены, 0 ошибок.

---

### 8. `scripts/google_contacts_phone_normalize.py` — нормализация телефонов

**Назначение**: Приводит все телефоны к формату `+7 (XXX) XXX-XX-XX` + тип (мобильный/городской).

**Переиспользует**: `src/postprocessing/phone_normalizer.py` (PhoneNormalizer).

**CLI**:
```bash
# Отчёт
python scripts/google_contacts_phone_normalize.py --report

# Обновить все телефоны
python scripts/google_contacts_phone_normalize.py --update

# Дедупликация телефонов внутри контактов
python scripts/google_contacts_phone_normalize.py --dedup-phones
```

**Результат**: 3087 обновлено, 10 ошибок, 482 без изменений.

---

### 9. `scripts/google_contacts_export.py` — экспорт и анализ ФИО

**Назначение**: Экспортирует контакты в Markdown/CSV с анализом проблем ФИО.

**Детекция**: перепутаны Фамилия/Имя (по словарю имён), отчество в неправильном поле, КАПС, пустое имя, имя в отчестве, displayName ≠ ФИО.

**CLI**:
```bash
# Полный отчёт (только проблемы)
python scripts/google_contacts_export.py --only-problems

# CSV всех контактов
python scripts/google_contacts_export.py --csv
```

**Выходные данные**:
- `data/contacts_export_problems.md` — Markdown с проблемами и решениями
- `data/contacts_export.csv` — CSV для Excel
- `data/contacts_info.json` — полные данные

---

### 10. `scripts/google_contacts_fix_names.py` — автофикс ФИО

**Назначение**: Автоматически исправляет проблемы ФИО в Google Contacts.

**Исправляет**: перепутаны Ф/И (по словарю имён + displayName), КАПС, отчество в fn/gn, пустое имя (fn=Имя+Фамилия), имя в mn.

**НЕ трогает**: пустая фамилия (нет данных), displayName ≠ ФИО (не критично).

**CLI**:
```bash
# Отчёт что будет исправлено
python scripts/google_contacts_fix_names.py --report

# Применить исправления
python scripts/google_contacts_fix_names.py --update

# Resume
python scripts/google_contacts_fix_names.py --update --skip=100
```

**Результат**: ~2514 контактов исправлено за 2 прогона (6 ошибок из 2517).

---

## Вспомогательные скрипты (одноразовые / отладка)

- `_debug_google_names.py` — отладка парсинга имён в Google
- `_debug_google_names2.py` — поиск по фамилии в Google
- `_debug_missing.py` — проверка приоритетных контактов
- `_check_priority.py` — сверка списка приоритетных
- `_add_phones.py` — добавление телефонов в new_contacts.json
- `_filter_people.py` — фильтрация организаций из шаблона
- `_capitalize_names.py` — капитализация ФИО
- `_strict_fix_swaps.py` — исправление перепутанных familyName/givenName

---

## План работ (PLAN V2.md)

Подробный пошаговый план с результатами каждого этапа — см. `PLAN V2.md` в этой же папке.
