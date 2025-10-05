# Критический анализ задачи: Phones UI Format from Normalized

## Обзор задачи

Задача направлена на устранение рассинхронизации между `number` и `normalized` в phone объектах, санитизацию лишних полей и обеспечение единого UI-формата.

## ✅ Сильные стороны плана

### 1. Четкий контракт данных
- **Whitelist полей**: Явное перечисление разрешенных ключей (`type`, `number`, `normalized`, `original`, `extension`) предотвращает утечку метаданных
- **Инварианты**: Четко определены роли каждого поля (source of truth, UI-формат, аудит)
- **Разделение ответственности**: `normalized` для машинной обработки, `number` для UI, `original` для аудита

### 2. Правильная интеграция в пайплайн
- **Место в цепочке**: После GID assignment и перед финальной нормализацией — логично
- **Не конфликтует с PLAN-004/005**: Дополняет существующую функциональность, не переписывает

### 3. Использование проверенных инструментов
- **libphonenumber**: Индустриальный стандарт для форматирования телефонов
- **E.164**: Международный стандарт для `normalized`

### 4. Graceful degradation
- **Fallback логика**: Если `normalized` невалиден, используется `original`
- **Error handling**: Исключения не ломают весь пайплайн

## ⚠️ Потенциальные проблемы и улучшения

### 1. **КРИТИЧНО: Дублирование логики с DataNormalizer**

**Проблема**: В `src/postprocessing/data_normalizer.py` уже есть метод `_normalize_phone_entry()`, который:
- Обрабатывает phone объекты от LLM
- Форматирует номера через `PhoneNormalizer`
- Определяет типы телефонов

**Риск**: Создание параллельной логики форматирования может привести к:
- Конфликтам между двумя форматтерами
- Дублированию кода
- Рассинхронизации при изменениях

**Рекомендация**: 
```python
# ВМЕСТО создания нового enforce_phone_ui()
# РАСШИРИТЬ существующий DataNormalizer._normalize_phone_entry()

def _normalize_phone_entry(self, entry, phone_type_hint=None):
    # ... существующая логика ...
    
    # ДОБАВИТЬ: Принудительная регенерация number из normalized
    if result.get('normalized'):
        result['number'] = self._format_ui_from_e164(result['normalized'])
    
    # ДОБАВИТЬ: Санитизация (whitelist)
    result = self._sanitize_phone_keys(result)
    
    return [result]
```

### 2. **ВАЖНО: Конфликт с PhoneNormalizer**

**Проблема**: `PhoneNormalizer.normalize_contact_phone()` уже генерирует `formatted` (который становится `number`). План предлагает **перезаписать** это значение.

**Текущий flow**:
```
LLM → PhoneNormalizer → DataNormalizer → [ваш код] → итоговый JSON
         ↓                    ↓                ↓
    генерирует number    сохраняет      перезаписывает?
```

**Риск**: 
- Двойное форматирование (производительность)
- Потеря информации о типе телефона (mobile/office)
- Конфликт форматов (PhoneNormalizer vs libphonenumber)

**Рекомендация**:
```python
# ВАРИАНТ A: Модифицировать PhoneNormalizer (предпочтительно)
# В PhoneNormalizer.normalize_contact_phone():
# Использовать libphonenumber для RU номеров вместо regex

# ВАРИАНТ B: Пропустить PhoneNormalizer для уже нормализованных
# В DataNormalizer._normalize_phone_entry():
if self._is_llm_phone_object(entry):
    # Уже обработан LLM, только регенерируем number
    return self._regenerate_ui_format(entry)
```

### 3. **СРЕДНЕ: Формат для RU номеров**

**Проблема**: План требует `+7 (XXX) XXX-XX-XX`, но libphonenumber для RU возвращает `+7 XXX XXX-XX-XX` (без скобок).

**Пример**:
```python
import phonenumbers as pn
num = pn.parse("+74956401771", None)
formatted = pn.format_number(num, pn.PhoneNumberFormat.INTERNATIONAL)
# Результат: "+7 495 640-17-71" (НЕ "+7 (495) 640-17-71")
```

