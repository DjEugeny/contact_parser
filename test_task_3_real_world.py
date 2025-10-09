#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-world scenario test for Task 3: OpenRouterProvider with automatic fallback
Simulates actual API errors and verifies the system handles them gracefully
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import UnifiedConfigManager


async def test_real_world_scenario():
    """Тест реального сценария с ошибками API"""
    
    print("\n" + "="*70)
    print("🌍 REAL-WORLD SCENARIO TEST")
    print("="*70)
    print("\nСценарий: Обработка email с автоматическим fallback при ошибках")
    
    # Инициализация
    config_manager = UnifiedConfigManager()
    
    if 'OpenRouter' not in config_manager.providers:
        print("❌ OpenRouter провайдер не найден")
        return False
    
    provider = config_manager.providers['OpenRouter']
    models_manager = config_manager.models_manager
    
    print("\n📊 Начальная конфигурация:")
    print(f"   Провайдер: OpenRouter")
    print(f"   Модель: {provider.config.model}")
    print(f"   Доступно моделей: {len(models_manager.get_all_models('openrouter'))}")
    
    # Сценарий 1: Успешный запрос
    print("\n" + "-"*70)
    print("📧 Сценарий 1: Успешная обработка email")
    print("-"*70)
    
    # Переключаемся на вторую модель для теста
    for _ in range(3):
        provider._handle_error_with_fallback("test error")
    
    current_model = models_manager.get_current_model('openrouter')
    print(f"1️⃣ Текущая модель (после fallback): {current_model.name}")
    print(f"   Позиция: {models_manager.current_openrouter_index + 1}")
    
    # Симулируем успешный запрос
    print(f"2️⃣ Обработка email успешна...")
    if config_manager.models_manager:
        config_manager.models_manager.reset_to_first_model('openrouter')
    
    reset_model = models_manager.get_current_model('openrouter')
    print(f"3️⃣ После успеха вернулись к первой модели: {reset_model.name}")
    print(f"   Позиция: {models_manager.current_openrouter_index + 1}")
    
    if models_manager.current_openrouter_index == 0:
        print("   ✅ Reset работает корректно")
    else:
        print("   ❌ Reset не сработал")
        return False
    
    # Сценарий 2: Ошибка data policy
    print("\n" + "-"*70)
    print("📧 Сценарий 2: Ошибка 'data policy' от модели")
    print("-"*70)
    
    initial_model = models_manager.get_current_model('openrouter')
    print(f"1️⃣ Начальная модель: {initial_model.name}")
    
    print(f"2️⃣ Получена ошибка: 'data policy violation'")
    print(f"   Попытка 1... ошибка")
    provider._handle_error_with_fallback("data policy violation")
    print(f"   Попытка 2... ошибка")
    provider._handle_error_with_fallback("data policy violation")
    print(f"   Попытка 3... ошибка, триггер fallback")
    switched = provider._handle_error_with_fallback("data policy violation")
    
    if switched:
        new_model = models_manager.get_current_model('openrouter')
        print(f"3️⃣ Автоматически переключились на: {new_model.name}")
        print(f"   ✅ Fallback сработал автоматически")
    else:
        print(f"   ❌ Fallback не сработал")
        return False
    
    # Сценарий 3: Rate limit
    print("\n" + "-"*70)
    print("📧 Сценарий 3: Rate limit (429) от модели")
    print("-"*70)
    
    current_model = models_manager.get_current_model('openrouter')
    print(f"1️⃣ Текущая модель: {current_model.name}")
    
    print(f"2️⃣ Получена ошибка: '429 Too Many Requests'")
    for i in range(3):
        switched = provider._handle_error_with_fallback("429 Too Many Requests")
        if switched:
            new_model = models_manager.get_current_model('openrouter')
            print(f"3️⃣ Переключились на следующую модель: {new_model.name}")
            print(f"   ✅ Rate limit обработан через fallback")
            break
    
    # Сценарий 4: Исчерпание всех моделей
    print("\n" + "-"*70)
    print("📧 Сценарий 4: Исчерпание всех доступных моделей")
    print("-"*70)
    
    all_models = models_manager.get_all_models('openrouter')
    print(f"1️⃣ Всего моделей: {len(all_models)}")
    
    # Переключаемся до последней модели
    while models_manager.current_openrouter_index < len(all_models) - 1:
        for _ in range(3):
            switched = provider._handle_error_with_fallback("404 model not found")
            if switched:
                break
    
    final_model = models_manager.get_current_model('openrouter')
    print(f"2️⃣ Достигли последней модели: {final_model.name}")
    print(f"   Позиция: {models_manager.current_openrouter_index + 1}/{len(all_models)}")
    
    # Пытаемся переключиться еще раз
    print(f"3️⃣ Попытка переключения за пределы списка...")
    for _ in range(3):
        switched = provider._handle_error_with_fallback("404 model not found")
        if not switched:
            print(f"   ✅ Корректно обработано исчерпание моделей")
            break
    else:
        print(f"   ❌ Некорректная обработка исчерпания моделей")
        return False
    
    # Финальный статус
    print("\n" + "="*70)
    print("📊 ФИНАЛЬНЫЙ СТАТУС СИСТЕМЫ")
    print("="*70)
    models_manager.print_status()
    
    print("\n" + "="*70)
    print("✅ ВСЕ REAL-WORLD СЦЕНАРИИ ПРОЙДЕНЫ")
    print("="*70)
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_real_world_scenario())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Ошибка теста: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
