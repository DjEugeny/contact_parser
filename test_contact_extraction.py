#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест извлечения контактов с исправленной обработкой Replicate API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm_extractor import ContactExtractor
import json

def test_contact_extraction():
    """Тест извлечения контактов"""
    print("🧪 Тестирование извлечения контактов с исправленным Replicate API...")
    
    # Создаем экстрактор в тестовом режиме
    extractor = ContactExtractor(test_mode=True)
    
    # Тестовый текст с контактами
    test_text = """
    Добро пожаловать в нашу компанию ООО "Технологии Будущего"!
    
    Наши контакты:
    Директор: Иван Петров
    Email: ivan.petrov@techfuture.ru
    Телефон: +7 (495) 123-45-67
    
    Менеджер по продажам: Анна Сидорова
    Email: anna.sidorova@techfuture.ru
    Мобильный: +7 (926) 987-65-43
    
    Офис: г. Москва, ул. Тверская, д. 10, офис 205
    Сайт: www.techfuture.ru
    """
    
    try:
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
            return True
        else:
            print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            return False
            
    except Exception as e:
        print(f"\n💥 Исключение: {e}")
        return False

if __name__ == "__main__":
    success = test_contact_extraction()
    sys.exit(0 if success else 1)