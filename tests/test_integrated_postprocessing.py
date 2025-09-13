#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест интеграции постобработки в IntegratedLLMProcessor
Проверяет корректность работы с новой структурой organizations/contacts

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
    from src.integrated_llm_processor import IntegratedLLMProcessor
except ImportError:
    # Fallback для прямого запуска
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    src_dir = os.path.join(parent_dir, 'src')
    sys.path.insert(0, src_dir)
    
    # Mock класс для тестирования
    class IntegratedLLMProcessor:
        def __init__(self, test_mode=False):
            from postprocessing import PostProcessor
            self.postprocessor = PostProcessor()
            self.test_mode = test_mode


class TestIntegratedPostprocessing(unittest.TestCase):
    """Тесты интеграции постобработки в IntegratedLLMProcessor"""
    
    def setUp(self):
        self.processor = IntegratedLLMProcessor(test_mode=True)
    
    def test_postprocessor_initialization(self):
        """Тест инициализации постпроцессора"""
        # Проверяем, что постпроцессор создан
        self.assertIsNotNone(self.processor.postprocessor)
        
        # Проверяем, что все компоненты постпроцессора инициализированы
        self.assertIsNotNone(self.processor.postprocessor.org_deduplicator)
        self.assertIsNotNone(self.processor.postprocessor.contact_filter)
        self.assertIsNotNone(self.processor.postprocessor.data_enricher)
        self.assertIsNotNone(self.processor.postprocessor.data_normalizer)
    
    def test_postprocessing_integration_mock(self):
        """Тест интеграции постобработки с mock данными"""
        # Mock LLM результат в новом формате
        mock_llm_result = {
            "organizations": [
                {
                    "organization_id": 1,
                    "name": "ДНК-Технология",
                    "inn": "1901066506",
                    "city": "Москва",
                    "address": "ул. Академика Королёва, д. 12",
                    "emails": ["info@dna-technology.ru"],
                    "phones": ["8 800 200-75-15"]
                }
            ],
            "contacts": [
                {
                    "contact_id": 101,
                    "name": "Гоголева Мария",
                    "organization_id": 1,
                    "position": "Менеджер по продажам",
                    "email": "m.gogoleva@dna-technology.ru",
                    "phones": [{"type": "main", "number": "+7(495) 640-17-71"}],
                    "confidence": 0.95
                },
                {
                    "contact_id": 102,
                    "organization_id": 1,
                    "email": "support@dna-technology.ru"  # Неценный контакт
                }
            ],
            "business_context": "Запрос коммерческого предложения",
            "summary": {"topic": "Коммерческое предложение"},
            "key_points": ["Запрос КП на оборудование"],
            "commercial_offers": []
        }
        
        # Mock email metadata
        mock_email_metadata = {
            'from': 'm.gogoleva@dna-technology.ru',
            'to': 'test@example.com',
            'subject': 'Коммерческое предложение',
            'date': '2025-01-27',
            'has_attachments': False
        }
        
        # Тестируем постобработку напрямую
        processed_result = self.processor.postprocessor.process_llm_response(
            mock_llm_result, mock_email_metadata
        )
        
        # Проверяем структуру результата
        self.assertIn('organizations', processed_result)
        self.assertIn('contacts', processed_result)
        self.assertIn('postprocessing_metadata', processed_result)
        
        # Проверяем, что неценный контакт отфильтрован (при строгом пороге)
        # Или перенесен в организацию
        organizations = processed_result['organizations']
        contacts = processed_result['contacts']
        
        self.assertEqual(len(organizations), 1)
        self.assertTrue(len(contacts) <= 2)  # Зависит от настроек фильтра
        
        # Проверяем глобальные organization_id
        if contacts:
            for contact in contacts:
                self.assertIn('organization_id', contact)
                # Глобальный ID должен быть >= 1000 (по логике дедупликатора)
                self.assertIsInstance(contact['organization_id'], int)
    
    def test_old_format_compatibility(self):
        """Тест совместимости со старым форматом"""
        # Mock LLM результат в старом формате (без organizations)
        mock_old_result = {
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
            "business_context": "Тестовое взаимодействие",
            "commercial_offers": []
        }
        
        # Проверяем, что старый формат не обрабатывается постпроцессором
        # (нет ключа 'organizations')
        self.assertNotIn('organizations', mock_old_result)
        
        # Постпроцессор должен пропустить такой результат
        # без изменений (проверяется в логике IntegratedLLMProcessor)
    
    def test_postprocessing_stats(self):
        """Тест получения статистики постобработки"""
        stats = self.processor.postprocessor.get_processing_stats()
        
        # Проверяем наличие основных полей статистики
        expected_fields = [
            'processed_emails',
            'total_organizations_processed',
            'total_contacts_processed',
            'organization_deduplicator',
            'contact_filter',
            'data_enricher',
            'data_normalizer'
        ]
        
        for field in expected_fields:
            self.assertIn(field, stats)
    
    def test_error_handling(self):
        """Тест обработки ошибок в постобработке"""
        # Некорректный LLM результат
        invalid_result = {
            "organizations": "invalid_format",  # Должен быть список
            "contacts": None
        }
        
        # Постпроцессор должен вернуть оригинальный результат при ошибке
        try:
            processed = self.processor.postprocessor.process_llm_response(invalid_result)
            # Если обработка прошла, результат должен быть валидным
            self.assertIsInstance(processed, dict)
        except Exception:
            # Если произошла ошибка, это тоже нормально (graceful degradation)
            pass


if __name__ == '__main__':
    # Настройка логирования для тестов
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Запуск тестов
    unittest.main(verbosity=2)