#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладочный тест для проверки обогащения локации
"""

import json
from pathlib import Path

def test_debug_location_enrichment():
    """Отладочный тест обогащения локации"""
    
    print("🔍 Отладка обогащения локации из вложений")
    
    # Читаем обработанный файл
    processed_file = Path("data/llm_results/2025-07-29/email_016_20250729_20250729_dna_technology_ru_6360137e_20251005_001450_001639_processed.json")
    
    if not processed_file.exists():
        print(f"❌ Файл не найден: {processed_file}")
        return
    
    with open(processed_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    processed_result = data.get('processed_result', {})
    
    # Проверяем организации
    print("\n📋 Организации в обработанном файле:")
    organizations = processed_result.get('organizations', [])
    for org in organizations:
        print(f"  - {org.get('name')}: city={org.get('city')}, address={org.get('address')}")
    
    # Проверяем метаданные обогащения
    print("\n📊 Метаданные постобработки:")
    metadata = processed_result.get('postprocessing_metadata', {})
    enrichment = metadata.get('enrichment', {})
    
    print(f"  ИНН обогащение: {len(enrichment.get('org_inn', {}))}")
    print(f"  Email обогащение: {len(enrichment.get('org_email_enrichment', {}))}")
    print(f"  Локация из вложений: {len(enrichment.get('org_location_from_attachments', {}))}")
    
    location_enrichment = enrichment.get('org_location_from_attachments', {})
    if location_enrichment:
        print(f"\n✅ Метаданные обогащения локации найдены:")
        print(json.dumps(location_enrichment, indent=2, ensure_ascii=False))
    else:
        print(f"\n❌ Метаданные обогащения локации ПУСТЫ!")
        print(f"   Это означает, что метод _enrich_organizations_location_from_attachments")
        print(f"   либо не вызывался, либо вернул пустой словарь")
    
    # Проверяем исходный файл письма
    print("\n📧 Проверка исходного файла письма:")
    email_file = Path("data/emails/2025-07-29/email_016_20250729_20250729_dna-technology_ru_6360137e.json")
    
    if email_file.exists():
        with open(email_file, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        attachments = email_data.get('attachments', [])
        print(f"  Всего вложений: {len(attachments)}")
        
        saved_attachments = [a for a in attachments if a.get('status') == 'saved']
        print(f"  Сохраненных вложений: {len(saved_attachments)}")
        
        for att in saved_attachments:
            print(f"    - {att.get('original_filename')}")
            print(f"      saved_filename: {att.get('saved_filename')}")
    else:
        print(f"  ❌ Файл письма не найден: {email_file}")
    
    # Проверяем OCR-текст
    print("\n📄 Проверка OCR-текста:")
    ocr_file = Path("data/final_results/texts/2025-07-29/20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.txt")
    
    if ocr_file.exists():
        print(f"  ✅ OCR-текст найден: {ocr_file.name}")
        with open(ocr_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие ключевых слов
        if 'МИЛЛАБ' in content:
            print(f"  ✅ 'МИЛЛАБ' найден в тексте")
        if 'Москва' in content:
            print(f"  ✅ 'Москва' найден в тексте")
        if 'Компания МИЛЛАБ' in content:
            print(f"  ✅ 'Компания МИЛЛАБ' найден в тексте")
    else:
        print(f"  ❌ OCR-текст не найден: {ocr_file}")
    
    print("\n🎯 Выводы:")
    
    # Проверяем, что МИЛЛАБ не имеет города
    millab_org = None
    for org in organizations:
        if 'МИЛЛАБ' in org.get('name', ''):
            millab_org = org
            break
    
    if millab_org:
        if millab_org.get('city'):
            print(f"  ✅ МИЛЛАБ имеет город: {millab_org.get('city')}")
        else:
            print(f"  ❌ МИЛЛАБ НЕ имеет города")
            print(f"  🔍 Возможные причины:")
            print(f"     1. Метод _enrich_organizations_location_from_attachments не вызывается")
            print(f"     2. AttachmentEvidenceExtractor не находит доказательства")
            print(f"     3. OrgLocationEnrichment не сопоставляет доказательства с организацией")
            print(f"     4. Обогащение не применяется из-за конфигурации")
    else:
        print(f"  ❌ Организация МИЛЛАБ не найдена")

if __name__ == "__main__":
    test_debug_location_enrichment()