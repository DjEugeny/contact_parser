
# Design: Нормализация телефонов с добавочными номерами

## Архитектурный обзор

### Текущая схема обработки

```
LLM Response (phones как строки)
    ↓
Validator (ожидает строки, uniqueItems: true)
    ↓
PostProcessor
    ↓
PhoneNormalizer (добавляет extension обратно в number) ❌
    ↓
Final Result (дубликаты, ошибки валидации)
```

**Проблемы текущей схемы**:
1. **PhoneNormalizer** добавляет добавочный обратно в `formatted`/`number`
2. **Validator** проверяет уникальность по полному равенству строк
3. **LLM** может вернуть дубликаты типа `['+7 (495) 933 71 47 (48)', '+7 (495) 933 71 47 (48)']`
4. **JSON Schema** требует `uniqueItems: true` → валидация падает

### Целевая схема обработки

```
LLM Response (phones как строки или объекты)
    ↓
Sanitizer (конвертация строк → объекты если нужно)
    ↓
PhoneNormalizer (парсинг базового + extension)
    ├─ Извлечение extension
    ├─ Парсинг множественных номеров (48)
    └─ E.164 нормализация
    ↓
Validator (проверка объектов phones)
    ↓
PostProcessor (дедуп, GID assignment)
    ↓
Final Result (корректные данные)
```

---

## Компоненты решения

### 1. PhoneNormalizer (Core Logic)

**Файл**: `src/postprocessing/phone_normalizer.py`

**Ключевые методы**:

#### 1.1 `normalize_phone_to_object(phone_str: str) -> List[Dict]`
Главная функция нормализации. Возвращает список объектов (может быть несколько из одной строки).

```python
def normalize_phone_to_object(phone_str: str) -> List[Dict]:
    """
    📞 Нормализация телефонной строки в объекты
    
    Вход: "+7 (495) 933 71 47 (48), доб.171"
    
    Выход: [
        {
            "type": "office",
            "number": "+7 (495) 933-71-47",
            "normalized": "+74959337147",
            "original": "+7 (495) 933 71 47 (48), доб.171",
            "extension": "171"
        },
        {
            "type": "office",
            "number": "+7 (495) 933-71-48",
            "normalized": "+74959337148",
            "original": "+7 (495) 933 71 47 (48), доб.171",
            "extension": "171"
        }
    ]
    """
```

#### 1.2 `_extract_extension_new(phone: str) -> Tuple[str, Optional[str]]`
Улучшенное извлечение добавочного (замена текущего метода).

**Regex паттерн**:
```python
pattern = r'(?i)\s*[\(,]?\s*(?:доб\.?|доп\.?|extension|ext\.?|вн\.?|в\.?\s*н\.?|x)\s*[:\-]?\s*([0-9#*]{1,10})\s*\)?'
```

**Правила**:
- Поиск справа налево (берём последний match)
- Извлекаем только цифры из группы захвата
- Удаляем весь паттерн из базовой строки

#### 1.3 `_split_compound_phones(phone: str, extension: str) -> List[str]`
Новый метод для распознавания `(48)` как второго номера.

```python
def _split_compound_phones(phone_base: str, extension: str) -> List[str]:
    """
    Распознаёт паттерн: "+7 (495) 933 71 47 (48)"
    
    Алгоритм:
    1. Regex: r'(.*?)\\s*\\((\\d{2,})\\)\\s*$'
    2. Если match:
       - base_part = группа 1
       - suffix_digits = группа 2
       - base_digits = только цифры из base_part
       - Если len(base_digits) >= len(suffix_digits):
         * phone1 = base_part (без скобок)
         * phone2 = base_digits[:-len(suffix)] + suffix
    3. Возврат: [phone1, phone2]
    """
```

#### 1.4 `_normalize_to_e164(phone: str) -> Tuple[str, str, str]`
Нормализация в E.164 **без** добавочного.

**Библиотека**: `phonenumbers`
- `parse(phone, "RU")`
- `format_number(..., PhoneNumberFormat.E164)` → `normalized`
- Custom formatter → `number` (UI вид)

---

### 2. Validator Schema Update

**Файл**: `src/core/validator.py`

**Изменения**:

#### 2.1 Organization Schema (строки 620-686)

**Было**:
```python
"phones": {
    "type": "array",
    "items": {"type": "string"},
    "uniqueItems": True
}
```

**Станет**:
```python
"phones": {
    "type": "array",
    "items": {
        "oneOf": [
            {"type": "string"},  # Backward compatibility
            {"$ref": "#/definitions/phone_object"}
        ]
    },
    "description": "Массив телефонов (строки или объекты)"
}
```

