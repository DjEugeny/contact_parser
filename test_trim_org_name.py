#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест обрезки названий организаций
"""

import re

def trim_organization_name(org_name: str) -> str:
    """Обрезает название организации на предлогах и персоналиях"""
    
    # Предлоги и стоп-слова
    stop_patterns = [
        r'\s+для\s+',      # для
        r'\s+от\s+',       # от
        r'\s+в\s+',        # в
        r'\s+на\s+',       # на
        r'\s+по\s+',       # по
        # Персоналии (отчества)
        r'\s+[А-ЯЁ][а-яё]+ович[а-яё]*\s+',  # Иванович
        r'\s+[А-ЯЁ][а-яё]+евн[а-яё]*\s+',   # Ивановна
        # Имена (заглавная + строчные)
        r'\s+[А-ЯЁ][а-яё]+у\s+[А-ЯЁ][а-яё]+',  # Акутину Ивану
    ]
    
    trimmed = org_name
    for pattern in stop_patterns:
        match = re.search(pattern, trimmed, re.IGNORECASE | re.UNICODE)
        if match:
            trimmed = trimmed[:match.start()].strip()
            print(f"  Обрезано по паттерну '{pattern}': '{org_name}' → '{trimmed}'")
            break
    
    return trimmed

# Тестовые случаи
test_cases = [
    "МИЛЛАБ для Абакан ЦГиЭ",
    "МИЛЛАБ \nАкутину Ивану Алексееви",
    "Компания МИЛЛАБ",
    "ООО Тестовая Компания для проекта",
    "Центр Диагностики от Иванова",
]

print("🧪 Тест обрезки названий организаций\n")

for test in test_cases:
    print(f"Исходное: '{test}'")
    result = trim_organization_name(test)
    print(f"Результат: '{result}'")
    print()
