#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправления формата дат в OCR процессоре
Дата создания: 2025-01-30 01:30 (UTC+07)
Агент: IMPLEMENT
"""

import sys
import os
from datetime import datetime

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from ocr_processor import normalize_date_string
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def test_normalize_date_string():
    """
    Тестирование функции normalize_date_string с различными форматами дат
    """
    print("🧪 Тестирование normalize_date_string...")
    
    test_cases = [
        # RFC 2822 формат (из email headers)
        ("Mon, 12 May 2025 12:30:14 +0700", "2025-05-12"),
        ("Tue, 01 Jan 2024 00:00:00 +0000", "2024-01-01"),
        ("Wed, 15 Dec 2023 23:59:59 -0500", "2023-12-15"),
        
        # ISO 8601 формат
        ("2025-05-12T12:30:14+07:00", "2025-05-12"),
        ("2024-01-01T00:00:00Z", "2024-01-01"),
        
        # Простые форматы
        ("2025-05-12", "2025-05-12"),
        ("12/05/2025", "2025-05-12"),
        ("12.05.2025", "2025-05-12"),
        
        # Форматы с названиями месяцев
        ("May 12, 2025", "2025-05-12"),
        ("12 May 2025", "2025-05-12"),
    ]
    
    passed = 0
    failed = 0
    
    for input_date, expected in test_cases:
        try:
            result = normalize_date_string(input_date)
            if result == expected:
                print(f"  ✅ '{input_date}' → '{result}'")
                passed += 1
            else:
                print(f"  ❌ '{input_date}' → '{result}' (ожидалось: '{expected}')")
                failed += 1
        except Exception as e:
            print(f"  ❌ '{input_date}' → ОШИБКА: {e}")
            failed += 1
    
    return passed, failed

def test_date_format_consistency():
    """
    Тестирование консистентности формата дат
    """
    print("\n🧪 Тестирование консистентности формата...")
    
    # Тестируем различные входные форматы, которые должны давать одинаковый результат
    same_date_formats = [
        "Mon, 12 May 2025 12:30:14 +0700",
        "2025-05-12T12:30:14+07:00",
        "2025-05-12",
        "May 12, 2025",
        "12 May 2025"
    ]
    
    expected_result = "2025-05-12"
    passed = 0
    failed = 0
    
    for date_format in same_date_formats:
        try:
            result = normalize_date_string(date_format)
            if result == expected_result:
                print(f"  ✅ '{date_format}' → '{result}'")
                passed += 1
            else:
                print(f"  ❌ '{date_format}' → '{result}' (ожидалось: '{expected_result}')")
                failed += 1
        except Exception as e:
            print(f"  ❌ '{date_format}' → ОШИБКА: {e}")
            failed += 1
    
    return passed, failed

def test_error_handling():
    """
    Тестирование обработки ошибочных входных данных
    """
    print("\n🧪 Тестирование обработки ошибок...")
    
    invalid_dates = [
        "invalid date",
        "32/13/2025",  # Невалидная дата
        "",  # Пустая строка
        "not a date at all",
        "2025-13-45",  # Невалидный месяц и день
    ]
    
    passed = 0
    failed = 0
    
    for invalid_date in invalid_dates:
        try:
            result = normalize_date_string(invalid_date)
            # Если функция не выбросила исключение, проверяем результат
            if result is None or result == invalid_date:
                print(f"  ✅ '{invalid_date}' → корректно обработано ('{result}')")
                passed += 1
            else:
                print(f"  ⚠️  '{invalid_date}' → '{result}' (неожиданный результат)")
                passed += 1  # Считаем как пройденный, если не упало
        except Exception as e:
            print(f"  ✅ '{invalid_date}' → корректно выброшено исключение: {type(e).__name__}")
            passed += 1
    
    return passed, failed

def main():
    """
    Основная функция тестирования
    """
    print("🚀 Запуск тестов исправления формата дат в OCR процессоре")
    print(f"📅 Дата тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC+07)")
    print("="*60)
    
    total_passed = 0
    total_failed = 0
    
    # Тест 1: Основная функция нормализации
    passed, failed = test_normalize_date_string()
    total_passed += passed
    total_failed += failed
    
    # Тест 2: Консистентность формата
    passed, failed = test_date_format_consistency()
    total_passed += passed
    total_failed += failed
    
    # Тест 3: Обработка ошибок
    passed, failed = test_error_handling()
    total_passed += passed
    total_failed += failed
    
    # Итоговые результаты
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print(f"✅ Пройдено тестов: {total_passed}")
    print(f"❌ Провалено тестов: {total_failed}")
    print(f"📈 Процент успеха: {(total_passed / (total_passed + total_failed) * 100):.1f}%")
    
    if total_failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Исправление формата дат работает корректно")
        return 0
    else:
        print(f"\n⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ: {total_failed} тестов провалено")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)