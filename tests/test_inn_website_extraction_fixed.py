#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест извлечения ИНН и сайтов после исправления критического бага
Проверяет работу нового ContactExtractor из core/extractor.py
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.integrated_llm_processor import IntegratedLLMProcessor

def test_inn_website_extraction_after_fix():
    """🔍 Тест извлечения ИНН и сайтов после исправления бага"""
    
    print("🧪 ТЕСТ ИЗВЛЕЧЕНИЯ ИНН И САЙТОВ ПОСЛЕ ИСПРАВЛЕНИЯ БАГА")
    print("=" * 60)
    
    # Инициализация процессора с тестовым режимом
    processor = IntegratedLLMProcessor(test_mode=True)
    
    # Тестовый текст с ИНН и сайтом
    test_text = """
    Добрый день!
    
    Меня зовут Иван Петров, я работаю в компании "ТехноЛаб" на должности менеджера по продажам.
    Мой email: ivan.petrov@technolab.ru, телефон: +7 (495) 123-45-67.
    ИНН нашей компании: 1901066506
    Наш сайт: https://technolab.ru
    
    Хотел бы обсудить возможность сотрудничества.
    
    С уважением,
    Иван Петров
    ООО "ТехноЛаб"
    г. Москва
    """
    
    print("📝 Тестовый текст:")
    print(test_text)
    print("\n" + "-" * 50)
    
    try:
        # Извлечение контактов
        result = processor.contact_extractor.extract_all_data(test_text)
        
        print("✅ Результат извлечения:")
        print(f"Всего контактов: {len(result.get('contacts', []))}")
        
        # Проверка извлечения ИНН и сайтов
        inn_found = 0
        website_found = 0
        
        for contact in result.get('contacts', []):
            print(f"\n📞 Контакт: {contact.get('name', 'Не указано')}")
            print(f"   Организация: {contact.get('organization', 'Не указано')}")
            print(f"   Телефон: {contact.get('phone', 'Не указано')}")
            print(f"   Email: {contact.get('email', 'Не указано')}")
            
            # Проверяем ИНН
            inn = contact.get('inn')
            if inn:
                print(f"   ✅ ИНН: {inn}")
                inn_found += 1
            else:
                print(f"   ❌ ИНН: не найден")
            
            # Проверяем сайт
            website = contact.get('website')
            if website:
                print(f"   ✅ Сайт: {website}")
                website_found += 1
            else:
                print(f"   ❌ Сайт: не найден")
        
        print("\n" + "=" * 50)
        print("📊 СТАТИСТИКА ИЗВЛЕЧЕНИЯ:")
        print(f"ИНН найдено: {inn_found}")
        print(f"Сайтов найдено: {website_found}")
        
        # Проверяем эффективность
        if inn_found > 0:
            print("✅ ИНН успешно извлекается!")
        else:
            print("❌ ИНН не извлекается")
            
        if website_found > 0:
            print("✅ Сайты успешно извлекаются!")
        else:
            print("❌ Сайты не извлекаются")
            
        return {
            'inn_found': inn_found,
            'website_found': website_found,
            'total_contacts': len(result.get('contacts', [])),
            'result': result
        }
        
    except Exception as e:
        print(f"❌ Ошибка при извлечении: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_inn_website_extraction_after_fix()