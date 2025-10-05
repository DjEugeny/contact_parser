#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обработки тестовых писем 016 и 017 (TASK-008B)
"""

import sys
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

print("="*80)
print("ОБРАБОТКА ТЕСТОВЫХ ПИСЕМ 016 и 017 (TASK-008B)")
print("="*80)
print()

# Импортируем необходимые модули
try:
    from src.api_pipeline_validator import APIPipelineValidator
    from argparse import Namespace
    print("✅ Модули импортированы успешно")
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# Проверяем, что изменения применены
print("\n🔍 Проверка изменений TASK-008B...")
try:
    from src.postprocessing.contact_location_safety import ContactLocationSafety
    from src.postprocessing.postprocessor import PostProcessor
    from src.postprocessing.data_enricher import DataEnricher
    
    # Проверяем наличие ключевых методов
    assert hasattr(ContactLocationSafety, 'extract_contact_location_evidence')
    assert hasattr(ContactLocationSafety, 'apply_contact_location')
    
    print("✅ Модуль contact_location_safety загружен")
    print("✅ Все изменения TASK-008B применены")
except Exception as e:
    print(f"❌ Ошибка проверки: {e}")
    print("⚠️  Возможно, нужно перезапустить Python интерпретатор")
    sys.exit(1)

print("\n" + "="*80)
print("ЗАПУСК ОБРАБОТКИ")
print("="*80)
print()
print("📋 Будут обработаны письма:")
print("  • email_016_20250729_20250729_dna-technology_ru_6360137e.json")
print("  • email_017_20250729_20250729_dna-technology_ru_ee04f823.json")
print()
print("🔍 После обработки проверьте:")
print("  1. Логи: grep 'TASK-008B' data/logs/*.log")
print("  2. Результаты в data/llm_results/2025-07-29/*_processed.json")
print()

input("Нажмите Enter для продолжения или Ctrl+C для отмены...")

# Создаем аргументы для валидатора
args = Namespace(
    mode="interactive",
    date="2025-07-29",
    count=None,
    start_date=None,
    end_date=None,
    dry_run=False
)

try:
    print("\n🚀 Инициализация валидатора...")
    validator = APIPipelineValidator(args)
    
    print("✅ Валидатор инициализирован")
    print()
    print("="*80)
    print("⚠️  ВАЖНО: Используйте интерактивное меню для выбора писем 016 и 017")
    print("="*80)
    print()
    
    # Запускаем интерактивное меню
    from src.validator_menu import main_menu
    main_menu(validator)
    
except KeyboardInterrupt:
    print("\n\n❌ Обработка отменена пользователем")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
