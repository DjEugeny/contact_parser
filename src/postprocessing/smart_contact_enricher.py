#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 Умный обогатитель контактов
Правильная логика обогащения с исключением публичных провайдеров и предотвращением перекрестного обогащения

Author: Contact Parser Team
Created: 2025-09-30
"""

import logging
import re
import socket
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional, Tuple, Iterable
import time

logger = logging.getLogger(__name__)


class SmartContactEnricher:
    """
    🧠 Умный обогатитель контактов
    
    Исправляет критические проблемы обогащения:
    1. Исключает публичные email провайдеры (mail.ru, yandex.ru, bk.ru, gmail.com)
    2. Предотвращает перекрестное обогащение между организациями
    3. Обогащает только корпоративные email соответствующими сайтами
    """
    
    def __init__(self):
        """Инициализация умного обогатителя"""
        self.logger = logging.getLogger(__name__)
        
        # Список публичных email провайдеров для исключения
        self.public_email_providers = {
            # Российские провайдеры
            'mail.ru', 'yandex.ru', 'ya.ru', 'yandex.com',
            'rambler.ru', 'inbox.ru', 'list.ru', 'bk.ru',
            
            # Международные провайдеры
            'gmail.com', 'yahoo.com', 'hotmail.com', 
            'outlook.com', 'live.com', 'aol.com',
            
            # Другие популярные провайдеры
            'protonmail.com', 'icloud.com', 'me.com'
        }
        
        # Статистика работы
        self.stats = {
            'contacts_processed': 0,
            'corporate_emails_found': 0,
            'public_providers_excluded': 0,
            'cross_organization_prevented': 0,
            'enrichments_applied': 0,
            'enrichments_skipped': 0,
            'errors': 0
        }
        
        self.logger.info("🧠 SmartContactEnricher инициализирован")
        self.logger.info(f"   Исключаем {len(self.public_email_providers)} публичных провайдеров")
    
    def enrich_contacts(self, contacts: List[Dict[str, Any]], organizations: Dict[int, Dict[str, Any]] = None, email_data: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Умное обогащение контактов
        
        Args:
            contacts: Список контактов для обогащения
            organizations: Словарь организаций {id: organization_data}
            email_data: Дополнительные данные письма
            
        Returns:
            List[Dict]: Обогащенные контакты
        """
        if not contacts:
            return []
        
        self.logger.info(f"🧠 Начинаем умное обогащение {len(contacts)} контактов")
        
        # Преобразуем organizations в нужный формат если нужно
        if organizations is None:
            organizations = {}
        
        enriched_contacts = []
        
        for i, contact in enumerate(contacts, 1):
            self.logger.info(f"📋 Контакт {i}/{len(contacts)}: {contact.get('name', 'Unknown')}")
            
            try:
                enriched_contact = self._enrich_single_contact(contact, organizations)
                enriched_contacts.append(enriched_contact)
                self.stats['contacts_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка при обогащении контакта {i}: {e}")
                self.stats['errors'] += 1
                # Возвращаем оригинальный контакт при ошибке
                enriched_contacts.append(contact)
        
        self._log_final_stats()
        return enriched_contacts
    
    def _enrich_single_contact(self, contact: Dict[str, Any], organizations: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Обогащение одного контакта
        
        Args:
            contact: Контакт для обогащения
            organizations: Словарь организаций
            
        Returns:
            Dict: Обогащенный контакт
        """
        enriched = contact.copy()

        org_id = contact.get('organization_id')
        org_data = organizations.get(org_id) if isinstance(organizations, dict) else {}
        org_emails = []
        org_website = None
        if isinstance(org_data, dict):
            org_emails = org_data.get('emails', []) or []
            org_website = org_data.get('website')

        # 1. Извлекаем email
        email = self._extract_contact_email(contact)
        if not email:
            fallback_email = self._select_fallback_email(org_emails)
            if fallback_email:
                email = fallback_email
                enriched['email'] = fallback_email
                enriched['email_source'] = 'organization_email_fallback'
                self.logger.info(f"   📧 Использую корпоративный email организации: {fallback_email}")

        if not email:
            website_candidate = self._normalize_website_url(org_website)
            if website_candidate:
                self.logger.info("   🌐 Используем сайт организации для контакта без email")
                enriched['website'] = website_candidate
                enriched['website_confidence'] = 0.6
                enriched['website_source'] = 'organization_profile'
                enriched['enrichment_skipped'] = False
                enriched['enrichment_reason'] = 'organization_website_used'
                enriched['smart_enrichment'] = {
                    'source_email': None,
                    'extracted_domain': self._normalize_domain(org_website) if org_website else None,
                    'website_found': website_candidate,
                    'enriched_at': time.time(),
                    'version': '1.0.0',
                    'source': 'organization_website'
                }
                self.stats['enrichments_applied'] += 1
                return enriched

            self.logger.info("   📧 Email не найден - пропускаем обогащение")
            enriched['enrichment_skipped'] = True
            enriched['enrichment_reason'] = 'no_email'
            self.stats['enrichments_skipped'] += 1
            return enriched

        self.logger.info(f"   📧 Email: {email}")
        
        # 2. Проверяем нужно ли обогащать
        should_enrich, reason = self._should_enrich_contact(contact, organizations)
        
        if not should_enrich:
            self.logger.info(f"   ⏭️  Обогащение пропущено: {reason}")
            enriched['enrichment_skipped'] = True
            enriched['enrichment_reason'] = reason
            self.stats['enrichments_skipped'] += 1
            return enriched
        
        # 3. Применяем обогащение
        domain = self._extract_domain(email)
        if domain:
            website_url = self._get_website_for_domain(domain)
            if not website_url and org_website:
                website_url = self._normalize_website_url(org_website)

            if website_url:
                enriched = self._apply_enrichment(enriched, website_url, domain, email, reason)
                self.stats['enrichments_applied'] += 1
                self.logger.info(f"   ✅ Обогащение применено: {email} → {website_url}")
            else:
                self.logger.info(f"   ❌ Веб-сайт не найден для домена: {domain}")
                enriched['enrichment_skipped'] = True
                enriched['enrichment_reason'] = f'website_not_found_for_{domain}'
                self.stats['enrichments_skipped'] += 1

        return enriched
    
    def _should_enrich_contact(self, contact: Dict[str, Any], organizations: Dict[int, Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Определяет нужно ли обогащать контакт
        
        Args:
            contact: Контакт
            organizations: Словарь организаций
            
        Returns:
            Tuple[bool, str]: (нужно ли обогащать, причина)
        """
        email = contact.get('email')
        if not email:
            return False, 'no_email'
        
        domain = self._extract_domain(email)
        if not domain:
            return False, 'invalid_domain'
        
        # 1. Исключаем публичные провайдеры
        if domain in self.public_email_providers:
            self.stats['public_providers_excluded'] += 1
            return False, f'public_provider_{domain}'
        
        self.stats['corporate_emails_found'] += 1
        
        # 2. Проверяем соответствие организации (если есть)
        org_id = contact.get('organization_id')
        if org_id and organizations and org_id in organizations:
            org = organizations[org_id]
            org_website = org.get('website', '')
            
            if org_website:
                # Нормализуем домен организации
                org_domain = self._normalize_domain(org_website)
                
                if org_domain and domain != org_domain:
                    self.stats['cross_organization_prevented'] += 1
                    return False, f'domain_mismatch_{domain}_vs_{org_domain}'
        
        return True, f'corporate_email_{domain}'
    
    def _extract_contact_email(self, contact: Dict[str, Any]) -> Optional[str]:
        """Извлечение email из контакта"""
        email = contact.get('email')
        if email and isinstance(email, str):
            return email.strip()
        return None
    
    def _extract_domain(self, email: str) -> Optional[str]:
        """Извлечение домена из email"""
        if not email or '@' not in email:
            return None
        
        try:
            domain = email.split('@')[1].strip().lower()
            # Убираем возможные лишние символы
            domain = re.sub(r'[<>]', '', domain)
            return domain if domain and '.' in domain else None
        except (IndexError, AttributeError):
            return None
    
    def _normalize_domain(self, website: str) -> Optional[str]:
        """Нормализация домена из URL веб-сайта"""
        if not website:
            return None
        
        # Убираем протокол и www
        domain = website.replace('https://', '').replace('http://', '').replace('www.', '')
        
        # Убираем путь
        if '/' in domain:
            domain = domain.split('/')[0]
        
        return domain.lower() if domain else None
    
    def _get_website_for_domain(self, domain: str) -> Optional[str]:
        """Возвращает рабочий URL сайта для корпоративного домена."""
        if not domain:
            return None

        normalized_domain = domain.lower().strip()
        if not normalized_domain or '.' not in normalized_domain:
            return None

        urls_to_check = [
            f"https://www.{normalized_domain}",
            f"https://{normalized_domain}",
            f"http://www.{normalized_domain}",
            f"http://{normalized_domain}"
        ]

        for url in urls_to_check:
            try:
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; SmartContactEnricher/1.0)'}
                )

                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.getcode() < 400:
                        return url

            except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout):
                continue
            except Exception:
                continue

            time.sleep(0.1)

        # Если прямой запрос не удался, возвращаем нормализованный HTTPS URL
        return self._normalize_website_url(normalized_domain)

    def _normalize_website_url(self, website: Optional[str]) -> Optional[str]:
        """Нормализует строку сайта до пригодного URL."""
        if not website:
            return None

        value = website.strip()
        if not value:
            return None

        if not value.startswith(('http://', 'https://')):
            value = value[1:] if value.startswith('/') else value
            if not value.startswith('www.') and '.' in value:
                value = f"www.{value}"
            value = f"https://{value}"

        return value

    def _select_fallback_email(self, organization_emails: Any) -> Optional[str]:
        """Возвращает корпоративный email организации для контакта без собственного адреса."""
        if not isinstance(organization_emails, list):
            return None

        corporate_emails: List[str] = []
        for item in organization_emails:
            if not isinstance(item, str):
                continue
            email = item.strip()
            if not email or '@' not in email:
                continue
            domain = self._extract_domain(email)
            if domain and domain not in self.public_email_providers:
                corporate_emails.append(email)

        if len(corporate_emails) == 1:
            return corporate_emails[0]

        return None

    def infer_website_from_emails(self, emails: Iterable[str]) -> Optional[str]:
        """Пытается определить сайт организации на основе корпоративных email."""
        if not emails:
            return None

        for email in emails:
            if not isinstance(email, str):
                continue
            domain = self._extract_domain(email)
            if not domain or domain in self.public_email_providers:
                continue
            website = self._get_website_for_domain(domain)
            if not website:
                website = self._normalize_website_url(domain)
            if website:
                return website

        return None
    
    def _apply_enrichment(self, contact: Dict[str, Any], website_url: str, domain: str, email: str, reason: str) -> Dict[str, Any]:
        """Применение обогащения к контакту"""
        enriched = contact.copy()
        
        enriched['website'] = website_url
        enriched['website_confidence'] = 0.9  # Высокая уверенность для корпоративных email
        enriched['website_source'] = 'smart_corporate_email'
        enriched['website_method'] = 'domain_extraction'
        enriched['enrichment_reason'] = reason
        enriched['enrichment_skipped'] = False
        
        # Диагностическая информация
        enriched['smart_enrichment'] = {
            'source_email': email,
            'extracted_domain': domain,
            'website_found': website_url,
            'enriched_at': time.time(),
            'version': '1.0.0'
        }
        
        return enriched
    
    def _log_final_stats(self):
        """Логирование финальной статистики"""
        self.logger.info("📊 Статистика умного обогащения:")
        for key, value in self.stats.items():
            self.logger.info(f"   {key}: {value}")
        
        # Вычисляем проценты
        if self.stats['contacts_processed'] > 0:
            enrichment_rate = (self.stats['enrichments_applied'] / self.stats['contacts_processed']) * 100
            skip_rate = (self.stats['enrichments_skipped'] / self.stats['contacts_processed']) * 100
            self.logger.info(f"   Процент обогащения: {enrichment_rate:.1f}%")
            self.logger.info(f"   Процент пропусков: {skip_rate:.1f}%")
        
        if self.stats['corporate_emails_found'] > 0:
            corporate_success_rate = (self.stats['enrichments_applied'] / self.stats['corporate_emails_found']) * 100
            self.logger.info(f"   Успешность корпоративных email: {corporate_success_rate:.1f}%")
    
    def get_enrichment_stats(self) -> Dict[str, Any]:
        """Получение статистики обогащения"""
        return {
            'stats': self.stats.copy(),
            'public_providers_count': len(self.public_email_providers),
            'enricher_version': '1.0.0',
            'enricher_type': 'smart'
        }


