#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест упрощенной логики AttachmentEvidenceExtractor
Проверяем что обрабатываются ВСЕ вложения с OCR-текстом
"""

import sys
import os

# Добавляем путь к src в PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

# Теперь импортируем напрямую
from postprocessing.attachment_evidence_extractor import AttachmentEvidenceExtractor, AttachmentEvidenceConfig, LocationEvidence

def test_simplified_logic():
    """Тест упрощенной логики - обрабатываем ВСЕ вложения"""
    
    # Тестовые данные с разными типами вложений
    test_email_data = {
        'attachments': [
            {
                'filename': 'random_document.pdf',  # НЕ деловой документ по имени
                'text_content': '''
                ООО "ТЕСТОВАЯ КОМПАНИЯ"
                Юридический адрес: 123456, г. Санкт-Петербург, ул. Тестовая, д. 1
                ИНН: 7812345678
                ''',
                'mime': 'application/pdf'
            },
            {
                'filename': 'image.jpg',  # Вообще не документ
                'text_content': '''
                Компания МИЛЛАБ
                г. Москва, Варшавское шоссе, 17
                Лаборатория медицинской диагностики
                ''',
                'mime': 'image/jpeg'
            },
            {
                'filename': 'empty_file.txt',  # Пустой файл
                'text_content': '',
                'mime': 'text/plain'
            },
            {
                'filename': 'no_orgs.txt',  # Нет организаций
                'text_content': 'Просто какой-то текст без организаций',
                'mime': 'text/plain'
            }
        ]
    }
    
    extractor = AttachmentEvidenceExtractor()
    evidence_list = extractor.extract(test_email_data)
    
    print("🧪 Тест упрощенной логики AttachmentEvidenceExtractor")
    print(f"📎 Обработано вложений: {len(test_email_data['attachments'])}")
    print(f"✅ Найдено доказательств: {len(evidence_list)}")
    print()
    
    for i, evidence in enumerate(evidence_list, 1):
        print(f"Доказательство {i}:")
        print(f"  📄 Файл: {evidence.source['filename']}")
        print(f"  🏢 Организация: {evidence.matched_name}")
        print(f"  🏙️ Город: {evidence.city}")
        print(f"  📍 Адрес: {evidence.address}")
        print(f"  🎯 Уверенность: {evidence.confidence:.2f}")
        print()
    
    # Проверяем что нашли доказательства из разных типов файлов
    filenames = [ev.source['filename'] for ev in evidence_list]
    print(f"📊 Файлы с найденными доказательствами: {filenames}")
    
    # Должны найти доказательства из random_document.pdf и image.jpg
    assert len(evidence_list) >= 2, f"Ожидали минимум 2 доказательства, получили {len(evidence_list)}"
    assert 'random_document.pdf' in filenames, "Должны обработать random_document.pdf"
    assert 'image.jpg' in filenames, "Должны обработать image.jpg"
    
    print("✅ Тест пройден! Упрощенная логика работает корректно")
    print("🎉 Обрабатываются ВСЕ вложения с OCR-текстом, независимо от имени файла")

if __name__ == "__main__":
    test_simplified_logic()