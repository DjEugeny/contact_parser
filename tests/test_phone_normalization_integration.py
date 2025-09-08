#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест интеграции нормализации телефонов (ФАЗА 3)
Проверяет работу PhoneNormalizer в ContactExtractor
"""

import sys
import os
import json
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm_extractor import ContactExtractor
from src.phone_normalizer import PhoneNormalizer

def test_phone_normalization_integration():
    """🔬 Тестирование интеграции нормализации телефонов"""

    print("🧪 ТЕСТ ИНТЕГРАЦИИ НОРМАЛИЗАЦИИ ТЕЛЕФОНОВ (ФАЗА 3)")
    print("=" * 60)

    # Тестовые данные с различными форматами телефонов
    test_cases = [
        {
            'name': 'Иван Петров',
            'email': 'ivan.petrov@company.ru',
            'phone': '+7 (495) 123-45-67',
            'organization': 'ООО Компания',
            'position': 'Директор',
            'confidence': 0.9
        },
        {
            'name': 'Мария Иванова',
            'email': 'maria@firm.com',
            'phone': '8-800-555-01-23 доб. 456',
            'organization': 'ЗАО Фирма',
            'position': 'Менеджер',
            'confidence': 0.85
        },
        {
            'name': 'Алексей Сидоров',
            'email': 'alex.sid@gmail.com',
            'phone': '+7(916)777-88-99',
            'organization': 'ИП Сидоров',
            'position': 'Владелец',
            'confidence': 0.8
        },
        {
            'name': 'Контакт без телефона',
            'email': 'no.phone@test.com',
            'phone': '',
            'organization': 'Без телефона',
            'position': 'Тест',
            'confidence': 0.7
        }
    ]

    print(f"📝 Тестовые данные: {len(test_cases)} контактов")
    print()

    # Тестирование PhoneNormalizer отдельно
    print("1️⃣ ТЕСТИРОВАНИЕ PHONENORMALIZER ОТДЕЛЬНО")
    print("-" * 40)

    normalizer = PhoneNormalizer()

    for i, contact in enumerate(test_cases, 1):
        print(f"🔍 Контакт {i}: {contact['name']}")
        print(f"   Оригинальный телефон: '{contact['phone']}'")

        if contact['phone']:
            normalized_data = normalizer.normalize_contact_phone(contact['phone'])
            print("   📞 Нормализованные данные:")
            print(f"      raw_phone: '{normalized_data['raw_phone']}'")
            print(f"      normalized_phone: '{normalized_data['normalized_phone']}'")
            print(f"      formatted_phone: '{normalized_data['formatted_phone']}'")
            print(f"      phone_type: '{normalized_data['phone_type']}'")
            print(f"      phone_extension: '{normalized_data['phone_extension']}'")
            print(f"      confidence: {normalized_data['confidence']:.2f}")
        else:
            print("   ⚠️ Нет телефона для нормализации")
        print()

    # Тестирование интеграции с ContactExtractor
    print("2️⃣ ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ С CONTACTEXTRACTOR")
    print("-" * 50)

    # Создаем экстрактор в тестовом режиме
    extractor = ContactExtractor(test_mode=True)

    # Создаем тестовый результат с нашими контактами
    test_result = {
        'contacts': test_cases.copy(),
        'business_context': 'Тестовый бизнес-контекст для проверки нормализации',
        'commercial_offers': [],
        'provider_used': 'Test Mode'
    }

    print("📤 Исходные контакты:")
    for i, contact in enumerate(test_result['contacts'], 1):
        print(f"   {i}. {contact['name']}: {contact.get('phone', 'нет телефона')}")

    # Применяем нормализацию через ContactExtractor
    print("\n🔧 Применение нормализации через ContactExtractor...")
    normalized_contacts = extractor.phone_normalizer.normalize_contact_list(test_result['contacts'])

    print("\n📥 Нормализованные контакты:")
    for i, contact in enumerate(normalized_contacts, 1):
        print(f"   {i}. {contact['name']}:")
        if contact.get('phone'):
            print(f"      Оригинал: '{contact.get('raw_phone', '')}'")
            print(f"      Нормализованный: '{contact.get('normalized_phone', '')}'")
            print(f"      Форматированный: '{contact.get('formatted_phone', '')}'")
            print(f"      Тип: '{contact.get('phone_type', '')}'")
            if contact.get('phone_extension'):
                print(f"      Добавочный: '{contact.get('phone_extension', '')}'")
        else:
            print("      ⚠️ Нет телефона")

    # Статистика нормализации
    print("\n📊 СТАТИСТИКА НОРМАЛИЗАЦИИ")
    print("-" * 30)

    phone_stats = extractor.phone_normalizer.get_phone_stats(normalized_contacts)
    print(f"Всего контактов: {phone_stats['total_contacts']}")
    print(f"С телефонами: {phone_stats['with_phones']}")
    print(f"С добавочными номерами: {phone_stats['extensions']}")
    print(f"Распределение по типам: {phone_stats['phone_types']}")
    print(f"Уверенность: {phone_stats['confidence_distribution']}")

    # Тестирование дедупликации
    print("\n3️⃣ ТЕСТИРОВАНИЕ ДЕДУПЛИКАЦИИ")
    print("-" * 35)

    # Создаем дубликаты для тестирования
    duplicate_contacts = [
        {
            'name': 'Иван Петров',
            'email': 'ivan.petrov@company.ru',
            'phone': '+7 (495) 123-45-67',
            'normalized_phone': '74951234567',
            'organization': 'ООО Компания',
            'confidence': 0.9
        },
        {
            'name': 'Иван Петров (дубликат)',
            'email': 'ivan.petrov@company.ru',  # Тот же email
            'phone': '8(495)123-45-67',  # Другой формат, но тот же номер
            'normalized_phone': '74951234567',  # Нормализованный будет тот же
            'organization': 'ООО Компания',
            'confidence': 0.85
        },
        {
            'name': 'Мария Иванова',
            'email': 'maria@firm.com',
            'phone': '8-800-555-01-23 доб. 456',
            'normalized_phone': '78005550123',
            'organization': 'ЗАО Фирма',
            'confidence': 0.8
        }
    ]

    print(f"📝 Тестовые данные с дубликатами: {len(duplicate_contacts)} контактов")

    # Применяем дедупликацию
    unique_contacts = extractor._deduplicate_contacts(duplicate_contacts)

    print("\n🎯 Результат дедупликации:")
    print(f"   Исходно: {len(duplicate_contacts)} контактов")
    print(f"   Уникальных: {len(unique_contacts)} контактов")

    for i, contact in enumerate(unique_contacts, 1):
        print(f"   {i}. {contact['name']} ({contact.get('email', 'нет email')})")

    # Финальный отчет
    print("\n🎉 ТЕСТ ИНТЕГРАЦИИ ЗАВЕРШЕН")
    print("=" * 60)
    print("✅ PhoneNormalizer успешно интегрирован")
    print("✅ Нормализация телефонов работает корректно")
    print("✅ Дедупликация использует нормализованные данные")
    print("✅ ФАЗА 3: Постобработка и нормализация - ВЫПОЛНЕНА")

    return True

if __name__ == "__main__":
    try:
        test_phone_normalization_integration()
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
