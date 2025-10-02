# PLAN-005: Нормализация телефонов и выделение `extension`

**Статус**: 🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА  
**Дата обнаружения**: 2025-10-02  
**Приоритет**: P0 (блокирующая)

---

## 🚨 Проблема

### Симптомы
Письма `email_014` и `email_015` падают с ошибкой валидации:
```
❌ JSON Schema валидация не прошла: ['+7 (495) 933 71 47 (48)', '+7 (495) 933 71 47 (48)'] has non-unique elements
```

### Корневая причина

**Входная строка**: `+7 (495) 933 71 47 (48), доб.171`

**Что происходит сейчас**:
1. [`PhoneNormalizer._split_multiple_phones()`](../../src/postprocessing/phone_normalizer.py:91-129) неправильно парсит `(48)` как второй номер
2. Создаётся дубль: `['+7 (495) 933 71 47 (48)', '+7 (495) 933 71 47 (48)']`
3. JSON Schema требует `uniqueItems: true` → валидация падает
4. [`PhoneNormalizer` добавляет](../../src/postprocessing/phone_normalizer.py:79-80) `extension` обратно в `formatted`, нарушая принцип разделения

**Что должно быть**:
- **Два базовых номера**: `+7 (495) 933-71-47` и `+7 (495) 933-71-48`
- **Каждый с добавочным**: `171`
- **Финальный результат**:
  ```json
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

### Архитектурные проблемы

1. **Validator Schema** ([`src/core/validator.py:675-683`](../../src/core/validator.py:675-683)):
   - Ожидает `phones: ["string"]` (массив строк)
   - Но должен быть `phones: [object]` (массив объектов)
   
2. **PhoneNormalizer** ([`src/postprocessing/phone_normalizer.py:79-80`](../../src/postprocessing/phone_normalizer.py:79-80)):
   - Добавочный **включается** в `number`/`formatted`
   - Должен быть только в `extension`

3. **LLM Prompt** ([`prompts/unified_contact_extraction_structured.txt:28`](../../prompts/unified_contact_extraction_structured.txt:28)):
   - Нет инструкций по обработке добавочных номеров

---

## 🎯 Цель решения

**ГЛАВНОЕ ПРАВИЛО**: 
> Поле `number` **НИКОГДА** не содержит добавочный номер.  
> Добавочный **ВСЕГДА** только в поле `extension`.

### Целевая структура телефона

```json
{
  "type": "mobile | office | fax | main | other | null",
  "number": "<UI формат БЕЗ добавочного>",
  "normalized": "<E.164 формат без добавочного>",
  "original": "<исходная строка как пришла>",
  "extension": "<только цифры добавочного или null>"
}
```

**Примеры**:

Вход: `+7 (495) 640-17-71 (доб. 2026)`
```json
{
  "type": "office",
  "number": "+7 (495) 640-17-71",
  "normalized": "+74956401771",
  "original": "+7 (495) 640-17-71 (доб. 2026)",
  "extension": "2026"
}
```

Вход: `+7 (495) 933 71 47 (48), доб.171`
```json
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

---

## 📦 Область работ

### 1. JSON Schema (Validator)
**Файл**: [`src/core/validator.py`](../../src/core/validator.py)

**Изменения**:
- Строки 620-686: Изменить схему организации
- Строки 730-733: Изменить схему контакта
- Удалить `organizations.phones` как массив строк
- Заменить на массив объектов с полями `{type, number, normalized, original, extension}`

### 2. PhoneNormalizer (Парсинг)
**Файл**: [`src/postprocessing/phone_normalizer.py`](../../src/postprocessing/phone_normalizer.py)

**Критические исправления**:

1. **Метод `_split_multiple_phones()`** (строки 91-129):
   - Правильно распознавать `(48)` как часть второго номера
   - НЕ создавать дубли

2. **Метод `normalize_contact_phone()`** (строки 79-80):
   ```python
   # УДАЛИТЬ:
   if extension:
       formatted = f"{formatted} (доб. {extension})"
   
   # ОСТАВИТЬ: extension в отдельном поле
   ```

3. **Метод `_extract_extension()`** (строки 131-159):
   - Поддержка всех форм: `доб.`, `доб:`, `ext`, `x`, `доп.`, `вн.`
   - Извлекать только последний (самый правый) добавочный

### 3. LLM Prompt
**Файл**: [`prompts/unified_contact_extraction_structured.txt`](../../prompts/unified_contact_extraction_structured.txt)

**Добавить** после строки 28:

```
📞 ПРАВИЛА ДЛЯ ТЕЛЕФОНОВ:
- НЕ включай добавочные номера (доб., ext) в поле `number`
- Указывай телефоны БЕЗ добавочных: `"+7 (495) 640-17-71"` вместо `"+7 (495) 640-17-71 (доб. 2026)"`
- Если в строке несколько номеров (например: `+7 (495) 933 71 47 (48)`) — это два номера: 
  * `+7 (495) 933-71-47` 
  * `+7 (495) 933-71-48`
- Примеры ПРАВИЛЬНО:
  * `"phones": ["+7 (495) 640-17-71", "8 800 200-75-15"]`
  * `"phones": [{"type": "office", "number": "+7 (495) 640-17-71"}]`
```

