#!/usr/bin/env python3
"""Интеграционный тест OCRCacheManager"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.ocr_cache_manager import OCRCacheManager

# Создаем менеджер
cache = OCRCacheManager()

# Тестовые файлы из логов
test_cases = [
    ("20250723_dna-technology_ru_be4fb59a_084146_attach_АНКЕТА Участника.docx", "2025-07-23"),
    ("20250723_dna-technology_ru_be4fb59a_084146_attach_Письмо для пользователей 1.1.doc", "2025-07-23"),
    ("20250723_dna-technology_ru_1c456124_084214_attach_КП 8386 от 23.07.2025.pdf", "2025-07-23"),
]

print("🧪 Интеграционный тест OCRCacheManager")
print("="*60)

for filename, date in test_cases:
    result = cache.get_cached_result(filename, date)
    status = "✅" if result else "❌"
    length = len(result) if result else 0
    print(f"{status} {filename[:50]}... ({length} символов)")

print("="*60)
print(f"�� Статистика:")
stats = cache.get_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")

