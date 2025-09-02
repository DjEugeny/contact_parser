#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🗑️ СКРИПТ ДЛЯ УДАЛЕНИЯ ДУБЛИРОВАННЫХ ФАЙЛОВ В OCR ПРОЦЕССОРЕ
Удаляет старые дублированные файлы, оставляя только самые свежие версии
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set

def parse_filename_correctly(filename: str) -> tuple:
    """Корректно парсит имя файла и извлекает ключевые компоненты"""

    # Исправленный паттерн: {date}_{domain}_{thread_id}_{timestamp}_attach_{original_filename}.txt
    # Пример: 20250721_mail_ru_3e6a56b8_033842_attach_IMG-20250721-WA0003.txt

    pattern = r'(\d{8})_(.+?)_([^_]+)_([^_]+)_attach_(.+)\.txt$'
    match = re.match(pattern, filename)

    if match:
        date, domain, thread_id, timestamp, original_name = match.groups()

        # Создаем ключ на основе оригинального имени файла (без учета thread_id и timestamp)
        # Это позволит правильно группировать дубликаты
        clean_key = f"{date}_{domain}_{original_name}"

        return {
            'full_name': filename,
            'date': date,
            'domain': domain,
            'thread_id': thread_id,
            'timestamp': timestamp,
            'attach_type': 'attach',
            'original_name': original_name,
            'key': clean_key,
            'file_path': None  # Будет заполнено позже
        }

    return None

def analyze_and_remove_duplicates(folder_path: Path, dry_run: bool = True) -> Dict:
    """Анализирует и удаляет дублированные файлы"""

    if not folder_path.exists():
        return {'error': f'Папка {folder_path} не существует'}

    files = list(folder_path.glob('*.txt'))
    parsed_files = []
    duplicates = defaultdict(list)

    # Парсим все файлы
    for file_path in files:
        parsed = parse_filename_correctly(file_path.name)
        if parsed:
            parsed['file_path'] = file_path
            parsed_files.append(parsed)
            duplicates[parsed['key']].append(parsed)

    # Находим только реальные дубликаты
    real_duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}

    files_to_remove = []
    files_to_keep = []

    # Для каждой группы дубликатов определяем, что удалить
    for key, files in real_duplicates.items():
        # Сортируем по времени модификации файла (новые сначала)
        sorted_files = sorted(files, key=lambda x: x['file_path'].stat().st_mtime, reverse=True)

        # Оставляем первый (самый новый), удаляем остальные
        files_to_keep.append(sorted_files[0]['full_name'])
        for file_info in sorted_files[1:]:
            files_to_remove.append(file_info)

    result = {
        'total_files': len(files),
        'parsed_files': len(parsed_files),
        'duplicate_groups': len(real_duplicates),
        'files_to_remove': files_to_remove,
        'files_to_keep': files_to_keep,
        'dry_run': dry_run
    }

    # Выполняем удаление, если не dry_run
    if not dry_run and files_to_remove:
        print("\n🗑️  ВЫПОЛНЯЮ УДАЛЕНИЕ ФАЙЛОВ...")
        removed_count = 0
        for file_info in files_to_remove:
            file_path = file_info['file_path']
            try:
                os.remove(file_path)
                print(f"  ✅ Удален: {file_info['full_name']}")
                removed_count += 1
            except Exception as e:
                print(f"  ❌ Ошибка удаления {file_info['full_name']}: {e}")

        result['removed_count'] = removed_count

    return result

def process_problematic_folders(dry_run: bool = True):
    """Обрабатывает проблемные папки"""

    print("🗑️ УДАЛЕНИЕ ДУБЛИРОВАННЫХ ФАЙЛОВ В OCR ПРОЦЕССОРЕ")
    print("=" * 70)

    if dry_run:
        print("🔍 РЕЖИМ АНАЛИЗА (файлы не будут удалены)")
    else:
        print("⚠️  РЕЖИМ УДАЛЕНИЯ (файлы будут удалены!)")

    base_path = Path("data/final_results/texts")
    problematic_dates = ["2025-07-21", "2025-07-14", "2025-07-02"]

    total_removed = 0
    total_duplicates = 0

    for date in problematic_dates:
        folder_path = base_path / date
        print(f"\n📁 ОБРАБОТКА ПАПКИ: {date}")
        print("-" * 50)

        result = analyze_and_remove_duplicates(folder_path, dry_run)

        if 'error' in result:
            print(f"❌ {result['error']}")
            continue

        print(f"📊 Всего файлов: {result['total_files']}")
        print(f"📄 Распарсено файлов: {result['parsed_files']}")
        print(f"🔄 Групп дубликатов: {result['duplicate_groups']}")

        if result['duplicate_groups'] > 0:
            print("\n📋 ФАЙЛЫ ДЛЯ УДАЛЕНИЯ:")
            for file_info in result['files_to_remove']:
                print(f"  ❌ {file_info['full_name']}")

            print("\n✅ ФАЙЛЫ ДЛЯ СОХРАНЕНИЯ:")
            for file_name in result['files_to_keep']:
                print(f"  💾 {file_name}")

            if not dry_run:
                print(f"🗑️  Удалено файлов: {result.get('removed_count', 0)}")

            total_duplicates += result['duplicate_groups']
            total_removed += len(result['files_to_remove'])
        else:
            print("✅ Дубликатов не найдено")

    print(f"\n" + "=" * 70)
    print("📊 ИТОГИ ОБРАБОТКИ:")
    print(f"   🔄 Всего групп дубликатов: {total_duplicates}")
    print(f"   🗑️  Всего файлов для удаления: {total_removed}")

    if dry_run:
        print("\n💡 Для выполнения удаления запустите скрипт с параметром:")
        print("   python remove_duplicates.py --execute")

    return total_duplicates, total_removed

def main():
    """Главная функция"""
    import sys

    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        dry_run = False

    process_problematic_folders(dry_run)

if __name__ == '__main__':
    main()
