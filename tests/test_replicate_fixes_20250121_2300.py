#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправлений Replicate провайдера
Создан: 2025-01-21 23:00 (UTC+07)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm_extractor import ContactExtractor
import time

def test_replicate_provider():
    """Тестирование исправлений Replicate провайдера"""
    
    print("🧪 Тест исправлений Replicate провайдера")
    print("=" * 50)
    
    # Инициализация с тестовым режимом
    extractor = ContactExtractor(test_mode=True)
    
    # Принудительно устанавливаем Replicate провайдер
    if 'replicate' in extractor.providers:
        extractor.current_provider = 'replicate'
        print(f"✅ Установлен провайдер: {extractor.current_provider}")
    else:
        print("❌ Replicate провайдер недоступен")
        return False
    
    # Тестовый текст
    test_text = """
    Добрый день!
    
    Меня зовут Анна Смирнова, я работаю в компании "ИнноТех" на должности директора по развитию.
    Мой email: anna.smirnova@innotech.ru, телефон: +7 (495) 987-65-43.
    
    Также хочу представить нашего технического директора:
    Петр Иванов, email: petr.ivanov@innotech.ru, тел: +7 (495) 987-65-44
    
    Компания "ИнноТех"
    Адрес: г. Москва, ул. Тверская, д. 10
    Сайт: www.innotech.ru
    
    С уважением,
    Анна Смирнова
    """
    
    print(f"📝 Тестовый текст ({len(test_text)} символов)")
    print("-" * 30)
    
    try:
        # Засекаем время выполнения
        start_time = time.time()
        
        # Выполняем извлечение контактов
        result = extractor.extract_contacts(test_text)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️ Время выполнения: {execution_time:.2f} секунд")
        print("-" * 30)
        
        # Проверяем результат
        if result['success']:
            print("✅ Извлечение контактов успешно")
            print(f"📊 Найдено контактов: {len(result['contacts'])}")
            
            for i, contact in enumerate(result['contacts'], 1):
                print(f"\n👤 Контакт {i}:")
                print(f"   Имя: {contact.get('name', 'Не указано')}")
                print(f"   Email: {contact.get('email', 'Не указан')}")
                print(f"   Телефон: {contact.get('phone', 'Не указан')}")
                print(f"   Компания: {contact.get('company', 'Не указана')}")
                print(f"   Должность: {contact.get('position', 'Не указана')}")
            
            # Проверяем статистику
            stats = extractor.get_stats()
            print(f"\n📈 Статистика:")
            print(f"   Успешных запросов: {stats['successful_requests']}")
            print(f"   Ошибок: {stats['failed_requests']}")
            print(f"   Повторных попыток: {stats['retry_attempts']}")
            
            return True
            
        else:
            print("❌ Ошибка извлечения контактов")
            print(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение во время тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_large_text_chunking():
    """Тестирование разбивки больших текстов"""
    
    print("\n🧪 Тест разбивки больших текстов")
    print("=" * 50)
    
    extractor = ContactExtractor(test_mode=True)
    
    if 'replicate' in extractor.providers:
        extractor.current_provider = 'replicate'
    else:
        print("❌ Replicate провайдер недоступен")
        return False
    
    # Создаем большой текст (более 10000 символов)
    base_text = """
    Контакт: Иван Петров, email: ivan@company.ru, тел: +7-495-123-4567
    Компания: ООО "Технологии", адрес: Москва, ул. Ленина, 1
    """
    
    large_text = base_text * 100  # Примерно 15000 символов
    
    print(f"📝 Большой текст ({len(large_text)} символов)")
    
    try:
        start_time = time.time()
        result = extractor.extract_contacts(large_text)
        end_time = time.time()
        
        print(f"⏱️ Время обработки: {end_time - start_time:.2f} секунд")
        
        if result['success']:
            print(f"✅ Обработка больших текстов работает")
            print(f"📊 Найдено контактов: {len(result['contacts'])}")
            return True
        else:
            print(f"❌ Ошибка обработки: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск тестов исправлений Replicate провайдера")
    print(f"📅 Время: 2025-01-21 23:00 (UTC+07)")
    print("=" * 60)
    
    # Запускаем тесты
    test1_result = test_replicate_provider()
    test2_result = test_large_text_chunking()
    
    print("\n" + "=" * 60)
    print("📋 Результаты тестирования:")
    print(f"   Основной тест Replicate: {'✅ ПРОЙДЕН' if test1_result else '❌ ПРОВАЛЕН'}")
    print(f"   Тест больших текстов: {'✅ ПРОЙДЕН' if test2_result else '❌ ПРОВАЛЕН'}")
    
    if test1_result and test2_result:
        print("\n🎉 Все тесты пройдены успешно!")
    else:
        print("\n⚠️ Некоторые тесты провалены. Требуется дополнительная отладка.")