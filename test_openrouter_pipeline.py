#!/usr/bin/env python3
"""
🔥 ИЗОЛИРОВАННЫЙ ТЕСТ OpenRouter В ПАЙПЛАЙНЕ
Цель: Проверить работу OpenRouter провайдера в реальном пайплайне
"""

import sys
import os
import asyncio
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from core.llm_manager import LLMManager
from core.error_handling.circuit_breaker import CircuitBreaker

# Загружаем переменные окружения
load_dotenv()

def test_openrouter_in_pipeline():
    """Тестирование OpenRouter в реальном пайплайне"""
    print("🔥 ИЗОЛИРОВАННЫЙ ТЕСТ OpenRouter В ПАЙПЛАЙНЕ")
    print("=" * 60)
    
    # Проверяем API ключ
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден в .env")
        return
    
    print(f"✅ API ключ найден: {api_key[:15]}...{api_key[-8:]}")
    
    # Создаем LLM Manager
    try:
        llm_manager = LLMManager()
        print(f"✅ LLM Manager создан с {len(llm_manager.providers)} провайдерами")
        
        # Показываем провайдеры
        for i, provider in enumerate(llm_manager.providers, 1):
            status = "✅ Доступен" if provider.is_available() else "❌ Недоступен"
            print(f"   {i}. {provider.config.name} - {status}")
            
            # Если это OpenRouter, показываем детали Circuit Breaker
            if "OpenRouter" in provider.config.name:
                print(f"      🔧 Модель: {provider.config.model}")
                print(f"      🌐 URL: {provider.config.base_url}")
                
                # Проверяем Circuit Breaker
                if hasattr(provider, '_circuit_breaker'):
                    cb = provider._circuit_breaker
                    print(f"      🔄 Circuit Breaker: {cb.state}")
                    print(f"      📊 Ошибки: {cb.failure_count}/{cb.failure_threshold}")
                    print(f"      ⏰ Последняя ошибка: {cb.last_failure_time}")
        
        # Тестовый запрос через LLM Manager
        print("\n🚀 Отправка тестового запроса через LLM Manager...")
        
        test_prompt = """Извлеки контактную информацию из этого текста:
        
Компания: ООО "Тест"
Телефон: +7 (495) 123-45-67
Email: test@example.com

Ответь в JSON формате."""

        async def test_llm_request():
            try:
                response = await llm_manager.make_request(test_prompt, max_tokens=200)
                return response
            except Exception as e:
                print(f"❌ Ошибка в LLM запросе: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # Выполняем запрос
        result = asyncio.run(test_llm_request())
        
        if result:
            print("✅ Запрос выполнен успешно!")
            print(f"📝 Ответ: {result.get('content', 'Нет содержимого')[:200]}...")
            print(f"🤖 Провайдер: {result.get('provider', 'Неизвестно')}")
            print(f"📊 Токены: {result.get('usage', {})}")
            
            # Проверяем какой провайдер ответил
            if result.get('provider') == 'OpenRouter':
                print("🎉 OpenRouter работает в пайплайне!")
            else:
                print(f"⚠️ Ответил {result.get('provider')}, а не OpenRouter")
        else:
            print("❌ Запрос не выполнен")
            
        # Показываем финальное состояние провайдеров
        print("\n📊 ФИНАЛЬНОЕ СОСТОЯНИЕ ПРОВАЙДЕРОВ:")
        for provider in llm_manager.providers:
            status = "✅ Доступен" if provider.is_available() else "❌ Недоступен"
            print(f"   {provider.config.name}: {status}")
            
    except Exception as e:
        print(f"❌ Ошибка создания LLM Manager: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_openrouter_in_pipeline()