#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 ТЕСТ С РЕАЛЬНЫМИ ПРИМЕРАМИ INLINE ФАЙЛОВ
Тестируем на реальных файлах из data/attachments
"""

import re
from pathlib import Path

def is_inline_image_excluded(filename: str, content_type: str = "image/png", content_id: str = None) -> str:
    """Проверка inline изображения на исключение"""

    if not filename:
        return None

    filename_lower = filename.lower()

    # Проверяем Content-ID (характерно для встроенных изображений)
    if content_id:
        return f"изображение с Content-ID: {content_id}"

    # Проверяем на очень короткие имена файлов
    if len(filename) <= 3:
        return f"слишком короткое имя файла: {filename}"

    # Проверяем на случайные имена (только буквы и цифры, без пробелов и точек)
    if re.match(r'^[a-zA-Z0-9]+$', filename):
        # Для коротких имен - проверяем длину
        if len(filename) <= 6:
            # Короткие имена могут быть нормальными, проверяем на специальные случаи
            if filename in ['img', 'pic', 'photo', 'image']:
                return None  # Эти короткие имена могут быть нормальными
            else:
                return f"слишком короткое имя файла: {filename}"

        # Для длинных имен - проверяем entropy
        unique_chars = len(set(filename.lower()))
        total_chars = len(filename)

        # Вычисляем коэффициент разнообразия
        diversity_ratio = unique_chars / total_chars

        # Если много повторяющихся символов - вероятно паттерн, а не случайное имя
        if diversity_ratio < 0.6:  # Менее 60% уникальных символов
            return f"низкая энтропия символов, вероятно паттерн: {filename}"

        # Если высокая энтропия и длина > 8 - вероятно случайное имя
        if len(filename) > 8 and diversity_ratio > 0.7:
            return f"высокая энтропия символов, вероятно случайное имя: {filename}"

        # Средний случай - исключаем имена длиннее 12 символов
        if len(filename) > 12:
            return f"слишком длинное имя файла: {filename}"

    # Расширенные паттерны мусорных inline изображений
    exclusion_patterns = [
        r'mailrusigimg_.*',     # Подписи Mail.ru
        r'signature.*',         # Подписи
        r'logo.*',              # Логотипы
        r'banner.*',            # Баннеры
        r'footer.*',            # Футеры
        r'header.*',            # Хедеры
        r'image00[1-9]\.',      # image001, image002 и т.д.
        r'image0[1-9]\.',       # image01, image02 и т.д.
        r'blocked\.',           # blocked.gif и т.д.
        r'WRD00.*',             # WRD000.jpg, WRD001.jpg и т.д.
        r'WRD0.*',              # WRD0.jpg и т.д.
        r'_\..*',               # _.jpg, _.png и т.д.
        r'^_+$',                # ___, ____ и т.д.
    ]

    # Проверяем паттерны
    for pattern in exclusion_patterns:
        if re.match(pattern, filename_lower, re.IGNORECASE):
            return f"соответствует паттерну исключения: {pattern}"

    return None

def test_real_files():
    """Тестируем на реальных файлах из attachments"""

    # Реальные файлы из data/attachments
    real_files = [
        "ghgq2FUQF40it72R.png",     # Мусорный файл - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "mailrusigimg_P7zCThU7.jpg", # Подпись Mail.ru - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "_WRD000.jpg",              # Microsoft мусор - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "Снимок.JPG",               # Возможно полезное изображение - ПРОПУСТИТЬ
        "image001.png",             # Мусор из подписи - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "normal_image.jpg",         # Нормальное изображение - ПРОПУСТИТЬ
        "contract.pdf",             # Документ (не изображение) - ПРОПУСТИТЬ
        "photo.png",                # Фото - ПРОПУСТИТЬ
        "_.png",                    # Короткий мусор - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "blocked.gif",              # Мусор - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "WRD0004.jpg",              # Microsoft мусор - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "FzRBj65g1dFl1OAD.png",     # Случайное имя - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "r090y9LzxmKv0iBB.png",     # Случайное имя - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "TUjUxftXXS8RWD3B.png",     # Случайное имя - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
        "M6T4nTn8HGJpqL8U.png",     # Случайное имя - ДОЛЖЕН БЫТЬ ИСКЛЮЧЕН
    ]

    print("🧪 ТЕСТИРОВАНИЕ НА РЕАЛЬНЫХ ФАЙЛАХ ИЗ data/attachments")
    print("=" * 70)
    print("25")
    print("=" * 70)

    excluded_count = 0
    total_count = len(real_files)

    for filename in real_files:
        result = is_inline_image_excluded(filename)

        if result:
            status = "🚫 ИСКЛЮЧЕН"
            excluded_count += 1
        else:
            status = "✅ ПРОПУЩЕН"

        print("25")

    print("=" * 70)
    print(f"📊 РЕЗУЛЬТАТЫ: {excluded_count}/{total_count} файлов исключено")
    print(".1f")
    return excluded_count

if __name__ == '__main__':
    test_real_files()
