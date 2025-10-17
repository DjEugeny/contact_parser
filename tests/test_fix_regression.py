#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест исправления деградации качества данных
Проверяет, что исправление api_pipeline_validator.py работает корректно
"""

import json
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api_pipeline_validator import APIPipelineValidator
from argparse import Namespace


def test_email_012():
    """Тест на email_012 (NEW fetcher format)"""
    print("\n" + "="*80)
    print("🧪 ТЕСТ 1: email_012_20250827 (NEW fetcher format)")
    print("="*80)
    
    # Путь к файлу с NEW форматом
    email_file = Path("data/emails/2025-08-27-new/email_012_20250827_20250827_assa-group_ru_d06eed18.json")
    
    if not email_file.exists():
        print(f"❌ Файл не найден: {email_file}")
        return False
    
    # Читаем файл
    with open(email_file, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    # Проверяем структуру
    print(f"\n📋 Структура данных:")
    print(f"   - body: {'✅' if 'body' in email_data else '❌'}")
    print(f"   - body_clean: {'✅' if 'body_clean' in email_data else '❌'}")
    print(f"   - body_raw: {'✅' if 'body_raw' in email_data else '❌'}")
    
    if 'body_clean' in email_data:
        print(f"   - body_clean length: {len(email_data['body_clean'])} символов")
    
    # Создаем validator
    args = Namespace(
        mode='first10',
        date='2025-08-27',
        count=1,
        start_id=None,
        end_id=None
    )
    
    validator = APIPipelineValidator(args)
    
    # Тестируем метод _compose_combined_text
    print(f"\n🔧 Тестируем _compose_combined_text()...")
    combined_text = validator._compose_combined_text(email_data, '2025-08-27')
    
    # Проверяем результат
    print(f"\n📊 Результаты:")
    print(f"   - Длина combined_text: {len(combined_text)} символов")
    print(f"   - Содержит '=== ТЕКСТ ПИСЬМА ===': {'✅' if '=== ТЕКСТ ПИСЬМА ===' in combined_text else '❌'}")
    
    # Критерии успеха
    success = True
    
    if len(combined_text) < 1000:
        print(f"   ❌ ПРОВАЛ: combined_text слишком короткий ({len(combined_text)} < 1000)")
        success = False
    else:
        print(f"   ✅ УСПЕХ: combined_text достаточно длинный")
    
    if '=== ТЕКСТ ПИСЬМА ===' not in combined_text:
        print(f"   ❌ ПРОВАЛ: Текст письма не добавлен в combined_text")
        success = False
    else:
        print(f"   ✅ УСПЕХ: Текст письма добавлен")
    
    # Проверяем наличие ключевых данных
    keywords = ['Роженцова', 'Алёна', 'АССА', 'ДНК-Технология', 'Гоголева']
    found_keywords = [kw for kw in keywords if kw in combined_text]
    
    print(f"\n🔍 Ключевые слова найдены: {len(found_keywords)}/{len(keywords)}")
    for kw in keywords:
        status = '✅' if kw in combined_text else '❌'
        print(f"   {status} {kw}")
    
    if len(found_keywords) < 4:
        print(f"   ❌ ПРОВАЛ: Недостаточно ключевых слов ({len(found_keywords)}/5)")
        success = False
    else:
        print(f"   ✅ УСПЕХ: Ключевые данные присутствуют")
    
    return success


def test_email_003():
    """Тест на email_003 (NEW fetcher format)"""
    print("\n" + "="*80)
    print("🧪 ТЕСТ 2: email_003_20250828 (NEW fetcher format)")
    print("="*80)
    
    # Путь к файлу с NEW форматом
    email_file = Path("data/emails/2025-08-28-new/email_003_20250828_20250828_assa-group_ru_08d594fe.json")
    
    if not email_file.exists():
        print(f"❌ Файл не найден: {email_file}")
        return False
    
    # Читаем файл
    with open(email_file, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    # Проверяем структуру
    print(f"\n📋 Структура данных:")
    print(f"   - body: {'✅' if 'body' in email_data else '❌'}")
    print(f"   - body_clean: {'✅' if 'body_clean' in email_data else '❌'}")
    print(f"   - body_raw: {'✅' if 'body_raw' in email_data else '❌'}")
    
    if 'body_clean' in email_data:
        print(f"   - body_clean length: {len(email_data['body_clean'])} символов")
    
    # Создаем validator
    args = Namespace(
        mode='first10',
        date='2025-08-28',
        count=1,
        start_id=None,
        end_id=None
    )
    
    validator = APIPipelineValidator(args)
    
    # Тестируем метод _compose_combined_text
    print(f"\n🔧 Тестируем _compose_combined_text()...")
    combined_text = validator._compose_combined_text(email_data, '2025-08-28')
    
    # Проверяем результат
    print(f"\n📊 Результаты:")
    print(f"   - Длина combined_text: {len(combined_text)} символов")
    print(f"   - Содержит '=== ТЕКСТ ПИСЬМА ===': {'✅' if '=== ТЕКСТ ПИСЬМА ===' in combined_text else '❌'}")
    
    # Критерии успеха
    success = True
    
    if len(combined_text) < 1500:
        print(f"   ❌ ПРОВАЛ: combined_text слишком короткий ({len(combined_text)} < 1500)")
        success = False
    else:
        print(f"   ✅ УСПЕХ: combined_text достаточно длинный")
    
    if '=== ТЕКСТ ПИСЬМА ===' not in combined_text:
        print(f"   ❌ ПРОВАЛ: Текст письма не добавлен в combined_text")
        success = False
    else:
        print(f"   ✅ УСПЕХ: Текст письма добавлен")
    
    # Проверяем наличие ключевых данных
    keywords = ['Роженцова', 'Гоголева', 'Воронова', 'АССА', 'Хакасская']
    found_keywords = [kw for kw in keywords if kw in combined_text]
    
    print(f"\n🔍 Ключевые слова найдены: {len(found_keywords)}/{len(keywords)}")
    for kw in keywords:
        status = '✅' if kw in combined_text else '❌'
        print(f"   {status} {kw}")
    
    if len(found_keywords) < 4:
        print(f"   ❌ ПРОВАЛ: Недостаточно ключевых слов ({len(found_keywords)}/5)")
        success = False
    else:
        print(f"   ✅ УСПЕХ: Ключевые данные присутствуют")
    
    return success


def test_legacy_compatibility():
    """Тест обратной совместимости с legacy форматом"""
    print("\n" + "="*80)
    print("🧪 ТЕСТ 3: Обратная совместимость (LEGACY format)")
    print("="*80)
    
    # Путь к файлу с LEGACY форматом
    email_file = Path("data/emails/2025-08-27/email_012_20250827_20250827_assa-group_ru_d06eed18.json")
    
    if not email_file.exists():
        print(f"❌ Файл не найден: {email_file}")
        return False
    
    # Читаем файл
    with open(email_file, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    # Проверяем структуру
    print(f"\n📋 Структура данных:")
    print(f"   - body: {'✅' if 'body' in email_data else '❌'}")
    print(f"   - body_clean: {'✅' if 'body_clean' in email_data else '❌'}")
    print(f"   - body_raw: {'✅' if 'body_raw' in email_data else '❌'}")
    
    if 'body' in email_data:
        print(f"   - body length: {len(email_data['body'])} символов")
    
    # Создаем validator
    args = Namespace(
        mode='first10',
        date='2025-08-27',
        count=1,
        start_id=None,
        end_id=None
    )
    
    validator = APIPipelineValidator(args)
    
    # Тестируем метод _compose_combined_text
    print(f"\n🔧 Тестируем _compose_combined_text()...")
    combined_text = validator._compose_combined_text(email_data, '2025-08-27')
    
    # Проверяем результат
    print(f"\n📊 Результаты:")
    print(f"   - Длина combined_text: {len(combined_text)} символов")
    print(f"   - Содержит '=== ТЕКСТ ПИСЬМА ===': {'✅' if '=== ТЕКСТ ПИСЬМА ===' in combined_text else '❌'}")
    
    # Критерии успеха
    success = True
    
    if len(combined_text) < 3000:
        print(f"   ❌ ПРОВАЛ: combined_text слишком короткий ({len(combined_text)} < 3000)")
        success = False
    else:
        print(f"   ✅ УСПЕХ: combined_text достаточно длинный")
    
    if '=== ТЕКСТ ПИСЬМА ===' not in combined_text:
        print(f"   ❌ ПРОВАЛ: Текст письма не добавлен в combined_text")
        success = False
    else:
        print(f"   ✅ УСПЕХ: Текст письма добавлен")
    
    return success


def main():
    """Запуск всех тестов"""
    print("\n" + "🎯"*40)
    print("🧪 РЕГРЕССИОННОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ")
    print("🎯"*40)
    print("\nПроверяем исправление api_pipeline_validator.py")
    print("Задача 1.3 из tasks.md")
    
    results = []
    
    # Тест 1
    try:
        result1 = test_email_012()
        results.append(("email_012 (NEW)", result1))
    except Exception as e:
        print(f"\n❌ ОШИБКА в тесте 1: {e}")
        import traceback
        traceback.print_exc()
        results.append(("email_012 (NEW)", False))
    
    # Тест 2
    try:
        result2 = test_email_003()
        results.append(("email_003 (NEW)", result2))
    except Exception as e:
        print(f"\n❌ ОШИБКА в тесте 2: {e}")
        import traceback
        traceback.print_exc()
        results.append(("email_003 (NEW)", False))
    
    # Тест 3
    try:
        result3 = test_legacy_compatibility()
        results.append(("Legacy compatibility", result3))
    except Exception as e:
        print(f"\n❌ ОШИБКА в тесте 3: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Legacy compatibility", False))
    
    # Итоги
    print("\n" + "="*80)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("="*80)
    
    for test_name, result in results:
        status = "✅ УСПЕХ" if result else "❌ ПРОВАЛ"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n🎯 Пройдено: {passed}/{total} тестов")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Исправление работает корректно.")
        return 0
    else:
        print(f"\n⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ ({total - passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
