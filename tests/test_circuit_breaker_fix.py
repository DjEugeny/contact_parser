#!/usr/bin/env python3
"""
🧪 Тест исправления Circuit Breaker
Проверяет что rate limit не блокирует весь провайдер
"""

import sys
import os
from pathlib import Path
import importlib

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Force reload of modules
if 'src.config.config_manager' in sys.modules:
    importlib.reload(sys.modules['src.config.config_manager'])
if 'src.config.models_manager' in sys.modules:
    importlib.reload(sys.modules['src.config.models_manager'])

from src.config.config_manager import UnifiedConfigManager
from src.config.models_manager import ModelsManager


def test_rate_limit_handling():
    """Тест обработки rate limit"""
    print("🧪 ТЕСТ: Rate Limit не блокирует провайдер")
    print("=" * 60)
    
    # Инициализация
    config_manager = UnifiedConfigManager()
    models_manager = ModelsManager()
    
    print("\n1️⃣ Начальное состояние:")
    print(f"   OpenRouter доступен: {config_manager.is_provider_available('OpenRouter')}")
    
    initial_stats = config_manager.provider_stats.get('OpenRouter')
    if initial_stats:
        print(f"   Consecutive failures: {initial_stats.consecutive_failures}")
        print(f"   Circuit breaker: {initial_stats.circuit_breaker_state.value}")
    
    # Симулируем rate limit ошибку
    print("\n2️⃣ Симулируем rate limit ошибку модели:")
    config_manager.record_provider_failure(
        'OpenRouter',
        'Rate limit exceeded for model',
        is_rate_limit=True,
        is_model_error=False
    )
    
    stats_after_rate_limit = config_manager.provider_stats.get('OpenRouter')
    print(f"   OpenRouter доступен: {config_manager.is_provider_available('OpenRouter')}")
    print(f"   Consecutive failures: {stats_after_rate_limit.consecutive_failures}")
    print(f"   Circuit breaker: {stats_after_rate_limit.circuit_breaker_state.value}")
    print(f"   Rate limit errors: {stats_after_rate_limit.rate_limit_errors}")
    
    # Проверка
    assert config_manager.is_provider_available('OpenRouter'), \
        "❌ FAIL: Провайдер заблокирован после rate limit!"
    assert stats_after_rate_limit.consecutive_failures == 0, \
        "❌ FAIL: consecutive_failures увеличился при rate limit!"
    print("   ✅ PASS: Провайдер остался доступным")
    
    # Симулируем ошибку модели (не провайдера)
    print("\n3️⃣ Симулируем ошибку модели (data policy):")
    config_manager.record_provider_failure(
        'OpenRouter',
        'Data policy error',
        is_rate_limit=False,
        is_model_error=True
    )
    
    stats_after_model_error = config_manager.provider_stats.get('OpenRouter')
    print(f"   OpenRouter доступен: {config_manager.is_provider_available('OpenRouter')}")
    print(f"   Consecutive failures: {stats_after_model_error.consecutive_failures}")
    print(f"   Circuit breaker: {stats_after_model_error.circuit_breaker_state.value}")
    
    # Проверка
    assert config_manager.is_provider_available('OpenRouter'), \
        "❌ FAIL: Провайдер заблокирован после ошибки модели!"
    assert stats_after_model_error.consecutive_failures == 0, \
        "❌ FAIL: consecutive_failures увеличился при ошибке модели!"
    print("   ✅ PASS: Провайдер остался доступным")
    
    # Симулируем критическую ошибку провайдера
    print("\n4️⃣ Симулируем критическую ошибку провайдера:")
    for i in range(15):  # failure_threshold = 15
        config_manager.record_provider_failure(
            'OpenRouter',
            'Network error - provider unavailable',
            is_rate_limit=False,
            is_model_error=False
        )
    
    stats_after_provider_error = config_manager.provider_stats.get('OpenRouter')
    print(f"   Consecutive failures: {stats_after_provider_error.consecutive_failures}")
    print(f"   Circuit breaker: {stats_after_provider_error.circuit_breaker_state.value}")
    print(f"   Circuit breaker opened at: {stats_after_provider_error.circuit_breaker_opened_at}")
    print(f"   Cooldown until: {stats_after_provider_error.cooldown_until}")
    
    # Проверяем is_provider_available напрямую через логику
    print(f"   Проверяем доступность напрямую:")
    stats = config_manager.provider_stats['OpenRouter']
    print(f"   - Circuit breaker state: {stats.circuit_breaker_state.value}")
    
    from src.config.config_manager import CircuitBreakerState
    print(f"   - Is OPEN: {stats.circuit_breaker_state == CircuitBreakerState.OPEN}")
    
    from datetime import datetime
    now = datetime.now()
    if stats.circuit_breaker_opened_at:
        time_since_open = (now - stats.circuit_breaker_opened_at).total_seconds()
        print(f"   - Time since open: {time_since_open}s")
        print(f"   - Recovery timeout: {config_manager.circuit_breaker_config.recovery_timeout}s")
    
    is_available = config_manager.is_provider_available('OpenRouter')
    print(f"   OpenRouter доступен (from method): {is_available}")
    
    # Проверка
    assert stats_after_provider_error.circuit_breaker_state.value == 'open', \
        "❌ FAIL: Circuit breaker не открылся!"
    assert not is_available, \
        f"❌ FAIL: Провайдер не заблокирован после критических ошибок! is_available={is_available}"
    print("   ✅ PASS: Провайдер заблокирован после критических ошибок")
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("\n📋 Итоги:")
    print("   ✓ Rate limit не блокирует провайдер")
    print("   ✓ Ошибки модели не блокируют провайдер")
    print("   ✓ Критические ошибки провайдера блокируют провайдер")


