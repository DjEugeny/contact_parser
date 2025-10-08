#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тест парсинга дат для advanced_email_fetcher"""

import sys
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / "src"))

from advanced_email_fetcher import parse_date_flexible

def test_parse_date_flexible():
    """Тест различных форматов дат"""
    
    test_cases = [
        ("2025-07-12", "2025-07-12"),  # ISO формат
        ("12.07.2025", "2025-07-12"),  # Точки
        ("12-7-25", "2025-07-12"),     # Короткий формат
        ("12 июля 25", "2025-07-12"),  # Текстовый русский
        ("1 января 2025", "2025-01-01"),  # Полный год
    ]
    
    print("🧪 Тестирование parse_date_flexible:")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for input_str, expected_output in test_cases:
        try:
            result = parse_date_flexible(input_str)
            result_str = result.strftime('%Y-%m-%d')
            
            if result_str == expected_output:
                print(f"✅ '{input_str}' → {result_str}")
                passed += 1
            else:
                print(f"❌ '{input_str}' → {result_str} (ожидалось: {expected_output})")
                failed += 1
        except Exception as e:
            print(f"❌ '{input_str}' → Ошибка: {e}")
            failed += 1
    
    print("="*60)
    print(f"Результаты: ✅ {passed} пройдено, ❌ {failed} провалено")
    
    return failed == 0

if __name__ == "__main__":
    success = test_parse_date_flexible()
    sys.exit(0 if success else 1)
