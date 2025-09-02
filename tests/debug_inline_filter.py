#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔍 ОТЛАДКА ФУНКЦИИ ФИЛЬТРАЦИИ INLINE ИЗОБРАЖЕНИЙ
Показывает пошаговую работу фильтра
"""

import re

def is_inline_image_excluded_debug(filename: str, content_type: str = "image/png", content_id: str = None) -> str:
    """Отладочная версия функции с подробным логированием"""

    print(f"\n🔍 АНАЛИЗ ФАЙЛА: {filename}")
    print(f"   Content-Type: {content_type}")
    print(f"   Content-ID: {content_id}")

    if not filename:
        print("   ❌ Пустое имя файла")
        return None

    filename_lower = filename.lower()
    print(f"   Lowercase: {filename_lower}")

    # Проверяем Content-ID (характерно для встроенных изображений)
    if content_id:
        print(f"   ❌ Найден Content-ID: {content_id}")
        return f"изображение с Content-ID: {content_id}"

    # Проверяем на очень короткие имена файлов
    if len(filename) <= 3:
        print(f"   ❌ Слишком короткое имя файла: {len(filename)} символов")
        return f"слишком короткое имя файла: {filename}"

    # Извлекаем имя файла без расширения для анализа
    name_without_ext = filename
    if '.' in filename:
        name_without_ext = filename.rsplit('.', 1)[0]

    print(f"   📄 Имя без расширения: {name_without_ext}")

    # Проверяем на случайные имена (только буквы и цифры, без пробелов и точек)
    if re.match(r'^[a-zA-Z0-9]+$', name_without_ext):
        print(f"   ✅ Соответствует паттерну букв/цифр без пробелов")

        # Для коротких имен - проверяем длину
        if len(name_without_ext) <= 6:
            print(f"   📏 Короткое имя ({len(name_without_ext)} символов)")
            # Короткие имена могут быть нормальными, проверяем на специальные случаи
            if name_without_ext in ['img', 'pic', 'photo', 'image']:
                print("   ✅ Короткое имя в списке разрешенных")
                return None
            else:
                print("   ❌ Короткое имя не в списке разрешенных")
                return f"слишком короткое имя файла: {filename}"

        # Для длинных имен - проверяем entropy
        unique_chars = len(set(name_without_ext.lower()))
        total_chars = len(name_without_ext)
        diversity_ratio = unique_chars / total_chars

        print(f"   📊 Энтропия: {unique_chars}/{total_chars} уникальных символов ({diversity_ratio:.2f})")

        # Если много повторяющихся символов - вероятно паттерн, а не случайное имя
        if diversity_ratio < 0.6:  # Менее 60% уникальных символов
            print("   ❌ Низкая энтропия - вероятно паттерн")
            return f"низкая энтропия символов, вероятно паттерн: {filename}"

        # Если высокая энтропия и длина > 8 - вероятно случайное имя
        if len(name_without_ext) > 8 and diversity_ratio > 0.7:
            print("   ❌ Высокая энтропия - вероятно случайное имя")
            return f"высокая энтропия символов, вероятно случайное имя: {filename}"

        # Средний случай - исключаем имена длиннее 12 символов
        if len(name_without_ext) > 12:
            print("   ❌ Слишком длинное имя файла")
            return f"слишком длинное имя файла: {filename}"

        print("   ✅ Имя прошло проверку энтропии")
    else:
        print("   📝 Имя содержит специальные символы или пробелы")

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
        r'.*WRD00.*',           # WRD000.jpg, WRD001.jpg и т.д.
        r'.*WRD0.*',            # WRD0.jpg и т.д.
        r'_\..*',               # _.jpg, _.png и т.д.
        r'^_+$',                # ___, ____ и т.д.
    ]

    print("   🔍 Проверка паттернов исключения:")
    # Проверяем паттерны
    for pattern in exclusion_patterns:
        if re.match(pattern, filename_lower, re.IGNORECASE):
            print(f"   ❌ Соответствует паттерну: {pattern}")
            return f"соответствует паттерну исключения: {pattern}"
        else:
            print(f"   ✅ Не соответствует паттерну: {pattern}")

    print("   ✅ Файл прошел все проверки")
    return None

def debug_test():
    """Отладочный тест"""

    test_files = [
        "ghgq2FUQF40it72R.png",
        "mailrusigimg_P7zCThU7.jpg",
        "_WRD000.jpg",
        "normal_image.jpg",
    ]

    for filename in test_files:
        result = is_inline_image_excluded_debug(filename)
        print(f"   РЕЗУЛЬТАТ: {result}")
        print("-" * 50)

if __name__ == '__main__':
    debug_test()
