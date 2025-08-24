#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест fallback системы ContactExtractor
Дата создания: 2025-01-21 23:15 (UTC+07)
"""

import sys
import os
import json
from datetime import datetime

# Добавляем путь к корневой папке проекта и src
project_root = os.path.join(os.path.dirname(__file__), '..')
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

try:
    from llm_extractor import ContactExtractor
    from advanced_email_fetcher import AdvancedEmailFetcherV2
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print(f"Путь к проекту: {project_root}")
    print(f"Путь к src: {src_path}")
    print(f"Содержимое корня: {os.listdir(project_root) if os.path.exists(project_root) else 'Папка не найдена'}")
    sys.exit(1)

def test_fallback_system():
    """Тестирование fallback системы с реальными данными"""
    
    print("🧪 Тест fallback системы ContactExtractor")
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
    print("="*60)
    
    # Инициализируем экстрактор
    extractor = ContactExtractor(test_mode=False)
    
    # 1. Проверяем начальное состояние системы
    print("\n1️⃣ Проверка начального состояния системы:")
    health = extractor.get_provider_health()
    print(f"   Текущий провайдер: {health['current_provider']}")
    print(f"   Здоровье системы: {health['system_health']}")
    
    for provider_id, provider_info in health['providers'].items():
        print(f"   {provider_info['name']}: {provider_info['status']} (приоритет: {provider_info['priority']})")
    
    if health['recommendations']:
        print("   Рекомендации:")
        for rec in health['recommendations']:
            print(f"   - {rec}")
    
    # 2. Тестируем симуляцию отказа провайдера
    print("\n2️⃣ Тестирование симуляции отказа провайдера:")
    
    # Симулируем отказ текущего провайдера
    current_provider = extractor.current_provider
    print(f"   Симулируем отказ провайдера: {extractor.providers[current_provider]['name']}")
    
    failure_result = extractor.simulate_provider_failure(current_provider)
    print(f"   Результат: {failure_result['message']}")
    print(f"   Новый провайдер: {extractor.providers[failure_result['current_provider']]['name']}")
    
    # 3. Проверяем состояние после отказа
    print("\n3️⃣ Состояние системы после отказа:")
    health_after = extractor.get_provider_health()
    print(f"   Здоровье системы: {health_after['system_health']}")
    print(f"   Текущий провайдер: {health_after['current_provider']}")
    
    # 4. Тестируем с реальными данными (если доступны)
    print("\n4️⃣ Тестирование с реальными данными:")
    
    try:
        # Пробуем получить реальные письма
        fetcher = AdvancedEmailFetcherV2(logger=None)
        emails = fetcher.fetch_emails_by_date('2025-01-15', limit=3)
        
        if emails:
            print(f"   Получено {len(emails)} писем для тестирования")
            
            for i, email in enumerate(emails[:2], 1):  # Тестируем только первые 2 письма
                print(f"\n   📧 Письмо {i}: {email.get('subject', 'Без темы')[:50]}...")
                
                # Извлекаем контакты
                result = extractor.extract_contacts(
                    email.get('body', ''),
                    metadata={'subject': email.get('subject', ''), 'date': email.get('date', '')}
                )
                
                print(f"      Провайдер: {result.get('provider_used', 'Неизвестно')}")
                print(f"      Найдено контактов: {len(result.get('contacts', []))}")
                
                if result.get('contacts'):
                    for contact in result['contacts'][:2]:  # Показываем первые 2 контакта
                        print(f"      - {contact.get('name', 'Без имени')}: {contact.get('email', 'Без email')}")
        else:
            print("   ⚠️ Реальные письма недоступны, используем тестовые данные")
            
            # Тестовые данные
            test_emails = [
                "Привет! Меня зовут Иван Петров, мой email: ivan.petrov@example.com, телефон +7 (999) 123-45-67",
                "Контакты нашей компании: support@company.ru, директор Анна Сидорова (anna.sidorova@company.ru)"
            ]
            
            for i, test_text in enumerate(test_emails, 1):
                print(f"\n   📧 Тестовое письмо {i}")
                result = extractor.extract_contacts(test_text)
                print(f"      Провайдер: {result.get('provider_used', 'Неизвестно')}")
                print(f"      Найдено контактов: {len(result.get('contacts', []))}")
                
    except Exception as e:
        print(f"   ❌ Ошибка при работе с письмами: {e}")
        print("   Используем простые тестовые данные")
        
        # Простой тест
        test_text = "Свяжитесь с нами: info@test.com, менеджер Петр Иванов +7 (123) 456-78-90"
        result = extractor.extract_contacts(test_text)
        print(f"   Провайдер: {result.get('provider_used', 'Неизвестно')}")
        print(f"   Найдено контактов: {len(result.get('contacts', []))}")
    
    # 5. Сброс состояния системы
    print("\n5️⃣ Сброс состояния системы:")
    reset_result = extractor.reset_system_state()
    print(f"   {reset_result['message']}")
    print(f"   Текущий провайдер: {extractor.providers[reset_result['current_provider']]['name']}")
    print(f"   Активные провайдеры: {len(reset_result['active_providers'])}")
    
    # 6. Финальная статистика
    print("\n6️⃣ Финальная статистика:")
    stats = extractor.get_stats()
    print(f"   Всего запросов: {stats['total_requests']}")
    print(f"   Успешных: {stats['successful_requests']}")
    print(f"   Неудачных: {stats['failed_requests']}")
    print(f"   Переключений fallback: {stats['fallback_switches']}")
    print(f"   Ошибки провайдеров:")
    for provider, count in stats['provider_failures'].items():
        print(f"     {provider}: {count}")
    
    print("\n✅ Тест fallback системы завершен")
    print(f"⏰ Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
    
    return True

if __name__ == "__main__":
    test_fallback_system()