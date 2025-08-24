#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест улучшенного промпта для извлечения контактов
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from llm_extractor import ContactExtractor

def test_prompt_optimization():
    """Тест работы улучшенного промпта"""
    print("🧪 ТЕСТ УЛУЧШЕННОГО ПРОМПТА")
    print("=" * 50)
    
    # Создаем экстрактор контактов в реальном режиме для проверки промпта
    extractor = ContactExtractor(test_mode=False)
    
    # Тестовый текст с контактами
    test_text = """
    Добрый день!
    
    Меня зовут Иван Петров, я представляю компанию ООО "Тест Лаб".
    Наш адрес: г. Москва, ул. Тестовая, д. 123, офис 456
    Телефон: +7 (495) 123-45-67
    Email: ivan.petrov@testlab.ru
    Сайт: www.testlab.ru
    
    С уважением,
    Иван Петров
    Директор по развитию
    """
    
    print(f"📝 Тестовый текст ({len(test_text)} символов):")
    print(test_text[:200] + "...")
    print()
    
    try:
        print("🤖 Отправка в LLM...")
        result = extractor.extract_contacts(test_text, {"subject": "Тестовое письмо"})
        
        print("✅ Результат получен:")
        print(f"Тип результата: {type(result)}")
        print(f"Содержимое: {result}")
        
        # Проверяем, что результат - это словарь (JSON)
        if isinstance(result, dict):
            print("\n✅ УСПЕХ: Получен корректный JSON")
            if 'contacts' in result:
                print(f"📞 Найдено контактов: {len(result['contacts'])}")
                for i, contact in enumerate(result['contacts'], 1):
                    print(f"  {i}. {contact}")
            else:
                print("⚠️ Поле 'contacts' не найдено в результате")
        else:
            print(f"❌ ОШИБКА: Результат не является JSON, тип: {type(result)}")
            
    except Exception as e:
        print(f"❌ ОШИБКА при обработке: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_prompt_optimization()