#### 2.2 Contact Schema (строка 730)

Аналогичное изменение для `contacts[].phones`.

#### 2.3 Phone Object Definition

Добавить в схему:
```python
"definitions": {
    "phone_object": {
        "type": "object",
        "required": ["number"],
        "properties": {
            "type": {
                "type": ["string", "null"],
                "enum": ["main", "mobile", "office", "fax", "other", null]
            },
            "number": {"type": "string", "minLength": 1},
            "normalized": {"type": ["string", "null"]},
            "original": {"type": ["string", "null"]},
            "extension": {"type": ["string", "null"]},
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1}
        }
    }
}
```

#### 2.4 Uniqueness Check

**Проблема**: `uniqueItems: true` проверяет полное равенство, не подходит для объектов.

**Решение**: Убрать `uniqueItems`, дедупликацию делать в PostProcessor по ключу `(normalized, extension, type)`.

---

### 3. PostProcessor Integration

**Файл**: `src/postprocessing/postprocessor.py`

**Новый метод** (добавить после `_cleanup_organization_emails`):

```python
def _normalize_all_phones(
    self, 
    organizations: List[Dict], 
    contacts: List[Dict]
) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    📞 Нормализация всех телефонов через PhoneNormalizer
    
    Возвращает: (organizations, contacts, metadata)
    """
    normalizer = PhoneNormalizer()
    stats = {
        "org_phones_processed": 0,
        "contact_phones_processed": 0,
        "extensions_found": 0,
        "multiple_split": 0,
        "errors": []
    }
    
    # Нормализация организаций
    for org_idx, org in enumerate(organizations):
        phones_raw = org.get('phones', [])
        normalized_phones = []
        
        for phone_entry in phones_raw:
            if isinstance(phone_entry, str):
                # Строка → парсим в объекты
                try:
                    phone_objects = normalizer.normalize_phone_to_object(phone_entry)
                    normalized_phones.extend(phone_objects)
                    stats["org_phones_processed"] += len(phone_objects)
                    
                    if len(phone_objects) > 1:
                        stats["multiple_split"] += 1
                    
                    for obj in phone_objects:
                        if obj.get('extension'):
                            stats["extensions_found"] += 1
                except Exception as e:
                    stats["errors"].append({
                        "org_id": org.get('organization_id'),
                        "phone": phone_entry,
                        "error": str(e)
                    })
            
            elif isinstance(phone_entry, dict):
                # Уже объект — проверяем, нет ли extension в number
                if 'extension' in phone_entry.get('number', ''):
                    # Перепарсиваем
                    try:
                        phone_objects = normalizer.normalize_phone_to_object(
                            phone_entry.get('original') or phone_entry.get('number')
                        )
                        normalized_phones.extend(phone_objects)
                    except Exception as e:
                        normalized_phones.append(phone_entry)
                else:
                    normalized_phones.append(phone_entry)
        
        # Дедупликация по (normalized, extension, type)
        org['phones'] = self._deduplicate_phones(normalized_phones)
    
    # Аналогично для contacts
    for contact in contacts:
        phones_raw = contact.get('phones', [])
        # ... аналогичная логика ...
        contact['phones'] = self._deduplicate_phones(normalized_phones)
    
    return organizations, contacts, stats


def _deduplicate_phones(self, phones: List[Dict]) -> List[Dict]:
    """Дедупликация по ключу (normalized, extension, type)"""
    seen = set()
    unique = []
    
    for phone in phones:
        key = (
            phone.get('normalized'),
            phone.get('extension'),
            phone.get('type')
        )
        if key not in seen:
            seen.add(key)
            unique.append(phone)
    
    return unique
```

**Вызов** в `process_llm_response()` (после `_cleanup_organization_emails`):
```python
# После line ~450
organizations, contacts = self._cleanup_organization_emails(...)

# НОВОЕ:
organizations, contacts, phone_stats = self._normalize_all_phones(
    organizations, contacts
)
metadata['phone_normalization'] = phone_stats
```

---

### 4. LLM Prompt Enhancement

**Файл**: `prompts/unified_contact_extraction_structured.txt`

**Добавить после строки 28**:

