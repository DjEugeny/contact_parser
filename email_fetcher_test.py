#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 Тестирование исправлений в advanced_email_fetcher_fixed.py
Проверяет работу фильтров исключения вложений
"""

import os
import logging
from pathlib import Path
import sys

# Добавляем текущую директорию в путь импорта
sys.path.append('.')

# Импортируем модуль
from src.advanced_email_fetcher_fixed import AdvancedEmailFetcherV2, EXCLUDED_EXTENSIONS

def setup_logger():
    """📝 Настройка простого логгера для тестирования"""
    logger = logging.getLogger("EmailFetcherTest")
    logger.setLevel(logging.INFO)
    
    # Очищаем обработчики, если есть
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Консольный вывод
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

def test_specific_files():
    """🧪 Тестирование исключения конкретных файлов"""
    logger = setup_logger()
    
    # Создаём экземпляр класса
    fetcher = AdvancedEmailFetcherV2(logger)
    
    # Список проблемных файлов для проверки
    test_files = [
        "_.jpg",             # Одиночный символ
        "blocked.gif",       # Мусорный GIF
        "WRD0004.jpg",       # Microsoft мусор
        "image001.png",      # Изображение из подписи
        "logo.png",          # Логотип
        "contract.pdf",      # Обычный документ (должен проходить)
        "important.xlsx",    # Обычный документ (должен проходить)
    ]
    
    print("\n�� ТЕСТИРОВАНИЕ ФИЛЬТРАЦИИ ФАЙЛОВ")
    print("="*50)
    
    # Проверка specific_excluded_files
    print("\n🔍 Проверка списка специальных исключений:")
    if hasattr(fetcher, 'specific_excluded_files'):
        for filename in test_files:
            result = filename in fetcher.specific_excluded_files
            status = "🚫 ИСКЛЮЧЕН" if result else "✅ РАЗРЕШЕН"
            print(f"{status}: {filename}")
    else:
        print("❌ ОШИБКА: Атрибут specific_excluded_files не найден")
    
    # Проверка расширений
    print("\n🔍 Проверка по расширениям файлов:")
    for filename in test_files:
        ext = Path(filename).suffix.lower()
        result = ext in EXCLUDED_EXTENSIONS
        status = "🚫 ИСКЛЮЧЕН" if result else "✅ РАЗРЕШЕН"
        print(f"{status}: {filename} (расширение: {ext})")
        
    print("\n🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    test_specific_files()
