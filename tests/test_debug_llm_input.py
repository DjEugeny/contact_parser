#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладочный тест для проверки входных данных LLM
Проверяем, что именно передается в LLM и почему он не находит ИНН и сайты
"""

import json
import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.integrated_llm_processor import IntegratedLLMProcessor

def test_debug_llm_input():
    """Отладочный тест для проверки входных данных LLM"""
    print("🔍 ОТЛАДОЧНЫЙ ТЕСТ LLM ВХОДНЫХ ДАННЫХ")
    print("=" * 60)
    
    # Инициализация процессора БЕЗ тестового режима
    processor = IntegratedLLMProcessor(test_mode=False)  # ОТКЛЮЧАЕМ тестовый режим для реального LLM
    print(f"✅ Процессор инициализирован: {type(processor).__name__}")
    
    # Загружаем тестовый файл с известными ИНН и сайтом
    test_file = "/Users/evgenyzach/contact_parser/data/emails/2025-07-29/email_025_20250729_20250729_dna-technology_ru_4aee22c5.json"
    
    with open(test_file, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    print(f"📄 Загружен файл: {os.path.basename(test_file)}")
    print(f"📝 Длина body: {len(email_data['body'])} символов")
    
    # Показываем фрагмент с ИНН и сайтом
    body = email_data['body']
    inn_pos = body.find('1901066506')
    site_pos = body.find('https://fgis.gost.ru/')
    
    print(f"\n🔍 ПОИСК В ИСХОДНОМ ТЕКСТЕ:")
    print(f"ИНН 1901066506 найден на позиции: {inn_pos}")
    print(f"Сайт https://fgis.gost.ru/ найден на позиции: {site_pos}")
    
    if inn_pos >= 0:
        print(f"\n📍 КОНТЕКСТ ИНН:")
        start = max(0, inn_pos - 100)
        end = min(len(body), inn_pos + 100)
        print(f"\"{body[start:end]}\"")
    
    if site_pos >= 0:
        print(f"\n🌐 КОНТЕКСТ САЙТА:")
        start = max(0, site_pos - 50)
        end = min(len(body), site_pos + 100)
        print(f"\"{body[start:end]}\"")
    
    # Теперь проверим, что передается в LLM
    print(f"\n🤖 ТЕСТИРУЕМ ОБРАБОТКУ LLM...")
    
    # Создаем временный метод для перехвата данных, передаваемых в LLM
    original_extract = processor.contact_extractor.extract_all_data
    
    def debug_extract_all_data(text, metadata=None, *args, **kwargs):
        print(f"\n📤 ДАННЫЕ, ПЕРЕДАВАЕМЫЕ В LLM:")
        print(f"Длина текста: {len(text)} символов")
        print(f"\n🔍 ПОИСК В LLM-ТЕКСТЕ:")
        inn_in_llm = text.find('1901066506')
        site_in_llm = text.find('https://fgis.gost.ru/')
        print(f"ИНН 1901066506 в LLM-тексте: {inn_in_llm >= 0} (позиция: {inn_in_llm})")
        print(f"Сайт https://fgis.gost.ru/ в LLM-тексте: {site_in_llm >= 0} (позиция: {site_in_llm})")
        
        if inn_in_llm >= 0:
            start = max(0, inn_in_llm - 50)
            end = min(len(text), inn_in_llm + 50)
            print(f"\n📍 КОНТЕКСТ ИНН В LLM-ТЕКСТЕ:")
            print(f"\"{text[start:end]}\"")
        
        if site_in_llm >= 0:
            start = max(0, site_in_llm - 50)
            end = min(len(text), site_in_llm + 50)
            print(f"\n🌐 КОНТЕКСТ САЙТА В LLM-ТЕКСТЕ:")
            print(f"\"{text[start:end]}\"")
        
        # Показываем первые 500 символов LLM-текста
        print(f"\n📝 ПЕРВЫЕ 500 СИМВОЛОВ LLM-ТЕКСТА:")
        print(f"\"{text[:500]}...\"")
        
        # Вызываем оригинальный метод
        return original_extract(text, metadata, *args, **kwargs)
    
    processor.contact_extractor.extract_all_data = debug_extract_all_data
    
    # Обрабатываем файл
    try:
        result = processor.process_single_email(email_data)
        
        print(f"\n📊 РЕЗУЛЬТАТ ОБРАБОТКИ:")
        print(f"Найдено контактов: {len(result.get('contacts', []))}")
        
        # Проверяем ИНН и сайты в результате
        has_inn = False
        has_website = False
        
        for contact in result.get('contacts', []):
            if contact.get('inn'):
                has_inn = True
                print(f"✅ Найден ИНН: {contact['inn']}")
            if contact.get('website'):
                has_website = True
                print(f"✅ Найден сайт: {contact['website']}")
        
        print(f"\n🎯 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"ИНН найден: {has_inn}")
        print(f"Сайт найден: {has_website}")
        
        if not has_inn:
            print("❌ ИНН НЕ НАЙДЕН - проблема в обработке LLM")
        if not has_website:
            print("❌ САЙТ НЕ НАЙДЕН - проблема в обработке LLM")
            
    except Exception as e:
        print(f"❌ Ошибка при обработке: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Отладочный тест завершен")

if __name__ == "__main__":
    test_debug_llm_input()