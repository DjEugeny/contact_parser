#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Фильтр контактов по ценности
Реализует функцию evaluate_contact_value из мини-ТЗ п.3.c

Author: Contact Parser Team
Created: 2025-09-13
"""

import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class ContactFilter:
    """Фильтр контактов по ценности
    
    Реализует алгоритм из мини-ТЗ:
    - Оценка ценности контакта по баллам
    - Фильтрация контактов с score >= 4
    - Перенос неценных контактов в organizations
    """
    
    def __init__(self, min_score: int = 4):
        self.min_score = min_score
        self.logger = logging.getLogger(__name__)
        
    def filter_valuable_contacts(self, contacts: List[Dict[str, Any]], 
                               organizations: Dict[int, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
        """Фильтрация ценных контактов
        
        Args:
            contacts: Список контактов для фильтрации
            organizations: Словарь организаций для обогащения
            
        Returns:
            Tuple[List[Dict], Dict]: (ценные контакты, обновленные организации)
        """
        if not contacts:
            return [], organizations
            
        self.logger.info(f"👤 Фильтрация {len(contacts)} контактов")
        
        valuable_contacts = []
        non_valuable_contacts = []
        
        for contact in contacts:
            score = self.evaluate_contact_value(contact)
            contact['value_score'] = score  # Добавляем score для отладки
            
            if score >= self.min_score:
                valuable_contacts.append(contact)
            else:
                non_valuable_contacts.append(contact)
                
        # Переносим неценные контакты в organizations
        updated_organizations = self._move_contacts_to_organizations(
            non_valuable_contacts, organizations
        )
        
        filtered_count = len(contacts) - len(valuable_contacts)
        if filtered_count > 0:
            self.logger.info(f"🗑️ Отфильтровано {filtered_count} неценных контактов")
            self.logger.info(f"✅ Оставлено {len(valuable_contacts)} ценных контактов")
        
        return valuable_contacts, updated_organizations
    
    def evaluate_contact_value(self, contact: Dict[str, Any]) -> int:
        """Оценка ценности контакта согласно мини-ТЗ
        
        Система баллов:
        - name: +3 балла
        - organization_id: +2 балла  
        - position: +2 балла
        - email: +2 балла
        - phones (непустой массив): +2 балла
        - city: +1 балл
        - inn: +1 балл
        
        Args:
            contact: Контакт для оценки
            
        Returns:
            int: Количество баллов
        """
        score = 0
        
        # name: +3 балла
        if contact.get('name'):
            score += 3
            
        # organization_id: +2 балла
        if contact.get('organization_id'):
            score += 2
            
        # position: +2 балла
        if contact.get('position'):
            score += 2
            
        # email: +2 балла
        if contact.get('email'):
            score += 2
            
        # phones: +2 балла (если массив не пустой)
        phones = contact.get('phones', [])
        if phones and len(phones) > 0:
            # Проверяем, что есть хотя бы один номер с непустым number
            has_valid_phone = any(
                phone.get('number') for phone in phones 
                if isinstance(phone, dict)
            )
            if has_valid_phone:
                score += 2
        # Поддержка старого формата phone (для совместимости)
        elif contact.get('phone'):
            score += 2
            
        # city: +1 балл
        if contact.get('city'):
            score += 1
            
        # inn: +1 балл
        if contact.get('inn'):
            score += 1
            
        return score
    
    def _move_contacts_to_organizations(self, non_valuable_contacts: List[Dict[str, Any]], 
                                      organizations: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """Перенос неценных контактов в organizations
        
        Args:
            non_valuable_contacts: Неценные контакты
            organizations: Существующие организации
            
        Returns:
            Dict: Обновленные организации
        """
        updated_organizations = organizations.copy()
        
        for contact in non_valuable_contacts:
            org_id = contact.get('organization_id')
            if not org_id or org_id not in updated_organizations:
                self.logger.warning(f"Контакт без валидного organization_id: {contact.get('name', 'Unknown')}")
                continue
                
            org = updated_organizations[org_id]
            
            # Добавляем email в организацию
            email = contact.get('email')
            if email:
                org_emails = set(org.get('emails', []))
                org_emails.add(email)
                org['emails'] = list(org_emails)
                
            # Добавляем телефоны в организацию
            phones = contact.get('phones', [])
            if phones:
                org_phones = set(org.get('phones', []))
                for phone in phones:
                    if isinstance(phone, dict) and phone.get('number'):
                        org_phones.add(phone['number'])
                    elif isinstance(phone, str):
                        org_phones.add(phone)
                org['phones'] = list(org_phones)
            # Поддержка старого формата phone
            elif contact.get('phone'):
                org_phones = set(org.get('phones', []))
                org_phones.add(contact['phone'])
                org['phones'] = list(org_phones)
                
            self.logger.debug(f"Перенесен контакт в организацию {org_id}: {contact.get('email', contact.get('name', 'Unknown'))}")
            
        return updated_organizations
    
    def get_contact_value_breakdown(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Детальная разбивка оценки контакта
        
        Args:
            contact: Контакт для анализа
            
        Returns:
            Dict: Детальная разбивка баллов
        """
        breakdown = {
            'total_score': 0,
            'details': {}
        }
        
        # name: +3 балла
        if contact.get('name'):
            breakdown['details']['name'] = 3
            breakdown['total_score'] += 3
        else:
            breakdown['details']['name'] = 0
            
        # organization_id: +2 балла
        if contact.get('organization_id'):
            breakdown['details']['organization_id'] = 2
            breakdown['total_score'] += 2
        else:
            breakdown['details']['organization_id'] = 0
            
        # position: +2 балла
        if contact.get('position'):
            breakdown['details']['position'] = 2
            breakdown['total_score'] += 2
        else:
            breakdown['details']['position'] = 0
            
        # email: +2 балла
        if contact.get('email'):
            breakdown['details']['email'] = 2
            breakdown['total_score'] += 2
        else:
            breakdown['details']['email'] = 0
            
        # phones: +2 балла
        phones = contact.get('phones', [])
        if phones and len(phones) > 0:
            has_valid_phone = any(
                phone.get('number') for phone in phones 
                if isinstance(phone, dict)
            )
            if has_valid_phone:
                breakdown['details']['phones'] = 2
                breakdown['total_score'] += 2
            else:
                breakdown['details']['phones'] = 0
        elif contact.get('phone'):
            breakdown['details']['phones'] = 2
            breakdown['total_score'] += 2
        else:
            breakdown['details']['phones'] = 0
            
        # city: +1 балл
        if contact.get('city'):
            breakdown['details']['city'] = 1
            breakdown['total_score'] += 1
        else:
            breakdown['details']['city'] = 0
            
        # inn: +1 балл
        if contact.get('inn'):
            breakdown['details']['inn'] = 1
            breakdown['total_score'] += 1
        else:
            breakdown['details']['inn'] = 0
            
        breakdown['is_valuable'] = breakdown['total_score'] >= self.min_score
        
        return breakdown
    
    def get_filter_stats(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Получение статистики фильтрации
        
        Args:
            contacts: Список контактов для анализа
            
        Returns:
            Dict: Статистика фильтрации
        """
        if not contacts:
            return {
                'total_contacts': 0,
                'valuable_contacts': 0,
                'non_valuable_contacts': 0,
                'average_score': 0.0,
                'score_distribution': {}
            }
            
        scores = [self.evaluate_contact_value(contact) for contact in contacts]
        valuable_count = sum(1 for score in scores if score >= self.min_score)
        
        # Распределение по баллам
        score_distribution = {}
        for score in scores:
            score_distribution[score] = score_distribution.get(score, 0) + 1
            
        return {
            'total_contacts': len(contacts),
            'valuable_contacts': valuable_count,
            'non_valuable_contacts': len(contacts) - valuable_count,
            'average_score': sum(scores) / len(scores) if scores else 0.0,
            'min_score_threshold': self.min_score,
            'score_distribution': score_distribution
        }


# Пример использования
if __name__ == "__main__":
    contact_filter = ContactFilter()
    
    # Тестовые контакты
    test_contacts = [
        {
            "contact_id": 101,
            "name": "Гоголева Мария",
            "organization_id": 1,
            "position": "Менеджер по продажам",
            "email": "m.gogoleva@dna-technology.ru",
            "phones": [{"type": "main", "number": "+7(495) 640-17-71"}],
            "city": "Москва",
            "confidence": 0.95
        },
        {
            "contact_id": 102,
            "name": None,
            "organization_id": 1,
            "position": None,
            "email": "info@dna-technology.ru",
            "phones": [],
            "city": None,
            "confidence": 0.5
        }
    ]
    
    test_organizations = {
        1: {
            "organization_id": 1,
            "name": "ДНК-Технология",
            "emails": [],
            "phones": []
        }
    }
    
    # Фильтрация
    valuable, updated_orgs = contact_filter.filter_valuable_contacts(test_contacts, test_organizations)
    
    print(f"Ценные контакты: {len(valuable)}")
    print(f"Обновленные организации: {updated_orgs}")
    print(f"Статистика: {contact_filter.get_filter_stats(test_contacts)}")
    
    # Детальная разбивка
    for contact in test_contacts:
        breakdown = contact_filter.get_contact_value_breakdown(contact)
        print(f"Контакт {contact.get('name', 'Unknown')}: {breakdown}")