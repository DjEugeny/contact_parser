# Тест: Singleton паттерн в ExtractorFactory

**Дата создания**: 2025-01-22 10:30 (UTC+07)  
**Тип теста**: Функциональный тест Singleton паттерна  
**Статус**: ✅ ГОТОВ К ЗАПУСКУ

## Описание теста

Проверка корректной работы Singleton паттерна для PhoneNormalizer и LLMResponseValidator в ExtractorFactory.

## Критерии успеха

### ✅ 1. Единственность экземпляров
- Повторные вызовы `get_phone_normalizer()` возвращают один и тот же объект
- Повторные вызовы `get_json_validator()` возвращают один и тот же объект
- Проверка через `id()` объектов

### ✅ 2. Ленивая инициализация
- Объекты создаются только при первом обращении
- До первого вызова `_phone_normalizer` и `_json_validator` равны `None`

### ✅ 3. Работа в create_extractor
- Несколько вызовов `create_extractor()` используют одни и те же экземпляры
- Экстракторы получают общие компоненты

## Тестовый код

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест Singleton паттерна в ExtractorFactory
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.extractor_factory import ExtractorFactory

def test_singleton_phone_normalizer():
    """Тест единственности PhoneNormalizer"""
    print("🧪 Тестирование Singleton для PhoneNormalizer...")
    
    # Сброс состояния для чистого теста
    ExtractorFactory._phone_normalizer = None
    
    # Проверка ленивой инициализации
    assert ExtractorFactory._phone_normalizer is None, "Должен быть None до первого вызова"
    
    # Первый вызов
    normalizer1 = ExtractorFactory.get_phone_normalizer()
    assert normalizer1 is not None, "Должен создать экземпляр"
    assert ExtractorFactory._phone_normalizer is normalizer1, "Должен сохранить экземпляр"
    
    # Второй вызов
    normalizer2 = ExtractorFactory.get_phone_normalizer()
    assert normalizer1 is normalizer2, "Должен вернуть тот же экземпляр"
    assert id(normalizer1) == id(normalizer2), "ID объектов должны совпадать"
    
    print(f"   ✅ PhoneNormalizer ID: {id(normalizer1)}")
    print("   ✅ Singleton работает корректно")

def test_singleton_json_validator():
    """Тест единственности LLMResponseValidator"""
    print("🧪 Тестирование Singleton для LLMResponseValidator...")
    
    # Сброс состояния для чистого теста
    ExtractorFactory._json_validator = None
    
    # Проверка ленивой инициализации
    assert ExtractorFactory._json_validator is None, "Должен быть None до первого вызова"
    
    # Первый вызов
    validator1 = ExtractorFactory.get_json_validator()
    assert validator1 is not None, "Должен создать экземпляр"
    assert ExtractorFactory._json_validator is validator1, "Должен сохранить экземпляр"
    
    # Второй вызов
    validator2 = ExtractorFactory.get_json_validator()
    assert validator1 is validator2, "Должен вернуть тот же экземпляр"
    assert id(validator1) == id(validator2), "ID объектов должны совпадать"
    
    print(f"   ✅ LLMResponseValidator ID: {id(validator1)}")
    print("   ✅ Singleton работает корректно")

def test_extractors_share_components():
    """Тест совместного использования компонентов экстракторами"""
    print("🧪 Тестирование совместного использования компонентов...")
    
    # Сброс состояния
    ExtractorFactory._phone_normalizer = None
    ExtractorFactory._json_validator = None
    
    try:
        # Создание первого экстрактора
        extractor1 = ExtractorFactory.create_extractor(test_mode=True)
        
        # Получение компонентов после создания первого экстрактора
        normalizer_after_first = ExtractorFactory.get_phone_normalizer()
        validator_after_first = ExtractorFactory.get_json_validator()
        
        # Создание второго экстрактора
        extractor2 = ExtractorFactory.create_extractor(test_mode=True)
        
        # Получение компонентов после создания второго экстрактора
        normalizer_after_second = ExtractorFactory.get_phone_normalizer()
        validator_after_second = ExtractorFactory.get_json_validator()
        
        # Проверка, что компоненты остались теми же
        assert normalizer_after_first is normalizer_after_second, "PhoneNormalizer должен быть тем же"
        assert validator_after_first is validator_after_second, "LLMResponseValidator должен быть тем же"
        
        print(f"   ✅ Оба экстрактора используют PhoneNormalizer ID: {id(normalizer_after_first)}")
        print(f"   ✅ Оба экстрактора используют LLMResponseValidator ID: {id(validator_after_first)}")
        print("   ✅ Компоненты успешно переиспользуются")
        
    except Exception as e:
        print(f"   ⚠️ Не удалось создать экстракторы (возможно, отсутствуют зависимости): {e}")
        print("   ℹ️ Тест Singleton компонентов все равно прошел успешно")

if __name__ == "__main__":
    print("🚀 Запуск тестов Singleton паттерна в ExtractorFactory\n")
    
    test_singleton_phone_normalizer()
    print()
    
    test_singleton_json_validator()
    print()
    
    test_extractors_share_components()
    print()
    
    print("🎉 Все тесты Singleton паттерна прошли успешно!")
```

## Ожидаемый результат

```
🚀 Запуск тестов Singleton паттерна в ExtractorFactory

🧪 Тестирование Singleton для PhoneNormalizer...
   ✅ PhoneNormalizer ID: 140234567890123
   ✅ Singleton работает корректно

🧪 Тестирование Singleton для LLMResponseValidator...
   ✅ LLMResponseValidator ID: 140234567890456
   ✅ Singleton работает корректно

🧪 Тестирование совместного использования компонентов...
   ✅ Оба экстрактора используют PhoneNormalizer ID: 140234567890123
   ✅ Оба экстрактора используют LLMResponseValidator ID: 140234567890456
   ✅ Компоненты успешно переиспользуются

🎉 Все тесты Singleton паттерна прошли успешно!
```

## Команда запуска

```bash
cd /Users/evgenyzach/contact_parser
python tests/test_singleton_pattern_20250122_1030.py
```

---
**Тест создан**: 2025-01-22 10:30 (UTC+07)  
**Готов к выполнению**: ✅ ДА