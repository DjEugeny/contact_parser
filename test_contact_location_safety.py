#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки Contact Location Safety (TASK-008B)
Проверяет, что контакты не получают ложные HQ-адреса/города организаций
"""

import sys
import json
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.postprocessing.contact_location_safety import ContactLocationSafety, ContactLocationEvidence


def test_hq_block_detection():
    """Тест определения HQ-блоков"""
    print("\n" + "="*80)
    print("ТЕСТ 1: Определение HQ-блоков")
    print("="*80)
    
    safety = ContactLocationSafety()
    
    # Тест 1: Блок с ИНН
    text_with_inn = """
    ООО «ДНК-Технология»
    ИНН: 1901066506
    Адрес: г. Москва, Варшавское шоссе, д. 125Ж, корп. 6
    """
    
    is_hq = safety.is_hq_block(text_with_inn)
    print(f"✓ Текст с ИНН определен как HQ-блок: {is_hq}")
    assert is_hq, "Текст с ИНН должен быть определен как HQ-блок"
    
    # Тест 2: Персональная подпись
    text_personal = """
    Воронова Светлана Сергеевна
    Менеджер по продажам
    Региональный представитель в г. Новосибирск
    Тел: +7 (383) 123-45-67
    """
    
    is_hq = safety.is_hq_block(text_personal)
    print(f"✓ Персональная подпись НЕ определена как HQ-блок: {not is_hq}")
    assert not is_hq, "Персональная подпись не должна быть определена как HQ-блок"
    
    print("✅ Тест определения HQ-блоков пройден")


def test_confidence_scoring():
    """Тест системы оценки уверенности"""
    print("\n" + "="*80)
    print("ТЕСТ 2: Система оценки уверенности (confidence scoring)")
    print("="*80)
    
    safety = ContactLocationSafety()
    
    # Тест 1: Сильный персональный маркер
    text_strong = "Региональный представитель в г. Новосибирск"
    context_strong = {'source_type': 'signature', 'has_name': True, 'has_title': True}
    confidence = safety.calculate_confidence(text_strong, context_strong)
    print(f"✓ Сильный персональный маркер: confidence = {confidence:.2f} (ожидается >= 0.9)")
    assert confidence >= 0.9, f"Confidence должен быть >= 0.9, получено {confidence}"
    
    # Тест 2: Подпись с ФИО и должностью
    text_signature = "Иванов Иван Иванович\nМенеджер\nг. Москва"
    context_signature = {'source_type': 'signature', 'has_name': True, 'has_title': True}
    confidence = safety.calculate_confidence(text_signature, context_signature)
    print(f"✓ Подпись с ФИО и должностью: confidence = {confidence:.2f} (ожидается >= 0.8)")
    assert confidence >= 0.8, f"Confidence должен быть >= 0.8, получено {confidence}"
    
    # Тест 3: HQ-блок
    text_hq = "ИНН: 1234567890\nАдрес: г. Москва, ул. Ленина, 1"
    context_hq = {'source_type': 'signature', 'has_name': False, 'has_title': False}
    confidence = safety.calculate_confidence(text_hq, context_hq)
    print(f"✓ HQ-блок: confidence = {confidence:.2f} (ожидается 0.0)")
    assert confidence == 0.0, f"Confidence для HQ-блока должен быть 0.0, получено {confidence}"
    
    # Тест 4: Упоминание в теле без контекста
    text_body = "Иванов работает в Москве"
    context_body = {'source_type': 'body_near_name', 'has_name': True, 'has_title': False}
    confidence = safety.calculate_confidence(text_body, context_body)
    print(f"✓ Упоминание в теле без контекста: confidence = {confidence:.2f} (ожидается <= 0.6)")
    assert confidence <= 0.6, f"Confidence должен быть <= 0.6, получено {confidence}"
    
    print("✅ Тест системы оценки уверенности пройден")


def test_city_extraction():
    """Тест извлечения городов"""
    print("\n" + "="*80)
    print("ТЕСТ 3: Извлечение городов")
    print("="*80)
    
    safety = ContactLocationSafety()
    
    # Тест 1: Простое извлечение
    text1 = "Региональный представитель в г. Новосибирск"
    city = safety._extract_city(text1)
    print(f"✓ Извлечен город: '{city}' (ожидается 'Новосибирск')")
    assert city == "Новосибирск", f"Ожидался 'Новосибирск', получено '{city}'"
    
    # Тест 2: Город с пробелом
    text2 = "Офис в г. Нижний Новгород"
    city = safety._extract_city(text2)
    print(f"✓ Извлечен город с пробелом: '{city}' (ожидается 'Нижний Новгород')")
    assert city == "Нижний Новгород", f"Ожидался 'Нижний Новгород', получено '{city}'"
    
    # Тест 3: Несколько городов (выбирается первый с высоким приоритетом)
    text3 = "Представитель в г. Москва, офис в г. Санкт-Петербург"
    city = safety._extract_city(text3)
    print(f"✓ Из нескольких городов выбран: '{city}'")
    assert city in ["Москва", "Санкт-Петербург"], f"Должен быть выбран один из городов, получено '{city}'"
    
    print("✅ Тест извлечения городов пройден")


def test_internal_domain_handling():
    """Тест обработки внутренних доменов"""
    print("\n" + "="*80)
    print("ТЕСТ 4: Обработка внутренних доменов")
    print("="*80)
    
    safety = ContactLocationSafety()
    
    # Контакт с внутренним доменом
    contact = {
        'gid': 'contact_001',
        'name': 'Воронова С.С.',
        'email': 's.voronova@dna-technology.ru',
        'city': None,
        'address': None
    }
    
    # Слабый персональный сигнал (confidence < 0.8)
    evidence_weak = ContactLocationEvidence(
        city='Москва',
        address='Варшавское шоссе',
        snippet='Москва, Варшавское шоссе',
        confidence=0.6,
        source_type='body_near_name',
        matched_patterns=['г.']
    )
    
    metadata = {}
    applied = safety.apply_contact_location(contact, evidence_weak, metadata)
    
    print(f"✓ Внутренний домен + слабый сигнал: применено = {applied} (ожидается False)")
    print(f"✓ city = {contact.get('city')} (ожидается None)")
    print(f"✓ address = {contact.get('address')} (ожидается None)")
    
    assert not applied, "Локация не должна быть применена для внутреннего домена со слабым сигналом"
    assert contact.get('city') is None, "city должен остаться None"
    assert contact.get('address') is None, "address должен остаться None"
    
    # Сильный персональный сигнал (confidence >= 0.8)
    contact2 = {
        'gid': 'contact_002',
        'name': 'Иванов И.И.',
        'email': 'i.ivanov@dna-technology.ru',
        'city': None,
        'address': None
    }
    
    evidence_strong = ContactLocationEvidence(
        city='Новосибирск',
        address=None,
        snippet='Региональный представитель в г. Новосибирск',
        confidence=0.9,
        source_type='signature',
        matched_patterns=['представитель', 'г.']
    )
    
    metadata2 = {}
    applied2 = safety.apply_contact_location(contact2, evidence_strong, metadata2)
    
    print(f"✓ Внутренний домен + сильный сигнал: применено = {applied2} (ожидается True)")
    print(f"✓ city = {contact2.get('city')} (ожидается 'Новосибирск')")
    
    assert applied2, "Локация должна быть применена для внутреннего домена с сильным сигналом"
    assert contact2.get('city') == 'Новосибирск', "city должен быть 'Новосибирск'"
    
    print("✅ Тест обработки внутренних доменов пройден")


def test_no_overwrite_existing():
    """Тест защиты от перезаписи существующих данных"""
    print("\n" + "="*80)
    print("ТЕСТ 5: Защита от перезаписи существующих данных")
    print("="*80)
    
    safety = ContactLocationSafety()
    
    # Контакт с уже заполненным городом
    contact = {
        'gid': 'contact_003',
        'name': 'Петров П.П.',
        'email': 'petrov@example.com',
        'city': 'Новосибирск',
        'address': None
    }
    
    # Пытаемся применить другой город
    evidence = ContactLocationEvidence(
        city='Москва',
        address='ул. Ленина, 1',
        snippet='Москва, ул. Ленина, 1',
        confidence=0.9,
        source_type='signature',
        matched_patterns=['г.']
    )
    
    metadata = {}
    applied = safety.apply_contact_location(contact, evidence, metadata)
    
    print(f"✓ Попытка перезаписи city: применено = {applied}")
    print(f"✓ city остался = '{contact.get('city')}' (ожидается 'Новосибирск')")
    print(f"✓ address применен = '{contact.get('address')}' (ожидается 'ул. Ленина, 1')")
    
    assert contact.get('city') == 'Новосибирск', "city не должен быть перезаписан"
    assert contact.get('address') == 'ул. Ленина, 1', "address должен быть применен (поле было пустым)"
    
    print("✅ Тест защиты от перезаписи пройден")


def main():
    """Запуск всех тестов"""
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ МОДУЛЯ CONTACT LOCATION SAFETY (TASK-008B)")
    print("="*80)
    
    try:
        test_hq_block_detection()
        test_confidence_scoring()
        test_city_extraction()
        test_internal_domain_handling()
        test_no_overwrite_existing()
        
        print("\n" + "="*80)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("="*80)
        
        # Выводим статистику
        safety = ContactLocationSafety()
        stats = safety.get_stats()
        print(f"\n📊 Статистика:")
        print(f"  - Контактов обработано: {stats['contacts_processed']}")
        print(f"  - Локаций применено: {stats['locations_applied']}")
        print(f"  - Локаций отклонено: {stats['locations_rejected']}")
        print(f"  - HQ-блоков обнаружено: {stats['hq_blocks_detected']}")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
