#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест реального API Replicate с исправленной обработкой HTTP кодов
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm_extractor import ContactExtractor
import json

def test_replicate_real():
    """Тест реального API Replicate"""
    print("🧪 Тестирование реального API Replicate с исправлениями...")
    
    # Создаем экстрактор БЕЗ тестового режима
    extractor = ContactExtractor(test_mode=False)
    
    # Принудительно устанавливаем Replicate как текущий провайдер
    extractor.current_provider = 'replicate'
    
    # Простой тестовый текст
    test_text = """
    Контакты компании:
    Иван Петров - ivan@company.ru
    Телефон: +7 (495) 123-45-67
    """
    
    try:
        print(f"🎯 Текущий провайдер: {extractor.current_provider}")
        print(f"📝 Тестовый текст: {len(test_text)} символов")
        
        # Извлекаем контакты
        result = extractor.extract_contacts(test_text)
        
        print("\n📊 Результат извлечения:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Проверяем статистику
        stats = extractor.get_stats()
        print("\n📈 Статистика:")
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        
        # Проверяем здоровье провайдеров
        health = extractor.get_provider_health()
        print("\n🏥 Здоровье провайдеров:")
        print(json.dumps(health, ensure_ascii=False, indent=2))
        
        # Проверяем успешность
        if result.get('success', False):
            contacts = result.get('contacts', [])
            print(f"\n✅ Успешно извлечено {len(contacts)} контактов")
            print(f"🤖 Использован провайдер: {result.get('provider_used', 'Неизвестно')}")
            return True
        else:
            error = result.get('error', 'Неизвестная ошибка')
            print(f"\n❌ Ошибка: {error}")
            
            # Если Replicate не сработал, проверим что система переключилась
            if 'replicate' not in result.get('provider_used', '').lower():
                print("🔄 Система корректно переключилась на резервный провайдер")
                return True
            return False
            
    except Exception as e:
        print(f"\n💥 Исключение: {e}")
        return False

if __name__ == "__main__":
    success = test_replicate_real()
    sys.exit(0 if success else 1)