#!/usr/bin/env python3
"""
🧪 Тест исправленного OpenRouter провайдера
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def test_openrouter_fixed():
    """Тестирование исправленного OpenRouter провайдера"""
    print("🧪 ТЕСТ ИСПРАВЛЕННОГО OpenRouter ПРОВАЙДЕРА")
    print("=" * 50)
    
    try:
        # Импорт с обработкой ошибок
        try:
            from providers.openrouter import OpenRouterProvider
            from providers.base_provider import ProviderConfig
            print("✅ Импорты успешны")
        except ImportError as e:
            print(f"❌ Ошибка импорта: {e}")
            return
        
        # Проверка API ключа
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print("❌ OPENROUTER_API_KEY не найден в .env")
            return
        
        print(f"✅ API ключ найден: {api_key[:15]}...{api_key[-8:]}")
        
        # Создание конфигурации
        config = ProviderConfig(
            name="OpenRouter",
            api_key=api_key,
            model="deepseek/deepseek-chat-v3.1:free",
            base_url="https://openrouter.ai/api/v1",
            priority=2,
            active=True,
            timeout=30
        )
        print("✅ Конфигурация создана")
        
        # Создание провайдера
        provider = OpenRouterProvider(config)
        print("✅ Провайдер создан")
        
        # Проверка доступности
        is_available = provider.is_available()
        print(f"✅ Доступность провайдера: {is_available}")
        
        if not is_available:
            print("❌ Провайдер недоступен")
            stats = provider.get_stats()
            print(f"   Circuit Break: {stats.get('in_circuit_break', False)}")
            print(f"   Failure Count: {stats.get('failure_count', 0)}")
            return
        
        # Тестовые данные в формате как в пайплайне
        request_data = {
            "messages": [
                {"role": "user", "content": "Привет! Ответь кратко на русском языке."}
            ],
            "temperature": 0.2,
            "max_tokens": 100
        }
        
        print("🚀 Отправка тестового запроса...")
        print(f"   Данные: {request_data}")
        
        # Выполнение запроса
        result = await provider.make_request(request_data)
        
        print("✅ Запрос выполнен успешно!")
        print(f"📝 Ответ: {result.get('content', 'Нет содержимого')}")
        print(f"🤖 Провайдер: {result.get('provider', 'Неизвестно')}")
        print(f"📊 Токены: {result.get('usage', {})}")
        print(f"⏱️ Время ответа: {result.get('response_time', 0):.2f}с")
        
        # Проверка статистики
        stats = provider.get_stats()
        print(f"\n📊 Статистика провайдера:")
        print(f"   Успешность: {stats.get('success_rate', 0):.1%}")
        print(f"   Всего запросов: {stats.get('requests_total', 0)}")
        print(f"   Circuit Break: {stats.get('in_circuit_break', False)}")
        
        print("\n🎉 Тест завершен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_openrouter_fixed())