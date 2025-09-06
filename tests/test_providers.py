#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест доступности LLM провайдеров для Фазы 0
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def test_openrouter():
    """Тест OpenRouter API"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        return "❌ OPENROUTER_API_KEY не найден"

    try:
        url = "https://openrouter.ai/api/v1/auth/key"
        headers = {"Authorization": f"Bearer {api_key}"}

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return f"✅ OpenRouter: {data.get('data', {}).get('label', 'OK')}"
        else:
            return f"❌ OpenRouter: HTTP {response.status_code}"

    except Exception as e:
        return f"❌ OpenRouter: {str(e)}"

def test_groq():
    """Тест Groq API"""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return "❌ GROQ_API_KEY не найден"

    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return f"✅ Groq: {len(data.get('data', []))} моделей доступно"
        else:
            return f"❌ Groq: HTTP {response.status_code}"

    except Exception as e:
        return f"❌ Groq: {str(e)}"

def test_replicate():
    """Тест Replicate API"""
    api_key = os.getenv('REPLICATE_API_KEY')
    if not api_key:
        return "❌ REPLICATE_API_KEY не найден"

    try:
        url = "https://api.replicate.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            return "✅ Replicate: API доступен"
        else:
            return f"❌ Replicate: HTTP {response.status_code}"

    except Exception as e:
        return f"❌ Replicate: {str(e)}"

def main():
    print("🧪 Тестирование доступности LLM провайдеров\n")

    providers = [
        ("OpenRouter", test_openrouter),
        ("Groq", test_groq),
        ("Replicate", test_replicate)
    ]

    results = []
    for name, test_func in providers:
        print(f"🔍 Тестирую {name}...")
        result = test_func()
        print(f"   {result}")
        results.append((name, result))
        time.sleep(1)  # Небольшая пауза между запросами

    print("\n📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    success_count = sum(1 for _, result in results if result.startswith("✅"))
    print(f"✅ Успешно: {success_count}/3 провайдеров")

    if success_count == 3:
        print("🎉 Все провайдеры доступны! Можно переходить к следующему шагу.")
    else:
        print("⚠️ Некоторые провайдеры недоступны. Проверь API ключи.")

if __name__ == "__main__":
    main()
