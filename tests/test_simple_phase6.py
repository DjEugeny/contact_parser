#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Простое тестирование оптимизаций Фазы 6
"""

import sys
import json
import time
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.extractor_factory import ExtractorFactory

def test_single_file():
    """Тестирование одного файла с оптимизациями"""

    # Путь к тестовому файлу
    test_file = Path('data/emails/2025-07-29/email_001_20250729_20250729_centerld_ru_d03bd60b.json')

    print("🧪 Тестирование оптимизаций Фазы 6")
    print(f"📁 Файл: {test_file.name}")

    try:
        # Загружаем данные
        with open(test_file, 'r', encoding='utf-8') as f:
            email_data = json.load(f)

        text = email_data.get('body', '')[:2000]  # Ограничиваем для теста
        print(f"📏 Размер текста: {len(text)} символов")

        # Создаем экстрактор
        print("🎯 Создание экстрактора...")
        extractor = ExtractorFactory.create_extractor()

        # Первый запуск (без кэша)
        print("🚀 Первый запуск...")
        start_time = time.time()
        result1 = extractor.extract_all_data(text)
        first_time = time.time() - start_time

        print(".2f")
        print(f"📊 Контактов: {len(result1.get('contacts', []))}")

        # Проверяем кэш
        cache_stats = extractor.cache.get_cache_stats()
        print(f"💾 Кэш - hits: {cache_stats.get('overall_hit_rate', 0):.1f}%")

        # Второй запуск (с кэшем)
        print("🔄 Второй запуск (с кэшем)...")
        start_time = time.time()
        result2 = extractor.extract_all_data(text)
        second_time = time.time() - start_time

        print(".2f")
        print(f"📊 Контактов: {len(result2.get('contacts', []))}")

        # Вычисляем ускорение
        if second_time > 0:
            speedup = first_time / second_time
            print(".1f")
        # Статистика памяти
        memory_stats = extractor.memory_optimizer.get_comprehensive_stats()
        print(".1f")
        print(".1f")
        print("✅ Тест завершен успешно!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_file()
