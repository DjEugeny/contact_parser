#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Исправление дубликатов в Global ID Registry
Удаляет дублирующиеся записи GID, оставляя только первые вхождения
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Добавляем корень проекта в path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def fix_registry_duplicates(registry_path: Path) -> None:
    """Исправление дубликатов в реестре"""
    print("🔧 Исправление дубликатов в Global ID Registry")
    print(f"📁 Путь: {registry_path}")
    print()

    org_file = registry_path / "organizations.jsonl"
    contact_file = registry_path / "contacts.jsonl"

    # Исправляем организации
    if org_file.exists():
        fix_file_duplicates(org_file, "организаций")
    else:
        print("❌ Файл organizations.jsonl не найден")

    # Исправляем контакты
    if contact_file.exists():
        fix_file_duplicates(contact_file, "контактов")
    else:
        print("❌ Файл contacts.jsonl не найден")


def fix_file_duplicates(filepath: Path, entity_name: str) -> None:
    """Исправление дубликатов в одном файле"""
    print(f"📄 Обработка {entity_name}: {filepath.name}")

    if not filepath.exists():
        print(f"  ⏭️  Файл не существует")
        return

    # Читаем все записи
    records = []
    with filepath.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append((line_num, record))
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Ошибка JSON в строке {line_num}: {e}")

    if not records:
        print("  ⏭️  Записей не найдено")
        return

    print(f"  📊 Всего записей: {len(records)}")

    # Находим дубликаты по GID
    gid_to_records: Dict[str, List[tuple]] = {}
    for line_num, record in records:
        gid = record.get("gid")
        if gid:
            if gid not in gid_to_records:
                gid_to_records[gid] = []
            gid_to_records[gid].append((line_num, record))

    # Определяем дубликаты
    duplicates = {gid: recs for gid, recs in gid_to_records.items() if len(recs) > 1}

    if not duplicates:
        print(f"  ✅ Дубликатов {entity_name} не найдено")
        return

    print(f"  ❌ Найдено дубликатов: {len(duplicates)}")

    # Оставляем только первые записи для каждого GID
    unique_records = []
    removed_count = 0

    for line_num, record in records:
        gid = record.get("gid")
        if gid in duplicates:
            # Это дубликат - оставляем только первую запись
            if (line_num, record) == duplicates[gid][0]:
                unique_records.append((line_num, record))
            else:
                removed_count += 1
        else:
            # Это уникальная запись
            unique_records.append((line_num, record))

    print(f"  📊 Уникальных записей: {len(unique_records)}")
    print(f"  🗑️  Удалено дубликатов: {removed_count}")

    # Создаём резервную копию
    backup_file = filepath.with_suffix('.jsonl.backup')
    import shutil
    shutil.copy2(filepath, backup_file)
    print(f"  💾 Создана резервная копия: {backup_file.name}")

    # Перезаписываем файл
    with filepath.open('w', encoding='utf-8') as f:
        for line_num, record in unique_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"  ✅ Файл исправлен")


def main():
    """Основная функция"""
    registry_path = PROJECT_ROOT / "src" / "registry"
    fix_registry_duplicates(registry_path)


if __name__ == "__main__":
    main()