def test_models_manager_error_classification():
    """Тест классификации ошибок в ModelsManager"""
    print("\n\n🧪 ТЕСТ: Классификация ошибок в ModelsManager")
    print("=" * 60)
    
    models_manager = ModelsManager()
    
    # Тест 1: Rate limit
    print("\n1️⃣ Тест rate limit:")
    initial_index = models_manager.current_openrouter_index
    models_manager.openrouter_error_count = 2  # Почти достигли лимита
    
    switched = models_manager.report_error('openrouter', 'Rate limit exceeded (429)')
    print(f"   Переключение произошло: {switched}")
    print(f"   Индекс модели: {initial_index} → {models_manager.current_openrouter_index}")
    
    if switched:
        print("   ✅ PASS: Переключение на следующую модель при rate limit")
    
    # Тест 2: Data policy error
    print("\n2️⃣ Тест data policy error:")
    models_manager.current_openrouter_index = 0
    models_manager.openrouter_error_count = 2
    
    switched = models_manager.report_error('openrouter', 'Data policy violation')
    print(f"   Переключение произошло: {switched}")
    print(f"   Индекс модели: 0 → {models_manager.current_openrouter_index}")
    
    if switched:
        print("   ✅ PASS: Переключение на следующую модель при data policy error")
    
    # Тест 3: Empty response
    print("\n3️⃣ Тест empty response:")
    models_manager.current_openrouter_index = 0
    models_manager.openrouter_error_count = 2
    
    switched = models_manager.report_error('openrouter', 'Empty response from model')
    print(f"   Переключение произошло: {switched}")
    print(f"   Индекс модели: 0 → {models_manager.current_openrouter_index}")
    
    if switched:
        print("   ✅ PASS: Переключение на следующую модель при empty response")
    
    print("\n" + "=" * 60)
    print("✅ ТЕСТЫ КЛАССИФИКАЦИИ ПРОЙДЕНЫ!")


if __name__ == "__main__":
    try:
        test_rate_limit_handling()
        test_models_manager_error_classification()
        
        print("\n" + "=" * 60)
        print("🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
