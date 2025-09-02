#!/usr/bin/env python3
"""🔍 Исправленная проверка пакетов"""

import sys

print(f"🐍 Используемый Python: {sys.executable}")
print(f"📍 Версия: {sys.version}")

print("\n🔍 ПРОВЕРКА УСТАНОВЛЕННЫХ ПАКЕТОВ:")
print("=" * 50)

# Список пакетов для проверки
packages_to_check = [
    ('openai', 'openai'),
    ('langchain', 'langchain'),
    ('gspread', 'gspread'),
    ('python-dotenv', 'dotenv'),
    ('beautifulsoup4', 'bs4'),
    ('tiktoken', 'tiktoken'),
    ('rapidfuzz', 'rapidfuzz')
]

for package_name, import_name in packages_to_check:
    try:
        module = __import__(import_name)
        # Безопасная проверка версии
        version = getattr(module, '__version__', 'установлен')
        print(f"✅ {package_name} - установлен (версия: {version})")
    except ImportError:
        print(f"❌ {package_name} - НЕ УСТАНОВЛЕН")

print("\n🎯 ПРОВЕРКА КЛЮЧЕВЫХ ИМПОРТОВ:")
print("=" * 40)

# Тестируем импорты которые нам нужны
test_imports = [
    ("from dotenv import load_dotenv", lambda: __import__('dotenv').load_dotenv),
    ("from bs4 import BeautifulSoup", lambda: getattr(__import__('bs4'), 'BeautifulSoup')),
    ("import openai", lambda: __import__('openai')),
    ("import langchain", lambda: __import__('langchain')),
    ("import gspread", lambda: __import__('gspread'))
]

for import_statement, test_func in test_imports:
    try:
        test_func()
        print(f"✅ {import_statement} - работает")
    except ImportError as e:
        print(f"❌ {import_statement} - ошибка: {e}")
    except Exception as e:
        print(f"⚠️ {import_statement} - работает, но: {e}")

print("\n🚀 ГОТОВНОСТЬ К РАБОТЕ:")
print("=" * 30)

ready_count = 0
critical_packages = ['openai', 'dotenv', 'langchain']

for pkg in critical_packages:
    try:
        __import__(pkg)
        ready_count += 1
    except:
        pass

if ready_count == len(critical_packages):
    print("🎉 ВСЁ ГОТОВО ДЛЯ ТЕСТИРОВАНИЯ LLM!")
    print("💪 Можем приступать к извлечению контактов!")
else:
    print(f"⚠️ Готово {ready_count}/{len(critical_packages)} критичных пакетов")
