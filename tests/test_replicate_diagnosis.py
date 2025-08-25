#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Детальная диагностика проблем с Replicate API
"""

import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_replicate_api():
    """Проверка состояния Replicate API"""
    print("🔍 Диагностика Replicate API")
    print("=" * 50)
    
    # Получаем API токен
    api_token = os.getenv('REPLICATE_API_KEY')
    if not api_token:
        print("❌ REPLICATE_API_KEY не найден в .env файле")
        return False
    
    print(f"🔑 API токен найден: {api_token[:10]}...{api_token[-4:]}")
    
    # Проверяем аккаунт и баланс
    headers = {
        'Authorization': f'Token {api_token}',
        'Content-Type': 'application/json'
    }
    
    print("\n💰 Проверка аккаунта и баланса...")
    try:
        # Проверяем информацию об аккаунте
        response = requests.get(
            'https://api.replicate.com/v1/account',
            headers=headers,
            timeout=10
        )
        
        print(f"📡 Статус ответа: {response.status_code}")
        
        if response.status_code == 401:
            print("❌ ПРОБЛЕМА: Неверный API токен")
            print(f"📄 Ответ: {response.text}")
            return False
            
        elif response.status_code == 200:
            data = response.json()
            print("✅ API токен действителен")
            print(f"👤 Пользователь: {data.get('username', 'Неизвестно')}")
            print(f"📧 Email: {data.get('email', 'Неизвестно')}")
            print(f"🎯 Тип аккаунта: {data.get('type', 'Неизвестно')}")
            
            # Проверяем баланс
            if 'billing' in data:
                billing = data['billing']
                print(f"💳 Баланс: ${billing.get('balance', 'Неизвестно')}")
                print(f"📊 Использовано в этом месяце: ${billing.get('current_month_usage', 'Неизвестно')}")
            
            return True
            
        else:
            print(f"⚠️ Неожиданный статус: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {str(e)}")
        return False

def check_replicate_model():
    """Проверка доступности модели"""
    print("\n🤖 Проверка модели...")
    
    api_token = os.getenv('REPLICATE_API_KEY')
    model = os.getenv('REPLICATE_MODEL', 'meta/llama-2-13b')
    
    headers = {
        'Authorization': f'Token {api_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"🎯 Проверяемая модель: {model}")
    
    try:
        # Получаем информацию о модели
        response = requests.get(
            f'https://api.replicate.com/v1/models/{model}',
            headers=headers,
            timeout=10
        )
        
        print(f"📡 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Модель доступна")
            print(f"📝 Описание: {data.get('description', 'Нет описания')[:100]}...")
            print(f"🏷️ Последняя версия: {data.get('latest_version', {}).get('id', 'Неизвестно')[:12]}...")
            
            # Проверяем статус модели
            if data.get('visibility') == 'public':
                print("🌐 Модель публичная")
            else:
                print(f"🔒 Видимость модели: {data.get('visibility', 'Неизвестно')}")
            
            return True
            
        elif response.status_code == 404:
            print("❌ Модель не найдена")
            print("   Возможные причины:")
            print("   - Неверное имя модели")
            print("   - Модель была удалена")
            print("   - Нет доступа к приватной модели")
            
        else:
            print(f"❌ Ошибка получения модели: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {str(e)}")
        return False

def test_replicate_prediction():
    """Тестирование создания предсказания"""
    print("\n🧪 Тестирование создания предсказания...")
    
    api_token = os.getenv('REPLICATE_API_KEY')
    model = os.getenv('REPLICATE_MODEL', 'meta/llama-2-13b')
    
    headers = {
        'Authorization': f'Token {api_token}',
        'Content-Type': 'application/json'
    }
    
    # Создаем минимальный запрос
    payload = {
        'version': model,  # Используем ID модели как версию
        'input': {
            'prompt': 'Ответь одним словом: тест',
            'max_tokens': 10,
            'temperature': 0
        }
    }
    
    try:
        print(f"📤 Создание предсказания для модели: {model}")
        response = requests.post(
            'https://api.replicate.com/v1/predictions',
            headers=headers,
            json=payload,  # Убираем параметр model, используем только version
            timeout=30
        )
        
        print(f"📡 Статус ответа: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            prediction_id = data.get('id')
            print(f"✅ Предсказание создано: {prediction_id}")
            print(f"📊 Статус: {data.get('status')}")
            print(f"🔗 URL: {data.get('urls', {}).get('get', 'Нет URL')}")
            
            # Ждем завершения предсказания
            print("\n⏳ Ожидание завершения предсказания...")
            return wait_for_prediction(prediction_id, headers)
            
        elif response.status_code == 400:
            print("❌ Ошибка запроса (400)")
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print(f"   Детали: {error_data.get('detail', 'Неизвестная ошибка')}")
            
        elif response.status_code == 402:
            print("❌ Недостаточно средств (402)")
            print("   Баланс аккаунта исчерпан")
            
        elif response.status_code == 429:
            print("❌ Превышен лимит запросов (429)")
            print("   Слишком много одновременных запросов")
            
        else:
            print(f"❌ Неожиданная ошибка: {response.status_code}")
            
        print(f"📄 Полный ответ: {response.text}")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {str(e)}")
        return False

def wait_for_prediction(prediction_id, headers, max_wait=60):
    """Ожидание завершения предсказания"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f'https://api.replicate.com/v1/predictions/{prediction_id}',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                
                print(f"📊 Статус: {status}")
                
                if status == 'succeeded':
                    output = data.get('output')
                    print(f"✅ Предсказание завершено успешно")
                    print(f"💬 Результат: {output}")
                    
                    # Показываем метрики
                    metrics = data.get('metrics', {})
                    if metrics:
                        print(f"⏱️ Время выполнения: {metrics.get('predict_time', 'Неизвестно')}с")
                    
                    return True
                    
                elif status == 'failed':
                    error = data.get('error')
                    print(f"❌ Предсказание завершилось с ошибкой: {error}")
                    return False
                    
                elif status in ['starting', 'processing']:
                    print(f"⏳ Обработка... ({status})")
                    time.sleep(2)
                    continue
                    
                else:
                    print(f"⚠️ Неизвестный статус: {status}")
                    time.sleep(2)
                    continue
            else:
                print(f"❌ Ошибка получения статуса: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при проверке статуса: {str(e)}")
            return False
    
    print(f"⏰ Превышено время ожидания ({max_wait}с)")
    return False

