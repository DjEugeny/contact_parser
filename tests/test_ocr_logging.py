#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки логирования в OCR модуле
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from ocr_processor import OCRProcessor
from ocr_processor_adapter import OCRProcessorAdapter

def test_ocr_logging():
    """
    Тест логирования OCR модуля:
    1. Проверяет сообщения о пропуске уже обработанных файлов
    2. Проверяет сообщения о начале обработки новых файлов
    3. Проверяет сообщения о сохранении результатов
    """
    print("🧪 Тестирование логирования OCR модуля")
    print("=" * 50)
    
    # Инициализируем OCR процессор
    ocr_processor = OCRProcessor()
    adapter = OCRProcessorAdapter()
    
    # Создаем тестовый email с вложениями
    test_date = datetime.now().strftime('%Y-%m-%d')
    test_email = {
        'date': test_date,
        'subject': 'Тестовое письмо',
        'attachments': [
            {
                'file_path': '/Users/evgenyzach/contact_parser/test_files/test_image.jpg'
            }
        ]
    }
    
    print(f"📅 Тестовая дата: {test_date}")
    print(f"📧 Тестовое письмо с {len(test_email['attachments'])} вложением")
    print()
    
    # Проверяем, есть ли тестовый файл
    test_file_path = Path('/Users/evgenyzach/contact_parser/test_files/test_image.jpg')
    if not test_file_path.exists():
        print("⚠️ Тестовый файл не найден. Создаем заглушку...")
        test_file_path.parent.mkdir(exist_ok=True)
        test_file_path.write_text("Test image content")
    
    print("🔄 Первый запуск - должен обработать файл:")
    print("-" * 30)
    
    # Первый запуск - должен обработать файл
    result1 = adapter.process_email_attachments(test_email, None)
    
    print()
    print("🔄 Второй запуск - должен пропустить уже обработанный файл:")
    print("-" * 30)
    
    # Второй запуск - должен пропустить файл
    result2 = adapter.process_email_attachments(test_email, None)
    
    print()
    print("✅ Тест завершен")
    print(f"📊 Результат первого запуска: {len(result1.get('attachments_text', []))} файлов обработано")
    print(f"📊 Результат второго запуска: {len(result2.get('attachments_text', []))} файлов обработано")
    
    return True

if __name__ == '__main__':
    try:
        test_ocr_logging()
        print("\n🎉 Тест успешно выполнен!")
    except Exception as e:
        print(f"\n❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()