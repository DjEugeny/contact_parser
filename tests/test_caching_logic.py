#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки логики кэширования OCR результатов
"""

import sys
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ocr_processor import OCRProcessor

def create_test_image_with_text():
    """Создает простое изображение с текстом для тестирования"""
    # Создаем белое изображение 400x200
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Добавляем текст
    text = "Test Image for OCR\nCaching Logic Test\n2025-12-31"
    
    try:
        # Пытаемся использовать системный шрифт
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
    except:
        # Если не получается, используем стандартный
        font = ImageFont.load_default()
    
    # Рисуем текст черным цветом
    draw.multiline_text((50, 50), text, fill='black', font=font)
    
    return img

def test_caching_logic():
    """Тестирует логику кэширования OCR результатов"""
    print("🧪 Тест логики кэширования OCR результатов")
    print("=" * 50)
    
    # Создаем тестовое изображение
    test_image = create_test_image_with_text()
    test_image_path = Path("/tmp/test_caching_image.png")
    test_image.save(test_image_path)
    print(f"📷 Создано тестовое изображение: {test_image_path}")
    
    # Инициализируем OCR процессор
    try:
        processor = OCRProcessor()
        print("✅ OCRProcessor инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации OCRProcessor: {e}")
        return
    
    test_date = "2025-12-31"
    
    print(f"\n🔍 Первый запуск обработки файла (должен обработать)")
    result1 = processor.extract_text_from_file(test_image_path, date=test_date)
    processor.save_result(result1, test_date)
    
    print(f"\n🔍 Второй запуск обработки того же файла (должен найти в кэше)")
    result2 = processor.extract_text_from_file(test_image_path, date=test_date)
    
    print(f"\n📊 Результаты теста:")
    print(f"   Первый запуск - метод: {result1.get('method', 'N/A')}, успех: {result1.get('success', False)}")
    print(f"   Второй запуск - метод: {result2.get('method', 'N/A')}, успех: {result2.get('success', False)}")
    
    # Проверяем, что второй запуск использовал кэш
    if 'cached' in result2.get('method', ''):
        print("✅ Логика кэширования работает корректно!")
    else:
        print("❌ Логика кэширования НЕ работает!")
    
    # Очищаем тестовый файл
    if test_image_path.exists():
        test_image_path.unlink()
        print(f"🗑️ Удален тестовый файл: {test_image_path}")

if __name__ == "__main__":
    test_caching_logic()