#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностический скрипт для анализа проблем с обработкой файлов по нескольким датам
Анализирует расхождения между файлами во вложениях и результатах
"""

import os
import re
from pathlib import Path
from datetime import datetime
from src.file_utils import normalize_filename

# Функция normalize_filename импортирована из src.file_utils

def analyze_date_folder(date_str):
    """Анализ папки для конкретной даты"""
    print(f"\n{'='*80}")
    print(f"АНАЛИЗ ДАТЫ: {date_str}")
    print(f"{'='*80}")
    
    attachments_path = f"/Users/evgenyzach/contact_parser/data/attachments/{date_str}"
    results_path = f"/Users/evgenyzach/contact_parser/data/final_results/texts/{date_str}"
    
    # Проверяем существование папок
    attachments_exists = os.path.exists(attachments_path)
    results_exists = os.path.exists(results_path)
    
    print(f"📁 Папка вложений: {attachments_path}")
    print(f"   Существует: {'✅' if attachments_exists else '❌'}")
    
    print(f"📁 Папка результатов: {results_path}")
    print(f"   Существует: {'✅' if results_exists else '❌'}")
    
    if not attachments_exists:
        print("⚠️  ПРОБЛЕМА: Папка вложений не существует!")
        return
    
    # Получаем список файлов во вложениях
    attachment_files = []
    for ext in ['*.pdf', '*.docx', '*.doc']:
        attachment_files.extend(Path(attachments_path).glob(ext))
    
    attachment_names = [f.name for f in attachment_files]
    attachment_count = len(attachment_names)
    
    print(f"\n📊 СТАТИСТИКА:")
    print(f"   Файлов во вложениях: {attachment_count}")
    
    if results_exists:
        result_files = list(Path(results_path).glob('*.txt'))
        result_count = len(result_files)
        print(f"   Файлов в результатах: {result_count}")
        print(f"   Разница: {attachment_count - result_count}")
    else:
        result_files = []
        result_count = 0
        print(f"   Файлов в результатах: 0 (папка не существует)")
        print(f"   Разница: {attachment_count}")
    
    # Анализ дубликатов по нормализованным именам
    normalized_map = {}
    for filename in attachment_names:
        normalized = normalize_filename(filename)
        if normalized not in normalized_map:
            normalized_map[normalized] = []
        normalized_map[normalized].append(filename)
    
    duplicates = {k: v for k, v in normalized_map.items() if len(v) > 1}
    unique_normalized_count = len(normalized_map)
    
    print(f"   Уникальных нормализованных имен: {unique_normalized_count}")
    print(f"   Групп дубликатов: {len(duplicates)}")
    
    # Детальная информация о файлах
    print(f"\n📋 СПИСОК ФАЙЛОВ ВО ВЛОЖЕНИЯХ:")
    for i, filename in enumerate(attachment_names, 1):
        normalized = normalize_filename(filename)
        is_duplicate = len(normalized_map[normalized]) > 1
        duplicate_marker = " 🔄 [ДУБЛИКАТ]" if is_duplicate else ""
        print(f"   {i:2d}. {filename}{duplicate_marker}")
        print(f"       Нормализованное: {normalized}")
    
    if duplicates:
        print(f"\n🔄 ГРУППЫ ДУБЛИКАТОВ:")
        for normalized, files in duplicates.items():
            print(f"   Нормализованное имя: {normalized}")
            for file in files:
                print(f"     - {file}")
    
    # Анализ результатов
    if results_exists and result_files:
        print(f"\n📄 ФАЙЛЫ РЕЗУЛЬТАТОВ:")
        result_names = [f.stem for f in result_files]
        for i, name in enumerate(result_names, 1):
            print(f"   {i:2d}. {name}.txt")
        
        # Поиск необработанных файлов
        processed_normalized = set()
        for result_name in result_names:
            # Пытаемся найти соответствующий исходный файл
            for normalized, original_files in normalized_map.items():
                if normalized in result_name or result_name in normalized:
                    processed_normalized.add(normalized)
                    break
        
        unprocessed_normalized = set(normalized_map.keys()) - processed_normalized
        
        if unprocessed_normalized:
            print(f"\n❌ НЕОБРАБОТАННЫЕ ФАЙЛЫ (по нормализованным именам):")
            for normalized in unprocessed_normalized:
                original_files = normalized_map[normalized]
                print(f"   Нормализованное: {normalized}")
                for file in original_files:
                    print(f"     - {file}")
        else:
            print(f"\n✅ Все уникальные файлы обработаны")
    
    # Рекомендации
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    if attachment_count == 0:
        print(f"   - Папка вложений пуста")
    elif not results_exists:
        print(f"   - Необходимо запустить обработку для этой даты")
    elif result_count == 0:
        print(f"   - Папка результатов пуста, возможны ошибки обработки")
    elif result_count < unique_normalized_count:
        print(f"   - Не все уникальные файлы обработаны")
        print(f"   - Проверить логи обработки на ошибки")
    elif duplicates:
        print(f"   - Обнаружены дубликаты файлов")
        print(f"   - OCR корректно обрабатывает их как один файл")
    else:
        print(f"   - Обработка выглядит корректной")

def main():
    """Основная функция анализа"""
    print("🔍 ДИАГНОСТИКА ПРОБЛЕМ ОБРАБОТКИ ФАЙЛОВ")
    print(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Список проблемных дат из сообщения пользователя
    problem_dates = [
        "2025-08-25",  # 10 файлов -> 8 результатов
        "2025-07-15",  # 7 файлов -> 6 результатов  
        "2025-08-15",  # 7 файлов -> 6 результатов
        "2025-08-20",  # 9 файлов, 1 с ошибками
        "2025-07-11",  # 1 файл обработан, но не сохранен
    ]
    
    for date_str in problem_dates:
        analyze_date_folder(date_str)
    
    print(f"\n{'='*80}")
    print("ОБЩИЕ ВЫВОДЫ:")
    print("1. Проверьте логи OCR процессора на ошибки")
    print("2. Убедитесь в корректности нормализации имен файлов")
    print("3. Проверьте права доступа к папкам результатов")
    print("4. Рассмотрите улучшение диагностики в реальном времени")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()