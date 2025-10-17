#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест всех бесплатных моделей OpenRouter
Найдем рабочую модель прямо сейчас
"""

import os
import requests
from dotenv import load_dotenv
import time

load_dotenv()

def test_model(api_key: str, model: str) -> dict:
    """Тест одной модели"""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://localhost:3000',
            'X-Title': 'Model Test'
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Hi"}
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        return {
            'model': model,
            'status': response.status_code,
            'success': response.status_code == 200,
            'error': response.text if response.status_code != 200 else None
        }
        
    except Exception as e:
        return {
            'model': model,
            'status': 0,
            'success': False,
            'error': str(e)
        }

def main():
    print("🧪 ТЕСТ ВСЕХ БЕСПЛАТНЫХ МОДЕЛЕЙ OPENROUTER")
    print("=" * 60)
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден")
        return
    
    # Список бесплатных моделей для тестирования
    models = [
        "qwen/qwen3-235b-a22b:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "microsoft/phi-3-mini-128k-instruct:free",
        "google/gemini-flash-1.5:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "liquid/lfm-40b:free",
    ]
    
    print(f"📋 Тестируем {len(models)} моделей...\n")
    
    working_models = []
    rate_limited_models = []
    policy_blocked_models = []
    other_errors = []
    
    for i, model in enumerate(models, 1):
        print(f"🧪 {i}/{len(models)} Тестируем: {model}")
        
        result = test_model(api_key, model)
        
        if result['success']:
            print(f"   ✅ РАБОТАЕТ!")
            working_models.append(model)
        elif result['status'] == 429:
            print(f"   🚫 Rate limit (временно перегружена)")
            rate_limited_models.append(model)
        elif result['status'] == 404 and 'data policy' in result['error'].lower():
            print(f"   🔒 Требует настройки приватности")
            policy_blocked_models.append(model)
        else:
            print(f"   ❌ Ошибка: {result['status']}")
            if result['error']:
                error_short = result['error'][:100]
                print(f"      {error_short}")
            other_errors.append((model, result['error']))
        
        # Небольшая пауза между запросами
        if i < len(models):
            time.sleep(1)
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    if working_models:
        print(f"\n✅ РАБОТАЮЩИЕ МОДЕЛИ ({len(working_models)}):")
        for model in working_models:
            print(f"   ✅ {model}")
    else:
        print(f"\n❌ НЕТ РАБОТАЮЩИХ МОДЕЛЕЙ")
    
    if rate_limited_models:
        print(f"\n🚫 ВРЕМЕННО ПЕРЕГРУЖЕНЫ ({len(rate_limited_models)}):")
        for model in rate_limited_models:
            print(f"   🚫 {model}")
    
    if policy_blocked_models:
        print(f"\n🔒 ТРЕБУЮТ НАСТРОЙКИ ПРИВАТНОСТИ ({len(policy_blocked_models)}):")
        for model in policy_blocked_models:
            print(f"   🔒 {model}")
    
    if other_errors:
        print(f"\n⚠️ ДРУГИЕ ОШИБКИ ({len(other_errors)}):")
        for model, error in other_errors:
            print(f"   ⚠️ {model}")
    
    # Рекомендации
    print("\n" + "=" * 60)
    print("💡 РЕКОМЕНДАЦИИ")
    print("=" * 60)
    
    if working_models:
        print(f"\n✅ Используйте рабочую модель:")
        print(f"   OPENROUTER_MODEL={working_models[0]}")
        print(f"\n📝 Обновите .env:")
        print(f"   sed -i '' 's/OPENROUTER_MODEL=.*/OPENROUTER_MODEL={working_models[0]}/' .env")
    elif rate_limited_models:
        print(f"\n⏰ Все модели временно перегружены")
        print(f"   1. Подождите 5-10 минут и попробуйте снова")
        print(f"   2. Или используйте Replicate (работает стабильно)")
        print(f"   3. Или добавьте свой API ключ провайдера на OpenRouter")
    else:
        print(f"\n❌ OpenRouter недоступен")
        print(f"   Используйте Replicate как основной провайдер")

if __name__ == "__main__":
    main()
