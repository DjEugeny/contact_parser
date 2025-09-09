"""
Интеграционные тесты для функциональности обогащения контактов (Фаза 8)
Тестирует работу ContactEnricher с реальными данными из email файлов 2025-07-29
"""

import pytest
import os
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from src.core.extractor_factory import ExtractorFactory
from src.core.contact_enricher import ContactEnricher
from src.core.inn_validator import RussianINNValidator
from src.core.website_extractor import WebsiteExtractor


class TestContactEnrichmentIntegration:
    """Интеграционные тесты обогащения контактов"""
    
    @pytest.fixture
    def extractor(self):
        """Фикстура для создания экстрактора"""
        return ExtractorFactory.create_extractor()
    
    @pytest.fixture
    def contact_enricher(self):
        """Фикстура для обогатителя контактов"""
        inn_validator = RussianINNValidator()
        website_extractor = WebsiteExtractor()
        return ContactEnricher(inn_validator, website_extractor)
    
    def test_basic_contact_extraction(self, extractor):
        """Тест базового извлечения контактов"""
        test_text = """
        Уважаемый Иван Алексеевич!
        
        Направляю Вам коммерческое предложение.
        
        С уважением,
        Иванов Иван Иванович
        Генеральный директор
        ООО «ДНК-Технология»
        Тел: +7 (495) 640-17-71
        Email: ivanov@dna-technology.ru
        """
        
        result = extractor.extract_all_data(test_text)
        contacts = result.get('contacts', [])
        
        assert len(contacts) >= 1
        contact = contacts[0]
        
        # Проверяем базовые поля
        assert contact.get('name') == 'Иванов Иван Иванович'
        assert contact.get('phone') == '+7 (495) 640-17-71'
        assert contact.get('email') == 'ivanov@dna-technology.ru'
        assert contact.get('organization') == 'ООО «ДНК-Технология»'
        assert contact.get('position') == 'Генеральный директор'
    
    def test_inn_extraction_from_text(self, contact_enricher):
        """Тест извлечения ИНН из текста"""
        test_contacts = [{
            'name': 'Иванов Иван Иванович',
            'organization': 'ООО «ДНК-Технология»',
            'email': 'ivanov@dna-technology.ru'
        }]
        
        test_text = """
        ООО «ДНК-Технология», ИНН: 1901066506, сайт: dna-technology.ru
        Контактное лицо: Иванов Иван Иванович
        """
        
        enriched_contacts = contact_enricher.enrich_contacts(test_contacts, {'body': test_text})
        
        assert len(enriched_contacts) == 1
        contact = enriched_contacts[0]
        
        # Проверяем, что ИНН извлечен
        assert contact.get('inn') == '1901066506'
        assert contact.get('website') == 'dna-technology.ru'
    
    def test_website_extraction_from_email_domain(self, contact_enricher):
        """Тест извлечения сайта из домена email"""
        test_contacts = [{
            'name': 'Петрова Анна Сергеевна',
            'email': 'anna.petrova@dna-technology.ru',
            'organization': 'ООО «ДНК-Технология»'
        }]
        
        enriched_contacts = contact_enricher.enrich_contacts(test_contacts)
        
        assert len(enriched_contacts) == 1
        contact = enriched_contacts[0]
        
        # Проверяем извлечение сайта из домена
        assert 'dna-technology.ru' in contact.get('website', '')
    
    def test_inn_validation_10_digits(self):
        """Тест валидации 10-значного ИНН"""
        validator = RussianINNValidator()
        
        # Валидные сайты
        assert extractor.is_website_accessible('https://dna-technology.ru') == True
        # Валидный ИНН организации
        result = validator.validate_inn('1901066506')
        assert result['is_valid'] == True
        assert result['type'] == "organization"        # Невалидные сайты
        assert extractor.is_website_accessible('not-a-website') == False        assert result['is_valid'] == True
        assert result['inn_type'] == 'organization'
        
        # Невалидный ИНН
        result = validator.validate_inn('1234567890')
        assert result['is_valid'] == False
        # Валидный ИНН индивидуального предпринимателя
        result = validator.validate_inn('123456789012')
        assert result['is_valid'] == True
        assert result['type'] == "individual"        # Валидный ИНН индивидуального предпринимателя
        result = validator.validate_inn('123456789012')
        assert result['is_valid'] == True
        assert result['inn_type'] == 'individual'
    
    def test_website_validation(self):
        """Тест валидации сайтов"""
        extractor = WebsiteExtractor()
        
        # Валидные сайты
        assert extractor.validate_website('https://dna-technology.ru') == True
        assert extractor.validate_website('www.company.com') == True
        assert extractor.validate_website('example.org') == True
        
        # Невалидные сайты
        assert extractor.validate_website('not-a-website') == False
    
    def test_name_formats_extraction(self, extractor):
        """Тест извлечения различных форматов имен"""
        test_text = """
        Контакты для связи:
        
        1. Иванов Иван Иванович (полное ФИО)
        2. Петрова Анна Сергеевна (полное ФИО)
        3. Клочкова-Абельянс Сатеник Аршавиловна (двойная фамилия)
        4. Сидоров И.И. (инициалы + фамилия)
        5. Мария Гоголева (имя + фамилия)
        6. Директор Иванов (должность + фамилия)
        """
        
        result = extractor.extract_all_data(test_text)
        contacts = result.get('contacts', [])
        
        # Проверяем, что найдены все форматы имен
        names_found = [c.get('name') for c in contacts if c.get('name')]
        
        expected_names = [
            'Иванов Иван Иванович',
            'Петрова Анна Сергеевна', 
            'Клочкова-Абельянс Сатеник Аршавиловна',
            'Сидоров И.И.',
            'Мария Гоголева',
            'Директор Иванов'
        ]
        
        for expected_name in expected_names:
            assert expected_name in names_found, f"Имя {expected_name} не найдено в результатах"
    
    def test_full_enrichment_pipeline(self, extractor, contact_enricher):
        """Тест полного пайплайна обогащения контактов"""
        test_text = """
        ООО «ДНК-Технология», ИНН: 1901066506
        Сайт: dna-technology.ru
        
        Контактное лицо:
        Иванов Иван Иванович
        Генеральный директор
        Тел: +7 (495) 640-17-71
        Email: ivanov@dna-technology.ru
        
        Также:
        Петрова Анна Сергеевна
        ИНН: 123456789012
        Email: anna.petrova@company.ru
        """
        
        # Шаг 1: Извлечение базовых контактов через LLM
        result = extractor.extract_all_data(test_text)
        contacts = result.get('contacts', [])
        
        # Шаг 2: Обогащение контактов дополнительными данными
        enriched_contacts = contact_enricher.enrich_contacts(contacts, {'body': test_text})
        
        # Проверки
        assert len(enriched_contacts) >= 2
        
        # Ищем контакт Иванова
        ivanov_contact = None
        petrova_contact = None
        
        for contact in enriched_contacts:
            if 'Иванов Иван Иванович' in contact.get('name', ''):
                ivanov_contact = contact
            elif 'Петрова Анна Сергеевна' in contact.get('name', ''):
                petrova_contact = contact
        
        # Проверяем данные Иванова
        assert ivanov_contact is not None
        assert ivanov_contact.get('inn') == '1901066506'
        assert 'dna-technology.ru' in ivanov_contact.get('website', '')
        
        # Проверяем данные Петровой
        assert petrova_contact is not None
        assert petrova_contact.get('inn') == '123456789012'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
