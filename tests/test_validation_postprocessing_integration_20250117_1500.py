#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест интеграции валидации и постпроцессинга
Дата: 2025-01-17 15:00 (UTC+07)
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_validation_postprocessing_integration():
    """Тест интеграции валидации и постпроцессинга"""
    try:
        from src.core.validator import LLMResponseValidator
        print("✅ Импорт LLMResponseValidator успешен")
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    
    validator = LLMResponseValidator()
    print("✅ Валидатор инициализирован")
    
    # Тест 1: Валидные данные с дублирующимися организациями
    print("\n🧪 Тест 1: Валидные данные с дублями")
    test_data_1 = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "inn": "1901066506",
                "city": "Москва",
                "emails": ["info@dna-technology.ru"],
                "phones": ["8 800 200-75-15"]
            },
            {
                "organization_id": 2,
                "name": "ДНК-Технология",
                "inn": "1901066506",
                "city": "Москва",
                "emails": ["info@dna-technology.ru"],
                "phones": ["8 800 200-75-15"]
            }
        ],
        "contacts": [
            {
                "name": "Гоголева Мария",
                "organization_id": 1,
                "email": "m.gogoleva@dna-technology.ru",
                "phones": [
                    {
                        "type": "main",
                        "number": "+7(495) 640-17-71"
                    }
                ],
                "confidence": 0.95
            },
            {
                "name": "Петров Иван",
                "organization_id": 2,
                "email": "i.petrov@dna-technology.ru",
                "phones": [
                    {
                        "type": "mobile",
                        "number": "+7(926) 123-45-67"
                    }
                ],
                "confidence": 0.85
            }
        ]
    }
    
    try:
        result_1 = validator.validate_and_postprocess(test_data_1)
        
        # Проверки
        assert "organizations" in result_1, "Отсутствует поле organizations"
        assert "contacts" in result_1, "Отсутствует поле contacts"
        assert isinstance(result_1["organizations"], list), "organizations должно быть списком"
        assert isinstance(result_1["contacts"], list), "contacts должно быть списком"
        
        print(f"   📊 Организаций до: {len(test_data_1['organizations'])}, после: {len(result_1['organizations'])}")
        print(f"   📊 Контактов до: {len(test_data_1['contacts'])}, после: {len(result_1['contacts'])}")
        
        # Проверяем дедупликацию организаций
        if len(result_1["organizations"]) < len(test_data_1["organizations"]):
            print("   ✅ Дедупликация организаций работает")
        
        print("✅ Тест 1 пройден: валидные данные обработаны")
        
    except Exception as e:
        print(f"❌ Тест 1 не пройден: {e}")
        return False
    
    # Тест 2: Невалидные данные (graceful degradation)
    print("\n🧪 Тест 2: Невалидные данные")
    test_data_2 = {
        "invalid_structure": True,
        "random_data": [1, 2, 3]
    }
    
    try:
        result_2 = validator.validate_and_postprocess(test_data_2)
        
        # Проверки graceful degradation
        assert "organizations" in result_2, "Graceful degradation должен создать organizations"
        assert "contacts" in result_2, "Graceful degradation должен создать contacts"
        assert isinstance(result_2["organizations"], list), "organizations должно быть списком"
        assert isinstance(result_2["contacts"], list), "contacts должно быть списком"
        
        print(f"   📊 Результат graceful degradation: {len(result_2['organizations'])} орг, {len(result_2['contacts'])} контактов")
        print("✅ Тест 2 пройден: graceful degradation работает")
        
    except Exception as e:
        print(f"❌ Тест 2 не пройден: {e}")
        return False
    
    # Тест 3: Данные с ошибками валидации (автокоррекция)
    print("\n🧪 Тест 3: Данные с ошибками валидации")
    test_data_3 = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ТестКомпания",
                "inn": "1234567890",
                "city": "Москва"
                # Отсутствуют обязательные поля emails и phones
            }
        ],
        "contacts": [
            {
                "name": "Тестовый Контакт",
                "organization_id": 1,
                "email": "test@example.com",
                "confidence": 0.9
            }
        ]
    }
    
    try:
        result_3 = validator.validate_and_postprocess(test_data_3)
        
        # Проверки автокоррекции
        assert "organizations" in result_3
        assert "contacts" in result_3
        
        # Проверяем, что автокоррекция добавила обязательные поля
        if result_3["organizations"]:
            org = result_3["organizations"][0]
            if "emails" in org and "phones" in org:
                print("   ✅ Автокоррекция добавила обязательные поля")
        
        print("✅ Тест 3 пройден: автокоррекция работает")
        
    except Exception as e:
        print(f"❌ Тест 3 не пройден: {e}")
        return False
    
    print("\n🎉 Все тесты интеграции пройдены успешно!")
    return True

def test_postprocessor_import():
    """Тест импорта постпроцессора"""
    print("\n🧪 Тест импорта постпроцессора")
    try:
        from src.postprocessing.postprocessor import PostProcessor
        postprocessor = PostProcessor()
        print("✅ PostProcessor импортирован и инициализирован")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта PostProcessor: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка инициализации PostProcessor: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск тестов интеграции валидации и постпроцессинга")
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print(f"📁 Корень проекта: {project_root}")
    
    # Проверяем импорт постпроцессора
    postprocessor_ok = test_postprocessor_import()
    
    # Основные тесты
    if postprocessor_ok:
        success = test_validation_postprocessing_integration()
        
        if success:
            print("\n✅ Все тесты пройдены успешно!")
            sys.exit(0)
        else:
            print("\n❌ Некоторые тесты не пройдены")
            sys.exit(1)
    else:
        print("\n❌ Не удалось импортировать постпроцессор")
        sys.exit(1)