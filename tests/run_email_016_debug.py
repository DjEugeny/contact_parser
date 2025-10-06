#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск обработки письма 016 с DEBUG-логированием
"""

import sys
import logging
import json
from pathlib import Path

# Настройка детального логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('email_016_debug.log', mode='w', encoding='utf-8')
    ]
)

# Добавляем путь к корню проекта
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("="*80)
print("🚀 ЗАПУСК ОБРАБОТКИ ПИСЬМА 016 С DEBUG-ЛОГИРОВАНИЕМ")
print("="*80)

try:
    from src.integrated_llm_processor import IntegratedLLMProcessor
    print("✅ IntegratedLLMProcessor импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта IntegratedLLMProcessor: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Создаем процессор
print("\n📋 Создание процессора...")
processor = IntegratedLLMProcessor(test_mode=False)
print("✅ Процессор создан")

# Путь к письму
email_file = "data/emails/2025-07-29/email_016_20250729_20250729_dna-technology_ru_6360137e.json"
print(f"\n📧 Обработка письма: {email_file}")

if not Path(email_file).exists():
    print(f"❌ Файл не найден: {email_file}")
    sys.exit(1)

# Обрабатываем письмо
print("\n" + "="*80)
print("🔄 НАЧАЛО ОБРАБОТКИ")
print("="*80 + "\n")

try:
    result = processor.process_single_email(email_file)
    print("\n" + "="*80)
    print("✅ ОБРАБОТКА ЗАВЕРШЕНА")
    print("="*80)
except Exception as e:
    print(f"\n❌ Ошибка при обработке: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Анализ результата
print("\n" + "="*80)
print("📊 АНАЛИЗ РЕЗУЛЬТАТА")
print("="*80)

processed_result = result.get('processed_result', {})

# Проверяем организации
print("\n🏢 Организации:")
organizations = processed_result.get('organizations', [])
for org in organizations:
    name = org.get('name', 'Unknown')
    city = org.get('city')
    address = org.get('address')
    print(f"  - {name}")
    print(f"    city: {city}")
    print(f"    address: {address[:50] + '...' if address and len(address) > 50 else address}")

# Ищем МИЛЛАБ
millab_org = None
for org in organizations:
    if 'МИЛЛАБ' in org.get('name', ''):
        millab_org = org
        break

if millab_org:
    print(f"\n🎯 Организация МИЛЛАБ:")
    print(f"  city: {millab_org.get('city')}")
    print(f"  address: {millab_org.get('address')}")
    
    if millab_org.get('city') == 'Москва':
        print(f"  ✅ УСПЕХ: Город Москва найден!")
    else:
        print(f"  ❌ ПРОБЛЕМА: Город не найден или неправильный")
else:
    print(f"\n❌ Организация МИЛЛАБ не найдена")

# Проверяем метаданные обогащения
print(f"\n📊 Метаданные постобработки:")
metadata = processed_result.get('postprocessing_metadata', {})
enrichment = metadata.get('enrichment', {})

print(f"  ИНН обогащение: {len(enrichment.get('org_inn', {}))}")
print(f"  Email обогащение: {len(enrichment.get('org_email_enrichment', {}))}")

location_enrichment = enrichment.get('org_location_from_attachments', {})
print(f"  Локация из вложений: {len(location_enrichment)}")

if location_enrichment:
    print(f"\n✅ Метаданные обогащения локации:")
    print(json.dumps(location_enrichment, indent=2, ensure_ascii=False))
else:
    print(f"\n❌ Метаданные обогащения локации ПУСТЫ!")
    print(f"   Проверьте логи выше на наличие сообщений:")
    print(f"   - '🔍 DEBUG: email_data type:'")
    print(f"   - '🔍 Анализируем ВСЕ X вложений'")
    print(f"   - '📄 Обрабатываем вложение:'")

print("\n" + "="*80)
print("📝 Логи сохранены в: email_016_debug.log")
print("="*80)
