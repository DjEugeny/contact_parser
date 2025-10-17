#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест OpenRouter с моделью qwen/qwen3-235b-a22b:free
"""

import os
import requests
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

def test_openrouter_qwen():
    """Тест OpenRouter с рабочей моделью"""
    print("🧪 ТЕСТ OPENROUTER С МОДЕЛЬЮ QWEN")
    print("=" * 40)
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    model = os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-235b-a22b:free')
    
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден")
        return False
    
    print(f"🔑 API Key: {api_key[:15]}...{api_key[-8:]}")
    print(f"🤖 Модель: {model}")
    
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://localhost:3000',
            'X-Title': 'OpenRouter Test'
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Привет! Ответь одним словом: работает?"}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        print("📡 Отправка запроса...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"📊 Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"✅ УСПЕХ! Ответ: {content}")
            return True
        elif response.status_code == 404:
            print(f"❌ Ошибка 404: {response.text}")
            if "data policy" in response.text.lower():
                print("💡 Проблема с настройками приватности!")
                print("🔗 Решение: https://openrouter.ai/settings/privacy")
            return False
        elif response.status_code == 429:
            print(f"🚫 Лимит исчерпан: {response.text}")
            return False
        else:
            print(f"⚠️ Неожиданный статус: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = test_openrouter_qwen()
    
    if success:
        print("\n🎉 OpenRouter настроен правильно!")
        print("✅ Можно запускать API Pipeline Validator")
    else:
        print("\n❌ OpenRouter не работает")
        print("💡 Проверьте настройки или используйте Replicate")
