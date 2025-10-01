#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Дедупликатор организаций с глобальными ID
Реализует алгоритм из мини-ТЗ п.3.a для объединения организаций

Author: Contact Parser Team
Created: 2025-09-13
"""

import logging
from typing import Dict, List, Any, Set, Optional
from difflib import SequenceMatcher

from .text_normalizer import normalize_first_word_only
from .email_classifier import MailboxType, classify_mailbox

logger = logging.getLogger(__name__)


class OrganizationDeduplicator:
    """Дедупликатор организаций с системой глобальных ID
    
    Реализует алгоритм согласно мини-ТЗ:
    1. Поиск дубликатов по названию, ИНН, сайту
    2. Объединение данных (emails, phones, address)
    3. Назначение глобальных organization_id
    4. Создание маппинга локальных -> глобальных ID
    """
    
    def __init__(self, initial_organizations: Dict[int, Dict[str, Any]] = None):
        self.global_organizations: Dict[int, Dict[str, Any]] = {}
        self.next_global_id = 1
        self.name_similarity_threshold = 0.85
        self.logger = logging.getLogger(__name__)
        self._stats = {
            'processed': 0,
            'created': 0,
            'merged': 0
        }
        # Используем простую нормализацию: только первое слово заглавное

        self.email_classifier_cfg: Dict[str, Any] = {}
        self.corporate_domains: Set[str] = set()
        self.allowed_org_mail_types: Set[MailboxType] = {
            MailboxType.SHARED_ORG,
            MailboxType.DEPARTMENT,
            MailboxType.GROUP_ALIAS,
            MailboxType.TECHNICAL,
        }
        self.email_classifier_enabled = False

        if initial_organizations:
            self.load_existing_organizations(initial_organizations)

    def load_existing_organizations(self, organizations: Dict[int, Dict[str, Any]]) -> None:
        """Загрузка существующих организаций в глобальный справочник"""
        for org_id, payload in organizations.items():
            if not isinstance(payload, dict):
                continue
            numeric_id = int(org_id)
            normalized_payload = payload.copy()
            original_name = normalized_payload.get('name', '')
            display_name = ''
            if original_name:
                display_name = normalize_first_word_only(original_name)
                normalized_payload['name'] = display_name
            normalized_payload['__match_key__'] = self._build_matching_key(display_name or original_name)
            if isinstance(normalized_payload.get('emails'), list):
                normalized_payload['emails'] = self._filter_emails(normalized_payload.get('emails', []))
            self.global_organizations[numeric_id] = normalized_payload
        if self.global_organizations:
            self.next_global_id = max(self.global_organizations.keys()) + 1

    def get_global_organizations(self) -> Dict[int, Dict[str, Any]]:
        """Возвращает текущий словарь глобальных организаций"""
        return {
            org_id: self._strip_internal_fields(org)
            for org_id, org in self.global_organizations.items()
        }
    
    def reset_state(self) -> None:
        """Очистка состояния дедупликатора для обработки нового письма"""
        self.global_organizations = {}
        self.next_global_id = 1
        self._stats = {
            'processed': 0,
            'created': 0,
            'merged': 0
        }
        self.logger.info("🔄 Состояние OrganizationDeduplicator очищено")

    def configure_email_classifier(
        self,
        cfg: Dict[str, Any],
        corp_domains: Set[str],
        allowed_types: Optional[Set[MailboxType]] = None,
    ) -> None:
        self.email_classifier_cfg = cfg or {}
        self.corporate_domains = {str(domain).lower() for domain in (corp_domains or set())}
        if allowed_types:
            self.allowed_org_mail_types = allowed_types
        self.email_classifier_enabled = True

    def _filter_emails(self, emails: List[Any]) -> List[str]:
        if not emails:
            return []

        normalized: List[str] = []
        seen: Set[str] = set()

        for item in emails:
            email_str = str(item or '').strip()
            if not email_str:
                continue
            email_lower = email_str.lower()
            if email_lower in seen:
                continue

            if self.email_classifier_enabled:
                mailbox_type = classify_mailbox(
                    email_str,
                    None,
                    self.corporate_domains,
                    self.email_classifier_cfg,
                )
                if mailbox_type not in self.allowed_org_mail_types:
                    continue

            normalized.append(email_str)
            seen.add(email_lower)

        return normalized

    def process_organizations(self, llm_organizations: List[Dict[str, Any]]) -> Dict[int, int]:
        """Обработка организаций из LLM ответа
        
        Args:
            llm_organizations: Список организаций из LLM
            
        Returns:
            Dict[int, int]: Маппинг локальных organization_id -> глобальных
        """
        if not llm_organizations:
            return {}
            
        self.logger.info(f"🏢 Обработка {len(llm_organizations)} организаций")
        
        local_to_global_mapping = {}
        
        for org in llm_organizations:
            local_id = org.get('organization_id')
            if local_id is None:
                self.logger.warning(f"Организация без organization_id: {org.get('name', 'Unknown')}")
                continue
                
            global_id = self._find_or_create_organization(org)
            local_to_global_mapping[local_id] = global_id
            self._stats['processed'] += 1

        self.logger.info(f"✅ Создан маппинг для {len(local_to_global_mapping)} организаций")
        return local_to_global_mapping
    
    def _find_or_create_organization(self, org: Dict[str, Any]) -> int:
        """Поиск существующей организации или создание новой
        
        Args:
            org: Данные организации из LLM
            
        Returns:
            int: Глобальный organization_id
        """
        prepared_org = self._prepare_organization_payload(org)

        # Поиск дубликата среди существующих организаций
        duplicate_id = self._find_duplicate_organization(prepared_org)

        if duplicate_id:
            # Объединяем данные с существующей организацией
            self._merge_organization_data(duplicate_id, prepared_org)
            self._stats['merged'] += 1
            return duplicate_id
        else:
            # Создаем новую организацию
            created_id = self._create_new_organization(prepared_org)
            self._stats['created'] += 1
            return created_id
    
    def _find_duplicate_organization(self, org: Dict[str, Any]) -> int:
        """Поиск дубликата организации
        
        Args:
            org: Данные организации для поиска
            
        Returns:
            int: ID найденного дубликата или None
        """
        raw_name = org.get('name', '') or ''
        display_name = normalize_first_word_only(raw_name) if raw_name else ''
        org_match_key = self._build_matching_key(display_name or raw_name)
        org_inn = org.get('inn')
        org_website = self._normalize_website(org.get('website', ''))

        for global_id, existing_org in self.global_organizations.items():
            # Проверка по ИНН (высший приоритет)
            if org_inn and existing_org.get('inn') == org_inn:
                self.logger.debug(f"Найден дубликат по ИНН: {org_inn}")
                return global_id
            
            # Проверка по сайту
            existing_website = self._normalize_website(existing_org.get('website', ''))
            if org_website and existing_website and org_website == existing_website:
                self.logger.debug(f"Найден дубликат по сайту: {org_website}")
                return global_id
            
            # Проверка по названию (fuzzy matching)
            existing_match_key = existing_org.get('__match_key__')
            if existing_match_key is None:
                existing_match_key = self._build_matching_key(existing_org.get('name', ''))
                existing_org['__match_key__'] = existing_match_key
            if org_match_key and existing_match_key:
                similarity = SequenceMatcher(None, org_match_key, existing_match_key).ratio()
                if similarity >= self.name_similarity_threshold:
                    self.logger.debug(
                        "Найден дубликат по названию: %s (%.2f)",
                        display_name or raw_name,
                        similarity
                    )
                    return global_id

        return None
    
    def _merge_organization_data(self, global_id: int, new_org: Dict[str, Any]) -> None:
        """Объединение данных организации

        Args:
            global_id: ID существующей организации
            new_org: Новые данные для объединения
        """
        existing_org = self.global_organizations[global_id]

        # Объединяем emails
        existing_emails = set(existing_org.get('emails', []))
        new_emails = set(new_org.get('emails', []))
        merged_emails = list(existing_emails | new_emails)
        if merged_emails:
            existing_org['emails'] = self._filter_emails(merged_emails)

        # Объединяем телефоны
        existing_phones = set(existing_org.get('phones', []))
        new_phones = set(new_org.get('phones', []))
        merged_phones = list(existing_phones | new_phones)
        if merged_phones:
            existing_org['phones'] = merged_phones

        # Обновляем название
        normalized_name = new_org.get('name')
        if normalized_name:
            self._update_organization_name(existing_org, normalized_name)

        # Обновляем поля, если они отсутствуют или новые данные более полные
        self._update_field_if_better(existing_org, new_org, 'inn')
        self._update_field_if_better(existing_org, new_org, 'website')
        self._update_field_if_better(existing_org, new_org, 'city')
        self._update_field_if_better(existing_org, new_org, 'address')

        self.logger.debug(f"Объединены данные организации ID {global_id}")
    
    def _create_new_organization(self, org: Dict[str, Any]) -> int:
        """Создание новой организации
        
        Args:
            org: Данные организации
            
        Returns:
            int: Новый глобальный ID
        """
        global_id = self.next_global_id
        while global_id in self.global_organizations:
            global_id += 1
        self.next_global_id = global_id + 1
        
        # Создаем копию организации с глобальным ID
        new_org = org.copy()
        new_org['organization_id'] = global_id

        # Нормализуем массивы
        if 'emails' not in new_org:
            new_org['emails'] = []
        if 'phones' not in new_org:
            new_org['phones'] = []

        if isinstance(new_org.get('emails'), list):
            new_org['emails'] = self._filter_emails(new_org['emails'])

        # Приводим название к нормализованному виду и сохраняем match key
        normalized_name = new_org.get('name', '')
        if normalized_name:
            formatted_name = normalize_first_word_only(normalized_name)
            new_org['name'] = formatted_name
            new_org['__match_key__'] = self._build_matching_key(formatted_name)
        else:
            new_org['__match_key__'] = ''

        self.global_organizations[global_id] = new_org

        self.logger.debug(f"Создана новая организация ID {global_id}: {org.get('name', 'Unknown')}")
        return global_id
    
    def _update_field_if_better(self, existing: Dict[str, Any], new: Dict[str, Any], field: str) -> None:
        """Обновление поля, если новое значение лучше
        
        Args:
            existing: Существующие данные
            new: Новые данные
            field: Название поля
        """
        existing_value = existing.get(field)
        new_value = new.get(field)
        
        # Если существующего значения нет, берем новое
        if not existing_value and new_value:
            existing[field] = new_value
        # Если новое значение длиннее (более информативное)
        elif new_value and len(str(new_value)) > len(str(existing_value or '')):
            existing[field] = new_value

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику работы дедупликатора"""
        return self._stats.copy()
    
    def _normalize_organization_name(self, name: str) -> str:
        """Нормализация названия организации
        
        Args:
            name: Исходное название
            
        Returns:
            str: Нормализованное название
        """
        if not name:
            return ''

        display_name = normalize_first_word_only(name)
        return self._build_matching_key(display_name)

    def _build_matching_key(self, name: str) -> str:
        """🔑 Создание ключа для сравнения названий организаций"""
        if not name:
            return ''

        normalized = ' '.join(name.strip().split()).lower()

        # Убираем общие сокращения и формы собственности
        common_abbreviations = [
            'ооо', 'зао', 'оао', 'ип', 'пао', 'ао', 'тоо', 'лтд', 'ltd', 
            'llc', 'inc', '«', '»', '"', "'", 'общество', 'с', 'ограниченной', 
            'ответственностью', 'закрытое', 'акционерное', 'открытое'
        ]

        words = normalized.split()
        filtered_words = []
        for word in words:
            clean_word = word.strip('\"\'«»()[]{}<>')
            if not clean_word or clean_word in common_abbreviations:
                continue
            filtered_words.append(clean_word)

        return ' '.join(filtered_words)

    def _prepare_organization_payload(self, org: Dict[str, Any]) -> Dict[str, Any]:
        """🧹 Подготовка данных организации перед обработкой"""
        prepared = org.copy()
        raw_name = prepared.get('name', '') or ''
        if raw_name:
            formatted_name = normalize_first_word_only(raw_name)
            prepared['name'] = formatted_name
            prepared['__match_key__'] = self._build_matching_key(formatted_name)
        else:
            prepared['__match_key__'] = ''

        if 'emails' in prepared and isinstance(prepared['emails'], list):
            prepared['emails'] = self._filter_emails(prepared['emails'])
        return prepared

    def _update_organization_name(self, existing_org: Dict[str, Any], new_name: str) -> None:
        """🆕 Обновление названия организации с сохранением регистра"""
        if not new_name:
            return

        current_name = existing_org.get('name')
        if not current_name:
            existing_org['name'] = new_name
            existing_org['__match_key__'] = self._build_matching_key(new_name)
            return

        # Если новое название длиннее или содержит больше слов, считаем его более информативным
        current_len = len(current_name or '')
        new_len = len(new_name)
        if new_len > current_len:
            existing_org['name'] = new_name

        # В любом случае пересчитываем ключ для сравнения
        existing_org['__match_key__'] = self._build_matching_key(existing_org.get('name', ''))

    def _strip_internal_fields(self, organization: Dict[str, Any]) -> Dict[str, Any]:
        """🛡️ Удаление служебных полей перед возвратом данных"""
        if not organization:
            return {}
        sanitized = organization.copy()
        sanitized.pop('__match_key__', None)
        return sanitized
    
    def _normalize_website(self, website: str) -> str:
        """Нормализация сайта
        
        Args:
            website: Исходный URL
            
        Returns:
            str: Нормализованный URL
        """
        if not website:
            return ''
        
        # Убираем протокол и www
        normalized = website.lower().strip()
        normalized = normalized.replace('https://', '').replace('http://', '')
        normalized = normalized.replace('www.', '')
        
        # Убираем trailing slash
        normalized = normalized.rstrip('/')
        
        return normalized
    
    def get_all_organizations(self) -> List[Dict[str, Any]]:
        """Получение всех организаций
        
        Returns:
            List[Dict]: Список всех организаций
        """
        return [self._strip_internal_fields(org) for org in self.global_organizations.values()]
    
    def get_organization_by_id(self, global_id: int) -> Dict[str, Any]:
        """Получение организации по ID
        
        Args:
            global_id: Глобальный ID организации
            
        Returns:
            Dict: Данные организации или None
        """
        organization = self.global_organizations.get(global_id)
        if not organization:
            return None
        return self._strip_internal_fields(organization)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики дедупликации
        
        Returns:
            Dict: Статистика работы
        """
        return {
            'total_organizations': len(self.global_organizations),
            'next_global_id': self.next_global_id,
            'organizations_with_inn': sum(1 for org in self.global_organizations.values() if org.get('inn')),
            'organizations_with_website': sum(1 for org in self.global_organizations.values() if org.get('website')),
            'organizations_with_emails': sum(1 for org in self.global_organizations.values() if org.get('emails')),
            'organizations_with_phones': sum(1 for org in self.global_organizations.values() if org.get('phones'))
        }


# Пример использования
if __name__ == "__main__":
    deduplicator = OrganizationDeduplicator()
    
    # Тестовые организации
    test_organizations = [
        {
            "organization_id": 1,
            "name": "ДНК-Технология",
            "inn": "1901066506",
            "website": "dna-technology.ru",
            "city": "Москва",
            "emails": ["info@dna-technology.ru"],
            "phones": ["8 800 200-75-15"]
        },
        {
            "organization_id": 2,
            "name": "ООО ДНК-Технология",
            "inn": "1901066506",
            "website": "https://dna-technology.ru",
            "city": "Москва",
            "emails": ["sales@dna-technology.ru"],
            "phones": []
        }
    ]
    
    # Обработка
    mapping = deduplicator.process_organizations(test_organizations)
    print(f"Маппинг: {mapping}")
    print(f"Статистика: {deduplicator.get_stats()}")
    print(f"Организации: {deduplicator.get_all_organizations()}")
