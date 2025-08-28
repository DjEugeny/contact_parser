#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тесты для модуля file_utils
Создано: 2025-01-27 23:30 (UTC+07)
"""

import pytest
import sys
from pathlib import Path

# Добавляем путь к src для импорта
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from file_utils import normalize_filename, get_normalized_filename_variants, find_best_filename_match


class TestNormalizeFilename:
    """Тесты для функции normalize_filename"""
    
    def test_basic_normalization(self):
        """Базовая нормализация имени файла"""
        result = normalize_filename("Test File.pdf")
        assert result == "test_file"
    
    def test_remove_extension_default(self):
        """По умолчанию расширение удаляется"""
        result = normalize_filename("document.docx")
        assert result == "document"
    
    def test_preserve_extension(self):
        """Сохранение расширения при remove_extension=False"""
        result = normalize_filename("document.docx", remove_extension=False)
        assert result == "document.docx"
    
    def test_preserve_case(self):
        """Сохранение регистра при to_lowercase=False"""
        result = normalize_filename("TestFile.pdf", to_lowercase=False)
        assert result == "TestFile"
    
    def test_timestamp_removal(self):
        """Удаление временных меток"""
        # Формат YYYYMMDD_domain_lang_hash_HHMMSS_attach_
        result = normalize_filename("20250127_example_ru_abc123_143000_attach_document.pdf")
        assert result == "document"
        
        # Старый формат _YYYYMMDD_HHMMSS
        result = normalize_filename("document_20250127_143000.pdf")
        assert result == "document"
        
        # Формат _YYYY-MM-DD_HH-MM-SS
        result = normalize_filename("document_2025-01-27_14-30-00.pdf")
        assert result == "document"
    
    def test_method_suffix_removal(self):
        """Удаление суффиксов методов"""
        result = normalize_filename("document___ocr_method.pdf")
        assert result == "document"
        
        result = normalize_filename("file___llm_extraction.txt")
        assert result == "file"
    
    def test_duplicate_suffix_removal(self):
        """Удаление суффиксов дубликатов"""
        result = normalize_filename("document (1).pdf")
        assert result == "document"
        
        result = normalize_filename("file_copy.txt")
        assert result == "file"
        
        result = normalize_filename("data_copy2.xlsx")
        assert result == "data"
        
        result = normalize_filename("backup_duplicate3.doc")
        assert result == "backup"
    
    def test_special_characters(self):
        """Обработка специальных символов"""
        result = normalize_filename("file@#$%^&*()name.pdf")
        assert result == "file_name"
        
        result = normalize_filename("документ-файл.pdf")
        assert result == "документ_файл"
    
    def test_preserve_structure(self):
        """Сохранение структуры при preserve_structure=True"""
        result = normalize_filename("Test-File_Name.pdf", preserve_structure=True)
        assert result == "test-file_name"
    
    def test_cyrillic_support(self):
        """Поддержка кириллицы"""
        result = normalize_filename("Тестовый Файл.pdf")
        assert result == "тестовый_файл"
        
        result = normalize_filename("ДОКУМЕНТ.docx")
        assert result == "документ"
    
    def test_unicode_normalization(self):
        """Нормализация Unicode символов"""
        # Тест с составными символами
        result = normalize_filename("café.pdf")
        assert result == "café"
    
    def test_empty_and_edge_cases(self):
        """Граничные случаи"""
        result = normalize_filename("")
        assert result == ""
        
        result = normalize_filename(".pdf")
        assert result == ""
        
        result = normalize_filename("___test___.pdf")
        assert result == "test"


class TestFilenameVariants:
    """Тесты для функции get_normalized_filename_variants"""
    
    def test_variants_generation(self):
        """Генерация вариантов нормализованных имен"""
        variants = get_normalized_filename_variants("Test File.pdf")
        
        # Проверяем, что есть разные варианты
        assert len(variants) > 1
        assert "test_file" in variants  # Базовый вариант
        
        # Проверяем уникальность
        assert len(variants) == len(set(variants))


class TestBestMatch:
    """Тесты для функции find_best_filename_match"""
    
    def test_exact_match(self):
        """Точное совпадение"""
        candidates = ["document.txt", "file.pdf", "test.docx"]
        result = find_best_filename_match("document.txt", candidates)
        assert result == "document.txt"
    
    def test_normalized_match(self):
        """Совпадение после нормализации"""
        candidates = ["Document File.txt", "other.pdf"]
        result = find_best_filename_match("document_file", candidates)
        assert result == "Document File.txt"
    
    def test_no_match(self):
        """Отсутствие совпадений"""
        candidates = ["file1.txt", "file2.pdf"]
        result = find_best_filename_match("nonexistent", candidates)
        assert result is None
    
    def test_empty_candidates(self):
        """Пустой список кандидатов"""
        result = find_best_filename_match("test", [])
        assert result is None


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])