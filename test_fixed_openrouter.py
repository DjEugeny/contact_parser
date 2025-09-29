#!/usr/bin/env python3
"""
🧪 Тест исправленного OpenRouter провайдера
"""

import asyncio
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def test_fixed_openrouter():
    """Тестирование исправленного OpenRouter провайдера"""
    print("🧪 ТЕСТ ИСПРАВЛЕННОГО OpenRouter ПРОВАЙДЕРА")
    print("=" * 50)
    
    # Прямой тест API
    import aiohttp
    
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
    
    # Данные запроса в формате как в пайплайне
    request_data = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [
            {"role": "user", "content": "Привет! Ответь кратко на русском языке."}
        ],
        "temperature": 0.2,
        "max_tokens": 100,
        "top_p": 0.95,
        "stream": False
    }
    
    # Формируем URL как в провайдере
    base_url = "https://openrouter.ai/api/v1"
    url = base_url
    if not url.endswith('/chat/completions'):
        if url.endswith('/'):
            url = url + 'chat/completions'
        else:
            url = url + '/chat/completions'
    
    print(f"🌐 URL: {url}")
    print(f"🤖 Модель: {request_data['model']}")
    print(f"📝 Сообщения: {len(request_data['messages'])}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=request_data,
                headers=headers,
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
                        
                    print("🎉 OpenRouter работает с исправленным форматом!")
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Ошибка {response.status}: {error_text}")
                    
                    # Анализируем ошибку
                    if response.status == 400:
                        print("📝 Проблема с форматом запроса - нужно проверить payload")
                        print(f"🔍 Отправленные данные: {request_data}")
                        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_openrouter())