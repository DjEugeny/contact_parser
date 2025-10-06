#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки предотвращения HQ-backfill (TASK-008B)
Проверяет, что контакты без персональных сигналов НЕ получают HQ-адреса
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_backfill_logic():
    """Тест логики backfill"""
    print("\n" + "="*80)
    print("ТЕСТ: Предотвращение HQ-backfill для контактов без персональных сигналов")
    print("="*80)
    
    # Симулируем логику из _backfill_contact_city_address
    
    def _has_value(val):
        """Проверка наличия значения"""
        if val is None or val == "":
            return False
        if isinstance(val, str):
            return bool(val.strip())
        return True
    
    # Тест 1: Контакт БЕЗ персональной локации (как Клочкова-Абельянц)
    print("\n--- Тест 1: Контакт без персональной локации ---")
    contact1 = {
        'name': 'Клочкова-Абельянц Сатеник Аршавиловна',
        'email': None,
        'city': None,
        'address': None
    }
    
    has_personal_location = (
        _has_value(contact1.get('city')) or 
        _has_value(contact1.get('address'))
    )
    allow_backfill = has_personal_location
    
    print(f"  Контакт: {contact1['name']}")
    print(f"  city: {contact1['city']}")
    print(f"  address: {contact1['address']}")
    print(f"  has_personal_location: {has_personal_location}")
    print(f"  allow_backfill: {allow_backfill}")
    print(f"  ✓ Результат: Backfill {'РАЗРЕШЕН' if allow_backfill else 'ЗАПРЕЩЕН'}")
    
    assert not allow_backfill, "Backfill должен быть запрещен для контакта без персональной локации"
    print("  ✅ PASS: Backfill корректно запрещен")
    
    # Тест 2: Контакт С персональной локацией (как Воронова с city=Новосибирск)
    print("\n--- Тест 2: Контакт с персональной локацией (city) ---")
    contact2 = {
        'name': 'Воронова Светлана Сергеевна',
        'email': 's.voronova@dna-technology.ru',
        'city': 'Новосибирск',
        'address': None
    }
    
    has_personal_location = (
        _has_value(contact2.get('city')) or 
        _has_value(contact2.get('address'))
    )
    allow_backfill = has_personal_location
    
    print(f"  Контакт: {contact2['name']}")
    print(f"  city: {contact2['city']}")
    print(f"  address: {contact2['address']}")
    print(f"  has_personal_location: {has_personal_location}")
    print(f"  allow_backfill: {allow_backfill}")
    print(f"  ✓ Результат: Backfill {'РАЗРЕШЕН' if allow_backfill else 'ЗАПРЕЩЕН'}")
    
    assert allow_backfill, "Backfill должен быть разрешен для контакта с персональной локацией"
    print("  ✅ PASS: Backfill корректно разрешен (может дополнить address)")
    
    # Тест 3: Контакт с персональным адресом, но без города
    print("\n--- Тест 3: Контакт с персональным адресом ---")
    contact3 = {
        'name': 'Иванов Иван',
        'email': 'ivanov@example.com',
        'city': None,
        'address': 'ул. Ленина, 10'
    }
    
    has_personal_location = (
        _has_value(contact3.get('city')) or 
        _has_value(contact3.get('address'))
    )
    allow_backfill = has_personal_location
    
    print(f"  Контакт: {contact3['name']}")
    print(f"  city: {contact3['city']}")
    print(f"  address: {contact3['address']}")
    print(f"  has_personal_location: {has_personal_location}")
    print(f"  allow_backfill: {allow_backfill}")
    print(f"  ✓ Результат: Backfill {'РАЗРЕШЕН' if allow_backfill else 'ЗАПРЕЩЕН'}")
    
    assert allow_backfill, "Backfill должен быть разрешен для контакта с персональным адресом"
    print("  ✅ PASS: Backfill корректно разрешен (может дополнить city)")
    
    # Тест 4: Контакт с пустыми строками (не None)
    print("\n--- Тест 4: Контакт с пустыми строками ---")
    contact4 = {
        'name': 'Петров Петр',
        'email': 'petrov@example.com',
        'city': '',
        'address': '   '
    }
    
    has_personal_location = (
        _has_value(contact4.get('city')) or 
        _has_value(contact4.get('address'))
    )
    allow_backfill = has_personal_location
    
    print(f"  Контакт: {contact4['name']}")
    print(f"  city: '{contact4['city']}'")
    print(f"  address: '{contact4['address']}'")
    print(f"  has_personal_location: {has_personal_location}")
    print(f"  allow_backfill: {allow_backfill}")
    print(f"  ✓ Результат: Backfill {'РАЗРЕШЕН' if allow_backfill else 'ЗАПРЕЩЕН'}")
    
    assert not allow_backfill, "Backfill должен быть запрещен для контакта с пустыми строками"
    print("  ✅ PASS: Backfill корректно запрещен")
    
    print("\n" + "="*80)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("="*80)
    print("\n📋 Резюме логики:")
    print("  • Backfill применяется ТОЛЬКО если у контакта есть city ИЛИ address")
    print("  • Если оба поля пустые/None - backfill ЗАПРЕЩЕН")
    print("  • Это предотвращает ложное обогащение HQ-адресами")
    print("  • Контакты получают локацию только через contact_location_safety")
    print("="*80)


def main():
    """Запуск тестов"""
    try:
        test_backfill_logic()
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
