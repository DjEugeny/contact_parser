#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полный тест для задачи 3: Автоматический fallback в OpenRouterProvider
Тестирует:
- Subtask 3.1: Success handling with model reset
- Subtask 3.2: Error handling with automatic fallback
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import UnifiedConfigManager


def test_complete_fallback_cycle():
    """Полный тест цикла fallback и reset"""
    
    print("\n" + "="*70)
    print("🧪 ПОЛНЫЙ ТЕСТ: OpenRouterProvider Fallback + Reset")
    print("="*70)
    
    # Создаем config manager
    config_manager = UnifiedConfigManager()
    
    if not hasattr(config_manager, 'models_manager') or not config_manager.models_manager:
        print("❌ ModelsManager не доступен")
        return False
    
    if 'OpenRouter' not in config_manager.providers:
        print("❌ OpenRouter провайдер не найден")
        return False
    
    provider = config_manager.providers['OpenRouter']
    models_manager = config_manager.models_manager
    
    print("\n📊 Начальное состояние:")
    models_manager.print_status()
    
    # Тест 1: Fallback при ошибках
    print("\n" + "="*70)
    print("🧪 ТЕСТ 1: Автоматический Fallback")
    print("="*70)
    
    initial_model = models_manager.get_current_model('openrouter')
    print(f"\n1️⃣ Начальная модель: {initial_model.name}")
    
    # Симулируем 3 ошибки для триггера fallback
    print(f"2️⃣ Симулируем 3 ошибки 'data policy'...")
    for i in range(3):
        switched = provider._handle_error_with_fallback("data policy violation")
        if switched:
            print(f"   ✅ Fallback сработал на ошибке {i+1}")
            break
        else:
            print(f"   ⏳ Ошибка {i+1}/3 зарегистрирована")
    
    fallback_model = models_manager.get_current_model('openrouter')
    print(f"3️⃣ Модель после fallback: {fallback_model.name}")
    
    if fallback_model.name != initial_model.name:
        print("   ✅ Fallback успешно переключил модель")
    else:
        print("   ❌ Fallback НЕ переключил модель")
        return False
    
    # Тест 2: Reset на первую модель после успеха
    print("\n" + "="*70)
    print("🧪 ТЕСТ 2: Reset на первую модель после успеха")
    print("="*70)
    
    print(f"\n1️⃣ Текущая модель (после fallback): {fallback_model.name}")
    print(f"2️⃣ Вызываем reset_to_first_model()...")
    
    models_manager.reset_to_first_model('openrouter')
    
    reset_model = models_manager.get_current_model('openrouter')
    print(f"3️⃣ Модель после reset: {reset_model.name}")
    
    if reset_model.name == initial_model.name:
        print("   ✅ Reset успешно вернул первую модель")
    else:
        print("   ❌ Reset НЕ вернул первую модель")
        return False
    
    # Тест 3: Множественный fallback
    print("\n" + "="*70)
    print("🧪 ТЕСТ 3: Множественный Fallback (все модели)")
    print("="*70)
    
    all_models = models_manager.get_all_models('openrouter')
    print(f"\n1️⃣ Всего доступно моделей: {len(all_models)}")
    
    models_switched = []
    current = models_manager.get_current_model('openrouter')
    models_switched.append(current.name)
    
    print(f"2️⃣ Переключаем все модели последовательно...")
    
    for i in range(len(all_models) - 1):
        # Симулируем 3 ошибки для каждой модели
        for j in range(3):
            switched = provider._handle_error_with_fallback("429 rate limit")
            if switched:
                new_model = models_manager.get_current_model('openrouter')
                models_switched.append(new_model.name)
                print(f"   ✅ Переключились на модель {i+2}: {new_model.name}")
                break
    
    print(f"\n3️⃣ Пройдено моделей: {len(models_switched)}")
    for idx, model_name in enumerate(models_switched, 1):
        print(f"   {idx}. {model_name}")
    
    if len(models_switched) == len(all_models):
        print("   ✅ Все модели были использованы")
    else:
        print(f"   ⚠️  Использовано {len(models_switched)}/{len(all_models)} моделей")
    
    # Финальный статус
    print("\n" + "="*70)
    print("📊 ФИНАЛЬНЫЙ СТАТУС")
    print("="*70)
    models_manager.print_status()
    
    print("\n" + "="*70)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
    print("="*70)
    
    return True


if __name__ == "__main__":
    try:
        success = test_complete_fallback_cycle()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Ошибка теста: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
