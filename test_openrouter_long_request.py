#!/usr/bin/env python3
"""
🧪 Тест OpenRouter с длинным запросом (как в пайплайне)
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def test_openrouter_long_request():
    """Тест OpenRouter с длинным запросом как в пайплайне"""
    print("🧪 ТЕСТ OpenRouter С ДЛИННЫМ ЗАПРОСОМ")
    print("=" * 50)
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден")
        return False
    
    print(f"✅ API ключ: {api_key[:15]}...{api_key[-8:]}")
    
    # Заголовки как в исправленном провайдере
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://localhost:3000',
        'X-Title': 'Contact Parser LLM Request'
    }
    
    # Создаем длинный запрос похожий на тот что в пайплайне
    long_content = """🎯 ЗАДАЧА:
- Проанализируй текст письма и всех вложений ниже (объединённый текст).
- 🚨 КРИТИЧЕСКИ ВАЖНО: Отвечай ТОЛЬКО валидным JSON без каких-либо дополнительных тегов, комментариев или объяснений!
- Не придумывай данные. Заполняй только то, что следует из текста.

📋 ПРАВИЛА ИЗВЛЕЧЕНИЯ:

## 🏢 ОРГАНИЗАЦИИ (organizations)
1. Собирай все найденные корпоративные email, телефоны, ИНН, сайты, город и адрес.
2. Включай контактные данные, не привязанные к конкретному человеку.
3. Если email/телефон указан без ФИО — относись к organizations.

""" + "Дополнительный текст для увеличения размера запроса. " * 100 + """

=== ТЕКСТ ПИСЬМА ===
Добрый день!
Юлия Александровна Пименова
medic.81@mail.ru

=== ВЛОЖЕНИЕ ===
АНКЕТА УЧАСТНИКА
МСЧ Клиницист-Клиника Претор, г. Новосибирск
Контактное лицо: Пименова Юлия Александровна
Телефон: +7(495) 640-17-71

Верни JSON с организациями и контактами."""
    
    # Данные запроса
    request_data = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [
            {"role": "user", "content": long_content}
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
        "top_p": 0.95,
        "stream": False
    }
    
    # URL
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    print(f"🌐 URL: {url}")
    print(f"🤖 Модель: {request_data['model']}")
    print(f"📝 Длина контента: {len(long_content)} символов")
    print(f"⏰ Таймаут: 120 секунд")
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=request_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)  # 2 минуты как в провайдере
            ) as response:
                
                end_time = asyncio.get_event_loop().time()
                response_time = end_time - start_time
                
                print(f"📊 Статус ответа: {response.status}")
                print(f"⏱️ Время ответа: {response_time:.2f} секунд")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ Запрос успешен!")
                    
                    if 'choices' in result and len(result['choices']) > 0:
                        content = result['choices'][0]['message']['content']
                        print(f"📝 Ответ (первые 200 символов): {content[:200]}...")
                    
                    if 'usage' in result:
                        print(f"📊 Использование токенов: {result['usage']}")
                        
                    print("🎉 OpenRouter справился с длинным запросом!")
                    return True
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Ошибка {response.status}: {error_text}")
                    return False
                        
    except asyncio.TimeoutError:
        print("⏰ Таймаут запроса (120 секунд)")
        print("💡 OpenRouter не успел обработать длинный запрос")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print(f"🔍 Тип ошибки: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openrouter_long_request())
    if success:
        print("\n🎉 Тест с длинным запросом прошел успешно!")
        print("✅ OpenRouter может обрабатывать запросы из пайплайна")
    else:
        print("\n💥 Тест с длинным запросом провалился!")
        print("❌ Нужно дальше исследовать проблему с таймаутами")
    
    import sys
    sys.exit(0 if success else 1)