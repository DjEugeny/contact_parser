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
from typing import Dict, List, Any, Optional, Tuple

from .text_normalizer import normalize_first_word_only
from .smart_contact_enricher import SmartContactEnricher
from ..utils.city_registry import CityRegistry

# Import as_text from postprocessor to avoid circular import issues
def as_text(value, *, default: str = "", strip: bool = True) -> str:
    """🔤 Безопасно приводит значение к строке."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip() if strip else value
    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8", errors="ignore")
        except Exception:
            text = str(value)
    else:
        text = str(value)
    return text.strip() if strip else text

logger = logging.getLogger(__name__)

COMMON_FIRST_NAMES = {
    'александр', 'алексей', 'андрей', 'анна', 'артем', 'арсений', 'алена', 'алёна',
    'алиса', 'алия', 'алия', 'богдан', 'борис', 'вадим', 'варвара', 'вера',
    'вероника', 'виктор', 'виктория', 'виталий', 'владимир', 'владислав', 'вячеслав',
    'галина', 'гарик', 'глеб', 'данил', 'даниил', 'денис', 'диана', 'евгений',
    'евгения', 'екатерина', 'елена', 'елизавета', 'зоя', 'иван', 'игорь', 'илия',
    'илья', 'инна', 'ирина', 'кирилл', 'константин', 'ксения', 'лариса', 'леонид',
    'лилия', 'лидия', 'любовь', 'людмила', 'маргарита', 'марина', 'мария', 'максим',
    'матвей', 'михаил', 'наталья', 'никита', 'николай', 'оксана', 'олег', 'ольга',
    'павел', 'полина', 'ростислав', 'светлана', 'семен', 'сергей', 'софия', 'степан',
    'таисия', 'таисса', 'тамара', 'татьяна', 'тимур', 'улла', 'ульяна', 'федор',
    'фёдор', 'харитон', 'эдуард', 'элеонора', 'элина', 'юлия', 'яна', 'ян',
    'евграф', 'ростислав', 'руслан', 'роман', 'вадим', 'георгий', 'григорий', 'елиссей',
    'елисей', 'евлампий', 'арина', 'аделина', 'валентина', 'валентин', 'валерий',
    'владлена', 'жана', 'ждан', 'зарина', 'илона', 'карина', 'кристина', 'лариса',
    'маргарита', 'мирослава', 'нелли', 'радмила', 'рафаэль', 'самуил', 'станислав',
    'тамара', 'етр', 'юрий', 'элина', 'юлиан', 'ярослав', 'ярослава'
}

SURNAME_SUFFIXES = (
    'ов', 'ова', 'ев', 'ева', 'ин', 'ина', 'ын', 'ына', 'ский', 'ская', 'цкий', 'цкая',
    'швили', 'дзе', 'ко', 'юк', 'чук', 'як', 'ский', 'ская', 'ман', 'ина', 'ян', 'янц',
    'оглы', 'улы', 'ашвили', 'их', 'ая', 'сий', 'сяя', 'цева', 'чёва'
)


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

        # Помощник для доменов/сайтов
        self.smart_enricher = SmartContactEnricher()
        self.city_registry = CityRegistry()

    @staticmethod
    def _is_first_name(token: str) -> bool:
        if not token:
            return False
        base = token.split('-')[0].strip().lower()
        return base in COMMON_FIRST_NAMES

    @staticmethod
    def _is_surname(token: str) -> bool:
        if not token:
            return False
        clean = token.split('-')[-1].strip().lower()
        for suffix in SURNAME_SUFFIXES:
            if clean.endswith(suffix):
                return True
        return False

    def _normalize_name_order(self, name: str) -> str:
        tokens = [token for token in name.split() if token]
        if len(tokens) < 2:
            return name

        first = tokens[0]
        if not self._is_first_name(first):
            return name

        surname_index = None
        if len(tokens) >= 2 and self._is_surname(tokens[1]):
            surname_index = 1
        elif len(tokens) >= 3 and self._is_surname(tokens[-1]):
            surname_index = len(tokens) - 1

        if surname_index is None:
            return name

        surname = tokens[surname_index]
        remaining = [tokens[i] for i in range(len(tokens)) if i != surname_index]
        reordered = [surname] + remaining
        return " ".join(reordered)
    
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
        
        # 4. Нормализация города через реестр
        normalized = self._normalize_city_field(normalized)

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
        normalized = self._normalize_organization_phones(normalized)

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
        
        normalized = self._normalize_organization_city(normalized)

        # Попытка обогатить веб-сайт по корпоративным email
        normalized = self._enrich_organization_website(normalized)

        return normalized

    def _normalize_city_field(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        original_city = contact.get('city')
        city_info = self.city_registry.normalize_city_value(
            original_city,
            fallback_region=contact.get('region'),
        )
        if not city_info:
            return contact

        contact['city'] = city_info['city']
        city_enriched = not original_city or not self.city_registry.is_same_city(
            city_info['city'],
            original_city,
        )

        if city_enriched:
            contact['region'] = city_info['region']
            contact['timezone'] = city_info['timezone']
            contact['city_validation_source'] = 'city_registry'
        else:
            if not contact.get('region'):
                contact.pop('region', None)
            if not contact.get('timezone'):
                contact.pop('timezone', None)
            contact.pop('city_validation_source', None)

        return contact

    def _normalize_organization_city(self, organization: Dict[str, Any]) -> Dict[str, Any]:
        original_city = organization.get('city')
        original_region = organization.get('region')
        original_federal = organization.get('federal_district')
        original_timezone = organization.get('timezone')
        original_source = organization.get('city_validation_source')
        original_region_type = organization.get('region_type')

        city_info = self.city_registry.normalize_city_value(
            original_city,
            fallback_region=original_region,
        )
        if not city_info:
            return organization

        organization['city'] = city_info['city']
        city_enriched = not original_city or not self.city_registry.is_same_city(
            city_info['city'],
            original_city,
        )

        if city_enriched:
            organization['region'] = city_info['region']
            organization['region_type'] = city_info.get('region_type')
            organization['federal_district'] = city_info['federal_district']
            organization['timezone'] = city_info['timezone']
            organization['city_validation_source'] = 'city_registry'
        else:
            if original_region is None:
                organization.pop('region', None)
            else:
                organization['region'] = original_region

            if original_region_type is None:
                organization.pop('region_type', None)
            else:
                organization['region_type'] = original_region_type

            if original_federal is None:
                organization.pop('federal_district', None)
            else:
                organization['federal_district'] = original_federal

            if original_timezone is None:
                organization.pop('timezone', None)
            else:
                organization['timezone'] = original_timezone

            if original_source is None:
                organization.pop('city_validation_source', None)
            else:
                organization['city_validation_source'] = original_source

        return organization

    def _enrich_organization_website(self, organization: Dict[str, Any]) -> Dict[str, Any]:
        website = organization.get('website')
        emails = organization.get('emails') or []
        if website:
            return organization

        inferred_website = self.smart_enricher.infer_website_from_emails(emails)
        if inferred_website:
            organization['website'] = inferred_website
            organization['website_confidence'] = 0.8
            organization['website_source'] = 'organization_email_domain'

        return organization
    
    def _normalize_organization_phones(self, organization: Dict[str, Any]) -> Dict[str, Any]:
        phones_source = organization.get('phones')
        if not phones_source and organization.get('phone'):
            phones_source = [organization['phone']]

        if not phones_source:
            organization['phones'] = []
            organization.pop('phone', None)
            return organization

        if not isinstance(phones_source, list):
            phones_iterable = [phones_source]
        else:
            phones_iterable = phones_source

        normalized_phones: List[Dict[str, Any]] = []
        seen: set[Tuple[str, Optional[str]]] = set()

        for entry in phones_iterable:
            for phone_record in self._normalize_phone_entry(entry):
                normalized_value = phone_record.get('normalized') or self._ensure_plus_format(
                    phone_record.get('number', '')
                )
                dedup_key = (normalized_value, phone_record.get('extension'))
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                if normalized_value:
                    phone_record['normalized'] = normalized_value
                normalized_phones.append(phone_record)

        organization['phones'] = normalized_phones
        organization.pop('phone', None)
        return organization

    def _normalize_phone_entry(self, entry: Any) -> List[Dict[str, Any]]:
        """Нормализация одного телефонного входа с использованием нового PhoneNormalizer.normalize_phone_to_object"""
        if entry is None:
            return []

        # Получаем исходную строку телефона
        raw_phone: str = ''
        metadata: Dict[str, Any] = {}

        if isinstance(entry, dict):
            # КРИТИЧЕСКИ ВАЖНО: Проверяем, является ли entry уже готовым phone объектом от LLM
            # Phone объект должен иметь поля: type, number, normalized, original, extension
            llm_phone_fields = {'type', 'number', 'normalized', 'original'}
            if llm_phone_fields.issubset(entry.keys()):
                # Это уже готовый phone объект от LLM - возвращаем его как есть
                self.logger.debug(f"Обнаружен готовый phone объект от LLM: {entry}")
                # Убеждаемся, что extension присутствует (может быть None)
                result_entry = dict(entry)
                if 'extension' not in result_entry:
                    result_entry['extension'] = None
                return [result_entry]
            elif 'number' in entry:
                # Это контейнер с номером телефона в поле 'number'
                if isinstance(entry['number'], str):
                    raw_phone = entry['number'].strip()
                else:
                    # Если number не строка - пытаемся преобразовать в строку
                    raw_phone = str(entry['number']).strip()
                # Сохраняем метаданные, но убираем поля, которые будут пересчитаны
                metadata = {
                    key: value for key, value in entry.items() 
                    if key not in {'number', 'normalized', 'original', 'formatted'}
                }
                # Если extension уже включен в number - убираем его
                if 'extension' in entry and entry['extension']:
                    ext_pattern = rf"\s*\(\s*доб\.?\s*{re.escape(str(entry['extension']))}\s*\)"
                    raw_phone = re.sub(ext_pattern, '', raw_phone, flags=re.IGNORECASE).strip()
            else:
                # Fallback для некорректных объектов
                raw_phone = str(entry.get('value') or entry.get('raw') or '').strip()
        elif isinstance(entry, str):
            raw_phone = entry.strip()
            metadata = {'confidence': 1.0, 'type': 'main'}
        else:
            return []

        if not raw_phone:
            return []

        # Используем новый метод normalize_phone_to_object для корректной нормализации
        if self.phone_normalizer_available:
            try:
                normalized_phones = self.phone_normalizer.normalize_phone_to_object(raw_phone)
                
                # Обогащаем результат метаданными
                results = []
                for phone_obj in normalized_phones:
                    # Объединяем с исходными метаданными, приоритет новым полям
                    final_phone = {**metadata, **phone_obj}
                    results.append(final_phone)
                    
                return results
            except Exception as exc:
                self.logger.error(f"Ошибка нормализации телефона через PhoneNormalizer '{raw_phone}': {exc}")
                # Fallback к старому методу
                
        # Fallback нормализация если PhoneNormalizer недоступен
        return self._normalize_phone_variants(raw_phone, metadata)

    def _normalize_phone_variants(self, raw_phone: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        metadata = metadata or {}
        variants: List[Dict[str, Any]] = []

        if self.phone_normalizer_available:
            try:
                variants = self.phone_normalizer.normalize_multiple_phones(raw_phone)
            except Exception as exc:
                self.logger.error(f"Ошибка нормализации телефона '{raw_phone}': {exc}")

        if not variants:
            cleaned = self._simple_phone_cleanup(raw_phone)
            if not cleaned:
                return []
            variants = [{
                'original': raw_phone,
                'formatted': cleaned,
                'normalized': ''.join(filter(str.isdigit, cleaned)) or cleaned,
                'type': metadata.get('type') or 'main',
                'extension': metadata.get('extension') or '',
                'confidence': 0.0,
            }]

        results: List[Dict[str, Any]] = []
        seen: set[Tuple[str, Optional[str]]] = set()

        for variant in variants:
            formatted = (variant.get('formatted') or '').strip()
            normalized_digits = ''.join(filter(str.isdigit, variant.get('normalized') or ''))

            if not formatted:
                formatted = self._simple_phone_cleanup(raw_phone)

            normalized_value = self._ensure_plus_format(normalized_digits or formatted)
            if not normalized_value:
                continue

            display_number = formatted or normalized_value
            extension = metadata.get('extension') or variant.get('extension')
            if extension:
                if 'доб' not in display_number:
                    display_number = f"{display_number} (доб. {extension})"

            dedup_key = (normalized_value, extension or None)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            phone_type = metadata.get('type') or variant.get('type') or 'main'
            if isinstance(phone_type, str):
                lowered_type = phone_type.lower()
                if lowered_type.startswith('неизвест') or lowered_type == 'unknown':
                    phone_type = 'main'

            record: Dict[str, Any] = {
                'number': display_number,
                'normalized': normalized_value,
                'original': variant.get('original') or raw_phone,
                'type': phone_type,
            }

            if extension:
                record['extension'] = extension

            confidence = variant.get('confidence')
            if confidence is not None:
                try:
                    record['confidence'] = round(float(confidence), 3)
                except (TypeError, ValueError):
                    pass

            for key, value in metadata.items():
                if key in {'type', 'extension'}:
                    continue
                record.setdefault(key, value)

            results.append(record)

        return results

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
            normalized_name = self._normalize_name_order(normalized_name)

            if normalized_name and normalized_name != original_name:
                self.logger.debug(
                    "Нормализация имени: '%s' → '%s'",
                    original_name,
                    normalized_name,
                )
                contact['name'] = normalized_name
                contact.setdefault('name_original', original_name)

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
    
    @staticmethod
    def _normalize_phone_key(phone_value: Any) -> Optional[str]:
        """Нормализация телефона для ключа (как в PostProcessor)."""
        if not phone_value:
            return None
        text = as_text(phone_value)
        if not text:
            return None
        digits = re.sub(r'\D+', '', text)
        if not digits:
            return None
        if digits.startswith('8') and len(digits) == 11:
            digits = '7' + digits[1:]
        if digits.startswith('7') and not digits.startswith('+'):
            digits = '+' + digits
        if not digits.startswith('+'):
            digits = '+' + digits
        return digits
     
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
