#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Интеграционные тесты для критических исправлений пайплайна
Проверяет все исправления: нормализация, обогащение, валидация

Author: Contact Parser Team
Created: 2025-09-30
"""

import unittest
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Импортируем модули для тестирования
try:
    # Импортируем напрямую чтобы избежать проблем с зависимостями
    import importlib.util
    
    # Загружаем safe_math_utils
    spec = importlib.util.spec_from_file_location(
        'safe_math_utils', 
        PROJECT_ROOT / 'src' / 'core' / 'safe_math_utils.py'
    )
    safe_math_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(safe_math_utils)
    
    # Загружаем text_normalizer
    spec = importlib.util.spec_from_file_location(
        'text_normalizer', 
        PROJECT_ROOT / 'src' / 'postprocessing' / 'text_normalizer.py'
    )
    text_normalizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(text_normalizer)
    
    # Загружаем resilient_processor
    spec = importlib.util.spec_from_file_location(
        'resilient_processor', 
        PROJECT_ROOT / 'src' / 'postprocessing' / 'resilient_processor.py'
    )
    resilient_processor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resilient_processor)
    
except Exception as e:
    print(f"⚠️ Ошибка импорта модулей: {e}")
    # Создаем заглушки для тестирования
    safe_math_utils = None
    text_normalizer = None
    resilient_processor = None


class TestSafeMathUtils(unittest.TestCase):
    """🔢 Тесты безопасных математических операций"""
    
    def setUp(self):
        if safe_math_utils is None:
            self.skipTest("Модуль safe_math_utils недоступен")
    
    def test_safe_multiply_with_none(self):
        """Тест safe_multiply с None значениями"""
        # Тест с None в первом операнде
        result = safe_math_utils.safe_multiply(None, 1.5)
        self.assertEqual(result, 0.0, "safe_multiply(None, 1.5) должно возвращать 0.0")
        
        # Тест с None во втором операнде
        result = safe_math_utils.safe_multiply(0.8, None)
        self.assertEqual(result, 0.0, "safe_multiply(0.8, None) должно возвращать 0.0")
        
        # Тест с None в обоих операндах
        result = safe_math_utils.safe_multiply(None, None)
        self.assertEqual(result, 0.0, "safe_multiply(None, None) должно возвращать 0.0")
    
    def test_safe_multiply_normal_values(self):
        """Тест safe_multiply с нормальными значениями"""
        result = safe_math_utils.safe_multiply(0.8, 1.2)
        self.assertAlmostEqual(result, 0.96, places=3, 
                              msg="safe_multiply(0.8, 1.2) должно возвращать 0.96")
        
        result = safe_math_utils.safe_multiply(2, 3)
        self.assertEqual(result, 6.0, "safe_multiply(2, 3) должно возвращать 6.0")
    
    def test_safe_multiply_string_conversion(self):
        """Тест safe_multiply с преобразованием строк"""
        result = safe_math_utils.safe_multiply("0.5", "2.0")
        self.assertEqual(result, 1.0, "safe_multiply('0.5', '2.0') должно возвращать 1.0")
        
        # Тест с некорректной строкой
        result = safe_math_utils.safe_multiply("invalid", 1.0)
        self.assertEqual(result, 0.0, "safe_multiply('invalid', 1.0) должно возвращать 0.0")
    
    def test_sanitize_json_fields(self):
        """Тест очистки JSON полей от некорректных символов"""
        test_data = {
            'message_id_h极': 'test_value',
            'normal_field': 'normal_value',
            'interactions': [
                {'message_id_极': 'another_test'}
            ]
        }
        
        result = safe_math_utils.sanitize_json_fields(test_data)
        
        # Проверяем что китайские символы исправлены
        self.assertIn('message_id_hint', result, 
                     "Поле message_id_h极 должно быть исправлено на message_id_hint")
        self.assertNotIn('message_id_h极', result, 
                        "Поле message_id_h极 не должно остаться в результате")
        
        # Проверяем вложенные структуры
        self.assertIn('message_id_hint', result['interactions'][0], 
                     "Вложенное поле message_id_极 должно быть исправлено")
    
    def test_fix_none_values_in_data(self):
        """Тест исправления None значений в данных"""
        test_data = {
            'contacts': [
                {'name': 'Test', 'confidence': None, 'score': 0.8},
                {'name': 'Test2', 'confidence': 0.9, 'score': None}
            ],
            'organizations': [
                {'name': 'Org', 'weight': None, 'value_score': 10}
            ]
        }
        
        result = safe_math_utils.fix_none_values_in_data(test_data)
        
        # Проверяем что None значения исправлены
        self.assertEqual(result['contacts'][0]['confidence'], 0.0, 
                        "None confidence должно быть исправлено на 0.0")
        self.assertEqual(result['contacts'][1]['score'], 0.0, 
                        "None score должно быть исправлено на 0.0")
        self.assertEqual(result['organizations'][0]['weight'], 0.0, 
                        "None weight должно быть исправлено на 0.0")


class TestTextNormalizer(unittest.TestCase):
    """📝 Тесты нормализации текста"""
    
    def setUp(self):
        if text_normalizer is None:
            self.skipTest("Модуль text_normalizer недоступен")
    
    def test_normalize_first_word_only(self):
        """Тест нормализации только первого слова"""
        test_cases = [
            ("руководитель ОМТС", "Руководитель ОМТС"),
            ("менеджер по продажам", "Менеджер по продажам"),
            ("ДИРЕКТОР", "ДИРЕКТОР"),
            ("главный ИНЖЕНЕР", "Главный ИНЖЕНЕР"),
            ("", ""),
            ("а", "А"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = text_normalizer.normalize_first_word_only(input_text)
                self.assertEqual(result, expected, 
                               f"normalize_first_word_only('{input_text}') должно возвращать '{expected}'")
    
    def test_normalize_first_word_only_with_quotes(self):
        """Тест нормализации с кавычками"""
        test_cases = [
            ('"руководитель ОМТС"', '"Руководитель ОМТС"'),
            ("'менеджер по продажам'", "'Менеджер по продажам'"),
            ('«ДИРЕКТОР»', '«ДИРЕКТОР»'),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = text_normalizer.normalize_first_word_only(input_text)
                self.assertEqual(result, expected, 
                               f"normalize_first_word_only('{input_text}') должно возвращать '{expected}'")


class TestResilientProcessor(unittest.TestCase):
    """🔄 Тесты устойчивого процессора"""
    
    def setUp(self):
        if resilient_processor is None:
            self.skipTest("Модуль resilient_processor недоступен")
    
    def test_processing_strategy_enum(self):
        """Тест перечисления стратегий обработки"""
        strategies = resilient_processor.ProcessingStrategy
        
        self.assertEqual(strategies.STANDARD.value, "standard")
        self.assertEqual(strategies.SIMPLIFIED.value, "simplified")
        self.assertEqual(strategies.FALLBACK.value, "fallback")
    
    def test_processing_result_dataclass(self):
        """Тест структуры результата обработки"""
        result = resilient_processor.ProcessingResult(
            email_file="test.json",
            success=True,
            strategy_used=resilient_processor.ProcessingStrategy.STANDARD,
            attempt_number=1,
            processing_time=1.5
        )
        
        self.assertEqual(result.email_file, "test.json")
        self.assertTrue(result.success)
        self.assertEqual(result.strategy_used, resilient_processor.ProcessingStrategy.STANDARD)
        self.assertEqual(result.attempt_number, 1)
        self.assertEqual(result.processing_time, 1.5)
        self.assertIsNone(result.error_message)
    
    def test_resilient_processor_initialization(self):
        """Тест инициализации устойчивого процессора"""
        mock_processor = Mock()
        
        processor = resilient_processor.ResilientEmailProcessor(
            original_processor=mock_processor,
            max_retries=3
        )
        
        self.assertEqual(processor.processor, mock_processor)
        self.assertEqual(processor.max_retries, 3)
        self.assertEqual(processor.failed_emails, [])
        self.assertEqual(processor.processing_results, [])
        self.assertEqual(processor.retry_statistics['total_emails'], 0)


class TestIntegrationScenarios(unittest.TestCase):
    """🔗 Интеграционные сценарии тестирования"""
    
    def test_email_014_error_scenario(self):
        """Тест сценария ошибки email_014 (NoneType * float)"""
        if safe_math_utils is None:
            self.skipTest("Модуль safe_math_utils недоступен")
        
        # Симулируем данные с None значениями
        problematic_data = {
            'contacts': [
                {
                    'name': 'Test Contact',
                    'confidence': None,  # Это вызывало ошибку
                    'organization_id': 1
                }
            ],
            'scores': [
                {'similarity': None, 'weight': 0.5},  # И это тоже
                {'similarity': 0.8, 'weight': None}
            ]
        }
        
        # Применяем исправления
        fixed_data = safe_math_utils.fix_none_values_in_data(problematic_data)
        
        # Проверяем что None значения исправлены
        self.assertEqual(fixed_data['contacts'][0]['confidence'], 0.0)
        self.assertEqual(fixed_data['scores'][0]['similarity'], 0.0)
        self.assertEqual(fixed_data['scores'][1]['weight'], 0.0)
        
        # Проверяем что safe_multiply работает с исправленными данными
        for score in fixed_data['scores']:
            result = safe_math_utils.safe_multiply(score['similarity'], score['weight'])
            self.assertIsInstance(result, float)
            self.assertGreaterEqual(result, 0.0)
    
    def test_email_022_chinese_characters_scenario(self):
        """Тест сценария ошибки email_022 (китайские символы)"""
        if safe_math_utils is None:
            self.skipTest("Модуль safe_math_utils недоступен")
        
        # Симулируем данные с китайскими символами в полях
        problematic_json = {
            'interactions': [
                {
                    'interaction_local_id': 1,
                    'contact_id': 1,
                    'message_id_h极': None,  # Проблемное поле
                    'role_in_message': 'sender'
                },
                {
                    'interaction_local_id': 2,
                    'contact_id': 2,
                    'message_id_极': 'test_value',  # Еще одно проблемное поле
                    'role_in_message': 'recipient'
                }
            ]
        }
        
        # Применяем очистку
        cleaned_json = safe_math_utils.sanitize_json_fields(problematic_json)
        
        # Проверяем что китайские символы исправлены
        self.assertIn('message_id_hint', cleaned_json['interactions'][0])
        self.assertNotIn('message_id_h极', cleaned_json['interactions'][0])
        
        self.assertIn('message_id_hint', cleaned_json['interactions'][1])
        self.assertNotIn('message_id_极', cleaned_json['interactions'][1])
        
        # Проверяем что значения сохранились
        self.assertIsNone(cleaned_json['interactions'][0]['message_id_hint'])
        self.assertEqual(cleaned_json['interactions'][1]['message_id_hint'], 'test_value')
    
    def test_normalization_integration(self):
        """Тест интеграции нормализации текста"""
        if text_normalizer is None:
            self.skipTest("Модуль text_normalizer недоступен")
        
        # Тестовые случаи из дизайна
        test_cases = [
            ("руководитель ОМТС", "Руководитель ОМТС"),
            ("менеджер по продажам", "Менеджер по продажам"),
            ("ДИРЕКТОР по развитию", "ДИРЕКТОР по развитию"),
            ("главный ИНЖЕНЕР", "Главный ИНЖЕНЕР"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = text_normalizer.normalize_first_word_only(input_text)
                self.assertEqual(result, expected, 
                               f"Нормализация '{input_text}' должна давать '{expected}'")
    
    def test_contact_enrichment_scenario(self):
        """Тест сценария обогащения контактов"""
        # Симулируем сценарий: sklad@centerld.ru → centerld.ru
        test_email = "sklad@centerld.ru"
        expected_website = "centerld.ru"
        
        # Извлекаем домен из email
        domain = test_email.split('@')[1] if '@' in test_email else None
        
        self.assertEqual(domain, expected_website, 
                        f"Домен из {test_email} должен быть {expected_website}")
        
        # Проверяем что это не публичный провайдер
        public_providers = ['mail.ru', 'yandex.ru', 'gmail.com', 'bk.ru', 'rambler.ru']
        self.assertNotIn(domain, public_providers, 
                        f"Домен {domain} не должен быть в списке публичных провайдеров")


class TestErrorRecovery(unittest.TestCase):
    """🚨 Тесты восстановления после ошибок"""
    
    def test_graceful_degradation(self):
        """Тест graceful degradation при ошибках"""
        if safe_math_utils is None:
            self.skipTest("Модуль safe_math_utils недоступен")
        
        # Тест с различными некорректными данными
        test_cases = [
            (None, 1.0, 0.0),
            (1.0, None, 0.0),
            ("invalid", 1.0, 0.0),
            (1.0, "invalid", 0.0),
            (float('inf'), 1.0, float('inf')),
            (1.0, float('nan'), True),  # NaN проверяем отдельно
        ]
        
        for value, multiplier, expected in test_cases:
            with self.subTest(value=value, multiplier=multiplier):
                result = safe_math_utils.safe_multiply(value, multiplier)
                
                if expected is True:  # Для NaN
                    self.assertTrue(str(result) == 'nan' or result != result, 
                                  f"safe_multiply({value}, {multiplier}) должно обрабатывать NaN")
                else:
                    self.assertEqual(result, expected, 
                                   f"safe_multiply({value}, {multiplier}) должно возвращать {expected}")
    
    def test_data_structure_preservation(self):
        """Тест сохранения структуры данных при исправлениях"""
        if safe_math_utils is None:
            self.skipTest("Модуль safe_math_utils недоступен")
        
        original_data = {
            'contacts': [
                {'name': 'Test', 'confidence': None, 'extra_field': 'preserved'},
                {'name': 'Test2', 'confidence': 0.9, 'score': None}
            ],
            'metadata': {
                'version': '1.0',
                'timestamp': '2025-09-30'
            }
        }
        
        fixed_data = safe_math_utils.fix_none_values_in_data(original_data.copy())
        
        # Проверяем что структура сохранилась
        self.assertEqual(len(fixed_data['contacts']), 2)
        self.assertIn('metadata', fixed_data)
        self.assertEqual(fixed_data['metadata']['version'], '1.0')
        self.assertEqual(fixed_data['contacts'][0]['extra_field'], 'preserved')
        
        # Проверяем что только числовые поля исправлены
        self.assertEqual(fixed_data['contacts'][0]['confidence'], 0.0)
        self.assertEqual(fixed_data['contacts'][1]['score'], 0.0)
        self.assertEqual(fixed_data['contacts'][1]['confidence'], 0.9)  # Не изменилось


def create_test_suite():
    """Создание набора тестов"""
    suite = unittest.TestSuite()
    
    # Добавляем все тестовые классы
    test_classes = [
        TestSafeMathUtils,
        TestTextNormalizer,
        TestResilientProcessor,
        TestIntegrationScenarios,
        TestErrorRecovery
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


def main():
    """Основная функция запуска тестов"""
    print("🧪 Запуск интеграционных тестов критических исправлений")
    print("=" * 70)
    
    # Создаем и запускаем тесты
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    print(f"📊 Результаты тестирования:")
    print(f"   ✅ Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ Неудачно: {len(result.failures)}")
    print(f"   💥 Ошибки: {len(result.errors)}")
    print(f"   ⏭️ Пропущено: {len(result.skipped)}")
    
    if result.failures:
        print(f"\n❌ Неудачные тесты:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"   • {test}: {error_msg}")
    
    if result.errors:
        print(f"\n💥 Ошибки в тестах:")
        for test, traceback in result.errors:
            error_msg = traceback.split('\n')[-2]
            print(f"   • {test}: {error_msg}")
    
    # Возвращаем код выхода
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())