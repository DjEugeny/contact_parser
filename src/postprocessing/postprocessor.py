#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный координатор постобработки данных LLM
Реализует полный алгоритм постобработки согласно мини-ТЗ

Author: Contact Parser Team
Created: 2025-09-13
"""

import logging
from typing import Dict, List, Any, Optional

from .organization_deduplicator import OrganizationDeduplicator
from .contact_filter import ContactFilter
from .data_enricher import DataEnricher
from .data_normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class PostProcessor:
    """Главный координатор постобработки данных LLM
    
    Реализует полный алгоритм согласно мини-ТЗ п.3:
    1. Дедупликация и объединение организаций (п.3.a)
    2. Обновление organization_id в контактах (п.3.b)
    3. Фильтрация ценных контактов (п.3.c)
    4. Обогащение полей city/address (п.3.e)
    5. Нормализация данных (п.3.f)
    """
    
    def __init__(self, 
                 organization_deduplicator: Optional[OrganizationDeduplicator] = None,
                 contact_filter: Optional[ContactFilter] = None,
                 data_enricher: Optional[DataEnricher] = None,
                 data_normalizer: Optional[DataNormalizer] = None):
        """Инициализация постпроцессора
        
        Args:
            organization_deduplicator: Дедупликатор организаций
            contact_filter: Фильтр контактов
            data_enricher: Обогатитель данных
            data_normalizer: Нормализатор данных
        """
        self.org_deduplicator = organization_deduplicator or OrganizationDeduplicator()
        self.contact_filter = contact_filter or ContactFilter()
        self.data_enricher = data_enricher or DataEnricher()
        self.data_normalizer = data_normalizer or DataNormalizer()
        self.logger = logging.getLogger(__name__)
        
        # Статистика обработки
        self.stats = {
            'processed_emails': 0,
            'total_organizations_processed': 0,
            'total_contacts_processed': 0,
            'organizations_deduplicated': 0,
            'contacts_filtered': 0,
            'contacts_enriched': 0,
            'data_normalized': 0
        }
    
    def process_llm_response(self, llm_result: Dict[str, Any], 
                           email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Полная постобработка ответа LLM
        
        Args:
            llm_result: Результат от LLM в новом формате
            email_data: Данные исходного email для обогащения
            
        Returns:
            Dict: Обработанный результат
        """
        self.logger.info("🔄 Начало постобработки ответа LLM")
        
        try:
            # Валидация входных данных
            if not self._validate_llm_result(llm_result):
                raise ValueError("Некорректная структура LLM результата")
            
            # Этап 1: Дедупликация и объединение организаций (п.3.a)
            organizations_mapping = self._process_organizations(
                llm_result.get('organizations', [])
            )
            
            # Этап 2: Обновление organization_id в контактах (п.3.b)
            updated_contacts = self._update_contact_organization_ids(
                llm_result.get('contacts', []), organizations_mapping
            )
            
            # Этап 3: Фильтрация ценных контактов (п.3.c)
            valuable_contacts, updated_organizations = self._filter_valuable_contacts(
                updated_contacts
            )
            
            # Этап 4: Обогащение данных (п.3.e)
            enriched_contacts = self._enrich_contact_data(
                valuable_contacts, updated_organizations, email_data
            )
            
            # Этап 5: Нормализация данных (п.3.f)
            final_contacts, final_organizations = self._normalize_data(
                enriched_contacts, updated_organizations
            )
            
            # Формирование финального результата
            processed_result = self._build_final_result(
                llm_result, final_contacts, final_organizations
            )
            
            # Обновление статистики
            self._update_stats(llm_result, processed_result)
            
            self.logger.info("✅ Постобработка завершена успешно")
            return processed_result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при постобработке: {str(e)}")
            # Возвращаем оригинальный результат в случае ошибки
            return llm_result
    
    def _validate_llm_result(self, llm_result: Dict[str, Any]) -> bool:
        """Валидация структуры LLM результата
        
        Args:
            llm_result: Результат от LLM
            
        Returns:
            bool: Валиден ли результат
        """
        required_fields = ['organizations', 'contacts']
        
        for field in required_fields:
            if field not in llm_result:
                self.logger.error(f"Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем, что organizations и contacts - это списки
        if not isinstance(llm_result['organizations'], list):
            self.logger.error("Поле 'organizations' должно быть списком")
            return False
            
        if not isinstance(llm_result['contacts'], list):
            self.logger.error("Поле 'contacts' должно быть списком")
            return False
        
        return True
    
    def _process_organizations(self, organizations: List[Dict[str, Any]]) -> Dict[int, int]:
        """Этап 1: Дедупликация и объединение организаций
        
        Args:
            organizations: Список организаций из LLM
            
        Returns:
            Dict[int, int]: Маппинг локальных -> глобальных ID
        """
        self.logger.info(f"🏢 Этап 1: Обработка {len(organizations)} организаций")
        
        mapping = self.org_deduplicator.process_organizations(organizations)
        
        self.stats['total_organizations_processed'] += len(organizations)
        self.stats['organizations_deduplicated'] += len(organizations) - len(set(mapping.values()))
        
        self.logger.info(f"✅ Создан маппинг для {len(mapping)} организаций")
        return mapping
    
    def _update_contact_organization_ids(self, contacts: List[Dict[str, Any]], 
                                       mapping: Dict[int, int]) -> List[Dict[str, Any]]:
        """Этап 2: Обновление organization_id в контактах
        
        Args:
            contacts: Список контактов
            mapping: Маппинг локальных -> глобальных ID
            
        Returns:
            List[Dict]: Контакты с обновленными ID
        """
        self.logger.info(f"👤 Этап 2: Обновление organization_id в {len(contacts)} контактах")
        
        updated_contacts = []
        
        for contact in contacts:
            updated_contact = contact.copy()
            local_id = contact.get('organization_id')
            
            if local_id in mapping:
                updated_contact['organization_id'] = mapping[local_id]
                self.logger.debug(f"Обновлен organization_id: {local_id} -> {mapping[local_id]}")
            else:
                self.logger.warning(f"Не найден маппинг для organization_id: {local_id}")
            
            updated_contacts.append(updated_contact)
        
        return updated_contacts
    
    def _filter_valuable_contacts(self, contacts: List[Dict[str, Any]]) -> tuple:
        """Этап 3: Фильтрация ценных контактов
        
        Args:
            contacts: Список контактов для фильтрации
            
        Returns:
            tuple: (ценные контакты, обновленные организации)
        """
        self.logger.info(f"🔍 Этап 3: Фильтрация {len(contacts)} контактов")
        
        # Получаем текущие организации
        current_organizations = {
            org_id: org for org_id, org in self.org_deduplicator.global_organizations.items()
        }
        
        valuable_contacts, updated_organizations = self.contact_filter.filter_valuable_contacts(
            contacts, current_organizations
        )
        
        # Обновляем организации в дедупликаторе
        self.org_deduplicator.global_organizations.update(updated_organizations)
        
        filtered_count = len(contacts) - len(valuable_contacts)
        self.stats['total_contacts_processed'] += len(contacts)
        self.stats['contacts_filtered'] += filtered_count
        
        self.logger.info(f"✅ Отфильтровано {filtered_count} неценных контактов")
        return valuable_contacts, updated_organizations
    
    def _enrich_contact_data(self, contacts: List[Dict[str, Any]], 
                           organizations: Dict[int, Dict[str, Any]],
                           email_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Этап 4: Обогащение данных контактов
        
        Args:
            contacts: Список контактов
            organizations: Словарь организаций
            email_data: Данные email
            
        Returns:
            List[Dict]: Обогащенные контакты
        """
        self.logger.info(f"💎 Этап 4: Обогащение {len(contacts)} контактов")
        
        enriched_contacts = self.data_enricher.enrich_contacts(
            contacts, organizations, email_data
        )
        
        self.stats['contacts_enriched'] += len(enriched_contacts)
        
        self.logger.info(f"✅ Обогащено {len(enriched_contacts)} контактов")
        return enriched_contacts
    
    def _normalize_data(self, contacts: List[Dict[str, Any]], 
                       organizations: Dict[int, Dict[str, Any]]) -> tuple:
        """Этап 5: Нормализация данных
        
        Args:
            contacts: Список контактов
            organizations: Словарь организаций
            
        Returns:
            tuple: (нормализованные контакты, нормализованные организации)
        """
        self.logger.info(f"🔧 Этап 5: Нормализация данных")
        
        normalized_contacts = self.data_normalizer.normalize_contacts(contacts)
        normalized_organizations = self.data_normalizer.normalize_organizations(organizations)
        
        self.stats['data_normalized'] += len(normalized_contacts) + len(normalized_organizations)
        
        self.logger.info(f"✅ Нормализовано {len(normalized_contacts)} контактов и {len(normalized_organizations)} организаций")
        return normalized_contacts, normalized_organizations
    
    def _build_final_result(self, original_result: Dict[str, Any], 
                          final_contacts: List[Dict[str, Any]],
                          final_organizations: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """Формирование финального результата
        
        Args:
            original_result: Оригинальный результат LLM
            final_contacts: Финальные контакты
            final_organizations: Финальные организации
            
        Returns:
            Dict: Финальный результат
        """
        processed_result = original_result.copy()
        
        # Обновляем обработанные данные
        processed_result['organizations'] = list(final_organizations.values())
        processed_result['contacts'] = final_contacts
        
        # Добавляем метаданные постобработки
        processed_result['postprocessing_metadata'] = {
            'processed_at': self._get_current_timestamp(),
            'stats': self.stats.copy(),
            'version': '1.0.0'
        }
        
        return processed_result
    
    def _update_stats(self, original_result: Dict[str, Any], 
                     processed_result: Dict[str, Any]) -> None:
        """Обновление статистики обработки
        
        Args:
            original_result: Оригинальный результат
            processed_result: Обработанный результат
        """
        self.stats['processed_emails'] += 1
        
        # Дополнительная статистика
        original_orgs = len(original_result.get('organizations', []))
        final_orgs = len(processed_result.get('organizations', []))
        
        original_contacts = len(original_result.get('contacts', []))
        final_contacts = len(processed_result.get('contacts', []))
        
        self.logger.info(f"📊 Статистика обработки:")
        self.logger.info(f"  Организации: {original_orgs} -> {final_orgs}")
        self.logger.info(f"  Контакты: {original_contacts} -> {final_contacts}")
    
    def _get_current_timestamp(self) -> str:
        """Получение текущего timestamp
        
        Returns:
            str: Текущее время в формате ISO
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Получение статистики обработки
        
        Returns:
            Dict: Полная статистика
        """
        base_stats = self.stats.copy()
        
        # Добавляем статистику компонентов
        base_stats['organization_deduplicator'] = self.org_deduplicator.get_stats()
        base_stats['contact_filter'] = self.contact_filter.get_filter_stats([])
        base_stats['data_enricher'] = self.data_enricher.get_enrichment_stats()
        base_stats['data_normalizer'] = self.data_normalizer.get_normalization_stats()
        
        return base_stats
    
    def reset_stats(self) -> None:
        """Сброс статистики"""
        self.stats = {
            'processed_emails': 0,
            'total_organizations_processed': 0,
            'total_contacts_processed': 0,
            'organizations_deduplicated': 0,
            'contacts_filtered': 0,
            'contacts_enriched': 0,
            'data_normalized': 0
        }
        self.logger.info("📊 Статистика сброшена")


# Пример использования
if __name__ == "__main__":
    postprocessor = PostProcessor()
    
    # Тестовый LLM результат в новом формате
    test_llm_result = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "inn": "1901066506",
                "website": "dna-technology.ru",
                "city": "Москва",
                "address": "ул. Академика Королёва, д. 12",
                "emails": ["info@dna-technology.ru"],
                "phones": ["8 800 200-75-15"]
            },
            {
                "organization_id": 2,
                "name": "ООО ДНК-Технология",  # Дубликат
                "inn": "1901066506",
                "website": "https://dna-technology.ru",
                "emails": ["sales@dna-technology.ru"],
                "phones": []
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
                "city": None,  # Будет обогащен из организации
                "address": None,
                "confidence": 0.95
            },
            {
                "contact_id": 102,
                "name": None,  # Неценный контакт
                "organization_id": 2,
                "position": None,
                "email": "support@dna-technology.ru",
                "phones": [],
                "confidence": 0.5
            }
        ],
        "business_context": "Запрос коммерческого предложения",
        "summary": {
            "topic": "Коммерческое предложение",
            "communication_stage": "Коммерческие переговоры"
        },
        "key_points": ["Запрос КП на оборудование"],
        "commercial_offers": []
    }
    
    # Обработка
    processed_result = postprocessor.process_llm_response(test_llm_result)
    
    print("🎯 Результат постобработки:")
    print(f"Организации: {len(processed_result['organizations'])}")
    print(f"Контакты: {len(processed_result['contacts'])}")
    print(f"\n📊 Статистика: {postprocessor.get_processing_stats()}")
    
    # Детальный вывод
    print("\n🏢 Финальные организации:")
    for org in processed_result['organizations']:
        print(f"  ID {org['organization_id']}: {org['name']}")
    
    print("\n👤 Финальные контакты:")
    for contact in processed_result['contacts']:
        print(f"  {contact.get('name', 'Unknown')} (org_id: {contact.get('organization_id')})")