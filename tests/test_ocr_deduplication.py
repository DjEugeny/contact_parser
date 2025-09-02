#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 ТЕСТ ПРОВЕРКИ ИСПРАВЛЕНИЯ ДУБЛИРОВАНИЯ ФАЙЛОВ В OCR ПРОЦЕССОРЕ
Тестируем исправление проблемы с датой 2025-07-22
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ocr_processor import OCRProcessor

def test_deduplication_fix():
    """Тестируем исправление дублирования файлов"""

    print("🧪 ТЕСТ ИСПРАВЛЕНИЯ ДУБЛИРОВАНИЯ ФАЙЛОВ В OCR ПРОЦЕССОРЕ")
    print("=" * 60)

    # Создаем процессор
    processor = OCRProcessor()

    # Тестируем дату с проблемой дублирования
    test_date = "2025-07-22"

    print(f"📅 Тестируем дату: {test_date}")
    print("-" * 40)

    # Получаем файлы для даты
    files_to_test = processor.get_files_for_date(test_date)

    if not files_to_test:
        print(f"❌ Не найдено файлов для даты {test_date}")
        return False

    print(f"📁 Найдено файлов: {len(files_to_test)}")

    # Проверяем каждый файл
    duplicated_found = False

    for i, file_path in enumerate(files_to_test, 1):
        file_name = file_path.name
        print(f"\n{i}. Проверяем файл: {file_name}")

        # Проверяем, есть ли уже результаты
        has_existing = processor._check_existing_results(file_path, test_date)

        if has_existing:
            print("   ✅ Уже обработан - будет пропущен")
            # Получаем существующий результат для дополнительной проверки
            existing_result = processor._get_existing_result(file_path, test_date)
            if existing_result and existing_result.get('success'):
                print(f"   📄 Результат: {existing_result.get('method', 'unknown')}")
            else:
                print("   ⚠️  Найден только результат с ошибкой")
        else:
            print("   🔄 Не обработан - будет обработан заново")
            duplicated_found = True

    print("\n" + "=" * 60)

    if duplicated_found:
        print("❌ ПРОБЛЕМА: Некоторые файлы будут обработаны повторно!")
        print("🔧 Исправление не сработало полностью")
        return False
    else:
        print("✅ УСПЕХ: Все файлы правильно распознаны как уже обработанные!")
        print("🎯 Исправление работает корректно")
        return True

if __name__ == "__main__":
    success = test_deduplication_fix()

    if success:
        print("\n🎉 ТЕСТ ПРОЙДЕН! Дублирование файлов исправлено.")
    else:
        print("\n⚠️  ТЕСТ НЕ ПРОЙДЕН! Требуется дополнительное исправление.")

    sys.exit(0 if success else 1)
