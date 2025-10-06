#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправленной обработки вложений в реальном пайплайне
"""

import sys
import os
import json
from pathlib import Path

# Добавляем путь к src
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

def test_fixed_attachment_processing():
    """Тест исправленной обработки вложений"""
    
    try:
        from postprocessing.attachment_evidence_extractor import AttachmentEvidenceExtractor
        print("✅ AttachmentEvidenceExtractor импортирован успешно")
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return
    
    # Тестовые данные - имитируем реальную структуру из IntegratedLLMProcessor
    email_data_with_attachments = {
        'from': 'm.gogoleva@dna-technology.ru',
        'to': 's.voronova@dna-technology.ru',
        'subject': 'ФБУЗ "Центр Гигиены и Эпидемиологии в Республике Хакасия"',
        'attachments': [
            {
                'original_filename': 'Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ (ДТпрайм 5М6, ноутбук).pdf',
                'saved_filename': '20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.pdf',
                'file_path': 'data/attachments/2025-07-29/20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.pdf',
                'file_type': 'application/pdf',
                'status': 'saved'
            }
        ]
    }
    
    # Тестовые данные с неправильным типом attachments (как в логе)
    email_data_with_wrong_attachments = {
        'from': 'm.gogoleva@dna-technology.ru',
        'attachments': 4  # Число вместо списка
    }
    
    extractor = AttachmentEvidenceExtractor()
    
    print("\n🧪 Тест 1: Правильная структура с вложениями")
    evidence_list = extractor.extract(email_data_with_attachments)
    print(f"📎 Найдено доказательств: {len(evidence_list)}")
    
    for evidence in evidence_list:
        print(f"  🏢 {evidence.matched_name} -> {evidence.city}")
    
    print("\n🧪 Тест 2: Неправильная структура (число вместо списка)")
    evidence_list_wrong = extractor.extract(email_data_with_wrong_attachments)
    print(f"📎 Найдено доказательств: {len(evidence_list_wrong)}")
    
    print("\n🧪 Тест 3: Отсутствие поля attachments")
    evidence_list_missing = extractor.extract({'from': 'test@example.com'})
    print(f"📎 Найдено доказательств: {len(evidence_list_missing)}")
    
    # Проверяем, что нашли доказательства в правильном случае
    if len(evidence_list) > 0:
        print("✅ ТЕСТ ПРОЙДЕН: Найдены доказательства локации из вложений")
        
        # Проверяем, что есть доказательство для МИЛЛАБ
        millab_found = False
        for evidence in evidence_list:
            if 'миллаб' in evidence.org_name_norm.lower():
                millab_found = True
                print(f"✅ Найдено доказательство для МИЛЛАБ: {evidence.city}")
                break
        
        if not millab_found:
            print("⚠️ Доказательство для МИЛЛАБ не найдено")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Доказательства не найдены")
    
    print("\n🎉 Тестирование завершено")

if __name__ == "__main__":
    test_fixed_attachment_processing()