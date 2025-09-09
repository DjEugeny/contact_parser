#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.integrated_llm_processor import IntegratedLLMProcessor
import json

def check_contacts():
    print("🔍 ПРОВЕРКА ИЗВЛЕЧЕНИЯ ИНН И САЙТОВ")
    print("="*50)
    
    # Инициализируем процессор БЕЗ тестового режима
    processor = IntegratedLLMProcessor(test_mode=False)
    
    # Обрабатываем одно письмо
    result = processor.process_emails_by_date('2025-07-29', max_emails=1)
    
    # Получаем контакты
    contacts = result.get('all_contacts', [])
    print(f"\n📋 НАЙДЕНО КОНТАКТОВ: {len(contacts)}")
    
    inn_count = 0
    website_count = 0
    
    for i, contact in enumerate(contacts, 1):
        print(f"\n{i}. {contact.get('name', 'N/A')}")
        print(f"   Confidence: {contact.get('confidence', 'N/A')}")
        
        if contact.get('inn'):
            print(f"   ✅ ИНН: {contact['inn']}")
            inn_count += 1
        else:
            print(f"   ❌ ИНН: не найден")
            
        if contact.get('websites'):
            print(f"   ✅ Сайты: {contact['websites']}")
            website_count += 1
        else:
            print(f"   ❌ Сайты: не найдены")
            
        # Показываем все поля контакта
        print(f"   📝 Все поля: {list(contact.keys())}")
    
    print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"Всего контактов: {len(contacts)}")
    print(f"Контактов с ИНН: {inn_count}")
    print(f"Контактов с сайтами: {website_count}")
    print(f"Эффективность ИНН: {inn_count/len(contacts)*100:.1f}%" if contacts else "0%")
    print(f"Эффективность сайтов: {website_count/len(contacts)*100:.1f}%" if contacts else "0%")

if __name__ == "__main__":
    check_contacts()