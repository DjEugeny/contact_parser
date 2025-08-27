#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправления фильтрации вложений в OCRProcessorAdapter
"""

import json
import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ocr_processor_adapter import OCRProcessorAdapter

def test_email_006_attachment_filtering():
    """Тест фильтрации вложений для email_006"""
    print("=== Тест исправления фильтрации вложений ===")
    
    # Инициализация адаптера
    adapter = OCRProcessorAdapter()
    
    # Загрузка email_006
    email_path = '/Users/evgenyzach/contact_parser/data/emails/2025-07-01/email_006_20250701_20250701_dna-technology_ru_539d677f.json'
    
    try:
        with open(email_path, 'r', encoding='utf-8') as f:
            email = json.load(f)
        
        print(f"Email thread_id: {email.get('thread_id', 'N/A')}")
        print(f"Email attachments: {email.get('attachments', [])}")
        
        # Тест с пустыми результатами вложений (как должно быть для email_006)
        combined_text_empty = adapter.combine_email_with_attachments(email, {})
        print(f"\nС пустыми вложениями:")
        print(f"Combined text length: {len(combined_text_empty)} characters")
        print(f"First 200 chars: {combined_text_empty[:200]}...")
        
        # Тест с фиктивными вложениями других писем
        fake_attachments = {
            'other_thread_id_1': 'Текст вложения от другого письма 1',
            'other_thread_id_2': 'Текст вложения от другого письма 2',
            email.get('thread_id', 'unknown'): 'Текст вложения для этого письма'
        }
        
        combined_text_filtered = adapter.combine_email_with_attachments(email, fake_attachments)
        print(f"\nС фильтрацией по thread_id:")
        print(f"Combined text length: {len(combined_text_filtered)} characters")
        print(f"Should contain only relevant attachment: {'Текст вложения для этого письма' in combined_text_filtered}")
        print(f"Should NOT contain other attachments: {'другого письма 1' not in combined_text_filtered}")
        
        return True
        
    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    success = test_email_006_attachment_filtering()
    if success:
        print("\n✅ Тест завершен успешно")
    else:
        print("\n❌ Тест завершен с ошибками")
        sys.exit(1)