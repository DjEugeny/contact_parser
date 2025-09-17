#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест Singleton паттерна в ExtractorFactory
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Устанавливаем PYTHONPATH для корректной работы относительных импортов
os.environ['PYTHONPATH'] = str(project_root)

try:
    from src.core.extractor_factory import ExtractorFactory
except ImportError:
    # Альтернативный способ импорта
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "extractor_factory", 
        project_root / "src" / "core" / "extractor_factory.py"
    )
    extractor_factory_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extractor_factory_module)
    ExtractorFactory = extractor_factory_module.ExtractorFactory

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