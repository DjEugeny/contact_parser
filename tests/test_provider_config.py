#!/usr/bin/env python3
"""
Тестирование динамической конфигурации LLM-провайдеров
Проверка работы с тремя провайдерами: OpenRouter, Groq, Replicate
"""

import sys
import os
import json
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import Config
from llm_extractor import ContactExtractor

def test_provider_config():
    """Тестирование загрузки конфигурации провайдеров"""
    print("🧪 Тестирование динамической конфигурации провайдеров...")
    
    # Тест 1: Загрузка конфигурации
    try:
        config = Config()
        print("✅ Конфигурация загружена успешно")
        
        # Проверяем наличие всех провайдеров
        expected_providers = ['openrouter', 'groq', 'replicate']
        actual_providers = config.provider_order
        
        print(f"📋 Ожидаемые провайдеры: {expected_providers}")
        print(f"📋 Фактические провайдеры: {actual_providers}")
        
        if all(p in actual_providers for p in expected_providers):
            print("✅ Все провайдеры присутствуют в конфигурации")
        else:
            print("❌ Некоторые провайдеры отсутствуют")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False
    
    # Тест 2: Инициализация LLMExtractor
    try:
        # В тестовом режиме не требуем API ключи
        extractor = ContactExtractor(test_mode=True)
        print("✅ ContactExtractor инициализирован успешно")
        
        # Проверяем состояния провайдеров
        if hasattr(extractor, 'provider_states'):
            print(f"📊 Состояния провайдеров: {extractor.provider_states}")
            
            # Проверяем наличие всех провайдеров в состояниях
            for provider in expected_providers:
                if provider in extractor.provider_states:
                    print(f"✅ Провайдер '{provider}' найден в состояниях")
                else:
                    print(f"❌ Провайдер '{provider}' отсутствует в состояниях")
                    return False
        else:
            print("❌ Отсутствует provider_states в LLMExtractor")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка инициализации LLMExtractor: {e}")
        return False
    
    # Тест 3: Проверка настроек провайдеров
    try:
        provider_settings = config.provider_settings
        print(f"⚙️ Настройки провайдеров: {provider_settings}")
        
        # Проверяем наличие настроек для каждого провайдера
        for provider in expected_providers:
            if provider in provider_settings:
                settings = provider_settings[provider]
                print(f"✅ Настройки для {provider}: priority={settings.get('priority')}, max_failures={settings.get('max_failures_before_skip')}")
            else:
                print(f"❌ Настройки для {provider} отсутствуют")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка проверки настроек: {e}")
        return False
    
    print("🎉 Все тесты пройдены успешно!")
    return True

def test_providers_json_structure():
    """Проверка структуры файла providers.json"""
    print("\n📁 Проверка структуры providers.json...")
    
    config_path = Path(__file__).parent / 'config' / 'providers.json'
    
    if not config_path.exists():
        print(f"❌ Файл {config_path} не найден")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_keys = ['provider_order', 'provider_settings']
        for key in required_keys:
            if key not in config:
                print(f"❌ Отсутствует ключ '{key}' в providers.json")
                return False
        
        print("✅ Структура providers.json корректна")
        print(f"📋 Провайдеры: {config['provider_order']}")
        print(f"📋 Настройки: {list(config['provider_settings'].keys())}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ДИНАМИЧЕСКОЙ КОНФИГУРАЦИИ ПРОВАЙДЕРОВ")
    print("=" * 60)
    
    success = True
    
    # Тест 1: Проверка JSON структуры
    if not test_providers_json_structure():
        success = False
    
    # Тест 2: Проверка конфигурации и инициализации
    if not test_provider_config():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
    print("=" * 60)