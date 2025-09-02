#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 ТЕСТОВЫЙ СКРИПТ ДЛЯ ПРОВЕРКИ ФИЛЬТРАЦИИ INLINE ИЗОБРАЖЕНИЙ
Проверяет работу функции is_inline_image_excluded
"""

import sys
import os
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from advanced_email_fetcher import test_inline_exclusion

if __name__ == '__main__':
    print("🧪 ЗАПУСК ТЕСТА ФИЛЬТРАЦИИ INLINE ИЗОБРАЖЕНИЙ")
    print("=" * 60)

    success = test_inline_exclusion()

    if success:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("🎯 Функция фильтрации inline изображений работает корректно")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ!")
        print("🔧 Нужно доработать функцию фильтрации")

    print("=" * 60)
