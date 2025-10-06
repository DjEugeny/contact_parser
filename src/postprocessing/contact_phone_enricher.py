#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль обогащения телефонов контактов от связанных организаций
Реализует безопасное обогащение контактов телефонами организаций с системой scoring

Author: Contact Parser Team
Created: 2025-01-10
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ContactPhoneEnricher:
    """Обогащение контактов телефонами от связанных организаций"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация модуля обогащения телефонов контактов

        Args:
            config: Конфигурация из settings.CONTACT_PHONE_ENRICHMENT_CONFIG
        """
        self.logger = logging.getLogger(__name__)

        # Загрузка конфигурации
        self.config = config or self._get_default_config()

        # Параметры из конфигурации
        self.enabled = self.config.get("enabled", True)
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.5)
        self.review_threshold = self.config.get("review_threshold", 0.75)
        self.allowed_phone_types = self.config.get(
            "allowed_phone_types", ["main", "office", "fax"]
        )
        self.enrichment_mode = self.config.get("enrichment_mode", "balanced")

        # Настройки mobile обогащения
        mobile_config = self.config.get("mobile_enrichment", {})
        self.mobile_enrichment_enabled = mobile_config.get("enabled", False)
        self.mobile_min_confidence = mobile_config.get("min_confidence_threshold", 0.3)
        self.require_name_in_attachment = mobile_config.get("require_name_in_attachment", False)
        self.proximity_boost = mobile_config.get("proximity_boost", True)

        # Веса факторов scoring
        self.scoring_factors = self.config.get("scoring_factors", {
            "corporate_email": 0.3,
            "position": 0.2,
            "role_in_message": 0.2,
            "city_match": 0.15,
            "high_value_score": 0.15,
            "name_in_attachment": 0.3,
            "phone_proximity": 0.2,
        })

        # Настройка порогов в зависимости от режима
        self._adjust_thresholds_by_mode()

        # Статистика обогащения
        self.stats = {
            "contacts_processed": 0,
            "contacts_enriched": 0,
            "phones_added_total": 0,
            "phones_skipped_total": 0,
            "avg_confidence": 0.0,
            "phones_skipped_by_reason": {
                "low_confidence": 0,
                "no_org_phones": 0,
                "already_has_phones": 0,
                "mobile_only": 0,
                "duplicate": 0,
                "no_organization": 0,
            },
        }

        self.logger.info(
            f"📞 ContactPhoneEnricher инициализирован: "
            f"enabled={self.enabled}, mode={self.enrichment_mode}, "
            f"min_confidence={self.min_confidence_threshold}, "
            f"review_threshold={self.review_threshold}, "
            f"mobile_enrichment={self.mobile_enrichment_enabled}"
        )

    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            "enabled": True,
            "min_confidence_threshold": 0.5,
            "review_threshold": 0.75,
            "allowed_phone_types": ["main", "office", "fax"],
            "enrichment_mode": "balanced",
            "mobile_enrichment": {
                "enabled": False,
                "min_confidence_threshold": 0.3,
                "require_name_in_attachment": False,
                "proximity_boost": True,
            },
            "scoring_factors": {
                "corporate_email": 0.3,
                "position": 0.2,
                "role_in_message": 0.2,
                "city_match": 0.15,
                "high_value_score": 0.15,
                "name_in_attachment": 0.3,
                "phone_proximity": 0.2,
            }
        }

    def _adjust_thresholds_by_mode(self):
        """Настраивает пороги confidence в зависимости от режима обогащения"""
        if self.enrichment_mode == "conservative":
            # Консервативный режим: высокие требования
            self.min_confidence_threshold = max(self.min_confidence_threshold, 0.75)
            self.review_threshold = 0.85
            self.logger.info("🔒 Консервативный режим: повышенные пороги confidence")
        elif self.enrichment_mode == "aggressive":
            # Агрессивный режим: низкие требования
            self.min_confidence_threshold = min(self.min_confidence_threshold, 0.4)
            self.review_threshold = 0.6
            self.logger.info("🚀 Агрессивный режим: пониженные пороги confidence")
        else:
            # Balanced режим: используем настройки из конфига
            self.logger.info("⚖️ Сбалансированный режим: стандартные пороги confidence")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику обогащения"""
        return self.stats.copy()

    def reset_stats(self):
        """Сбрасывает статистику"""
        self.stats = {
            "contacts_processed": 0,
            "contacts_enriched": 0,
            "phones_added_total": 0,
            "phones_skipped_total": 0,
            "avg_confidence": 0.0,
            "phones_skipped_by_reason": {
                "low_confidence": 0,
                "no_org_phones": 0,
                "already_has_phones": 0,
                "mobile_only": 0,
                "duplicate": 0,
                "no_organization": 0,
            },
        }

    def _calculate_enrichment_confidence(
        self, contact: Dict[str, Any], organization: Dict[str, Any], 
        attachment_context: Optional[str] = None
    ) -> float:
        """
        Вычисляет уровень уверенности для обогащения контакта телефонами организации

        Система scoring с конфигурируемыми весами:
        - Корпоративный email с доменом организации
        - Наличие должности (position)
        - role_in_message = "sender" или "recipient"
        - Совпадение города контакта и организации
        - Высокий value_score (≥ 7)
        - Имя контакта найдено во вложении (новое)
        - Телефон рядом с именем во вложении (новое)

        Args:
            contact: Словарь с данными контакта
            organization: Словарь с данными организации
            attachment_context: Текст вложений для проверки proximity (опционально)

        Returns:
            float: Уровень уверенности от 0.0 до 1.0+
        """
        confidence = 0.0
        factors = []

        # 1. Проверка корпоративного email
        contact_email = contact.get("email")
        org_website = organization.get("website")

        if org_website and contact_email:
            # Извлекаем домен из website (убираем http/https и www)
            org_domain = org_website.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
            
            if org_domain.lower() in contact_email.lower():
                weight = self.scoring_factors.get("corporate_email", 0.3)
                confidence += weight
                factors.append(f"corporate_email:{contact_email}")
                self.logger.debug(f"  ✓ Корпоративный email: {contact_email} соответствует домену {org_domain} (+{weight})")
            else:
                self.logger.debug(f"  ✗ Email {contact_email} не соответствует домену {org_domain}")

        # 2. Проверка должности
        position = contact.get("position")
        if position and position.strip():
            weight = self.scoring_factors.get("position", 0.2)
            confidence += weight
            factors.append(f"position:{position}")
            self.logger.debug(f"  ✓ Должность: {position} (+{weight})")

        # 3. Проверка role_in_message
        role = contact.get("role_in_message")
        if role in ["sender", "recipient"]:
            weight = self.scoring_factors.get("role_in_message", 0.2)
            confidence += weight
            factors.append(f"role:{role}")
            self.logger.debug(f"  ✓ Роль в сообщении: {role} (+{weight})")

        # 4. Проверка совпадения города
        contact_city = contact.get("city")
        org_city = organization.get("city")

        if contact_city and org_city:
            # Нормализуем для сравнения
            contact_city_norm = contact_city.strip().lower()
            org_city_norm = org_city.strip().lower()

            if contact_city_norm == org_city_norm:
                weight = self.scoring_factors.get("city_match", 0.15)
                confidence += weight
                factors.append(f"city_match:{contact_city}")
                self.logger.debug(f"  ✓ Совпадение города: {contact_city} (+{weight})")

        # 5. Проверка value_score
        value_score = contact.get("value_score", 0)
        if value_score >= 7:
            weight = self.scoring_factors.get("high_value_score", 0.15)
            confidence += weight
            factors.append(f"high_value_score:{value_score}")
            self.logger.debug(f"  ✓ Высокий value_score: {value_score} (+{weight})")

        # 6. НОВОЕ: Проверка имени во вложении
        if attachment_context and self._check_name_in_attachment(contact, attachment_context):
            weight = self.scoring_factors.get("name_in_attachment", 0.3)
            confidence += weight
            factors.append("name_in_attachment")
            self.logger.debug(f"  ✓ Имя найдено во вложении (+{weight})")

        # 7. НОВОЕ: Проверка proximity телефона к имени
        if attachment_context and self.proximity_boost:
            if self._check_phone_proximity(contact, organization, attachment_context):
                weight = self.scoring_factors.get("phone_proximity", 0.2)
                confidence += weight
                factors.append("phone_proximity")
                self.logger.debug(f"  ✓ Телефон рядом с именем во вложении (+{weight})")

        self.logger.debug(
            f"  📊 Итоговый confidence: {confidence:.2f} "
            f"(факторы: {', '.join(factors) if factors else 'нет'})"
        )

        return confidence

    def _check_name_in_attachment(
        self, contact: Dict[str, Any], attachment_context: str
    ) -> bool:
        """
        Проверяет, упоминается ли имя контакта во вложении

        Args:
            contact: Словарь с данными контакта
            attachment_context: Текст вложений

        Returns:
            bool: True если имя найдено во вложении
        """
        contact_name = contact.get("name", "").strip()
        if not contact_name or not attachment_context:
            return False

        # Нормализуем текст для поиска
        attachment_lower = attachment_context.lower()
        
        # Разбиваем имя на части (Фамилия Имя Отчество)
        name_parts = contact_name.split()
        
        # Проверяем каждую часть имени (минимум 3 символа)
        matches = 0
        for part in name_parts:
            if len(part) >= 3:
                part_lower = part.lower()
                if part_lower in attachment_lower:
                    matches += 1
                    self.logger.debug(f"    🔍 Найдена часть имени '{part}' во вложении")
        
        # Считаем успехом, если найдено хотя бы 2 части имени (Фамилия + Имя)
        # или 1 часть для коротких имен
        threshold = 2 if len(name_parts) >= 2 else 1
        found = matches >= threshold
        
        if found:
            self.logger.debug(f"    ✅ Имя '{contact_name}' найдено во вложении ({matches}/{len(name_parts)} частей)")
        
        return found

    def _check_phone_proximity(
        self, contact: Dict[str, Any], organization: Dict[str, Any], 
        attachment_context: str
    ) -> bool:
        """
        Проверяет, находится ли телефон организации рядом с именем контакта во вложении

        Логика: ищем контекст, где имя контакта и телефон организации находятся
        в пределах 150 символов (примерно 2-3 строки текста)

        Args:
            contact: Словарь с данными контакта
            organization: Словарь с данными организации
            attachment_context: Текст вложений

        Returns:
            bool: True если телефон рядом с именем
        """
        contact_name = contact.get("name", "").strip()
        org_phones = organization.get("phones", [])
        
        if not contact_name or not org_phones or not attachment_context:
            return False

        # Нормализуем текст
        attachment_lower = attachment_context.lower()
        name_lower = contact_name.lower()
        
        # Ищем позицию имени в тексте
        name_positions = []
        start = 0
        while True:
            pos = attachment_lower.find(name_lower, start)
            if pos == -1:
                break
            name_positions.append(pos)
            start = pos + 1
        
        if not name_positions:
            # Попробуем найти хотя бы фамилию
            name_parts = contact_name.split()
            if name_parts:
                surname = name_parts[0].lower()
                pos = attachment_lower.find(surname)
                if pos != -1:
                    name_positions.append(pos)
        
        if not name_positions:
            return False
        
        # Проверяем каждый телефон организации
        for phone in org_phones:
            phone_number = phone.get("number", "")
            phone_original = phone.get("original", "")
            
            if not phone_number and not phone_original:
                continue
            
            # Извлекаем только цифры из телефона для поиска
            phone_digits = ''.join(filter(str.isdigit, phone_number or phone_original))
            if len(phone_digits) < 7:  # Минимум 7 цифр для валидного телефона
                continue
            
            # Ищем телефон в тексте разными способами
            phone_pos = -1
            
            # Способ 1: Поиск по форматированному номеру
            if phone_number:
                phone_pos = attachment_context.find(phone_number)
            
            # Способ 2: Поиск по оригинальному номеру
            if phone_pos == -1 and phone_original:
                phone_pos = attachment_context.find(phone_original)
            
            # Способ 3: Поиск по последним 10 цифрам (без кода страны)
            if phone_pos == -1 and len(phone_digits) >= 10:
                last_10_digits = phone_digits[-10:]
                # Ищем эти цифры в тексте (могут быть с пробелами/дефисами)
                search_patterns = [
                    last_10_digits,
                    f"{last_10_digits[:3]} {last_10_digits[3:6]} {last_10_digits[6:8]} {last_10_digits[8:]}",
                    f"{last_10_digits[:3]} {last_10_digits[3:6]}-{last_10_digits[6:8]}-{last_10_digits[8:]}",
                ]
                for pattern in search_patterns:
                    phone_pos = attachment_context.find(pattern)
                    if phone_pos != -1:
                        break
            
            # Способ 4: Поиск по последним 7 цифрам
            if phone_pos == -1:
                last_digits = phone_digits[-7:]
                phone_pos = attachment_context.find(last_digits)
            
            if phone_pos == -1:
                continue
            
            # Проверяем proximity: телефон в пределах 150 символов от имени
            proximity_threshold = 150
            for name_pos in name_positions:
                distance = abs(phone_pos - name_pos)
                if distance <= proximity_threshold:
                    self.logger.debug(
                        f"    ✅ Телефон {phone_number} найден в {distance} символах от имени '{contact_name}'"
                    )
                    return True
        
        return False

    def _make_enrichment_decision(
        self, confidence: float, contact_gid: str, org_gid: str
    ) -> Dict[str, Any]:
        """
        Принимает решение об обогащении на основе уровня уверенности

        Логика принятия решений:
        - confidence < min_confidence_threshold (default 0.5) → reject
        - min_confidence_threshold ≤ confidence < review_threshold (default 0.75) → needs_review
        - confidence ≥ review_threshold → auto_accept

        Args:
            confidence: Уровень уверенности от 0.0 до 1.0
            contact_gid: Global ID контакта
            org_gid: Global ID организации

        Returns:
            Dict с полями:
                - decision: "reject" | "needs_review" | "auto_accept"
                - confidence: float
                - reason: str (описание причины решения)
                - contact_gid: str
                - org_gid: str
        """
        decision_data = {
            "confidence": confidence,
            "contact_gid": contact_gid,
            "org_gid": org_gid,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Решение на основе порогов
        if confidence < self.min_confidence_threshold:
            decision_data["decision"] = "reject"
            decision_data["reason"] = (
                f"Низкий уровень уверенности ({confidence:.2f} < {self.min_confidence_threshold})"
            )
            self.logger.debug(
                f"  ❌ REJECT: confidence {confidence:.2f} < {self.min_confidence_threshold}"
            )

        elif confidence < self.review_threshold:
            decision_data["decision"] = "needs_review"
            decision_data["reason"] = (
                f"Средний уровень уверенности ({confidence:.2f}), требуется проверка"
            )
            self.logger.debug(
                f"  ⚠️ NEEDS_REVIEW: {self.min_confidence_threshold} ≤ {confidence:.2f} < {self.review_threshold}"
            )

        else:
            decision_data["decision"] = "auto_accept"
            decision_data["reason"] = (
                f"Высокий уровень уверенности ({confidence:.2f} ≥ {self.review_threshold})"
            )
            self.logger.debug(
                f"  ✅ AUTO_ACCEPT: confidence {confidence:.2f} ≥ {self.review_threshold}"
            )

        return decision_data

    def _filter_organization_phones(
        self, org_phones: List[Dict[str, Any]], is_mobile_enrichment: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Фильтрует телефоны организации по типам для безопасного обогащения контактов

        Логика фильтрации:
        - Разрешенные типы: main, office, fax (из конфигурации)
        - Mobile телефоны: разрешены только при is_mobile_enrichment=True
        - Телефоны без типа (type = null) обрабатываются как "main" с пониженным confidence

        Args:
            org_phones: Список телефонов организации
            is_mobile_enrichment: Флаг разрешения mobile обогащения для этого контакта

        Returns:
            List[Dict]: Список отфильтрованных телефонов с добавленным полем confidence_adjustment
        """
        if not org_phones:
            self.logger.debug("  📞 Нет телефонов для фильтрации")
            return []

        filtered_phones = []

        for phone in org_phones:
            if not isinstance(phone, dict):
                self.logger.warning(f"  ⚠️ Пропуск невалидного телефона: {phone}")
                continue

            phone_type = phone.get("type")
            phone_number = phone.get("number") or phone.get("normalized")

            # Пропускаем телефоны без номера
            if not phone_number:
                self.logger.debug("  ⚠️ Пропуск телефона без номера")
                continue

            # Обработка мобильных телефонов
            if phone_type == "mobile":
                if not is_mobile_enrichment:
                    # Mobile обогащение отключено - исключаем телефон
                    self.logger.debug(
                        f"  🚫 Исключен mobile телефон: {phone_number} "
                        f"(mobile_enrichment отключено)"
                    )
                    self.stats["phones_skipped_by_reason"]["mobile_only"] += 1
                    continue
                else:
                    # Mobile обогащение разрешено для этого контакта
                    self.logger.debug(
                        f"  📱 Разрешен mobile телефон: {phone_number} "
                        f"(mobile_enrichment включено, достаточный confidence)"
                    )
                    # Создаем копию телефона с метаданными
                    filtered_phone = phone.copy()
                    filtered_phone["confidence_adjustment"] = 0.0
                    filtered_phone["_is_mobile_enrichment"] = True  # Маркер mobile обогащения
                    filtered_phones.append(filtered_phone)
                    continue

            # Обработка телефонов с null типом (Requirement 3.4)
            if phone_type is None:
                self.logger.debug(
                    f"  ⚠️ Телефон без типа: {phone_number}, обрабатывается как 'main' с пониженным confidence"
                )
                # Создаем копию телефона с добавленными метаданными
                filtered_phone = phone.copy()
                filtered_phone["type"] = "main"  # Присваиваем тип main
                filtered_phone["confidence_adjustment"] = -0.1  # Понижаем confidence
                filtered_phone["_original_type"] = None  # Сохраняем оригинальный тип
                filtered_phones.append(filtered_phone)
                continue

            # Фильтрация по разрешенным типам (Requirements 3.1, 3.3)
            if phone_type in self.allowed_phone_types:
                self.logger.debug(
                    f"  ✅ Разрешен телефон типа '{phone_type}': {phone_number}"
                )
                # Создаем копию телефона с метаданными
                filtered_phone = phone.copy()
                filtered_phone["confidence_adjustment"] = 0.0  # Без корректировки
                filtered_phones.append(filtered_phone)
            else:
                self.logger.debug(
                    f"  🚫 Исключен телефон типа '{phone_type}': {phone_number} "
                    f"(не в списке разрешенных: {self.allowed_phone_types})"
                )

        self.logger.debug(
            f"  📊 Фильтрация завершена: {len(filtered_phones)} из {len(org_phones)} телефонов прошли фильтр"
        )

        return filtered_phones

    def _check_phone_duplicate(
        self, contact_phones: List[Dict[str, Any]], new_phone: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Проверяет наличие дубликата телефона у контакта

        Логика проверки:
        - Сравнение по полю normalized (нормализованный номер)
        - Приоритет LLM-источника над org_enrichment
        - Логирование обнаруженных дубликатов

        Args:
            contact_phones: Список существующих телефонов контакта
            new_phone: Новый телефон для проверки

        Returns:
            Dict с полями:
                - is_duplicate: bool (True если дубликат найден)
                - reason: str (причина, если дубликат)
                - existing_phone: Dict (существующий телефон, если найден)
        """
        result = {
            "is_duplicate": False,
            "reason": None,
            "existing_phone": None,
        }

        # Получаем normalized номер нового телефона
        new_normalized = new_phone.get("normalized")

        # Если нет normalized, не можем проверить дубликат (Requirement 8.4)
        if not new_normalized:
            self.logger.warning(
                f"  ⚠️ Телефон без normalized поля: {new_phone.get('number', 'unknown')}"
            )
            result["is_duplicate"] = True
            result["reason"] = "no_normalized_field"
            return result

        # Проверяем каждый существующий телефон контакта
        for existing_phone in contact_phones:
            if not isinstance(existing_phone, dict):
                continue

            existing_normalized = existing_phone.get("normalized")

            # Пропускаем телефоны без normalized
            if not existing_normalized:
                continue

            # Проверка дубликата по normalized (Requirement 4.1)
            if existing_normalized == new_normalized:
                existing_source = existing_phone.get("source", "unknown")

                # LLM-источник имеет приоритет (Requirement 4.3)
                if existing_source == "llm":
                    self.logger.debug(
                        f"  🔄 Дубликат найден: {new_normalized}, "
                        f"источник LLM имеет приоритет над org_enrichment"
                    )
                    result["is_duplicate"] = True
                    result["reason"] = "llm_source_priority"
                    result["existing_phone"] = existing_phone
                    self.stats["phones_skipped_by_reason"]["duplicate"] += 1
                    return result

                # Любой другой дубликат (Requirement 4.2)
                self.logger.debug(
                    f"  🔄 Дубликат найден: {new_normalized}, "
                    f"источник существующего телефона: {existing_source}"
                )
                result["is_duplicate"] = True
                result["reason"] = f"duplicate_from_{existing_source}"
                result["existing_phone"] = existing_phone
                self.stats["phones_skipped_by_reason"]["duplicate"] += 1
                return result

        # Дубликат не найден
        self.logger.debug(f"  ✅ Дубликат не найден для: {new_normalized}")
        return result

    def enrich_contacts_phones(
        self,
        contacts: List[Dict[str, Any]],
        organizations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Основной метод обогащения телефонов контактов от связанных организаций

        Алгоритм:
        1. Итерация по всем контактам
        2. Проверка наличия organization_id
        3. Получение организации по ID
        4. Проверка наличия телефонов у организации
        5. Вычисление confidence score
        6. Фильтрация телефонов организации
        7. Проверка дубликатов
        8. Добавление телефонов с метаданными
        9. Обработка edge cases

        Args:
            contacts: Список контактов для обогащения
            organizations: Список организаций

        Returns:
            Dict с метаданными обогащения:
                - enrichment_metadata: List[Dict] (метаданные по каждому контакту)
                - stats: Dict (общая статистика)
        """
        if not self.enabled:
            self.logger.info("📞 ContactPhoneEnricher отключен в конфигурации")
            return {
                "enrichment_metadata": [],
                "stats": self.get_stats(),
            }

        self.logger.info(
            f"📞 Начало обогащения телефонов: {len(contacts)} контактов, {len(organizations)} организаций"
        )

        # Сброс статистики перед обработкой
        self.reset_stats()

        # Создаем индекс организаций по organization_id для быстрого поиска
        org_index = {}
        for org in organizations:
            org_id = org.get("organization_id")
            if org_id:
                org_index[org_id] = org

        self.logger.debug(f"  📊 Создан индекс организаций: {len(org_index)} записей по organization_id")

        # Метаданные обогащения для каждого контакта
        enrichment_metadata = []

        # Список для накопления confidence scores
        confidence_scores = []

        # Итерация по всем контактам (Requirement 1.1)
        for contact in contacts:
            self.stats["contacts_processed"] += 1

            contact_gid = contact.get("gid", "unknown")
            contact_name = contact.get("name", "unknown")

            # Метаданные для текущего контакта (Requirements 5.1, 5.2, 5.3)
            contact_metadata = {
                "contact_gid": contact_gid,
                "contact_name": contact_name,
                "phones_added": [],  # Список добавленных телефонов с деталями
                "phones_skipped": [],  # Список пропущенных телефонов с причинами
                "confidence_scores": [],  # Список confidence scores для каждого решения
                "decision": None,  # Решение об обогащении (reject/needs_review/auto_accept)
                "skip_reasons": [],  # Причины пропуска: low_confidence, no_org_phones, already_has_phones, mobile_only
            }

            try:
                # Edge case: Проверка наличия organization_id (Requirement 8.1)
                organization_id = contact.get("organization_id")
                if not organization_id:
                    self.logger.debug(
                        f"  ⏭️ Контакт {contact_gid} ({contact_name}): нет organization_id"
                    )
                    skip_info = {
                        "reason": "no_organization",
                        "message": "Контакт не связан с организацией",
                    }
                    contact_metadata["phones_skipped"].append(skip_info)
                    contact_metadata["skip_reasons"].append("no_organization")
                    self.stats["phones_skipped_by_reason"]["no_organization"] += 1
                    enrichment_metadata.append(contact_metadata)
                    continue

                # Edge case: Получение организации по ID (Requirement 8.2)
                organization = org_index.get(organization_id)
                if not organization:
                    self.logger.warning(
                        f"  ⚠️ Контакт {contact_gid} ({contact_name}): "
                        f"организация {organization_id} не найдена"
                    )
                    skip_info = {
                        "reason": "organization_not_found",
                        "message": f"Организация {organization_id} не найдена",
                    }
                    contact_metadata["phones_skipped"].append(skip_info)
                    contact_metadata["skip_reasons"].append("no_organization")
                    self.stats["phones_skipped_by_reason"]["no_organization"] += 1
                    enrichment_metadata.append(contact_metadata)
                    continue

                org_gid = organization.get("gid", organization_id)
                org_name = organization.get("name", "unknown")

                self.logger.debug(
                    f"\n  🔍 Обработка контакта: {contact_name} (gid: {contact_gid})"
                )
                self.logger.debug(f"     Связан с организацией: {org_name} (id: {organization_id}, gid: {org_gid})")

                # Edge case: Проверка наличия телефонов у организации (Requirement 8.3)
                org_phones = organization.get("phones", [])
                if not org_phones:
                    self.logger.debug(
                        f"  ⏭️ Организация {org_name} не имеет телефонов"
                    )
                    skip_info = {
                        "reason": "no_org_phones",
                        "message": "Организация не имеет телефонов",
                    }
                    contact_metadata["phones_skipped"].append(skip_info)
                    contact_metadata["skip_reasons"].append("no_org_phones")
                    self.stats["phones_skipped_by_reason"]["no_org_phones"] += 1
                    enrichment_metadata.append(contact_metadata)
                    continue

                # Вычисление confidence score (Requirement 2.1-2.5)
                # TODO: Передать attachment_context когда будет доступен
                confidence = self._calculate_enrichment_confidence(contact, organization)
                confidence_scores.append(confidence)
                contact_metadata["confidence_scores"].append(confidence)

                # Определяем, есть ли у организации mobile телефоны
                has_mobile_phones = any(p.get('type') == 'mobile' for p in org_phones)
                
                # Определяем минимальный порог для этого контакта
                # Если есть mobile телефоны и mobile обогащение включено, используем mobile порог
                effective_threshold = self.min_confidence_threshold
                if has_mobile_phones and self.mobile_enrichment_enabled:
                    effective_threshold = min(self.min_confidence_threshold, self.mobile_min_confidence)
                    self.logger.debug(
                        f"  📱 Организация имеет mobile телефоны, используем порог: {effective_threshold}"
                    )

                # Принятие решения на основе confidence (Requirement 2.6-2.8)
                decision = self._make_enrichment_decision(confidence, contact_gid, org_gid)
                contact_metadata["decision"] = decision

                # Проверяем, достаточен ли confidence для обогащения
                if confidence < effective_threshold:
                    skip_info = {
                        "reason": "low_confidence",
                        "message": f"Низкий уровень уверенности ({confidence:.2f} < {effective_threshold})",
                        "confidence": confidence,
                    }
                    contact_metadata["phones_skipped"].append(skip_info)
                    contact_metadata["skip_reasons"].append("low_confidence")
                    self.stats["phones_skipped_by_reason"]["low_confidence"] += 1
                    enrichment_metadata.append(contact_metadata)
                    self.logger.debug(
                        f"  ❌ Обогащение отклонено: confidence {confidence:.2f} < {effective_threshold}"
                    )
                    continue

                # Определяем, разрешено ли mobile обогащение для этого контакта
                is_mobile_enrichment = False
                if self.mobile_enrichment_enabled and has_mobile_phones:
                    # Проверяем, достаточен ли confidence для mobile обогащения
                    if confidence >= self.mobile_min_confidence:
                        is_mobile_enrichment = True
                        self.logger.debug(
                            f"  📱 Mobile обогащение разрешено: confidence {confidence:.2f} >= {self.mobile_min_confidence}"
                        )
                    else:
                        self.logger.debug(
                            f"  🚫 Mobile обогащение запрещено: confidence {confidence:.2f} < {self.mobile_min_confidence}"
                        )

                # Фильтрация телефонов организации (Requirement 3.1-3.4)
                filtered_phones = self._filter_organization_phones(org_phones, is_mobile_enrichment)

                if not filtered_phones:
                    self.logger.debug(
                        f"  ⏭️ Нет подходящих телефонов после фильтрации"
                    )
                    skip_info = {
                        "reason": "no_suitable_phones",
                        "message": "Нет подходящих телефонов после фильтрации",
                    }
                    contact_metadata["phones_skipped"].append(skip_info)
                    contact_metadata["skip_reasons"].append("mobile_only")
                    enrichment_metadata.append(contact_metadata)
                    continue

                # Edge case: Инициализация phones если null (Requirement 8.5)
                if contact.get("phones") is None:
                    self.logger.debug(
                        f"  🔧 Инициализация пустого массива phones для контакта {contact_gid}"
                    )
                    contact["phones"] = []

                contact_phones = contact.get("phones", [])

                # Добавление телефонов с проверкой дубликатов
                phones_added_count = 0

                for org_phone in filtered_phones:
                    # Проверка дубликатов (Requirement 4.1-4.4)
                    duplicate_check = self._check_phone_duplicate(contact_phones, org_phone)

                    if duplicate_check["is_duplicate"]:
                        contact_metadata["phones_skipped"].append(
                            {
                                "phone": org_phone.get("normalized"),
                                "reason": duplicate_check["reason"],
                                "message": "Телефон уже существует у контакта",
                            }
                        )
                        self.stats["phones_skipped_total"] += 1
                        continue

                    # Создание обогащенного телефона с метаданными (Requirement 1.5, 5.2)
                    enriched_phone = self._create_enriched_phone(
                        org_phone, org_gid, org_name, confidence
                    )

                    # Добавление телефона контакту
                    contact_phones.append(enriched_phone)
                    phones_added_count += 1
                    self.stats["phones_added_total"] += 1

                    # Логирование добавленного телефона
                    contact_metadata["phones_added"].append(
                        {
                            "phone": enriched_phone.get("normalized"),
                            "type": enriched_phone.get("type"),
                            "confidence": confidence,
                            "source": "org_enrichment",
                        }
                    )

                    self.logger.debug(
                        f"  ✅ Добавлен телефон: {enriched_phone.get('normalized')} "
                        f"(type: {enriched_phone.get('type')}, confidence: {confidence:.2f})"
                    )

                # Обновление статистики
                if phones_added_count > 0:
                    self.stats["contacts_enriched"] += 1
                    self.logger.info(
                        f"  ✅ Контакт {contact_name} обогащен: добавлено {phones_added_count} телефонов"
                    )
                else:
                    self.logger.debug(
                        f"  ⏭️ Контакт {contact_name}: телефоны не добавлены"
                    )

                enrichment_metadata.append(contact_metadata)

            except Exception as e:
                # Edge case: Обработка исключений (Requirement 8.6)
                self.logger.error(
                    f"  ❌ Ошибка при обогащении контакта {contact_gid} ({contact_name}): {e}",
                    exc_info=True,
                )
                contact_metadata["error"] = {
                    "message": str(e),
                    "type": type(e).__name__,
                }
                enrichment_metadata.append(contact_metadata)
                # Продолжаем обработку следующего контакта
                continue

        # Вычисление средней уверенности
        if confidence_scores:
            self.stats["avg_confidence"] = sum(confidence_scores) / len(confidence_scores)

        # Итоговая статистика
        self.logger.info(
            f"\n📊 Обогащение завершено:\n"
            f"  • Обработано контактов: {self.stats['contacts_processed']}\n"
            f"  • Обогащено контактов: {self.stats['contacts_enriched']}\n"
            f"  • Добавлено телефонов: {self.stats['phones_added_total']}\n"
            f"  • Пропущено телефонов: {self.stats['phones_skipped_total']}\n"
            f"  • Средняя уверенность: {self.stats['avg_confidence']:.2f}\n"
            f"  • Причины пропуска: {self.stats['phones_skipped_by_reason']}"
        )

        # Формируем полную структуру метаданных (Requirements 5.1-5.4)
        return self.get_enrichment_metadata_summary(enrichment_metadata)

    def _create_enriched_phone(
        self, org_phone: Dict[str, Any], org_gid: str, org_name: str, confidence: float
    ) -> Dict[str, Any]:
        """
        Создает обогащенный телефон с метаданными для постобработки и UI

        Добавляет метаданные согласно Requirement 1.5, 5.2:
        - source: "org_enrichment"
        - org_gid: "<organization_gid>"
        - confidence: <score>
        - enriched_at: <timestamp>
        - ui_metadata: метаданные для отображения в UI (иконка источника)

        Args:
            org_phone: Телефон организации
            org_gid: Global ID организации
            org_name: Название организации (для UI tooltip)
            confidence: Уровень уверенности обогащения

        Returns:
            Dict: Телефон с добавленными метаданными
        """
        # Создаем копию телефона организации
        enriched_phone = org_phone.copy()

        # Удаляем служебные поля, если они есть
        enriched_phone.pop("confidence_adjustment", None)
        enriched_phone.pop("_original_type", None)
        is_mobile_enrichment = enriched_phone.pop("_is_mobile_enrichment", False)

        # Добавляем метаданные обогащения (Requirement 1.5, 5.2)
        enriched_phone["source"] = "org_enrichment"
        enriched_phone["org_gid"] = org_gid
        enriched_phone["confidence"] = round(confidence, 2)
        enriched_phone["enriched_at"] = datetime.utcnow().isoformat()

        # Добавляем UI метаданные для отображения иконки источника
        enriched_phone["ui_metadata"] = {
            "source_type": "organization",  # Тип источника для выбора иконки
            "source_name": org_name,  # Название организации для tooltip
            "enrichment_method": "postprocessing",  # Метод обогащения
            "icon": "building",  # Тип иконки (здание организации)
            "is_mobile_enrichment": is_mobile_enrichment,  # Флаг mobile обогащения
        }

        return enriched_phone

    def get_enrichment_metadata_summary(
        self, enrichment_metadata: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Создает сводку метаданных обогащения для интеграции с PostProcessor

        Формирует структуру согласно Requirements 5.1, 5.2, 5.3, 5.4:
        - Метаданные по каждому контакту
        - Причины пропуска
        - Confidence scores
        - Общая статистика

        Args:
            enrichment_metadata: Список метаданных по контактам

        Returns:
            Dict: Сводка метаданных для contact_phone_enrichment секции
        """
        summary = {
            "contacts": enrichment_metadata,
            "statistics": self.get_stats(),
            "timestamp": datetime.utcnow().isoformat(),
            "config": {
                "enabled": self.enabled,
                "enrichment_mode": self.enrichment_mode,
                "min_confidence_threshold": self.min_confidence_threshold,
                "review_threshold": self.review_threshold,
                "allowed_phone_types": self.allowed_phone_types,
            },
        }

        return summary
