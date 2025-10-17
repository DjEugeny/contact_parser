#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тест фильтра массовой рассылки"""

import sys
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import logging

# Настраиваем логгер
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Импортируем после настройки путей
from src.advanced_email_fetcher import EmailFilters

def test_mass_mailing_filter():
    """Тест фильтра массовой рассылки"""
    
    config_dir = Path(__file__).parent / "config"
    filters = EmailFilters(config_dir, logger)
    
    print("🧪 Тестирование фильтра массовой рассылки:")
    print("="*70)
    
    test_cases = [
        {
            'name': 'Внешний отправитель с 15 получателями',
            'from_addr': 'partner@external-company.com',
            'to_addrs': [f'user{i}@dna-technology.ru' for i in range(15)],
            'expected': None,  # НЕ должен фильтроваться
        },
        {
            'name': 'Внутренний отправитель с 15 получателями',
            'from_addr': 'admin@dna-technology.ru',
            'to_addrs': [f'user{i}@dna-technology.ru' for i in range(15)],
            'expected': 'массовая',  # Должен фильтроваться
        },
        {
            'name': 'Внутренний отправитель с 5 получателями',
            'from_addr': 'admin@dna-technology.ru',
            'to_addrs': [f'user{i}@dna-technology.ru' for i in range(5)],
            'expected': None,  # НЕ должен фильтроваться (меньше порога)
        },
        {
            'name': 'Внешний отправитель с 1 внутренним получателем',
            'from_addr': 'partner@external-company.com',
            'to_addrs': ['s.voronova@dna-technology.ru'],
            'expected': None,  # НЕ должен фильтроваться
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = filters.is_internal_mass_mailing(
            test['from_addr'],
            test['to_addrs']
        )
        
        if test['expected'] is None:
            if result is None:
                print(f"✅ {test['name']}: НЕ фильтруется (правильно)")
                passed += 1
            else:
                print(f"❌ {test['name']}: Фильтруется (ошибка!)")
                print(f"   Результат: {result}")
                failed += 1
        else:
            if result and test['expected'] in result:
                print(f"✅ {test['name']}: Фильтруется (правильно)")
                print(f"   Причина: {result}")
                passed += 1
            else:
                print(f"❌ {test['name']}: НЕ фильтруется (ошибка!)")
                failed += 1
    
    print("="*70)
    print(f"Результаты: ✅ {passed} пройдено, ❌ {failed} провалено")
    
    return failed == 0

if __name__ == "__main__":
    success = test_mass_mailing_filter()
    sys.exit(0 if success else 1)
