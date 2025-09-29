#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Дополнительный тест для проверки Replicate провайдера
Проверяет работу Replicate провайдера отдельно и в сценарии fallback
"""

import sys
import os
import asyncio
import json
import time
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.providers import AsyncProviderManager
from src.providers.base_provider import ProviderConfig
from src.providers.openrouter import OpenRouterProvider
from src.providers.replicate import ReplicateProvider
from src.config.config_manager import UnifiedConfigManager


async def test_replicate_provider():
    """🧪 Тест Replicate провайдера"""
    print("🧪 ТЕСТ REPLICATE ПРОВАЙДЕРА")
    print("="*50)
    
    try:
        # Инициализация конфигурации
        config_manager = UnifiedConfigManager()
        providers_config = config_manager.get_llm_providers()
        
        # Находим Replicate провайдер
        replicate_config = None
        for provider_config in providers_config:
            if provider_config.name.lower() == 'replicate':
                replicate_config = provider_config
                break
        
        if not replicate_config:
            print("❌ Replicate провайдер не найден в конфигурации")
            return False
        
        print(f"✅ Найден Replicate провайдер:")
        print(f"   Модель: {replicate_config.model}")
        print(f"   Активен: {replicate_config.active}")
        print(f"   Приоритет: {replicate_config.priority}")
        
        # Создаем провайдер
        provider_config = ProviderConfig(
            name=replicate_config.name,
            api_key=replicate_config.api_key,
            model=replicate_config.model,
            base_url=replicate_config.base_url,
            priority=replicate_config.priority,
            active=replicate_config.active,
            timeout=replicate_config.timeout,
            max_retries=replicate_config.max_retries
        )
        
        replicate_provider = ReplicateProvider(provider_config)
        print(f"✅ Replicate провайдер создан")
        
        # Тестируем запрос
        test_prompt = "Извлеки контакты из текста: Иван Петров, ivan@test.com, +7-123-456-78-90"
        request_data = {
            'messages': [{'role': 'user', 'content': test_prompt}]
        }
        
        print(f"📝 Отправляем тестовый запрос...")
        start_time = time.time()
        
        result = await replicate_provider.make_request(request_data)
        
        processing_time = time.time() - start_time
        
        print(f"✅ Replicate ответил за {processing_time:.2f}с")
        print(f"   Провайдер: {result.get('provider', 'Unknown')}")
        print(f"   Модель: {result.get('model', 'Unknown')}")
        print(f"   Ответ: {len(result.get('content', ''))} символов")
        print(f"   Первые 200 символов: {result.get('content', '')[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования Replicate: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fallback_scenario():
    """🧪 Тест сценария fallback между провайдерами"""
    print("\n🧪 ТЕСТ FALLBACK СЦЕНАРИЯ")
    print("="*50)
    
    try:
        # Инициализация
        config_manager = UnifiedConfigManager()
        providers_config = config_manager.get_llm_providers()
        
        # Создаем провайдеры
        base_providers = []
        for llm_config in providers_config:
            if not llm_config.active:
                continue
                
            provider_config = ProviderConfig(
                name=llm_config.name,
                api_key=llm_config.api_key,
                model=llm_config.model,
                base_url=llm_config.base_url,
                priority=llm_config.priority,
                active=llm_config.active,
                timeout=llm_config.timeout,
                max_retries=llm_config.max_retries
            )
            
            if llm_config.name.lower() == 'openrouter':
                provider = OpenRouterProvider(provider_config)
            elif llm_config.name.lower() == 'replicate':
                provider = ReplicateProvider(provider_config)
            else:
                continue
                
            base_providers.append(provider)
            print(f"✅ Создан провайдер: {llm_config.name} (приоритет: {llm_config.priority})")
        
        if len(base_providers) < 2:
            print("❌ Недостаточно провайдеров для тестирования fallback")
            return False
        
        # Создаем менеджер
        async_manager = AsyncProviderManager(providers=base_providers)
        
        # Блокируем первый провайдер (с наивысшим приоритетом)
        first_provider = None
        for wrapper in async_manager.async_providers:
            if wrapper.provider.config.priority == 1:  # OpenRouter
                first_provider = wrapper.provider
                break
        
        if first_provider:
            print(f"🔧 Блокируем провайдер {first_provider.config.name} для тестирования fallback")
            # Искусственно активируем Circuit Breaker
            for i in range(5):
                first_provider.record_failure("test_fallback")
            
            print(f"   Circuit Breaker активирован: {first_provider.in_circuit_break}")
            print(f"   Провайдер доступен: {first_provider.is_available()}")
        
        # Тестируем запрос - должен пойти ко второму провайдеру
        test_prompt = "Найди организацию в тексте: ООО Тест, ИНН 1234567890"
        
        print(f"📝 Отправляем запрос (должен пойти к резервному провайдеру)...")
        start_time = time.time()
        
        result = await async_manager.make_request_async(test_prompt)
        
        processing_time = time.time() - start_time
        
        print(f"✅ Запрос обработан за {processing_time:.2f}с")
        print(f"   Использован провайдер: {result.get('provider', 'Unknown')}")
        print(f"   Модель: {result.get('model', 'Unknown')}")
        print(f"   Ответ: {len(result.get('content', ''))} символов")
        
        # Проверяем что использовался резервный провайдер
        used_provider = result.get('provider', '').lower()
        fallback_worked = used_provider != 'openrouter'
        
        print(f"🔄 Fallback сработал: {fallback_worked}")
        
        # Восстанавливаем первый провайдер
        if first_provider:
            first_provider.failure_count = 0
            first_provider.in_circuit_break = False
            first_provider.last_failure_time = None
            print(f"🔄 Провайдер {first_provider.config.name} восстановлен")
        
        return fallback_worked
        
    except Exception as e:
        print(f"❌ Ошибка тестирования fallback: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """🚀 Основная функция"""
    print("🧪 ДОПОЛНИТЕЛЬНОЕ ТЕСТИРОВАНИЕ REPLICATE ИНТЕГРАЦИИ")
    print("="*80)
    
    # Тест 1: Replicate провайдер
    test1_result = await test_replicate_provider()
    
    # Тест 2: Fallback сценарий
    test2_result = await test_fallback_scenario()
    
    # Итоги
    print("\n📊 ИТОГИ ДОПОЛНИТЕЛЬНОГО ТЕСТИРОВАНИЯ")
    print("="*50)
    print(f"✅ Тест Replicate провайдера: {'ПРОЙДЕН' if test1_result else 'ПРОВАЛЕН'}")
    print(f"✅ Тест Fallback сценария: {'ПРОЙДЕН' if test2_result else 'ПРОВАЛЕН'}")
    
    all_passed = test1_result and test2_result
    
    if all_passed:
        print(f"\n🎉 ВСЕ ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print(f"✅ Replicate провайдер работает корректно")
        print(f"✅ Fallback между провайдерами функционирует")
    else:
        print(f"\n⚠️ НЕКОТОРЫЕ ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ")
        if not test1_result:
            print(f"❌ Проблемы с Replicate провайдером")
        if not test2_result:
            print(f"❌ Проблемы с Fallback механизмом")
    
    return all_passed


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)