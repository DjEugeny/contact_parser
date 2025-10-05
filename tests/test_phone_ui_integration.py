#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграционные тесты для UI-форматирования телефонов

Author: Contact Parser Team
Created: 2025-10-05
"""

import pytest
import json
from src.postprocessing.postprocessor import PostProcessor


class TestPhoneUIIntegration:
    """Интеграционные тесты phone UI форматирования"""
    
    def setup_method(self):
        """Инициализация перед каждым тестом"""
        self.postprocessor = PostProcessor()
    
    def test_phone_sanitization_in_pipeline(self):
        """Тест санитизации phone объектов в полном пайплайне"""
        # Создаем тестовый LLM результат с лишними полями в phones
        llm_result = {
            'organizations': [
                {
                    'organization_id': 1,
                    'name': 'Тестовая Компания',
                    'inn': '7707083893',
                    'phones': [
                        {
                            'type': 'office',
                            'number': '+7 495 640-17-71',
                            'normalized': '+74956401771',
                            'original': '+7 (495) 640-17-71',
                            'confidence': 0.95,  # ДОЛЖЕН БЫТЬ УДАЛЕН
                            'source': 'llm'      # ДОЛЖЕН БЫТЬ УДАЛЕН
                        }
                    ],
                    'emails': ['info@test.ru'],
                    'city': 'Москва'
                }
            ],
            'contacts': [
                {
                    'contact_id': 1,
                    'name': 'Иванов Иван',
                    'organization_id': 1,
                    'email': 'ivanov@test.ru',
                    'phones': [
                        {
                            'type': 'mobile',
                            'number': '+7 916 123-45-67',
                            'normalized': '+79161234567',
                            'original': '+7 (916) 123-45-67',
                            'confidence': 0.9,   # ДОЛЖЕН БЫТЬ УДАЛЕН
                            'metadata': {'foo': 'bar'}  # ДОЛЖЕН БЫТЬ УДАЛЕН
                        }
                    ],
                    'position': 'Менеджер'
                }
            ],
            'summary': {
                'subject': 'Тест',
                'main_topic': 'Тестирование'
            },
            'key_points': [],
            'business_context': 'test',
            'commercial_offers': []
        }
        
        email_data = {
            'from': 'test@test.ru',
            'to': ['recipient@test.ru'],
            'subject': 'Test',
            'body': 'Test body'
        }
        
        # Обрабатываем через постпроцессор
        result = self.postprocessor.process_llm_response(llm_result, email_data)
        
        # Проверяем организации
        assert 'organizations' in result
        assert len(result['organizations']) > 0
        
        org = result['organizations'][0]
        assert 'phones' in org
        assert len(org['phones']) > 0
        
        org_phone = org['phones'][0]
        
        # Проверяем санитизацию
        assert 'confidence' not in org_phone, "Поле confidence должно быть удалено"
        assert 'source' not in org_phone, "Поле source должно быть удалено"
        
        # Проверяем whitelist поля
        allowed_keys = {'type', 'number', 'normalized', 'original', 'extension'}
        assert set(org_phone.keys()).issubset(allowed_keys), f"Найдены лишние ключи: {set(org_phone.keys()) - allowed_keys}"
        
        # Проверяем контакты
        assert 'contacts' in result
        assert len(result['contacts']) > 0
        
        contact = result['contacts'][0]
        assert 'phones' in contact
        assert len(contact['phones']) > 0
        
        contact_phone = contact['phones'][0]
        
        # Проверяем санитизацию
        assert 'confidence' not in contact_phone, "Поле confidence должно быть удалено"
        assert 'metadata' not in contact_phone, "Поле metadata должно быть удалено"
        
        # Проверяем whitelist поля
        assert set(contact_phone.keys()).issubset(allowed_keys), f"Найдены лишние ключи: {set(contact_phone.keys()) - allowed_keys}"
    
    def test_ui_format_regeneration_in_pipeline(self):
        """Тест регенерации UI-формата в полном пайплайне"""
        llm_result = {
            'organizations': [
                {
                    'organization_id': 1,
                    'name': 'Тестовая Компания',
                    'phones': [
                        {
                            'type': 'office',
                            'number': 'old format',  # Будет перезаписан
                            'normalized': '+74956401771',
                            'original': '+7 (495) 640-17-71'
                        }
                    ],
                    'emails': ['info@test.ru'],
                    'city': 'Москва'
                }
            ],
            'contacts': [],
            'summary': {'subject': 'Тест', 'main_topic': 'Тестирование'},
            'key_points': [],
            'business_context': 'test',
            'commercial_offers': []
        }
        
        email_data = {
            'from': 'test@test.ru',
            'to': ['recipient@test.ru'],
            'subject': 'Test',
            'body': 'Test body'
        }
        
        result = self.postprocessor.process_llm_response(llm_result, email_data)
        
        org = result['organizations'][0]
        phone = org['phones'][0]
        
        # Проверяем, что number регенерирован из normalized
        assert phone['number'] != 'old format', "number должен быть регенерирован"
        assert phone['number'] == '+7 (495) 640-17-71', f"Неправильный формат: {phone['number']}"
        
        # Проверяем формат RU номера
        assert phone['number'].startswith('+7 ('), "RU номер должен начинаться с +7 ("
        assert ')' in phone['number'], "RU номер должен содержать скобки"
    
    def test_metadata_collection(self):
        """Тест сбора метаданных phone UI форматирования"""
        llm_result = {
            'organizations': [
                {
                    'organization_id': 1,
                    'name': 'Компания 1',
                    'phones': [
                        {
                            'type': 'office',
                            'number': '+7 495 640-17-71',
                            'normalized': '+74956401771',
                            'original': '+7 (495) 640-17-71'
                        },
                        {
                            'type': 'mobile',
                            'number': '+7 916 123-45-67',
                            'normalized': '+79161234567',
                            'original': '+7 (916) 123-45-67'
                        }
                    ],
                    'emails': ['info@test.ru'],
                    'city': 'Москва'
                }
            ],
            'contacts': [
                {
                    'contact_id': 1,
                    'name': 'Иванов Иван',
                    'organization_id': 1,
                    'email': 'ivanov@test.ru',
                    'phones': [
                        {
                            'type': 'mobile',
                            'number': '+7 916 999-88-77',
                            'normalized': '+79169998877',
                            'original': '+7 (916) 999-88-77'
                        }
                    ],
                    'position': 'Менеджер'
                }
            ],
            'summary': {'subject': 'Тест', 'main_topic': 'Тестирование'},
            'key_points': [],
            'business_context': 'test',
            'commercial_offers': []
        }
        
        email_data = {
            'from': 'test@test.ru',
            'to': ['recipient@test.ru'],
            'subject': 'Test',
            'body': 'Test body'
        }
        
        result = self.postprocessor.process_llm_response(llm_result, email_data)
        
        # Проверяем наличие метаданных
        assert 'postprocessing_metadata' in result
        assert 'phone_ui_formatting' in result['postprocessing_metadata']
        
        stats = result['postprocessing_metadata']['phone_ui_formatting']
        
        # Проверяем структуру метаданных
        assert 'phones_processed' in stats
        assert 'organizations_processed' in stats
        assert 'contacts_processed' in stats
        assert 'ui_format_applied' in stats
        assert 'phones_sanitized' in stats
        
        # Проверяем значения
        assert stats['phones_processed'] == 3, f"Должно быть 3 телефона, получено {stats['phones_processed']}"
        assert stats['organizations_processed'] == 1
        assert stats['contacts_processed'] == 1
        assert stats['ui_format_applied'] > 0, "UI формат должен быть применен"
        assert stats['phones_sanitized'] > 0, "Телефоны должны быть санитизированы"
    
    def test_international_number_formatting(self):
        """Тест форматирования международных номеров"""
        llm_result = {
            'organizations': [
                {
                    'organization_id': 1,
                    'name': 'US Company',
                    'phones': [
                        {
                            'type': 'office',
                            'number': 'old',
                            'normalized': '+12025551234',  # US number
                            'original': '+1 (202) 555-1234'
                        }
                    ],
                    'emails': ['info@uscompany.com'],
                    'city': 'Washington'
                }
            ],
            'contacts': [],
            'summary': {'subject': 'Test', 'main_topic': 'Test'},
            'key_points': [],
            'business_context': 'test',
            'commercial_offers': []
        }
        
        email_data = {
            'from': 'test@test.com',
            'to': ['recipient@test.com'],
            'subject': 'Test',
            'body': 'Test body'
        }
        
        result = self.postprocessor.process_llm_response(llm_result, email_data)
        
        org = result['organizations'][0]
        phone = org['phones'][0]
        
        # Проверяем, что number регенерирован
        assert phone['number'] != 'old'
        assert phone['number'].startswith('+1'), f"US номер должен начинаться с +1, получено: {phone['number']}"
        
        # Проверяем санитизацию
        allowed_keys = {'type', 'number', 'normalized', 'original', 'extension'}
        assert set(phone.keys()).issubset(allowed_keys)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
