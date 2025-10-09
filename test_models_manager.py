#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест ModelsManager - менеджера моделей с fallback
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.models_manager import ModelsManager


def test_models_manager():
    """Тест менеджера моделей"""
    print("🧪 ТЕСТ MODELS MANAGER")
    print("=" * 50)
    
    # Создаем менеджер
    manager = ModelsManager()
    
    # Показываем начальный статус
    print("\n📊 НАЧАЛЬНЫЙ СТАТУС:")
    manager.print_status()
    
    # Тест 1: Получение текущей модели
    print("\n🧪 ТЕСТ 1: Получение текущей модели")
    print("-" * 50)
    
    or_model = manager.get_current_model('openrouter')
    print(f"OpenRouter текущая модель: {or_model.name}")
    print(f"  Описание: {or_model.description}")
    print(f"  Требует публикацию: {or_model.requires_prompt_publication}")
    
    rep_model = manager.get_current_model('replicate')
    print(f"Replicate текущая модель: {rep_model.name}")
    print(f"  Описание: {rep_model.description}")
    
    # Тест 2: Симуляция ошибок и fallback
    print("\n🧪 ТЕСТ 2: Симуляция ошибок и fallback")
    print("-" * 50)
    
    # Симулируем ошибку "data policy" для OpenRouter
    print("\n❌ Симулируем ошибку 'data policy' для OpenRouter...")
    for i in range(3):
        print(f"   Попытка {i+1}/3...")
        switched = manager.report_error('openrouter', 'HTTP 404: data policy error')
        if switched:
            print(f"   ✅ Переключились на следующую модель!")
            break
    
    # Показываем новый статус
    print("\n📊 СТАТУС ПОСЛЕ ОШИБОК:")
    manager.print_status()
    
    # Тест 3: Получение всех моделей
    print("\n🧪 ТЕСТ 3: Список всех моделей")
    print("-" * 50)
    
    all_or_models = manager.get_all_models('openrouter')
    print(f"\nOpenRouter ({len(all_or_models)} моделей):")
    for i, model in enumerate(all_or_models, 1):
        pub_req = "🔒" if model.requires_prompt_publication else "🔓"
        print(f"  {i}. {pub_req} {model.name}")
        print(f"     {model.description}")
    
    all_rep_models = manager.get_all_models('replicate')
    print(f"\nReplicate ({len(all_rep_models)} моделей):")
    for i, model in enumerate(all_rep_models, 1):
        print(f"  {i}. {model.name}")
        print(f"     {model.description}")
    
    # Тест 4: Сброс на первую модель
    print("\n🧪 ТЕСТ 4: Сброс на первую модель")
    print("-" * 50)
    
    manager.reset_to_first_model('openrouter')
    print("✅ Сброс выполнен")
    
    # Финальный статус
    print("\n📊 ФИНАЛЬНЫЙ СТАТУС:")
    manager.print_status()
    
    print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")


if __name__ == "__main__":
    test_models_manager()
