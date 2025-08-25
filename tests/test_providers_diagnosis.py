#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Диагностика провайдеров LLM для выявления проблем с лимитами и сбоями
"""

import json
import time
from src.llm_extractor import ContactExtractor
from datetime import datetime

def test_provider_health():
    """Тестирование состояния всех провайдеров"""
    print("🔍 Диагностика провайдеров LLM")
    print("=" * 50)
    
    # Создаем экстрактор без тестового режима
    extractor = ContactExtractor(test_mode=False)
    
    # Тестовый текст для проверки
    test_text = """Письмо от Иван Петров, email: ivan.petrov@example.com, 
    телефон: +7 (495) 123-45-67, компания ООО Тест, должность менеджер."""
    
    print(f"📝 Тестовый текст: {test_text[:50]}...")
    print()
    
    # Получаем информацию о здоровье провайдеров
    health_before = extractor.get_provider_health()
    print("🏥 Состояние провайдеров ДО тестирования:")
    for provider, status in health_before.items():
        print(f"   {provider}: {status}")
    print()
    
    # Тестируем извлечение контактов
    print("🚀 Запуск реального теста извлечения контактов...")
    start_time = time.time()
    
    try:
        result = extractor.extract_contacts(test_text)
        end_time = time.time()
        
        print(f"✅ Тест завершен за {end_time - start_time:.2f} секунд")
        print(f"🎯 Использован провайдер: {result.get('provider_used', 'Неизвестно')}")
        print(f"👥 Найдено контактов: {len(result.get('contacts', []))}")
        
        # Выводим найденные контакты
        if result.get('contacts'):
            print("\n📋 Найденные контакты:")
            for i, contact in enumerate(result['contacts'], 1):
                print(f"   {i}. {contact.get('name', 'Без имени')} - {contact.get('email', 'Без email')}")
        
    except Exception as e:
        end_time = time.time()
        print(f"❌ Ошибка при тестировании: {str(e)}")
        print(f"⏱️ Время до ошибки: {end_time - start_time:.2f} секунд")
    
    # Получаем статистику после теста
    print("\n📊 Статистика после тестирования:")
    stats = extractor.get_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for sub_key, sub_value in value.items():
                print(f"     {sub_key}: {sub_value}")
        else:
            print(f"   {key}: {value}")
    
    # Проверяем здоровье провайдеров после теста
    print("\n🏥 Состояние провайдеров ПОСЛЕ тестирования:")
    health_after = extractor.get_provider_health()
    for provider, status in health_after.items():
        print(f"   {provider}: {status}")
        
        # Сравниваем с состоянием до теста
        if health_before.get(provider) != status:
            print(f"     ⚠️ ИЗМЕНЕНИЕ: было {health_before.get(provider)}")
    
    return {
        'health_before': health_before,
        'health_after': health_after,
        'stats': stats,
        'test_completed': True
    }

def test_individual_providers():
    """Тестирование каждого провайдера отдельно"""
    print("\n" + "=" * 50)
    print("🔬 Индивидуальное тестирование провайдеров")
    print("=" * 50)
    
    extractor = ContactExtractor(test_mode=False)
    test_text = "Тест от test@example.com"
    
    providers_to_test = ['openrouter', 'groq', 'replicate']
    results = {}
    
    for provider in providers_to_test:
        print(f"\n🧪 Тестирование {provider}...")
        
        # Принудительно устанавливаем провайдера
        extractor.current_provider = provider
        
        try:
            start_time = time.time()
            result = extractor._make_llm_request_with_retries(
                "Extract contacts from text", 
                test_text, 
                max_retries=1
            )
            end_time = time.time()
            
            if result.get('success'):
                print(f"   ✅ {provider}: Успешно ({end_time - start_time:.2f}с)")
                results[provider] = 'SUCCESS'
            else:
                print(f"   ❌ {provider}: Ошибка - {result.get('error', 'Неизвестная ошибка')}")
                results[provider] = f"ERROR: {result.get('error', 'Unknown')}"
                
        except Exception as e:
            print(f"   💥 {provider}: Исключение - {str(e)}")
            results[provider] = f"EXCEPTION: {str(e)}"
    
    return results

if __name__ == "__main__":
    print(f"🕐 Время начала диагностики: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Основное тестирование
    main_results = test_provider_health()
    
    # Индивидуальное тестирование
    individual_results = test_individual_providers()
    
    print("\n" + "=" * 50)
    print("📋 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    print("\n🔍 Результаты индивидуального тестирования:")
    for provider, result in individual_results.items():
        status_emoji = "✅" if "SUCCESS" in result else "❌"
        print(f"   {status_emoji} {provider}: {result}")
    
    print(f"\n🕐 Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🎯 Диагностика завершена!")