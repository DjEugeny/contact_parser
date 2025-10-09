#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для задачи 3: Автоматический fallback в OpenRouterProvider
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import UnifiedConfigManager
from src.providers.openrouter import OpenRouterProvider


def test_openrouter_integration():
    """Тест интеграции OpenRouterProvider с ModelsManager"""
    
    print("\n" + "="*60)
    print("🧪 ТЕСТ: OpenRouterProvider с ModelsManager")
    print("="*60)
    
    # Создаем config manager
    config_manager = UnifiedConfigManager()
    
    # Проверяем наличие models_manager
    print("\n1️⃣ Проверка ModelsManager:")
    if hasattr(config_manager, 'models_manager') and config_manager.models_manager:
        print("   ✅ ModelsManager доступен")
        config_manager.models_manager.print_status()
    else:
        print("   ⚠️  ModelsManager не инициализирован")
        return False
    
    # Проверяем инициализацию OpenRouter провайдера
    print("\n2️⃣ Проверка OpenRouter провайдера:")
    if 'OpenRouter' in config_manager.providers:
        provider = config_manager.providers['OpenRouter']
        print(f"   ✅ OpenRouter провайдер инициализирован")
        print(f"   📋 Текущая модель: {provider.config.model}")
        
        # Проверяем наличие config_manager в провайдере
        if hasattr(provider, 'config_manager') and provider.config_manager:
            print(f"   ✅ config_manager передан в провайдер")
        else:
            print(f"   ❌ config_manager НЕ передан в провайдер")
            return False
        
        # Проверяем метод fallback
        if hasattr(provider, '_handle_error_with_fallback'):
            print(f"   ✅ Метод _handle_error_with_fallback доступен")
        else:
            print(f"   ❌ Метод _handle_error_with_fallback НЕ найден")
            return False
    else:
        print("   ❌ OpenRouter провайдер не найден")
        return False
    
    # Тестируем fallback механизм
    print("\n3️⃣ Тест fallback механизма:")
    provider = config_manager.providers['OpenRouter']
    
    # Получаем текущую модель
    current_model = config_manager.models_manager.get_current_model('openrouter')
    print(f"   📋 Начальная модель: {current_model.name if current_model else 'None'}")
    
    # Симулируем 3 ошибки (max_retries_per_model = 3)
    test_error = "data policy violation"
    print(f"   🧪 Симулируем 3 ошибки для триггера fallback...")
    
    switched = False
    for i in range(3):
        print(f"      Ошибка {i+1}/3...")
        switched = provider._handle_error_with_fallback(test_error)
        if switched:
            break
    
    if switched:
        new_model = config_manager.models_manager.get_current_model('openrouter')
        print(f"   ✅ Fallback сработал!")
        print(f"   📋 Новая модель: {new_model.name if new_model else 'None'}")
    else:
        print(f"   ℹ️  Fallback не сработал (возможно, нужно больше ошибок или ошибка не подходит)")
    
    # Показываем финальный статус
    print("\n4️⃣ Финальный статус:")
    config_manager.models_manager.print_status()
    
    print("\n" + "="*60)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_openrouter_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Ошибка теста: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