```
📞 КРИТИЧЕСКИ ВАЖНО ДЛЯ ТЕЛЕФОНОВ:
1. НЕ включай добавочные номера в поле `number` или элемент массива `phones`
2. Указывай телефоны БЕЗ добавочных:
   - ✅ ПРАВИЛЬНО: `"phones": ["+7 (495) 640-17-71"]`
   - ❌ НЕПРАВИЛЬНО: `"phones": ["+7 (495) 640-17-71 (доб. 2026)"]`
3. Если видишь конструкцию типа `+7 (495) 933 71 47 (48)` — это ДВА номера:
   - Первый: `+7 (495) 933-71-47`
   - Второй: `+7 (495) 933-71-48` (замени последние цифры)
4. Если после номера есть "доб.", "ext" и т.п. — просто опусти эту часть
5. Для объектов phones используй только `type` и `number`:
   ```json
   "phones": [
     {"type": "office", "number": "+7 (495) 640-17-71"},
     {"type": "mobile", "number": "+7 (916) 584-82-77"}
   ]
   ```

⚠️ Примеры НЕПРАВИЛЬНЫХ телефонов (НЕ делай так):
- ❌ `"+7 (495) 640-17-71 (доб. 2026)"` — уберите "(доб. 2026)"
- ❌ `"8-926-535-18-55 доб:123"` — уберите "доб:123"
- ❌ `"+7(985)-170-03-87 ext.45"` — уберите "ext.45"
```

---

## Поток данных

### Входные форматы (от LLM)

**Вариант 1: Строки** (текущий, legacy):
```json
"phones": [
  "+7 (495) 640-17-71 (доб. 2026)",
  "8 800 200-75-15"
]
```

**Вариант 2: Объекты** (новый, предпочтительный):
```json
"phones": [
  {"type": "office", "number": "+7 (495) 640-17-71"},
  {"type": "main", "number": "8 800 200-75-15"}
]
```

**Вариант 3: Смешанный**:
```json
"phones": [
  "+7 (495) 640-17-71",
  {"type": "mobile", "number": "+7 (916) 584-82-77"}
]
```

### Промежуточная обработка

**PhoneNormalizer.normalize_phone_to_object()**:

```python
# Вход (string)
"+7 (495) 933 71 47 (48), доб.171"

# Шаг 1: Извлечение extension
base = "+7 (495) 933 71 47 (48)"
extension = "171"

# Шаг 2: Распознавание множественных
match = re.match(r'(.*?)\s*\((\d{2,})\)\s*$', base)
if match:
    primary = "+7 (495) 933 71 47"
    suffix = "48"
    
    # Создаём два номера
    phone1 = "+7 (495) 933 71 47"
    phone2 = "+7 (495) 933 71 48"  # последние 2 цифры заменены

# Шаг 3: E.164 нормализация
for phone in [phone1, phone2]:
    normalized = phonenumbers.format_number(..., E164)
    # Убираем '+' для хранения
    normalized = normalized[1:]  # "74959337147"

# Выход (List[Dict])
[
    {
        "type": "office",
        "number": "+7 (495) 933-71-47",
        "normalized": "+74959337147",
        "original": "+7 (495) 933 71 47 (48), доб.171",
        "extension": "171"
    },
    {
        "type": "office",
        "number": "+7 (495) 933-71-48",
        "normalized": "+74959337148",
        "original": "+7 (495) 933 71 47 (48), доб.171",
        "extension": "171"
    }
]
```

### Финальная структура

**Organizations**:
```json
{
  "organization_id": 1,
  "name": "МИЛЛАБ",
  "phones": [
    {
      "type": "main",
      "number": "+7 (495) 933-71-47",
      "normalized": "+74959337147",
      "original": "+7 (495) 933 71 47 (48), доб.171",
      "extension": "171",
      "confidence": 1.0
    },
    {
      "type": "main",
      "number": "+7 (495) 933-71-48",
      "normalized": "+74959337148",
      "original": "+7 (495) 933 71 47 (48), доб.171",
      "extension": "171",
      "confidence": 0.8
    },
    {
      "type": "mobile",
      "number": "+7 (968) 628-75-81",
      "normalized": "+79686287581",
      "original": "+7 (968) 628 75 81",
      "extension": null,
      "confidence": 1.0
    }
  ]
}
```

---

## Алгоритмы

### Парсинг добавочного

