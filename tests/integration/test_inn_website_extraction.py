#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграционный тест для проверки извлечения ИНН и сайтов на реальных данных

Тест проверяет:
1. Корректное извлечение ИНН из email текстов
2. Корректное извлечение сайтов из email текстов  
3. Валидацию ИНН
4. Обогащение контактов через ContactEnricher
5. Работу с реальными данными из /data/emails/

Создан: 2025-01-13 18:44 (UTC+07)
"""

import os
import sys
import pytest
import json
from pathlib import Path
from typing import Dict, List, Any

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.integrated_llm_processor import IntegratedLLMProcessor
from src.core.contact_enricher import ContactEnricher
from src.core.inn_validator import RussianINNValidator
from src.core.website_extractor import WebsiteExtractor


class TestINNWebsiteExtraction:
    """Тесты извлечения ИНН и сайтов"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Настройка тестов"""
        self.data_dir = Path("/Users/evgenyzach/contact_parser/data/emails/2025-01-29")
        self.llm_processor = IntegratedLLMProcessor()
        self.enricher = ContactEnricher(
            inn_validator=RussianINNValidator(),
            website_extractor=WebsiteExtractor()
        )
        
    def test_real_email_inn_extraction(self):
        """Тест извлечения ИНН из реального email"""
        # Используем тестовый файл с известным ИНН
        test_file = self.data_dir / "email_1737977700_1.txt"
        
        if not test_file.exists():
            pytest.skip(f"Тестовый файл не найден: {test_file}")
            
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Извлекаем контакты через LLM
        result = self.llm_processor.process_text(content)
        
        # Проверяем, что результат получен
        assert result is not None, "LLM не вернул результат"
        assert 'contacts' in result, "В результате нет поля contacts"
        
        contacts = result['contacts']
        assert len(contacts) > 0, "Контакты не найдены"
        
        # Ищем контакт с ИНН
        inn_found = False
        expected_inn = "7723537840"  # Известный ИНН из тестового файла
        
        for contact in contacts:
            if contact.get('inn') == expected_inn:
                inn_found = True
                assert contact.get('inn_validated') == True, f"ИНН {expected_inn} не прошел валидацию"
                break
                
        assert inn_found, f"Ожидаемый ИНН {expected_inn} не найден в контактах"
        
    def test_real_email_website_extraction(self):
        """Тест извлечения сайта из реального email"""
        test_file = self.data_dir / "email_1737977700_1.txt"
        
        if not test_file.exists():
            pytest.skip(f"Тестовый файл не найден: {test_file}")
            
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Извлекаем контакты через LLM
        result = self.llm_processor.process_text(content)
        
        contacts = result['contacts']
        
        # Ищем контакт с сайтом
        website_found = False
        expected_website = "https://www.dna-technology.ru"  # Известный сайт
        
        for contact in contacts:
            website = contact.get('website')
            if website and 'dna-technology.ru' in website:
                website_found = True
                assert contact.get('website_confidence', 0) > 0, "Уверенность в сайте должна быть > 0"
                break
                
        assert website_found, "Ожидаемый сайт не найден в контактах"
        
    def test_contact_enrichment_integration(self):
        """Тест интеграции обогащения контактов"""
        # Тестовый контакт
        test_contact = {
            'name': 'Гоголева Мария',
            'email': 'mail@dna-technology.ru',
            'organization': 'ООО «ДНК-Технология»',
            'inn': '7723537840',
            'website': 'https://www.dna-technology.ru',
            'confidence': 0.9
        }
        
        # Тестовые email данные
        email_data = {
            'body': '''
            Добрый день!
            ИНН: 7723537840
            Сайт: dna-technology.ru
            Email: m.gogoleva@dna-technology.ru
            '''
        }
        
        # Обогащаем контакт
        enriched = self.enricher._enrich_single_contact(test_contact, email_data)
        
        # Проверяем результат
        assert enriched['inn'] == '7723537840', "ИНН должен сохраниться"
        assert enriched.get('inn_validated') is not None, "Должна быть валидация ИНН"
        assert enriched.get('website') is not None, "Сайт должен быть найден"
        assert enriched.get('website_confidence') is not None, "Должна быть уверенность в сайте"
        
    def test_multiple_emails_processing(self):
        """Тест обработки нескольких email файлов"""
        if not self.data_dir.exists():
            pytest.skip(f"Директория с данными не найдена: {self.data_dir}")
            
        email_files = list(self.data_dir.glob("email_*.txt"))[:3]  # Берем первые 3 файла
        
        if len(email_files) == 0:
            pytest.skip("Email файлы не найдены")
            
        total_contacts = 0
        total_inns = 0
        total_websites = 0
        
        for email_file in email_files:
            with open(email_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            result = self.llm_processor.process_text(content)
            
            if result and 'contacts' in result:
                contacts = result['contacts']
                total_contacts += len(contacts)
                
                for contact in contacts:
                    if contact.get('inn'):
                        total_inns += 1
                    if contact.get('website'):
                        total_websites += 1
                        
        # Проверяем, что хотя бы что-то извлечено
        assert total_contacts > 0, "Контакты не найдены ни в одном файле"
        
        # Логируем статистику
        print(f"\n📊 Статистика обработки {len(email_files)} файлов:")
        print(f"   Всего контактов: {total_contacts}")
        print(f"   Контактов с ИНН: {total_inns}")
        print(f"   Контактов с сайтами: {total_websites}")
        print(f"   % с ИНН: {(total_inns/total_contacts*100):.1f}%")
        print(f"   % с сайтами: {(total_websites/total_contacts*100):.1f}%")
        
    def test_inn_validation_accuracy(self):
        """Тест точности валидации ИНН"""
        validator = RussianINNValidator()
        
        # Тестовые ИНН
        valid_inns = [
            "7723537840",  # ООО ДНК-Технология
            "1901066506",  # Другая организация
            "7707083893",  # ПАО Сбербанк
        ]
        
        invalid_inns = [
            "1234567890",  # Неверная контрольная сумма
            "123456789",   # Неверная длина
            "abcdefghij",  # Не цифры
        ]
        
        # Проверяем валидные ИНН
        for inn in valid_inns:
            result = validator.validate_inn(inn)
            assert result['is_valid'], f"ИНН {inn} должен быть валидным"
            
        # Проверяем невалидные ИНН
        for inn in invalid_inns:
            result = validator.validate_inn(inn)
            assert not result['is_valid'], f"ИНН {inn} должен быть невалидным"
            

if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v", "-s"])