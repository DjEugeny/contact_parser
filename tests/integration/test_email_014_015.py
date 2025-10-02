#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграционные тесты для обработки email_014 и email_015 после исправления нормализации телефонов
"""

import sys
import os
sys.path.insert(0, '/Users/evgenyzach/contact_parser')
sys.path.insert(0, '/Users/evgenyzach/contact_parser/src')

from src.api_pipeline_validator import process_single_email

def test_email_014_phone_normalization():
    """Проверка обработки email_014 после исправления"""
    print("=== Тест: email_014 phone normalization ===")

    try:
        result = process_single_email("email_014", "2025-07-29")
        print(f"Результат обработки: success={result.get('success')}")

        assert result['success'] == True, "Обработка email_014 должна быть успешной"
        assert 'validation_error' not in result or not result['validation_error'], "Не должно быть ошибок валидации"

        # Проверка структуры телефонов
        organizations = result.get('organizations', [])
        assert len(organizations) > 0, "Должна быть хотя бы одна организация"

        org = organizations[0]  # МИЛЛАБ
        phones = org.get('phones', [])
        print(f"Телефоны организации: {phones}")

        # Должно быть 2-3 телефона (после split)
        assert len(phones) >= 2, f"Ожидалось >=2 телефонов, получено {len(phones)}"

        # Все phones — объекты
        assert all(isinstance(p, dict) for p in phones), "Все телефоны должны быть объектами"

        # extension не в number
        for phone in phones:
            number = phone.get('number', '')
            assert 'доб' not in number, f"Добавочный не должен быть в number: {number}"
            assert 'ext' not in number, f"Добавочный не должен быть в number: {number}"

        # Есть extension
        extensions = [p.get('extension') for p in phones if p.get('extension')]
        assert len(extensions) >= 1, f"Должен быть хотя бы один телефон с extension, найдено: {extensions}"

        print("✅ email_014 обработан корректно")

    except Exception as e:
        print(f"❌ Ошибка в тесте email_014: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_email_015_phone_normalization():
    """Проверка обработки email_015 после исправления"""
    print("\n=== Тест: email_015 phone normalization ===")

    try:
        result = process_single_email("email_015", "2025-07-29")
        print(f"Результат обработки: success={result.get('success')}")

        assert result['success'] == True, "Обработка email_015 должна быть успешной"
        assert 'validation_error' not in result or not result['validation_error'], "Не должно быть ошибок валидации"

        # Проверка структуры телефонов аналогично email_014
        organizations = result.get('organizations', [])
        contacts = result.get('contacts', [])

        # Проверяем организации
        for org in organizations:
            phones = org.get('phones', [])
            if phones:
                assert all(isinstance(p, dict) for p in phones), f"Все телефоны организации должны быть объектами: {phones}"
                for phone in phones:
                    number = phone.get('number', '')
                    assert 'доб' not in number, f"Добавочный не должен быть в number: {number}"

        # Проверяем контакты
        for contact in contacts:
            phones = contact.get('phones', [])
            if phones:
                assert all(isinstance(p, dict) for p in phones), f"Все телефоны контакта должны быть объектами: {phones}"
                for phone in phones:
                    number = phone.get('number', '')
                    assert 'доб' not in number, f"Добавочный не должен быть в number: {number}"

        print("✅ email_015 обработан корректно")

    except Exception as e:
        print(f"❌ Ошибка в тесте email_015: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_no_duplicates():
    """Проверка отсутствия дубликатов телефонов"""
    print("\n=== Тест: Отсутствие дубликатов ===")

    try:
        # Тестируем на обоих письмах
        for email_id in ["email_014", "email_015"]:
            result = process_single_email(email_id, "2025-07-29")

            # Собираем все normalized значения
            all_normalized = []
            for org in result.get('organizations', []):
                for phone in org.get('phones', []):
                    if isinstance(phone, dict) and 'normalized' in phone:
                        all_normalized.append(phone['normalized'])

            for contact in result.get('contacts', []):
                for phone in contact.get('phones', []):
                    if isinstance(phone, dict) and 'normalized' in phone:
                        all_normalized.append(phone['normalized'])

            # Проверяем уникальность
            unique_normalized = set(all_normalized)
            assert len(all_normalized) == len(unique_normalized), f"Найдены дубликаты в {email_id}: {all_normalized}"

            print(f"✅ В {email_id} нет дубликатов телефонов")

    except Exception as e:
        print(f"❌ Ошибка в тесте дубликатов: {e}")
        import traceback
        traceback.print_exc()
        raise

def run_integration_tests():
    """Запуск интеграционных тестов"""
    print("🚀 Запуск интеграционных тестов phone normalization\n")

    try:
        test_email_014_phone_normalization()
        test_email_015_phone_normalization()
        test_no_duplicates()

        print("\n🎉 Все интеграционные тесты пройдены!")

    except Exception as e:
        print(f"\n❌ Ошибка в интеграционных тестах: {e}")
        return False

    return True

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)