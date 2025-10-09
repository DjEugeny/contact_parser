#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки ошибки OpenRouter
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_openrouter():
    """Тестовый запрос к OpenRouter для проверки ошибки"""
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден в .env")
        return
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://localhost:3000',
        'X-Title': 'Contact Parser Test'
    }
    
    # Тест 1: Простой запрос
    payload_simple = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [
            {
                "role": "user",
                "content": "Привет! Это тестовое сообщение."
            }
        ],
        "temperature": 0.2,
        "max_tokens": 100
    }
    
    # Тест 2: Большой запрос (как в реальном pipeline)
    payload_large = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [
            {
                "role": "system",
                "content": "Ты - ассистент для извлечения контактной информации из писем."
            },
            {
                "role": "user",
                "content": "Извлеки контакты из этого письма:\n\n" + ("Тестовый текст. " * 1000)
            }
        ],
        "temperature": 0.2,
        "max_tokens": 4000
    }
    
    # Выбираем какой тест запустить
    payload = payload_simple  # Можно поменять на payload_large
    
    print("🔍 Отправка тестового запроса к OpenRouter...")
    print(f"📝 Модель: {payload['model']}")
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                print(f"\n📊 HTTP Status: {response.status}")
                print(f"📋 Headers: {dict(response.headers)}")
                
                try:
                    result = await response.json()
                    print(f"\n✅ JSON Response:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    
                    # Проверяем структуру ответа
                    if 'error' in result:
                        print(f"\n❌ ОШИБКА ОТ OPENROUTER:")
                        print(f"   Сообщение: {result.get('error', {}).get('message', 'N/A')}")
                        print(f"   Код: {result.get('error', {}).get('code', 'N/A')}")
                        print(f"   Метаданные: {result.get('error', {}).get('metadata', {})}")
                    
                    if 'choices' in result:
                        print(f"\n✅ Ответ получен успешно:")
                        print(f"   Content: {result['choices'][0]['message']['content']}")
                    
                except json.JSONDecodeError as e:
                    text = await response.text()
                    print(f"\n❌ Ошибка парсинга JSON: {e}")
                    print(f"📄 Raw response: {text}")
                    
    except Exception as e:
        print(f"\n❌ Ошибка: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_openrouter())
