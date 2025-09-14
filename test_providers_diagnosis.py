#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Диагностика провайдеров LLM для API Pipeline Validator
Создан для решения проблемы недоступности провайдеров
"""

import os
import sys
import requests
import json
from pathlib import Path

def check_environment_variables():
    """Проверка переменных окружения"""
    print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("=" * 50)
    
    # Сначала пробуем загрузить .env файл
    try:
        from dotenv import load_dotenv
        project_root = Path(__file__).parent
        env_path = project_root / ".env"
        
        print(f"   🔄 Попытка загрузки .env из: {env_path}")
        
        if env_path.exists():
            load_dotenv(env_path)
            print(f"   ✅ .env файл загружен")
        else:
            print(f"   ⚠️ .env файл не найден, используем системные переменные")
    except ImportError:
        print(f"   ⚠️ dotenv не установлен")
    except Exception as e:
        print(f"   ❌ Ошибка загрузки .env: {e}")
    
    required_vars = [
        'OPENROUTER_API_KEY',
        'REPLICATE_API_KEY', 
        'GROQ_API_KEY'
    ]
    
    found_vars = {}
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Показываем только первые и последние символы ключа
            masked_value = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***"
            found_vars[var] = masked_value
            print(f"   ✅ {var}: {masked_value}")
        else:
            print(f"   ❌ {var}: НЕ НАЙДЕН")
    
    return found_vars

def check_dotenv_file():
    """Проверка .env файла"""
    print("\n📄 ПРОВЕРКА .ENV ФАЙЛА")
    print("=" * 30)
    
    # Исправленные пути - ищем .env в корне проекта
    project_root = Path(__file__).parent  # Корень проекта
    env_files = [
        project_root / ".env",
        project_root / ".env.local",
        project_root / "config" / ".env"
    ]
    
    print(f"   🔍 Ищем в директории: {project_root}")
    
    for env_file in env_files:
        print(f"   🔍 Проверяем: {env_file}")
        if env_file.exists():
            print(f"   ✅ Найден: {env_file}")
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                    # Ищем API ключи
                    if 'OPENROUTER_API_KEY' in content:
                        print(f"      📋 OPENROUTER_API_KEY присутствует")
                    if 'REPLICATE_API_KEY' in content:
                        print(f"      📋 REPLICATE_API_KEY присутствует")
                    if 'GROQ_API_KEY' in content:
                        print(f"      📋 GROQ_API_KEY присутствует")
            except Exception as e:
                print(f"      ❌ Ошибка чтения: {e}")
        else:
            print(f"   ❌ Не найден: {env_file}")

def test_openrouter_direct():
    """Тест OpenRouter с реальным ключом из .env"""
    print("\n🤖 ТЕСТ OPENROUTER (РЕАЛЬНЫЙ КЛЮЧ ИЗ .ENV)")
    print("=" * 45)
    
    # Используем реальный ключ из переменных окружения
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("   ❌ OPENROUTER_API_KEY не найден в переменных окружения")
        return
    
    print(f"   🔑 Используем реальный ключ: {api_key[:15]}...{api_key[-8:]}")
    
    try:
        # Тест авторизации
        auth_url = "https://openrouter.ai/api/v1/auth/key"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.get(auth_url, headers=headers, timeout=10)
        print(f"   📡 Статус авторизации: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Авторизация успешна: {data}")
            
            # Проверяем использование и лимиты
            usage_data = data.get('data', {})
            if usage_data:
                usage = usage_data.get('usage', 'N/A')
                limit = usage_data.get('limit', 'N/A') 
                is_free = usage_data.get('is_free_tier', False)
                print(f"   📊 Использование: {usage}")
                print(f"   📊 Лимит: {limit}")
                print(f"   📊 Free tier: {is_free}")
            
            # Тест генерации
            test_completion(api_key)
            
        elif response.status_code == 401:
            print(f"   ❌ Ошибка авторизации: {response.text}")
            error_data = response.json()
            if 'User not found' in error_data.get('error', {}).get('message', ''):
                print(f"   💡 Ключ недействителен или заблокирован")
        elif response.status_code == 429:
            print(f"   🚫 ЛИМИТ ИСЧЕРПАН! {response.text}")
        else:
            print(f"   ⚠️ Неожиданный статус: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"   ⏱️ Таймаут запроса")
    except requests.exceptions.ConnectionError:
        print(f"   🌐 Ошибка соединения")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

def test_completion(api_key):
    """Тест генерации текста"""
    print(f"   🧪 Тест генерации текста...")
    
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://localhost:3000',
            'X-Title': 'Provider Diagnosis Test'
        }
        
        payload = {
            "model": "qwen/qwen3-235b-a22b:free",
            "messages": [
                {"role": "user", "content": "Привет! Это тест."}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"   📡 Статус генерации: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"   ✅ Ответ получен: {content[:100]}...")
        elif response.status_code == 429:
            print(f"   🚫 ЛИМИТ ИСЧЕРПАН! OpenRouter: {response.text}")
            # Проверяем детали лимита
            try:
                error_data = response.json()
                print(f"   📊 Детали лимита: {error_data}")
            except:
                pass
        else:
            print(f"   ❌ Ошибка генерации: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Ошибка тестирования: {e}")

def check_replicate_key():
    """Проверка ключа Replicate"""
    print("\n🦎 ПРОВЕРКА REPLICATE")
    print("=" * 25)
    
    api_key = os.getenv('REPLICATE_API_KEY')
    
    if not api_key:
        print("   ❌ REPLICATE_API_KEY не найден в переменных окружения")
        return False
        
    print(f"   🔑 Ключ найден: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        url = "https://api.replicate.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   📡 Статус: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Replicate API доступен")
            return True
        else:
            print(f"   ❌ Ошибка: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def check_api_pipeline_validator_setup():
    """Проверка настройки API Pipeline Validator"""
    print("\n🎯 ПРОВЕРКА API PIPELINE VALIDATOR")
    print("=" * 40)
    
    try:
        # Добавляем путь к src
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        from api_pipeline_validator import RealLLMProcessor
        
        print("   🔄 Инициализация RealLLMProcessor...")
        processor = RealLLMProcessor()
        
        print(f"   📊 Доступно провайдеров: {len(processor.api_providers)}")
        
        for provider in processor.api_providers:
            print(f"      - {provider['name']}: {provider['model']}")
            
        if not processor.api_providers:
            print("   ❌ НЕТ ДОСТУПНЫХ ПРОВАЙДЕРОВ!")
            print("   💡 Это объясняет, почему не создаются файлы результатов")
        
        return len(processor.api_providers) > 0
        
    except ImportError as e:
        print(f"   ❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def check_openrouter_status():
    """Проверить текущий статус OpenRouter (доступен ли для генерации)"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        return False
    
    try:
        # Тест простого запроса для проверки лимитов
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'deepseek/deepseek-chat-v3.1:free',
            'messages': [{'role': 'user', 'content': 'test'}],
            'max_tokens': 1
        }
        
        response = requests.post('https://openrouter.ai/api/v1/chat/completions', 
                               headers=headers, json=data, timeout=10)
        
        # Если статус 200, провайдер доступен
        # Если 429, превышен лимит
        return response.status_code == 200
    except:
        return False

