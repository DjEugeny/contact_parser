#!/usr/bin/env python3
"""
🔥 ПРОСТОЙ ТЕСТ OpenRouter
Цель: Проверить работу OpenRouter провайдера напрямую
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def test_openrouter_direct():
    """Прямой тест OpenRouter API"""
    print("🔥 ПРЯМОЙ ТЕСТ OpenRouter API")
    print("=" * 40)
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден")
        return
    
    print(f"✅ API ключ: {api_key[:15]}...{api_key[-8:]}")
    
    # Заголовки как в исправленном провайдере
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://localhost:3000',
        'X-Title': 'Contact Parser LLM Request'
    }
    
    # Данные запроса
    data = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [
            {"role": "user", "content": "Привет! Ответь кратко на русском языке."}
        ],
        "max_tokens": 50,
        "temperature": 0.1
    }
    
    print("🚀 Отправка запроса к OpenRouter...")
    print(f"🌐 URL: https://openrouter.ai/api/v1/chat/completions")
    print(f"🤖 Модель: {data['model']}")
    print(f"📝 Сообщение: {data['messages'][0]['content']}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                print(f"📊 Статус ответа: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ Запрос успешен!")
                    
                    if 'choices' in result and len(result['choices']) > 0:
                        content = result['choices'][0]['message']['content']
                        print(f"📝 Ответ: {content}")
                    
                    if 'usage' in result:
                        print(f"📊 Использование токенов: {result['usage']}")
                        
                    print("🎉 OpenRouter работает корректно!")
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Ошибка {response.status}: {error_text}")
                    
                    # Анализируем ошибку
                    if response.status == 401:
                        print("🔑 Проблема с авторизацией - проверьте API ключ")
                    elif response.status == 400:
                        print("📝 Проблема с форматом запроса")
                    elif response.status == 429:
                        print("⏰ Превышен лимит запросов")
                    elif response.status >= 500:
                        print("🔧 Проблема на стороне сервера OpenRouter")
                        
    except asyncio.TimeoutError:
        print("⏰ Таймаут запроса")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_openrouter_direct())