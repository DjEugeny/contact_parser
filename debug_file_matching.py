#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Скрипт для диагностики проблем с подсчетом и сопоставлением файлов
"""

import re
from pathlib import Path
from typing import List, Dict, Set
from src.file_utils import normalize_filename

# Функция normalize_filename импортирована из src.file_utils

def analyze_file_matching(date: str):
    """📊 Анализ сопоставления файлов для указанной даты"""
    
    attachments_dir = Path(f"/Users/evgenyzach/contact_parser/data/attachments/{date}")
    results_dir = Path(f"/Users/evgenyzach/contact_parser/data/final_results/texts/{date}")
    
    print(f"🔍 Анализ файлов для даты: {date}")
    print("=" * 60)
    
    # Получаем список файлов в attachments
    if not attachments_dir.exists():
        print(f"❌ Папка {attachments_dir} не существует")
        return
    
    attachment_files = []
    for ext in ['*.pdf', '*.docx', '*.doc', '*.xlsx', '*.xls', '*.png', '*.jpg', '*.jpeg', '*.tiff']:
        attachment_files.extend(attachments_dir.glob(ext))
    
    print(f"📁 Файлы в attachments ({len(attachment_files)}):")
    for i, file_path in enumerate(attachment_files, 1):
        print(f"  {i:2d}. {file_path.name}")
    
    print()
    
    # Получаем список результатов
    result_files = []
    if results_dir.exists():
        result_files = list(results_dir.glob('*.txt'))
    
    print(f"📄 Файлы результатов ({len(result_files)}):")
    for i, file_path in enumerate(result_files, 1):
        # Извлекаем оригинальное имя из результата
        result_name = file_path.stem.split('___')[0]
        print(f"  {i:2d}. {result_name} -> {file_path.name}")
    
    print()
    print("🔍 Детальный анализ сопоставления:")
    print("-" * 60)
    
    # Создаем множества для сравнения
    processed_stems = set()
    processed_normalized = set()
    
    for result_file in result_files:
        result_stem = result_file.stem.split('___')[0]
        processed_stems.add(result_stem)
        processed_normalized.add(normalize_filename(result_stem))
    
    unprocessed_files = []
    
    for attachment_file in attachment_files:
        file_stem = attachment_file.stem
        normalized_stem = normalize_filename(file_stem)
        
        # Проверяем точное совпадение
        exact_match = file_stem in processed_stems
        
        # Проверяем нормализованное совпадение
        normalized_match = normalized_stem in processed_normalized
        
        status = "✅ Обработан" if (exact_match or normalized_match) else "❌ НЕ обработан"
        
        print(f"  {status}: {attachment_file.name}")
        print(f"    Исходное имя: '{file_stem}'")
        print(f"    Нормализованное: '{normalized_stem}'")
        print(f"    Точное совпадение: {exact_match}")
        print(f"    Нормализованное совпадение: {normalized_match}")
        
        if not (exact_match or normalized_match):
            unprocessed_files.append(attachment_file)
        
        print()
    
    print("📊 Итоговая статистика:")
    print(f"  Всего файлов в attachments: {len(attachment_files)}")
    print(f"  Обработанных файлов: {len(result_files)}")
    print(f"  Необработанных файлов: {len(unprocessed_files)}")
    
    if unprocessed_files:
        print("\n❌ Необработанные файлы:")
        for i, file_path in enumerate(unprocessed_files, 1):
            print(f"  {i}. {file_path.name}")
    
    print()
    
    # Проверяем возможные дубликаты в нормализованных именах
    print("🔍 Анализ возможных дубликатов:")
    print("-" * 40)
    
    normalized_groups = {}
    for attachment_file in attachment_files:
        normalized = normalize_filename(attachment_file.stem)
        if normalized not in normalized_groups:
            normalized_groups[normalized] = []
        normalized_groups[normalized].append(attachment_file.name)
    
    for normalized, files in normalized_groups.items():
        if len(files) > 1:
            print(f"  Группа '{normalized}':")
            for file in files:
                print(f"    - {file}")
            print()

if __name__ == "__main__":
    # Анализируем проблемную дату
    analyze_file_matching("2025-07-29")