**Рекомендация**:
```python
def format_ui_from_e164(e164: str) -> str:
    num = pn.parse(e164, None)
    region = pn.region_code_for_number(num)
    intl = pn.format_number(num, pn.PhoneNumberFormat.INTERNATIONAL)
    
    if region == "RU":
        # Преобразуем "+7 495 640-17-71" → "+7 (495) 640-17-71"
        import re
        match = re.match(r'\+7\s+(\d{3})\s+(.+)', intl)
        if match:
            return f"+7 ({match.group(1)}) {match.group(2)}"
    
    return intl
```

### 4. **СРЕДНЕ: Санитизация и метаданные**

**Проблема**: План требует логировать удаленные поля в `postprocessing_metadata.sanitizer.removed_props`, но:
- Эта структура не существует в текущем коде
- Нет механизма сбора статистики по санитизации

**Рекомендация**:
```python
# В PostProcessor.process_llm_response():
sanitizer_stats = {
    'phones_sanitized': 0,
    'fields_removed': {},  # {gid: [field_names]}
    'contacts_affected': [],
    'organizations_affected': []
}

# После санитизации:
metadata['sanitizer'] = sanitizer_stats
```

### 5. **НИЗКО: UI Guidelines для фронтенда**

**Проблема**: Раздел 4 (UI-рендеринг) — это не backend задача, а документация для фронтенда.

**Рекомендация**:
- Вынести в отдельный документ `docs/frontend/phone-display-guidelines.md`
- Или оставить как комментарий в requirements, но не реализовывать в backend

### 6. **НИЗКО: Extension в click-to-call**

**Проблема**: Формат `tel:+74956401771;ext=171` не поддерживается всеми браузерами/устройствами.

**Рекомендация**:
```javascript
// Frontend: Использовать паузы (запятые) для совместимости
const telLink = `tel:${normalized}${extension ? ',' + extension : ''}`;
// Результат: tel:+74956401771,171
```

## 🎯 Рекомендуемый план реализации

### Фаза 1: Интеграция с существующим кодом (КРИТИЧНО)

1. **Расширить DataNormalizer** вместо создания нового модуля:
   ```python
   # src/postprocessing/data_normalizer.py
   
   def _normalize_phone_entry(self, entry, phone_type_hint=None):
       # Существующая логика...
       
       # НОВОЕ: Санитизация
       result = self._sanitize_phone_keys(result)
       
       # НОВОЕ: Регенерация UI-формата
       if result.get('normalized'):
           result['number'] = self._format_ui_from_e164(result['normalized'])
       
       return [result]
   
   def _sanitize_phone_keys(self, phone: dict) -> dict:
       """Удаляет лишние ключи из phone объекта"""
       ALLOWED_KEYS = {'type', 'number', 'normalized', 'original', 'extension'}
       removed = set(phone.keys()) - ALLOWED_KEYS
       if removed:
           self.logger.debug(f"Sanitized phone keys: {removed}")
       return {k: v for k, v in phone.items() if k in ALLOWED_KEYS}
   
   def _format_ui_from_e164(self, e164: str) -> str:
       """Форматирует E.164 в UI-формат"""
       try:
           num = phonenumbers.parse(e164, None)
           region = phonenumbers.region_code_for_number(num)
           formatted = phonenumbers.format_number(
               num, phonenumbers.PhoneNumberFormat.INTERNATIONAL
           )
           
           # Специальный формат для RU
           if region == "RU":
               import re
               match = re.match(r'\+7\s+(\d{3})\s+(.+)', formatted)
               if match:
                   return f"+7 ({match.group(1)}) {match.group(2)}"
           
           return formatted
       except Exception as e:
           self.logger.warning(f"Failed to format {e164}: {e}")
           return e164  # Fallback
   ```

