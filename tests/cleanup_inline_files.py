#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧹 СКРИПТ ДЛЯ ОЧИСТКИ МУСОРНЫХ INLINE ФАЙЛОВ
Удаляет мусорные inline изображения из существующих папок
"""

import os
import re
from pathlib import Path
from typing import List

def should_exclude_inline_file(filename: str) -> bool:
    """Проверяет, нужно ли исключить inline файл"""

    if not filename:
        return False

    filename_lower = filename.lower()

    # Извлекаем имя файла без расширения для анализа
    name_without_ext = filename
    if '.' in filename:
        name_without_ext = filename.rsplit('.', 1)[0]

    # Проверяем на очень короткие имена файлов
    if len(filename) <= 3:
        return True

    # Проверяем на случайные имена (только буквы и цифры, без пробелов и точек)
    if re.match(r'^[a-zA-Z0-9]+$', name_without_ext):
        # Для коротких имен - проверяем длину
        if len(name_without_ext) <= 6:
            # Короткие имена могут быть нормальными, проверяем на специальные случаи
            if name_without_ext in ['img', 'pic', 'photo', 'image']:
                return False  # Эти короткие имена могут быть нормальными
            else:
                return True

        # Для длинных имен - проверяем entropy
        unique_chars = len(set(name_without_ext.lower()))
        total_chars = len(name_without_ext)

        # Вычисляем коэффициент разнообразия
        diversity_ratio = unique_chars / total_chars

        # Если много повторяющихся символов - вероятно паттерн, а не случайное имя
        if diversity_ratio < 0.6:  # Менее 60% уникальных символов
            return True

        # Если высокая энтропия и длина > 8 - вероятно случайное имя
        if len(name_without_ext) > 8 and diversity_ratio > 0.7:
            return True

        # Средний случай - исключаем имена длиннее 12 символов
        if len(name_without_ext) > 12:
            return True

    # Паттерны мусорных inline изображений
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

    # Проверяем паттерны
    for pattern in exclusion_patterns:
        if re.match(pattern, filename_lower, re.IGNORECASE):
            return True

    return False

def cleanup_inline_files(dates: List[str]):
    """Очищает мусорные inline файлы за указанные даты"""

    attachments_dir = Path("data/attachments")
    cleaned_files = []

    print("🧹 НАЧИНАЕМ ОЧИСТКУ МУСОРНЫХ INLINE ФАЙЛОВ")
    print("=" * 60)

    for date in dates:
        date_dir = attachments_dir / date
        if not date_dir.exists():
            print(f"📁 Папка {date} не найдена, пропускаем")
            continue

        print(f"🔍 Обрабатываем папку: {date}")
        inline_files = list(date_dir.glob("*inline*"))

        if not inline_files:
            print(f"   ℹ️ Inline файлов не найдено")
            continue

        print(f"   📎 Найдено inline файлов: {len(inline_files)}")

        removed_count = 0
        for file_path in inline_files:
            filename = file_path.name

            # Извлекаем оригинальное имя файла из имени файла системы
            # Формат: {thread_id}_{timestamp}_{type}_{original_filename}
            if '_inline_' in filename:
                # Находим позицию '_inline_' и берем всё после неё
                inline_pos = filename.find('_inline_')
                original_filename = filename[inline_pos + 8:]  # +8 для пропуска '_inline_'
            else:
                # Если формат не распознан, используем полное имя
                original_filename = filename

            if should_exclude_inline_file(original_filename):
                try:
                    file_path.unlink()
                    cleaned_files.append(str(file_path))
                    removed_count += 1
                    print(f"   🗑️ УДАЛЕН: {filename} (оригинал: {original_filename})")
                except Exception as e:
                    print(f"   ❌ ОШИБКА удаления {filename}: {e}")
            else:
                print(f"   ✅ СОХРАНЕН: {filename} (оригинал: {original_filename})")

        print(f"   📊 Удалено файлов: {removed_count}/{len(inline_files)}")

    print("=" * 60)
    print(f"🎯 ОБЩИЙ РЕЗУЛЬТАТ: удалено {len(cleaned_files)} мусорных файлов")

    if cleaned_files:
        print("\nУдаленные файлы:")
        for file in cleaned_files[:10]:  # Показываем первые 10
            print(f"  - {file}")
        if len(cleaned_files) > 10:
            print(f"  ... и еще {len(cleaned_files) - 10} файлов")

    return len(cleaned_files)

def main():
    """Главная функция"""

    # Даты для очистки
    target_dates = [
        "2025-07-07", "2025-07-09", "2025-07-10",
        "2025-07-15", "2025-07-16", "2025-07-21", "2025-07-22"
    ]

    print("🎯 ОЧИСТКА МУСОРНЫХ INLINE ФАЙЛОВ")
    print(f"📅 Целевые даты: {', '.join(target_dates)}")
    print("=" * 60)

    cleaned_count = cleanup_inline_files(target_dates)

    if cleaned_count > 0:
        print(f"\n✅ ОЧИСТКА ЗАВЕРШЕНА: удалено {cleaned_count} мусорных файлов")
        print("📝 Резервная копия сохранена в: data/attachments_backup_before_fix")
    else:
        print("\nℹ️ Мусорных файлов для удаления не найдено")

if __name__ == '__main__':
    main()
