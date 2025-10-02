#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔍 Отладочный скрипт для диагностики проблем с LLM ответами"""

import json
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.extractor_factory import ExtractorFactory

def test_simple_extraction():
    """Тестируем простое извлечение на коротком тексте"""
    
    # Простой тестовый текст
    test_text = """
    Добрый день!
    
    Меня зовут Иван Петров, я работаю в компании "ТестЛаб" (ИНН: 1234567890).
    Наш сайт: testlab.ru
    Мой телефон: +7 (495) 123-45-67
    Email: i.petrov@testlab.ru
    
    Адрес: 123456, г. Москва, ул. Тестовая, д. 1
    
    Прошу выслать коммерческое предложение на амплификатор ДНК.
    
    С уважением,
    Иван Петров
    """
    
    print("🧪 Тестируем простое извлечение контактов...")
    print(f"📝 Текст для анализа ({len(test_text)} символов):")
    print(test_text)
    print("\n" + "="*50 + "\n")
    
    try:
        # Создаем экстрактор
        extractor = ExtractorFactory.create_extractor(test_mode=False)
        
        # Тестовые метаданные
        metadata = {
            "from": "i.petrov@testlab.ru",
            "to": "sales@dna-technology.ru", 
            "subject": "Запрос КП на амплификатор",
            "date": "2025-09-28T15:00:00+07:00"
        }
        
        print("🤖 Запускаем извлечение...")
        result = extractor.extract_all_data(test_text, metadata)
        
        print("✅ Результат получен!")
        print(f"📊 Статистика:")
        print(f"   - Организации: {len(result.get('organizations', []))}")
        print(f"   - Контакты: {len(result.get('contacts', []))}")
        print(f"   - КП: {len(result.get('commercial_offers', []))}")
        print(f"   - Взаимодействия: {len(result.get('interactions', []))}")
        print(f"   - Провайдер: {result.get('provider_used', 'неизвестно')}")
        print(f"   - Время обработки: {result.get('processing_time', 0):.2f} сек")
        
        # Показываем найденные организации
        if result.get('organizations'):
            print("\n🏢 Найденные организации:")
            for org in result['organizations']:
                print(f"   - {org.get('name', 'Без названия')} (ID: {org.get('organization_id')})")
                print(f"     ИНН: {org.get('inn', 'не указан')}")
                print(f"     Сайт: {org.get('website', 'не указан')}")
                print(f"     Город: {org.get('city', 'не указан')}")
                print(f"     Emails: {', '.join(org.get('emails', []))}")
                print(f"     Телефоны: {', '.join(org.get('phones', []))}")
        
        # Показываем найденные контакты
        if result.get('contacts'):
            print("\n👤 Найденные контакты:")
            for contact in result['contacts']:
                print(f"   - {contact.get('name', 'Без имени')} (ID: {contact.get('contact_id')})")
                print(f"     Должность: {contact.get('position', 'не указана')}")
                print(f"     Email: {contact.get('email', 'не указан')}")
                phones = contact.get('phones', [])
                if phones:
                    phone_str = []
                    for phone in phones:
                        if isinstance(phone, dict):
                            phone_str.append(f"{phone.get('number', '')} ({phone.get('type', 'неизвестно')})")
                        else:
                            phone_str.append(str(phone))
                    print(f"     Телефоны: {', '.join(phone_str)}")
                print(f"     Роль: {contact.get('role_in_message', 'не указана')}")
                print(f"     Confidence: {contact.get('confidence', 0)}")
        
        # Показываем бизнес-контекст
        if result.get('business_context'):
            print(f"\n💼 Бизнес-контекст: {result['business_context']}")
        
        # Показываем summary
        if result.get('summary'):
            summary = result['summary']
            print(f"\n📋 Резюме:")
            print(f"   - Тема: {summary.get('topic', 'не определена')}")
            print(f"   - Интерес к продукту: {summary.get('product_interest', 'не определен')}")
            print(f"   - Стадия коммуникации: {summary.get('communication_stage', 'не определена')}")
            print(f"   - Тип запроса: {summary.get('request_type', 'не определен')}")
        
        # Показываем ключевые моменты
        if result.get('key_points'):
            print(f"\n🔑 Ключевые моменты:")
            for i, point in enumerate(result['key_points'], 1):
                print(f"   {i}. {point}")
        
        # Проверяем наличие ошибок
        if result.get('validation_error'):
            print(f"\n⚠️ Обнаружена ошибка валидации!")
        
        if result.get('error'):
            print(f"\n❌ Ошибка: {result['error']}")
        
        # Сохраняем результат в файл для анализа
        debug_file = PROJECT_ROOT / "debug_result.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Результат сохранен в {debug_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_real_email():
    """Тестируем на реальном письме из датасета"""
    
    email_file = PROJECT_ROOT / "data/emails/2025-07-29/email_001_20250729_20250729_centerld_ru_d03bd60b.json"
    
    if not email_file.exists():
        print(f"❌ Файл письма не найден: {email_file}")
        return None
    
    print("🧪 Тестируем на реальном письме...")
    
    try:
        with open(email_file, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        text = email_data.get('body', '')
        print(f"📝 Текст письма ({len(text)} символов):")
        print(text[:500] + "..." if len(text) > 500 else text)
        print("\n" + "="*50 + "\n")
        
        # Создаем экстрактор
        extractor = ExtractorFactory.create_extractor(test_mode=False)
        
        # Метаданные из письма
        metadata = {
            "from": email_data.get('from', ''),
            "to": email_data.get('to', ''),
            "subject": email_data.get('subject', ''),
            "date": email_data.get('parsed_date', ''),
            "message_id": email_data.get('message_id', ''),
            "thread_id": email_data.get('thread_id', '')
        }
        
        print("🤖 Запускаем извлечение...")
        result = extractor.extract_all_data(text, metadata)
        
        print("✅ Результат получен!")
        print(f"📊 Статистика:")
        print(f"   - Организации: {len(result.get('organizations', []))}")
        print(f"   - Контакты: {len(result.get('contacts', []))}")
        print(f"   - КП: {len(result.get('commercial_offers', []))}")
        print(f"   - Взаимодействия: {len(result.get('interactions', []))}")
        print(f"   - Провайдер: {result.get('provider_used', 'неизвестно')}")
        print(f"   - Время обработки: {result.get('processing_time', 0):.2f} сек")
        print(f"   - Успех: {result.get('success', False)}")
        
        # Проверяем наличие ошибок
        if result.get('validation_error'):
            print(f"\n⚠️ Обнаружена ошибка валидации!")
        
        if result.get('error'):
            print(f"\n❌ Ошибка: {result['error']}")
        
        # Сохраняем результат в файл для анализа
        debug_file = PROJECT_ROOT / "debug_real_email_result.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Результат сохранен в {debug_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании реального письма: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🔍 Диагностика проблем с LLM ответами")
    print("="*50)
    
    # Тест 1: Простое извлечение
    print("\n1️⃣ Тест простого извлечения:")
    simple_result = test_simple_extraction()
    
    # Тест 2: Реальное письмо
    print("\n2️⃣ Тест реального письма:")
    real_result = test_real_email()
    
    print("\n🏁 Диагностика завершена!")