#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Нормализатор данных постобработки
Интегрирует нормализацию телефонов и email для новой структуры

Author: Contact Parser Team
Created: 2025-01-27
"""

import re
import logging
from typing import Dict, List, Any, Optional

from .text_normalizer import normalize_first_word_only

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Нормализатор данных постобработки
    
    Функции:
    1. Нормализация телефонов в новом формате phones[]
    2. Валидация и нормализация email адресов
    3. Очистка и стандартизация имен и должностей
    4. Интеграция с phone_normalizer.py
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        # Импорт phone_normalizer из той же папки postprocessing
        try:
            from .phone_normalizer import PhoneNormalizer
            self.phone_normalizer = PhoneNormalizer()
            self.phone_normalizer_available = True
            self.logger.info("📞 phone_normalizer.py успешно импортирован")
        except ImportError as e:
            self.logger.warning(f"⚠️ Не удалось импортировать phone_normalizer: {e}")
            self.phone_normalizer_available = False
            self.phone_normalizer = None

        # Простая нормализация регистра - только первое слово заглавное
        self.logger.info("📝 Используем простую нормализацию: только первое слово с заглавной буквы")
    
    def normalize_contacts(self, contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Нормализация списка контактов
        
        Args:
            contacts: Список контактов для нормализации
            
        Returns:
            List[Dict]: Нормализованные контакты
        """
        if not contacts:
            return []
            
        self.logger.info(f"🔧 Нормализация {len(contacts)} контактов")
        
        normalized_contacts = []
        
        for contact in contacts:
            try:
                normalized_contact = self._normalize_single_contact(contact)
                normalized_contacts.append(normalized_contact)
            except Exception as e:
                self.logger.error(f"Ошибка при нормализации контакта {contact.get('name', 'Unknown')}: {str(e)}")
                # Возвращаем оригинальный контакт в случае ошибки
                normalized_contacts.append(contact)
        
        return normalized_contacts
    
    def normalize_organizations(self, organizations: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """Нормализация организаций
        
        Args:
            organizations: Словарь организаций
            
        Returns:
            Dict: Нормализованные организации
        """
        if not organizations:
            return {}
            
        self.logger.info(f"🏢 Нормализация {len(organizations)} организаций")
        
        normalized_organizations = {}
        
        for org_id, org in organizations.items():
            try:
                normalized_org = self._normalize_single_organization(org)
                normalized_organizations[org_id] = normalized_org
            except Exception as e:
                self.logger.error(f"Ошибка при нормализации организации {org.get('name', 'Unknown')}: {str(e)}")
                # Возвращаем оригинальную организацию в случае ошибки
                normalized_organizations[org_id] = org
        
        return normalized_organizations
    
    def _normalize_single_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Нормализация одного контакта
        
        Args:
            contact: Контакт для нормализации
            
        Returns:
            Dict: Нормализованный контакт
        """
        normalized = contact.copy()
        
        # 1. Нормализация телефонов в новом формате phones[]
        normalized = self._normalize_contact_phones(normalized)
        
        # 2. Нормализация email
        normalized = self._normalize_contact_email(normalized)
        
        # 3. Нормализация имени
        normalized = self._normalize_contact_name(normalized)
        
        # 4. Нормализация должности
        normalized = self._normalize_contact_position(normalized)
        
        return normalized
    
    def _normalize_single_organization(self, organization: Dict[str, Any]) -> Dict[str, Any]:
        """Нормализация одной организации
        
        Args:
            organization: Организация для нормализации
            
        Returns:
            Dict: Нормализованная организация
        """
        normalized = organization.copy()
        
        # 1. Нормализация массива телефонов
        if 'phones' in normalized and normalized['phones']:
            normalized_phones = []
            phones_list = normalized['phones']
            
            # Если phones - это список, обрабатываем каждый элемент
            if isinstance(phones_list, list):
                for phone in phones_list:
                    if isinstance(phone, str) and phone.strip():
                        original_phone = phone.strip()
                        if self.phone_normalizer_available:
                            # Используем новый метод для обработки множественных номеров
                            multiple_results = self.phone_normalizer.normalize_multiple_phones(original_phone)
                            for result in multiple_results:
                                normalized_digits = result.get('normalized') or ''
                                normalized_formatted = result.get('formatted') or ''
                                value = self._ensure_plus_format(normalized_digits) or self._ensure_plus_format(normalized_formatted)
                                if value:
                                    normalized_phones.append(value)
                        else:
                            # Fallback: простая нормализация без phone_normalizer
                            normalized_phone = self._simple_phone_cleanup(original_phone)
                            if normalized_phone:
                                normalized_phones.append(normalized_phone)
            # Если phones - это строка, преобразуем в список
            elif isinstance(phones_list, str) and phones_list.strip():
                original_phone = phones_list.strip()
                if self.phone_normalizer_available:
                    multiple_results = self.phone_normalizer.normalize_multiple_phones(original_phone)
                    for result in multiple_results:
                        normalized_digits = result.get('normalized') or ''
                        normalized_formatted = result.get('formatted') or ''
                        value = self._ensure_plus_format(normalized_digits) or self._ensure_plus_format(normalized_formatted)
                        if value:
                            normalized_phones.append(value)
                else:
                    # Fallback: простая нормализация без phone_normalizer
                    normalized_phone = self._simple_phone_cleanup(original_phone)
                    if normalized_phone:
                        normalized_phones.append(normalized_phone)
            
            normalized['phones'] = normalized_phones
        
        # 2. Нормализация массива emails
        if 'emails' in normalized and normalized['emails']:
            normalized_emails = []
            for email in normalized['emails']:
                if isinstance(email, str) and email.strip():
                    normalized_email = self._normalize_email(email.strip())
                    if normalized_email:
                        normalized_emails.append(normalized_email)
            normalized['emails'] = list(set(normalized_emails))  # Убираем дубликаты
        
        # 3. Нормализация названия организации
        if normalized.get('name'):
            original_name = normalized['name']
            normalized_name = normalize_first_word_only(original_name)
            if normalized_name != original_name:
                self.logger.debug(f"Нормализация организации: '{original_name}' → '{normalized_name}'")
            normalized['name'] = normalized_name
        
        return normalized
    
    def _normalize_contact_phones(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Нормализация телефонов контакта в новом формате phones[]
        
        Args:
            contact: Контакт с телефонами
            
        Returns:
            Dict: Контакт с нормализованными телефонами
        """
        # Обработка нового формата phones[]
        if 'phones' in contact and contact['phones']:
            normalized_phones = []
            
            for phone_obj in contact['phones']:
                if isinstance(phone_obj, dict) and phone_obj.get('number'):
                    original_number = phone_obj['number']
                    if self.phone_normalizer_available:
                        normalized_result = self.phone_normalizer.normalize_contact_phone(original_number)
                        normalized_number = normalized_result.get('formatted_phone', '')
                        normalized_digits = normalized_result.get('normalized_phone', '')
                        phone_type = normalized_result.get('phone_type', 'unknown')
                        extension = normalized_result.get('phone_extension', '')
                    else:
                        normalized_number = self._simple_phone_cleanup(original_number)
                        normalized_digits = ''.join(filter(str.isdigit, normalized_number))
                        phone_type = 'unknown'
                        extension = ''

                    if normalized_number:
                        normalized_phone_obj = phone_obj.copy()
                        normalized_phone_obj['number'] = normalized_number
                        normalized_phone_obj['normalized'] = self._ensure_plus_format(
                            normalized_digits or normalized_number
                        )
                        normalized_phone_obj['original'] = original_number

                        # Добавляем добавочный номер если есть
                        if extension:
                            normalized_phone_obj['extension'] = extension

                        # Определяем тип телефона, если не указан
                        if not normalized_phone_obj.get('type'):
                            normalized_phone_obj['type'] = phone_type

                        normalized_phones.append(normalized_phone_obj)
                elif isinstance(phone_obj, str) and phone_obj.strip():
                    # Поддержка старого формата в массиве
                    original_number = phone_obj.strip()
                    if self.phone_normalizer_available:
                        normalized_result = self.phone_normalizer.normalize_contact_phone(original_number)
                        normalized_number = normalized_result.get('formatted_phone', '')
                        normalized_digits = normalized_result.get('normalized_phone', '')
                        phone_type = normalized_result.get('phone_type', 'unknown')
                        extension = normalized_result.get('phone_extension', '')
                    else:
                        normalized_number = self._simple_phone_cleanup(original_number)
                        normalized_digits = ''.join(filter(str.isdigit, normalized_number))
                        phone_type = 'unknown'
                        extension = ''

                    if normalized_number:
                        phone_obj_dict = {
                            'type': phone_type,
                            'number': normalized_number,
                            'normalized': self._ensure_plus_format(
                                normalized_digits or normalized_number
                            ),
                            'original': original_number
                        }

                        # Добавляем добавочный номер если есть
                        if extension:
                            phone_obj_dict['extension'] = extension

                        normalized_phones.append(phone_obj_dict)
            
            contact['phones'] = normalized_phones
        
        # Поддержка старого формата phone (для совместимости)
        elif 'phone' in contact and contact['phone']:
            original_phone = contact['phone']
            if self.phone_normalizer_available:
                normalized_result = self.phone_normalizer.normalize_contact_phone(original_phone)
                normalized_phone = normalized_result.get('formatted_phone', '')
                phone_type = normalized_result.get('phone_type', 'unknown')
                extension = normalized_result.get('phone_extension', '')
            else:
                normalized_phone = self._simple_phone_cleanup(original_phone)
                phone_type = 'unknown'
                extension = ''
            
            if normalized_phone:
                # Конвертируем в новый формат
                phone_obj = {
                    'type': phone_type,
                    'number': normalized_phone,
                    'normalized': self._ensure_plus_format(normalized_phone),
                    'original': original_phone
                }
                
                # Добавляем добавочный номер если есть
                if extension:
                    phone_obj['extension'] = extension
                    
                contact['phones'] = [phone_obj]
                # Оставляем старое поле для совместимости
                contact['phone_normalized'] = normalized_phone
        
        return contact
    
    def _normalize_contact_email(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Нормализация email контакта
        
        Args:
            contact: Контакт с email
            
        Returns:
            Dict: Контакт с нормализованным email
        """
        if contact.get('email'):
            original_email = contact['email']
            normalized_email = self._normalize_email(original_email)
            
            if normalized_email:
                contact['email'] = normalized_email
                contact['email_valid'] = self._validate_email(normalized_email)
                if original_email != normalized_email:
                    contact['email_original'] = original_email
            else:
                contact['email_valid'] = False
        
        return contact
    
    def _normalize_contact_name(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Нормализация имени контакта
        
        Args:
            contact: Контакт с именем
            
        Returns:
            Dict: Контакт с нормализованным именем
        """
        if contact.get('name'):
            original_name = contact['name']
            normalized_name = normalize_first_word_only(original_name)
            
            if normalized_name and normalized_name != original_name:
                self.logger.debug(f"Нормализация имени: '{original_name}' → '{normalized_name}'")
                contact['name'] = normalized_name
                contact['name_original'] = original_name
        
        return contact
    
    def _normalize_contact_position(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Нормализация должности контакта
        
        Args:
            contact: Контакт с должностью
            
        Returns:
            Dict: Контакт с нормализованной должностью
        """
        if contact.get('position'):
            original_position = contact['position']
            normalized_position = normalize_first_word_only(original_position)
            
            if normalized_position and normalized_position != original_position:
                self.logger.debug(f"Нормализация должности: '{original_position}' → '{normalized_position}'")
                contact['position'] = normalized_position
                contact['position_original'] = original_position
        
        return contact
    
    def _simple_phone_cleanup(self, phone: str) -> str:
        """Простая очистка телефона для fallback случаев

        Args:
            phone: Исходный телефон
            
        Returns:
            str: Очищенный телефон
        """
        if not phone:
            return ''
        
        # Убираем все символы кроме цифр и +
        normalized = re.sub(r'[^\d+]', '', phone)
        
        # Приводим к единому формату: если начинается с 8, заменяем на +7
        if normalized.startswith('8') and len(normalized) == 11:
            normalized = '+7' + normalized[1:]
        elif normalized.startswith('7') and len(normalized) == 11:
            normalized = '+' + normalized

        return normalized

    def _ensure_plus_format(self, digits: str) -> str:
        """☎️ Преобразование цифр телефона в формат с плюсом"""
        if not digits:
            return ''

        value = digits.strip()
        if not value:
            return ''

        if value.startswith('+'):
            return value

        digits_only = ''.join(filter(str.isdigit, value))
        if not digits_only:
            return value

        if digits_only.startswith('8') and len(digits_only) == 11:
            return '+7' + digits_only[1:]

        if digits_only.startswith('7') and len(digits_only) == 11:
            return '+' + digits_only

        if value.startswith('00'):
            return '+' + value[2:]

        return '+' + digits_only
     
    def _normalize_email(self, email: str) -> str:
        """Нормализация email адреса
        
        Args:
            email: Исходный email
            
        Returns:
            str: Нормализованный email
        """
        if not email:
            return ''
        
        # Приводим к нижнему регистру и убираем пробелы
        normalized = email.lower().strip()
        
        # Убираем лишние символы
        normalized = re.sub(r'[<>]', '', normalized)
        
        return normalized
    
    def _validate_email(self, email: str) -> bool:
        """Валидация email адреса
        
        Args:
            email: Email для валидации
            
        Returns:
            bool: Валиден ли email
        """
        if not email:
            return False
        
        return bool(self.email_pattern.match(email))
    
    def _normalize_person_name(self, name: str) -> str:
        """Нормализация имени человека
        
        Args:
            name: Исходное имя
            
        Returns:
            str: Нормализованное имя
        """
        if not name:
            return ''
        
        # Убираем лишние пробелы и приводим к правильному регистру
        words = name.strip().split()
        normalized_words = []
        
        for word in words:
            # Пропускаем пустые слова
            if not word:
                continue
            
            # Обрабатываем инициалы
            if len(word) <= 2 and word.endswith('.'):
                normalized_words.append(word.upper())
            else:
                # Приводим к правильному регистру (первая буква заглавная)
                normalized_words.append(word.capitalize())
        
        return ' '.join(normalized_words)
    
    def _normalize_position_title(self, position: str) -> str:
        """Нормализация должности
        
        Args:
            position: Исходная должность
            
        Returns:
            str: Нормализованная должность
        """
        if not position:
            return ''
        
        # Убираем лишние пробелы и приводим к нижнему регистру
        normalized = ' '.join(position.strip().split()).lower()
        
        # Словарь сокращений должностей
        position_abbreviations = {
            'ген. директор': 'генеральный директор',
            'зам. директора': 'заместитель директора',
            'нач. отдела': 'начальник отдела',
            'рук.': 'руководитель',
        }

        # Применяем сокращения
        for abbr, full in position_abbreviations.items():
            normalized = normalized.replace(abbr, full)

        return ' '.join(word.capitalize() for word in normalized.split())
    
    def _normalize_organization_name(self, name: str) -> str:
        """Нормализация названия организации
        
        Args:
            name: Исходное название
            
        Returns:
            str: Нормализованное название
        """
        if not name:
            return ''
        
        # Убираем лишние пробелы
        normalized = ' '.join(name.strip().split())
        
        # Не трогаем кавычки, если они парные
        # normalized = normalized.strip('"«»"')
        
        return normalized
    
    def get_normalization_stats(self) -> Dict[str, Any]:
        """Получение статистики нормализации
        
        Returns:
            Dict: Статистика работы нормализатора
        """
        return {
            'phone_normalizer_available': self.phone_normalizer_available,
            'contacts_normalized': getattr(self, '_contacts_normalized', 0),
            'organizations_normalized': getattr(self, '_organizations_normalized', 0),
            'phones_normalized': getattr(self, '_phones_normalized', 0),
            'emails_normalized': getattr(self, '_emails_normalized', 0)
        }


# Пример использования
if __name__ == "__main__":
    normalizer = DataNormalizer()
    
    # Тестовый контакт
    test_contact = {
        'name': 'гоголева  мария   михайловна',
        'email': '  M.Gogoleva@DNA-Technology.RU  ',
        'phones': [
            {'type': 'main', 'number': '+7 (495) 640-17-71'},
            {'type': 'mobile', 'number': '8-916-123-45-67'}
        ],
        'position': 'менеджер по продажам',
        'organization_id': 1
    }
    
    # Тестовая организация
    test_organizations = {
        1: {
            'name': '  ООО "ДНК-Технология"  ',
            'emails': ['INFO@DNA-technology.ru', '  sales@dna-technology.ru  '],
            'phones': ['8 800 200-75-15', '+7(495)640-17-71']
        }
    }
    
    # Нормализация
    normalized_contacts = normalizer.normalize_contacts([test_contact])
    normalized_organizations = normalizer.normalize_organizations(test_organizations)
    
    print("🎯 Результат нормализации контакта:")
    for key, value in normalized_contacts[0].items():
        print(f"  {key}: {value}")
    
    print("\n🏢 Результат нормализации организации:")
    for key, value in normalized_organizations[1].items():
        print(f"  {key}: {value}")
    
    print(f"\n📊 Статистика: {normalizer.get_normalization_stats()}")
