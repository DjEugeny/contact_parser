#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка сохраненных вложений
"""

import json
from pathlib import Path

def test_check_saved_attachments():
    """Проверка сохраненных вложений"""
    
    print("🔍 Проверка сохраненных вложений")
    
    # Читаем исходный файл письма
    email_file = Path("data/emails/2025-07-29/email_016_20250729_20250729_dna-technology_ru_6360137e.json")
    
    with open(email_file, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    attachments = email_data.get('attachments', [])
    
    print(f"\n📎 Всего вложений: {len(attachments)}")
    
    for i, att in enumerate(attachments, 1):
        print(f"\n  Вложение {i}:")
        print(f"    original_filename: {att.get('original_filename')}")
        print(f"    status: {att.get('status')}")
        print(f"    saved_filename: {att.get('saved_filename')}")
        print(f"    file_path: {att.get('file_path')}")
        
        if att.get('status') == 'saved':
            print(f"    ✅ Это сохраненное вложение!")
            
            # Проверяем наличие OCR-текста
            saved_filename = att.get('saved_filename', '')
            if saved_filename:
                # Извлекаем дату из имени файла
                if saved_filename.startswith('202'):
                    date_part = saved_filename[:8]  # 20250729
                    formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"  # 2025-07-29
                    
                    txt_filename = Path(saved_filename).with_suffix('.txt').name
                    ocr_path = Path(f"data/final_results/texts/{formatted_date}/{txt_filename}")
                    
                    if ocr_path.exists():
                        print(f"    ✅ OCR-текст найден: {ocr_path}")
                    else:
                        print(f"    ❌ OCR-текст НЕ найден: {ocr_path}")
    
    # Фильтруем только сохраненные вложения
    saved_attachments = [a for a in attachments if a.get('status') == 'saved']
    print(f"\n📊 Сохраненных вложений: {len(saved_attachments)}")
    
    if saved_attachments:
        print(f"\n🎯 Вывод:")
        print(f"  AttachmentEvidenceExtractor должен обработать {len(saved_attachments)} сохраненных вложений")
        print(f"  Но он получает ВСЕ {len(attachments)} вложений, включая excluded_inline_image")
        print(f"\n💡 Возможная проблема:")
        print(f"  AttachmentEvidenceExtractor пытается обработать ВСЕ вложения,")
        print(f"  но OCR-тексты есть только для вложений со status='saved'")
    else:
        print(f"\n❌ Нет сохраненных вложений!")

if __name__ == "__main__":
    test_check_saved_attachments()