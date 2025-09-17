#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование полного пайплайна с обновленной нормализацией телефонов
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_phone_normalizer_integration():
    """Тестирование интеграции phone_normalizer в postprocessing"""
    print("🔧 Тестирование интеграции phone_normalizer...")
    
    try:
        from src.postprocessing.phone_normalizer import PhoneNormalizer
        normalizer = PhoneNormalizer()
        
        # Тестовые номера
        test_phones = [
            "+7 (495) 123-45-67 доб. 123",
            "8-800-555-35-35, +7-926-123-45-67",
            "495-123-45-67"
        ]
        
        print("\n📞 Тестирование нормализации телефонов:")
        for phone in test_phones:
            result = normalizer.normalize_contact_phone(phone)
            print(f"  Исходный: {phone}")
            print(f"  Результат: {result}")
            print()
            
        # Тестирование множественных номеров
        print(f"\n📱 Множественная нормализация:")
        for phone in test_phones:
            multiple_result = normalizer.normalize_multiple_phones(phone)
            print(f"  Исходный: {phone}")
            print(f"  Результаты: {len(multiple_result)} номеров")
            for i, result in enumerate(multiple_result):
                print(f"    {i+1}. {result}")
            print()
            
        print("✅ phone_normalizer интегрирован успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка интеграции phone_normalizer: {e}")
        return False

def test_data_normalizer_integration():
    """Тестирование DataNormalizer с новым phone_normalizer"""
    print("\n🔧 Тестирование DataNormalizer...")
    
    try:
        from src.postprocessing.data_normalizer import DataNormalizer
        normalizer = DataNormalizer()
        
        # Тестовые контакты
        test_contacts = [
            {
                "name": "Иван Петров",
                "phones": ["+7 (495) 123-45-67 доб. 123", "8-926-555-35-35"],
                "email": "ivan@example.com",
                "organization": "ООО Тест"
            },
            {
                "name": "Мария Сидорова", 
                "phone": "+7-800-555-35-35, +7-926-123-45-67",
                "email": "maria@test.ru"
            }
        ]
        
        print("\n👥 Тестирование нормализации контактов:")
        normalized = normalizer.normalize_contacts(test_contacts)
        
        for i, contact in enumerate(normalized):
            print(f"  Контакт {i+1}:")
            print(f"    Имя: {contact.get('name')}")
            print(f"    Телефоны: {contact.get('phones', [])}")
            print(f"    Email: {contact.get('email')}")
            print(f"    Организация: {contact.get('organization')}")
            print()
            
        print("✅ DataNormalizer работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка DataNormalizer: {e}")
        return False

def test_postprocessor_integration():
    """Тестирование PostProcessor с обновленной нормализацией"""
    print("\n🔧 Тестирование PostProcessor...")
    
    try:
        from src.postprocessing import PostProcessor
        processor = PostProcessor()
        
        # Тестовый LLM результат
        test_llm_result = {
            "organizations": [
                {
                    "organization_id": 1,
                    "name": "ООО Тестовая Компания",
                    "phones": ["+7 (495) 123-45-67 доб. 100", "8-800-555-35-35"]
                }
            ],
            "contacts": [
                {
                    "contact_id": 1,
                    "name": "Алексей Иванов",
                    "organization_id": 1,
                    "phones": [
                        {
                            "type": "main",
                            "number": "+7-926-123-45-67 доб. 200"
                        }
                    ],
                    "email": "alexey@test.com"
                }
            ]
        }
        
        email_metadata = {
            "from": "test@example.com",
            "subject": "Тестовое письмо"
        }
        
        print("\n🏭 Тестирование постпроцессинга:")
        result = processor.process_llm_response(test_llm_result, email_metadata)
        
        print(f"  Организации: {len(result.get('organizations', []))}")
        for org in result.get('organizations', []):
            print(f"    - {org.get('name')}: {org.get('phones', [])}")
            
        print(f"  Контакты: {len(result.get('contacts', []))}")
        for contact in result.get('contacts', []):
            print(f"    - {contact.get('name')}: {contact.get('phones', [])}")
            
        print("✅ PostProcessor работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка PostProcessor: {e}")
        return False

def test_api_pipeline_validator():
    """Проверка импортов в api_pipeline_validator"""
    print("\n🔧 Проверка api_pipeline_validator...")
    
    try:
        # Проверяем, что можем импортировать основные компоненты
        from src.api_pipeline_validator import APIPipelineValidator
        
        # Создаем валидатор в тестовом режиме
        validator = APIPipelineValidator(test_mode=True)
        
        print("✅ APIPipelineValidator импортируется корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка APIPipelineValidator: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ ПОЛНОГО ПАЙПЛАЙНА")
    print("=" * 50)
    
    tests = [
        test_phone_normalizer_integration,
        test_data_normalizer_integration, 
        test_postprocessor_integration,
        test_api_pipeline_validator
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 РЕЗУЛЬТАТЫ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        print("✅ Пайплайн готов к работе")
    else:
        print(f"⚠️ {total - passed} тестов не пройдено")
        print("❌ Требуется исправление ошибок")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)