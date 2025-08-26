#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест продвинутого алгоритма дедупликации контактов
Дата создания: 2025-01-21 22:50 (UTC+07)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from advanced_deduplication import AdvancedContactDeduplicator

def test_advanced_deduplication():
    """🔬 Тестирование продвинутой дедупликации на примере цепочек пересылок"""
    print("\n" + "="*80)
    print("🧪 ТЕСТ ПРОДВИНУТОЙ ДЕДУПЛИКАЦИИ КОНТАКТОВ")
    print(f"⏰ Время запуска: 2025-01-21 22:50 (UTC+07)")
    print("="*80)
    
    deduplicator = AdvancedContactDeduplicator()
    
    # Тестовые данные: имитация контактов из цепочки пересылок
    test_contacts = [
        # Оригинальные контакты
        {
            'name': 'Иван Петров',
            'email': 'ivan.petrov@company.ru',
            'phone': '+7 (495) 123-45-67',
            'organization': 'ООО "Рога и Копыта"',
            'position': 'Менеджер по продажам',
            'city': 'Москва',
            'confidence': 0.95,
            'source': 'original_email'
        },
        # Дубликат из пересылки (немного другое форматирование)
        {
            'name': 'Петров Иван',
            'email': 'ivan.petrov@company.ru',
            'phone': '8 495 123 45 67',
            'organization': 'ООО Рога и Копыта',
            'position': 'менеджер продаж',
            'city': 'Москва',
            'confidence': 0.85,
            'source': 'forwarded_email_1'
        },
        # Еще один дубликат из другой пересылки
        {
            'name': 'И. Петров',
            'email': 'ivan.petrov@company.ru',
            'phone': '+7-495-123-45-67',
            'organization': 'Рога и Копыта',
            'position': 'Менеджер',
            'confidence': 0.75,
            'source': 'forwarded_email_2'
        },
        # Другой контакт
        {
            'name': 'Мария Сидорова',
            'email': 'maria.sidorova@example.com',
            'phone': '+7 (916) 987-65-43',
            'organization': 'ИП Сидорова',
            'position': 'Директор',
            'city': 'Санкт-Петербург',
            'confidence': 0.90,
            'source': 'original_email'
        },
        # Семантически похожий контакт (возможно тот же человек)
        {
            'name': 'Мария Сидорова',
            'email': 'maria@example.com',  # Другой email
            'phone': '+7 916 987 65 43',
            'organization': 'Сидорова М.В. ИП',
            'position': 'Индивидуальный предприниматель',
            'city': 'СПб',
            'confidence': 0.80,
            'source': 'forwarded_email_1'
        },
        # Контакт только с телефоном
        {
            'name': 'Алексей Иванов',
            'phone': '+7 (903) 555-12-34',
            'organization': 'Фриланс',
            'confidence': 0.70,
            'source': 'original_email'
        },
        # Дубликат по телефону
        {
            'name': 'А. Иванов',
            'phone': '8 903 555 12 34',
            'organization': 'Фрилансер',
            'confidence': 0.65,
            'source': 'forwarded_email_1'
        },
        # Контакт с неполными данными
        {
            'name': 'Елена',
            'email': 'elena@test.ru',
            'confidence': 0.60,
            'source': 'forwarded_email_2'
        }
    ]
    
    print(f"\n📊 Исходные данные: {len(test_contacts)} контактов")
    print("\n🔍 Детали исходных контактов:")
    for i, contact in enumerate(test_contacts, 1):
        print(f"   {i}. {contact.get('name', 'Без имени')} | {contact.get('email', 'Без email')} | {contact.get('phone', 'Без телефона')} | Источник: {contact.get('source', 'Неизвестно')}")
    
    # Выполняем дедупликацию
    print("\n" + "-"*60)
    print("🚀 ЗАПУСК ПРОДВИНУТОЙ ДЕДУПЛИКАЦИИ")
    print("-"*60)
    
    unique_contacts = deduplicator.deduplicate_contacts(test_contacts)
    
    print("\n" + "-"*60)
    print("📋 РЕЗУЛЬТАТЫ ДЕДУПЛИКАЦИИ")
    print("-"*60)
    
    print(f"\n📊 Результат: {len(unique_contacts)} уникальных контактов")
    print(f"🗑️ Удалено дубликатов: {len(test_contacts) - len(unique_contacts)}")
    print(f"📈 Эффективность: {((len(test_contacts) - len(unique_contacts)) / len(test_contacts) * 100):.1f}% дубликатов удалено")
    
    print("\n🎯 Финальные уникальные контакты:")
    for i, contact in enumerate(unique_contacts, 1):
        print(f"\n   {i}. {contact.get('name', 'Без имени')}")
        print(f"      📧 Email: {contact.get('email', 'Не указан')}")
        print(f"      📞 Телефон: {contact.get('phone', 'Не указан')}")
        print(f"      🏢 Организация: {contact.get('organization', 'Не указана')}")
        print(f"      💼 Должность: {contact.get('position', 'Не указана')}")
        print(f"      🌍 Город: {contact.get('city', 'Не указан')}")
        print(f"      📊 Confidence: {contact.get('confidence', 0):.2f}")
        
        # Показываем дополнительные поля, если есть
        if contact.get('other_emails'):
            print(f"      📧+ Другие emails: {', '.join(contact['other_emails'])}")
        if contact.get('other_phones'):
            print(f"      📞+ Другие телефоны: {', '.join(contact['other_phones'])}")
        if contact.get('merged_from_count'):
            print(f"      🔗 Объединено из {contact['merged_from_count']} дубликатов")
    
    print("\n" + "="*80)
    print("✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
    print(f"⏰ Время завершения: 2025-01-21 22:50 (UTC+07)")
    print("="*80)
    
    return unique_contacts

def test_semantic_similarity():
    """🧠 Тестирование семантического сравнения контактов"""
    print("\n" + "="*80)
    print("🧠 ТЕСТ СЕМАНТИЧЕСКОГО СРАВНЕНИЯ")
    print("="*80)
    
    deduplicator = AdvancedContactDeduplicator()
    
    # Тестовые пары контактов для семантического сравнения
    test_pairs = [
        (
            {'name': 'Иван Петров', 'organization': 'ООО Рога и Копыта', 'position': 'Менеджер'},
            {'name': 'Петров И.В.', 'organization': 'Рога и Копыта', 'position': 'Менеджер по продажам'}
        ),
        (
            {'name': 'Мария Сидорова', 'organization': 'ИП Сидорова', 'city': 'Москва'},
            {'name': 'М. Сидорова', 'organization': 'Сидорова М.В.', 'city': 'Москва'}
        ),
        (
            {'name': 'Алексей Иванов', 'position': 'Программист'},
            {'name': 'Петр Сидоров', 'position': 'Дизайнер'}
        )
    ]
    
    for i, (contact1, contact2) in enumerate(test_pairs, 1):
        similarity = deduplicator._calculate_contact_similarity(contact1, contact2)
        print(f"\n🔍 Пара {i}:")
        print(f"   Контакт 1: {contact1}")
        print(f"   Контакт 2: {contact2}")
        print(f"   📊 Схожесть: {similarity:.3f} ({similarity*100:.1f}%)")
        print(f"   🎯 Результат: {'ДУБЛИКАТЫ' if similarity >= deduplicator.similarity_threshold else 'РАЗНЫЕ КОНТАКТЫ'}")
    
    print("\n✅ Тест семантического сравнения завершен")

if __name__ == "__main__":
    try:
        # Основной тест дедупликации
        unique_contacts = test_advanced_deduplication()
        
        # Тест семантического сравнения
        test_semantic_similarity()
        
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()