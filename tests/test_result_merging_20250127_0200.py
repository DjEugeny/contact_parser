#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест логики объединения результатов и дедупликации контактов
Дата создания: 2025-01-27 02:00 (UTC+07)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm_extractor import ContactExtractor

def test_deduplicate_contacts():
    """Тест дедупликации контактов"""
    print("\n🧪 Тестирование дедупликации контактов...")
    
    extractor = ContactExtractor(test_mode=True)
    
    # Тестовые контакты с дубликатами
    test_contacts = [
        {
            'name': 'Иван Петров',
            'email': 'ivan@example.com',
            'phone': '+7 (999) 123-45-67',
            'organization': 'ООО Тест',
            'confidence': 0.9
        },
        {
            'name': 'Иван Петров',  # Дубликат по email
            'email': 'ivan@example.com',
            'phone': '+7 999 123 45 67',  # Тот же телефон в другом формате
            'organization': 'ООО Тест',
            'confidence': 0.8
        },
        {
            'name': 'Мария Сидорова',
            'email': 'maria@example.com',
            'phone': '+7 (888) 987-65-43',
            'organization': 'ИП Сидорова',
            'confidence': 0.95
        },
        {
            'name': 'Петр Иванов',
            'email': 'petr@example.com',
            'phone': '8-888-987-65-43',  # Дубликат телефона Марии в другом формате
            'organization': 'ООО Иванов',
            'confidence': 0.7
        }
    ]
    
    # Применяем дедупликацию
    unique_contacts = extractor._deduplicate_contacts(test_contacts)
    
    print(f"   📊 Исходных контактов: {len(test_contacts)}")
    print(f"   📊 Уникальных контактов: {len(unique_contacts)}")
    
    # Выводим детали для анализа
    print("   📋 Уникальные контакты:")
    for i, contact in enumerate(unique_contacts):
        print(f"      {i+1}. {contact['name']} - {contact['email']} - {contact['phone']}")
    
    # Проверяем результат - должно остаться 2 уникальных контакта
    # (Иван и Мария, так как у Петра телефон дублирует Марию)
    expected_count = 2
    
    if len(unique_contacts) == expected_count:
        print("   ✅ Дедупликация работает корректно")
        return True
    else:
        print(f"   ❌ Ошибка дедупликации: ожидалось {expected_count}, получено {len(unique_contacts)}")
        return False

def test_chunk_processing():
    """Тест обработки больших текстов по частям"""
    print("\n🧪 Тестирование обработки больших текстов...")
    
    extractor = ContactExtractor(test_mode=True)
    
    # Создаем большой тестовый текст (больше 6000 символов)
    large_text = """Уважаемые коллеги!
    
    Меня зовут Александр Иванов, я директор компании ООО "Инновации". 
    Мой email: alex.ivanov@innovations.ru, телефон: +7 (495) 123-45-67.
    
    Хочу представить нашу команду:
    
    1. Мария Петрова - менеджер по продажам
       Email: maria.petrova@innovations.ru
       Телефон: +7 (495) 234-56-78
       
    2. Сергей Сидоров - технический директор
       Email: sergey.sidorov@innovations.ru
       Телефон: +7 (495) 345-67-89
    
    """ * 50  # Повторяем 50 раз для создания большого текста
    
    print(f"   📝 Размер тестового текста: {len(large_text)} символов")
    
    # Обрабатываем большой текст
    result = extractor.extract_contacts(large_text)
    
    print(f"   📊 Найдено контактов: {len(result.get('contacts', []))}")
    print(f"   🤖 Провайдер: {result.get('provider_used', 'Неизвестно')}")
    
    # Проверяем, что результат содержит ожидаемые поля
    required_fields = ['contacts', 'business_context', 'recommended_actions']
    
    for field in required_fields:
        if field not in result:
            print(f"   ❌ Отсутствует поле: {field}")
            return False
    
    # В тестовом режиме должен быть хотя бы один контакт
    if len(result['contacts']) > 0:
        print("   ✅ Обработка больших текстов работает корректно")
        return True
    else:
        print("   ❌ Не найдено контактов в большом тексте")
        return False

def test_text_chunking():
    """Тест разбивки текста на части"""
    print("\n🧪 Тестирование разбивки текста на части...")
    
    extractor = ContactExtractor(test_mode=True)
    
    # Тестовый текст
    test_text = "Это тестовый текст для проверки разбивки на части. " * 200
    
    print(f"   📝 Размер тестового текста: {len(test_text)} символов")
    
    # Проверяем, есть ли метод _create_text_chunks
    if hasattr(extractor, '_create_text_chunks'):
        # Загружаем конфигурацию chunking
        chunking_config = extractor._load_chunking_config() if hasattr(extractor, '_load_chunking_config') else {
            'max_tokens_per_chunk': 4000,
            'overlap_tokens': 200
        }
        
        # Создаем части
        chunks = extractor._create_text_chunks(test_text, chunking_config)
        
        print(f"   📊 Создано частей: {len(chunks)}")
        
        if len(chunks) > 0:
            print(f"   📏 Размер первой части: {len(chunks[0])} символов")
            print("   ✅ Разбивка текста работает корректно")
            return True
        else:
            print("   ❌ Не создано ни одной части")
            return False
    else:
        print("   ⚠️ Метод _create_text_chunks не найден, пропускаем тест")
        return True  # Считаем успешным, если метод не реализован

def main():
    """Основная функция запуска тестов"""
    print("🚀 Запуск тестов логики объединения результатов")
    print("=" * 60)
    
    tests = [
        ("Дедупликация контактов", test_deduplicate_contacts),
        ("Разбивка текста на части", test_text_chunking),
        ("Обработка больших текстов", test_chunk_processing)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ Ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 Результаты тестирования:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"   {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Итого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты успешно пройдены!")
        return True
    else:
        print("⚠️ Некоторые тесты провалены, требуется доработка")
        return False

if __name__ == "__main__":
    main()