#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contact Location Safety Module
Предотвращает ложное обогащение контактов локационными данными из HQ-блоков организаций.
Заполняет contacts.city/address только при явных персональных сигналах.

Author: Contact Parser Team
Created: 2025-01-10
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ContactLocationEvidence:
    """Доказательства персональной локации контакта"""
    city: Optional[str] = None
    address: Optional[str] = None
    snippet: str = ""  # Фрагмент текста-источника
    confidence: float = 0.0  # 0.0-1.0
    source_type: str = ""  # "signature", "body_near_name", "title_context", "rejected_hq_block"
    matched_patterns: List[str] = field(default_factory=list)  # Какие паттерны сработали
    rejected_reason: Optional[str] = None  # Причина отклонения


class ContactLocationSafety:
    """
    Безопасное обогащение локации контактов
    
    Предотвращает копирование HQ-адресов/городов организации в контакты.
    Заполняет локацию только при явных персональных сигналах.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация модуля безопасности локаций
        
        Args:
            config_path: Путь к файлу конфигурации (по умолчанию config/processing_config.json)
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Параметры из конфигурации
        self.min_confidence = self.config.get('min_confidence', 0.7)
        self.internal_domains = set(self.config.get('internal_domains', []))
        self.personal_markers = self.config.get('personal_markers', [
            'г.', 'город', 'регион', 'представитель', 'офис в', 
            'территориальный менеджер', 'региональный представитель'
        ])
        self.hq_markers = self.config.get('hq_markers', [
            'ИНН', 'ОГРН', 'р/с', 'к/с', 'БИК', 'ОКПО'
        ])
        self.enabled = self.config.get('enabled', True)
        
        # Статистика
        self.stats = {
            'contacts_processed': 0,
            'locations_applied': 0,
            'locations_rejected': 0,
            'hq_blocks_detected': 0
        }
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Загружает конфигурацию из файла
        
        Args:
            config_path: Путь к файлу конфигурации
            
        Returns:
            Dict: Конфигурация модуля
        """
        if config_path is None:
            # Путь по умолчанию
            project_root = Path(__file__).resolve().parent.parent.parent
            config_path = project_root / 'config' / 'processing_config.json'
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            self.logger.warning(
                f"⚠️ Конфигурация не найдена: {config_path}. Используются значения по умолчанию."
            )
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = json.load(f)
                return full_config.get('contact_location_safety', {})
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            return {}
    
    def is_hq_block(self, text: str, organization_names: Optional[List[str]] = None) -> bool:
        """
        Определяет, является ли текст HQ-блоком организации
        
        Args:
            text: Текст для проверки
            organization_names: Список названий организаций для проверки контекста
            
        Returns:
            bool: True если это HQ-блок
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Проверка на юридические маркеры (ИНН, ОГРН, р/с, к/с, БИК, ОКПО)
        for marker in self.hq_markers:
            if marker.lower() in text_lower:
                self.logger.debug(f"🏢 Обнаружен HQ-блок по маркеру '{marker}': {text[:100]}...")
                self.stats['hq_blocks_detected'] += 1
                return True
        
        # Проверка на адрес рядом с названием организации без персонального контекста
        if organization_names:
            for org_name in organization_names:
                if not org_name:
                    continue
                
                org_name_lower = org_name.lower()
                # Ищем название организации в тексте
                if org_name_lower in text_lower:
                    # Проверяем, есть ли рядом адресные маркеры без персональных
                    address_markers = ['адрес', 'юридический адрес', 'фактический адрес', 
                                     'местонахождение', 'ул.', 'улица', 'проспект', 'пр.']
                    personal_markers_lower = [m.lower() for m in self.personal_markers]
                    
                    has_address_marker = any(marker in text_lower for marker in address_markers)
                    has_personal_marker = any(marker in text_lower for marker in personal_markers_lower)
                    
                    # Если есть адресный маркер рядом с названием организации, но нет персональных маркеров
                    if has_address_marker and not has_personal_marker:
                        self.logger.debug(
                            f"🏢 Обнаружен HQ-блок: адрес рядом с '{org_name}' без персонального контекста"
                        )
                        self.stats['hq_blocks_detected'] += 1
                        return True
        
        return False
    
    def calculate_confidence(self, text: str, context: Dict[str, Any]) -> float:
        """
        Вычисляет уверенность в персональности сигнала
        
        Шкала confidence:
        - 0.9-1.0: Очень высокая (сильные персональные маркеры)
        - 0.8-0.9: Высокая (подпись с ФИО и должностью)
        - 0.7-0.8: Средняя (подпись с локационными маркерами)
        - 0.6-0.7: Низкая (упоминание в теле без контекста)
        - 0.0-0.6: Очень низкая (не применяется по умолчанию)
        
        Args:
            text: Текст с локационным сигналом
            context: Контекст (source_type, has_name, has_title, etc.)
            
        Returns:
            float: Confidence score 0.0-1.0
        """
        # Если это HQ-блок, confidence = 0.0
        if self.is_hq_block(text):
            return 0.0
        
        confidence = 0.5  # Базовое значение
        
        source_type = context.get('source_type', '')
        text_lower = text.lower()
        
        # Сильные персональные маркеры: >= 0.9
        strong_markers = [
            'представитель', 'офис в', 'территориальный менеджер', 
            'региональный представитель', 'региональный менеджер',
            'представитель в', 'менеджер в'
        ]
        if any(marker in text_lower for marker in strong_markers):
            confidence = max(confidence, 0.9)
            self.logger.debug(f"✅ Обнаружен сильный персональный маркер, confidence=0.9+")
        
        # Подпись с ФИО и должностью: >= 0.8
        if source_type == 'signature' and context.get('has_name') and context.get('has_title'):
            confidence = max(confidence, 0.8)
            self.logger.debug(f"✅ Подпись с ФИО и должностью, confidence=0.8+")
        
        # Подпись с локационными маркерами: +0.2
        location_markers = ['г.', 'город', 'регион']
        if any(marker in text_lower for marker in location_markers):
            confidence += 0.2
        
        # Упоминание в теле письма рядом с ФИО без дополнительного контекста: <= 0.6
        if source_type == 'body_near_name':
            if context.get('has_title'):
                confidence = min(confidence, 0.7)  # С должностью - чуть выше
            else:
                confidence = min(confidence, 0.6)  # Без должности - низкая
                self.logger.debug(f"⚠️ Упоминание в теле без контекста, confidence<=0.6")
        
        # Ограничиваем диапазон 0.0-1.0
        final_confidence = max(0.0, min(1.0, confidence))
        
        return final_confidence
    
    def extract_contact_location_evidence(
        self, 
        message: Dict[str, Any],
        contacts: List[Dict[str, Any]],
        signature_blocks_by_person: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ContactLocationEvidence]:
        """
        Извлекает персональные локационные сигналы для каждого контакта
        
        Args:
            message: Данные сообщения
            contacts: Список контактов для обработки
            signature_blocks_by_person: Блоки подписей по персонам (contact_gid -> signature)
            
        Returns:
            Dict[contact_gid, ContactLocationEvidence]: Доказательства локации для каждого контакта
        """
        evidence_map: Dict[str, ContactLocationEvidence] = {}
        
        if not self.enabled:
            self.logger.debug("⚠️ Contact location safety отключен в конфигурации")
            return evidence_map
        
        # Получаем названия организаций для определения HQ-блоков
        organization_names = []
        if 'organizations' in message:
            organization_names = [org.get('name', '') for org in message.get('organizations', [])]
        
        # Обрабатываем каждый контакт
        for contact in contacts:
            contact_gid = contact.get('gid', '')
            if not contact_gid:
                continue
            
            # Пытаемся извлечь локацию из подписи
            if signature_blocks_by_person and contact_gid in signature_blocks_by_person:
                signature_text = signature_blocks_by_person[contact_gid]
                evidence = self._extract_from_signature(
                    signature_text, contact, organization_names
                )
                if evidence and evidence.confidence > 0:
                    evidence_map[contact_gid] = evidence
                    continue
            
            # Если в подписи не нашли, пытаемся извлечь из тела письма
            body = message.get('body', '') or message.get('text', '')
            if body:
                evidence = self._extract_from_body(
                    body, contact, organization_names
                )
                if evidence and evidence.confidence > 0:
                    evidence_map[contact_gid] = evidence
        
        return evidence_map
    
    def _extract_from_signature(
        self,
        signature_text: str,
        contact: Dict[str, Any],
        organization_names: List[str]
    ) -> Optional[ContactLocationEvidence]:
        """
        Извлекает локацию из блока подписи
        
        Args:
            signature_text: Текст подписи
            contact: Данные контакта
            organization_names: Названия организаций
            
        Returns:
            ContactLocationEvidence или None
        """
        if not signature_text:
            return None
        
        # Проверяем, не является ли это HQ-блоком
        if self.is_hq_block(signature_text, organization_names):
            evidence = ContactLocationEvidence(
                snippet=signature_text[:200],
                confidence=0.0,
                source_type='rejected_hq_block',
                rejected_reason='HQ block detected in signature'
            )
            return evidence
        
        # Ищем локационные сигналы
        contact_title = contact.get('title') or contact.get('position')
        city = self._extract_city(signature_text, contact_title)
        address = self._extract_address(signature_text)
        matched_patterns = self._find_matched_patterns(signature_text)
        
        if not city and not address:
            return None
        
        # Определяем контекст для расчета confidence
        context = {
            'source_type': 'signature',
            'has_name': bool(contact.get('name')),
            'has_title': bool(contact.get('title') or contact.get('position'))
        }
        
        confidence = self.calculate_confidence(signature_text, context)
        
        evidence = ContactLocationEvidence(
            city=city,
            address=address,
            snippet=signature_text[:200],
            confidence=confidence,
            source_type='signature',
            matched_patterns=matched_patterns
        )
        
        return evidence
    
    def _extract_from_body(
        self,
        body_text: str,
        contact: Dict[str, Any],
        organization_names: List[str]
    ) -> Optional[ContactLocationEvidence]:
        """
        Извлекает локацию из тела письма рядом с упоминанием контакта
        
        Args:
            body_text: Текст письма
            contact: Данные контакта
            organization_names: Названия организаций
            
        Returns:
            ContactLocationEvidence или None
        """
        if not body_text:
            return None
        
        contact_name = contact.get('name', '')
        if not contact_name:
            return None
        
        # Ищем упоминание имени контакта в тексте
        name_pos = body_text.lower().find(contact_name.lower())
        if name_pos == -1:
            return None
        
        # Берем контекст вокруг имени (200 символов до и после)
        context_start = max(0, name_pos - 200)
        context_end = min(len(body_text), name_pos + len(contact_name) + 200)
        context_text = body_text[context_start:context_end]
        
        # Проверяем, не является ли это HQ-блоком
        if self.is_hq_block(context_text, organization_names):
            return None
        
        # Ищем локационные сигналы в контексте
        contact_title = contact.get('title') or contact.get('position')
        city = self._extract_city(context_text, contact_title)
        address = self._extract_address(context_text)
        matched_patterns = self._find_matched_patterns(context_text)
        
        if not city and not address:
            return None
        
        # Определяем контекст для расчета confidence
        context_dict = {
            'source_type': 'body_near_name',
            'has_name': True,
            'has_title': bool(contact.get('title') or contact.get('position'))
        }
        
        confidence = self.calculate_confidence(context_text, context_dict)
        
        evidence = ContactLocationEvidence(
            city=city,
            address=address,
            snippet=context_text[:200],
            confidence=confidence,
            source_type='body_near_name',
            matched_patterns=matched_patterns
        )
        
        return evidence
    
    def _extract_city(self, text: str, contact_title: Optional[str] = None) -> Optional[str]:
        """
        Извлекает название города из текста
        
        Обрабатывает граничные случаи:
        - Несколько городов в тексте (выбирает с наивысшим приоритетом)
        - Формат "Офис в Москве | Представитель в Новосибирске" (использует контекст роли)
        
        Args:
            text: Текст для анализа
            contact_title: Должность контакта для определения контекста роли
            
        Returns:
            Название города или None
        """
        if not text:
            return None
        
        # Паттерны для поиска городов с приоритетами
        # Приоритет 1: Сильные персональные маркеры с городом
        high_priority_patterns = [
            r'(?:представитель|менеджер)\s+в\s+(?:г\.\s*)?([А-ЯЁ][\wа-яё\-\s]+?)(?=\s*[,.\n]|$)',  # представитель в Москве
            r'(?:офис|филиал)\s+в\s+(?:г\.\s*)?([А-ЯЁ][\wа-яё\-\s]+?)(?=\s*[,.\n]|$)',  # офис в Москве
        ]
        
        # Приоритет 2: Явные локационные маркеры
        medium_priority_patterns = [
            r'г\.\s*([А-ЯЁ][\wа-яё\-\s]+?)(?=\s*[,.\n]|$)',  # г. Москва, г. Нижний Новгород, г. Санкт-Петербург
            r'город\s+([А-ЯЁ][\wа-яё\-\s]+?)(?=\s*[,.\n]|$)',  # город Москва
        ]
        
        # Приоритет 3: Город перед адресом
        low_priority_patterns = [
            r'([А-ЯЁ][\wа-яё\-\s]+?)\s*,\s*(?:ул\.|улица|пр\.|проспект)',  # Москва, ул. Ленина
        ]
        
        # Пытаемся найти город с наивысшим приоритетом
        for patterns in [high_priority_patterns, medium_priority_patterns, low_priority_patterns]:
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                cities = []
                for match in matches:
                    city = match.group(1).strip()
                    # Фильтруем слишком короткие или слишком длинные названия
                    if 3 <= len(city) <= 50:
                        cities.append((city, match.start()))
                
                if cities:
                    # Если несколько городов найдено
                    if len(cities) > 1:
                        # Пытаемся выбрать по контексту роли
                        if contact_title:
                            title_lower = contact_title.lower()
                            for city, pos in cities:
                                # Ищем контекст вокруг города
                                context_start = max(0, pos - 50)
                                context_end = min(len(text), pos + 50)
                                context = text[context_start:context_end].lower()
                                
                                # Если в контексте есть слова из должности, выбираем этот город
                                title_words = title_lower.split()
                                if any(word in context for word in title_words if len(word) > 3):
                                    self.logger.debug(
                                        f"🎯 Выбран город '{city}' по контексту роли '{contact_title}'"
                                    )
                                    return city
                        
                        # Если не удалось выбрать по контексту, берем первый упомянутый
                        self.logger.debug(
                            f"⚠️ Найдено несколько городов: {[c[0] for c in cities]}. "
                            f"Выбран первый: '{cities[0][0]}'"
                        )
                        return cities[0][0]
                    else:
                        return cities[0][0]
        
        return None
    
    def _extract_address(self, text: str) -> Optional[str]:
        """
        Извлекает адрес из текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            Адрес или None
        """
        if not text:
            return None
        
        # Паттерны для поиска адресов
        address_patterns = [
            r'(?:ул\.|улица)\s+[А-ЯЁа-яё\-\s]+,?\s*(?:д\.|дом)?\s*\d+[а-я]?',  # ул. Ленина, д. 10
            r'(?:пр\.|проспект)\s+[А-ЯЁа-яё\-\s]+,?\s*(?:д\.|дом)?\s*\d+[а-я]?',  # пр. Мира, 15
            r'(?:пер\.|переулок)\s+[А-ЯЁа-яё\-\s]+,?\s*(?:д\.|дом)?\s*\d+[а-я]?',  # пер. Садовый, 3
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, text)
            if match:
                address = match.group(0).strip()
                # Фильтруем слишком короткие или слишком длинные адреса
                if 10 <= len(address) <= 200:
                    return address
        
        return None
    
    def _find_matched_patterns(self, text: str) -> List[str]:
        """
        Находит совпавшие персональные маркеры в тексте
        
        Args:
            text: Текст для анализа
            
        Returns:
            Список совпавших маркеров
        """
        matched = []
        text_lower = text.lower()
        
        for marker in self.personal_markers:
            if marker.lower() in text_lower:
                matched.append(marker)
        
        return matched
    
    def apply_contact_location(
        self,
        contact: Dict[str, Any],
        evidence: ContactLocationEvidence,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Применяет локацию к контакту, если безопасно
        
        Правила применения:
        1. Только если поле пустое (не перезаписываем существующие данные)
        2. Только если confidence >= min_confidence
        3. Для внутренних доменов требуется сильный персональный сигнал (confidence >= 0.8)
        4. Если нет персонального сигнала для внутреннего домена - оставляем city=null, address=null
        
        Args:
            contact: Контакт для обогащения
            evidence: Доказательства персональной локации
            metadata: Метаданные постобработки
            
        Returns:
            bool: True если локация была применена
        """
        if not self.enabled:
            return False
        
        self.stats['contacts_processed'] += 1
        contact_gid = contact.get('gid', 'unknown')
        
        # Проверка confidence
        if evidence.confidence < self.min_confidence:
            self._record_rejection(contact, evidence, metadata, 
                                  f"Low confidence: {evidence.confidence:.2f} < {self.min_confidence}")
            return False
        
        # Проверка на внутренний домен без сильного персонального сигнала
        email = contact.get('email', '')
        if email and '@' in email:
            domain = email.split('@')[1].lower()
            if domain in self.internal_domains:
                if evidence.confidence < 0.8:
                    # Для внутренних сотрудников без сильного персонального сигнала
                    # оставляем city=null, address=null
                    self.logger.info(
                        f"⚠️ Внутренний домен {domain} без сильного персонального сигнала "
                        f"(confidence={evidence.confidence:.2f}). Оставляем city=null, address=null"
                    )
                    # Явно устанавливаем null, если поля не заполнены
                    if not contact.get('city'):
                        contact['city'] = None
                    if not contact.get('address'):
                        contact['address'] = None
                    
                    self._record_rejection(contact, evidence, metadata,
                                          f"Internal domain {domain} without strong personal signal (confidence < 0.8)")
                    return False
                else:
                    self.logger.info(
                        f"✅ Внутренний домен {domain} с сильным персональным сигналом "
                        f"(confidence={evidence.confidence:.2f}). Применяем локацию."
                    )
        
        applied = False
        
        # Применяем city только если поле пустое
        if evidence.city and not contact.get('city'):
            contact['city'] = evidence.city
            applied = True
            self.logger.info(
                f"✅ Применена локация city='{evidence.city}' для контакта {contact_gid} "
                f"(confidence={evidence.confidence:.2f}, source={evidence.source_type})"
            )
        elif contact.get('city'):
            self.logger.debug(
                f"⚠️ Поле city уже заполнено для контакта {contact_gid}: '{contact.get('city')}'. "
                f"Не перезаписываем."
            )
        
        # Применяем address только если поле пустое
        if evidence.address and not contact.get('address'):
            contact['address'] = evidence.address
            applied = True
            self.logger.info(
                f"✅ Применена локация address='{evidence.address}' для контакта {contact_gid} "
                f"(confidence={evidence.confidence:.2f}, source={evidence.source_type})"
            )
        elif contact.get('address'):
            self.logger.debug(
                f"⚠️ Поле address уже заполнено для контакта {contact_gid}: '{contact.get('address')}'. "
                f"Не перезаписываем."
            )
        
        if applied:
            self.stats['locations_applied'] += 1
            self._record_application(contact, evidence, metadata)
        else:
            self._record_rejection(contact, evidence, metadata, "Fields already filled or no data to apply")
        
        return applied
    
    def _record_application(
        self,
        contact: Dict[str, Any],
        evidence: ContactLocationEvidence,
        metadata: Dict[str, Any]
    ) -> None:
        """Записывает метаданные о применении локации"""
        contact_gid = contact.get('gid', 'unknown')
        
        if 'location_evidence' not in metadata:
            metadata['location_evidence'] = {}
        
        metadata['location_evidence'][contact_gid] = {
            'applied': True,
            'city': evidence.city,
            'address': evidence.address,
            'snippet': evidence.snippet,
            'confidence': evidence.confidence,
            'source_type': evidence.source_type,
            'matched_patterns': evidence.matched_patterns
        }
    
    def _record_rejection(
        self,
        contact: Dict[str, Any],
        evidence: ContactLocationEvidence,
        metadata: Dict[str, Any],
        reason: str
    ) -> None:
        """Записывает метаданные об отклонении локации"""
        contact_gid = contact.get('gid', 'unknown')
        
        self.stats['locations_rejected'] += 1
        
        if 'location_evidence' not in metadata:
            metadata['location_evidence'] = {}
        
        metadata['location_evidence'][contact_gid] = {
            'applied': False,
            'rejected_reason': reason,
            'snippet': evidence.snippet,
            'confidence': evidence.confidence,
            'source_type': evidence.source_type,
            'matched_patterns': evidence.matched_patterns
        }
        
        self.logger.debug(
            f"⚠️ Отклонена локация для контакта {contact_gid}: {reason} "
            f"(confidence={evidence.confidence:.2f})"
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Возвращает статистику работы модуля"""
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """Сбрасывает статистику"""
        self.stats = {
            'contacts_processed': 0,
            'locations_applied': 0,
            'locations_rejected': 0,
            'hq_blocks_detected': 0
        }
