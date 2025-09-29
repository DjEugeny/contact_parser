#!/usr/bin/env python3
"""
🐛 Отладка ошибки OpenRouter провайдера
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def debug_openrouter():
    """Отладка OpenRouter провайдера"""
    print("🐛 ОТЛАДКА OpenRouter ПРОВАЙДЕРА")
    print("=" * 40)
    
    try:
        # Импортируем провайдер
        from providers.openrouter import OpenRouterProvider
        from providers.base_provider import ProviderConfig
        
        # Создаем конфигурацию
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print("❌ OPENROUTER_API_KEY не найден")
            return
        
        config = ProviderConfig(
            name="OpenRouter",
            api_key=api_key,
            model="deepseek/deepseek-chat-v3.1:free",
            base_url="https://openrouter.ai/api/v1",
            priority=2,
            active=True,
            timeout=30
        )
        
        print(f"✅ Конфигурация создана")
        print(f"   🔑 API ключ: {api_key[:15]}...{api_key[-8:]}")
        print(f"   🤖 Модель: {config.model}")
        print(f"   🌐 URL: {config.base_url}")
        
        # Создаем провайдер
        provider = OpenRouterProvider(config)
        print(f"✅ Провайдер создан")
        
        # Проверяем доступность
        is_available = provider.is_available()
        print(f"✅ Доступность: {is_available}")
        
        if not is_available:
            print("❌ Провайдер недоступен, завершаем тест")
            return
        
        # Тестовые данные запроса
        request_data = {
            "messages": [
                {"role": "user", "content": "Привет! Ответь кратко."}
            ],
            "temperature": 0.2,
            "max_tokens": 50
        }
        
        print(f"🚀 Отправка тестового запроса...")
        print(f"   📝 Данные: {request_data}")
        
        # Выполняем запрос
        try:
            result = await provider.make_request(request_data)
            print("✅ Запрос выполнен успешно!")
            print(f"📝 Результат: {result}")
            
        except Exception as e:
            print(f"❌ Ошибка в make_request: {e}")
            print(f"🔍 Тип ошибки: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_openrouter())