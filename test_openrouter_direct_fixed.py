#!/usr/bin/env python3
"""
🧪 Прямой тест исправленного OpenRouter API
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def test_openrouter_direct():
    """Прямой тест OpenRouter API с исправленным форматом"""
    print("🧪 ПРЯМОЙ ТЕСТ OpenRouter API (ИСПРАВЛЕННЫЙ)")
    print("=" * 50)
    
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
    
    # Данные запроса в точном формате как в провайдере
    payload = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [
            {"role": "user", "content": "Привет! Ответь кратко на русском языке."}
        ],
        "temperature": 0.2,
        "max_tokens": 100,
        "top_p": 0.95,
        "stream": False
    }
    
    # URL как в провайдере
    base_url = "https://openrouter.ai/api/v1"
    url = base_url
    if not url.endswith('/chat/completions'):
        if url.endswith('/'):
            url = url + 'chat/completions'
        else:
            url = url + '/chat/completions'
    
    print(f"🌐 URL: {url}")
    print(f"🤖 Модель: {payload['model']}")
    print(f"📝 Сообщения: {len(payload['messages'])}")
    print(f"📋 Заголовки: {list(headers.keys())}")
    
    try:
        print("🚀 Отправка запроса...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
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
                        usage = result['usage']
                        print(f"📊 Токены: {usage}")
                        
                    print("🎉 OpenRouter работает с исправленным форматом!")
                    return True
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Ошибка {response.status}: {error_text}")
                    
                    # Анализ ошибки
                    if response.status == 400:
                        print("📝 Проблема с форматом запроса")
                        print(f"🔍 Отправленные данные: {payload}")
                    elif response.status == 401:
                        print("🔑 Проблема с авторизацией")
                    elif response.status == 429:
                        print("⏰ Превышен лимит запросов")
                    
                    return False
                        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_with_long_request():
    """Тест с длинным запросом как в пайплайне"""
    print("\n🧪 ТЕСТ С ДЛИННЫМ ЗАПРОСОМ (КАК В ПАЙПЛАЙНЕ)")
    print("=" * 50)
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден")
        return
    
    # Заголовки
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://localhost:3000',
        'X-Title': 'Contact Parser LLM Request'
    }
    
    # Длинный запрос как в пайплайне
    long_content = """
    Извлеки контактную информацию из следующего текста:
    
    Компания: ООО "Тестовая Компания"
    Адрес: г. Москва, ул. Тестовая, д. 123
    Телефон: +7 (495) 123-45-67
    Email: test@example.com
    Сайт: https://example.com
    
    Контактное лицо: Иванов Иван Иванович
    Должность: Менеджер по продажам
    Мобильный: +7 (999) 888-77-66
    
    Ответь в JSON формате со всей найденной информацией.
    """
    
    payload = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [
            {"role": "user", "content": long_content.strip()}
        ],
        "temperature": 0.2,
        "max_tokens": 1000,
        "top_p": 0.95,
        "stream": False
    }
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    try:
        print("🚀 Отправка длинного запроса...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)  # Увеличенный таймаут
            ) as response:
                
                print(f"📊 Статус ответа: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ Длинный запрос успешен!")
                    
                    if 'choices' in result and len(result['choices']) > 0:
                        content = result['choices'][0]['message']['content']
                        print(f"📝 Ответ (первые 200 символов): {content[:200]}...")
                    
                    if 'usage' in result:
                        usage = result['usage']
                        print(f"📊 Токены: {usage}")
                        
                    print("🎉 Длинный запрос работает!")
                    return True
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Ошибка {response.status}: {error_text}")
                    return False
                        
    except Exception as e:
        print(f"❌ Ошибка в длинном запросе: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🔧 ТЕСТИРОВАНИЕ ИСПРАВЛЕННОГО OpenRouter ПРОВАЙДЕРА")
    print("=" * 60)
    
    # Тест 1: Простой запрос
    success1 = await test_openrouter_direct()
    
    # Тест 2: Длинный запрос
    success2 = await test_with_long_request()
    
    print(f"\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"   Простой запрос: {'✅ Успех' if success1 else '❌ Ошибка'}")
    print(f"   Длинный запрос: {'✅ Успех' if success2 else '❌ Ошибка'}")
    
    if success1 and success2:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("   OpenRouter провайдер готов к использованию в пайплайне")
    else:
        print("\n⚠️ ЕСТЬ ПРОБЛЕМЫ С ТЕСТАМИ")
        print("   Нужно дополнительно исследовать ошибки")

if __name__ == "__main__":
    asyncio.run(main())