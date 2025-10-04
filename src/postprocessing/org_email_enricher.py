#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль обогащения организаций email-адресами
Реализует TASK-007B для извлечения, классификации и добавления email-адресов организаций

Author: Contact Parser Team  
Created: 2025-10-04
"""

import re
import logging
from typing import Dict, List, Any, Set, Optional, Tuple
from urllib.parse import urlparse
from pathlib import Path

logger = logging.getLogger(__name__)

# Конфигурация для классификации email-адресов
ROLE_EMAIL_PREFIXES = {
    'info', 'mail', 'sales', 'office', 'contact', 'support', 'admin', 'order',
    'service', 'pr', 'hr', 'marketing', 'accounting', 'billing', 'tender',
    'export', 'import', 'help', 'it', 'hello', 'welcome', 'general', 'noreply',
    'no-reply', 'reception', 'secretary', 'manager', 'director', 'ceo',
    'commercial', 'zakaz', 'orders', 'buh', 'finance', 'logistics'
}

PERSONAL_EMAIL_INDICATORS = {
    # Персональные домены
    'personal_domains': {
        'gmail.com', 'yahoo.com', 'yahoo.ru', 'mail.ru', 'yandex.ru', 
        'yandex.com', 'hotmail.com', 'outlook.com', 'rambler.ru', 'bk.ru',
        'inbox.ru', 'list.ru', 'internet.ru'
    },
    # Паттерны персональных локальных частей
    'personal_patterns': [
        r'^[a-z]+\.[a-z]+$',  # firstname.lastname
        r'^[a-z]+_[a-z]+$',   # firstname_lastname  
        r'^[a-z]\.[a-z]+$',   # f.lastname
        r'^[a-z]+\.[a-z]$',   # firstname.l
        r'^\d+$',             # только цифры
        r'^[a-z]+\d+$',       # имя+цифры
        r'^\d+[a-z]+$',       # цифры+имя
    ]
}

# Домены нашей компании (не должны попадать в сторонние организации)
OUR_DOMAINS = {'dna-technology.ru'}


class OrganizationEmailEnricher:
    """Обогащение организаций email-адресами из заголовков, подписей и вложений"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'organizations_processed': 0,
            'emails_added': 0,
            'emails_skipped': 0,
            'from_headers': 0,
            'from_signature': 0, 
            'from_attachments': 0
        }
        
    def enrich_organizations_emails(
        self,
        organizations: Dict[int, Dict[str, Any]],
        email_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Основная функция обогащения организаций email-адресами
        
        Args:
            organizations: Словарь организаций {org_id: org_data}
            email_data: Данные письма с заголовками и содержимым
            
        Returns:
            Dict: Метаданные обогащения для postprocessing_metadata.org_email_enrichment
        """
        if not organizations:
            return {}
            
        self.logger.info(f"🏢 Начинаем обогащение {len(organizations)} организаций email-адресами")
        
        # Отладочная информация
        self.logger.debug(f"Organizations type: {type(organizations)}")
        self.logger.debug(f"Organizations keys: {list(organizations.keys()) if isinstance(organizations, dict) else 'not dict'}")
        
        enrichment_metadata = {}
        
        for org_id, org_data in organizations.items():
            self.logger.debug(f"Processing org {org_id}: type={type(org_data)}, data={org_data}")
            
            # Защита от неправильного типа данных
            if not isinstance(org_data, dict):
                self.logger.warning(f"Organization {org_id} is not a dict (type: {type(org_data)}), skipping")
                continue
            
            gid = org_data.get('gid')
            if not gid:
                self.logger.warning(f"Organization {org_id} has no GID, skipping email enrichment")
                continue
                
            # Извлекаем кандидатов email из разных источников
            candidates = self._collect_email_candidates(org_data, email_data)
            
            # Классифицируем и фильтруем
            classified = self._classify_emails(candidates, org_data)
            
            # Добавляем в организацию
            added_emails = self._add_emails_to_organization(org_data, classified['role_emails'])
            
            # Сохраняем метаданные
            if added_emails or classified['skipped_emails']:
                enrichment_metadata[gid] = {
                    'added': added_emails,
                    'skipped': classified['skipped_emails'],
                    'source': classified['sources']
                }
                
            self.stats['organizations_processed'] += 1
            self.stats['emails_added'] += len(added_emails)
            self.stats['emails_skipped'] += len(classified['skipped_emails'])
        
        self.logger.info(
            f"✅ Обогащение завершено. Добавлено {self.stats['emails_added']} email, "
            f"пропущено {self.stats['emails_skipped']}"
        )
        
        return enrichment_metadata
    
    def _collect_email_candidates(
        self, 
        org_data: Dict[str, Any], 
        email_data: Dict[str, Any]
    ) -> List[Tuple[str, str]]:
        """
        Собирает кандидатов email из всех источников
        
        Returns:
            List[Tuple[str, str]]: Список (email, source)
        """
        candidates = []
        
        # 1. Извлекаем из заголовков письма
        header_emails = self._extract_emails_from_headers(email_data)
        candidates.extend([(email, 'headers') for email in header_emails])
        self.stats['from_headers'] += len(header_emails)
        
        # 2. Извлекаем из подписи письма  
        signature_emails = self._extract_emails_from_signature(email_data)
        candidates.extend([(email, 'signature') for email in signature_emails])
        self.stats['from_signature'] += len(signature_emails)
        
        # 3. Извлекаем из OCR-текста вложений
        attachment_emails = self._extract_emails_from_attachments(email_data, org_data)
        candidates.extend([(email, 'attachments') for email in attachment_emails])
        self.stats['from_attachments'] += len(attachment_emails)
        
        return candidates
    
    def _extract_emails_from_headers(self, email_data: Dict[str, Any]) -> List[str]:
        """Извлекает email из заголовков письма (From, To, Cc, Reply-To)"""
        emails = []
        headers = email_data.get('headers', {})
        
        # Список заголовков для проверки
        header_fields = ['from', 'to', 'cc', 'reply-to', 'sender']
        
        for field in header_fields:
            header_value = headers.get(field, '')
            if header_value:
                found_emails = self._parse_email_addresses(header_value)
                emails.extend(found_emails)
        
        # Дедуплицируем с сохранением порядка
        seen = set()
        unique_emails = []
        for email in emails:
            email_lower = email.lower()
            if email_lower not in seen:
                seen.add(email_lower)
                unique_emails.append(email)
                
        return unique_emails
    
    def _extract_emails_from_signature(self, email_data: Dict[str, Any]) -> List[str]:
        """Извлекает email из блока подписи письма"""
        emails = []
        
        # Ищем в body и plain_text
        text_sources = []
        if email_data.get('body'):
            text_sources.append(email_data['body'])
        if email_data.get('plain_text'):
            text_sources.append(email_data['plain_text'])
            
        for text in text_sources:
            if text:
                found_emails = self._parse_email_addresses(text)
                emails.extend(found_emails)
        
        # Дедуплицируем
        return list(set(email.lower() for email in emails))
    
    def _extract_emails_from_attachments(
        self, 
        email_data: Dict[str, Any], 
        org_data: Dict[str, Any]
    ) -> List[str]:
        """Извлекает email из OCR-текста вложений"""
        emails = []
        
        attachments = email_data.get('attachments', [])
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
                
            # Ищем OCR-текст во вложении
            ocr_text = attachment.get('ocr_text', '')
            if ocr_text:
                found_emails = self._parse_email_addresses(ocr_text)
                # Фильтруем только те, что связаны с организацией
                relevant_emails = self._filter_attachment_emails(found_emails, org_data)
                emails.extend(relevant_emails)
        
        return list(set(email.lower() for email in emails))
    
    def _parse_email_addresses(self, text: str) -> List[str]:
        """Парсит email адреса из текста с помощью регулярки"""
        if not text:
            return []
            
        # Регулярка для email адресов
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        matches = re.findall(email_pattern, text, re.IGNORECASE)
        
        # Очищаем и валидируем
        valid_emails = []
        for email in matches:
            email = email.strip().lower()
            if self._is_valid_email_format(email):
                valid_emails.append(email)
                
        return valid_emails
    
    def _is_valid_email_format(self, email: str) -> bool:
        """Базовая валидация формата email"""
        if not email or '@' not in email:
            return False
            
        local, domain = email.rsplit('@', 1)
        
        # Проверяем локальную часть
        if not local or len(local) > 64:
            return False
            
        # Проверяем домен
        if not domain or len(domain) > 255 or not '.' in domain:
            return False
            
        return True
    
    def _filter_attachment_emails(
        self, 
        emails: List[str], 
        org_data: Dict[str, Any]
    ) -> List[str]:
        """Фильтрует email из вложений, оставляя только релевантные для организации"""
        if not emails:
            return []
            
        org_name = org_data.get('name', '').lower()
        org_domain = self._extract_organization_domain(org_data)
        
        relevant = []
        for email in emails:
            email_domain = self._extract_domain_from_email(email)
            
            # Проверяем связь с организацией
            if org_domain and email_domain == org_domain:
                relevant.append(email)
            elif org_name and self._is_email_near_org_name(email, org_name):
                relevant.append(email)
                
        return relevant
    
    def _classify_emails(
        self, 
        candidates: List[Tuple[str, str]], 
        org_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Классифицирует email кандидатов на роль/общие vs персональные
        
        Returns:
            Dict с ключами: role_emails, skipped_emails, sources
        """
        role_emails = []
        skipped_emails = []
        sources = {}
        
        org_domain = self._extract_organization_domain(org_data)
        
        for email, source in candidates:
            email_lower = email.lower()
            
            # Защита от добавления наших доменов в сторонние организации
            if self._is_our_domain_email(email_lower):
                skipped_emails.append(email_lower)
                continue
                
            # Определяем принадлежность к организации
            if org_domain:
                email_domain = self._extract_domain_from_email(email_lower)
                if email_domain != org_domain:
                    skipped_emails.append(email_lower)
                    continue
            
            # Классифицируем тип email
            email_type = self._classify_email_type(email_lower)
            
            if email_type == 'role':
                role_emails.append(email_lower)
                sources[email_lower] = source
            else:
                skipped_emails.append(email_lower)
        
        return {
            'role_emails': role_emails,
            'skipped_emails': skipped_emails,
            'sources': sources
        }
    
    def _classify_email_type(self, email: str) -> str:
        """
        Классифицирует email как 'role' (организационный) или 'personal' (персональный)
        """
        local_part = email.split('@')[0]
        domain = self._extract_domain_from_email(email)
        
        # Проверяем персональные домены
        if domain in PERSONAL_EMAIL_INDICATORS['personal_domains']:
            return 'personal'
        
        # Проверяем роль/общие префиксы
        if local_part in ROLE_EMAIL_PREFIXES:
            return 'role'
            
        # Проверяем паттерны персональных адресов
        for pattern in PERSONAL_EMAIL_INDICATORS['personal_patterns']:
            if re.match(pattern, local_part, re.IGNORECASE):
                return 'personal'
        
        # По умолчанию считаем персональным (безопасный подход)
        return 'personal'
    
    def _add_emails_to_organization(
        self, 
        org_data: Dict[str, Any], 
        role_emails: List[str]
    ) -> List[str]:
        """Добавляет role email в organizations[].emails с дедупликацией"""
        if not role_emails:
            return []
            
        current_emails = org_data.get('emails', [])
        if not isinstance(current_emails, list):
            current_emails = []
            
        # Приводим к lowercase для дедупликации
        existing_lower = {email.lower() for email in current_emails if email}
        
        added = []
        for email in role_emails:
            if email not in existing_lower:
                current_emails.append(email)
                existing_lower.add(email)
                added.append(email)
        
        org_data['emails'] = current_emails
        return added
    
    def _extract_organization_domain(self, org_data: Dict[str, Any]) -> Optional[str]:
        """Извлекает домен организации из website или существующих emails"""
        # Сначала пробуем website
        website = org_data.get('website', '')
        if website:
            domain = self._extract_domain_from_url(website)
            if domain:
                return domain
        
        # Если нет website, берем домен из первого email
        emails = org_data.get('emails', [])
        if emails and isinstance(emails, list):
            for email in emails:
                if email and '@' in str(email):
                    return self._extract_domain_from_email(str(email))
        
        return None
    
    def _extract_domain_from_email(self, email: str) -> str:
        """Извлекает домен из email адреса"""
        if not email or '@' not in email:
            return ''
        return email.split('@')[-1].lower()
    
    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """Извлекает домен из URL"""
        if not url:
            return None
            
        # Добавляем схему если её нет
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Убираем www. если есть
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain if domain else None
        except:
            return None
    
    def _extract_e2ld(self, domain: str) -> str:
        """Извлекает effective 2nd level domain (e2LD)"""
        if not domain:
            return ''
        
        parts = domain.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
        return domain
    
    def _is_our_domain_email(self, email: str) -> bool:
        """Проверяет, относится ли email к нашим доменам"""
        domain = self._extract_domain_from_email(email)
        return domain in OUR_DOMAINS
    
    def _is_email_near_org_name(self, email: str, org_name: str) -> bool:
        """Проверяет, упоминается ли email рядом с названием организации (для вложений)"""
        # Упрощенная проверка - можно усложнить при необходимости
        domain = self._extract_domain_from_email(email)
        if not domain:
            return False
            
        # Проверяем по ключевым словам из названия организации
        org_words = re.findall(r'\w+', org_name.lower())
        domain_words = re.findall(r'\w+', domain.lower())
        
        # Ищем пересечения
        common_words = set(org_words) & set(domain_words)
        return len(common_words) > 0
    
    def get_stats(self) -> Dict[str, int]:
        """Возвращает статистику обогащения"""
        return self.stats.copy()