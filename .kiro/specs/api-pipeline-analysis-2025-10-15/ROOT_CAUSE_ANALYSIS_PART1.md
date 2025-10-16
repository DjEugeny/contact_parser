# 🔬 ROOT CAUSE ANALYSIS — API Pipeline Validator (Часть 1/2)
## Дата: 2025-10-16

---

## 📋 Исполнительное резюме

Выявлены **4 критические системные проблемы** с чёткими root causes:

1. ✅ **organization_id=1**: Автокоррекция подставляет несуществующий ID
2. ✅ **OCR кеш**: Несовпадение хешей блокирует готовые результаты
3. ✅ **GID assignment**: Контакты остаются без глобальных ID
4. ✅ **Фильтрация вложений**: Pipeline обрабатывает excluded файлы

---

## 🔴 ПРОБЛЕМА 1: organization_id=1 для несуществующих организаций

### Симптомы
```
❌ JSON Schema валидация не прошла: None is not of type 'integer'
🔧 Установлено значение по умолчанию для contact 0 organization_id: 1
⚠️ Контакт unknown (Кузнецова Ирина Андреевна): организация 1 не найдена
```

### Root Cause Chain

**1. Исходное письмо** (email_001_20250828):
```json
{
  "from": "anda4@yandex.ru",
  "subject": "Билеты", 
  "body": "Светлана Сергеевна, нашла удобные рейсы...",
  "attachments": []
}
```
→ **Нет организаций** (личное письмо о билетах)

**2. LLM ответ** (✅ корректный):
```json
{
  "organizations": [],
  "contacts": [
    {
      "contact_id": 1,
      "organization_id": null,  // ✅ LLM правильно вернул null
      "name": "Кузнецова Ирина Андреевна"
    }
  ]
}
```

**3. Автокоррекция** (src/core/safe_math_utils.py:171):
```python
elif key in integer_fields and value is None:
    data[key] = 1  # ❌ ХАРДКОД: всегда 1
```
→ **Заменяет null → 1 без проверки существования**

**4. Результат** (organizations отсутствуют):
```json
{
  "organizations": [],  // ❌ ПУСТО
  "contacts": [
    {"organization_id": 1}  // ❌ Ссылка на несуществующую
  ],
  "gid": {"assigned": []}  // ❌ GID не назначены
}
```

### Почему промпт v1.1 НЕ решает проблему

**Промпт v1.1** требует:
```
❌ НИКОГДА не используй null для обязательных ID полей:
  - organization_id - ВСЕГДА число (1, 2, 3...)
```

**Проблема**: Невыполнимое требование для писем БЕЗ организаций!
- Вернуть null → нарушение правила
- Вернуть 1 → фиктивная организация

### РЕШЕНИЕ

**A. Разрешить null для писем без организаций** (РЕКОМЕНДУЕТСЯ)

1. **Изменить JSON Schema**:
```json
{
  "organization_id": {
    "anyOf": [
      {"type": "integer", "minimum": 1},
      {"type": "null"}
    ]
  }
}
```

2. **Изменить промпт v1.1**:
```diff
- organization_id - ВСЕГДА число
+ organization_id:
+   - Если контакт из organizations[] → укажи ID
+   - Если организации НЕТ → используй null
+   - НИКОГДА не придумывай несуществующие!
```

3. **Убрать автокоррекцию** (safe_math_utils.py):
```python
# УДАЛИТЬ:
# data[key] = 1  # ❌ ХАРДКОД
```

4. **Обработать null в постобработке**:
```python
if contact.get('organization_id') is None:
    logger.info(f"Контакт {name} без организации")
    continue  # Пропускаем org-based enrichment
```

---

## 🔴 ПРОБЛЕМА 2: OCR кеш не работает из-за хешей

### Симптомы
```
📎 OCR кеш промах для 20250827_20081ed0_...attach_Ком.пред.27.08.2025.pdf
   Файл существует: True
```

### Root Cause

**Формат имени вложения**:
```
{date}_{hash}_{time}_{id}_attach_{original_name}
20250827_20081ed0_005329_963544_attach_Ком.пред.27.08.2025.pdf
         ^^^^^^^^
         Хеш зависит от времени сохранения!
```

**Существующие OCR результаты**:
```bash
data/ocr/texts/2025-08-27/
  20250827_38ae8d4c_...attach_Ком.пред.27.08.2025.txt  ✅ Есть
  20250827_9aa1233a_...attach_Ком.пред.27.08.2025.txt  ✅ Есть
```

**Хеш 20081ed0 ≠ 38ae8d4c/9aa1233a** → кеш промах!

**Причина несовпадения**:
1. День 1: Fetcher сохранил файл с хешем 38ae8d4c
2. День 1: OCR обработал → сохранил как 38ae8d4c_...txt
3. День 2: Fetcher переобнаружил вложение
4. День 2: Создал новую запись с хешем 20081ed0 (новый timestamp!)
5. Pipeline ищет 20081ed0_...txt → не находит

