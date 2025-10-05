# Implementation Plan: Phones UI Format from Normalized

## Обзор

Реализация единого UI-формата для телефонов с санитизацией лишних полей и принудительной регенерацией `number` из `normalized`.

**Приоритет**: P1 (высокий)  
**Оценка**: 12-16 часов  
**Зависимости**: PLAN-004 (Phone Disambiguation), PLAN-005 (Phone Extension Normalization)

---

## Задачи

- [x] 1. Добавить санитизацию phone объектов в DataNormalizer
  - Создать метод `_sanitize_phone_keys()` для удаления лишних полей
  - Whitelist: `type`, `number`, `normalized`, `original`, `extension`
  - Логировать удаленные поля для отладки
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Добавить генерацию UI-формата из normalized
  - [x] 2.1 Создать метод `_format_ui_from_e164()` с использованием libphonenumber
    - Для RU: формат `+7 (XXX) XXX-XX-XX`
    - Для других стран: INTERNATIONAL формат
    - Обработка ошибок с fallback на original
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 2.2 Интегрировать регенерацию number в `_normalize_phone_entry()`
    - После нормализации через PhoneNormalizer
    - Перед возвратом результата
    - Только если normalized валиден
    - _Requirements: 3.1, 3.5, 4.2_

- [x] 3. Добавить метаданные санитизации в PostProcessor
  - Создать структуру `postprocessing_metadata.phone_ui_formatting`
  - Собирать статистику: phones_processed, ui_regenerated, fields_sanitized
  - Логировать удаленные поля по GID
  - _Requirements: 4.3, 6.2_

- [x] 4. Обновить обработку phone объектов от LLM
  - Проверять наличие готовых phone объектов с корректными полями
  - Применять санитизацию к LLM объектам
  - Регенерировать number если normalized валиден
  - _Requirements: 1.1, 3.1, 6.1_

- [x] 5. Написать unit-тесты
  - [x] 5.1 Тест санитизации phone keys
    - Удаление поля `confidence` из phone объекта
    - Удаление произвольных полей
    - Сохранение whitelist полей
    - _Requirements: 2.1, 2.2, 2.4_

  - [x] 5.2 Тест форматирования RU номеров
    - E.164 → `+7 (XXX) XXX-XX-XX`
    - Проверка скобок вокруг кода города
    - _Requirements: 3.2_

  - [x] 5.3 Тест форматирования международных номеров
    - E.164 → INTERNATIONAL формат
    - Различные страны (US, UK, DE)
    - _Requirements: 3.3_

  - [x] 5.4 Тест fallback при ошибках
    - Невалидный normalized → использование original
    - Exception в libphonenumber → graceful degradation
    - _Requirements: 3.4, 3.6_

- [x] 6. Интеграционное тестирование
  - Запуск на письмах с проблемными телефонами
  - Проверка отсутствия лишних полей в итоговом JSON
  - Проверка единообразия формата number
  - Валидация метаданных phone_ui_formatting
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 7. Обновить документацию
  - Добавить раздел в `src/postprocessing/README_postprocessing.md`
  - Описать санитизацию и UI-форматирование
  - Примеры использования и метаданных
  - _Requirements: 4.3_

---

## Детали реализации

### 1. Санитизация phone объектов

**Файл**: `src/postprocessing/data_normalizer.py`

**Метод**: `_sanitize_phone_keys()`

```python
def _sanitize_phone_keys(self, phone: dict) -> dict:
    """Удаляет лишние ключи из phone объекта (whitelist)
    
    Args:
        phone: Phone объект для санитизации
        
    Returns:
        dict: Санитизированный phone объект
    """
    ALLOWED_KEYS = {'type', 'number', 'normalized', 'original', 'extension'}
    removed = set(phone.keys()) - ALLOWED_KEYS
    
    if removed:
        self.logger.debug(f"Sanitized phone keys: {removed} from {phone.get('normalized', 'unknown')}")
    
    return {k: v for k, v in phone.items() if k in ALLOWED_KEYS}
```

**Интеграция**: Вызывать в конце `_normalize_phone_entry()` перед возвратом результата.

---

### 2. Генерация UI-формата

**Файл**: `src/postprocessing/data_normalizer.py`

**Метод**: `_format_ui_from_e164()`

```python
def _format_ui_from_e164(self, e164: str) -> str:
    """Форматирует E.164 номер в UI-формат
    
    Args:
        e164: Номер в формате E.164 (например, +74956401771)
        
    Returns:
        str: Отформатированный номер для UI
    """
    try:
        import phonenumbers
        
        num = phonenumbers.parse(e164, None)
        region = phonenumbers.region_code_for_number(num)
        formatted = phonenumbers.format_number(
            num, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )
        
        # Специальный формат для RU: +7 (XXX) XXX-XX-XX
        if region == "RU":
            import re
            # libphonenumber возвращает "+7 495 640-17-71"
            # Преобразуем в "+7 (495) 640-17-71"
            match = re.match(r'\+7\s+(\d{3})\s+(.+)', formatted)
            if match:
                return f"+7 ({match.group(1)}) {match.group(2)}"
        
        return formatted
        
    except Exception as e:
        self.logger.warning(f"Failed to format {e164}: {e}")
        return e164  # Fallback на исходное значение
```

**Интеграция**: Вызывать в `_normalize_phone_entry()` после получения результата от PhoneNormalizer:

