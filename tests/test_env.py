# Создаем диагностический файл
#!/usr/bin/env python3
"""🔍 Проверка переменных окружения"""

import os
from pathlib import Path
from dotenv import load_dotenv

print("🔍 ДИАГНОСТИКА API КЛЮЧА:")
print("=" * 40)

# Проверяем текущую папку
current_dir = os.getcwd()
print(f"📁 Текущая папка: {current_dir}")

# Проверяем существование .env
env_file = Path(".env")
print(f"📄 .env файл существует: {env_file.exists()}")
if env_file.exists():
    print(f"   Размер файла: {env_file.stat().st_size} байт")

# Загружаем .env
print(f"\n🔄 Загрузка .env файла...")
load_result = load_dotenv()
print(f"   Результат загрузки: {load_result}")

# Проверяем ключ
print(f"\n🔑 Проверка API ключа:")
api_key = os.getenv('OPENROUTER_API_KEY')
if api_key:
    print(f"✅ OPENROUTER_API_KEY найден")
    print(f"   Длина: {len(api_key)} символов")
    print(f"   Начинается с: {api_key[:15]}...")
    
    # Проверяем формат ключа OpenRouter
    if api_key.startswith('sk-or-v1-'):
        print("✅ Формат ключа ПРАВИЛЬНЫЙ (sk-or-v1-...)")
    else:
        print("⚠️ Неправильный формат ключа OpenRouter")
        print("   Должен начинаться с: sk-or-v1-")
        
    # Проверяем на скрытые символы
    clean_key = api_key.strip()
    if len(clean_key) != len(api_key):
        print("⚠️ В ключе есть лишние пробелы/символы")
    else:
        print("✅ Ключ без лишних символов")
        
else:
    print("❌ OPENROUTER_API_KEY НЕ НАЙДЕН!")

# Проверяем все переменные окружения
print(f"\n📋 Все переменные из .env:")
env_vars = ['IMAP_SERVER', 'IMAP_USER', 'OPENROUTER_API_KEY', 'COMPANY_DOMAIN']
for var in env_vars:
    value = os.getenv(var)
    if value:
        # Показываем только первые символы для безопасности
        if 'KEY' in var or 'PASSWORD' in var:
            safe_value = value[:10] + "..." if len(value) > 10 else value
        else:
            safe_value = value
        print(f"   ✅ {var}: {safe_value}")
    else:
        print(f"   ❌ {var}: НЕ НАЙДЕН")

# Тест подключения к OpenRouter
print(f"\n🤖 ТЕСТ ПОДКЛЮЧЕНИЯ К OPENROUTER:")
try:
    import openai
    
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    print("✅ OpenAI клиент создан успешно")
    print("🚀 Готов к тестированию LLM!")
    
except Exception as e:
    print(f"❌ Ошибка создания клиента: {e}")
    
print(f"\n" + "=" * 40)