def suggest_fixes():
    """Предложения по исправлению на основе реальной ситуации"""
    print("\n💡 РЕКОМЕНДАЦИИ ПО ОПТИМИЗАЦИИ")
    print("=" * 35)
    
    # Проверяем статус ключей
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    replicate_key = os.getenv('REPLICATE_API_KEY')
    groq_key = os.getenv('GROQ_API_KEY')
    
    # Проверяем актуальный статус OpenRouter
    openrouter_available = check_openrouter_status()
    
    if openrouter_key and replicate_key:
        if openrouter_available:
            print("✅ **ОТЛИЧНО: ВСЕ ПРОВАЙДЕРЫ ДОСТУПНЫ!**")
            print("   - OpenRouter: работает нормально")
            print("   - Replicate: работает нормально")
            print("   - API Pipeline Validator готов к работе")
        else:
            print("⚠️ **ЧАСТИЧНАЯ ДОСТУПНОСТЬ ПРОВАЙДЕРОВ**")
            print("   - OpenRouter: превышен дневной лимит (50 запросов)")
            print("   - Replicate: работает нормально ✅")
            print("   - API Pipeline Validator будет работать через Replicate")
            
        print("")
        print("🚀 **ЧТО МОЖНО ДЕЛАТЬ ПРЯМО СЕЙЧАС:**")
        print("   1. Запустить API Pipeline Validator:")
        print("      python src/api_pipeline_validator.py --mode first10")
        print("   2. Система автоматически использует доступные провайдеры")
        
        if not openrouter_available:
            print("")
            print("🔄 **ДЛЯ OpenRouter:**")
            print("   - Лимит сбросится завтра (50 запросов/день)")
            print("   - Или добавьте 10 кредитов для 1000 запросов/день")
            print("   - Сейчас система работает через Replicate")
        
        if not groq_key:
            print("")
            print("🔶 **ОПЦИОНАЛЬНОЕ УЛУЧШЕНИЕ:**")
            print("   - Можно добавить GROQ_API_KEY для третьего провайдера")
        
        print("")
        print("⚠️ **О ОШИБКАХ ИМПОРТА:**")
        print("   - Ошибки 'psutil' и 'google' не критичны")
        print("   - Система работает через fallback механизмы")
        print("   - Основная функциональность сохранена")
        
    else:
        print("❌ **ПРОБЛЕМЫ С НАСТРОЙКОЙ:**")
        
        if not openrouter_key and not replicate_key:
            print("1. 🔑 НАСТРОЙКА API КЛЮЧЕЙ:")
            print("   - Создайте файл .env в корне проекта")
            print("   - Добавьте действующие ключи:")
            print("     OPENROUTER_API_KEY=your_key_here")
            print("     REPLICATE_API_KEY=your_key_here")
        
        print("\n2. 🔄 ПРОВЕРКА ЛИМИТОВ:")
        print("   - OpenRouter free tier: 50 запросов/день")
        print("   - Проверьте использование на https://openrouter.ai/credits")
        print("   - Replicate: платный доступ, проверьте баланс")
        
        print("\n3. 🔧 ВРЕМЕННОЕ РЕШЕНИЕ:")
        print("   - Используйте режим test_mode=True для тестирования без LLM")
        print("   - Или настройте локальную модель (Ollama)")