```python
def extract_extension(phone_str: str) -> Tuple[str, Optional[str]]:
    """
    Извлечение добавочного номера
    
    Поддерживаемые форматы:
    - доб., доб:, доб
    - доп., доп:
    - extension, ext, ext.
    - вн., в.н., внутр.
    - x (как префикс)
    """
    patterns = [
        r'(?i)[\(,]?\s*доб\.?\s*[:\-]?\s*([0-9]{1,10})\s*\)?',
        r'(?i)[\(,]?\s*доп\.?\s*[:\-]?\s*([0-9]{1,10})\s*\)?',
        r'(?i)[\(,]?\s*extension\s+([0-9]{1,10})\s*\)?',
        r'(?i)[\(,]?\s*ext\.?\s*[:\-]?\s*([0-9]{1,10})\s*\)?',
        r'(?i)[\(,]?\s*вн\.?\s*[:\-]?\s*([0-9]{1,10})\s*\)?',
        r'(?i)[\(,]?\s*в\.?\s*н\.?\s*[:\-]?\s*([0-9]{1,10})\s*\)?',
        r'(?i)\s+x\s*([0-9]{1,10})\s*\)?',
    ]
    
    for pattern in patterns:
        # Ищем справа налево (последний match)
        matches = list(re.finditer(pattern, phone_str))
        if matches:
            last_match = matches[-1]
            extension = last_match.group(1)
            
            # Удаляем из базовой строки
            phone_clean = phone_str[:last_match.start()] + phone_str[last_match.end():]
            phone_clean = phone_clean.strip(' ,;')
            
            return phone_clean, extension
    
    return phone_str, None
```

### Распознавание множественных номеров

```python
def split_compound_phones(phone_base: str) -> List[str]:
    """
    Распознаёт: "+7 (495) 933 71 47 (48)" → два номера
    """
    # Паттерн: цифры + пробел + (NN)
    match = re.search(r'^(.*?)\s*\((\d{2,})\)\s*$', phone_base.strip())
    
    if not match:
        return [phone_base]
    
    primary_part = match.group(1).strip()
    suffix_digits = match.group(2)
    
    # Извлекаем цифры из primary
    primary_digits = re.sub(r'\D', '', primary_part)
    
    # Проверка: достаточно ли цифр для замены
    if len(primary_digits) < len(suffix_digits):
        return [phone_base]  # Не множественный номер
    
    # Создаём второй номер заменой последних N цифр
    phone1_digits = primary_digits
    phone2_digits = primary_digits[:-len(suffix_digits)] + suffix_digits
    
    # Форматируем обратно
    phone1 = format_russian_phone(phone1_digits)
    phone2 = format_russian_phone(phone2_digits)
    
    return [phone1, phone2]
```

### Дедупликация

```python
def deduplicate_phones(phones: List[Dict]) -> List[Dict]:
    """
    Дедупликация по ключу (normalized, extension, type)
    """
    seen_keys = set()
    unique_phones = []
    
    for phone in phones:
        key = (
            phone.get('normalized'),
            phone.get('extension') or '',  # None → ''
            phone.get('type') or ''
        )
        
        if key not in seen_keys:
            seen_keys.add(key)
            unique_phones.append(phone)
        else:
            # Дубликат — можно объединить originals
            existing = next(p for p in unique_phones if (
                p.get('normalized') == phone.get('normalized') and
                p.get('extension') == phone.get('extension') and
                p.get('type') == phone.get('type')
            ))
            
            # Обновляем original если текущий полнее
            if len(phone.get('original', '')) > len(existing.get('original', '')):
                existing['original'] = phone.get('original')
    
    return unique_phones
```

---

## Обработка ошибок

### Graceful Degradation

**Если PhoneNormalizer упал**:
```python
try:
    phone_objects = normalizer.normalize_phone_to_object(phone_str)
except Exception as e:
    # Fallback: создаём минимальный объект
    phone_objects = [{
        "type": null,
        "number": phone_str,
        "normalized": null,
        "original": phone_str,
        "extension": null,
        "confidence": 0.3
    }]
    
    log_error(f"Phone normalization failed: {phone_str}, error: {e}")
```

### Backward Compatibility

**Validator должен принимать** старые файлы со строками:
```python
def _sanitize_organization(org):
    phones = org.get('phones', [])
    
    # Конвертация строк в объекты на лету
    normalized_phones = []
    for phone_entry in phones:
        if isinstance(phone_entry, str):
            normalized_phones.append({
                "type": null,
                "number": phone_entry,
                "original": phone_entry
            })
        else:
            normalized_phones.append(phone_entry)
    
    org['phones'] = normalized_phones
```

---

## Метаданные

### postprocessing_metadata.phone_normalization

```json
{
  "phone_normalization": {
    "version": "1.0.0",
    "org_phones_processed": 25,
    "contact_phones_processed": 48,
    "extensions_found": 12,
    "multiple_split": 2,
    "errors": [],
    "examples": [
      {
        "original": "+7 (495) 933 71 47 (48), доб.171",
        "result_count": 2,
        "extension": "171",
        "numbers": ["+7 (495) 933-71-47", "+7 (495) 933-71-48"]
      }
    ]
  }
}
```

