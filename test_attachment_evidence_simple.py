#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест для TASK-008A без сложных импортов
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.append(str(Path(__file__).parent / "src"))

# Тестируем AttachmentEvidenceExtractor отдельно
try:
    from postprocessing.attachment_evidence_extractor import AttachmentEvidenceExtractor
    
    print("✅ AttachmentEvidenceExtractor импортирован успешно")
    
    # Тестовые данные
    email_data = {
        'attachments': [{
            'filename': 'Ком.пред.14.03.2025_для_Москва_Компания_МИЛЛАБ_для_Абакан_ЦГиЭ.txt',
            'text_content': '''
            ООО "МИЛЛАБ"
            Юридический адрес: 117105, г. Москва, Варшавское шоссе, д. 17
            ИНН: 7728123456
            ОГРН: 1027739123456
            
            Коммерческое предложение
            Поставка медицинского оборудования
            ''',
            'mime': 'text/plain'
        }]
    }
    
    # Создаем экстрактор и тестируем
    extractor = AttachmentEvidenceExtractor()
    evidence_list = extractor.extract(email_data)
    
    print(f"📎 Найдено {len(evidence_list)} доказательств локации")
    
    for evidence in evidence_list:
        print(f"  Организация: {evidence.matched_name}")
        print(f"  Нормализованное: {evidence.org_name_norm}")
        print(f"  Город: {evidence.city}")
        print(f"  Адрес: {evidence.address}")
        print(f"  Уверенность: {evidence.confidence}")
        print(f"  Источник: {evidence.source.get('filename', 'unknown')}")
        print()
    
    # Проверяем ключевые результаты
    if evidence_list:
        millab_evidence = None
        for evidence in evidence_list:
            if 'миллаб' in evidence.org_name_norm.lower():
                millab_evidence = evidence
                break
        
        if millab_evidence:
            print("✅ ТЕСТ ПРОЙДЕН: Найдено доказательство для МИЛЛАБ")
            if millab_evidence.city == "Москва":
                print("✅ ТЕСТ ПРОЙДЕН: Город Москва извлечен корректно")
            else:
                print(f"❌ ТЕСТ НЕ ПРОЙДЕН: Ожидался город Москва, получен {millab_evidence.city}")
            
            if "117105" in (millab_evidence.address or ""):
                print("✅ ТЕСТ ПРОЙДЕН: Адрес с индексом 117105 извлечен корректно")
            else:
                print(f"❌ ТЕСТ НЕ ПРОЙДЕН: Адрес не содержит 117105: {millab_evidence.address}")
        else:
            print("❌ ТЕСТ НЕ ПРОЙДЕН: Не найдено доказательство для МИЛЛАБ")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Не найдено ни одного доказательства")

except ImportError as e:
    print(f"❌ Ошибка импорта AttachmentEvidenceExtractor: {e}")

# Тестируем OrgLocationEnrichment отдельно
try:
    from postprocessing.org_location_enrichment import OrgLocationEnrichment, LocationEvidence
    
    print("\n✅ OrgLocationEnrichment импортирован успешно")
    
    # Тестовые данные
    organizations = {
        1: {
            'name': 'ООО "МИЛЛАБ"',
            'city': None,
            'address': None
        }
    }
    
    evidence_list = [
        LocationEvidence(
            org_name_norm='миллаб',
            matched_name='ООО "МИЛЛАБ"',
            city='Москва',
            address='117105, г. Москва, Варшавское шоссе, д. 17',
            confidence=0.9,
            source={
                'type': 'attachment',
                'filename': 'КП_МИЛЛАБ.txt',
                'snippet': 'Юридический адрес: 117105, г. Москва...'
            }
        )
    ]
    
    # Создаем обогащение и тестируем
    enrichment = OrgLocationEnrichment()
    metadata = {}
    
    enriched_orgs = enrichment.enrich_organizations(
        organizations, evidence_list, metadata
    )
    
    print(f"🏢 Обогащено {len(enriched_orgs)} организаций")
    
    # Проверяем результат
    millab_org = enriched_orgs.get(1)
    if millab_org:
        print(f"  Организация: {millab_org['name']}")
        print(f"  Город: {millab_org.get('city', 'не указан')}")
        print(f"  Адрес: {millab_org.get('address', 'не указан')}")
        
        if millab_org.get('city') == 'Москва':
            print("✅ ТЕСТ ПРОЙДЕН: Организация МИЛЛАБ получила город Москва")
        else:
            print(f"❌ ТЕСТ НЕ ПРОЙДЕН: Ожидался город Москва, получен {millab_org.get('city')}")
        
        if '117105' in (millab_org.get('address') or ''):
            print("✅ ТЕСТ ПРОЙДЕН: Организация МИЛЛАБ получила адрес с индексом 117105")
        else:
            print(f"❌ ТЕСТ НЕ ПРОЙДЕН: Адрес не содержит 117105: {millab_org.get('address')}")
    
    # Проверяем метаданные
    if 'location_evidence' in metadata and 1 in metadata['location_evidence']:
        evidence_meta = metadata['location_evidence'][1]
        if evidence_meta.applied:
            print("✅ ТЕСТ ПРОЙДЕН: Метаданные показывают что обогащение применено")
        else:
            print("❌ ТЕСТ НЕ ПРОЙДЕН: Метаданные показывают что обогащение не применено")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Метаданные обогащения не найдены")

except ImportError as e:
    print(f"❌ Ошибка импорта OrgLocationEnrichment: {e}")

print("\n🎯 Тестирование TASK-008A завершено")