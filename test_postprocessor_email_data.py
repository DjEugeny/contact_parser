#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест передачи email_data в PostProcessor
"""

import json
from pathlib import Path

def test_postprocessor_email_data():
    """Тест передачи email_data в PostProcessor"""
    
    print("🔍 Проверка передачи email_data в PostProcessor")
    
    # Читаем исходный файл письма
    email_file = Path("data/emails/2025-07-29/email_016_20250729_20250729_dna-technology_ru_6360137e.json")
    
    if not email_file.exists():
        print(f"❌ Файл письма не найден: {email_file}")
        return
    
    with open(email_file, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    print(f"\n📧 Исходный файл письма:")
    print(f"  Ключи: {list(email_data.keys())}")
    print(f"  Вложений: {len(email_data.get('attachments', []))}")
    
    # Имитируем что делает IntegratedLLMProcessor
    email_metadata = {
        'from': email_data.get('from', ''),
        'to': email_data.get('to', ''),
        'cc': email_data.get('cc', ''),
        'subject': email_data.get('subject', ''),
        'date': email_data.get('date', ''),
        'thread_id': email_data.get('thread_id', ''),
        'has_attachments': len(email_data.get('attachments', [])) > 0,
        'attachments_count': len(email_data.get('attachments', [])),
        'attachments': email_data.get('attachments', [])  # Добавляем полные данные о вложениях
    }
    
    print(f"\n📋 email_metadata (передается в PostProcessor):")
    print(f"  Ключи: {list(email_metadata.keys())}")
    print(f"  has_attachments: {email_metadata['has_attachments']}")
    print(f"  attachments_count: {email_metadata['attachments_count']}")
    print(f"  attachments type: {type(email_metadata['attachments'])}")
    print(f"  attachments length: {len(email_metadata['attachments'])}")
    
    if email_metadata['attachments']:
        print(f"\n📎 Первое вложение:")
        first_att = email_metadata['attachments'][0]
        print(f"  Ключи: {list(first_att.keys())}")
        print(f"  original_filename: {first_att.get('original_filename')}")
        print(f"  saved_filename: {first_att.get('saved_filename')}")
        print(f"  status: {first_att.get('status')}")
    
    # Проверяем, что будет передано в _enrich_organizations_location_from_attachments
    print(f"\n🔍 Проверка условия в _enrich_organizations_location_from_attachments:")
    print(f"  email_data is not None: {email_metadata is not None}")
    print(f"  email_data.get('attachments'): {email_metadata.get('attachments') is not None}")
    print(f"  bool(email_data.get('attachments')): {bool(email_metadata.get('attachments'))}")
    
    if not email_metadata or not email_metadata.get('attachments'):
        print(f"  ❌ Условие НЕ пройдено - метод вернет пустой словарь!")
    else:
        print(f"  ✅ Условие пройдено - метод должен обработать вложения")
    
    # Проверяем, что будет в AttachmentEvidenceExtractor
    print(f"\n🔍 Проверка в AttachmentEvidenceExtractor:")
    attachments = email_metadata.get('attachments', [])
    print(f"  attachments type: {type(attachments)}")
    print(f"  isinstance(attachments, list): {isinstance(attachments, list)}")
    print(f"  len(attachments): {len(attachments) if isinstance(attachments, list) else 'N/A'}")
    
    if not isinstance(attachments, list):
        print(f"  ❌ Attachments не список - вернет пустой список!")
    elif not attachments:
        print(f"  ❌ Attachments пустой - вернет пустой список!")
    else:
        print(f"  ✅ Attachments корректный - должен обработать {len(attachments)} вложений")
    
    print(f"\n🎯 Вывод:")
    print(f"  Данные о вложениях корректно подготовлены для передачи в PostProcessor")
    print(f"  Если обогащение не работает, проблема в другом месте")

if __name__ == "__main__":
    test_postprocessor_email_data()