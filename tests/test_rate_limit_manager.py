#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тесты для адаптивного менеджера rate limit
"""

import sys
import time
from pathlib import Path

# Добавляем src в путь для импорта
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from rate_limit_manager import RateLimitManager, RequestResult


def test_basic_functionality():
    """Тест базовой функциональности менеджера"""
    print("🧪 Тест базовой функциональности...")
    
    # Создаем менеджер с короткими задержками для тестирования
    manager = RateLimitManager(
        initial_delay=2.0,
        min_delay=1.0,
        max_delay=5.0
    )
    
    # Проверяем начальное состояние
    stats = manager.get_statistics()
    print(f"   📊 Начальная задержка: {stats['current_delay']:.1f}с")
    assert stats['current_delay'] == 2.0
    
    # Тестируем успешный запрос
    delay = manager.wait_if_needed()
    print(f"   ⏳ Первая задержка: {delay:.1f}с")
    manager.record_request('success')
    
    # После успешного запроса задержка должна уменьшиться
    stats = manager.get_statistics()
    print(f"   📊 Задержка после успеха: {stats['current_delay']:.1f}с")
    assert stats['current_delay'] < 2.0
    
    print("   ✅ Базовая функциональность работает")


def test_rate_limit_adaptation():
    """Тест адаптации к ошибкам rate limit"""
    print("\n🧪 Тест адаптации к rate limit...")
    
    manager = RateLimitManager(
        initial_delay=1.0,
        min_delay=0.5,
        max_delay=3.0
    )
    
    initial_delay = manager.get_statistics()['current_delay']
    print(f"   📊 Начальная задержка: {initial_delay:.1f}с")
    
    # Симулируем ошибку rate limit
    manager.record_request('rate_limit_error')
    
    after_error_delay = manager.get_statistics()['current_delay']
    print(f"   📊 Задержка после rate limit: {after_error_delay:.1f}с")
    
    # Задержка должна увеличиться
    assert after_error_delay > initial_delay
    
    # Симулируем несколько успешных запросов
    for i in range(3):
        manager.record_request('success')
        delay = manager.get_statistics()['current_delay']
        print(f"   📊 Задержка после успеха #{i+1}: {delay:.1f}с")
    
    final_delay = manager.get_statistics()['current_delay']
    print(f"   📊 Финальная задержка: {final_delay:.1f}с")
    
    # После успешных запросов задержка должна уменьшиться
    assert final_delay < after_error_delay
    
    print("   ✅ Адаптация к rate limit работает")


def test_statistics():
    """Тест сбора статистики"""
    print("\n🧪 Тест статистики...")
    
    manager = RateLimitManager(initial_delay=1.0)
    
    # Записываем разные типы результатов
    manager.record_request('success')
    manager.record_request('rate_limit_error')
    manager.record_request('timeout')
    manager.record_request('other_error')
    
    stats = manager.get_statistics()
    print(f"   📊 Статистика: {stats}")
    
    # Проверяем, что статистика собирается
    assert stats['total_requests'] == 4
    assert 'recent_success_rate' in stats
    assert 'consecutive_errors' in stats
    
    print("   ✅ Статистика работает")


def test_reset():
    """Тест сброса состояния"""
    print("\n🧪 Тест сброса состояния...")
    
    manager = RateLimitManager(initial_delay=2.0)
    
    # Изменяем состояние
    manager.record_request('rate_limit_error')
    manager.record_request('success')
    
    stats_before = manager.get_statistics()
    print(f"   📊 До сброса: {stats_before['total_requests']} запросов")
    
    # Сбрасываем
    manager.reset()
    
    stats_after = manager.get_statistics()
    print(f"   📊 После сброса: {stats_after['total_requests']} запросов")
    
    # Проверяем сброс
    assert stats_after['total_requests'] == 0
    assert stats_after['current_delay'] == 2.0
    
    print("   ✅ Сброс работает")


def main():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов RateLimitManager\n")
    
    try:
        test_basic_functionality()
        test_rate_limit_adaptation()
        test_statistics()
        test_reset()
        
        print("\n🎉 Все тесты пройдены успешно!")
        
    except Exception as e:
        print(f"\n❌ Тест провален: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())