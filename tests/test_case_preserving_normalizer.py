#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для CasePreservingNormalizer
Проверка сохранения регистра для аббревиатур, названий и должностей

Author: Contact Parser Team
Created: 2025-09-29
"""

import unittest
import sys
from pathlib import Path

# Добавляем путь к src для импорта
sys.path.append(str(Path(__file__).parent.parent / "src"))

from postprocessing.case_preserving_normalizer import (
    CasePreservingNormalizer, 
    NormalizationConfig,
    normalize_preserving_case
)


class TestCasePreservingNormalizer(unittest.TestCase):
    """Тесты для CasePreservingNormalizer"""
    
    def setUp(self):
        """Настройка тестов"""
        self.normalizer = CasePreservingNormalizer()
    
    def test_abbreviation_preservation(self):
        """Тест сохранения аббревиатур"""
        test_cases = [
            # Русские аббревиатуры
            ("кдл", "organization", "КДЛ"),
            ("омтс", "organization", "ОМТС"),
            ("ооо", "organization", "ООО"),
            ("зао", "organization", "ЗАО"),
            ("узи", "position", "УЗИ"),
            ("мрт", "organization", "МРТ"),
            
            # Английские аббревиатуры
            ("llc", "organization", "LLC"),
            ("inc", "organization", "Inc"),
            ("ceo", "position", "CEO"),
            
            # Инициалы
            ("и.и.", "name", "И.И."),
            ("а.с.", "name", "А.С."),
        ]
        
        for input_text, field_type, expected in test_cases:
            with self.subTest(input_text=input_text, field_type=field_type):
                result = self.normalizer.normalize_preserving_case(input_text, field_type)
                self.assertEqual(result, expected, 
                    f"Ожидали '{expected}', получили '{result}' для '{input_text}'")
    
    def test_title_preservation(self):
        """Тест сохранения названий и титулов"""
        test_cases = [
            ("медицина", "organization", "Медицина"),
            ("заведующая", "position", "Заведующая"),
            ("заведующий", "position", "Заведующий"),
            ("директор", "position", "Директор"),
            ("менеджер", "position", "Менеджер"),
            ("руководитель", "position", "Руководитель"),
        ]
        
        for input_text, field_type, expected in test_cases:
            with self.subTest(input_text=input_text, field_type=field_type):
                result = self.normalizer.normalize_preserving_case(input_text, field_type)
                self.assertEqual(result, expected,
                    f"Ожидали '{expected}', получили '{result}' для '{input_text}'")
    
    def test_organization_names(self):
        """Тест нормализации названий организаций"""
        test_cases = [
            ("ооо рога и копыта", "organization", "ООО Рога И Копыта"),
            ("зао медицина", "organization", "ЗАО Медицина"),
            ("кдл центр", "organization", "КДЛ Центр"),
            ("омтс клиника", "organization", "ОМТС Клиника"),
            ("llc medical center", "organization", "LLC Medical Center"),
        ]
        
        for input_text, field_type, expected in test_cases:
            with self.subTest(input_text=input_text, field_type=field_type):
                result = self.normalizer.normalize_preserving_case(input_text, field_type)
                self.assertEqual(result, expected,
                    f"Ожидали '{expected}', получили '{result}' для '{input_text}'")
    
    def test_position_normalization(self):
        """Тест нормализации должностей"""
        test_cases = [
            ("заведующая кдл", "position", "Заведующая КДЛ"),
            ("директор по медицине", "position", "Директор По Медицине"),
            ("главный врач", "position", "Главный Врач"),
            ("менеджер по продажам", "position", "Менеджер По Продажам"),
        ]
        
        for input_text, field_type, expected in test_cases:
            with self.subTest(input_text=input_text, field_type=field_type):
                result = self.normalizer.normalize_preserving_case(input_text, field_type)
                self.assertEqual(result, expected,
                    f"Ожидали '{expected}', получили '{result}' для '{input_text}'")
    
    def test_name_normalization(self):
        """Тест нормализации имен"""
        test_cases = [
            ("иванов и.и.", "name", "Иванов И.И."),
            ("петрова а.с.", "name", "Петрова А.С."),
            ("сидоров петр иванович", "name", "Сидоров Петр Иванович"),
        ]
        
        for input_text, field_type, expected in test_cases:
            with self.subTest(input_text=input_text, field_type=field_type):
                result = self.normalizer.normalize_preserving_case(input_text, field_type)
                self.assertEqual(result, expected,
                    f"Ожидали '{expected}', получили '{result}' для '{input_text}'")
    
    def test_whitespace_normalization(self):
        """Тест нормализации пробелов"""
        test_cases = [
            ("  кдл  ", "organization", "КДЛ"),
            ("ооо   рога   и   копыта", "organization", "ООО Рога И Копыта"),
            ("заведующая    кдл", "position", "Заведующая КДЛ"),
        ]
        
        for input_text, field_type, expected in test_cases:
            with self.subTest(input_text=input_text, field_type=field_type):
                result = self.normalizer.normalize_preserving_case(input_text, field_type)
                self.assertEqual(result, expected,
                    f"Ожидали '{expected}', получили '{result}' для '{input_text}'")
    
    def test_empty_and_none_input(self):
        """Тест обработки пустых значений"""
        test_cases = [
            ("", "organization", ""),
            (None, "position", ""),
            ("   ", "name", ""),
        ]
        
        for input_text, field_type, expected in test_cases:
            with self.subTest(input_text=input_text, field_type=field_type):
                result = self.normalizer.normalize_preserving_case(input_text, field_type)
                self.assertEqual(result, expected,
                    f"Ожидали '{expected}', получили '{result}' для '{input_text}'")
    
    def test_mixed_case_preservation(self):
        """Тест сохранения смешанного регистра"""
        test_cases = [
            ("КДЛ медицина", "organization", "КДЛ Медицина"),
            ("ОМТС центр", "organization", "ОМТС Центр"),
            ("Заведующая КДЛ", "position", "Заведующая КДЛ"),
        ]
        
        for input_text, field_type, expected in test_cases:
            with self.subTest(input_text=input_text, field_type=field_type):
                result = self.normalizer.normalize_preserving_case(input_text, field_type)
                self.assertEqual(result, expected,
                    f"Ожидали '{expected}', получили '{result}' для '{input_text}'")
    
    def test_global_function(self):
        """Тест глобальной функции normalize_preserving_case"""
        result = normalize_preserving_case("кдл", "organization")
        self.assertEqual(result, "КДЛ")
        
        result = normalize_preserving_case("заведующая", "position")
        self.assertEqual(result, "Заведующая")
    
    def test_config_customization(self):
        """Тест кастомизации конфигурации"""
        # Конфигурация без сохранения аббревиатур
        config = NormalizationConfig(preserve_abbreviations=False)
        normalizer = CasePreservingNormalizer(config)
        
        result = normalizer.normalize_preserving_case("кдл", "organization")
        # Без сохранения аббревиатур должно быть "Кдл"
        self.assertEqual(result, "Кдл")
    
    def test_stats(self):
        """Тест получения статистики"""
        stats = self.normalizer.get_stats()
        
        self.assertIn('config', stats)
        self.assertIn('patterns', stats)
        self.assertTrue(stats['config']['preserve_abbreviations'])
        self.assertGreater(stats['patterns']['special_cases_count'], 0)


class TestRealWorldExamples(unittest.TestCase):
    """Тесты на реальных примерах из проблемных писем"""
    
    def setUp(self):
        """Настройка тестов"""
        self.normalizer = CasePreservingNormalizer()
    
    def test_problematic_examples(self):
        """Тест на примерах из проблемных писем"""
        # Примеры из action plan
        test_cases = [
            ("Медицина", "organization", "Медицина"),  # Не должно стать "медицина"
            ("КДЛ", "organization", "КДЛ"),            # Не должно стать "кдл"
            ("ОМТС", "organization", "ОМТС"),          # Не должно стать "омтс"
            ("Заведующая", "position", "Заведующая"),  # Не должно стать "заведующая"
        ]
        
        for input_text, field_type, expected in test_cases:
            with self.subTest(input_text=input_text, field_type=field_type):
                result = self.normalizer.normalize_preserving_case(input_text, field_type)
                self.assertEqual(result, expected,
                    f"КРИТИЧЕСКАЯ ОШИБКА: '{input_text}' стало '{result}' вместо '{expected}'")


if __name__ == '__main__':
    # Запуск тестов
    unittest.main(verbosity=2)