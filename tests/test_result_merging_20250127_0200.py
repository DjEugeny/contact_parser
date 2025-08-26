#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест логики объединения результатов из частей и дедупликации контактов
Создан: 2025-01-27 02:00 (UTC+07)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm_extractor import ContactExtractor
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_deduplicate_contacts():
    """Тест функции дедупликации контактов"""
    print("\n=== Тест дедупликации контактов ===")
    
    # Создаем экземпляр ContactExtractor в тестовом режиме
    extractor = ContactExtractor(test_mode=True)
    
    # Тестовые контакты с дубликатами
    test_contacts = [
        {
            "name": "Иван Петров",
            "email": "ivan@example.com",
            "phone": "+7 (123) 456-78-90",
            "confidence": 0.9
        },
        {
            "name": "Иван Петров",
            "email": "ivan@example.com",  # Дубликат по email
            "phone": "8-123-456-78-90",   # Тот же номер в другом формате
            "confidence": 0.8
        },
        {
            "name": "Мария Сидорова",
            "email": "maria@test.ru",
            "phone": "+7-987-654-32-10",
            "confidence": 0.95
        },
        {
            "name": "Петр Иванов",
            "email": "petr@company.com",
            "phone": "8 (987) 654 32 10",  # Дубликат по телефону
            "confidence": 0.85
        },
        {
            "name": "Анна Козлова",
            "email": "anna@mail.ru",
            "phone": "+7-555-123-45-67",
            "confidence": 0.7
        }
    ]
    
    print(f"Исходные контакты: {len(test_contacts)}")
    for i, contact in enumerate(test_contacts):
        print(f"  {i+1}. {contact['name']} - {contact['email']} - {contact['phone']}")
    
    # Применяем дедупликацию
    deduplicated = extractor._deduplicate_contacts(test_contacts)
    
    print(f"\nПосле дедупликации: {len(deduplicated)}")
    for i, contact in enumerate(deduplicated):
        print(f"  {i+1}. {contact['name']} - {contact['email']} - {contact['phone']} (confidence: {contact['confidence']})")
    
    # Проверяем результат
    expected_count = 3  # Ожидаем 3 уникальных контакта
    if len(deduplicated) == expected_count:
        print(f"✅ Дедупликация работает корректно: {len(deduplicated)} уникальных контактов")
        return True
    else:
        print(f"❌ Ошибка дедупликации: ожидалось {expected_count}, получено {len(deduplicated)}")
        return False

def test_chunk_processing():
    """Тест обработки больших текстов по частям"""
    print("\n=== Тест обработки текста по частям ===")
    
    # Создаем экземпляр ContactExtractor в тестовом режиме
    extractor = ContactExtractor(test_mode=True)
    
    # Создаем большой тестовый текст с контактами
    large_text = """
    Часть 1: Контакты отдела продаж
    
    Менеджер по продажам: Иван Петров
    Email: ivan.petrov@company.com
    Телефон: +7 (495) 123-45-67
    
    """ + "Дополнительная информация о компании. " * 1000 + """
    
    Часть 2: Контакты технического отдела
    
    Технический директор: Мария Сидорова
    Email: maria.sidorova@company.com
    Телефон: +7 (495) 987-65-43
    
    """ + "Техническая документация и описания. " * 1000 + """
    
    Часть 3: Контакты бухгалтерии
    
    Главный бухгалтер: Петр Иванов
    Email: petr.ivanov@company.com
    Телефон: +7 (495) 555-12-34
    
    """ + "Финансовая отчетность и документы. " * 1000
    
    print(f"Размер тестового текста: {len(large_text)} символов")
    
    # Обрабатываем большой текст
    try:
        result = extractor.extract_contacts(large_text)
        
        print(f"\nРезультат обработки:")
        print(f"Найдено контактов: {len(result.get('contacts', []))}")
        
        for i, contact in enumerate(result.get('contacts', [])):
            print(f"  {i+1}. {contact.get('name', 'N/A')} - {contact.get('email', 'N/A')} - {contact.get('phone', 'N/A')}")
        
        # Проверяем статистику
        stats = extractor.get_stats()
        print(f"\nСтатистика обработки:")
        print(f"  Всего чанков: {stats.get('total_chunks', 0)}")
        print(f"  Успешно обработано: {stats.get('successful_chunks', 0)}")
        print(f"  Ошибок: {stats.get('failed_chunks', 0)}")
        print(f"  Всего контактов до дедупликации: {stats.get('total_contacts_before_dedup', 0)}")
        print(f"  Контактов после дедупликации: {stats.get('total_contacts_after_dedup', 0)}")
        
        # В тестовом режиме должно быть 3 контакта
        expected_contacts = 3
        if len(result.get('contacts', [])) >= expected_contacts:
            print(f"✅ Обработка больших текстов работает корректно")
            return True
        else:
            print(f"❌ Найдено меньше контактов чем ожидалось")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при обработке большого текста: {e}")
        return False

def test_text_chunking():
    """Тест разбивки текста на части"""
    print("\n=== Тест разбивки текста на части ===")
    
    extractor = ContactExtractor(test_mode=True)
    
    # Создаем текст разного размера
    test_texts = [
        "Короткий текст с контактом: ivan@test.com",
        "Средний текст. " * 100 + " Контакт: maria@example.com, +7-123-456-78-90",
        "Длинный текст. " * 1000 + " Контакт: petr@company.ru, 8-987-654-32-10"
    ]
    
    for i, text in enumerate(test_texts):
        print(f"\nТекст {i+1}: {len(text)} символов")
        
        # Создаем чанки
        chunks = extractor._create_text_chunks(text, max_chunk_size=2000, overlap_size=200)
        
        print(f"  Количество чанков: {len(chunks)}")
        for j, chunk in enumerate(chunks):
            print(f"    Чанк {j+1}: {len(chunk)} символов")
            
        # Проверяем, что текст не потерялся
        total_unique_chars = len(set(text))
        chunks_unique_chars = len(set(''.join(chunks)))
        
        if chunks_unique_chars >= total_unique_chars * 0.9:  # 90% символов должны сохраниться
            print(f"  ✅ Разбивка корректна")
        else:
            print(f"  ❌ Потеря данных при разбивке")
            return False
    
    return True

def main():
    """Основная функция тестирования"""
    print("Тестирование логики объединения результатов и дедупликации")
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
            print(f"❌ Ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nПройдено тестов: {passed}/{len(results)}")
    
    if passed == len(results):
        print("🎉 Все тесты пройдены успешно!")
        return True
    else:
        print("⚠️  Некоторые тесты провалены")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)