#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Детальная диагностика проблем с Groq API
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_groq_api():
    """Проверка состояния Groq API"""
    print("🔍 Диагностика Groq API")
    print("=" * 50)
    
    # Получаем API ключ
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("❌ GROQ_API_KEY не найден в .env файле")
        return False
    
    print(f"🔑 API ключ найден: {api_key[:10]}...{api_key[-4:]}")
    
    # Проверяем доступность API
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print("\n🔌 Проверка доступности API...")
    try:
        # Проверяем список моделей (это не тратит лимиты)
        response = requests.get(
            'https://api.groq.com/openai/v1/models',
            headers=headers,
            timeout=10
        )
        
        print(f"📡 Статус ответа: {response.status_code}")
        
        if response.status_code == 401:
            print("❌ ПРОБЛЕМА: Неверный API ключ")
            print(f"📄 Ответ: {response.text}")
            return False
            
        elif response.status_code == 429:
            print("❌ ПРОБЛЕМА: Превышен лимит запросов")
            print("   Бесплатный лимит Groq исчерпан")
            print(f"📄 Ответ: {response.text}")
            return False
            
        elif response.status_code == 200:
            data = response.json()
            models = data.get('data', [])
            print(f"✅ API доступен, найдено {len(models)} моделей")
            
            # Показываем доступные модели
            print("\n🤖 Доступные модели:")
            for model in models[:5]:  # Показываем первые 5
                print(f"   - {model.get('id', 'Unknown')}")
            
            # Проверяем текущую модель
            current_model = os.getenv('GROQ_MODEL', 'llama3-8b-8192')
            print(f"\n🎯 Текущая модель в .env: {current_model}")
            
            model_ids = [m.get('id') for m in models]
            if current_model in model_ids:
                print("✅ Модель доступна")
            else:
                print("❌ Модель недоступна")
                print(f"💡 Доступные модели: {', '.join(model_ids[:3])}...")
            
            return True
            
        else:
            print(f"⚠️ Неожиданный статус: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {str(e)}")
        return False

def test_groq_request():
    """Тестирование реального запроса к Groq"""
    print("\n🧪 Тестирование реального запроса...")
    
    api_key = os.getenv('GROQ_API_KEY')
    model = os.getenv('GROQ_MODEL', 'llama3-8b-8192')
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'user',
                'content': 'Ответь одним словом: тест'
            }
        ],
        'max_tokens': 10,
        'temperature': 0
    }
    
    try:
        print(f"📤 Отправка запроса к модели: {model}")
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"📡 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Запрос успешен")
            content = data.get('choices', [{}])[0].get('message', {}).get('content', 'Нет ответа')
            print(f"💬 Ответ: {content}")
            print(f"📊 Использование токенов: {data.get('usage', {})}")
            return True
            
        elif response.status_code == 401:
            print("❌ Ошибка авторизации (401)")
            print("   Неверный API ключ")
            
        elif response.status_code == 429:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print("❌ Превышен лимит запросов (429)")
            print("   Бесплатный лимит Groq исчерпан")
            
            # Пытаемся извлечь информацию о лимитах
            error_message = error_data.get('error', {}).get('message', '')
            if 'rate limit' in error_message.lower():
                print(f"   Детали: {error_message}")
            
            # Проверяем заголовки для информации о лимитах
            rate_limit_headers = {
                'x-ratelimit-limit-requests': 'Лимит запросов',
                'x-ratelimit-remaining-requests': 'Оставшиеся запросы',
                'x-ratelimit-reset-requests': 'Сброс лимита запросов',
                'x-ratelimit-limit-tokens': 'Лимит токенов',
                'x-ratelimit-remaining-tokens': 'Оставшиеся токены',
                'x-ratelimit-reset-tokens': 'Сброс лимита токенов'
            }
            
            print("\n📊 Информация о лимитах:")
            for header, description in rate_limit_headers.items():
                value = response.headers.get(header)
                if value:
                    print(f"   {description}: {value}")
            
        elif response.status_code == 400:
            print("❌ Ошибка запроса (400)")
            print("   Неверный формат запроса")
            
        else:
            print(f"❌ Неожиданная ошибка: {response.status_code}")
            
        print(f"📄 Полный ответ: {response.text}")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {str(e)}")
        return False

def check_groq_limits():
    """Проверка текущих лимитов Groq"""
    print("\n📊 Проверка лимитов Groq...")
    
    # Groq не предоставляет отдельный endpoint для проверки лимитов
    # Но мы можем сделать минимальный запрос и посмотреть заголовки
    
    api_key = os.getenv('GROQ_API_KEY')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Делаем минимальный запрос для получения информации о лимитах
    payload = {
        'model': 'llama3-8b-8192',
        'messages': [{'role': 'user', 'content': 'hi'}],
        'max_tokens': 1
    }
    
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        # Извлекаем информацию о лимитах из заголовков
        rate_limit_info = {
            'requests_limit': response.headers.get('x-ratelimit-limit-requests'),
            'requests_remaining': response.headers.get('x-ratelimit-remaining-requests'),
            'requests_reset': response.headers.get('x-ratelimit-reset-requests'),
            'tokens_limit': response.headers.get('x-ratelimit-limit-tokens'),
            'tokens_remaining': response.headers.get('x-ratelimit-remaining-tokens'),
            'tokens_reset': response.headers.get('x-ratelimit-reset-tokens')
        }
        
        print("📈 Информация о лимитах:")
        for key, value in rate_limit_info.items():
            if value:
                print(f"   {key}: {value}")
        
        # Анализируем состояние лимитов
        requests_remaining = rate_limit_info.get('requests_remaining')
        tokens_remaining = rate_limit_info.get('tokens_remaining')
        
        if requests_remaining == '0' or tokens_remaining == '0':
            print("\n⚠️ ВНИМАНИЕ: Лимиты исчерпаны!")
            if requests_remaining == '0':
                print("   - Лимит запросов исчерпан")
            if tokens_remaining == '0':
                print("   - Лимит токенов исчерпан")
        
        return rate_limit_info
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка проверки лимитов: {str(e)}")
        return None

if __name__ == "__main__":
    print(f"🕐 Время начала диагностики Groq: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Проверяем API
    api_valid = check_groq_api()
    
    if api_valid:
        # Проверяем лимиты
        limits_info = check_groq_limits()
        
        # Тестируем реальный запрос
        request_success = test_groq_request()
        
        print("\n" + "=" * 50)
        print("📋 ИТОГИ ДИАГНОСТИКИ GROQ")
        print("=" * 50)
        print(f"🔑 API ключ: {'✅ Действителен' if api_valid else '❌ Недействителен'}")
        print(f"🧪 Тестовый запрос: {'✅ Успешен' if request_success else '❌ Неуспешен'}")
        
        if limits_info:
            requests_remaining = limits_info.get('requests_remaining', 'Неизвестно')
            tokens_remaining = limits_info.get('tokens_remaining', 'Неизвестно')
            print(f"📊 Оставшиеся запросы: {requests_remaining}")
            print(f"🎯 Оставшиеся токены: {tokens_remaining}")
        
        if not request_success:
            print("\n🔧 РЕКОМЕНДАЦИИ:")
            print("1. Проверить, не исчерпан ли дневной лимит Groq")
            print("2. Подождать до сброса лимитов (обычно в полночь UTC)")
            print("3. Рассмотреть переход на платный план Groq")
            print("4. Использовать альтернативные провайдеры")
    
    print(f"\n🕐 Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")