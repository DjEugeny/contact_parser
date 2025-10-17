 # 🧪 ПЛАН ТЕСТИРОВАНИЯ GID ДЛЯ КОНТАКТОВ БЕЗ ОРГАНИЗАЦИИ

## 📋 Список писем для проверки

### 📅 Дата: 2025-08-28 (2 письма)

#### 1. **email_001** — Кузнецова Ирина Андреевна
- **Файл**: `email_001_20250828_20250828_yandex_ru_6caea8a0.json`
- **Контакты без организации**: 1
  - Кузнецова Ирина Андреевна
  - Email: `anda4@yandex.ru` ✅
  - Телефон: `+79134820532` ✅
- **Текущий статус**: ❌ НЕТ `gid`
- **Ожидаемый ключ**: `["CONTACT", "EMAIL", "PERSONAL", "anda4@yandex.ru"]`

#### 2. **email_009** — Кондратюк Екатерина + Светлана Сергеевна
- **Файл**: `email_009_20250828_20250828_cnmt_ru_84c2a1ae.json`
- **Контакты без организации**: 2
  - Кондратюк Екатерина
    - Email: `kondratyuk_eyu@cnmt.ru` ✅
  - Светлана Сергеевна
    - Email: `s.voronova@dna-technology.ru` ✅
- **Текущий статус**: ❌ НЕТ `gid`
- **Ожидаемые ключи**:
  - `["CONTACT", "EMAIL", "PERSONAL", "kondratyuk_eyu@cnmt.ru"]`
  - `["CONTACT", "EMAIL", "PERSONAL", "s.voronova@dna-technology.ru"]`

---

### 📅 Дата: 2025-08-27 (8 писем)

#### 3. **email_003** — Свалов Андрей Владимирович
- **Файл**: `email_003_20250827_20250827_helicon_ru_146cade6.json`
- **Контакты без организации**: 1
  - Свалов Андрей Владимирович
  - Email: ❌ НЕТ
  - Телефон: Нужно проверить
- **Текущий статус**: ❌ НЕТ `gid`
- **Ожидаемый ключ**: `["CONTACT", "NAME_POSITION", "PERSONAL", "свалов андрей владимирович", "..."]`

#### 4. **email_009** — Кондратюк Екатерина
- **Файл**: `email_009_20250827_20250827_dna-technology_ru_e224d0e4.json`
- **Контакты без организации**: 1
  - Кондратюк Екатерина
  - Email: ❌ НЕТ
- **Текущий статус**: ❌ НЕТ `gid`

#### 5-11. **email_014, 016, 017, 018, 019, 021** — Свалов + другие
- **Файлы**: `email_014/016/017/018/019/021_20250827_...`
- **Контакты без организации**: 1-3 в каждом письме
  - Свалов Андрей Владимирович (повторяется в 7 письмах)
  - Лунева Ирина Владимировна (email_021)
  - Релина Светлана Геннадьевна (email_021)
- **Текущий статус**: ❌ НЕТ `gid`

---

## 🎯 Приоритетные письма для тестирования

### Высокий приоритет (ОБЯЗАТЕЛЬНО проверить):

1. **email_001 (2025-08-28)** — простой случай, 1 контакт с email
2. **email_009 (2025-08-28)** — 2 контакта без организации в одном письме
3. **email_003 (2025-08-27)** — контакт БЕЗ email (только имя)

### Средний приоритет (рекомендуется):

4. **email_021 (2025-08-27)** — 3 контакта без организации
5. **email_014 (2025-08-27)** — проверка дедупликации (Свалов повторяется)

### Низкий приоритет (опционально):

6-10. Остальные письма с Сваловым (для проверки дедупликации)

---

## 📝 Инструкция по тестированию

### Шаг 1: Запустить обработку приоритетных писем

```bash
cd /Users/evgenyzach/contact_parser
python -m src.api_pipeline_validator

# В меню выбрать:
# 1. Дата: 2025-08-28
# 2. Выбор конкретного письма(писем)
# 3. Ввести: email_001.json email_009.json
```

### Шаг 2: Проверить наличие GID

```bash
# Найти последний обработанный файл
ls -lt data/llm_results/2025-08-28/old/email_001_*_processed.json | head -1

# Проверить GID у контакта без организации
jq '.processed_result.contacts[] | select(.organization_id == null) | {
  name, 
  organization_id, 
  email, 
  gid
}' data/llm_results/2025-08-28/old/email_001_*_processed.json | tail -20
```

**Ожидаемый вывод**:
```json
{
  "name": "Кузнецова Ирина Андреевна",
  "organization_id": null,
  "email": "anda4@yandex.ru",
  "gid": "a1b2c3d4-5678-90ab-cdef-1234567890ab"  // ✅ Должен быть
}
```

