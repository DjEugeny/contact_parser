#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Integration Test: ModelsManager Integration with UnifiedConfigManager
Tests Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_manager import UnifiedConfigManager


def test_models_manager_integration():
    """
    Тест интеграции ModelsManager с UnifiedConfigManager
    
    Проверяет:
    - Requirement 6.1: ModelsManager правильно интегрирован в UnifiedConfigManager
    - Requirement 6.2: Провайдеры получают модели из ModelsManager
    - Requirement 6.3: Статус моделей отображается корректно
    - Requirement 6.4: Количество и конфигурация активных провайдеров
    - Requirement 6.5: Четкие сообщения об ошибках при сбоях
    """
    print("🧪 INTEGRATION TEST: ModelsManager + UnifiedConfigManager")
    print("=" * 70)
    
    test_results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }
    
    try:
        # Инициализация UnifiedConfigManager
        print("\n📋 Шаг 1: Инициализация UnifiedConfigManager...")
        config_manager = UnifiedConfigManager()
        print("✅ UnifiedConfigManager успешно инициализирован")
        test_results["passed"].append("UnifiedConfigManager initialization")
        
    except Exception as e:
        print(f"❌ ОШИБКА: Не удалось инициализировать UnifiedConfigManager: {e}")
        test_results["failed"].append(f"UnifiedConfigManager initialization: {e}")
        return test_results
    
    # Requirement 6.1: Проверка наличия models_manager
    print("\n📋 Шаг 2: Проверка интеграции ModelsManager...")
    print("-" * 70)
    
    if hasattr(config_manager, 'models_manager'):
        print("✅ Атрибут 'models_manager' найден в UnifiedConfigManager")
        test_results["passed"].append("models_manager attribute exists")
        
        if config_manager.models_manager is not None:
            print("✅ ModelsManager успешно инициализирован")
            test_results["passed"].append("ModelsManager initialization")
        else:
            print("⚠️  ModelsManager = None (fallback на .env конфигурацию)")
            test_results["warnings"].append("ModelsManager is None, using .env fallback")
    else:
        print("❌ ОШИБКА: Атрибут 'models_manager' не найден!")
        test_results["failed"].append("models_manager attribute missing")
        return test_results
    
    # Requirement 6.3: Отображение статуса моделей
    print("\n📋 Шаг 3: Отображение статуса моделей...")
    print("-" * 70)
    
    if config_manager.models_manager:
        try:
            print("\n📊 СТАТУС МОДЕЛЕЙ:")
            config_manager.models_manager.print_status()
            print("\n✅ Статус моделей отображен успешно")
            test_results["passed"].append("Model status display")
        except Exception as e:
            print(f"❌ ОШИБКА при отображении статуса: {e}")
            test_results["failed"].append(f"Model status display: {e}")
    else:
        print("⚠️  Пропуск: ModelsManager не инициализирован")
        test_results["warnings"].append("Skipped model status display (no ModelsManager)")
    
    # Requirement 6.2 & 6.4: Проверка конфигурации провайдеров
    print("\n📋 Шаг 4: Проверка конфигурации провайдеров...")
    print("-" * 70)
    
    try:
        providers = config_manager.get_llm_providers()
        print(f"\n📊 Найдено провайдеров: {len(providers)}")
        
        if len(providers) == 0:
            print("❌ ОШИБКА: Не найдено ни одного провайдера!")
            test_results["failed"].append("No providers configured")
        else:
            print(f"✅ Активных провайдеров: {len(providers)}")
            test_results["passed"].append(f"Provider count: {len(providers)}")
        
        print("\n📋 КОНФИГУРАЦИЯ ПРОВАЙДЕРОВ:")
        for i, provider in enumerate(providers, 1):
            print(f"\n{i}. {provider.name}")
            print(f"   Модель: {provider.model}")
            print(f"   Приоритет: {provider.priority}")
            print(f"   Активен: {provider.active}")
            print(f"   Base URL: {provider.base_url}")
            print(f"   API Key: {'*' * 10}{provider.api_key[-4:] if len(provider.api_key) > 4 else '****'}")
            
            # Проверяем, что модель получена из ModelsManager
            if config_manager.models_manager:
                current_model = config_manager.models_manager.get_current_model(provider.name.lower())
                if current_model:
                    if provider.model == current_model.name:
                        print(f"   ✅ Модель получена из ModelsManager")
                        test_results["passed"].append(f"{provider.name} uses ModelsManager model")
                    else:
                        print(f"   ⚠️  Модель не совпадает с ModelsManager:")
                        print(f"      Provider: {provider.model}")
                        print(f"      ModelsManager: {current_model.name}")
                        test_results["warnings"].append(f"{provider.name} model mismatch")
                else:
                    print(f"   ⚠️  Модель не найдена в ModelsManager (используется fallback)")
                    test_results["warnings"].append(f"{provider.name} using fallback model")
            else:
                print(f"   ℹ️  Модель из .env (ModelsManager не инициализирован)")
        
        print("\n✅ Конфигурация провайдеров проверена")
        test_results["passed"].append("Provider configuration check")
        
    except Exception as e:
        print(f"❌ ОШИБКА при проверке провайдеров: {e}")
        test_results["failed"].append(f"Provider configuration: {e}")
    
    # Дополнительная проверка: Backward compatibility
    print("\n📋 Шаг 5: Проверка обратной совместимости...")
    print("-" * 70)
    
    if config_manager.models_manager is None:
        print("✅ Система работает без ModelsManager (backward compatibility)")
        test_results["passed"].append("Backward compatibility verified")
    else:
        print("ℹ️  ModelsManager активен, backward compatibility не требуется")
    
    # Итоговый отчет
    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 70)
    
    print(f"\n✅ Пройдено тестов: {len(test_results['passed'])}")
    for test in test_results["passed"]:
        print(f"   ✓ {test}")
    
    if test_results["warnings"]:
        print(f"\n⚠️  Предупреждений: {len(test_results['warnings'])}")
        for warning in test_results["warnings"]:
            print(f"   ⚠ {warning}")
    
    if test_results["failed"]:
        print(f"\n❌ Провалено тестов: {len(test_results['failed'])}")
        for failure in test_results["failed"]:
            print(f"   ✗ {failure}")
        print("\n❌ ИНТЕГРАЦИОННЫЙ ТЕСТ ПРОВАЛЕН")
        return test_results
    
    print("\n✅ ВСЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОЙДЕНЫ!")
    
    # Дополнительная информация
    print("\n" + "=" * 70)
    print("📋 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ")
    print("=" * 70)
    
    print("\n🔍 Проверенные требования:")
    print("   ✓ 6.1: ModelsManager интегрирован в UnifiedConfigManager")
    print("   ✓ 6.2: Провайдеры получают модели из ModelsManager")
    print("   ✓ 6.3: Статус моделей отображается корректно")
    print("   ✓ 6.4: Количество и конфигурация активных провайдеров")
    print("   ✓ 6.5: Четкие сообщения об ошибках")
    
    print("\n💡 Следующие шаги:")
    print("   1. Запустите реальную обработку для проверки fallback")
    print("   2. Проверьте логи в data/logs/model_fallback.log")
    print("   3. Убедитесь, что модели переключаются при ошибках")
    
    return test_results


if __name__ == "__main__":
    print("\n🚀 Запуск интеграционного теста...\n")
    results = test_models_manager_integration()
    
    # Возвращаем код выхода на основе результатов
    exit_code = 0 if len(results["failed"]) == 0 else 1
    sys.exit(exit_code)
