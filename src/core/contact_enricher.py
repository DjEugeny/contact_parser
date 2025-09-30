"""
Обогатитель контактов дополнительными данными
Интегрирует валидацию ИНН и извлечение сайтов в процесс обработки контактов.

Author: Contact Parser Team
Created: 2025-09-08
"""

import re
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict, List, Optional

from .inn_validator import RussianINNValidator
from .website_extractor import WebsiteExtractor

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentStats:
    """📊 Статистика работы обогатителя контактов"""

    contacts_processed: int = 0
    websites_extracted: int = 0
    inns_validated: int = 0
    corporate_profiles: int = 0
    errors: int = 0
    total_runtime_seconds: float = 0.0
    sources: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """📊 Возвращает статистику в формате словаря"""
        data = asdict(self)
        data['sources'] = dict(self.sources)
        return data

    def record_source(self, source: Optional[str]) -> None:
        """📌 Регистрирует источник найденного сайта"""
        if not source:
            source = 'unknown'
        self.sources[source] = self.sources.get(source, 0) + 1


class EnrichmentErrorHandler:
    """🛡️ Обработчик ошибок обогащения контактов"""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.error_stats: Dict[str, int] = {}

    def handle_enrichment_error(self, error: Exception, contact: Dict[str, Any]) -> None:
        """⚠️ Логирует ошибку обогащения и обновляет статистику"""
        contact_name = contact.get('name', 'Unknown')
        error_type = error.__class__.__name__
        self.logger.error(f"❌ Ошибка обогащения контакта {contact_name}: {error}")
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1

    def get_error_stats(self) -> Dict[str, int]:
        """📊 Возвращает собранную статистику ошибок"""
        return dict(self.error_stats)


class ContactEnricher:
    """
    Обогатитель контактов дополнительными данными
    
    Функции:
    1. Валидация ИНН из контактов
    2. Извлечение сайтов компаний
    3. Обогащение контактов метаданными
    4. Корпоративная разведка по email доменам
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
                       email_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Обогащение списка контактов дополнительными данными
        
        Args:
            contacts: Список контактов для обогащения
            email_data: Данные email для дополнительного анализа
            
        Returns:
            List[Dict]: Обогащенные контакты
        """
        if not contacts:
            return []
        
        enriched_contacts = []
        
        for contact in contacts:
            try:
                enriched_contact = self._enrich_single_contact(contact, email_data)
                enriched_contacts.append(enriched_contact)
            except Exception as e:
                self.logger.error(f"Ошибка при обогащении контакта {contact.get('name', 'Unknown')}: {str(e)}")
                # Возвращаем оригинальный контакт в случае ошибки
                enriched_contacts.append(contact)
        
        return enriched_contacts
    
    def _enrich_single_contact(self, contact: Dict[str, Any], 
                              email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Обогащение одного контакта
        
        Args:
            contact: Контакт для обогащения
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
        
        # 3. Корпоративная разведка
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
            if isinstance(website_info, dict):
                contact['website_source'] = website_info.get('source')
                contact['website_method'] = website_info.get('method')
        else:
            contact['website'] = None
            contact['website_confidence'] = 0.0
            contact.pop('website_source', None)
            contact.pop('website_method', None)

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
        """📊 Возвращает базовую статистику обогащения"""
        return {
            'contacts_processed': getattr(self, '_contacts_enriched_count', 0),
            'websites_extracted': getattr(self, '_websites_extracted_count', 0),
            'inns_validated': getattr(self, '_inn_validated_count', 0),
            'errors': getattr(self, '_errors_count', 0),
        }


class EnhancedContactEnricher(ContactEnricher):
    """🚀 Расширенный обогатитель контактов с диагностикой"""

    def __init__(self, inn_validator: Optional[RussianINNValidator] = None,
                 website_extractor: Optional[WebsiteExtractor] = None,
                 error_handler: Optional[EnrichmentErrorHandler] = None) -> None:
        super().__init__(inn_validator=inn_validator, website_extractor=website_extractor)
        self.logger = logging.getLogger(__name__)
        self.error_handler = error_handler or EnrichmentErrorHandler(self.logger)
        self.stats = EnrichmentStats()
        self._last_run_summary: Dict[str, Any] = {}

    def enrich_contacts(self, contacts: List[Dict[str, Any]],
                        email_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """🔍 Обогащает контакты с логированием и обработкой ошибок"""
        if not contacts:
            self.logger.info("⚠️ Нет контактов для обогащения")
            return []

        start_time = perf_counter()
        self.logger.info(f"🔍 Запуск обогащения {len(contacts)} контактов")

        enriched_contacts: List[Dict[str, Any]] = []

        for contact in contacts:
            self.stats.contacts_processed += 1
            try:
                enriched = self._enrich_single_contact(contact.copy(), email_data)
                self._update_stats(enriched)
                enriched_contacts.append(enriched)
            except Exception as error:  # pylint: disable=broad-except
                self.stats.errors += 1
                self.error_handler.handle_enrichment_error(error, contact)
                enriched_contacts.append(contact)

        duration = perf_counter() - start_time
        self.stats.total_runtime_seconds += duration
        self._last_run_summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'contacts_requested': len(contacts),
            'contacts_returned': len(enriched_contacts),
            'duration_seconds': round(duration, 6),
            'errors': self.stats.errors,
        }

        self.logger.info(
            f"✅ Обогащение завершено: {len(enriched_contacts)} контактов за {duration:.3f} сек."
        )

        return enriched_contacts

    def get_enrichment_stats(self) -> Dict[str, Any]:
        """📊 Возвращает агрегированную статистику обогащения"""
        stats = self.stats.to_dict()
        stats['error_types'] = self.error_handler.get_error_stats()
        if self._last_run_summary:
            stats['last_run'] = self._last_run_summary
        return stats

    def get_diagnostic_info(self) -> Dict[str, Any]:
        """🩺 Возвращает расширенную диагностическую информацию"""
        diagnostics = self.get_enrichment_stats()
        diagnostics['diagnostic_timestamp'] = datetime.now(timezone.utc).isoformat()
        return diagnostics

    def reset_stats(self) -> None:
        """🔄 Сбрасывает накопленную статистику"""
        self.stats = EnrichmentStats()
        self._last_run_summary = {}
        self.error_handler = EnrichmentErrorHandler(self.logger)

    def _update_stats(self, contact: Dict[str, Any]) -> None:
        """📈 Обновляет статистику по результатам обогащения"""
        if contact.get('website'):
            self.stats.websites_extracted += 1
            self.stats.record_source(contact.get('website_source'))

        if contact.get('inn') and contact.get('inn_validated'):
            self.stats.inns_validated += 1

        if contact.get('organization_type'):
            self.stats.corporate_profiles += 1


# Пример использования
if __name__ == "__main__":
    enricher = ContactEnricher()
    
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
    
    # Обогащение контакта
    enriched_contacts = enricher.enrich_contacts([test_contact], test_email_data)
    
    print("🎯 Результат обогащения контакта:")
    for key, value in enriched_contacts[0].items():
        if value is not None:
            print(f"  {key}: {value}")
