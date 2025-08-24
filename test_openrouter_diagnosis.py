#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Детальная диагностика проблем с OpenRouter API
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_openrouter_api():
    """Проверка состояния OpenRouter API"""
    print("🔍 Диагностика OpenRouter API")
    print("=" * 50)
    
    # Получаем API ключ
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY не найден в .env файле")
        return False
    
    print(f"🔑 API ключ найден: {api_key[:10]}...{api_key[-4:]}")
    
    # Проверяем баланс и лимиты
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print("\n💰 Проверка баланса и лимитов...")
    try:
        # Проверяем информацию об аккаунте
        response = requests.get(
            'https://openrouter.ai/api/v1/auth/key',
            headers=headers,
            timeout=10
        )
        
        print(f"📡 Статус ответа: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
        
        if response.status_code == 401:
            print("❌ ПРОБЛЕМА: Неверный API ключ или аккаунт не найден")
            print("   Возможные причины:")
            print("   - API ключ недействителен")
            print("   - Аккаунт заблокирован")
            print("   - Превышен бесплатный лимит")
            return False
            
        elif response.status_code == 200:
            data = response.json()
            print("✅ API ключ действителен")
            print(f"📊 Данные аккаунта: {json.dumps(data, indent=2)}")
            return True
            
        else:
            print(f"⚠️ Неожиданный статус: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {str(e)}")
        return False

def test_openrouter_models():
    """Тестирование доступных моделей OpenRouter"""
    print("\n🤖 Проверка доступных моделей...")
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            'https://openrouter.ai/api/v1/models',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Получено {len(models.get('data', []))} моделей")
            
            # Ищем бесплатные модели
            free_models = []
            for model in models.get('data', []):
                if model.get('pricing', {}).get('prompt', '0') == '0':
                    free_models.append(model['id'])
            
            print(f"🆓 Найдено {len(free_models)} бесплатных моделей:")
            for model in free_models[:5]:  # Показываем первые 5
                print(f"   - {model}")
            
            # Проверяем текущую модель из .env
            current_model = os.getenv('OPENROUTER_MODEL', 'z-ai/glm-4.5-air:free')
            print(f"\n🎯 Текущая модель в .env: {current_model}")
            
            if current_model in [m['id'] for m in models.get('data', [])]:
                print("✅ Модель доступна")
            else:
                print("❌ Модель недоступна или не найдена")
                
        else:
            print(f"❌ Ошибка получения моделей: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {str(e)}")

def test_openrouter_request():
    """Тестирование реального запроса к OpenRouter"""
    print("\n🧪 Тестирование реального запроса...")
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    model = os.getenv('OPENROUTER_MODEL', 'z-ai/glm-4.5-air:free')
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://contact-parser.local',
        'X-Title': 'Contact Parser'
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
            'https://openrouter.ai/api/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"📡 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Запрос успешен")
            print(f"💬 Ответ: {data.get('choices', [{}])[0].get('message', {}).get('content', 'Нет ответа')}")
            print(f"📊 Использование токенов: {data.get('usage', {})}")
            return True
            
        elif response.status_code == 401:
            print("❌ Ошибка авторизации (401)")
            print("   Возможные причины:")
            print("   - Неверный API ключ")
            print("   - Исчерпан бесплатный лимит")
            print("   - Аккаунт заблокирован")
            
        elif response.status_code == 429:
            print("❌ Превышен лимит запросов (429)")
            print("   Бесплатный лимит исчерпан")
            
        elif response.status_code == 402:
            print("❌ Требуется оплата (402)")
            print("   Недостаточно средств на балансе")
            
        else:
            print(f"❌ Неожиданная ошибка: {response.status_code}")
            
        print(f"📄 Полный ответ: {response.text}")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {str(e)}")
        return False

def check_openrouter_limits():
    """Проверка лимитов и использования"""
    print("\n📊 Проверка лимитов использования...")
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Проверяем статистику использования
        response = requests.get(
            'https://openrouter.ai/api/v1/generation',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Статистика получена")
            print(f"📈 Данные использования: {json.dumps(data, indent=2)}")
        else:
            print(f"⚠️ Не удалось получить статистику: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка получения статистики: {str(e)}")

if __name__ == "__main__":
    print(f"🕐 Время начала диагностики OpenRouter: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Проверяем API ключ и аккаунт
    api_valid = check_openrouter_api()
    
    if api_valid:
        # Проверяем модели
        test_openrouter_models()
        
        # Проверяем лимиты
        check_openrouter_limits()
        
        # Тестируем реальный запрос
        request_success = test_openrouter_request()
        
        print("\n" + "=" * 50)
        print("📋 ИТОГИ ДИАГНОСТИКИ OPENROUTER")
        print("=" * 50)
        print(f"🔑 API ключ: {'✅ Действителен' if api_valid else '❌ Недействителен'}")
        print(f"🧪 Тестовый запрос: {'✅ Успешен' if request_success else '❌ Неуспешен'}")
        
        if not request_success:
            print("\n🔧 РЕКОМЕНДАЦИИ:")
            print("1. Проверить баланс аккаунта OpenRouter")
            print("2. Убедиться, что не исчерпан бесплатный лимит")
            print("3. Попробовать другую бесплатную модель")
            print("4. Рассмотреть пополнение баланса")
    
    print(f"\n🕐 Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")