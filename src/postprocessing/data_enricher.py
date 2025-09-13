"""Обогатитель данных постобработки
Интегрирует валидацию ИНН, извлечение сайтов и обогащение полей city/address
Адаптирован для новой структуры organizations/contacts согласно мини-ТЗ

Author: Contact Parser Team
Created: 2025-09-13 (адаптировано из contact_enricher.py)
"""

import re
import logging
from typing import List, Dict, Optional, Any
# Попытка импорта модулей из core
try:
    from ..core.inn_validator import RussianINNValidator
    from ..core.website_extractor import WebsiteExtractor
except ImportError:
    # Fallback для тестов и прямого запуска
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
    try:
        from inn_validator import RussianINNValidator
        from website_extractor import WebsiteExtractor
    except ImportError:
        # Mock классы для тестирования
        class RussianINNValidator:
            def validate_inn(self, inn):
                return {'valid': True, 'type': 'organization'}
        
        class WebsiteExtractor:
            def extract_from_email_body(self, body):
                return []
            def extract_from_email_domain(self, email):
                return None

logger = logging.getLogger(__name__)


class DataEnricher:
    """Обогатитель данных постобработки
    
    Функции:
    1. Валидация ИНН из контактов и организаций
    2. Извлечение сайтов компаний
    3. Обогащение полей city/address из организаций в контакты
    4. Корпоративная разведка по email доменам
    5. Работа с новой структурой phones[] массива
    """
    
    def __init__(self, inn_validator: Optional[RussianINNValidator] = None,
                 website_extractor: Optional[WebsiteExtractor] = None):
        """
        Инициализация обогатителя контактов
        
        Args:
            inn_validator: Валидатор ИНН (создается автоматически если None)
            website_extractor: Извлекатель сайтов (создается автоматически если None)
        """
        self.inn_validator = inn_validator or RussianINNValidator()
        self.website_extractor = website_extractor or WebsiteExtractor()
        self.logger = logging.getLogger(__name__)
    
    def enrich_contacts(self, contacts: List[Dict[str, Any]], 
                       organizations: Dict[int, Dict[str, Any]] = None,
                       email_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Обогащение списка контактов дополнительными данными
        
        Args:
            contacts: Список контактов для обогащения
            organizations: Словарь организаций для обогащения полей
            email_data: Данные email для дополнительного анализа
            
        Returns:
            List[Dict]: Обогащенные контакты
        """
        if not contacts:
            return []
        
        enriched_contacts = []
        
        for contact in contacts:
            try:
                enriched_contact = self._enrich_single_contact(contact, organizations, email_data)
                enriched_contacts.append(enriched_contact)
            except Exception as e:
                self.logger.error(f"Ошибка при обогащении контакта {contact.get('name', 'Unknown')}: {str(e)}")
                # Возвращаем оригинальный контакт в случае ошибки
                enriched_contacts.append(contact)
        
        return enriched_contacts
    
    def _enrich_single_contact(self, contact: Dict[str, Any],
                              organizations: Dict[int, Dict[str, Any]] = None,
                              email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Обогащение одного контакта
        
        Args:
            contact: Контакт для обогащения
            organizations: Словарь организаций
            email_data: Данные email
            
        Returns:
            Dict: Обогащенный контакт
        """
        # Создаем копию контакта
        enriched = contact.copy()
        
        # 1. Обработка ИНН
        enriched = self._enrich_inn_data(enriched, email_data)
        
        # 2. Обработка сайта
        enriched = self._enrich_website_data(enriched, email_data)
        
        # 3. Обогащение полей city/address из организации
        enriched = self._enrich_location_from_organization(enriched, organizations)
        
        # 4. Корпоративная разведка
        enriched = self._enrich_corporate_intelligence(enriched, email_data)
        
        return enriched
    
    def _enrich_inn_data(self, contact: Dict[str, Any], 
                        email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Обогащение контакта данными ИНН
        
        Args:
            contact: Контакт для обогащения
            email_data: Данные email
            
        Returns:
            Dict: Контакт с данными ИНН
        """
        # ИНН может быть уже в контакте (извлечен LLM)
        inn = contact.get('inn')
        
        # Если ИНН не найден в контакте, ищем в email данных
        if not inn and email_data:
            inn = self._extract_inn_from_email_data(email_data)
        
        if inn:
            # Валидация ИНН
            validation_result = self.inn_validator.validate_inn(inn)
            
            contact['inn'] = inn
            contact['inn_type'] = validation_result.get('type')
            contact['inn_validated'] = validation_result.get('valid', False)
            
            # Добавляем детали валидации для отладки
            if not validation_result.get('valid', False) and validation_result.get('error'):
                contact['inn_validation_error'] = validation_result['error']
        else:
            # Если ИНН не найден, устанавливаем значения по умолчанию
            contact['inn'] = None
            contact['inn_type'] = None
            contact['inn_validated'] = False
        
        return contact
    
    def _enrich_website_data(self, contact: Dict[str, Any], 
                           email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Обогащение контакта данными сайта
        
        Args:
            contact: Контакт для обогащения
            email_data: Данные email
            
        Returns:
            Dict: Контакт с данными сайта
        """
        # Сайт может быть уже в контакте (извлечен LLM)
        website = contact.get('website')
        confidence = contact.get('website_confidence', 0.0)  # Инициализируем confidence
        
        # Если сайт не найден в контакте, ищем в email данных
        if not website:
            website_info = self._extract_website_from_email_data(contact, email_data)
            if website_info:
                website = website_info['url']
                confidence = website_info['confidence']
            else:
                confidence = 0.0
        
        if website:
            # Валидация сайта (опционально, может быть дорого)
            # validation = self.website_extractor.validate_website(website)
            
            contact['website'] = website
            contact['website_confidence'] = confidence
        else:
            contact['website'] = None
            contact['website_confidence'] = 0.0
        
        return contact
    
    def _enrich_location_from_organization(self, contact: Dict[str, Any],
                                         organizations: Dict[int, Dict[str, Any]] = None) -> Dict[str, Any]:
        """Обогащение полей city и address из организации согласно мини-ТЗ п.5
        
        Args:
            contact: Контакт для обогащения
            organizations: Словарь организаций
            
        Returns:
            Dict: Контакт с обогащенными полями
        """
        if not organizations:
            return contact
            
        org_id = contact.get('organization_id')
        if not org_id or org_id not in organizations:
            return contact
            
        organization = organizations[org_id]
        
        # Обогащаем city, если у контакта не указан
        if not contact.get('city') and organization.get('city'):
            contact['city'] = organization['city']
            self.logger.debug(f"Обогащен city для контакта {contact.get('name', 'Unknown')}: {organization['city']}")
            
        # Обогащаем address, если у контакта не указан
        if not contact.get('address') and organization.get('address'):
            contact['address'] = organization['address']
            self.logger.debug(f"Обогащен address для контакта {contact.get('name', 'Unknown')}: {organization['address']}")
            
        return contact
    
    def _enrich_corporate_intelligence(self, contact: Dict[str, Any], 
                                     email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Корпоративная разведка - дополнительные insights
        
        Args:
            contact: Контакт для анализа
            email_data: Данные email
            
        Returns:
            Dict: Контакт с дополнительными insights
        """
        # Анализ корпоративного email
        email = contact.get('email')
        if email and '@' in email:
            domain = email.split('@')[1].lower()
            
            # Определение типа организации по домену
            if domain.endswith('.ru'):
                contact['organization_type'] = 'russian_company'
            elif domain.endswith(('.com', '.org', '.net')):
                contact['organization_type'] = 'international_company'
            else:
                contact['organization_type'] = 'other'
            
            # Проверка на государственные организации
            if any(keyword in domain for keyword in ['gov.ru', 'min', 'fsb', 'mvd']):
                contact['organization_type'] = 'government'
        
        return contact
    
    def _extract_inn_from_email_data(self, email_data: Dict[str, Any]) -> Optional[str]:
        """
        Извлечение ИНН из данных email
        
        Args:
            email_data: Данные email
            
        Returns:
            str or None: Найденный ИНН
        """
        if not email_data:
            return None
        
        # Поиск ИНН в теле письма
        body = email_data.get('body', '')
        if body:
            # Регулярное выражение для поиска ИНН
            inn_patterns = [
                r'ИНН[:\s]+(\d{10})',  # ИНН: 1234567890
                r'ИНН[:\s]+(\d{12})',  # ИНН: 123456789012
                r'\b(\d{10})\b',        # Просто 10 цифр
                r'\b(\d{12})\b',        # Просто 12 цифр
            ]
            
            for pattern in inn_patterns:
                matches = re.findall(pattern, body)
                for match in matches:
                    # Проверяем, что это действительно ИНН (не телефон и т.п.)
                    if self._is_likely_inn(match, body):
                        return match
        
        return None
    
    def _extract_website_from_email_data(self, contact: Dict[str, Any], 
                                       email_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Извлечение сайта из данных email
        
        Args:
            contact: Данные контакта
            email_data: Данные email
            
        Returns:
            Dict or None: Информация о сайте
        """
        # 1. Извлечение из тела письма
        if email_data and email_data.get('body'):
            websites = self.website_extractor.extract_from_email_body(email_data['body'])
            if websites:
                return websites[0]  # Возвращаем самый уверенный
        
        # 2. Извлечение из домена email контакта
        email = contact.get('email')
        if email:
            domain_website = self.website_extractor.extract_from_email_domain(email)
            if domain_website:
                return domain_website
        
        # 3. Извлечение из домена отправителя
        if email_data and email_data.get('from'):
            sender_website = self.website_extractor.extract_from_email_domain(email_data['from'])
            if sender_website:
                return sender_website
        
        return None
    
    def _is_likely_inn(self, candidate: str, context: str) -> bool:
        """
        Проверка, является ли кандидат ИНН (а не чем-то другим)
        
        Args:
            candidate: Кандидат на ИНН
            context: Контекст, где найден кандидат
            
        Returns:
            bool: Вероятно ли, что это ИНН
        """
        # Проверяем контекст вокруг кандидата
        context_window = 50  # Символов до и после
        
        # Ищем позицию кандидата в контексте
        pos = context.find(candidate)
        if pos == -1:
            return False
        
        # Извлекаем контекст
        start = max(0, pos - context_window)
        end = min(len(context), pos + len(candidate) + context_window)
        surrounding = context[start:end].lower()
        
        # Ключевые слова, указывающие на ИНН
        inn_keywords = ['инн', 'inn', 'идентификационн', 'налогоплательщик']
        
        # Ключевые слова, указывающие, что это НЕ ИНН
        not_inn_keywords = ['тел', 'телефон', 'phone', 'факс', 'fax', '+7', '+8']
        
        # Проверяем наличие ключевых слов
        has_inn_keywords = any(keyword in surrounding for keyword in inn_keywords)
        has_not_inn_keywords = any(keyword in surrounding for keyword in not_inn_keywords)
        
        # Если есть ключевые слова ИНН и нет ключевых слов НЕ ИНН
        if has_inn_keywords and not has_not_inn_keywords:
            return True
        
        # Если есть ключевые слова НЕ ИНН
        if has_not_inn_keywords:
            return False
        
        # Если нет явных указателей, проверяем формат
        # ИНН обычно не начинается с 7 или 8 (телефонные коды)
        if candidate.startswith(('7', '8')):
            return False
        
        # ИНН обычно содержит разнообразные цифры
        unique_digits = len(set(candidate))
        if unique_digits < 5:  # Слишком мало уникальных цифр
            return False
        
        return True
    
    def get_enrichment_stats(self) -> Dict[str, Any]:
        """
        Получение статистики обогащения
        
        Returns:
            Dict: Статистика работы обогатителя
        """
        return {
            'inn_validated_count': getattr(self, '_inn_validated_count', 0),
            'websites_extracted_count': getattr(self, '_websites_extracted_count', 0),
            'contacts_enriched_count': getattr(self, '_contacts_enriched_count', 0),
            'errors_count': getattr(self, '_errors_count', 0)
        }


# Пример использования
if __name__ == "__main__":
    enricher = DataEnricher()
    
    # Тестовый контакт
    test_contact = {
        'name': 'Гоголева Мария Михайловна',
        'email': 'm.gogoleva@dna-technology.ru',
        'organization': 'ООО «ДНК-Технология»',
        'phone': '+7 (495) 640-17-71',
        'confidence': 0.95
    }
    
    # Тестовые данные email
    test_email_data = {
        'from': 'm.gogoleva@dna-technology.ru',
        'body': '''
        Добрый день, Иван Алексеевич!
        КП во вложении.
        Гоголева Мария Михайловна
        Менеджер по продаже оборудования | ООО «ДНК-Технология»
        ИНН: 1901066506
        Email: m.gogoleva@dna-technology.ru
        Сайт: dna-technology.ru
        '''
    }
    
    # Тестовые организации
    test_organizations = {
        1: {
            'organization_id': 1,
            'name': 'ООО «ДНК-Технология»',
            'city': 'Москва',
            'address': 'ул. Академика Королёва, д. 12',
            'inn': '1901066506',
            'website': 'dna-technology.ru'
        }
    }
    
    # Обогащение контакта
    enriched_contacts = enricher.enrich_contacts([test_contact], test_organizations, test_email_data)
    
    print("🎯 Результат обогащения контакта:")
    for key, value in enriched_contacts[0].items():
        if value is not None:
            print(f"  {key}: {value}")
