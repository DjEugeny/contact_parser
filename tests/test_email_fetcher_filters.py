#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 Автоматические тесты для проверки фильтров модуля advanced_email_fetcher.py
"""

import os
import sys
import unittest
import logging
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.advanced_email_fetcher import AdvancedEmailFetcherV2, EXCLUDED_EXTENSIONS

class TestEmailFetcherFilters(unittest.TestCase):
    """Тестирование фильтров для вложений в email_fetcher"""
    
    def setUp(self):
        """Подготовка перед каждым тестом"""
        # Настраиваем тихий логгер для тестов
        logger = logging.getLogger("TestLogger")
        logger.setLevel(logging.ERROR)  # Минимизируем вывод во время тестов
        
        # Создаем экземпляр класса для тестирования
        self.fetcher = AdvancedEmailFetcherV2(logger)
    
    def test_specific_excluded_files(self):
        """Проверка списка специально исключаемых файлов"""
        # Проверяем наличие атрибута
        self.assertTrue(hasattr(self.fetcher, 'specific_excluded_files'), 
                       "Атрибут specific_excluded_files отсутствует")
        
        # Проверяем содержимое списка
        specific_files = self.fetcher.specific_excluded_files
        
        # Файлы, которые должны быть исключены
        must_exclude = ["_.jpg", "blocked.gif", "WRD0004.jpg", "image001.png"]
        
        for filename in must_exclude:
            self.assertIn(filename, specific_files, 
                         f"Файл {filename} должен быть в списке исключений")
    
    def test_gif_extension_excluded(self):
        """Проверка исключения GIF файлов"""
        self.assertIn('.gif', EXCLUDED_EXTENSIONS, 
                     "Расширение .gif должно быть в списке исключенных")
    
    def test_specific_file_filtering(self):
        """Проверка фильтрации конкретных файлов"""
        # Набор тестовых файлов и ожидаемых результатов (True = должен быть исключен)
        test_cases = [
            ("_.jpg", True),       # Одиночный символ - исключить
            ("blocked.gif", True), # GIF файл - исключить по расширению и имени
            ("important.pdf", False), # Нормальный документ - не исключать
            ("image001.png", True), # Мусорное изображение - исключить
            ("contract.docx", False) # Рабочий документ - не исключать
        ]
        
        for filename, should_exclude in test_cases:
            # Прямая проверка через список исключений
            is_in_specific = filename in self.fetcher.specific_excluded_files
            
            # Проверка через расширение
            ext = Path(filename).suffix.lower()
            is_ext_excluded = ext in EXCLUDED_EXTENSIONS
            
            # Комбинированный результат
            is_excluded = is_in_specific or is_ext_excluded
            
            self.assertEqual(is_excluded, should_exclude, 
                           f"Файл {filename}: ожидаем исключение={should_exclude}, получено={is_excluded}")

if __name__ == "__main__":
    unittest.main()
