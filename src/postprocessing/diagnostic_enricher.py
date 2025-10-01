#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Диагностический инструмент для ContactEnricher
Детальное логирование и анализ процесса обогащения данных

Author: Contact Parser Team
Created: 2025-09-30
"""

import logging
import re
import socket
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import time

logger = logging.getLogger(__name__)


class DiagnosticContactEnricher:
    """
    🔍 Диагностический обертка для ContactEnricher
    
    Добавляет детальное логирование каждого этапа обогащения:
    - Извлечение домена из email
    - Проверка существования веб-сайта
    - Валидация результатов
    """
    
    def __init__(self, original_enricher=None):
        """
        Инициализация диагностического обогатителя
        
        Args:
            original_enricher: Оригинальный ContactEnricher (если есть)
        """
        self.original_enricher = original_enricher
        self.logger = logging.getLogger(__name__)
        
        # Статистика диагностики
        self.stats = {
            'contacts_processed': 0,
            'emails_found': 0,
            'domains_extracted': 0,
            'websites_validated': 0,
            'websites_found': 0,
            'enrichment_applied': 0,
            'errors': 0
        }
        
        self.logger.info("🔍 DiagnosticContactEnricher инициализирован")
    
    def diagnose_enrichment(self, contacts: List[Dict[str, Any]], email_data: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Диагностика процесса обогащения контактов
        
        Args:
            contacts: Список контактов для обогащения
            email_data: Дополнительные данные письма
            
        Returns:
            List[Dict]: Обогащенные контакты с диагностической информацией
        """
        self.logger.info(f"🔍 Начинаем диагностику обогащения для {len(contacts)} контактов")
        
        enriched_contacts = []
        
        for i, contact in enumerate(contacts, 1):
            self.logger.info(f"📋 Контакт {i}/{len(contacts)}: {contact.get('name', 'Unknown')}")
            
            try:
                enriched_contact = self._diagnose_single_contact(contact, email_data)
                enriched_contacts.append(enriched_contact)
                self.stats['contacts_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка при диагностике контакта {i}: {e}")
                self.stats['errors'] += 1
                # Возвращаем оригинальный контакт при ошибке
                enriched_contacts.append(contact)
        
        self._log_final_stats()
        return enriched_contacts
    
    def _diagnose_single_contact(self, contact: Dict[str, Any], email_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Диагностика обогащения одного контакта
        
        Args:
            contact: Контакт для диагностики
            email_data: Данные письма
            
        Returns:
            Dict: Обогащенный контакт
        """
        enriched = contact.copy()
        
        # 1. Поиск email в контакте
        email = self._extract_contact_email(contact)
        if not email:
            self.logger.info("   📧 Email не найден в контакте")
            return enriched
        
        self.logger.info(f"   📧 Найден email: {email}")
        self.stats['emails_found'] += 1
        
        # 2. Извлечение домена
        domain = self._extract_domain(email)
        if not domain:
            self.logger.warning(f"   🌐 Не удалось извлечь домен из {email}")
            return enriched
        
        self.logger.info(f"   🌐 Извлечен домен: {domain}")
        self.stats['domains_extracted'] += 1
        
        # 3. Проверка существования веб-сайта
        website_exists, website_url = self._check_website_exists(domain)
        self.stats['websites_validated'] += 1
        
        if website_exists:
            self.logger.info(f"   ✅ Веб-сайт найден: {website_url}")
            self.stats['websites_found'] += 1
            
            # 4. Применение обогащения
            enriched = self._apply_website_enrichment(enriched, website_url, domain, email)
            self.stats['enrichment_applied'] += 1
            
        else:
            self.logger.info(f"   ❌ Веб-сайт не найден для домена: {domain}")
        
        return enriched
    
    def _extract_contact_email(self, contact: Dict[str, Any]) -> Optional[str]:
        """
        Извлечение email из контакта
        
        Args:
            contact: Контакт
            
        Returns:
            Optional[str]: Email или None
        """
        # Проверяем поле email
        if contact.get('email'):
            return contact['email'].strip()
        
        # Проверяем другие возможные поля
        for field in ['email_address', 'mail', 'e_mail']:
            if contact.get(field):
                return contact[field].strip()
        
        return None
    
    def _extract_domain(self, email: str) -> Optional[str]:
        """
        Извлечение домена из email адреса
        
        Args:
            email: Email адрес
            
        Returns:
            Optional[str]: Домен или None
        """
        if not email or '@' not in email:
            return None
        
        try:
            domain = email.split('@')[1].strip().lower()
            
            # Базовая валидация домена
            if not domain or '.' not in domain:
                return None
            
            # Убираем возможные лишние символы
            domain = re.sub(r'[<>]', '', domain)
            
            return domain
            
        except (IndexError, AttributeError):
            return None
    
    def _check_website_exists(self, domain: str) -> tuple[bool, Optional[str]]:
        """
        Проверка существования веб-сайта для домена
        
        Args:
            domain: Доменное имя
            
        Returns:
            tuple: (существует ли сайт, URL сайта)
        """
        if not domain:
            return False, None
        
        # Сначала проверяем DNS резолюцию
        try:
            socket.gethostbyname(domain)
            self.logger.debug(f"      ✅ DNS резолюция успешна для {domain}")
        except socket.gaierror:
            self.logger.debug(f"      ❌ DNS резолюция не удалась для {domain}")
            return False, None
        
        # Варианты URL для проверки
        urls_to_check = [
            f"https://www.{domain}",
            f"https://{domain}",
            f"http://www.{domain}",
            f"http://{domain}"
        ]
        
        for url in urls_to_check:
            try:
                self.logger.debug(f"      🔍 Проверяем URL: {url}")
                
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; ContactEnricher/1.0)'}
                )
                
                with urllib.request.urlopen(req, timeout=5) as response:
                    status_code = response.getcode()
                    if status_code < 400:
                        self.logger.debug(f"      ✅ URL доступен: {url} (статус: {status_code})")
                        return True, url
                    else:
                        self.logger.debug(f"      ❌ URL недоступен: {url} (статус: {status_code})")
                        
            except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout) as e:
                self.logger.debug(f"      ❌ Ошибка при проверке {url}: {e}")
                continue
            except Exception as e:
                self.logger.debug(f"      ❌ Неожиданная ошибка при проверке {url}: {e}")
                continue
            
            # Небольшая пауза между запросами
            time.sleep(0.1)
        
        return False, None
    
    def _apply_website_enrichment(self, contact: Dict[str, Any], website_url: str, domain: str, email: str) -> Dict[str, Any]:
        """
        Применение обогащения веб-сайтом к контакту
        
        Args:
            contact: Контакт для обогащения
            website_url: URL веб-сайта
            domain: Домен
            email: Email адрес
            
        Returns:
            Dict: Обогащенный контакт
        """
        enriched = contact.copy()
        
        # Добавляем информацию о веб-сайте
        enriched['website'] = website_url
        enriched['website_confidence'] = 0.8  # Высокая уверенность для проверенных сайтов
        enriched['website_source'] = 'email_domain'
        enriched['website_method'] = 'domain_extraction'
        
        # Добавляем диагностическую информацию
        enriched['enrichment_diagnostic'] = {
            'source_email': email,
            'extracted_domain': domain,
            'website_found': website_url,
            'enriched_at': time.time()
        }
        
        self.logger.info(f"   🎯 Обогащение применено: {email} → {website_url}")
        
        return enriched
    
    def _log_final_stats(self):
        """Логирование финальной статистики"""
        self.logger.info("📊 Статистика диагностики обогащения:")
        for key, value in self.stats.items():
            self.logger.info(f"   {key}: {value}")
        
        # Вычисляем проценты
        if self.stats['contacts_processed'] > 0:
            enrichment_rate = (self.stats['enrichment_applied'] / self.stats['contacts_processed']) * 100
            self.logger.info(f"   Процент обогащения: {enrichment_rate:.1f}%")
        
        if self.stats['domains_extracted'] > 0:
            website_success_rate = (self.stats['websites_found'] / self.stats['domains_extracted']) * 100
            self.logger.info(f"   Успешность поиска сайтов: {website_success_rate:.1f}%")

    def log_email_classification_summary(self, report: Optional[Dict[str, Any]]) -> None:
        """Логирование статистики классификации почтовых ящиков."""
        if not report:
            return

        counts = report.get('counts', {})
        removed_total = report.get('removed_total')
        kept_total = report.get('kept_total')

        self.logger.info("📬 Сводка классификации email адресов:")
        if removed_total is not None or kept_total is not None:
            self.logger.info("   оставлено: %s, удалено: %s", kept_total, removed_total)

        if counts:
            for mailbox_type, count in counts.items():
                self.logger.info("   %s: %s", mailbox_type, count)

    def get_diagnostic_info(self) -> Dict[str, Any]:
        """
        Получение диагностической информации
        
        Returns:
            Dict: Диагностическая информация
        """
        return {
            'stats': self.stats.copy(),
            'has_original_enricher': self.original_enricher is not None,
            'diagnostic_version': '1.0.0'
        }


# Пример использования
if __name__ == "__main__":
    # Настройка логирования для демонстрации
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Тестовые контакты
    test_contacts = [
        {
            'contact_id': 1,
            'name': 'Бабиченко Иван Сергеевич',
            'email': 'sklad@centerld.ru',
            'position': 'Руководитель ОМТС'
        },
        {
            'contact_id': 2,
            'name': 'Гоголева Мария',
            'email': 'm.gogoleva@dna-technology.ru',
            'position': 'Менеджер'
        },
        {
            'contact_id': 3,
            'name': 'Тест без email',
            'position': 'Тестовая должность'
        }
    ]
    
    # Создаем диагностический обогатитель
    diagnostic_enricher = DiagnosticContactEnricher()
    
    # Запускаем диагностику
    print("🚀 Запуск диагностики обогащения контактов")
    enriched_contacts = diagnostic_enricher.diagnose_enrichment(test_contacts)
    
    print(f"\n📋 Результаты диагностики:")
    for contact in enriched_contacts:
        print(f"  {contact.get('name', 'Unknown')}: website = {contact.get('website', 'не найден')}")
    
    print(f"\n📊 Диагностическая информация:")
    diagnostic_info = diagnostic_enricher.get_diagnostic_info()
    print(json.dumps(diagnostic_info, indent=2, ensure_ascii=False))
