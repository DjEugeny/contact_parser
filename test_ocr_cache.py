#!/usr/bin/env python3
"""Тест OCRCacheManager"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.ocr_cache_manager import OCRCacheManager

# Создаем менеджер
cache = OCRCacheManager()

# Тестируем поиск файла
filename = "ru_be4fb59a_084146_attach_АНКЕТА Участника.docx"
date = "2025-07-23"

print(f"🧪 Тест поиска файла:")
print(f"  Файл: {filename}")
print(f"  Дата: {date}")
print()

result = cache.get_cached_result(filename, date)

if result:
    print(f"✅ Найден результат OCR!")
    print(f"  Длина текста: {len(result)} символов")
    print(f"  Превью: {result[:200]}...")
else:
    print(f"❌ Результат не найден")

print()
print(f"📊 Статистика:")
stats = cache.get_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")