### 4. PostProcessor Integration
**Файл**: [`src/postprocessing/postprocessor.py`](../../src/postprocessing/postprocessor.py)

**Новый этап** (после `_cleanup_organization_emails`, перед `_assign_global_ids`):

```python
def _normalize_all_phones(self, organizations, contacts):
    """📞 Нормализация всех телефонов через PhoneNormalizer"""
    normalizer = PhoneNormalizer()
    
    # Нормализация phones организаций
    for org in organizations:
        if isinstance(org.get('phones'), list):
            normalized_phones = []
            for phone_entry in org['phones']:
                if isinstance(phone_entry, str):
                    # Парсим строку
                    results = normalizer.normalize_multiple_phones(phone_entry)
                    normalized_phones.extend(results)
                elif isinstance(phone_entry, dict):
                    # Уже объект — проверяем наличие extension в number
                    # и удаляем его если есть
                    normalized_phones.append(phone_entry)
            org['phones'] = normalized_phones
    
    # Аналогично для контактов
    return organizations, contacts
```

---

## 🧪 Тест-план

### Unit-тесты

**Файл**: `tests/test_phone_normalizer.py`

```python
def test_extension_parsing():
    """Тест извлечения добавочных номеров"""
    cases = [
        ("(доб. 2026)", "2026"),
        ("доб:171", "171"),
        ("ext 45", "45"),
        ("x1234", "1234"),
        ("вн. 101", "101"),
    ]
    
def test_multiple_phones_with_extension():
    """Тест парсинга: +7 (495) 933 71 47 (48), доб.171"""
    input_str = "+7 (495) 933 71 47 (48), доб.171"
    expected = [
        {
            "number": "+7 (495) 933-71-47",
            "normalized": "+74959337147",
            "extension": "171"
        },
        {
            "number": "+7 (495) 933-71-48",
            "normalized": "+74959337148",
            "extension": "171"
        }
    ]
```

### Интеграция

**Команда**:
```bash
python src/api_pipeline_validator.py --mode emails \
  --emails email_014 email_015 \
  --date 2025-07-29
```

**Критерии успеха**:
- ✅ Валидация проходит без ошибок `non-unique elements`
- ✅ В результате нет добавочных в `number`/`normalized`
- ✅ Все добавочные в `extension`
- ✅ `postprocessing_metadata.phone_normalization` содержит статистику

---

## 🎯 Definition of Done

1. **Валидация**:
   - JSON Schema принимает `phones` как массив объектов
   - Уникальность проверяется по `(normalized, extension, type)`

2. **Нормализация**:
   - `number` БЕЗ добавочного
   - `extension` отдельно (или `null`)
   - `normalized` в E.164 формате БЕЗ добавочного

3. **Парсинг**:
   - `+7 (495) 933 71 47 (48), доб.171` → 2 объекта
   - Каждый с `extension: "171"`
   - Разные `number` и `normalized`

4. **Письма**:
   - `email_014` и `email_015` успешно обрабатываются
   - `postprocessing_metadata` содержит детали нормализации

5. **Тесты**:
   - Unit-тесты покрывают все edge cases
   - Интеграционные тесты на реальных письмах

---

## 📚 Связанные документы

- [PLAN-004: Phone Ownership Disambiguation](../org-phone-disambiguation/PLAN-004_Org_Phone_Disambiguation.md)
- [PLAN-001: Email Classifier](../contact-email-filter/PLAN-001_Email_Classifier_and_OrgEmails_Cleanup.md)
- [Technical Specification](../../../memory-bank/mini_crm_prd/14_TECHNICAL_SPECIFICATION.md)

---

## 🔧 Порядок реализации

1. ✅ Анализ проблемы и создание спецификации
2. ⏳ Обновить JSON Schema в validator.py
3. ⏳ Исправить PhoneNormalizer
4. ⏳ Обновить промпт LLM
5. ⏳ Интегрировать в PostProcessor
6. ⏳ Написать тесты
7. ⏳ Провести интеграционное тестирование
8. ⏳ Создать отчёт

---

## ⚠️ Риски и ограничения

### Риски
- Миграция старых данных: существующие файлы с телефонами-строками
- Обратная совместимость с LLM, которая вернёт строки вместо объектов

### Ограничения
- **НЕ** включать `extension` в `number`/`normalized`
- **НЕ** добавлять новые поля к схеме phone
- **НЕ** менять имена существующих полей

### Митигация
- Graceful degradation: если LLM вернул строки → конвертировать в объекты
- Auto-correction в Validator для старых форматов
- Backward compatibility слой в PostProcessor