def check_replicate_usage():
    """Проверка использования и лимитов"""
    print("\n📊 Проверка использования...")
    
    api_token = os.getenv('REPLICATE_API_KEY')
    headers = {
        'Authorization': f'Token {api_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Получаем список последних предсказаний
        response = requests.get(
            'https://api.replicate.com/v1/predictions?limit=5',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            predictions = data.get('results', [])
            
            print(f"📈 Последние {len(predictions)} предсказаний:")
            for pred in predictions:
                status = pred.get('status')
                created = pred.get('created_at', '')[:19].replace('T', ' ')
                model = pred.get('model', 'Неизвестно')
                print(f"   {created} | {status} | {model}")
                
                # Показываем ошибки если есть
                if status == 'failed' and pred.get('error'):
                    print(f"     ❌ Ошибка: {pred.get('error')[:100]}...")
        else:
            print(f"❌ Не удалось получить историю: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка получения истории: {str(e)}")

if __name__ == "__main__":
    print(f"🕐 Время начала диагностики Replicate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Проверяем API токен и аккаунт
    api_valid = check_replicate_api()
    
    if api_valid:
        # Проверяем модель
        model_valid = check_replicate_model()
        
        # Проверяем историю использования
        check_replicate_usage()
        
        # Тестируем создание предсказания
        if model_valid:
            prediction_success = test_replicate_prediction()
        else:
            prediction_success = False
        
        print("\n" + "=" * 50)
        print("📋 ИТОГИ ДИАГНОСТИКИ REPLICATE")
        print("=" * 50)
        print(f"🔑 API токен: {'✅ Действителен' if api_valid else '❌ Недействителен'}")
        print(f"🤖 Модель: {'✅ Доступна' if model_valid else '❌ Недоступна'}")
        print(f"🧪 Тестовое предсказание: {'✅ Успешно' if prediction_success else '❌ Неуспешно'}")
        
        if not prediction_success:
            print("\n🔧 РЕКОМЕНДАЦИИ:")
            print("1. Проверить баланс аккаунта Replicate")
            print("2. Убедиться, что модель meta/llama-2-13b доступна")
            print("3. Проверить правильность параметров запроса")
            print("4. Рассмотреть использование другой модели")
            print("5. Проверить сетевое соединение")
    
    print(f"\n🕐 Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")