**Код проблемы** (ocr_cache_manager.py:111):
```python
if txt_name.endswith(filename_without_ext):  # ❌ Полное совпадение с хешем
    return text
```

### РЕШЕНИЕ

**Поиск по оригинальному имени** (без хеша):

```python
def get_cached_result(self, filename: str, date: str) -> Optional[str]:
    # Извлекаем оригинальное имя (после 'attach_')
    if '_attach_' in filename:
        original_name = filename.split('_attach_', 1)[1]
        original_name = original_name.rsplit('.', 1)[0]  # Без ext
    else:
        original_name = filename.rsplit('.', 1)[0]
    
    # Ищем паттерном: *_attach_{original_name}.txt
    pattern = f"*_attach_{original_name}.txt"
    
    for txt_file in (self.results_dir / date).glob(pattern):
        text = self._read_text_file(txt_file)
        if text:
            self.logger.info(f"✅ Кеш найден: {txt_file.name}")
            return text
    
    return None
```

**Преимущества**:
- Находит OCR независимо от хеша/timestamp
- Не требует изменений в других модулях
- Работает с существующими результатами

---

## 🟡 ПРОБЛЕМА 3: GID не назначается контактам

### Симптомы
```json
{
  "gid": {"assigned": []},
  "contacts": [
    {"contact_gid": "unknown"}  // ❌ Не назначен
  ]
}
```

### Root Cause

**GlobalRegistry требует org_gid** (global_registry.py:430):
```python
def resolve_contact(self, contact: Dict, org_gid: str) -> ResolutionResult:
    keys = list(iter_contact_keys(contact, org_gid))  # ❌ org_gid обязателен

def iter_contact_keys(contact: Dict, org_gid: str):
    key = ("CONTACT", "EMAIL", org_gid, email)  # ❌ org_gid в ключе
```

**Цепочка**:
1. organization_id=1, но organizations=[]
2. Нет org_gid для организации 1
3. GlobalRegistry не может создать ключи
4. GID не назначается

### РЕШЕНИЕ

**Независимые GID для контактов без организаций**:

```python
def resolve_contact(self, contact: Dict, org_gid: str = None):
    if org_gid is None:
        # Независимый контакт
        keys = self._generate_independent_keys(contact)
        namespace = INDEPENDENT_CONTACT_NS
    else:
        # С организацией
        keys = list(iter_contact_keys(contact, org_gid))
        namespace = CONTACT_NS
    # ...

def _generate_independent_keys(self, contact: Dict):
    keys = []
    if email := norm_email(contact.get("email")):
        keys.append(("CONTACT", "EMAIL_IND", email))
    if phone := norm_e164(contact.get("phones", [{}])[0].get("number")):
        keys.append(("CONTACT", "PHONE_IND", phone))
    return keys
```

---

## 🟡 ПРОБЛЕМА 4: Pipeline обрабатывает excluded вложения

### Симптомы
```
⚠️ У вложения 'unknown' отсутствует путь к файлу (×80)
```

### Root Cause

**Письмо**:
```json
{
  "attachments": [
    {"status": "excluded", "original_filename": "image001.png"},  // ❌
    {"status": "excluded", "original_filename": "image002.png"},  // ❌
    {"status": "saved", "file_path": "/path/to/doc.pdf"}  // ✅
  ]
}
```

**Код** (_compose_combined_text, строка 691):
```python
for attachment in attachments:  # ❌ ВСЕ, включая excluded
    status = attachment.get("status")
    if status in {"excluded_by_filter", "excluded_by_size"}:  # ❌ Неполный список
        continue
```

**Проблема**: Проверка не включает просто `"excluded"`

### РЕШЕНИЕ

**Фильтровать только saved**:

```python
def _compose_combined_text(self, email_data, date):
    # ...
    
    # ✅ Только сохранённые вложения
    saved_attachments = [
        att for att in attachments
        if att.get("status") == "saved" and att.get("file_path")
    ]
    
    for index, attachment in enumerate(saved_attachments, start=1):
        text = self._get_attachment_text(email_data, attachment, date)
        # ...
```

---

## 📊 ПРИОРИТИЗАЦИЯ

| Проблема | Приоритет | Сложность | Время | Риск |
|----------|-----------|-----------|-------|------|
| 2. OCR кеш | **P0** | Низкая | 1 ч | Низкий |
| 4. Excluded вложения | **P0** | Низкая | 30 мин | Низкий |
| 1. organization_id | **P0** | Средняя | 2-3 ч | Средний |
| 3. GID assignment | **P1** | Средняя | 2-3 ч | Средний |

**ИТОГО P0**: ~4 часа работы

---

**Продолжение**: ROOT_CAUSE_ANALYSIS_PART2.md (План имплементации)
