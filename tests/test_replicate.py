#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест работы с Replicate API через новую архитектуру
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.config_manager import UnifiedConfigManager
from src.core.extractor_factory import ExtractorFactory

def test_replicate_api():
    """🧪 Тестирование Replicate API"""
    print("🧪 Тестирование Replicate API...")
    
    # Инициализация конфигурации
    config = UnifiedConfigManager()
    
    # Проверяем что провайдеры инициализированы
    print(f"🔧 Инициализированные провайдеры: {list(config.providers.keys())}")
    
    # Создаем экстрактор через фабрику
    extractor = ExtractorFactory.create_extractor(test_mode=False)
    
    # Тестовый текст
    test_text = """
    Компания: ООО "Тестовая Компания"
    Контактное лицо: Иван Петров
    Телефон: +7 (495) 123-45-67
    Email: ivan.petrov@test.com
    Адрес: Москва, ул. Тестовая, д. 1
    """
    
    try:
        print("📤 Отправляем запрос к Replicate API...")
        result = extractor.extract_all_data(test_text)
        
        print("✅ Результат получен:")
        print(f"📊 Найдено организаций: {len(result.get('organizations', []))}")
        print(f"👥 Найдено контактов: {len(result.get('contacts', []))}")
        
        if result.get('organizations'):
            org = result['organizations'][0]
            print(f"🏢 Первая организация: {org.get('name', 'N/A')}")
            
        if result.get('contacts'):
            contact = result['contacts'][0]
            print(f"👤 Первый контакт: {contact.get('name', 'N/A')}")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_replicate_api()
    if success:
        print("\n🎉 Тест успешно завершен!")
    else:
        print("\n💥 Тест завершился с ошибкой!")
        sys.exit(1)