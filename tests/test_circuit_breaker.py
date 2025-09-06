#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест Circuit Breaker функциональности
"""

import sys
sys.path.append('src')
from llm_extractor import ContactExtractor

def test_circuit_breaker():
    """Тест Circuit Breaker паттерна"""
    print("🧪 Тестирование Circuit Breaker...")

    extractor = ContactExtractor(test_mode=True)

    # Тестируем начальное состояние
    print("\n1. Начальное состояние провайдеров:")
    for pid, provider in extractor.providers.items():
        circuit_break = extractor._is_provider_in_circuit_break(pid)
        print(f"   {provider['name']}: failures={provider['failure_count']}, circuit_break={circuit_break}")

    # Симулируем множественные неудачи для OpenRouter
    print("\n2. Симуляция 5 неудач для OpenRouter:")
    for i in range(5):
        extractor.providers['openrouter']['failure_count'] += 1
        if i == 4:  # После 5-й неудачи
            extractor.providers['openrouter']['last_failure'] = '2025-01-01T12:00:00'
            circuit_break = extractor._is_provider_in_circuit_break('openrouter')
            print(f"   После {i+1} неудач: circuit_break={circuit_break}")

    # Тестируем переключение провайдеров
    print("\n3. Тестирование переключения провайдеров:")
    current_before = extractor.current_provider
    switched = extractor._switch_to_next_provider()
    current_after = extractor.current_provider

    print(f"   Переключение: {current_before} -> {current_after}, успех={switched}")

    # Тестируем circuit break блокировку
    print("\n4. Тестирование блокировки circuit break:")
    extractor.current_provider = 'openrouter'  # Переключаемся на заблокированный
    can_switch = extractor._switch_to_next_provider()
    print(f"   Попытка переключения с заблокированного провайдера: {can_switch}")

    print("\n✅ Тест Circuit Breaker завершен")

if __name__ == "__main__":
    test_circuit_breaker()