### Шаг 3: Проверить metadata

```bash
jq '.processed_result.postprocessing_metadata.gid.assigned[] | select(.entity == "contact")' \
  data/llm_results/2025-08-28/old/email_001_*_processed.json
```

**Ожидаемый вывод**:
```json
{
  "entity": "contact",
  "local_id": 2,
  "gid": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "match_rule": "EMAIL",
  "key_tuple": [
    "CONTACT",
    "EMAIL",
    "PERSONAL",
    "anda4@yandex.ru"
  ],
  "alias_added": false,
  "source": "new"
}
```

**Важно**: НЕ должно быть полей `organization_id` и `organization_gid` в metadata!

### Шаг 4: Проверить реестр

```bash
# Проверить последние записи с маркером PERSONAL
grep '"PERSONAL"' registry/contacts.jsonl | tail -5
```

**Ожидаемый вывод**:
```json
{
  "event": "create",
  "gid": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "key": ["CONTACT", "EMAIL", "PERSONAL", "anda4@yandex.ru"],
  "aliases": [],
  "created_at": "2025-10-16T15:48:00Z"
}
```

### Шаг 5: Проверить дедупликацию (email_009)

```bash
# Проверить, что оба контакта получили разные GID
jq '.processed_result.contacts[] | select(.organization_id == null) | {name, gid}' \
  data/llm_results/2025-08-28/old/email_009_*_processed.json
```

**Ожидается**:
```json
{
  "name": "Кондратюк Екатерина",
  "gid": "gid-1"  // ✅ Уникальный
}
{
  "name": "Светлана Сергеевна",
  "gid": "gid-2"  // ✅ Другой GID
}
```

### Шаг 6: Проверить контакт БЕЗ email (email_003)

```bash
python -m src.api_pipeline_validator
# Дата: 2025-08-27
# Письмо: email_003.json

# Проверить GID
jq '.processed_result.contacts[] | select(.organization_id == null) | {
  name, 
  email, 
  phones,
  gid,
  key_tuple: .postprocessing_metadata.gid.assigned[0].key_tuple
}' data/llm_results/2025-08-27/old/email_003_*_processed.json
```

**Ожидается**:
- Если есть телефон: ключ `["CONTACT", "PHONE", "PERSONAL", "+7..."]`
- Если нет телефона: ключ `["CONTACT", "NAME_POSITION", "PERSONAL", "свалов андрей владимирович", "..."]`

---

## ✅ Критерии успеха

### Обязательные требования:

1. ✅ **Все контакты без организации имеют `gid`**
   - В поле `contacts[].gid` присутствует UUID

2. ✅ **Metadata содержит запись о назначении GID**
   - `postprocessing_metadata.gid.assigned[]` содержит запись с `entity: "contact"`

3. ✅ **Ключ содержит маркер "PERSONAL"**
   - `key_tuple[2] == "PERSONAL"`

4. ✅ **Нет полей организации в metadata для контактов без организации**
   - В `gid.assigned[]` НЕТ полей `organization_id` и `organization_gid`

5. ✅ **Реестр содержит записи с "PERSONAL"**
   - `registry/contacts.jsonl` содержит записи с ключами `["CONTACT", ..., "PERSONAL", ...]`

### Дополнительные проверки:

6. ✅ **Дедупликация работает**
   - Повторная обработка того же письма не создаёт новый GID
   - Свалов Андрей Владимирович имеет одинаковый GID в разных письмах

7. ✅ **Контакты с организацией не затронуты**
   - Контакты с `organization_id != null` работают как раньше
   - В их metadata есть `organization_id` и `organization_gid`

---

## 📊 Ожидаемая статистика

### До исправления:
- Контактов без организации: **13**
- Контактов с `gid`: **0** (0%)

### После исправления:
- Контактов без организации: **13**
- Контактов с `gid`: **13** (100%)

### Записи в реестре:
- Новых записей с "PERSONAL": **~8-10** (с учётом дедупликации Свалова)

---

## 🚨 Возможные проблемы

### 1. ValueError: Contact object does not contain identification data
**Причина**: Контакт не имеет ни email, ни телефона, ни имени  
**Решение**: Проверить логику `iter_contact_keys()` в `global_registry.py`

### 2. GID не появляется в metadata
**Причина**: Исключение в блоке `try-except`  
**Решение**: Проверить логи на наличие ошибок

### 3. Дублирование GID при повторной обработке
**Причина**: Реестр не сохраняется между запусками  
**Решение**: Проверить, что `registry/contacts.jsonl` обновляется

---

**Дата создания**: 2025-10-16 22:48  
**Автор**: Cascade AI  
**Статус**: Готов к тестированию
