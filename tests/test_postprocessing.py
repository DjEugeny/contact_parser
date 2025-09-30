#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для модуля постобработки данных LLM
Проверяет корректность работы всех компонентов согласно мини-ТЗ

Author: Contact Parser Team
Created: 2025-09-13
"""

import unittest
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from postprocessing import (
    PostProcessor,
    OrganizationDeduplicator,
    ContactFilter,
    DataEnricher,
    DataNormalizer,
    AdvancedContactDeduplicator
)


class TestOrganizationDeduplicator(unittest.TestCase):
    """Тесты дедупликатора организаций"""
    
    def setUp(self):
        self.deduplicator = OrganizationDeduplicator()
    
    def test_duplicate_by_inn(self):
        """Тест дедупликации по ИНН"""
        organizations = [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "inn": "1901066506",
                "emails": ["info@dna-technology.ru"]
            },
            {
                "organization_id": 2,
                "name": "ООО ДНК-Технология",
                "inn": "1901066506",
                "emails": ["sales@dna-technology.ru"]
            }
        ]
        
        mapping = self.deduplicator.process_organizations(organizations)
        
        # Должен быть создан один глобальный ID для обеих организаций
        self.assertEqual(len(set(mapping.values())), 1)
        self.assertEqual(mapping[1], mapping[2])
        
        # Проверяем объединение emails
        global_org = self.deduplicator.get_all_organizations()[0]
        self.assertIn("info@dna-technology.ru", global_org['emails'])
        self.assertIn("sales@dna-technology.ru", global_org['emails'])
    
    def test_duplicate_by_website(self):
        """Тест дедупликации по сайту"""
        organizations = [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "website": "dna-technology.ru"
            },
            {
                "organization_id": 2,
                "name": "DNA Technology",
                "website": "https://dna-technology.ru"
            }
        ]
        
        mapping = self.deduplicator.process_organizations(organizations)
        
        # Должен быть создан один глобальный ID
        self.assertEqual(len(set(mapping.values())), 1)
    
    def test_no_duplicates(self):
        """Тест отсутствия дубликатов"""
        organizations = [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "inn": "1901066506"
            },
            {
                "organization_id": 2,
                "name": "Другая компания",
                "inn": "1234567890"
            }
        ]
        
        mapping = self.deduplicator.process_organizations(organizations)
        
        # Должно быть создано два разных глобальных ID
        self.assertEqual(len(set(mapping.values())), 2)
        self.assertNotEqual(mapping[1], mapping[2])

    def test_preserve_case_in_names(self):
        """Тест сохранения регистра названий при дедупликации"""
        organizations = [
            {
                "organization_id": 1,
                "name": "кдл центр",
                "inn": "1234567890"
            },
            {
                "organization_id": 2,
                "name": "КДЛ Центр Лаборатория",
                "inn": "1234567890"
            }
        ]

        mapping = self.deduplicator.process_organizations(organizations)
        self.assertEqual(mapping[1], mapping[2])

        global_org = self.deduplicator.get_organization_by_id(mapping[1])
        self.assertEqual(global_org['name'], "КДЛ Центр Лаборатория")
        self.assertNotIn('__match_key__', global_org)


class TestContactFilter(unittest.TestCase):
    """Тесты фильтра контактов"""
    
    def setUp(self):
        self.contact_filter = ContactFilter(min_score=5)  # Более строгий порог
    
    def test_evaluate_contact_value(self):
        """Тест функции оценки ценности контакта"""
        # Ценный контакт (score = 3+2+2+2+1 = 10)
        valuable_contact = {
            "name": "Иванов Иван",  # +3
            "organization_id": 1,  # +2
            "position": "Директор",  # +2
            "email": "ivan@company.ru",  # +2
            "city": "Москва"  # +1
        }
        
        score = self.contact_filter.evaluate_contact_value(valuable_contact)
        self.assertEqual(score, 10)
        self.assertTrue(score >= 5)
        
        # Неценный контакт (score = 2 < 4)
        non_valuable_contact = {
            "email": "info@company.ru"  # +2
        }
        
        score = self.contact_filter.evaluate_contact_value(non_valuable_contact)
        self.assertEqual(score, 2)
        self.assertFalse(score >= 5)
    
    def test_phones_scoring(self):
        """Тест оценки телефонов в новом формате"""
        # Контакт с телефонами в новом формате
        contact_with_phones = {
            "name": "Петров Петр",  # +3
            "phones": [
                {"type": "main", "number": "+7(495)123-45-67"}
            ]  # +2
        }
        
        score = self.contact_filter.evaluate_contact_value(contact_with_phones)
        self.assertEqual(score, 5)
        
        # Контакт с пустым массивом телефонов
        contact_empty_phones = {
            "name": "Сидоров Сидор",  # +3
            "phones": []  # +0
        }
        
        score = self.contact_filter.evaluate_contact_value(contact_empty_phones)
        self.assertEqual(score, 3)
    
    def test_filter_valuable_contacts(self):
        """Тест фильтрации ценных контактов"""
        contacts = [
            {
                "name": "Ценный контакт",
                "organization_id": 1,
                "position": "Директор",
                "email": "director@company.ru"
            },
            {
                "organization_id": 1,  # Нужен для переноса в организацию
                "email": "info@company.ru"  # Неценный (2+2=4 балла, но порог можно поднять)
            }
        ]
        
        organizations = {
            1: {
                "organization_id": 1,
                "name": "Тестовая компания",
                "emails": [],
                "phones": []
            }
        }
        
        valuable, updated_orgs = self.contact_filter.filter_valuable_contacts(
            contacts, organizations
        )
        
        # Должен остаться только один ценный контакт
        self.assertEqual(len(valuable), 1)
        self.assertEqual(valuable[0]['name'], "Ценный контакт")
        
        # Неценный контакт должен быть перенесен в организацию
        self.assertIn("info@company.ru", updated_orgs[1]['emails'])


class TestDataNormalizer(unittest.TestCase):
    """Тесты нормализатора данных"""
    
    def setUp(self):
        self.normalizer = DataNormalizer()
    
    def test_normalize_phones_new_format(self):
        """Тест нормализации телефонов в новом формате"""
        contact = {
            "name": "Тестовый контакт",
            "phones": [
                {"type": "main", "number": "+7 (495) 123-45-67"},
                {"type": "mobile", "number": "8-916-987-65-43"}
            ]
        }
        
        normalized_contacts = self.normalizer.normalize_contacts([contact])
        normalized_contact = normalized_contacts[0]
        
        # Проверяем, что добавлены нормализованные номера
        self.assertIn('normalized', normalized_contact['phones'][0])
        self.assertIn('normalized', normalized_contact['phones'][1])
        
        # Проверяем нормализацию 8 -> +7
        mobile_phone = normalized_contact['phones'][1]
        self.assertTrue(mobile_phone['normalized'].startswith('+7'))
    
    def test_normalize_email(self):
        """Тест нормализации email"""
        contact = {
            "name": "Тестовый контакт",
            "email": "  Test.Email@COMPANY.RU  "
        }
        
        normalized_contacts = self.normalizer.normalize_contacts([contact])
        normalized_contact = normalized_contacts[0]
        
        # Email должен быть приведен к нижнему регистру и обрезан
        self.assertEqual(normalized_contact['email'], "test.email@company.ru")
        self.assertTrue(normalized_contact['email_valid'])
    
    def test_normalize_organizations(self):
        """Тест нормализации организаций"""
        organizations = {
            1: {
                "name": "  ООО \"Тестовая компания\"  ",
                "emails": ["INFO@Company.RU", "  sales@company.ru  "],
                "phones": ["8 800 123-45-67", "+7(495)987-65-43"]
            }
        }
        
        normalized_orgs = self.normalizer.normalize_organizations(organizations)
        normalized_org = normalized_orgs[1]
        
        # Проверяем нормализацию названия
        self.assertEqual(normalized_org['name'], 'ООО "Тестовая компания"')
        
        # Проверяем нормализацию emails
        self.assertIn("info@company.ru", normalized_org['emails'])
        self.assertIn("sales@company.ru", normalized_org['emails'])
        
        # Проверяем нормализацию телефонов
        self.assertIn("+78001234567", normalized_org['phones'])  # Fallback нормализатор сохраняет все цифры


class TestPostProcessor(unittest.TestCase):
    """Тесты главного постпроцессора"""
    
    def setUp(self):
        # Используем более строгий фильтр для тестов
        from postprocessing import ContactFilter
        contact_filter = ContactFilter(min_score=5)
        self.postprocessor = PostProcessor(contact_filter=contact_filter)
    
    def test_full_processing_pipeline(self):
        """Тест полного пайплайна постобработки"""
        llm_result = {
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
                    "position": "Менеджер",
                    "email": "m.gogoleva@dna-technology.ru",
                    "phones": [{"type": "main", "number": "+7(495) 640-17-71"}],
                    "confidence": 0.95
                },
                {
                    "contact_id": 102,
                    "organization_id": 1,  # Нужен для переноса
                    "email": "support@dna-technology.ru"  # Неценный контакт (2+2=4 < 5)
                }
            ],
            "business_context": "Тестовый контекст",
            "summary": {"topic": "Тест"},
            "key_points": ["Тестовый пункт"],
            "commercial_offers": []
        }
        
        processed_result = self.postprocessor.process_llm_response(llm_result)
        
        # Проверяем структуру результата
        self.assertIn('organizations', processed_result)
        self.assertIn('contacts', processed_result)
        self.assertIn('postprocessing_metadata', processed_result)
        
        # Должен остаться только один ценный контакт
        self.assertEqual(len(processed_result['contacts']), 1)
        self.assertEqual(processed_result['contacts'][0]['name'], "Гоголева Мария")
        
        # Неценный контакт должен быть перенесен в организацию
        org = processed_result['organizations'][0]
        self.assertIn("support@dna-technology.ru", org['emails'])
        
        # Проверяем обогащение полей city/address
        contact = processed_result['contacts'][0]
        self.assertEqual(contact['city'], "Москва")
        self.assertEqual(contact['address'], "ул. Академика Королёва, д. 12")
    
    def test_invalid_llm_result(self):
        """Тест обработки некорректного LLM результата"""
        invalid_result = {
            "invalid_field": "test"
        }
        
        # Должен вернуть оригинальный результат при ошибке
        processed_result = self.postprocessor.process_llm_response(invalid_result)
        self.assertEqual(processed_result, invalid_result)
    
    def test_processing_stats(self):
        """Тест статистики обработки"""
        stats = self.postprocessor.get_processing_stats()
        
        # Проверяем наличие основных полей статистики
        self.assertIn('processed_emails', stats)
        self.assertIn('total_organizations_processed', stats)
        self.assertIn('total_contacts_processed', stats)
        self.assertIn('organization_deduplicator', stats)
        self.assertIn('contact_filter', stats)


class TestAdvancedContactDeduplicator(unittest.TestCase):
    """Тесты продвинутого дедупликатора контактов"""
    
    def setUp(self):
        self.deduplicator = AdvancedContactDeduplicator()
    
    def test_deduplicate_by_phone_new_format(self):
        """Тест дедупликации по телефону в новом формате"""
        contacts = [
            {
                "name": "Иванов Иван",
                "phones": [{"type": "main", "number": "+7(495)123-45-67"}]
            },
            {
                "name": "И. Иванов",
                "phones": [{"type": "office", "number": "8 (495) 123-45-67"}]
            }
        ]
        
        deduplicated = self.deduplicator.deduplicate_contacts(contacts)
        
        # Должен остаться один контакт
        self.assertEqual(len(deduplicated), 1)
        
        # Проверяем объединение данных
        merged_contact = deduplicated[0]
        self.assertIn('phones', merged_contact)
        self.assertTrue(len(merged_contact['phones']) >= 1)
    
    def test_deduplicate_by_email(self):
        """Тест дедупликации по email"""
        contacts = [
            {
                "name": "Петров Петр Петрович",
                "email": "p.petrov@company.ru",
                "position": "Директор"
            },
            {
                "name": "П. Петров",
                "email": "p.petrov@company.ru",
                "phones": [{"type": "mobile", "number": "+7-916-123-45-67"}]
            }
        ]
        
        deduplicated = self.deduplicator.deduplicate_contacts(contacts)
        
        # Должен остаться один контакт с объединенными данными
        self.assertEqual(len(deduplicated), 1)
        
        merged_contact = deduplicated[0]
        self.assertEqual(merged_contact['email'], "p.petrov@company.ru")
        self.assertEqual(merged_contact['position'], "Директор")
        self.assertIn('phones', merged_contact)

    def test_preserve_case_after_merge(self):
        """Тест сохранения регистра после объединения контактов"""
        contacts = [
            {
                "contact_id": 1,
                "name": "иванов и.и.",
                "position": "директор по продажам",
                "phones": [
                    {
                        "type": "main",
                        "number": "+7 (495) 123-45-67",
                        "normalized": "+74951234567",
                        "original": "+7 (495) 123-45-67"
                    }
                ]
            },
            {
                "contact_id": 2,
                "name": "Иванов И.И.",
                "position": "Директор По Продажам",
                "phones": [
                    {
                        "type": "main",
                        "number": "+7 (495) 123-45-67",
                        "normalized": "+74951234567",
                        "original": "+7 (495) 123-45-67"
                    }
                ]
            }
        ]

        deduplicated = self.deduplicator.deduplicate_contacts(contacts)
        self.assertEqual(len(deduplicated), 1)

        merged_contact = deduplicated[0]
        self.assertEqual(merged_contact['name'], "Иванов И.И.")
        self.assertEqual(merged_contact['position'], "Директор По Продажам")
        self.assertIn('phones', merged_contact)
        self.assertEqual(merged_contact['phones'][0]['number'], "+7 (495) 123-45-67")


if __name__ == '__main__':
    # Настройка логирования для тестов
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Запуск тестов
    unittest.main(verbosity=2)
