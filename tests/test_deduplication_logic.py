#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 ПРОСТОЙ ТЕСТ ЛОГИКИ ИСПРАВЛЕНИЯ ДУБЛИРОВАНИЯ
Проверяем логику без зависимостей
"""

import re
from pathlib import Path

def check_existing_results_fixed(file_stem: str, date: str) -> bool:
    """Исправленная версия проверки существующих результатов"""

    # Моделируем структуру файлов для даты 2025-07-22
    existing_files = [
        "20250722_dna-technology_ru_17cb0020_033857_attach_реквизиты ООО.txt",
        "20250722_dna-technology_ru_17cb0020_084046_attach_реквизиты ООО.txt",  # Дубликат с другой меткой времени
        "20250722_dna-technology_ru_7fd711e1_033859_attach_КП 8196 от 22.07.2025.txt",
        "20250722_dna-technology_ru_7fd711e1_084056_attach_КП 8196 от 22.07.2025.txt",  # Дубликат
        "20250722_dna-technology_ru_c1a40aee_033901_attach_Счет на оплату _ 8363 от 22.07.2025.txt",
        "20250722_dna-technology_ru_c1a40aee_084113_attach_Счет на оплату _ 8363 от 22.07.2025.txt",  # Дубликат
        "20250722_dna-technology_ru_e0bfeeac_033855_attach_О компании ДНК -Технология.txt",
        "20250722_dna-technology_ru_e0bfeeac_084041_attach_О компании ДНК -Технология.txt",  # Дубликат
        "20250722_dna-technology_ru_e0bfeeac_033855_attach_DNA-Tech_logo_rus.txt"
    ]

    print(f"\n🔍 Проверяем файл: {file_stem}")

    # 🆕 Новая логика исправления
    parts = file_stem.split('_')
    if len(parts) >= 4 and parts[-2] == 'attach':
        # Это файл вложения с правильным форматом
        original_name = '_'.join(parts[3:])  # parts[3:] содержит оригинальное имя
        print(f"   📄 Распознано имя вложения: {original_name}")

        # Ищем файлы, содержащие оригинальное имя
        matching_files = []

        for existing_file in existing_files:
            existing_stem = existing_file.replace('.txt', '')
            # Убираем суффиксы методов и ошибок для сравнения
            clean_existing_stem = existing_stem.replace('___google_vision_pdf_optimized', '').replace('___local_pdf_text', '').replace('_ERROR', '')

            # Проверяем, содержит ли имя файла оригинальное имя вложения
            if original_name in clean_existing_stem:
                matching_files.append(existing_file)
                print(f"   🎯 Найден соответствующий файл: {existing_file}")

        if matching_files:
            # Проверяем, есть ли успешные результаты
            error_files = [f for f in matching_files if '_ERROR.txt' in f]
            success_files = [f for f in matching_files if '_ERROR.txt' not in f]

            if success_files:
                print(f"   ✅ Найдены успешные результаты: {len(success_files)} файлов")
                return True  # Есть успешные результаты - пропускаем
            elif error_files:
                print(f"   ⚠️  Найдены только файлы-маркеры ошибок: {len(error_files)} файлов")
                return False  # Файлы с ошибками нуждаются в повторной обработке

    # Резервная логика для файлов не соответствующего формата
    print("   🔄 Файл не соответствует формату вложения или используется резервная логика")
    exact_match_files = [f for f in existing_files if file_stem in f]

    if exact_match_files:
        print(f"   ✅ Найдены файлы с точным совпадением: {len(exact_match_files)}")
        return True

    print("   ❌ Результаты не найдены")
    return False

def test_files():
    """Тестируем на реальных файлах из 2025-07-22"""

    test_files = [
        "20250722_dna-technology_ru_17cb0020_033857_attach_реквизиты ООО",
        "20250722_dna-technology_ru_7fd711e1_033859_attach_КП 8196 от 22.07.2025",
        "20250722_dna-technology_ru_c1a40aee_033901_attach_Счет на оплату _ 8363 от 22.07.2025",
        "20250722_dna-technology_ru_e0bfeeac_033855_attach_О компании ДНК -Технология",
        "20250722_dna-technology_ru_e0bfeeac_033855_attach_DNA-Tech_logo_rus"
    ]

    print("🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ ЛОГИКИ ПРОВЕРКИ СУЩЕСТВУЮЩИХ РЕЗУЛЬТАТОВ")
    print("=" * 70)

    all_correct = True

    for file_stem in test_files:
        result = check_existing_results_fixed(file_stem, "2025-07-22")
        if not result:
            all_correct = False
            print("   ❌ ЭТО ФАЙЛ ДОЛЖЕН БЫТЬ РАСПОЗНАН КАК УЖЕ ОБРАБОТАННЫЙ!")
        print()

    print("=" * 70)
    if all_correct:
        print("✅ УСПЕХ: Все файлы корректно распознаны как уже обработанные!")
        print("🎯 Исправление работает правильно")
        return True
    else:
        print("❌ ПРОВАЛ: Некоторые файлы не распознаны корректно")
        print("🔧 Требуется доработка логики")
        return False

if __name__ == "__main__":
    success = test_files()
    exit(0 if success else 1)
