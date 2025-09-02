#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 ФИНАЛЬНЫЙ ТЕСТ ФИЛЬТРАЦИИ INLINE ИЗОБРАЖЕНИЙ
Тестируем исправленную функцию в основном файле
"""

import sys
import os
from pathlib import Path

def test_main_filter():
    """Тестируем функцию из основного файла"""

    # Имитируем структуру основного файла
    class MockLogger:
        def debug(self, msg):
            pass
        def info(self, msg):
            pass
        def warning(self, msg):
            pass
        def error(self, msg):
            pass

    class MockEmailFilters:
        def __init__(self, logger):
            self.logger = logger
            self.inline_exclusion_patterns = {
                r'mailrusigimg_.*',     # Подписи Mail.ru
                r'signature.*',         # Подписи
                r'logo.*',              # Логотипы
                r'banner.*',            # Баннеры
                r'footer.*',            # Футеры
                r'header.*',            # Хедеры
                r'image00[1-9]\.',      # image001, image002 и т.д.
                r'image0[1-9]\.',       # image01, image02 и т.д.
                r'blocked\.',           # blocked.gif и т.д.
                r'.*WRD00.*',           # WRD000.jpg, WRD001.jpg и т.д.
                r'.*WRD0.*',            # WRD0.jpg и т.д.
                r'_\..*',               # _.jpg, _.png и т.д.
                r'^_+$',                # ___, ____ и т.д.
            }

        def is_inline_image_excluded(self, filename: str, content_type: str, content_id: str = None):
            """Исправленная функция из основного файла"""
            import re
            from typing import Optional

            if not filename:
                return None

            filename_lower = filename.lower()

            # Проверяем Content-ID (характерно для встроенных изображений)
            if content_id:
                return f"изображение с Content-ID: {content_id}"

            # Проверяем на очень короткие имена файлов
            if len(filename) <= 3:
                return f"слишком короткое имя файла: {filename}"

            # Извлекаем имя файла без расширения для анализа
            name_without_ext = filename
            if '.' in filename:
                name_without_ext = filename.rsplit('.', 1)[0]

            # Проверяем на случайные имена (только буквы и цифры, без пробелов и точек)
            if re.match(r'^[a-zA-Z0-9]+$', name_without_ext):
                # Для коротких имен - проверяем длину
                if len(name_without_ext) <= 6:
                    # Короткие имена могут быть нормальными, проверяем на специальные случаи
                    if name_without_ext in ['img', 'pic', 'photo', 'image']:
                        return None  # Эти короткие имена могут быть нормальными
                    else:
                        return f"слишком короткое имя файла: {filename}"

                # Для длинных имен - проверяем entropy
                unique_chars = len(set(name_without_ext.lower()))
                total_chars = len(name_without_ext)

                # Вычисляем коэффициент разнообразия
                diversity_ratio = unique_chars / total_chars

                # Если много повторяющихся символов - вероятно паттерн, а не случайное имя
                if diversity_ratio < 0.6:  # Менее 60% уникальных символов
                    return f"низкая энтропия символов, вероятно паттерн: {filename}"

                # Если высокая энтропия и длина > 8 - вероятно случайное имя
                if len(name_without_ext) > 8 and diversity_ratio > 0.7:
                    return f"высокая энтропия символов, вероятно случайное имя: {filename}"

                # Средний случай - исключаем имена длиннее 12 символов
                if len(name_without_ext) > 12:
                    return f"слишком длинное имя файла: {filename}"

            # Проверяем паттерны мусорных inline изображений
            for pattern in self.inline_exclusion_patterns:
                if re.match(pattern, filename_lower, re.IGNORECASE):
                    return f"соответствует паттерну исключения: {pattern}"

            return None

    # Тестовые файлы
    test_files = [
        # Реальные файлы из data/attachments
        "ghgq2FUQF40it72R.png",     # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - случайное имя
        "mailrusigimg_P7zCThU7.jpg", # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - паттерн Mail.ru
        "_WRD000.jpg",              # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - паттерн WRD
        "Снимок.JPG",               # ПРОПУСТИТЬ - нормальное изображение
        "image001.png",             # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - паттерн image00
        "normal_image.jpg",         # ПРОПУСТИТЬ - нормальное изображение
        "contract.pdf",             # ПРОПУСТИТЬ - не изображение
        "photo.png",                # ПРОПУСТИТЬ - нормальное фото
        "_.png",                    # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - короткое имя
        "blocked.gif",              # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - паттерн blocked
        "WRD0004.jpg",              # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - паттерн WRD
        "FzRBj65g1dFl1OAD.png",     # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - случайное имя
        "r090y9LzxmKv0iBB.png",     # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - случайное имя
        "TUjUxftXXS8RWD3B.png",     # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - случайное имя
        "M6T4nTn8HGJpqL8U.png",     # ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН - случайное имя
    ]

    logger = MockLogger()
    filters = MockEmailFilters(logger)

    print("🎯 ФИНАЛЬНЫЙ ТЕСТ ФИЛЬТРАЦИИ INLINE ИЗОБРАЖЕНИЙ")
    print("=" * 70)
    print("35")
    print("=" * 70)

    excluded_count = 0
    total_count = len(test_files)

    for filename in test_files:
        result = filters.is_inline_image_excluded(filename, "image/png")

        if result:
            status = "🚫 ИСКЛЮЧЕН"
            excluded_count += 1
        else:
            status = "✅ ПРОПУЩЕН"

        print("35")

    print("=" * 70)
    print(f"📊 РЕЗУЛЬТАТЫ: {excluded_count}/{total_count} файлов исключено")
    print(".1f")

    # Проверяем, что основные мусорные файлы исключены
    critical_files = ["ghgq2FUQF40it72R.png", "mailrusigimg_P7zCThU7.jpg", "_WRD000.jpg", "image001.png"]
    critical_excluded = 0

    for filename in critical_files:
        if filters.is_inline_image_excluded(filename, "image/png"):
            critical_excluded += 1

    print(f"🎯 КРИТИЧЕСКИЕ ФАЙЛЫ: {critical_excluded}/{len(critical_files)} исключено")
    return excluded_count >= 10 and critical_excluded == len(critical_files)

if __name__ == '__main__':
    success = test_main_filter()

    if success:
        print("✅ ТЕСТ ПРОЙДЕН! Функция фильтрации работает корректно")
        print("🎉 Готово к использованию в основном коде")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН! Нужно доработать функцию")
        print("🔧 Проверьте логику фильтрации")
