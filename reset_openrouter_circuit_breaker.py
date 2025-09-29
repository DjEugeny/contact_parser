#!/usr/bin/env python3
"""
🔄 ПРИНУДИТЕЛЬНЫЙ СБРОС Circuit Breaker для OpenRouter
Цель: Сбросить состояние Circuit Breaker и протестировать OpenRouter
"""

import sys
import os
import asyncio
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def reset_and_test_openrouter():
    """Сброс Circuit Breaker и тест OpenRouter"""
    print("🔄 ПРИНУДИТЕЛЬНЫЙ СБРОС Circuit Breaker для OpenRouter")
    print("=" * 60)
    
    try:
        # Импортируем после добавления src в путь
        from providers.openrouter import OpenRouterProvider
        from config.config_manager import LLMProviderConfig
        
        # Создаем конфигурацию
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print("❌ OPENROUTER_API_KEY не найден")
            return
        
        config = LLMProviderConfig(
            name="OpenRouter",
            api_key=api_key,
            model="deepseek/deepseek-chat-v3.1:free",
            base_url="https://openrouter.ai/api/v1",
            max_tokens=100,
            temperature=0.1
        )
        
        # Создаем провайдер
        provider = OpenRouterProvider(config)
        
        print(f"✅ Провайдер создан: {provider.config.name}")
        print(f"🔧 Модель: {provider.config.model}")
        
        # Показываем текущее состояние
        stats = provider.get_stats()
        print(f"📊 Текущее состояние:")
        print(f"   🔄 Circuit Break: {stats.get('in_circuit_break', False)}")
        print(f"   ❌ Ошибки подряд: {stats.get('failure_count', 0)}")
        print(f"   📈 Успешность: {stats.get('success_rate', 0):.1%}")
        
        # ПРИНУДИТЕЛЬНЫЙ СБРОС
        print("\n🔄 Выполняем принудительный сброс...")
        provider.reset_stats()
        
        # Проверяем состояние после сброса
        stats_after = provider.get_stats()
        print(f"✅ Состояние после сброса:")
        print(f"   🔄 Circuit Break: {stats_after.get('in_circuit_break', False)}")
        print(f"   ❌ Ошибки подряд: {stats_after.get('failure_count', 0)}")
        print(f"   📈 Успешность: {stats_after.get('success_rate', 0):.1%}")
        
        # Проверяем доступность
        is_available = provider.is_available()
        print(f"   ✅ Доступен: {is_available}")
        
        if not is_available:
            print("❌ Провайдер все еще недоступен после сброса")
            return
        
        # Тестовый запрос
        print("\n🚀 Тестовый запрос к OpenRouter...")
        
        request_data = {
            "messages": [
                {"role": "user", "content": "Привет! Ответь кратко на русском языке."}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        async def test_request():
            try:
                response = await provider.make_request(request_data)
                return response
            except Exception as e:
                print(f"❌ Ошибка в запросе: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        result = asyncio.run(test_request())
        
        if result:
            print("✅ Запрос выполнен успешно!")
            print(f"📝 Ответ: {result.get('content', 'Нет содержимого')}")
            print(f"📊 Токены: {result.get('usage', {})}")
            print("🎉 OpenRouter работает после сброса Circuit Breaker!")
            
            # Финальная статистика
            final_stats = provider.get_stats()
            print(f"\n📊 Финальная статистика:")
            print(f"   📈 Успешность: {final_stats.get('success_rate', 0):.1%}")
            print(f"   🔄 Circuit Break: {final_stats.get('in_circuit_break', False)}")
            
        else:
            print("❌ Запрос не выполнен")
            
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Попробуйте запустить из корневой директории проекта")
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reset_and_test_openrouter()