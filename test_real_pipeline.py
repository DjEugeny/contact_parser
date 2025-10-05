#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест реального пайплайна с TASK-008A
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from postprocessing.postprocessor import PostProcessor
    
    print("✅ PostProcessor импортирован успешно")
    
    # Тестовые данные - структура как в реальном письме 016
    llm_result = {
        'organizations': [{
            'organization_id': 1,
            'name': 'ДНК-Технология',
            'city': 'Москва',
            'address': '117587, г. Москва, вн. тер. г. муниципальный округ Чертаново Северное, Варшавское шоссе, д. 125Ж, корп. 5, этаж 1, пом. 12'
        }, {
            'organization_id': 2,
            'name': 'МИЛЛАБ',
            'city': None,  # Должно быть обогащено
            'address': None  # Должно быть обогащено
        }],
        'contacts': [{
            'contact_id': 1,
            'name': 'Воронова С.С.',
            'organization_id': 2,
            'email': 'voronova@millab.ru'
        }],
        'interactions': [],
        'summary': {'topic': 'Коммерческое предложение'},
        'key_points': ['Запрос КП'],
        'commercial_offers': []
    }
    
    email_data = {
        'attachments': [{
            'original_filename': 'Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ (ДТпрайм 5М6, ноутбук).pdf',
            'saved_filename': '20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.pdf',
            'file_path': 'data/attachments/2025-07-29/20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.pdf',
            'file_type': 'application/pdf',
            'status': 'saved'
        }]
    }
    
    # Создаем PostProcessor и тестируем
    postprocessor = PostProcessor()
    
    print("🧪 Тестирование PostProcessor с TASK-008A")
    print(f"📋 Исходные данные:")
    print(f"  Организация МИЛЛАБ: city={llm_result['organizations'][1]['city']}, address={llm_result['organizations'][1]['address']}")
    
    # Обрабатываем через PostProcessor
    try:
        result = postprocessor.process_llm_response(llm_result, email_data)
        
        print("✅ Обработка завершена успешно")
        
        # Проверяем результат
        organizations = result.get('organizations', [])
        millab_org = None
        
        for org in organizations:
            if 'МИЛЛАБ' in org.get('name', ''):
                millab_org = org
                break
        
        if millab_org:
            print(f"📋 Результат для организации МИЛЛАБ:")
            print(f"  Название: {millab_org.get('name')}")
            print(f"  Город: {millab_org.get('city')}")
            print(f"  Адрес: {millab_org.get('address')}")
            
            if millab_org.get('city') == 'Москва':
                print("✅ ТЕСТ ПРОЙДЕН: Организация МИЛЛАБ получила город Москва из вложения")
            else:
                print(f"❌ ТЕСТ НЕ ПРОЙДЕН: Ожидался город Москва, получен {millab_org.get('city')}")
        else:
            print("❌ ТЕСТ НЕ ПРОЙДЕН: Организация МИЛЛАБ не найдена")
        
        # Проверяем метаданные
        metadata = result.get('postprocessing_metadata', {})
        enrichment_meta = metadata.get('enrichment', {})
        location_meta = enrichment_meta.get('org_location_from_attachments', {})
        
        if location_meta:
            print(f"📊 Метаданные обогащения:")
            print(f"  Доказательств найдено: {location_meta.get('evidence_count', 0)}")
            print(f"  Организаций обогащено: {location_meta.get('organizations_enriched', 0)}")
            print(f"  Городов добавлено: {location_meta.get('cities_added', 0)}")
            print(f"  Адресов добавлено: {location_meta.get('addresses_added', 0)}")
        else:
            print("❌ Метаданные обогащения не найдены")
            
    except Exception as e:
        print(f"❌ Ошибка при обработке: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")

print("\n🎯 Тестирование завершено")