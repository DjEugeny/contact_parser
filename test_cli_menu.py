#!/usr/bin/env python3
"""Тест CLI меню с автоматическим вводом"""

import sys
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from advanced_email_fetcher import cli_menu

def test_exit_option():
    """Тест опции выхода"""
    print("🧪 Тест опции 'Выход' (0):")
    print("="*60)
    
    # Симулируем ввод "0" (выход)
    old_stdin = sys.stdin
    sys.stdin = StringIO("0\n")
    
    try:
        start_date, end_date = cli_menu()
        
        if start_date is None and end_date is None:
            print("✅ Опция 'Выход' работает корректно")
            return True
        else:
            print("❌ Опция 'Выход' не работает")
            return False
    finally:
        sys.stdin = old_stdin

def test_single_date():
    """Тест выбора одной даты"""
    print("\n🧪 Тест выбора одной даты:")
    print("="*60)
    
    # Симулируем ввод: режим 2, дата 12.07.2025
    old_stdin = sys.stdin
    sys.stdin = StringIO("2\n12.07.2025\n")
    
    try:
        start_date, end_date = cli_menu()
        
        if start_date and end_date and start_date == end_date:
            print(f"✅ Одна дата выбрана: {start_date.strftime('%Y-%m-%d')}")
            return True
        else:
            print("❌ Ошибка выбора одной даты")
            return False
    finally:
        sys.stdin = old_stdin

if __name__ == "__main__":
    results = []
    results.append(test_exit_option())
    results.append(test_single_date())
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    print(f"📊 Результаты: ✅ {passed}/{total} тестов пройдено")
    
    sys.exit(0 if all(results) else 1)