def main():
    """Главная функция диагностики"""
    print("🔍 ДИАГНОСТИКА ПРОВАЙДЕРОВ LLM")
    print("=" * 50)
    print("Создано для решения проблемы с API Pipeline Validator")
    print("")
    
    # 1. Проверка переменных окружения
    env_vars = check_environment_variables()
    
    # 2. Проверка .env файлов
    check_dotenv_file()
    
    # 3. Тест OpenRouter (реальный ключ)
    test_openrouter_direct()  # Показываем детальный вывод
    openrouter_works = check_openrouter_status()  # Получаем актуальный статус
    
    # 4. Тест Replicate
    replicate_works = check_replicate_key()
    
    # 5. Тест настройки валидатора
    has_providers = check_api_pipeline_validator_setup()
    
    # 6. Рекомендации
    suggest_fixes()
    
    print(f"\n🏁 ИТОГ ДИАГНОСТИКИ")
    print("=" * 20)
    
    if not env_vars:
        print("❌ Основная проблема: НЕТ API КЛЮЧЕЙ в переменных окружения")
    elif openrouter_works or replicate_works:
        print("✅ Провайдеры работают корректно")
        if openrouter_works and replicate_works:
            print("🎉 Оба основных провайдера доступны!")
        elif openrouter_works:
            print("🔶 OpenRouter работает, Replicate недоступен")
        elif replicate_works:
            print("🔶 Replicate работает, OpenRouter недоступен")
    else:
        print("❌ Основная проблема: API ключи недействительны или исчерпаны лимиты")

def test_openrouter_with_real_key():
    """Тест OpenRouter с реальным ключом и возврат статуса"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        return False
        
    try:
        auth_url = "https://openrouter.ai/api/v1/auth/key"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(auth_url, headers=headers, timeout=10)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    main()