---

## Тестирование

### Unit Tests

**Файл**: `tests/test_phone_normalizer.py`

```python
class TestPhoneNormalization:
    
    def test_simple_extension(self):
        """Простой добавочный"""
        result = normalize_phone_to_object("+7 (495) 640-17-71 (доб. 2026)")
        
        assert len(result) == 1
        assert result[0]['number'] == "+7 (495) 640-17-71"
        assert result[0]['extension'] == "2026"
        assert 'доб' not in result[0]['number']
    
    def test_compound_with_extension(self):
        """Множественный номер с добавочным"""
        result = normalize_phone_to_object("+7 (495) 933 71 47 (48), доб.171")
        
        assert len(result) == 2
        assert result[0]['normalized'] == "+74959337147"
        assert result[1]['normalized'] == "+74959337148"
        assert result[0]['extension'] == "171"
        assert result[1]['extension'] == "171"
        assert result[0]['original'] == result[1]['original']
    
    def test_no_duplicates(self):
        """Проверка отсутствия дублей"""
        result = normalize_phone_to_object("+7 (495) 933 71 47 (48), доб.171")
        
        normalized_set = {p['normalized'] for p in result}
        assert len(normalized_set) == len(result)  # Все уникальны
```

### Integration Tests

**Файл**: `tests/integration/test_email_014_015.py`

```python
def test_email_014_phone_normalization():
    """Проверка обработки email_014 после исправления"""
    
    from src.api_pipeline_validator import process_single_email
    
    result = process_single_email("email_014_20250729_...", "2025-07-29")
    
    assert result['success'] == True
    assert 'validation_error' not in result or not result['validation_error']
    
    # Проверка структуры телефонов
    org = result['organizations'][0]  # МИЛЛАБ
    phones = org['phones']
    
    # Должно быть 2-3 телефона (после split)
    assert len(phones) >= 2
    
    # Все phones — объекты
    assert all(isinstance(p, dict) for p in phones)
    
    # extension не в number
    for phone in phones:
        assert 'доб' not in phone.get('number', '')
        assert 'ext' not in phone.get('number', '')
    
    # Есть extension
    extensions = [p.get('extension') for p in phones if p.get('extension')]
    assert len(extensions) >= 1  # Минимум один телефон с extension
```

---

## Миграция

### Шаг 1: Обновить код

1. `src/core/validator.py` — новая схема
2. `src/postprocessing/phone_normalizer.py` — новые методы
3. `src/postprocessing/postprocessor.py` — интеграция
4. `prompts/unified_contact_extraction_structured.txt` — инструкции

### Шаг 2: Тестирование

1. Unit-тесты на новой логике
2. Интеграционные тесты на email_014, email_015
3. Regression на всех письмах 2025-07-29

### Шаг 3: Ре-процессинг

Перезапустить проблемные письма:
```bash
python scripts/reprocess_problematic_emails.py \
  --date 2025-07-29 \
  --emails email_014 email_015 email_025
```

---

## Альтернативы (отклонены)

### Альтернатива 1: Оставить phones как строки

**Плюсы**: Не нужно менять схему  
**Минусы**: Невозможно хранить structured данные (extension, type)  
**Решение**: ❌ Отклонено — не решает корневую проблему

### Альтернатива 2: Запретить LLM возвращать добавочные

**Плюсы**: Упрощает парсинг  
**Минусы**: Теряем информацию о добавочных номерах  
**Решение**: ❌ Отклонено — добавочные важны для бизнеса

### Альтернатива 3: Парсить добавочные в UI

**Плюсы**: Бэкенд не меняется  
**Минусы**: Дублирование логики, несогласованность данных  
**Решение**: ❌ Отклонено — single source of truth должен быть в БД
```
LLM Response (phones как строки)
    ↓
Validator (ожидает строки, но должен ожидать объекты) ❌
    ↓
PostProcessor
    ↓
PhoneNormalizer (добавляет extension обратно в number) ❌
    ↓
Final Result (с ошибками)
```

### Целевая схема обработки

```
LLM Response
    ↓
Sanitizer (конвертация строк → объекты если нужно)
    ↓
PhoneNormalizer (парсинг базового + extension)
    ├─ Извлечение extension
    ├─ Парсинг множественных номеров (48)
    └─ E.164 нормализация
    ↓
Validator (проверка объектов phones)
    ↓
PostProcessor (дедуп, GID assignment)
    ↓
Final Result (корректные данные)
```