#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправлений chunking логики
Дата создания: 2025-08-26 22:40 (UTC+07)

Проверяет:
1. Короткие тексты не разбиваются на избыточное количество чанков
2. Длинные тексты корректно разбиваются с учетом новых ограничений
3. Логика overlap_tokens работает корректно
"""

import sys
import os
import json
from datetime import datetime

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm_extractor import ContactExtractor

def test_short_text_chunking():
    """Тест разбиения короткого текста"""
    print("\n=== Тест короткого текста ===")
    
    # Короткий текст (примерно 50 токенов)
    short_text = """
    Уважаемые коллеги!
    
    Меня зовут Иван Петров, я представляю компанию ООО "Технологии".
    Телефон: +7 (495) 123-45-67
    Email: ivan.petrov@tech.ru
    
    С уважением,
    Иван Петров
    """
    
    extractor = ContactExtractor(test_mode=True)
    config = {
        'use_token_based': True,
        'max_tokens_per_chunk': 3000,
        'overlap_tokens': 300,
        'max_chunks_per_text': 10
    }
    chunks = extractor._create_token_based_chunks(short_text, config)
    
    print(f"Количество чанков для короткого текста: {len(chunks)}")
    print(f"Ожидается: 1-2 чанка")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\nЧанк {i} (длина: {len(chunk)} символов):")
        print(f"'{chunk[:100]}...'" if len(chunk) > 100 else f"'{chunk}'")
    
    # Проверка: короткий текст должен давать 1-2 чанка максимум
    assert len(chunks) <= 2, f"Короткий текст разбился на {len(chunks)} чанков, ожидалось ≤2"
    assert all(chunk.strip() for chunk in chunks), "Найдены пустые чанки"
    
    print("✅ Тест короткого текста пройден")
    return len(chunks)

def test_medium_text_chunking():
    """Тест разбиения текста средней длины"""
    print("\n=== Тест текста средней длины ===")
    
    # Текст средней длины (примерно 200-300 токенов)
    medium_text = """
    Добрый день!
    
    Меня зовут Александр Сидоров, я коммерческий директор компании ООО "Инновации Плюс".
    Наша компания специализируется на разработке и внедрении современных IT-решений 
    для автоматизации бизнес-процессов в различных отраслях экономики.
    
    Мы предлагаем следующие услуги:
    - Разработка корпоративных веб-приложений
    - Интеграция с существующими системами учета
    - Консультации по цифровой трансформации
    - Техническая поддержка и сопровождение
    
    Наши контакты:
    Телефон: +7 (812) 987-65-43
    Email: a.sidorov@innovations-plus.ru
    Сайт: www.innovations-plus.ru
    Адрес: г. Санкт-Петербург, ул. Невский проспект, д. 123, офис 456
    
    Мы готовы предложить индивидуальные решения под ваши задачи.
    Будем рады обсудить возможности сотрудничества.
    
    С уважением,
    Александр Сидоров
    Коммерческий директор
    ООО "Инновации Плюс"
    """
    
    extractor = ContactExtractor(test_mode=True)
    config = {
        'use_token_based': True,
        'max_tokens_per_chunk': 3000,
        'overlap_tokens': 300,
        'max_chunks_per_text': 10
    }
    chunks = extractor._create_token_based_chunks(medium_text, config)
    
    print(f"Количество чанков для текста средней длины: {len(chunks)}")
    print(f"Ожидается: 2-4 чанка")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\nЧанк {i} (длина: {len(chunk)} символов):")
        print(f"'{chunk[:150]}...'" if len(chunk) > 150 else f"'{chunk}'")
    
    # Проверка: текст средней длины должен давать разумное количество чанков
    assert len(chunks) <= 10, f"Текст средней длины разбился на {len(chunks)} чанков, ожидалось ≤10"
    assert all(chunk.strip() for chunk in chunks), "Найдены пустые чанки"
    
    print("✅ Тест текста средней длины пройден")
    return len(chunks)

def test_long_text_chunking():
    """Тест разбиения длинного текста"""
    print("\n=== Тест длинного текста ===")
    
    # Создаем действительно длинный текст путем повторения
    long_text = "Это очень длинное письмо с множеством информации и деталей. " * 3000 + "Контакт: long@example.com"
    
    extractor = ContactExtractor(test_mode=True)
    config = {
        'use_token_based': True,
        'max_tokens_per_chunk': 1000,  # Уменьшаем размер чанка для принудительного разбиения
        'overlap_tokens': 100,
        'max_chunks_per_text': 10
    }
    
    chunks = extractor._create_token_based_chunks(long_text, config)
    
    print(f"Количество чанков для длинного текста: {len(chunks)}")
    print(f"Ожидается: 5-10 чанков (не более 10)")
    
    # Показываем информацию о чанках
    for i, chunk in enumerate(chunks[:3]):  # Показываем только первые 3
        print(f"\nЧанк {i+1} (длина: {len(chunk)} символов):")
        print(f"'{chunk[:100]}...'")
    
    # Проверяем, что длинный текст действительно разбился
    assert len(chunks) >= 3, f"Длинный текст разбился только на {len(chunks)} чанков, ожидалось ≥3"
    assert len(chunks) <= 10, f"Превышен лимит чанков: {len(chunks)} > 10"
    
    print("✅ Тест длинного текста пройден")
    return len(chunks)

def test_overlap_logic():
    """Тест логики overlap_tokens"""
    print("\n=== Тест логики overlap ===")
    
    # Текст для проверки overlap
    test_text = """
    Первый абзац с важной информацией о компании и контактах.
    Второй абзац с дополнительными деталями и описанием услуг.
    Третий абзац с финальной информацией и призывом к действию.
    """
    
    extractor = ContactExtractor(test_mode=True)
    
    # Проверяем, что overlap не создает проблем
    config = {
        'use_token_based': True,
        'max_tokens_per_chunk': 3000,
        'overlap_tokens': 300,
        'max_chunks_per_text': 10
    }
    chunks = extractor._create_token_based_chunks(test_text, config)
    
    print(f"Количество чанков с overlap: {len(chunks)}")
    
    # Проверяем отсутствие полностью дублирующихся чанков
    unique_chunks = set(chunks)
    assert len(unique_chunks) == len(chunks), "Найдены полностью дублирующиеся чанки"
    
    # Дополнительный тест с большим overlap
    short_text = "Короткий текст"
    config_big_overlap = {
        'use_token_based': True,
        'max_tokens_per_chunk': 100,  # Маленький размер чанка
        'overlap_tokens': 500,        # Большой overlap
        'max_chunks_per_text': 10
    }
    
    chunks_big_overlap = extractor._create_token_based_chunks(short_text, config_big_overlap)
    print(f"Количество чанков с большим overlap: {len(chunks_big_overlap)}")
    
    # Не должно быть бесконечного цикла или ошибок
    assert len(chunks_big_overlap) > 0, "Чанки не созданы"
    assert len(chunks_big_overlap) <= 5, f"Слишком много чанков для короткого текста: {len(chunks_big_overlap)}"
    
    print("✅ Тест логики overlap пройден")
    return len(chunks)

def main():
    """Основная функция тестирования"""
    print("Тестирование исправлений chunking логики")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
    print("=" * 60)
    
    try:
        # Запускаем тесты
        short_chunks = test_short_text_chunking()
        medium_chunks = test_medium_text_chunking()
        long_chunks = test_long_text_chunking()
        overlap_chunks = test_overlap_logic()
        
        # Сводка результатов
        print("\n" + "=" * 60)
        print("СВОДКА РЕЗУЛЬТАТОВ:")
        print(f"Короткий текст: {short_chunks} чанков (ожидалось ≤2)")
        print(f"Средний текст: {medium_chunks} чанков (ожидалось ≤10)")
        print(f"Длинный текст: {long_chunks} чанков (ожидалось 3-10)")
        print(f"Тест overlap: {overlap_chunks} чанков")
        
        # Проверка общих ограничений
        max_chunks_found = max(short_chunks, medium_chunks, long_chunks, overlap_chunks)
        print(f"\nМаксимальное количество чанков: {max_chunks_found}")
        print(f"Лимит max_chunks_per_text: 10")
        
        if max_chunks_found <= 10:
            print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("Исправления chunking работают корректно.")
        else:
            print("\n❌ ТЕСТЫ НЕ ПРОЙДЕНЫ!")
            print(f"Найдено {max_chunks_found} чанков, что превышает лимит 10.")
            
    except Exception as e:
        print(f"\n❌ ОШИБКА ПРИ ТЕСТИРОВАНИИ: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\nВремя завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)