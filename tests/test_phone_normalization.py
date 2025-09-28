#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование нормализации телефонов в основном пайплайне
"""

import sys
import os
sys.path.append('/Users/evgenyzach/contact_parser/src')

from postprocessing.phone_normalizer import PhoneNormalizer
from postprocessing.data_normalizer import DataNormalizer

def test_phone_normalizer():
    """Тестирование phone_normalizer.py"""
    print("=== Тестирование phone_normalizer.py ===")
    
    phone_normalizer = PhoneNormalizer()
    
    test_phones = [
        "(495) 640-17-71",
        "+7 (495) 933 71 47 (48), +7 (495) 933 71 47 (48), доб.171",
        "+7 (495) 933 71 47",
        "8 (495) 640-17-71"
    ]
    
    for phone in test_phones:
        print(f"\nИсходный: {phone}")
        result = phone_normalizer.normalize_contact_phone(phone)
        print(f"Результат: {result}")
        print(f"Тип результата: {type(result)}")

def test_data_normalizer():
    """Тестирование DataNormalizer"""
    print("\n=== Тестирование DataNormalizer ===")
    
    normalizer = DataNormalizer()
    print(f"phone_normalizer_available: {normalizer.phone_normalizer_available}")
    
    # Тестируем контакт с телефонами
    test_contact = {
        "name": "Иван Иванов",
        "phones": [
            {
                "type": "office",
                "number": "(495) 640-17-71"
            },
            {
                "type": "mobile", 
                "number": "+7 (495) 933 71 47 (48), доб.171"
            }
        ]
    }
    
    print(f"\nИсходный контакт: {test_contact}")
    
    normalized_contact = normalizer._normalize_single_contact(test_contact)
    print(f"\nНормализованный контакт: {normalized_contact}")
    
    # Тестируем организацию с телефонами
    test_org = {
        "name": "ООО Тест",
        "phones": [
            "(495) 640-17-71",
            "+7 (495) 933 71 47 (48), доб.171"
        ]
    }
    
    print(f"\nИсходная организация: {test_org}")
    
    normalized_org = normalizer._normalize_single_organization(test_org)
    print(f"\nНормализованная организация: {normalized_org}")

def test_fallback_normalizer():
    """Тестирование fallback нормализатора"""
    print("\n=== Тестирование fallback нормализатора ===")
    
    normalizer = DataNormalizer()
    
    test_phones = [
        "(495) 640-17-71",
        "8 (495) 640-17-71",
        "+7 (495) 933 71 47"
    ]
    
    for phone in test_phones:
        print(f"\nИсходный: {phone}")
        result = normalizer._simple_phone_cleanup(phone)
        print(f"Simple cleanup результат: {result}")
        print(f"Тип результата: {type(result)}")

if __name__ == "__main__":
    test_phone_normalizer()
    test_data_normalizer()
    test_fallback_normalizer()