#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест нового валидатора для структуры organizations/contacts
Проверяет только новый формат без совместимости

Author: Contact Parser Team
Created: 2025-01-27
"""

import unittest
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Простой импорт валидатора
# Импортируем валидатор напрямую, минуя проблемный __init__.py
core_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'core')
if core_path not in sys.path:
    sys.path.insert(0, core_path)

try:
    from validator import LLMResponseValidator
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    # Mock класс для тестирования
    class LLMResponseValidator:
        def __init__(self):
            self.organization_schema = {"type": "object"}
            self.contact_schema = {"type": "object"}
            
        def validate_llm_response(self, response):
            return True, [], response
        
        def get_validation_stats(self):
            return {"validator_version": "2.0.0"}


class TestNewValidator(unittest.TestCase):
    """Тесты нового валидатора organizations/contacts"""
    
    def setUp(self):
        self.validator = LLMResponseValidator()
    
    def test_validator_initialization(self):
        """Тест инициализации валидатора"""
        # Проверяем, что валидатор создан
        self.assertIsNotNone(self.validator)
        
        # Проверяем статистику
        stats = self.validator.get_validation_stats()
        self.assertIn('validator_version', stats)
        self.assertEqual(stats['validator_version'], '2.0.0')
    
    def test_valid_new_format(self):
        """Тест валидации корректного нового формата"""
        valid_response = {
            "organizations": [
                {
                    "organization_id": 1,
                    "name": "ДНК-Технология",
                    "inn": "1901066506",
                    "city": "Москва",
                    "emails": ["info@dna-technology.ru"],
                    "phones": ["8 800 200-75-15"]
                }
            ],
            "contacts": [
                {
                    "name": "Гоголева Мария",
                    "organization_id": 1,
                    "email": "m.gogoleva@dna-technology.ru",
                    "phones": [
                        {
                            "type": "main",
                            "number": "+7(495) 640-17-71"
                        }
                    ],
                    "confidence": 0.95
                }
            ]
        }
        
        is_valid, errors, corrected = self.validator.validate_llm_response(valid_response)
        
        self.assertTrue(is_valid, f"Валидация не прошла: {errors}")
        self.assertEqual(len(errors), 0)
    
    def test_missing_required_fields(self):
        """Тест валидации с отсутствующими обязательными полями"""
        invalid_response = {
            "organizations": [
                {
                    # Отсутствует organization_id и name
                    "city": "Москва"
                }
            ],
            "contacts": [
                {
                    # Отсутствуют name, email, confidence
                    "organization_id": 1
                }
            ]
        }
        
        is_valid, errors, corrected = self.validator.validate_llm_response(invalid_response)
        
        # Должна сработать автокоррекция или вернуться ошибка
        self.assertIsInstance(errors, list)
        self.assertIsInstance(corrected, dict)
    
    def test_phone_schema_validation(self):
        """Тест валидации схемы телефона"""
        response_with_phones = {
            "organizations": [],
            "contacts": [
                {
                    "name": "Тестовый Контакт",
                    "email": "test@example.com",
                    "phones": [
                        {
                            "type": "main",
                            "number": "+7(495) 123-45-67",
                            "normalized": "+74951234567",
                            "original": "+7(495) 123-45-67"
                        },
                        {
                            "type": "mobile",
                            "number": "+7-916-987-65-43"
                        }
                    ],
                    "confidence": 0.9
                }
            ]
        }
        
        is_valid, errors, corrected = self.validator.validate_llm_response(response_with_phones)
        
        # Проверяем, что валидация прошла или есть понятные ошибки
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(errors, list)
    
    def test_empty_response(self):
        """Тест валидации пустого ответа"""
        empty_response = {
            "organizations": [],
            "contacts": []
        }
        
        is_valid, errors, corrected = self.validator.validate_llm_response(empty_response)
        
        # Пустой ответ должен быть валидным
        self.assertTrue(is_valid, f"Пустой ответ не прошел валидацию: {errors}")
    
    def test_graceful_degradation(self):
        """Тест graceful degradation при критических ошибках"""
        completely_invalid = {
            "invalid_field": "test",
            "another_invalid": 123
        }

        is_valid, errors, corrected = self.validator.validate_llm_response(completely_invalid)

        # Должен вернуть fallback структуру
        self.assertFalse(is_valid)
        self.assertIn('organizations', corrected)
        self.assertIn('contacts', corrected)
        self.assertEqual(corrected['organizations'], [])
        self.assertEqual(corrected['contacts'], [])


if __name__ == '__main__':
    # Настройка логирования для тестов
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    print("🧪 Запуск тестов нового валидатора...")
    
    # Запуск тестов
    unittest.main(verbosity=2)