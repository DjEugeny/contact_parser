#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.extractor import ContactExtractor
from src.integrated_llm_processor import IntegratedLLMProcessor as LLMProcessor
import json

def debug_llm_extraction():
    print("🔍 ОТЛАДКА LLM ИЗВЛЕЧЕНИЯ ИНН И САЙТОВ")
    print("="*60)
    
    # Путь к файлу с ИНН и сайтом
    test_file = "/Users/evgenyzach/contact_parser/data/final_results/texts/2025-07-29/20250729_dna-technology_ru_6360137e_084824_attach_Ком.пред.29.07.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_ Дтпрайм II 6М6_.txt"
    
    # Читаем содержимое файла
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 Файл: {os.path.basename(test_file)}")
    print(f"📏 Размер: {len(content)} символов")
    
    # Показываем фрагмент с ИНН и сайтом
    lines = content.split('\n')
    for i, line in enumerate(lines[:20], 1):
        if 'ИНН' in line or 'www' in line or '@' in line:
            print(f"🎯 Строка {i}: {line.strip()}")
    
    print("\n" + "="*60)
    print("🤖 ТЕСТИРОВАНИЕ LLM ИЗВЛЕЧЕНИЯ")
    
    # Инициализируем LLM процессор БЕЗ тестового режима
    llm_processor = LLMProcessor(test_mode=False)
    
    # Инициализируем обогатитель контактов
    from src.core.contact_enricher import ContactEnricher
    enricher = ContactEnricher()
    
    # Инициализируем экстрактор через фабрику
    from src.core.extractor_factory import ExtractorFactory
    extractor = ExtractorFactory.create_extractor()
    
    print("\n1️⃣ Базовое извлечение контактов...")
    base_contacts = extractor.extract_contacts(content)
    print(f"   Тип результата: {type(base_contacts)}")
    print(f"   Содержимое: {base_contacts}")
    
    # Проверяем структуру данных
    if isinstance(base_contacts, dict):
        contacts_list = base_contacts.get('contacts', [])
        print(f"   Найдено контактов в словаре: {len(contacts_list)}")
        for i, contact in enumerate(contacts_list[:3], 1):
            if isinstance(contact, dict):
                print(f"   {i}. {contact.get('name', 'N/A')} - {contact.get('email', 'N/A')}")
            else:
                print(f"   {i}. {str(contact)[:100]}...")
    elif isinstance(base_contacts, list):
        print(f"   Найдено контактов в списке: {len(base_contacts)}")
        for i, contact in enumerate(base_contacts[:3], 1):
            if isinstance(contact, dict):
                print(f"   {i}. {contact.get('name', 'N/A')} - {contact.get('email', 'N/A')}")
            else:
                print(f"   {i}. {str(contact)[:100]}...")
    else:
        print(f"   Неожиданный тип данных: {type(base_contacts)}")
    
    print("\n2️⃣ LLM обогащение контактов...")
    if isinstance(base_contacts, dict) and 'contacts' in base_contacts:
        contacts_list = base_contacts['contacts']
        if contacts_list:
            # Берем первый контакт для тестирования
            test_contact = contacts_list[0].copy()
            print(f"   Тестируем контакт: {test_contact.get('name', 'N/A')}")
            
            # Обогащаем через ContactEnricher
            enriched_contact = enricher._enrich_single_contact(test_contact, {'body': content})
            
            print("\n📊 РЕЗУЛЬТАТ ОБОГАЩЕНИЯ:")
            print(f"   ИНН до: {test_contact.get('inn', 'не найден')}")
            print(f"   ИНН после: {enriched_contact.get('inn', 'не найден')}")
            print(f"   Сайт до: {test_contact.get('website', 'не найден')}")
            print(f"   Сайт после: {enriched_contact.get('website', 'не найден')}")
            
            # Показываем все изменения
            print("\n🔄 ВСЕ ИЗМЕНЕНИЯ:")
            for key in enriched_contact:
                if enriched_contact[key] != test_contact.get(key):
                    print(f"   {key}: '{test_contact.get(key, 'N/A')}' → '{enriched_contact[key]}'")
        else:
            print("   ❌ Список контактов пуст")
    else:
        print("   ❌ Нет базовых контактов для обогащения")

if __name__ == "__main__":
    debug_llm_extraction()