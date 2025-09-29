#!/usr/bin/env python3
"""
🔄 Утилита для сброса Circuit Breaker провайдеров
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


def reset_circuit_breakers():
    """Простой сброс Circuit Breaker через тестирование провайдеров"""
    print("🔄 Тестирование провайдеров для сброса Circuit Breaker...")

    # Тестируем OpenRouter напрямую
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден")
        return

    import requests

    try:
        print("🧪 Тестирование OpenRouter...")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost:3000",
            "X-Title": "Circuit Breaker Reset Test",
        }

        payload = {
            "model": "deepseek/deepseek-chat-v3.1:free",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 10,
            "temperature": 0.1,
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10,
        )

        print(f"📡 Статус ответа: {response.status_code}")

        if response.status_code == 200:
            print("✅ OpenRouter работает корректно!")
            result = response.json()
            content = (
                result.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            print(f"📝 Ответ: {content}")
        elif response.status_code == 429:
            print("🚫 OpenRouter: превышен лимит запросов")
            print("💡 Это нормально для бесплатного уровня")
        else:
            print(f"⚠️ OpenRouter: {response.text}")

    except Exception as e:
        print(f"❌ Ошибка тестирования OpenRouter: {e}")

    print("\n💡 Для сброса Circuit Breaker в системе:")
    print("   1. Подождите 5 минут после последней ошибки")
    print("   2. Или перезапустите приложение")
    print("   3. Circuit Breaker автоматически перейдет в режим тестирования")


if __name__ == "__main__":
    reset_circuit_breakers()
