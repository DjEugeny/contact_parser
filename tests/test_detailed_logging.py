#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест детального логирования в google_sheets_bridge.py
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from google_sheets_bridge import LLM_Sheets_Bridge
from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image_with_text(text: str, output_path: Path):
    """Создает тестовое изображение с текстом"""
    # Создаем изображение
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Пытаемся использовать системный шрифт
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    # Добавляем текст
    draw.text((50, 50), text, fill='black', font=font)
    
    # Сохраняем
    img.save(output_path)
    print(f"Создано тестовое изображение: {output_path}")

def setup_test_data():
    """Настройка тестовых данных"""
    # Создаем папку для тестовой даты
    test_date = "2024-01-15"
    attachments_dir = Path("data/attachments") / test_date
    attachments_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем тестовое изображение
    test_image_path = attachments_dir / "test_logging_image.png"
    create_test_image_with_text(
        "Тестовый контакт\nИван Петров\n+7-999-123-45-67\nivan@example.com\nООО Тест",
        test_image_path
    )
    
    return test_date, test_image_path

def test_detailed_logging():
    """Тест детального логирования через google_sheets_bridge"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ ДЕТАЛЬНОГО ЛОГИРОВАНИЯ")
    print("="*60)
    
    # Настраиваем тестовые данные с реальной датой
    test_date = "2025-07-01"
    attachments_dir = Path("data/attachments") / test_date
    attachments_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем тестовое изображение
    test_image_path = attachments_dir / "test_logging_image.png"
    create_test_image_with_text(
        "Тестовый контакт\nИван Петров\n+7-999-123-45-67\nivan@example.com\nООО Тест",
        test_image_path
    )
    
    print(f"\n📅 Тестовая дата: {test_date}")
    print(f"📎 Тестовое изображение: {test_image_path}")
    
    # Создаем bridge
    print("\n🔧 Инициализация LLM_Sheets_Bridge...")
    bridge = LLM_Sheets_Bridge()
    
    # Переключаем процессор в тестовый режим
    bridge.processor.test_mode = True
    print("   🧪 Включен тестовый режим для LLM процессора")
    
    # Запускаем обработку с лимитом 1 письмо
    print(f"\n🚀 Запуск обработки писем за {test_date} (лимит: 1 письмо)...")
    print("\n" + "-"*60)
    
    try:
        success = bridge.process_and_export(test_date, max_emails=1)
        
        print("\n" + "-"*60)
        print("📊 РЕЗУЛЬТАТ ТЕСТА:")
        if success:
            print("   ✅ Обработка завершена")
        else:
            print("   ❌ Обработка не удалась")
            
        print("\n✅ Тест детального логирования завершен!")
        print("   Проверьте вывод выше на наличие сообщений OCR:")
        print("   - 'Обрабатываю вложение X'")
        print("   - 'Вложение X уже обработано. Пропускаю.'")
        print("   - 'Результаты распознавания сохранены'")
            
    except Exception as e:
        print(f"\n❌ ОШИБКА ТЕСТА: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return success

if __name__ == "__main__":
    test_detailed_logging()