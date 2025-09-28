#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование улучшенной нормализации телефонов
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from phone_normalizer import PhoneNormalizer

def test_complex_phones():
    normalizer = PhoneNormalizer()
    
    test_cases = [
        "(495) 640-17-71",
        "+7 (495) 933 71 47 (48), доб.171",
        "+7 (495) 933 71 47 (48)",
        "8 (495) 123-45-67 доб. 123",
        "495 123 45 67",
        "+7 495 933-71-47 (48), доб.171"
    ]
    
    print("=== Тестирование одиночной нормализации ===")
    for phone in test_cases:
        print(f"\nИсходный: {phone}")
        result = normalizer.normalize_contact_phone(phone)
        print(f"Результат: {result}")
    
    print("\n=== Тестирование множественной нормализации ===")
    for phone in test_cases:
        print(f"\nИсходный: {phone}")
        results = normalizer.normalize_multiple_phones(phone)
        for i, result in enumerate(results, 1):
            print(f"Номер {i}: {result}")

if __name__ == "__main__":
    test_complex_phones()