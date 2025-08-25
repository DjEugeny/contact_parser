#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тестирование реального извлечения контактов с Replicate API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm_extractor import ContactExtractor
import json

def test_real_extraction():
    """Тестирование реального извлечения контактов"""
    print("🧪 Тестирование реального извлечения контактов")
    print("=" * 50)
    
    # Создаем экстрактор БЕЗ тестового режима
    extractor = ContactExtractor(test_mode=False)
    
    # Тестовый текст письма
    test_email = """
    Добрый день!
    
    Меня зовут Иван Петров, я директор по развитию в компании "ТехноСфера".
    Хотел бы обсудить возможности сотрудничества.
    
    Мои контакты:
    Email: ivan.petrov@technosphere.ru
    Телефон: +7 (495) 123-45-67
    
    С уважением,
    Иван Петров
    Директор по развитию
    ООО "ТехноСфера"
    г. Москва
    """
    
    try:
        print("📧 Тестовое письмо:")
        print(test_email[:200] + "...")
        print()
        
        print("🔍 Извлечение контактов...")
        result = extractor.extract_contacts(test_email)
        
        print("\n✅ Результат извлечения:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        print("\n📈 Статистика:")
        stats = extractor.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        
        print("\n🏥 Здоровье провайдеров:")
        health = extractor.get_provider_health()
        print(json.dumps(health, ensure_ascii=False, indent=2))
        
        # Проверяем успешность
        if result.get('contacts') and len(result['contacts']) > 0:
            print("\n🎉 ТЕСТ УСПЕШЕН: Контакты извлечены!")
            return True
        else:
            print("\n❌ ТЕСТ НЕУСПЕШЕН: Контакты не найдены")
            return False
            
    except Exception as e:
        print(f"\n❌ ОШИБКА ТЕСТА: {e}")
        
        # Показываем статистику даже при ошибке
        try:
            stats = extractor.get_stats()
            print("\n📈 Статистика (при ошибке):")
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        except:
            pass
            
        return False

if __name__ == "__main__":
    success = test_real_extraction()
    exit(0 if success else 1)