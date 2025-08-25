#!/usr/bin/env python3
"""
🧪 Комплексное тестирование стабильности провайдеров после улучшений
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock

# Добавляем путь к src в PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm_extractor import ContactExtractor
from integrated_llm_processor import IntegratedLLMProcessor

def test_provider_stability():
    """
    🎯 Тест стабильности работы всех провайдеров
    """
    print("🧪 Комплексное тестирование стабильности провайдеров...")
    
    # Устанавливаем фейковые API ключи
    os.environ['OPENROUTER_API_KEY'] = 'test-key-123'
    os.environ['GROQ_API_KEY'] = 'test-key-456'
    os.environ['REPLICATE_API_KEY'] = 'test-key-789'
    
    try:
        # Тест 1: Инициализация всех провайдеров
        print("\n1️⃣ Тест: Инициализация провайдеров")
        extractor = ContactExtractor(test_mode=True)
        assert extractor is not None, "ContactExtractor должен инициализироваться"
        print("   ✅ ContactExtractor успешно инициализирован")
        
        # Тест 2: Проверка конфигурации провайдеров
        print("\n2️⃣ Тест: Конфигурация провайдеров")
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'providers.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        provider_order = config.get('provider_order', [])
        provider_settings = config.get('provider_settings', {})
        
        assert len(provider_order) >= 3, "Должно быть минимум 3 провайдера в порядке"
        expected_names = ['replicate', 'groq', 'openrouter']
        for name in expected_names:
            assert name in provider_settings, f"Провайдер {name} должен быть в конфигурации"
        print("   ✅ Все провайдеры присутствуют в конфигурации")
        
        # Тест 3: Проверка приоритетов
        print("\n3️⃣ Тест: Приоритеты провайдеров")
        priorities = [settings['priority'] for settings in provider_settings.values()]
        assert len(set(priorities)) == len(priorities), "Приоритеты должны быть уникальными"
        print("   ✅ Приоритеты провайдеров корректно настроены")
        
        # Тест 4: Проверка работы системы провайдеров
        print("\n4️⃣ Тест: Система провайдеров")
        processor = IntegratedLLMProcessor(test_mode=True)
        
        # Проверяем что система инициализировалась
        assert processor.contact_extractor is not None, "ContactExtractor должен быть инициализирован"
        print("   ✅ Система провайдеров инициализирована")
        
        # Тест 6: Тестовый режим работает корректно
        print("\n6️⃣ Тест: Тестовый режим")
        # Проверяем что test_mode корректно передан в ContactExtractor
        assert processor.contact_extractor.test_mode == True, "test_mode должен быть установлен"
        print("   ✅ Тестовый режим работает корректно")
        
        print("\n🎉 Все тесты стабильности провайдеров пройдены успешно!")
        
    finally:
        # Очищаем временные переменные окружения
        for key in ['OPENROUTER_API_KEY', 'GROQ_API_KEY', 'REPLICATE_API_KEY']:
            if key in os.environ:
                del os.environ[key]

if __name__ == "__main__":
    test_provider_stability()