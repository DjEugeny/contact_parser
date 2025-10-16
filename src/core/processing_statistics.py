#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Класс для сбора и вывода детальной статистики обработки

Author: Contact Parser Team
Created: 2025-10-16
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path


@dataclass
class ProcessingStatistics:
    """
    📊 Статистика обработки писем
    
    Собирает метрики по всем этапам обработки и выводит красивую таблицу
    """
    
    # Счётчики писем
    total_emails: int = 0
    successful_emails: int = 0
    failed_emails: int = 0
    
    # Счётчики сущностей
    total_organizations: int = 0
    organizations_with_inn: int = 0
    total_contacts: int = 0
    contacts_with_org: int = 0
    contacts_without_org: int = 0
    total_commercial_offers: int = 0
    valid_commercial_offers: int = 0
    offers_with_dates: int = 0
    total_interactions: int = 0
    
    # Счётчики вложений
    total_attachments: int = 0
    ocr_processed: int = 0
    ocr_errors: int = 0
    ocr_skipped: int = 0
    ocr_cache_hits: int = 0
    ocr_cache_misses: int = 0
    
    # Время обработки
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_time: float = 0.0
    avg_time_per_email: float = 0.0
    avg_time_per_ocr: float = 0.0
    
    # Дополнительные метрики
    validation_errors: int = 0
    retry_count: int = 0
    
    def start(self):
        """Начать отсчёт времени"""
        self.start_time = time.time()
    
    def finish(self):
        """Завершить отсчёт времени и рассчитать средние значения"""
        self.end_time = time.time()
        self.total_time = self.end_time - self.start_time
        
        if self.total_emails > 0:
            self.avg_time_per_email = self.total_time / self.total_emails
        
        total_ocr = self.ocr_processed + self.ocr_errors
        if total_ocr > 0:
            self.avg_time_per_ocr = self.total_time / total_ocr
    
    def add_email_result(self, result: Dict[str, Any]):
        """
        Добавить результат обработки письма
        
        Args:
            result: Результат обработки письма
        """
        self.total_emails += 1
        
        if result.get('success', False):
            self.successful_emails += 1
        else:
            self.failed_emails += 1
        
        if result.get('validation_error'):
            self.validation_errors += 1
        
        # Подсчёт организаций
        organizations = result.get('organizations', [])
        self.total_organizations += len(organizations)
        self.organizations_with_inn += sum(
            1 for org in organizations 
            if org.get('inn') and org['inn'] not in [None, '', 'null']
        )
        
        # Подсчёт контактов
        contacts = result.get('contacts', [])
        self.total_contacts += len(contacts)
        self.contacts_with_org += sum(
            1 for contact in contacts 
            if contact.get('organization_id') is not None
        )
        self.contacts_without_org += sum(
            1 for contact in contacts 
            if contact.get('organization_id') is None
        )
        
        # Подсчёт КП
        offers = result.get('commercial_offers', [])
        self.total_commercial_offers += len(offers)
        self.valid_commercial_offers += sum(
            1 for offer in offers 
            if offer.get('found', False)
        )
        self.offers_with_dates += sum(
            1 for offer in offers 
            if offer.get('valid_until')
        )
        
        # Подсчёт взаимодействий
        interactions = result.get('interactions', [])
        self.total_interactions += len(interactions)
    
    def add_ocr_result(self, success: bool, from_cache: bool = False):
        """
        Добавить результат OCR обработки
        
        Args:
            success: Успешна ли обработка
            from_cache: Из кеша ли результат
        """
        self.total_attachments += 1
        
        if from_cache:
            self.ocr_cache_hits += 1
            self.ocr_processed += 1
        elif success:
            self.ocr_cache_misses += 1
            self.ocr_processed += 1
        else:
            self.ocr_errors += 1
    
    def add_skipped_attachment(self):
        """Добавить пропущенное вложение"""
        self.total_attachments += 1
        self.ocr_skipped += 1
    
    def print_summary(self):
        """Вывести красивую таблицу со статистикой"""
        if self.end_time is None:
            self.finish()
        
        # Рассчитываем проценты
        email_success_rate = (self.successful_emails / self.total_emails * 100) if self.total_emails > 0 else 0
        ocr_success_rate = (self.ocr_processed / self.total_attachments * 100) if self.total_attachments > 0 else 0
        cache_hit_rate = (self.ocr_cache_hits / (self.ocr_cache_hits + self.ocr_cache_misses) * 100) if (self.ocr_cache_hits + self.ocr_cache_misses) > 0 else 0
        
        print("\n" + "═" * 80)
        print("📊 ИТОГОВАЯ СТАТИСТИКА ОБРАБОТКИ")
        print("═" * 80)
        
        # Письма
        print(f"\n📧 Письма:")
        print(f"   Всего:           {self.total_emails}")
        print(f"   ✅ Успешно:      {self.successful_emails} ({email_success_rate:.1f}%)")
        print(f"   ❌ С ошибками:   {self.failed_emails}")
        if self.validation_errors > 0:
            print(f"   ⚠️  Валидация:    {self.validation_errors}")
        
        # Организации
        if self.total_organizations > 0:
            print(f"\n🏢 Организации:")
            print(f"   Всего:           {self.total_organizations}")
            print(f"   С ИНН:           {self.organizations_with_inn}")
            print(f"   Без ИНН:         {self.total_organizations - self.organizations_with_inn}")
        
        # Контакты
        if self.total_contacts > 0:
            print(f"\n👥 Контакты:")
            print(f"   Всего:           {self.total_contacts}")
            if self.contacts_with_org > 0:
                print(f"   С организацией:  {self.contacts_with_org}")
            if self.contacts_without_org > 0:
                print(f"   Без организации: {self.contacts_without_org}")
        
        # Коммерческие предложения
        if self.total_commercial_offers > 0:
            print(f"\n📄 Коммерческие предложения:")
            print(f"   Всего:           {self.total_commercial_offers}")
            print(f"   Валидных:        {self.valid_commercial_offers}")
            if self.offers_with_dates > 0:
                print(f"   С датами:        {self.offers_with_dates}")
        
        # Взаимодействия
        if self.total_interactions > 0:
            print(f"\n🔁 Взаимодействия: {self.total_interactions}")
        
        # Вложения и OCR
        if self.total_attachments > 0:
            print(f"\n📎 Вложения:")
            print(f"   Всего:           {self.total_attachments}")
            print(f"   ✅ OCR успешно:  {self.ocr_processed} ({ocr_success_rate:.1f}%)")
            if self.ocr_cache_hits > 0:
                print(f"      └─ Из кеша:   {self.ocr_cache_hits} (hit rate: {cache_hit_rate:.1f}%)")
            if self.ocr_cache_misses > 0:
                print(f"      └─ Новых:     {self.ocr_cache_misses}")
            if self.ocr_errors > 0:
                print(f"   ❌ OCR ошибки:   {self.ocr_errors}")
            if self.ocr_skipped > 0:
                print(f"   ⏭️  Пропущено:    {self.ocr_skipped}")
        
        # Время
        print(f"\n⏱️  Время обработки:")
        print(f"   Общее:           {self.total_time:.1f}s")
        if self.total_emails > 0:
            print(f"   На письмо:       {self.avg_time_per_email:.1f}s")
        if self.ocr_processed > 0:
            print(f"   На OCR:          {self.avg_time_per_ocr:.1f}s")
        
        print("═" * 80 + "\n")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Экспорт статистики в словарь
        
        Returns:
            Dict со всеми метриками
        """
        if self.end_time is None:
            self.finish()
        
        return {
            'emails': {
                'total': self.total_emails,
                'successful': self.successful_emails,
                'failed': self.failed_emails,
                'validation_errors': self.validation_errors,
                'success_rate': (self.successful_emails / self.total_emails * 100) if self.total_emails > 0 else 0
            },
            'organizations': {
                'total': self.total_organizations,
                'with_inn': self.organizations_with_inn,
                'without_inn': self.total_organizations - self.organizations_with_inn
            },
            'contacts': {
                'total': self.total_contacts,
                'with_org': self.contacts_with_org,
                'without_org': self.contacts_without_org
            },
            'commercial_offers': {
                'total': self.total_commercial_offers,
                'valid': self.valid_commercial_offers,
                'with_dates': self.offers_with_dates
            },
            'interactions': {
                'total': self.total_interactions
            },
            'attachments': {
                'total': self.total_attachments,
                'ocr_processed': self.ocr_processed,
                'ocr_errors': self.ocr_errors,
                'ocr_skipped': self.ocr_skipped,
                'cache_hits': self.ocr_cache_hits,
                'cache_misses': self.ocr_cache_misses,
                'cache_hit_rate': (self.ocr_cache_hits / (self.ocr_cache_hits + self.ocr_cache_misses) * 100) if (self.ocr_cache_hits + self.ocr_cache_misses) > 0 else 0
            },
            'timing': {
                'total_seconds': self.total_time,
                'avg_per_email': self.avg_time_per_email,
                'avg_per_ocr': self.avg_time_per_ocr
            }
        }


# Пример использования
if __name__ == "__main__":
    # Создаём статистику
    stats = ProcessingStatistics()
    stats.start()
    
    # Симулируем обработку
    import time
    
    # Письмо 1
    stats.add_email_result({
        'success': True,
        'organizations': [
            {'organization_id': 1, 'name': 'Компания А', 'inn': '1234567890'}
        ],
        'contacts': [
            {'contact_id': 1, 'name': 'Иванов', 'organization_id': 1}
        ],
        'commercial_offers': [
            {'found': True, 'valid_until': '2025-12-31'}
        ],
        'interactions': [
            {'interaction_local_id': 1}
        ]
    })
    
    stats.add_ocr_result(success=True, from_cache=True)
    stats.add_ocr_result(success=True, from_cache=False)
    
    time.sleep(0.1)
    
    # Письмо 2
    stats.add_email_result({
        'success': True,
        'organizations': [],
        'contacts': [
            {'contact_id': 1, 'name': 'Петров', 'organization_id': None}
        ],
        'commercial_offers': [],
        'interactions': []
    })
    
    stats.add_skipped_attachment()
    
    # Выводим статистику
    stats.print_summary()
    
    # Экспорт в dict
    print("\n📋 Экспорт в dict:")
    import json
    print(json.dumps(stats.to_dict(), indent=2, ensure_ascii=False))
