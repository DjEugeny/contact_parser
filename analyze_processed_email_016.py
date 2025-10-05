#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ уже обработанного письма 016
Проверяем, почему обогащение локации не сработало
"""

import json
import sys
from pathlib import Path

# Добавляем пути
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

print("="*80)
print("🔍 АНАЛИЗ ОБРАБОТАННОГО ПИСЬМА 016")
print("="*80)

# Читаем обработанный файл
processed_file = Path("data/llm_results/2025-07-29/email_016_20250729_20250729_dna_technology_ru_6360137e_20251005_001450_001639_processed.json")

if not processed_file.exists():
    print(f"❌ Файл не найден: {processed_file}")
    sys.exit(1)

with open(processed_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

processed_result = data.get('processed_result', {})

# Проверяем организации
print("\n🏢 Организации:")
organizations = processed_result.get('organizations', [])
for org in organizations:
    print(f"  - {org.get('name')}: city={org.get('city')}")

# Проверяем метаданные
print("\n📊 Метаданные обогащения:")
metadata = processed_result.get('postprocessing_metadata', {})
enrichment = metadata.get('enrichment', {})

for key, value in enrichment.items():
    if isinstance(value, dict):
        print(f"  {key}: {len(value)} записей")
    else:
        print(f"  {key}: {value}")

# Детально проверяем org_location_from_attachments
location_enrichment = enrichment.get('org_location_from_attachments', {})
print(f"\n🔍 Детали org_location_from_attachments:")
if location_enrichment:
    print(json.dumps(location_enrichment, indent=2, ensure_ascii=False))
else:
    print("  ❌ ПУСТО!")

# Теперь попробуем вручную запустить обогащение
print("\n" + "="*80)
print("🧪 РУЧНОЙ ТЕСТ ОБОГАЩЕНИЯ")
print("="*80)

try:
    from postprocessing.attachment_evidence_extractor import AttachmentEvidenceExtractor
    from postprocessing.org_location_enrichment import OrgLocationEnrichment
    print("✅ Модули импортированы")
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Читаем исходное письмо
email_file = Path("data/emails/2025-07-29/email_016_20250729_20250729_dna-technology_ru_6360137e.json")
with open(email_file, 'r', encoding='utf-8') as f:
    email_data = json.load(f)

# Подготавливаем email_metadata
email_metadata = {
    'from': email_data.get('from', ''),
    'to': email_data.get('to', ''),
    'cc': email_data.get('cc', ''),
    'subject': email_data.get('subject', ''),
    'date': email_data.get('date', ''),
    'thread_id': email_data.get('thread_id', ''),
    'has_attachments': len(email_data.get('attachments', [])) > 0,
    'attachments_count': len(email_data.get('attachments', [])),
    'attachments': email_data.get('attachments', [])
}

print(f"\n📧 email_metadata:")
print(f"  Вложений: {len(email_metadata['attachments'])}")

# Извлекаем доказательства
print(f"\n🔍 Извлечение доказательств...")
extractor = AttachmentEvidenceExtractor()
evidence_list = extractor.extract(email_metadata)

print(f"✅ Найдено доказательств: {len(evidence_list)}")

for i, evidence in enumerate(evidence_list, 1):
    print(f"\n  Доказательство {i}:")
    print(f"    Организация: {evidence.matched_name}")
    print(f"    Нормализованное: {evidence.org_name_norm}")
    print(f"    Город: {evidence.city}")
    print(f"    Адрес: {evidence.address[:50] + '...' if evidence.address and len(evidence.address) > 50 else evidence.address}")
    print(f"    Уверенность: {evidence.confidence}")
    print(f"    Источник: {evidence.source.get('filename')}")

# Применяем обогащение
if evidence_list:
    print(f"\n🔍 Применение обогащения...")
    
    # Преобразуем организации в нужный формат
    organizations_dict = {}
    for org in organizations:
        org_id = org.get('organization_id')
        if org_id:
            organizations_dict[org_id] = org.copy()
    
    print(f"  Организаций для обогащения: {len(organizations_dict)}")
    
    enrichment_service = OrgLocationEnrichment()
    postprocessing_metadata = {}
    
    enriched_organizations = enrichment_service.enrich_organizations(
        organizations_dict, evidence_list, postprocessing_metadata
    )
    
    print(f"✅ Обогащение завершено")
    
    # Проверяем результат
    print(f"\n📊 Результат обогащения:")
    for org_id, org in enriched_organizations.items():
        if 'МИЛЛАБ' in org.get('name', ''):
            print(f"\n  Организация МИЛЛАБ (ID={org_id}):")
            print(f"    city: {org.get('city')}")
            print(f"    address: {org.get('address')}")
            
            if org.get('city') == 'Москва':
                print(f"    ✅ УСПЕХ: Город Москва добавлен!")
            else:
                print(f"    ❌ ПРОБЛЕМА: Город не добавлен")
    
    # Проверяем метаданные
    if postprocessing_metadata.get('location_evidence'):
        print(f"\n📊 Метаданные обогащения:")
        print(json.dumps(postprocessing_metadata['location_evidence'], indent=2, ensure_ascii=False))
else:
    print(f"\n❌ Доказательства не найдены - обогащение невозможно")

print("\n" + "="*80)
print("📝 АНАЛИЗ ЗАВЕРШЕН")
print("="*80)
