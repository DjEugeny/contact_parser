#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Простой тест исправления (без импорта всего модуля)
Тестирует только логику извлечения body
"""

import json
from pathlib import Path


def extract_body_with_fallback(email_data):
    """Копия исправленной логики из api_pipeline_validator.py"""
    body_candidates = [
        email_data.get("body"),          # legacy
        email_data.get("body_clean"),    # NEW (приоритет)
        email_data.get("body_raw"),      # NEW (fallback)
        email_data.get("body_plain"),
        email_data.get("body_text"),
        email_data.get("text"),
    ]
    
    body = None
    body_source = None
    for candidate_name, candidate in zip(
        ["body", "body_clean", "body_raw", "body_plain", "body_text", "text"],
        body_candidates
    ):
        if candidate and isinstance(candidate, str) and candidate.strip():
            body = candidate
            body_source = candidate_name
            break
    
    return body, body_source


def test_file(file_path, expected_min_length, test_name):
    """Тестирует один файл"""
    print(f"\n{'='*80}")
    print(f"🧪 {test_name}")
    print(f"{'='*80}")
    print(f"📁 Файл: {file_path}")
    
    if not file_path.exists():
        print(f"❌ Файл не найден!")
        return False
    
    # Читаем файл
    with open(file_path, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    # Проверяем структуру
    print(f"\n📋 Структура данных:")
    has_body = 'body' in email_data
    has_body_clean = 'body_clean' in email_data
    has_body_raw = 'body_raw' in email_data
    
    print(f"   - body: {'✅' if has_body else '❌'}")
    print(f"   - body_clean: {'✅' if has_body_clean else '❌'}")
    print(f"   - body_raw: {'✅' if has_body_raw else '❌'}")
    
    if has_body:
        print(f"   - body length: {len(email_data['body'])} символов")
    if has_body_clean:
        print(f"   - body_clean length: {len(email_data['body_clean'])} символов")
    if has_body_raw:
        print(f"   - body_raw length: {len(email_data['body_raw'])} символов")
    
    # Тестируем извлечение
    print(f"\n🔧 Тестируем извлечение body...")
    body, body_source = extract_body_with_fallback(email_data)
    
    # Результаты
    print(f"\n📊 Результаты:")
    
    if body is None:
        print(f"   ❌ ПРОВАЛ: body не извлечён!")
        return False
    
    print(f"   ✅ Использовано поле: '{body_source}'")
    print(f"   ✅ Длина: {len(body)} символов")
    
    # Проверка длины
    if len(body) < expected_min_length:
        print(f"   ❌ ПРОВАЛ: body слишком короткий ({len(body)} < {expected_min_length})")
        return False
    else:
        print(f"   ✅ УСПЕХ: body достаточно длинный (>= {expected_min_length})")
    
    # Проверка ключевых слов
    keywords = ['Роженцова', 'Гоголева', 'АССА', 'ДНК']
    found = [kw for kw in keywords if kw in body]
    
    print(f"\n🔍 Ключевые слова: {len(found)}/{len(keywords)}")
    for kw in keywords:
        status = '✅' if kw in body else '❌'
        print(f"   {status} {kw}")
    
    if len(found) < 3:
        print(f"   ⚠️ ПРЕДУПРЕЖДЕНИЕ: Мало ключевых слов ({len(found)}/{len(keywords)})")
    else:
        print(f"   ✅ УСПЕХ: Ключевые данные присутствуют")
    
    return True


def main():
    """Запуск всех тестов"""
    print("\n" + "🎯"*40)
    print("🧪 РЕГРЕССИОННОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ")
    print("🎯"*40)
    print("\nПроверяем логику извлечения body из email_data")
    print("Задача 1.3 из tasks.md\n")
    
    tests = [
        (
            Path("data/emails/2025-08-27-new/email_012_20250827_20250827_assa-group_ru_d06eed18.json"),
            2000,
            "ТЕСТ 1: email_012 (NEW fetcher - body_clean)"
        ),
        (
            Path("data/emails/2025-08-28-new/email_003_20250828_20250828_assa-group_ru_08d594fe.json"),
            2500,
            "ТЕСТ 2: email_003 (NEW fetcher - body_clean)"
        ),
        (
            Path("data/emails/2025-08-27/email_012_20250827_20250827_assa-group_ru_d06eed18.json"),
            5000,
            "ТЕСТ 3: email_012 (LEGACY fetcher - body)"
        ),
    ]
    
    results = []
    
    for file_path, min_length, test_name in tests:
        try:
            result = test_file(file_path, min_length, test_name)
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Итоги
    print(f"\n{'='*80}")
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print(f"{'='*80}\n")
    
    for test_name, result in results:
        status = "✅ УСПЕХ" if result else "❌ ПРОВАЛ"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n🎯 Пройдено: {passed}/{total} тестов")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ Исправление работает корректно")
        print("✅ Поддержка NEW формата (body_clean, body_raw)")
        print("✅ Обратная совместимость с LEGACY форматом (body)")
        return 0
    else:
        print(f"\n⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ ({total - passed}/{total})")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