2. **Добавить метаданные санитизации** в PostProcessor:
   ```python
   # src/postprocessing/postprocessor.py
   
   def _collect_sanitizer_stats(self, organizations, contacts):
       """Собирает статистику санитизации после нормализации"""
       stats = {
           'phones_processed': 0,
           'phones_sanitized': 0,
           'ui_format_regenerated': 0
       }
       # ... логика подсчета ...
       return stats
   ```

### Фаза 2: Тестирование (ВАЖНО)

1. **Unit-тесты** для новых методов:
   ```python
   # tests/test_data_normalizer_ui_format.py
   
   def test_sanitize_phone_keys():
       """Тест удаления лишних ключей"""
       phone = {
           'type': 'mobile',
           'number': '+7 (495) 640-17-71',
           'normalized': '+74956401771',
           'confidence': 0.95,  # ДОЛЖЕН БЫТЬ УДАЛЕН
           'source': 'llm'      # ДОЛЖЕН БЫТЬ УДАЛЕН
       }
       result = normalizer._sanitize_phone_keys(phone)
       assert 'confidence' not in result
       assert 'source' not in result
       assert len(result) == 3
   
   def test_format_ui_from_e164_ru():
       """Тест форматирования RU номеров"""
       e164 = '+74956401771'
       result = normalizer._format_ui_from_e164(e164)
       assert result == '+7 (495) 640-17-71'
   
   def test_format_ui_from_e164_international():
       """Тест форматирования международных номеров"""
       e164 = '+12025551234'
       result = normalizer._format_ui_from_e164(e164)
       assert result.startswith('+1')
   ```

2. **Интеграционные тесты** на реальных письмах:
   ```bash
   python src/api_pipeline_validator.py --mode emails \
     --emails email_001 email_014 email_018 \
     --date 2025-07-29
   ```

### Фаза 3: Документация (СРЕДНЕ)

1. Обновить `src/postprocessing/README_postprocessing.md`:
   - Добавить раздел "Phone UI Format Generation"
   - Описать санитизацию и метаданные

2. Создать `docs/frontend/phone-display-guidelines.md`:
   - Правила отображения
   - Click-to-call форматы
   - Примеры кода

## 📊 Оценка сложности

| Компонент | Сложность | Время | Риск |
|-----------|-----------|-------|------|
| Интеграция с DataNormalizer | Средняя | 2-3 часа | Низкий |
| Форматирование RU номеров | Низкая | 1 час | Низкий |
| Санитизация phone keys | Низкая | 1 час | Низкий |
| Метаданные и статистика | Средняя | 2 часа | Средний |
| Unit-тесты | Средняя | 2-3 часа | Низкий |
| Интеграционные тесты | Высокая | 3-4 часа | Средний |
| Документация | Низкая | 1-2 часа | Низкий |
| **ИТОГО** | **Средняя** | **12-16 часов** | **Низкий-Средний** |

## 🎯 Финальные рекомендации

### ✅ СОГЛАСЕН с планом в части:
1. Контракт данных (whitelist полей)
2. Санитизация лишних полей
3. Использование libphonenumber
4. Graceful degradation

### ⚠️ ТРЕБУЕТ ДОРАБОТКИ:
1. **Интеграция**: Расширить DataNormalizer вместо создания нового модуля
2. **Формат RU**: Добавить regex для преобразования в `+7 (XXX) XXX-XX-XX`
3. **Метаданные**: Реализовать структуру `sanitizer` в metadata
4. **Тестирование**: Обязательные unit и integration тесты

### 🚀 ДОПОЛНИТЕЛЬНЫЕ УЛУЧШЕНИЯ:
1. **Кэширование**: Кэшировать форматированные номера для производительности
2. **Валидация**: Проверять E.164 перед форматированием
3. **Мониторинг**: Добавить метрики (сколько номеров перегенерировано, сколько fallback)
4. **Миграция**: Скрипт для обновления существующих файлов

## Вывод

План **хороший и реализуемый**, но требует **интеграции с существующим кодом** вместо создания параллельной логики. Основные риски — дублирование функциональности и конфликты с PhoneNormalizer. Рекомендую начать с расширения DataNormalizer и добавления санитизации, затем тестирование на реальных данных.
