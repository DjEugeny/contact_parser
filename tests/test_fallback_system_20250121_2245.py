#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест системы fallback с тремя провайдерами
Дата создания: 2025-01-21 22:45 (UTC+07)
"""

import sys
import os
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm_extractor import ContactExtractor
import json

def test_provider_configuration():
    """Тест конфигурации провайдеров"""
    print("\n🔧 Тестирование конфигурации провайдеров...")
    
    extractor = ContactExtractor(test_mode=True)
    
    # Проверяем, что все три провайдера загружены
    providers = extractor.providers
    print(f"📋 Загружено провайдеров: {len(providers)}")
    
    expected_providers = ['openrouter', 'groq', 'replicate']
    for provider_id in expected_providers:
        if provider_id in providers:
            provider = providers[provider_id]
            print(f"✅ {provider['name']} (приоритет: {provider['priority']})")
        else:
            print(f"❌ Провайдер {provider_id} не найден")
    
    return len(providers) >= 3

def test_provider_fallback_simulation():
    """Тест симуляции fallback между провайдерами"""
    print("\n🔄 Тестирование fallback системы...")
    
    extractor = ContactExtractor(test_mode=True)
    
    # Получаем начальное состояние
    initial_provider = extractor._get_first_active_provider()
    print(f"🎯 Начальный провайдер: {initial_provider}")
    
    # Симулируем отказ текущего провайдера
    failure_result = extractor.simulate_provider_failure(initial_provider)
    print(f"💥 Симуляция отказа: {failure_result['message']}")
    
    # Проверяем переключение на следующий провайдер
    switch_result = extractor._switch_to_next_provider()
    if switch_result:
        new_provider = extractor._get_first_active_provider()
        print(f"🔄 Переключение на: {new_provider}")
    else:
        print("❌ Не удалось переключиться на следующий провайдер")
    
    return switch_result

def test_provider_health_check():
    """Тест проверки здоровья провайдеров"""
    print("\n🏥 Проверка здоровья провайдеров...")
    
    extractor = ContactExtractor(test_mode=True)
    health = extractor.get_provider_health()
    
    print("📊 Состояние провайдеров:")
    for provider_id, status in health['providers'].items():
        status_icon = "✅" if status['active'] else "❌"
        print(f"  {status_icon} {provider_id}: {status['status']} (ошибок: {status['failure_count']})")
    
    print(f"🏥 Общее здоровье системы: {health['system_health']}")
    if health['recommendations']:
        print("💡 Рекомендации:")
        for rec in health['recommendations']:
            print(f"  - {rec}")
    
    return health

def test_configuration_file():
    """Тест загрузки конфигурационного файла"""
    print("\n📄 Тестирование конфигурационного файла...")
    
    config_path = Path(__file__).parent.parent / "config" / "providers.json"
    
    if config_path.exists():
        print(f"✅ Конфигурационный файл найден: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"📋 Провайдеров в конфигурации: {len(config.get('providers', {}))}")
        print(f"🔄 Максимум попыток: {config.get('fallback_settings', {}).get('max_retries', 'не указано')}")
        
        return True
    else:
        print(f"❌ Конфигурационный файл не найден: {config_path}")
        return False

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование системы fallback с тремя провайдерами")
    print("=" * 60)
    
    tests = [
        ("Конфигурация провайдеров", test_provider_configuration),
        ("Конфигурационный файл", test_configuration_file),
        ("Проверка здоровья", test_provider_health_check),
        ("Fallback система", test_provider_fallback_simulation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 Запуск теста: {test_name}")
            result = test_func()
            results.append((test_name, "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"))
        except Exception as e:
            print(f"💥 Ошибка в тесте {test_name}: {e}")
            results.append((test_name, f"💥 ОШИБКА: {e}"))
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    for test_name, status in results:
        print(f"  {status} {test_name}")
    
    print(f"\n⏰ Тестирование завершено: 2025-01-21 22:45 (UTC+07)")

if __name__ == "__main__":
    main()