#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка, что изменения TASK-008B применились в коде
"""

import re
from pathlib import Path


def check_file_contains(file_path, patterns, description):
    """Проверяет, содержит ли файл все указанные паттерны"""
    print(f"\n{'='*80}")
    print(f"Проверка: {description}")
    print(f"Файл: {file_path}")
    print(f"{'='*80}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_found = True
        for pattern_desc, pattern in patterns:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                print(f"✅ Найдено: {pattern_desc}")
            else:
                print(f"❌ НЕ найдено: {pattern_desc}")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return False


def main():
    """Проверка всех изменений"""
    print("\n" + "="*80)
    print("ПРОВЕРКА ИЗМЕНЕНИЙ TASK-008B")
    print("="*80)
    
    all_checks_passed = True
    
    # Проверка 1: data_enricher.py
    patterns_enricher = [
        ("TASK-008B комментарий", r"TASK-008B.*НЕ применяет обогащение локации"),
        ("Функция _has_value", r"def _has_value\(val\):"),
        ("Проверка has_personal_location", r"has_personal_location\s*=.*_has_value"),
        ("Логирование вызова метода", r"TASK-008B.*_enrich_location_from_organization вызван"),
        ("Проверка и return", r"if not has_personal_location:.*return contact"),
    ]
    
    result1 = check_file_contains(
        "src/postprocessing/data_enricher.py",
        patterns_enricher,
        "data_enricher.py - предотвращение backfill"
    )
    all_checks_passed = all_checks_passed and result1
    
    # Проверка 2: postprocessor.py - _backfill_contact_city_address
    patterns_postprocessor = [
        ("TASK-008B комментарий в backfill", r"TASK-008B.*Проверяем, был ли контакт уже обработан"),
        ("Проверка has_personal_location", r"has_personal_location\s*=.*self\._has_value"),
        ("allow_backfill", r"allow_backfill\s*=\s*has_personal_location"),
        ("Логирование вызова backfill", r"TASK-008B.*_backfill_contact_city_address вызван"),
        ("Условие if organization and allow_backfill", r"if organization and allow_backfill:"),
    ]
    
    result2 = check_file_contains(
        "src/postprocessing/postprocessor.py",
        patterns_postprocessor,
        "postprocessor.py - _backfill_contact_city_address"
    )
    all_checks_passed = all_checks_passed and result2
    
    # Проверка 3: postprocessor.py - _apply_contact_location_safety
    patterns_location_safety = [
        ("Метод _apply_contact_location_safety", r"def _apply_contact_location_safety"),
        ("Логирование вызова", r"TASK-008B.*_apply_contact_location_safety вызван"),
        ("Вызов extract_contact_location_evidence", r"extract_contact_location_evidence"),
        ("Вызов apply_contact_location", r"apply_contact_location"),
    ]
    
    result3 = check_file_contains(
        "src/postprocessing/postprocessor.py",
        patterns_location_safety,
        "postprocessor.py - _apply_contact_location_safety"
    )
    all_checks_passed = all_checks_passed and result3
    
    # Проверка 4: contact_location_safety.py существует
    patterns_module = [
        ("Класс ContactLocationSafety", r"class ContactLocationSafety"),
        ("Метод extract_contact_location_evidence", r"def extract_contact_location_evidence"),
        ("Метод apply_contact_location", r"def apply_contact_location"),
        ("Метод is_hq_block", r"def is_hq_block"),
    ]
    
    result4 = check_file_contains(
        "src/postprocessing/contact_location_safety.py",
        patterns_module,
        "contact_location_safety.py - основной модуль"
    )
    all_checks_passed = all_checks_passed and result4
    
    # Итоговый результат
    print("\n" + "="*80)
    if all_checks_passed:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("="*80)
        print("\n📋 Изменения TASK-008B применены корректно:")
        print("  1. ✅ data_enricher.py - добавлена проверка персональной локации")
        print("  2. ✅ postprocessor.py - модифицирован _backfill_contact_city_address")
        print("  3. ✅ postprocessor.py - добавлен _apply_contact_location_safety")
        print("  4. ✅ contact_location_safety.py - создан новый модуль")
        print("\n⚠️  ВАЖНО: Необходимо перезапустить Python процесс для применения изменений!")
        print("="*80)
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ ПРОВАЛЕНЫ!")
        print("="*80)
        print("\n⚠️  Возможные причины:")
        print("  • Файлы не были сохранены")
        print("  • Изменения были отменены")
        print("  • Проблемы с кодировкой файлов")
        print("="*80)
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
