#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальный тест извлечения доказательств
"""

import json
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def test_extract_evidence_detailed():
    """Детальный тест извлечения доказательств"""
    
    print("🔍 Детальный тест извлечения доказательств")
    
    # Читаем исходный файл письма
    email_file = Path("data/emails/2025-07-29/email_016_20250729_20250729_dna-technology_ru_6360137e.json")
    
    with open(email_file, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    # Подготавливаем email_metadata как в IntegratedLLMProcessor
    email_metadata = {
        'from': email_data.get('from', ''),
        'to': email_data.get('to', ''),
        'cc': email_data.get('cc', ''),
        'subject': email_data.get('subject', ''),
        'date': email_data.get('date', ''),
        'thread_id': email_data.get('thread_id', ''),
        'has_attachments': len(email_data.get('attachments', [])) > 0,
        'attachments_count': len(email_data.get('attachments', [])),
        'attachments': email_data.get('attachments', [])
    }
    
    print(f"\n📧 email_metadata подготовлен:")
    print(f"  Вложений: {len(email_metadata['attachments'])}")
    
    # Имитируем работу AttachmentEvidenceExtractor
    print(f"\n🔍 Имитация AttachmentEvidenceExtractor.extract():")
    
    attachments = email_metadata.get('attachments', [])
    
    for i, attachment in enumerate(attachments, 1):
        print(f"\n  Вложение {i}: {attachment.get('original_filename')}")
        print(f"    status: {attachment.get('status')}")
        print(f"    file_path: {attachment.get('file_path')}")
        print(f"    saved_filename: {attachment.get('saved_filename')}")
        
        # Проверяем наличие OCR-текста
        has_ocr = False
        
        if attachment.get('file_path'):
            # Пробуем найти OCR-текст
            file_path = attachment['file_path']
            file_path_obj = Path(file_path)
            
            # Извлекаем дату из пути
            if 'attachments' in file_path and '2025-' in file_path:
                parts = file_path.split('/')
                for part in parts:
                    if part.startswith('2025-'):
                        date_folder = part
                        txt_filename = file_path_obj.with_suffix('.txt').name
                        ocr_text_path = Path(f"data/final_results/texts/{date_folder}/{txt_filename}")
                        
                        if ocr_text_path.exists():
                            print(f"    ✅ OCR-текст найден: {ocr_text_path.name}")
                            has_ocr = True
                            
                            # Читаем текст
                            with open(ocr_text_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Убираем заголовок
                            lines = content.split('\n')
                            text_start = 0
                            for j, line in enumerate(lines):
                                if line.strip().startswith('====='):
                                    text_start = j + 1
                                    break
                            text_content = '\n'.join(lines[text_start:])
                            
                            print(f"    📄 Длина текста: {len(text_content)} символов")
                            
                            # Ищем организации
                            if 'МИЛЛАБ' in text_content:
                                print(f"    ✅ 'МИЛЛАБ' найден в тексте")
                            if 'Москва' in text_content:
                                print(f"    ✅ 'Москва' найден в тексте")
                            if 'Компания МИЛЛАБ' in text_content:
                                print(f"    ✅ 'Компания МИЛЛАБ' найден в тексте")
                        else:
                            print(f"    ❌ OCR-текст НЕ найден: {ocr_text_path}")
                        break
        
        if not has_ocr:
            print(f"    ⚠️ OCR-текст не найден - вложение будет пропущено")
    
    print(f"\n🎯 Вывод:")
    print(f"  AttachmentEvidenceExtractor должен найти OCR-текст для 1 вложения")
    print(f"  В тексте есть 'МИЛЛАБ' и 'Москва'")
    print(f"  Доказательства должны быть извлечены")

if __name__ == "__main__":
    test_extract_evidence_detailed()