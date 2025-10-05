#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для UI-форматирования телефонов и санитизации

Author: Contact Parser Team
Created: 2025-10-05
"""

import pytest
from src.postprocessing.data_normalizer import DataNormalizer


class TestPhoneSanitization:
    """Тесты санитизации phone объектов"""
    
    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.normalizer = DataNormalizer()
    
    def test_sanitize_removes_confidence(self):
        """Тест удаления поля confidence из phone объекта"""
        phone = {
            'type': 'mobile',
            'number': '+7 (495) 640-17-71',
            'normalized': '+74956401771',
            'original': '+7 (495) 640-17-71',
            'confidence': 0.95,  # ДОЛЖЕН БЫТЬ УДАЛЕН
        }
        
        result = self.normalizer._sanitize_phone_keys(phone)
        
        assert 'confidence' not in result
        assert 'type' in result
        assert 'number' in result
        assert 'normalized' in result
        assert 'original' in result
    
    def test_sanitize_removes_multiple_fields(self):
        """Тест удаления нескольких лишних полей"""
        phone = {
            'type': 'office',
            'number': '+7 (495) 640-17-71',
            'normalized': '+74956401771',
            'original': '+7 (495) 640-17-71',
            'confidence': 0.95,  # ДОЛЖЕН БЫТЬ УДАЛЕН
            'source': 'llm',     # ДОЛЖЕН БЫТЬ УДАЛЕН
            'metadata': {'foo': 'bar'},  # ДОЛЖЕН БЫТЬ УДАЛЕН
        }
        
        result = self.normalizer._sanitize_phone_keys(phone)
        
        assert 'confidence' not in result
        assert 'source' not in result
        assert 'metadata' not in result
        assert len(result) == 4  # Только whitelist поля
    
    def test_sanitize_preserves_extension(self):
        """Тест сохранения поля extension"""
        phone = {
            'type': 'office',
            'number': '+7 (495) 640-17-71',
            'normalized': '+74956401771',
            'original': '+7 (495) 640-17-71 (доб. 2026)',
            'extension': '2026',
            'confidence': 0.95,  # ДОЛЖЕН БЫТЬ УДАЛЕН
        }
        
        result = self.normalizer._sanitize_phone_keys(phone)
        
        assert 'extension' in result
        assert result['extension'] == '2026'
        assert 'confidence' not in result


class TestUIFormatting:
    """Тесты форматирования UI из E.164"""
    
    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.normalizer = DataNormalizer()
    
    def test_format_ru_number(self):
        """Тест форматирования RU номера в +7 (XXX) XXX-XX-XX"""
        e164 = '+74956401771'
        result = self.normalizer._format_ui_from_e164(e164)
        
        # Проверяем формат +7 (XXX) XXX-XX-XX
        assert result.startswith('+7 (')
        assert ')' in result
        assert result == '+7 (495) 640-17-71'
    
    def test_format_ru_number_different_area_code(self):
        """Тест форматирования RU номера с другим кодом города"""
        e164 = '+73833802104'  # Новосибирск
        result = self.normalizer._format_ui_from_e164(e164)
        
        assert result.startswith('+7 (383)')
        assert ')' in result
    
    def test_format_international_number(self):
        """Тест форматирования международного номера"""
        e164 = '+12025551234'  # US number
        result = self.normalizer._format_ui_from_e164(e164)
        
        # Должен начинаться с +1
        assert result.startswith('+1')
        # Не должен иметь формат RU
        assert '(' not in result or not result.startswith('+7')
    
    def test_format_invalid_number_fallback(self):
        """Тест fallback при невалидном номере"""
        e164 = 'invalid'
        result = self.normalizer._format_ui_from_e164(e164)
        
        # Должен вернуть исходное значение
        assert result == 'invalid'
    
    def test_format_empty_number(self):
        """Тест обработки пустого номера"""
        result = self.normalizer._format_ui_from_e164('')
        assert result == ''
        
        result = self.normalizer._format_ui_from_e164(None)
        assert result == ''


class TestPhoneEntryNormalization:
    """Интеграционные тесты нормализации phone entry"""
    
    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.normalizer = DataNormalizer()
    
    def test_llm_phone_object_sanitization(self):
        """Тест санитизации LLM phone объекта"""
        llm_phone = {
            'type': 'office',
            'number': '+7 495 640-17-71',
            'normalized': '+74956401771',
            'original': '+7 (495) 640-17-71',
            'confidence': 0.95,  # ДОЛЖЕН БЫТЬ УДАЛЕН
            'source': 'llm',     # ДОЛЖЕН БЫТЬ УДАЛЕН
        }
        
        results = self.normalizer._normalize_phone_entry(llm_phone)
        
        assert len(results) == 1
        result = results[0]
        
        # Проверяем санитизацию
        assert 'confidence' not in result
        assert 'source' not in result
        
        # Проверяем whitelist поля
        assert 'type' in result
        assert 'number' in result
        assert 'normalized' in result
        assert 'original' in result
        assert 'extension' in result
    
    def test_llm_phone_object_ui_regeneration(self):
        """Тест регенерации UI-формата для LLM phone объекта"""
        llm_phone = {
            'type': 'office',
            'number': 'old format',  # Будет перезаписан
            'normalized': '+74956401771',
            'original': '+7 (495) 640-17-71',
        }
        
        results = self.normalizer._normalize_phone_entry(llm_phone)
        
        assert len(results) == 1
        result = results[0]
        
        # Проверяем, что number регенерирован из normalized
        assert result['number'] == '+7 (495) 640-17-71'
        assert result['number'] != 'old format'
    
    def test_string_phone_normalization(self):
        """Тест нормализации строкового телефона"""
        phone_str = '+7 (495) 640-17-71'
        
        results = self.normalizer._normalize_phone_entry(phone_str)
        
        assert len(results) >= 1
        result = results[0]
        
        # Проверяем наличие всех обязательных полей
        assert 'type' in result
        assert 'number' in result
        assert 'normalized' in result
        assert 'original' in result
        
        # Проверяем санитизацию (не должно быть лишних полей)
        allowed_keys = {'type', 'number', 'normalized', 'original', 'extension'}
        assert set(result.keys()).issubset(allowed_keys)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