# Пример использования
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Тестовые данные
    test_contacts = [
        {
            'contact_id': 1,
            'name': 'Корпоративный контакт',
            'email': 'sklad@centerld.ru',
            'organization_id': 1
        },
        {
            'contact_id': 2,
            'name': 'Публичный провайдер',
            'email': '086975@bk.ru',
            'organization_id': 2
        },
        {
            'contact_id': 3,
            'name': 'Перекрестное обогащение',
            'email': 'medic.81@mail.ru',
            'organization_id': 2
        }
    ]
    
    test_organizations = {
        1: {'name': 'Центр ЛД', 'website': 'centerld.ru'},
        2: {'name': 'Другая организация', 'website': 'other.ru'}
    }
    
    # Создаем умный обогатитель
    smart_enricher = SmartContactEnricher()
    
    # Тестируем
    print("🚀 Тестирование SmartContactEnricher")
    enriched = smart_enricher.enrich_contacts(test_contacts, test_organizations)
    
    print(f"\n📋 Результаты:")
    for contact in enriched:
        name = contact.get('name', 'Unknown')
        email = contact.get('email', 'no email')
        website = contact.get('website', 'не обогащен')
        reason = contact.get('enrichment_reason', 'unknown')
        
        status = "✅" if website != 'не обогащен' else "⏭️ "
        print(f"{status} {name}: {email} → {website} ({reason})")
    
    print(f"\n📊 Статистика:")
    stats = smart_enricher.get_enrichment_stats()
    for key, value in stats['stats'].items():
        print(f"  {key}: {value}")
