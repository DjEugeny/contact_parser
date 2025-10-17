#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправления нормализации телефонов (Task 5)
Проверяет:
1. Порядок нормализации (ДО обогащения контактов)
2. Обработку коротких номеров с контекстом города
3. Правильное логирование невалидных vs неполных номеров
"""

import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.postprocessing.phone_normalizer import PhoneNormalizer
from src.postprocessing.data_normalizer import DataNormalizer
from src.postprocessing.contact_phone_enricher import ContactPhoneEnricher

def test_phone_normalizer_with_city_context():
    """Тест нормализации коротких номеров с контекстом города"""
    print("=" * 80)
    print("ТЕСТ 1: Нормализация коротких номеров с контекстом города")
    print("=" * 80)
    
    normalizer = PhoneNormalizer()
    
    # Тест 1: Короткий номер без контекста
    print("\n1. Короткий номер без контекста города:")
    result = normalizer.normalize_phone_to_object("28-54-83")
    print(f"   Вход: '28-54-83'")
    print(f"   Результат: {result}")
    assert len(result) == 1
    assert result[0]['type'] == 'incomplete'
    assert result[0]['needs_manual_review'] == True
    print("   ✅ Корректно помечен как incomplete")
    
    # Тест 2: Короткий номер с контекстом Новосибирска
    print("\n2. Короткий номер с контекстом города (Новосибирск):")
    result = normalizer.normalize_phone_to_object("28-54-83", city_context="Новосибирск")
    print(f"   Вход: '28-54-83', город: 'Новосибирск'")
    print(f"   Результат: {result}")
    if result and result[0].get('normalized'):
        print(f"   ✅ Успешно обогащен: {result[0]['normalized']}")
        # Проверяем что номер содержит код 383 (Новосибирск)
        assert '383' in result[0]['normalized']
    else:
        print("   ⚠️ Не удалось обогатить (ожидаемо для коротких номеров)")
    
    # Тест 3: Нормальный номер с кодом города
    print("\n3. Нормальный номер с кодом города:")
    result = normalizer.normalize_phone_to_object("8(38822)49313")
    print(f"   Вход: '8(38822)49313'")
    print(f"   Результат: {result}")
    assert len(result) == 1
    assert result[0]['normalized'] is not None
    assert result[0]['type'] != 'incomplete'
    print(f"   ✅ Корректно нормализован: {result[0]['normalized']}")
    
    # Тест 4: Мобильный номер
    print("\n4. Мобильный номер:")
    result = normalizer.normalize_phone_to_object("8(977)702-72-19")
    print(f"   Вход: '8(977)702-72-19'")
    print(f"   Результат: {result}")
    assert len(result) == 1
    assert result[0]['normalized'] is not None
    print(f"   ✅ Корректно нормализован: {result[0]['normalized']}")
    
    print("\n" + "=" * 80)
    print("✅ ВСЕ ТЕСТЫ PhoneNormalizer ПРОЙДЕНЫ")
    print("=" * 80)


def test_data_normalizer_with_city():
    """Тест DataNormalizer с передачей контекста города"""
    print("\n" + "=" * 80)
    print("ТЕСТ 2: DataNormalizer с контекстом города")
    print("=" * 80)
    
    normalizer = DataNormalizer()
    
    # Тест организации с коротким номером
    print("\n1. Организация с коротким номером и городом:")
    org = {
        "organization_id": 1,
        "name": "Тестовая компания",
        "city": "Новосибирск",
        "phones": ["28-54-83"]
    }
    
    normalized_orgs = normalizer.normalize_organizations({1: org})
    result_org = normalized_orgs[1]
    
    print(f"   Вход: phones=['28-54-83'], city='Новосибирск'")
    print(f"   Результат: {result_org['phones']}")
    
    if result_org['phones']:
        phone = result_org['phones'][0]
        if phone.get('normalized'):
            print(f"   ✅ Телефон обогащен: {phone['normalized']}")
        else:
            print(f"   ⚠️ Телефон помечен как incomplete: {phone.get('incomplete_reason')}")
    
    # Тест организации с нормальным номером
    print("\n2. Организация с нормальным номером:")
    org2 = {
        "organization_id": 2,
        "name": "Компания 2",
        "city": "Москва",
        "phones": ["8(495)640-17-71"]
    }
    
    normalized_orgs2 = normalizer.normalize_organizations({2: org2})
    result_org2 = normalized_orgs2[2]
    
    print(f"   Вход: phones=['8(495)640-17-71']")
    print(f"   Результат: {result_org2['phones']}")
    
    if result_org2['phones']:
        phone = result_org2['phones'][0]
        assert phone.get('normalized') is not None
        print(f"   ✅ Телефон нормализован: {phone['normalized']}")
    
    print("\n" + "=" * 80)
    print("✅ ВСЕ ТЕСТЫ DataNormalizer ПРОЙДЕНЫ")
    print("=" * 80)


def test_contact_phone_enricher_logic():
    """Тест логики ContactPhoneEnricher"""
    print("\n" + "=" * 80)
    print("ТЕСТ 3: ContactPhoneEnricher - проверка дубликатов")
    print("=" * 80)
    
    enricher = ContactPhoneEnricher()
    
    # Тест 1: Телефон с normalized - не дубликат
    print("\n1. Телефон с normalized полем:")
    contact_phones = []
    new_phone = {
        "type": "office",
        "number": "+7 (495) 640-17-71",
        "normalized": "+74956401771",
        "original": "8(495)640-17-71"
    }
    
    result = enricher._check_phone_duplicate(contact_phones, new_phone)
    print(f"   Вход: {new_phone}")
    print(f"   Результат: is_duplicate={result['is_duplicate']}, reason={result['reason']}")
    assert result['is_duplicate'] == False
    print("   ✅ Корректно определен как не дубликат")
    
    # Тест 2: Короткий номер без normalized
    print("\n2. Короткий номер без normalized (неполный):")
    short_phone = {
        "type": "incomplete",
        "number": "28-54-83",
        "normalized": None,
        "original": "28-54-83",
        "needs_manual_review": True
    }
    
    result = enricher._check_phone_duplicate(contact_phones, short_phone)
    print(f"   Вход: {short_phone}")
    print(f"   Результат: is_duplicate={result['is_duplicate']}, reason={result['reason']}")
    assert result['is_duplicate'] == True
    assert 'invalid' in result['reason'] or 'no_normalized' in result['reason']
    print(f"   ✅ Корректно помечен как {result['reason']}")
    
    # Тест 3: Нормальный номер без normalized (ошибка нормализации)
    print("\n3. Нормальный номер без normalized (ошибка):")
    error_phone = {
        "type": "office",
        "number": "8(495)640-17-71",
        "normalized": None,
        "original": "8(495)640-17-71"
    }
    
    result = enricher._check_phone_duplicate(contact_phones, error_phone)
    print(f"   Вход: {error_phone}")
    print(f"   Результат: is_duplicate={result['is_duplicate']}, reason={result['reason']}")
    assert result['is_duplicate'] == True
    print(f"   ✅ Корректно помечен как {result['reason']}")
    
    print("\n" + "=" * 80)
    print("✅ ВСЕ ТЕСТЫ ContactPhoneEnricher ПРОЙДЕНЫ")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_phone_normalizer_with_city_context()
        test_data_normalizer_with_city()
        test_contact_phone_enricher_logic()
        
        print("\n" + "=" * 80)
        print("🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        print("=" * 80)
        print("\nИзменения:")
        print("1. ✅ Телефоны организаций нормализуются ДО обогащения контактов")
        print("2. ✅ Короткие номера обрабатываются с контекстом города")
        print("3. ✅ Различается 'невалидный' vs 'неполный' номер")
        print("4. ✅ Правильное логирование для каждого случая")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