```python
# В конце _normalize_phone_entry(), перед санитизацией:
for phone_obj in normalized_phones:
    # Регенерируем number из normalized
    if phone_obj.get('normalized'):
        phone_obj['number'] = self._format_ui_from_e164(phone_obj['normalized'])
    
    # Санитизация
    phone_obj = self._sanitize_phone_keys(phone_obj)
```

---

### 3. Метаданные санитизации

**Файл**: `src/postprocessing/postprocessor.py`

**Метод**: `_collect_phone_ui_stats()`

```python
def _collect_phone_ui_stats(self, organizations, contacts):
    """Собирает статистику UI-форматирования телефонов
    
    Returns:
        dict: Статистика обработки
    """
    stats = {
        'phones_processed': 0,
        'ui_format_regenerated': 0,
        'phones_sanitized': 0,
        'fields_removed': {}  # {gid: [field_names]}
    }
    
    # Подсчет для организаций
    for org in organizations:
        gid = org.get('organization_id')
        phones = org.get('phones', [])
        stats['phones_processed'] += len(phones)
        
        # Здесь можно добавить логику подсчета
        # (требует модификации _sanitize_phone_keys для возврата removed fields)
    
    # Аналогично для контактов
    for contact in contacts:
        gid = contact.get('contact_id')
        phones = contact.get('phones', [])
        stats['phones_processed'] += len(phones)
    
    return stats
```

**Интеграция**: Вызывать после нормализации данных, добавить в metadata:

```python
# В PostProcessor.process_llm_response():
phone_ui_stats = self._collect_phone_ui_stats(organizations, contacts)
metadata['phone_ui_formatting'] = phone_ui_stats
```

---

### 4. Обработка LLM phone объектов

**Модификация**: В `_normalize_phone_entry()` уже есть проверка LLM объектов:

```python
# Существующий код (строки ~200-210):
llm_phone_fields = {'type', 'number', 'normalized', 'original'}
if llm_phone_fields.issubset(entry.keys()):
    if entry.get('normalized') and entry['normalized'].strip():
        # Это готовый phone объект от LLM
        result_entry = dict(entry)
        
        # ДОБАВИТЬ: Регенерация UI-формата
        result_entry['number'] = self._format_ui_from_e164(result_entry['normalized'])
        
        # ДОБАВИТЬ: Санитизация
        result_entry = self._sanitize_phone_keys(result_entry)
        
        if 'extension' not in result_entry:
            result_entry['extension'] = None
        return [result_entry]
```

---

## Критерии приемки (DoD)

### Функциональные
- ✅ Все phone объекты содержат только whitelist поля
- ✅ Поле `number` регенерировано из `normalized` в UI-формате
- ✅ RU номера в формате `+7 (XXX) XXX-XX-XX`
- ✅ Международные номера в INTERNATIONAL формате
- ✅ Лишние поля (например, `confidence`) удалены
- ✅ Метаданные `phone_ui_formatting` содержат статистику

### Качественные
- ✅ Unit-тесты покрывают все edge cases
- ✅ Интеграционные тесты проходят на реальных письмах
- ✅ Нет регрессии в существующих тестах
- ✅ Документация обновлена
- ✅ Производительность не ухудшилась

### Валидация
- ✅ JSON Schema валидация проходит
- ✅ Нет дубликатов телефонов
- ✅ Extension не включен в `number`
- ✅ `normalized` в E.164 формате

---

## Тестовые данные

### Входные данные (примеры)

```json
{
  "phones": [
    {
      "type": "office",
      "number": "+7 495 640-17-71",
      "normalized": "+74956401771",
      "original": "+7 (495) 640-17-71",
      "confidence": 0.95,
      "source": "llm"
    }
  ]
}
```

### Ожидаемый результат

```json
{
  "phones": [
    {
      "type": "office",
      "number": "+7 (495) 640-17-71",
      "normalized": "+74956401771",
      "original": "+7 (495) 640-17-71",
      "extension": null
    }
  ]
}
```

**Изменения**:
- ✅ Удалены поля `confidence` и `source`
- ✅ `number` регенерирован в формат `+7 (XXX) XXX-XX-XX`
- ✅ Добавлено поле `extension` (null)

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Конфликт с PhoneNormalizer | Средняя | Высокое | Интеграция в существующий flow, не создавать параллельную логику |
| Производительность | Низкая | Среднее | Кэширование форматированных номеров |
| Обратная совместимость | Средняя | Среднее | Graceful degradation, fallback на original |
| Качество данных | Средняя | Среднее | Валидация E.164 перед форматированием |

---

## Связанные документы

- [PLAN-Phones_UI_from_Normalized.md](./PLAN-Phones_UI_from_Normalized.md)
- [requirements.md](./requirements.md)
- [analysis.md](./analysis.md)
- [PLAN-004: Phone Disambiguation](../org-phone-disambiguation/PLAN-004_Org_Phone_Disambiguation.md)
- [PLAN-005: Phone Extension Normalization](../phone-normalization/PLAN-005_Phone_Extension_Normalization.md)
- [README_postprocessing.md](../../src/postprocessing/README_postprocessing.md)

---

## Порядок выполнения

1. **Задача 1**: Санитизация (1-2 часа)
2. **Задача 2.1**: UI-форматирование (2-3 часа)
3. **Задача 2.2**: Интеграция в normalize_phone_entry (1 час)
4. **Задача 4**: Обработка LLM объектов (1 час)
5. **Задача 3**: Метаданные (2 часа)
6. **Задача 5**: Unit-тесты (3-4 часа)
7. **Задача 6**: Интеграционное тестирование (2-3 часа)
8. **Задача 7**: Документация (1-2 часа)

**Общая оценка**: 12-16 часов
