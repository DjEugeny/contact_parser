#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Переобработка письма 016 с новым кодом обогащения локации
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

print("="*80)
print("🔄 ПЕРЕОБРАБОТКА ПИСЬМА 016")
print("="*80)

# Шаг 1: Сохраняем старый файл
print("\n📦 Шаг 1: Сохранение старого обработанного файла...")
old_file = Path("data/llm_results/2025-07-29/email_016_20250729_20250729_dna_technology_ru_6360137e_20251005_001450_001639_processed.json")

if old_file.exists():
    backup_file = old_file.with_suffix('.json.old')
    shutil.move(str(old_file), str(backup_file))
    print(f"✅ Старый файл сохранен: {backup_file.name}")
else:
    print(f"⚠️ Старый файл не найден: {old_file}")

# Шаг 2: Запускаем обработку
print("\n🚀 Шаг 2: Запуск обработки через api_pipeline_validator...")
print("="*80)

# Добавляем пути
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.api_pipeline_validator import APIPipelineValidator
    from argparse import Namespace
    
    # Создаем аргументы для обработки конкретного письма
    args = Namespace(
        mode="first10",
        date="2025-07-29",
        count=1,
        start_date="email_016_20250729_20250729_dna-technology_ru_6360137e.json",
        end_date=None,
        dry_run=False
    )
    
    # Создаем валидатор и запускаем
    validator = APIPipelineValidator(args)
    validator.run()
    
    print("\n" + "="*80)
    print("✅ ОБРАБОТКА ЗАВЕРШЕНА")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ Ошибка при обработке: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Шаг 3: Проверяем результат
print("\n🔍 Шаг 3: Проверка результата...")
print("="*80)

# Ищем новый обработанный файл
results_dir = Path("data/llm_results/2025-07-29")
processed_files = list(results_dir.glob("email_016_*_processed.json"))

if not processed_files:
    print("❌ Новый обработанный файл не найден!")
    sys.exit(1)

# Берем самый свежий файл
latest_file = max(processed_files, key=lambda p: p.stat().st_mtime)
print(f"📄 Найден файл: {latest_file.name}")

# Читаем и анализируем
with open(latest_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

processed_result = data.get('processed_result', {})

# Проверяем организации
print("\n🏢 Организации:")
organizations = processed_result.get('organizations', [])
millab_org = None

for org in organizations:
    name = org.get('name', 'Unknown')
    city = org.get('city')
    if 'МИЛЛАБ' in name:
        millab_org = org
        print(f"  ✨ {name}")
        print(f"     city: {city}")
        address = org.get('address')
        if address:
            print(f"     address: {address[:50]}...")
        else:
            print(f"     address: None")
    else:
        print(f"  - {name}: city={city}")

# Проверяем метаданные обогащения
print("\n📊 Метаданные обогащения:")
metadata = processed_result.get('postprocessing_metadata', {})
enrichment = metadata.get('enrichment', {})

location_enrichment = enrichment.get('org_location_from_attachments', {})
print(f"  org_location_from_attachments: {len(location_enrichment) if isinstance(location_enrichment, dict) else 'N/A'}")

if location_enrichment:
    print(f"\n✅ Метаданные обогащения локации найдены:")
    print(json.dumps(location_enrichment, indent=2, ensure_ascii=False))
else:
    print(f"\n❌ Метаданные обогащения локации ПУСТЫ!")

# Итоговая проверка
print("\n" + "="*80)
print("🎯 ИТОГОВАЯ ПРОВЕРКА")
print("="*80)

if millab_org:
    if millab_org.get('city') == 'Москва':
        print("✅ УСПЕХ! Организация МИЛЛАБ получила city=Москва из вложения!")
        print("🎉 TASK-008A работает корректно!")
    else:
        print(f"❌ ПРОБЛЕМА: МИЛЛАБ имеет city={millab_org.get('city')}, ожидалась Москва")
        print("🔍 Проверьте логи обработки выше")
else:
    print("❌ ПРОБЛЕМА: Организация МИЛЛАБ не найдена")

print("\n" + "="*80)
