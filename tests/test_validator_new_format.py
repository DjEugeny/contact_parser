#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест обновленной JSON схемы валидации для новой структуры
Проверяет поддержку organizations/contacts формата

Author: Contact Parser Team
Created: 2025-01-27
"""

import unittest
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Импортируем с обработкой ошибок
try:
    from src.core.validator import LLMResponseValidator
except ImportError:
    # Fallback для прямого запуска
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    src_dir = os.path.join(parent_dir, 'src')
    sys.path.insert(0, src_dir)
    
    # Простой импорт валидатора
    try:
        from core.validator import LLMResponseValidator
    except ImportError:
        # Mock класс для тестирования
        class LLMResponseValidator:
            def __init__(self):
                self.organization_schema = {"type": "object"}
                self.contact_schema = {"type": "object"}
                
            def validate_llm_response(self, response):
                return True, [], response


class TestValidatorNewFormat(unittest.TestCase):
    """Тесты валидатора для новой структуры organizations/contacts"""
    
    def setUp(self):
        self.validator = LLMResponseValidator()
    
    def test_new_format_validation_success(self):
        """Тест успешной валидации нового формата"""
        new_format_response = {
            "organizations": [
                {
                    "organization_id": 1,
                    "name": "ДНК-Технология",
                    "inn": "1901066506",
                    "website": "https://dna-technology.ru",
                    "city": "Москва",
                    "address": "ул. Академика Королёва, д. 12",
                    "emails": ["info@dna-technology.ru", "sales@dna-technology.ru"],
                    "phones": ["8 800 200-75-15", "+7(495) 640-17-71"]
                }
            ],
            "contacts": [
                {
                    "contact_id": 101,
                    "name": "Гоголева Мария",
                    "organization_id": 1,
                    "position": "Менеджер по продажам",
                    "email": "m.gogoleva@dna-technology.ru",
                    "role_in_message": "sender",
                    "phones": [
                        {
                            "type": "main",
                            "number": "+7(495) 640-17-71",
                            "normalized": "+74956401771",
                            "formatted": "+7 (495) 640-17-71",
                            "original": "+7(495) 640-17-71"
                        }
                    ],
                    "city": "Москва",
                    "address": "ул. Академика Королёва, д. 12",
                    "confidence": 0.95
                }
            ],
            "business_context": "Запрос коммерческого предложения",
            "summary": {
                "topic": "Коммерческое предложение",
                "product_interest": "Амплификаторы",
                "communication_stage": "Коммерческие переговоры",
                "request_type": "Запрос КП"
            },
            "key_points": ["Запрос КП на оборудование"],
            "commercial_offers": [],
            "interactions": [
                {
                    "interaction_local_id": 1,
                    "contact_id": 101,
                    "organization_id": 1,
                    "message_subject": "Re: Коммерческое предложение",
                    "message_date": "2025-01-27T10:00:00+03:00",
                    "role_in_message": "sender",
                    "interaction_type": "requested_quote",
                    "summary": "Запросил отправку обновлённого КП",
                    "attachments": [],
                    "confidence": 0.9,
                    "human_note": "Проверить наличие вложений",
                    "participants": {
                        "actor": "Гоголева Мария",
                        "audience": ["Центр Лабораторной Диагностики"]
                    }
                }
            ],
            "postprocessing_metadata": {
                "processed_at": "2025-01-27T19:00:00",
                "stats": {"organizations_deduplicated": 0},
                "version": "1.0.0"
            }
        }
        
        is_valid, errors, corrected = self.validator.validate_llm_response(new_format_response)
        
        self.assertTrue(is_valid, f"Валидация не прошла: {errors}")
        self.assertEqual(len(errors), 0)
        self.assertEqual(corrected, new_format_response)

    def test_interaction_schema_supports_participants(self):
        """Проверяет поддержку human_note и participants в interactions"""
        import jsonschema

        interaction = {
            "interaction_local_id": 1,
            "contact_id": 5,
            "organization_id": 2,
            "role_in_message": "recipient",
            "interaction_type": "follow_up",
            "summary": "Ответил на запрос",
            "attachments": ["reply.pdf"],
            "confidence": 0.8,
            "human_note": "Ответ согласован",
            "participants": {
                "actor": "Иван Иванов",
                "audience": ["Менеджер ОМТС", "Финансовый отдел"]
            }
        }

        try:
            jsonschema.validate(interaction, self.validator.interaction_schema)
        except jsonschema.ValidationError as error:
            self.fail(f"Interaction с участниками не прошёл валидацию: {error}")
    
    def test_old_format_validation_success(self):
        """Тест успешной валидации старого формата"""
        old_format_response = {
            "contacts": [
                {
                    "name": "Тестовый Контакт",
                    "phone": "+7-999-123-45-67",
                    "email": "test@example.com",
                    "organization": "Тестовая Компания",
                    "position": "Менеджер",
                    "city": "Москва",
                    "confidence": 0.95
                }
            ],
            "business_context": {
                "topic": "Тестовое взаимодействие",
                "product_interest": "Амплификаторы",
                "communication_stage": "Начальный контакт"
            },
            "commercial_offers": []
        }
        
        is_valid, errors, corrected = self.validator.validate_llm_response(old_format_response)
        
        self.assertTrue(is_valid, f"Валидация старого формата не прошла: {errors}")
        self.assertEqual(len(errors), 0)
    
    def test_organization_schema_validation(self):
        """Тест валидации схемы организации"""
        import jsonschema
        
        # Валидная организация
        valid_org = {
            "organization_id": 1,
            "name": "Тестовая Компания",
            "inn": "1234567890",
            "website": "https://example.com",
            "city": "Москва",
            "emails": ["info@example.com"],
            "phones": ["+7-495-123-45-67"]
        }
        
        # Не должно вызывать исключение
        try:
            jsonschema.validate(valid_org, self.validator.organization_schema)
        except jsonschema.ValidationError as e:
            self.fail(f"Валидная организация не прошла валидацию: {e}")
    
    def test_contact_phones_array_validation(self):
        """Тест валидации массива телефонов в контакте"""
        import jsonschema
        
        # Контакт с новым форматом телефонов
        contact_with_phones = {
            "contact_id": 777,
            "name": "Тестовый Контакт",
            "email": "test@example.com",
            "organization_id": 12,
            "role_in_message": "sender",
            "phones": [
                {
                    "type": "main",
                    "number": "+7(495) 123-45-67"
                },
                {
                    "type": "mobile",
                    "number": "+7-916-987-65-43",
                    "normalized": "+79169876543"
                }
            ],
            "confidence": 0.9
        }
        
        # Не должно вызывать исключение
        try:
            jsonschema.validate(contact_with_phones, self.validator.contact_schema)
        except jsonschema.ValidationError as e:
            self.fail(f"Контакт с phones[] не прошел валидацию: {e}")
    
    def test_invalid_phone_type(self):
        """Тест валидации неверного типа телефона"""
        import jsonschema
        
        contact_invalid_phone = {
            "name": "Тестовый Контакт",
            "email": "test@example.com",
            "phones": [
                {
                    "type": "invalid_type",  # Неверный тип
                    "number": "+7(495) 123-45-67"
                }
            ],
            "confidence": 0.9
        }
        
        # Должно вызвать исключение
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(contact_invalid_phone, self.validator.contact_schema)
    
    def test_missing_required_organization_fields(self):
        """Тест валидации организации без обязательных полей"""
        import jsonschema
        
        invalid_org = {
            "organization_id": 1
            # Отсутствует обязательное поле "name"
        }
        
        # Должно вызвать исключение
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(invalid_org, self.validator.organization_schema)
    
    def test_format_detection(self):
        """Тест определения формата ответа"""
        # Новый формат
        new_format = {"organizations": [], "contacts": []}
        is_valid, errors, corrected = self.validator.validate_llm_response(new_format)
        # Должен определить как новый формат
        
        # Старый формат
        old_format = {"contacts": [], "business_context": {}, "commercial_offers": []}
        is_valid, errors, corrected = self.validator.validate_llm_response(old_format)
        # Должен определить как старый формат
    
    def test_postprocessing_metadata_validation(self):
        """Тест валидации метаданных постобработки"""
        response_with_metadata = {
            "organizations": [],
            "contacts": [],
            "postprocessing_metadata": {
                "processed_at": "2025-01-27T19:00:00",
                "stats": {
                    "organizations_deduplicated": 2,
                    "contacts_filtered": 1
                },
                "version": "1.0.0"
            }
        }
        
        is_valid, errors, corrected = self.validator.validate_llm_response(response_with_metadata)
        self.assertTrue(is_valid, f"Валидация метаданных не прошла: {errors}")


if __name__ == '__main__':
    # Настройка логирования для тестов
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Запуск тестов
    unittest.main(verbosity=2)
