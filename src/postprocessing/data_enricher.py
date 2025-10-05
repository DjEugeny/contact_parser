"""Обогатитель данных постобработки
Интегрирует валидацию ИНН, извлечение сайтов и обогащение полей city/address
Адаптирован для новой структуры organizations/contacts согласно мини-ТЗ

Author: Contact Parser Team
Created: 2025-09-13 (адаптировано из contact_enricher.py)
"""

import logging
from typing import List, Dict, Optional, Any

try:
    from ..core.inn_validator import RussianINNValidator
    from ..core.website_extractor import WebsiteExtractor
    from ..core.contact_enricher import ContactEnricher, EnhancedContactEnricher
    from .smart_contact_enricher import SmartContactEnricher
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
    try:
        from inn_validator import RussianINNValidator
        from website_extractor import WebsiteExtractor
        from contact_enricher import ContactEnricher, EnhancedContactEnricher
        from smart_contact_enricher import SmartContactEnricher
    except ImportError:
        class RussianINNValidator:
            def validate_inn(self, inn):
                return {'valid': True, 'type': 'organization', 'valid': True}

        class WebsiteExtractor:
            def extract_from_email_body(self, body):
                return []

            def extract_from_email_domain(self, email):
                return None

        class ContactEnricher:
            def __init__(self, *args, **kwargs):
                pass

            def enrich_contacts(self, contacts, email_data=None):
                return contacts

        class EnhancedContactEnricher(ContactEnricher):
            pass
        
        class SmartContactEnricher:
            def __init__(self, *args, **kwargs):
                pass
            
            def enrich_contacts(self, contacts, organizations=None, email_data=None):
                return contacts
            
            def get_enrichment_stats(self):
                return {}

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
                 website_extractor: Optional[WebsiteExtractor] = None,
                 contact_enricher: Optional[ContactEnricher] = None):
        """
        Инициализация обогатителя контактов
        
        Args:
            inn_validator: Валидатор ИНН (создается автоматически если None)
            website_extractor: Извлекатель сайтов (создается автоматически если None)
        """
        self.inn_validator = inn_validator or RussianINNValidator()
        self.website_extractor = website_extractor or WebsiteExtractor()
        # Используем SmartContactEnricher вместо EnhancedContactEnricher
        self.contact_enricher = contact_enricher or SmartContactEnricher()
        self.logger = logging.getLogger(__name__)
        self._stats = {
            'contacts_enriched': 0,
            'location_enriched': 0,
            'errors': 0
        }

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
        
        # SmartContactEnricher принимает organizations для правильной логики обогащения
        base_enriched = self.contact_enricher.enrich_contacts(contacts, organizations, email_data)
        enriched_contacts: List[Dict[str, Any]] = []

        for contact in base_enriched:
            try:
                enriched = self._enrich_location_from_organization(contact.copy(), organizations)
                enriched_contacts.append(enriched)
                self._stats['contacts_enriched'] += 1
            except Exception as exc:
                self.logger.error(
                    f"Ошибка при обогащении контакта {contact.get('name', 'Unknown')}: {exc}"
                )
                self._stats['errors'] += 1
                enriched_contacts.append(contact)

        return enriched_contacts
    
    def _enrich_location_from_organization(self, contact: Dict[str, Any],
                                         organizations: Dict[int, Dict[str, Any]] = None) -> Dict[str, Any]:
        """Обогащение полей city и address из организации согласно мини-ТЗ п.5
        
        TASK-008B: НЕ применяет обогащение локации, если у контакта нет персонального сигнала.
        Это предотвращает ложное обогащение HQ-адресами.
        
        ВАЖНО: Адрес НЕ копируется, если город контакта отличается от города организации.
        Это предотвращает попадание адреса HQ к контактам в других городах.
        
        Args:
            contact: Контакт для обогащения
            organizations: Словарь организаций
            
        Returns:
            Dict: Контакт с обогащенными полями
        """
        self.logger.info(f"🔍 TASK-008B: _enrich_location_from_organization вызван для контакта {contact.get('name', 'unknown')}")
        
        if not organizations:
            return contact
            
        org_id = contact.get('organization_id')
        if not org_id or org_id not in organizations:
            return contact
            
        organization = organizations[org_id]
        
        # TASK-008B: Проверяем, есть ли у контакта персональная локация
        # Если у контакта УЖЕ есть city или address, значит был найден персональный сигнал
        # В этом случае можем дополнить недостающее поле
        # Если оба поля пустые - НЕ применяем обогащение, чтобы избежать HQ-протечек
        
        def _has_value(val):
            """Проверка наличия значения (аналогично postprocessor)"""
            if val is None or val == "":
                return False
            if isinstance(val, str):
                return bool(val.strip())
            return True
        
        has_personal_location = _has_value(contact.get('city')) or _has_value(contact.get('address'))
        
        if not has_personal_location:
            self.logger.debug(
                f"🔒 Контакт {contact.get('name', 'Unknown')} без персональной локации. "
                f"Обогащение HQ-локации пропущено (TASK-008B)."
            )
            return contact
        
        # Обогащаем city, если у контакта не указан (но есть address)
        if not contact.get('city') and organization.get('city'):
            contact['city'] = organization['city']
            self.logger.debug(f"Обогащен city для контакта {contact.get('name', 'Unknown')}: {organization['city']}")
            
        # Обогащаем address ТОЛЬКО если город контакта совпадает с городом организации
        # Это предотвращает попадание адреса HQ к региональным представителям
        if not contact.get('address') and organization.get('address'):
            contact_city = contact.get('city', '').strip().lower() if contact.get('city') else ''
            org_city = organization.get('city', '').strip().lower() if organization.get('city') else ''
            
            # Копируем адрес только если города совпадают
            if contact_city and org_city and contact_city == org_city:
                contact['address'] = organization['address']
                self.logger.debug(
                    f"Обогащен address для контакта {contact.get('name', 'Unknown')}: "
                    f"{organization['address']} (город совпадает: {contact_city})"
                )
            elif contact_city and org_city and contact_city != org_city:
                self.logger.debug(
                    f"Адрес НЕ обогащен для контакта {contact.get('name', 'Unknown')}: "
                    f"город контакта ({contact_city}) отличается от города организации ({org_city})"
                )
            
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
    
    
    def get_enrichment_stats(self) -> Dict[str, Any]:
        """Получение статистики обогащения"""
        base_stats = getattr(self.contact_enricher, 'get_enrichment_stats', lambda: {})()
        base_stats.update(self._stats)
        return base_stats


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
