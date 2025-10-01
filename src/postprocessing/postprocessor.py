#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный координатор постобработки данных LLM
Реализует полный алгоритм постобработки согласно мини-ТЗ

Author: Contact Parser Team
Created: 2025-09-13
"""

import logging
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

try:
    import yaml
except ImportError as exc:
    raise ImportError(
        "PyYAML is required for email classification. Install it via 'pip install PyYAML'."
    ) from exc

from .organization_deduplicator import OrganizationDeduplicator
from .contact_filter import ContactFilter
from .data_enricher import DataEnricher
from .data_normalizer import DataNormalizer
from .advanced_contact_deduplicator import AdvancedContactDeduplicator
from .smart_contact_enricher import SmartContactEnricher
from .email_classifier import MailboxType, classify_mailbox

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent


class PostProcessor:
    """Главный координатор постобработки данных LLM
    
    Реализует полный алгоритм согласно мини-ТЗ п.3:
    1. Дедупликация и объединение организаций (п.3.a)
    2. Обновление organization_id в контактах (п.3.b)
    3. Фильтрация ценных контактов (п.3.c)
    3.1 Мягкий backfill города/адреса из организации
    4. Обогащение полей (Smart + Data enricher, п.3.e)
    5. Нормализация данных (п.3.f)
    """
    
    def __init__(self, 
                 organization_deduplicator: Optional[OrganizationDeduplicator] = None,
                 contact_filter: Optional[ContactFilter] = None,
                 data_enricher: Optional[DataEnricher] = None,
                 data_normalizer: Optional[DataNormalizer] = None,
                 contact_deduplicator: Optional[AdvancedContactDeduplicator] = None):
        """Инициализация постпроцессора
        
        Args:
            organization_deduplicator: Дедупликатор организаций
            contact_filter: Фильтр контактов
            data_enricher: Обогатитель данных
            data_normalizer: Нормализатор данных
        """
        self.org_deduplicator = organization_deduplicator or OrganizationDeduplicator()
        self.contact_filter = contact_filter or ContactFilter()
        # Используем SmartContactEnricher вместо обычного DataEnricher
        self.data_enricher = data_enricher or DataEnricher()
        self.smart_enricher = SmartContactEnricher()
        self.data_normalizer = data_normalizer or DataNormalizer()
        self.contact_deduplicator = contact_deduplicator or AdvancedContactDeduplicator()
        self.logger = logging.getLogger(__name__)

        # Управляемый бэкфилл города/адреса контактов из организации
        self.backfill_city_from_org = self._read_bool_env(
            'POSTPROCESSOR_BACKFILL_CITY_FROM_ORG',
            default=True
        )
        self.backfill_address_from_org = self._read_bool_env(
            'POSTPROCESSOR_BACKFILL_ADDRESS_FROM_ORG',
            default=False
        )

        # Управляемая фильтрация email организационных ящиков
        self.keep_only_shared_org_emails = self._read_bool_env(
            'POSTPROCESSOR_KEEP_ONLY_SHARED_ORG_EMAILS',
            default=True,
        )
        self.demote_personal_org_emails_to_contacts = self._read_bool_env(
            'POSTPROCESSOR_DEMOTE_PERSONAL_ORG_EMAILS',
            default=True,
        )
        default_classifier_path = REPO_ROOT / 'config' / 'org_profile.yml'
        self.email_classifier_config_path = os.getenv(
            'POSTPROCESSOR_EMAIL_CLASSIFIER_CONFIG',
            str(default_classifier_path),
        )
        self._email_classifier_assets: Optional[Tuple[Dict[str, Any], Set[str]]] = None
        self.email_classification_stats = {
            'counts': Counter(),
            'removed_total': 0,
            'kept_total': 0,
        }
        self.email_classification_log: Dict[int, Dict[str, Any]] = {}

        # Статистика обработки
        self.stats = {
            'processed_emails': 0,
            'total_organizations_processed': 0,
            'total_contacts_processed': 0,
            'organizations_deduplicated': 0,
            'contacts_filtered': 0,
            'contacts_enriched': 0,
            'data_normalized': 0
        }
        self.organization_mapping: Dict[int, int] = {}
        self.contact_mapping: Dict[int, int] = {}

        self._configure_deduplicator_email_filter()

    def _read_bool_env(self, env_name: str, default: bool) -> bool:
        """🧭 Читает булевый флаг из переменных окружения."""
        raw_value = os.getenv(env_name)
        if raw_value is None:
            return default
        normalized = raw_value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        return default

    def _configure_deduplicator_email_filter(self) -> None:
        if not self.keep_only_shared_org_emails:
            return
        cfg, corp_domains = self._get_email_classifier_assets()
        allowed_types = {
            MailboxType.SHARED_ORG,
            MailboxType.DEPARTMENT,
            MailboxType.GROUP_ALIAS,
            MailboxType.TECHNICAL,
        }
        if hasattr(self.org_deduplicator, 'configure_email_classifier'):
            self.org_deduplicator.configure_email_classifier(cfg, corp_domains, allowed_types)

    def _get_email_classifier_assets(self) -> Tuple[Dict[str, Any], Set[str]]:
        if self._email_classifier_assets is not None:
            return self._email_classifier_assets

        cfg: Dict[str, Any] = {}
        corp_domains: Set[str] = set()
        config_path = Path(self.email_classifier_config_path)
        if config_path.exists():
            try:
                with config_path.open('r', encoding='utf-8') as handle:
                    loaded = yaml.safe_load(handle) or {}
                    if isinstance(loaded, dict):
                        cfg = loaded
                        corp_domains = {str(domain).lower() for domain in loaded.get('internal_domains', [])}
            except Exception as exc:
                self.logger.warning("⚠️ Не удалось загрузить конфиг email классификатора: %s", exc)

        self._email_classifier_assets = (cfg, corp_domains)
        return self._email_classifier_assets

    def _build_contact_email_index(self, contacts: List[Dict[str, Any]]) -> Set[Tuple[int, str]]:
        index: Set[Tuple[int, str]] = set()
        for contact in contacts:
            email = contact.get('email')
            org_id = contact.get('organization_id')
            if not email or not isinstance(org_id, int):
                continue
            index.add((org_id, str(email).strip().lower()))
        return index

    def _cleanup_organization_emails(
        self,
        organizations: Dict[int, Dict[str, Any]],
        contacts: List[Dict[str, Any]],
    ) -> Dict[int, Dict[str, Any]]:
        if not self.keep_only_shared_org_emails:
            return {}

        cfg, corp_domains = self._get_email_classifier_assets()
        classification_log: Dict[int, Dict[str, Any]] = {}
        contact_index = self._build_contact_email_index(contacts)
        allowed_types = {
            MailboxType.SHARED_ORG,
            MailboxType.DEPARTMENT,
            MailboxType.GROUP_ALIAS,
            MailboxType.TECHNICAL,
        }

        for org_id, org_payload in organizations.items():
            emails = org_payload.get('emails') or []
            if not isinstance(emails, list):
                continue

            kept: List[str] = []
            removed: List[str] = []
            removed_types: Dict[str, str] = {}
            quarantine: List[str] = []

            for raw_email in emails:
                email_str = str(raw_email or '').strip()
                if not email_str:
                    continue

                mailbox_type = classify_mailbox(email_str, None, corp_domains, cfg)
                self.email_classification_stats['counts'][mailbox_type.value] += 1

                if mailbox_type in allowed_types:
                    kept.append(email_str)
                    self.email_classification_stats['kept_total'] += 1
                    continue

                removed.append(email_str)
                removed_types[email_str] = mailbox_type.value
                self.email_classification_stats['removed_total'] += 1

                if (
                    self.demote_personal_org_emails_to_contacts
                    and mailbox_type == MailboxType.PERSONAL_INTERNAL
                    and (org_id, email_str.lower()) not in contact_index
                ):
                    quarantine.append(email_str)

            org_payload['emails'] = kept
            if org_id in self.org_deduplicator.global_organizations:
                self.org_deduplicator.global_organizations[org_id]['emails'] = kept

            classification_log[org_id] = {
                'kept': kept,
                'removed': removed,
                'removed_types': removed_types,
            }
            if quarantine:
                classification_log[org_id]['quarantine'] = quarantine

        self.email_classification_log = classification_log
        if classification_log:
            kept_total = sum(len(entry['kept']) for entry in classification_log.values())
            removed_total = sum(len(entry['removed']) for entry in classification_log.values())
            self.logger.info(
                "📬 Фильтрация email организаций: оставлено %s, удалено %s",
                kept_total,
                removed_total,
            )
        return classification_log

    def process_llm_response(self, llm_result: Dict[str, Any], 
                           email_data: Optional[Dict[str, Any]] = None,
                           existing_organizations: Optional[Dict[int, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Полная постобработка ответа LLM
        
        Args:
            llm_result: Результат от LLM в новом формате
            email_data: Данные исходного email для обогащения
            existing_organizations: Предзагруженный справочник организаций
            
        Returns:
            Dict: Обработанный результат
        """
        self.logger.info("🔄 Начало постобработки ответа LLM")
        
        try:
            self._reset_runtime_state()
            # Валидация входных данных
            if not self._validate_llm_result(llm_result):
                raise ValueError("Некорректная структура LLM результата")

            # Применяем критические исправления в начале обработки
            llm_result = self._apply_critical_fixes(llm_result)

            if existing_organizations:
                self.org_deduplicator.load_existing_organizations(existing_organizations)
            
            # Этап 1: Дедупликация и объединение организаций (п.3.a)
            organizations_mapping = self._process_organizations(
                llm_result.get('organizations', [])
            )
            self.organization_mapping = organizations_mapping
            # Этап 2: Обновление organization_id в контактах (п.3.b)
            updated_contacts = self._update_contact_organization_ids(
                llm_result.get('contacts', []), organizations_mapping
            )
            
            # Этап 2.5: Дедупликация контактов
            deduplicated_contacts, contact_mapping = self._deduplicate_contacts(updated_contacts)
            self.contact_mapping = contact_mapping

            # Этап 3: Фильтрация ценных контактов (п.3.c)
            valuable_contacts, updated_organizations = self._filter_valuable_contacts(
                deduplicated_contacts
            )

            # Этап 3.1: Мягкий бэкфилл города/адреса из организации (управляемый)
            contacts_after_backfill, provenance = self._backfill_contact_city_address(
                valuable_contacts,
                updated_organizations
            )

            email_classification_log = self._cleanup_organization_emails(
                updated_organizations,
                contacts_after_backfill,
            )
            
            # Этап 4: Обогащение данных (п.3.e)
            enriched_contacts = self._enrich_contact_data(
                contacts_after_backfill, updated_organizations, email_data
            )
            
            # Этап 5: Нормализация данных (п.3.f)
            final_contacts, final_organizations = self._normalize_data(
                enriched_contacts, updated_organizations
            )
            
            # Этап 6: Обновление interactions
            processed_interactions = self._process_interactions(
                llm_result.get('interactions', []),
                final_contacts,
                final_organizations
            )

            summary = self._sanitize_summary(llm_result.get('summary'))
            key_points = self._sanitize_key_points(llm_result.get('key_points'))
            business_context = llm_result.get('business_context') or ""
            filtered_offers = self._filter_commercial_offers(
                llm_result.get('commercial_offers', []),
                email_data
            )

            # Формирование финального результата
            processed_result = self._build_final_result(
                llm_result,
                final_contacts,
                final_organizations,
                processed_interactions,
                summary,
                key_points,
                business_context,
                filtered_offers,
                provenance,
                email_classification_log,
            )
            
            # Обновление статистики
            self._update_stats(llm_result, processed_result)
            
            self.logger.info("✅ Постобработка завершена успешно")
            return processed_result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при постобработке: {str(e)}")
            # Возвращаем оригинальный результат в случае ошибки
            return llm_result

    def _reset_runtime_state(self) -> None:
        """Сброс временных структур перед обработкой"""
        self.organization_mapping = {}
        self.contact_mapping = {}
        # КРИТИЧНО: Очищаем состояние дедупликатора организаций
        self.org_deduplicator.reset_state()
        self.logger.info("🔄 Состояние постпроцессора сброшено для нового письма")
        self.email_classification_stats = {
            'counts': Counter(),
            'removed_total': 0,
            'kept_total': 0,
        }
        self.email_classification_log = {}

    def _validate_llm_result(self, llm_result: Dict[str, Any]) -> bool:
        """Валидация структуры LLM результата
        
        Args:
            llm_result: Результат от LLM
            
        Returns:
            bool: Валиден ли результат
        """
        required_fields = ['organizations', 'contacts']
        
        for field in required_fields:
            if field not in llm_result:
                self.logger.error(f"Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем, что organizations и contacts - это списки
        if not isinstance(llm_result['organizations'], list):
            self.logger.error("Поле 'organizations' должно быть списком")
            return False
            
        if not isinstance(llm_result['contacts'], list):
            self.logger.error("Поле 'contacts' должно быть списком")
            return False
        
        return True
    
    def _process_organizations(self, organizations: List[Dict[str, Any]]) -> Dict[int, int]:
        """Этап 1: Дедупликация и объединение организаций
        
        Args:
            organizations: Список организаций из LLM
            
        Returns:
            Dict[int, int]: Маппинг локальных -> глобальных ID
        """
        self.logger.info(f"🏢 Этап 1: Обработка {len(organizations)} организаций")
        
        mapping = self.org_deduplicator.process_organizations(organizations)
        
        self.stats['total_organizations_processed'] += len(organizations)
        self.stats['organizations_deduplicated'] += len(organizations) - len(set(mapping.values()))
        
        self.logger.info(f"✅ Создан маппинг для {len(mapping)} организаций")
        return mapping
    
    def _update_contact_organization_ids(self, contacts: List[Dict[str, Any]], 
                                       mapping: Dict[int, int]) -> List[Dict[str, Any]]:
        """Этап 2: Обновление organization_id в контактах
        
        Args:
            contacts: Список контактов
            mapping: Маппинг локальных -> глобальных ID
            
        Returns:
            List[Dict]: Контакты с обновленными ID
        """
        self.logger.info(f"👤 Этап 2: Обновление organization_id в {len(contacts)} контактах")
        
        updated_contacts = []
        
        for contact in contacts:
            updated_contact = contact.copy()
            local_id = contact.get('organization_id')
            
            if local_id in mapping:
                updated_contact['organization_id'] = mapping[local_id]
                self.logger.debug(f"Обновлен organization_id: {local_id} -> {mapping[local_id]}")
            else:
                self.logger.warning(f"Не найден маппинг для organization_id: {local_id}")
            
            updated_contacts.append(updated_contact)
        
        return updated_contacts
    
    def _filter_valuable_contacts(self, contacts: List[Dict[str, Any]]) -> tuple:
        """Этап 3: Фильтрация ценных контактов
        
        Args:
            contacts: Список контактов для фильтрации
            
        Returns:
            tuple: (ценные контакты, обновленные организации)
        """
        self.logger.info(f"🔍 Этап 3: Фильтрация {len(contacts)} контактов")
        
        # Получаем текущие организации
        current_organizations = {
            org_id: org for org_id, org in self.org_deduplicator.get_global_organizations().items()
        }
        
        valuable_contacts, updated_organizations = self.contact_filter.filter_valuable_contacts(
            contacts, current_organizations
        )
        
        # Обновляем организации в дедупликаторе без служебных полей
        sanitized_updates = {
            org_id: self.org_deduplicator._strip_internal_fields(org)
            for org_id, org in updated_organizations.items()
        }
        self.org_deduplicator.global_organizations.update(sanitized_updates)
        
        filtered_count = len(contacts) - len(valuable_contacts)
        self.stats['total_contacts_processed'] += len(contacts)
        self.stats['contacts_filtered'] += filtered_count
        
        self.logger.info(f"✅ Отфильтровано {filtered_count} неценных контактов")
        return valuable_contacts, sanitized_updates

    def _deduplicate_contacts(self, contacts: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[int, int]]:
        """Дедупликация контактов с сохранением маппинга ID"""
        if not contacts:
            return [], {}

        deduplicated = self.contact_deduplicator.deduplicate_contacts(contacts)
        mapping = self.contact_deduplicator.get_last_mapping()
        return deduplicated, mapping

    def _backfill_contact_city_address(
        self,
        contacts: List[Dict[str, Any]],
        organizations: Dict[int, Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, str]]]:
        """🌐 Мягкое обогащение города/адреса контактов из организации."""

        if not contacts:
            return [], {}

        provenance: Dict[int, Dict[str, str]] = {}
        updated_contacts: List[Dict[str, Any]] = []

        for contact in contacts:
            normalized_contact = dict(contact)
            cid = normalized_contact.get('contact_id')
            oid = normalized_contact.get('organization_id')
            organization = organizations.get(oid) if isinstance(oid, int) else None
            provenance_entry: Dict[str, str] = {}

            if organization:
                if self.backfill_city_from_org and not self._has_value(normalized_contact.get('city')):
                    org_city = organization.get('city')
                    if self._has_value(org_city):
                        normalized_contact['city'] = org_city.strip()
                        provenance_entry['city_source'] = 'org_fallback'

                if self.backfill_address_from_org and not self._has_value(normalized_contact.get('address')):
                    org_address = organization.get('address')
                    if self._has_value(org_address):
                        normalized_contact['address'] = org_address.strip()
                        provenance_entry['address_source'] = 'org_fallback'

            if provenance_entry and isinstance(cid, int):
                provenance[cid] = provenance_entry

            updated_contacts.append(normalized_contact)

        return updated_contacts, provenance

    @staticmethod
    def _has_value(value: Any) -> bool:
        """🔍 Проверяет, что значение не пустое."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    def _enrich_contact_data(self, contacts: List[Dict[str, Any]], 
                           organizations: Dict[int, Dict[str, Any]],
                           email_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Этап 4: Обогащение данных контактов

        Args:
            contacts: Список контактов
            organizations: Словарь организаций
            email_data: Данные email
            
        Returns:
            List[Dict]: Обогащенные контакты
        """
        self.logger.info(f"💎 Этап 4: Обогащение {len(contacts)} контактов")
        
        # Используем SmartContactEnricher для улучшенного обогащения
        enriched_contacts = self.smart_enricher.enrich_contacts(
            contacts, organizations, email_data
        )
        
        # Дополнительное обогащение через стандартный enricher
        enriched_contacts = self.data_enricher.enrich_contacts(
            enriched_contacts, organizations, email_data
        )

        self.stats['contacts_enriched'] += len(enriched_contacts)

        enrichment_stats = self.data_enricher.get_enrichment_stats()
        websites_found = enrichment_stats.get('websites_extracted', 0)
        inns_validated = enrichment_stats.get('inns_validated', 0)
        self.logger.info(
            "✅ Обогащено %s контактов (🌐 сайтов: %s, 🧾 ИНН: %s)",
            len(enriched_contacts),
            websites_found,
            inns_validated,
        )
        return enriched_contacts
    
    def _normalize_data(self, contacts: List[Dict[str, Any]], 
                       organizations: Dict[int, Dict[str, Any]]) -> tuple:
        """Этап 5: Нормализация данных
        
        Args:
            contacts: Список контактов
            organizations: Словарь организаций
            
        Returns:
            tuple: (нормализованные контакты, нормализованные организации)
        """
        self.logger.info(f"🔧 Этап 5: Нормализация данных")
        
        normalized_contacts = self.data_normalizer.normalize_contacts(contacts)
        normalized_organizations = self.data_normalizer.normalize_organizations(organizations)
        
        self.stats['data_normalized'] += len(normalized_contacts) + len(normalized_organizations)
        
        self.logger.info(f"✅ Нормализовано {len(normalized_contacts)} контактов и {len(normalized_organizations)} организаций")
        return normalized_contacts, normalized_organizations

    def _process_interactions(self, interactions: Optional[List[Dict[str, Any]]],
                              contacts: List[Dict[str, Any]],
                              organizations: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Приведение interactions к актуальным идентификаторам и структуре"""
        if not interactions:
            return []

        allowed_types = {
            "requested_quote",
            "sent_quote",
            "follow_up",
            "clarification",
            "complaint",
            "invoice_sent",
            "invoice_paid",
            "contract_sent",
            "contract_signed",
            "delivery",
            "support",
            "other"
        }

        valid_contact_ids = {
            contact.get('contact_id') for contact in contacts
            if isinstance(contact.get('contact_id'), int)
        }
        organization_ids = set(organizations.keys())
        fallback_org_id = next(iter(organization_ids), None)

        processed: List[Dict[str, Any]] = []
        for index, interaction in enumerate(interactions, 1):
            if not isinstance(interaction, dict):
                continue

            item = interaction.copy()
            contact_id = item.get('contact_id')
            if contact_id in self.contact_mapping:
                item['contact_id'] = self.contact_mapping[contact_id]

            if item.get('contact_id') not in valid_contact_ids:
                continue

            org_id = item.get('organization_id')
            if org_id in self.organization_mapping:
                item['organization_id'] = self.organization_mapping[org_id]

            if item.get('organization_id') not in organization_ids:
                if fallback_org_id is None:
                    continue
                item['organization_id'] = fallback_org_id

            item['interaction_local_id'] = item.get('interaction_local_id') or index
            item['role_in_message'] = str(item.get('role_in_message') or 'other').lower()

            interaction_type = str(item.get('interaction_type') or 'other').lower()
            if interaction_type not in allowed_types:
                interaction_type = 'other'
            item['interaction_type'] = interaction_type

            attachments = item.get('attachments', [])
            if not isinstance(attachments, list):
                attachments = [attachments] if attachments else []
            item['attachments'] = [str(att).strip() for att in attachments if att]

            try:
                confidence = float(item.get('confidence', 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            item['confidence'] = max(0.0, min(1.0, confidence))

            if item.get('message_date'):
                item['message_date'] = str(item['message_date']).strip()

            processed.append(item)

        return processed

    def _sanitize_summary(self, summary: Optional[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        """Гарантия структуры summary блока"""
        template = {
            'topic': None,
            'product_interest': None,
            'communication_stage': None,
            'request_type': None
        }

        if not isinstance(summary, dict):
            return template

        sanitized = {}
        for key in template:
            value = summary.get(key)
            if value is None:
                sanitized[key] = None
            else:
                text = str(value).strip()
                sanitized[key] = text if text else None

        return sanitized

    def _sanitize_key_points(self, key_points: Optional[List[Any]]) -> List[str]:
        """Очистка списка ключевых пунктов"""
        if not isinstance(key_points, list):
            return []

        sanitized: List[str] = []
        for point in key_points:
            if point is None:
                continue
            text = str(point).strip()
            if text:
                sanitized.append(text)
            if len(sanitized) >= 5:
                break

        return sanitized

    def _filter_commercial_offers(self, offers: Any, email_metadata: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Фильтрация коммерческих предложений по наличию фактических КП."""
        if not isinstance(offers, list) or not offers:
            return []

        attachments_count = 0
        if isinstance(email_metadata, dict):
            attachments_count = email_metadata.get('attachments_count') or 0
        if attachments_count <= 0:
            self.logger.info("   💼 КП отклонены: вложения отсутствуют")
            return []

        filtered: List[Dict[str, Any]] = []
        for offer in offers:
            if not isinstance(offer, dict):
                continue
            if not offer.get('found'):
                continue

            equipment_items = offer.get('equipment_items') or []
            if not isinstance(equipment_items, list):
                continue

            normalized_items: List[Dict[str, Any]] = []
            for item in equipment_items:
                if not isinstance(item, dict):
                    continue

                quantity = self._coerce_positive_float(item.get('quantity'))
                unit_price = self._coerce_positive_float(item.get('unit_price'))
                total_price = self._coerce_positive_float(item.get('total_price'))

                if quantity is None or unit_price is None:
                    continue

                if total_price is None:
                    total_price = round(quantity * unit_price, 2)

                normalized_item = item.copy()
                normalized_item['quantity'] = int(round(quantity))
                normalized_item['unit_price'] = unit_price
                normalized_item['total_price'] = total_price
                normalized_items.append(normalized_item)

            if not normalized_items:
                continue

            normalized_offer = offer.copy()
            normalized_offer['equipment_items'] = normalized_items
            filtered.append(normalized_offer)

        if not filtered:
            self.logger.info("   💼 КП отклонены: не обнаружены позиции с ценами")

        return filtered

    def _coerce_positive_float(self, value: Any) -> Optional[float]:
        """Безопасное преобразование значения в положительное число."""
        if value in (None, "", [], {}):
            return None

        try:
            if isinstance(value, str):
                cleaned = value.replace(' ', '').replace(',', '.').strip()
                result = float(cleaned)
            else:
                result = float(value)
        except (TypeError, ValueError):
            return None

        if result <= 0:
            return None

        return result
    
    def _build_final_result(self, original_result: Dict[str, Any], 
                          final_contacts: List[Dict[str, Any]],
                          final_organizations: Dict[int, Dict[str, Any]],
                          interactions: List[Dict[str, Any]],
                          summary: Dict[str, Optional[str]],
                          key_points: List[str],
                          business_context: str,
                          commercial_offers: List[Dict[str, Any]],
                          provenance: Optional[Dict[int, Dict[str, str]]] = None,
                          email_classification: Optional[Dict[int, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Формирование финального результата
        
        Args:
            original_result: Оригинальный результат LLM
            final_contacts: Финальные контакты
            final_organizations: Финальные организации
            
        Returns:
            Dict: Финальный результат
        """
        processed_result = original_result.copy()
        
        # Обновляем обработанные данные
        sorted_org_ids = sorted(final_organizations.keys())
        processed_result['organizations'] = [final_organizations[oid] for oid in sorted_org_ids]
        processed_result['contacts'] = final_contacts
        processed_result['interactions'] = interactions
        processed_result['summary'] = summary
        processed_result['key_points'] = key_points
        processed_result['business_context'] = business_context
        processed_result['commercial_offers'] = commercial_offers
        
        # Добавляем метаданные постобработки
        processed_result['postprocessing_metadata'] = {
            'processed_at': self._get_current_timestamp(),
            'stats': self.stats.copy(),
            'version': '1.1.0',
            'organization_mapping': self.organization_mapping,
            'contact_mapping': self.contact_mapping
        }

        if provenance:
            processed_result['postprocessing_metadata']['provenance'] = {
                'contacts': provenance
            }
        if email_classification:
            processed_result['postprocessing_metadata']['email_classification'] = email_classification

        return processed_result
    
    def _update_stats(self, original_result: Dict[str, Any], 
                     processed_result: Dict[str, Any]) -> None:
        """Обновление статистики обработки
        
        Args:
            original_result: Оригинальный результат
            processed_result: Обработанный результат
        """
        self.stats['processed_emails'] += 1
        
        # Дополнительная статистика
        original_orgs = len(original_result.get('organizations', []))
        final_orgs = len(processed_result.get('organizations', []))
        
        original_contacts = len(original_result.get('contacts', []))
        final_contacts = len(processed_result.get('contacts', []))
        
        self.logger.info(f"📊 Статистика обработки:")
        self.logger.info(f"  Организации: {original_orgs} -> {final_orgs}")
        self.logger.info(f"  Контакты: {original_contacts} -> {final_contacts}")
    
    def _apply_critical_fixes(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔧 Применение критических исправлений к результату LLM
        
        Исправляет:
        1. None значения в числовых полях (ошибка "NoneType * float")
        2. Некорректные символы в полях JSON (китайские символы)
        
        Args:
            llm_result: Результат от LLM
            
        Returns:
            Dict: Исправленный результат
        """
        self.logger.debug("🔧 Применяю критические исправления")
        
        try:
            from ..core.safe_math_utils import fix_none_values_in_data, sanitize_json_fields  # локальный импорт во избежание циклов

            # 1. Очистка полей от некорректных символов (email_022 fix)
            cleaned_result = sanitize_json_fields(llm_result)
            
            # 2. Исправление None значений в числовых полях (email_014 fix)
            fixed_result = fix_none_values_in_data(cleaned_result)
            
            self.logger.debug("✅ Критические исправления применены успешно")
            return fixed_result
            
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка при применении критических исправлений: {e}")
            # Возвращаем оригинальный результат если исправления не удались
            return llm_result
    
    def _get_current_timestamp(self) -> str:
        """Получение текущего timestamp
        
        Returns:
            str: Текущее время в формате ISO
        """
        from datetime import datetime
        return datetime.now().isoformat()

    def get_email_classification_stats(self) -> Dict[str, Any]:
        """Возвращает статистику классификации email."""
        return {
            'counts': dict(self.email_classification_stats['counts']),
            'removed_total': self.email_classification_stats['removed_total'],
            'kept_total': self.email_classification_stats['kept_total'],
            'log': self.email_classification_log,
        }

    def get_processing_stats(self) -> Dict[str, Any]:
        """Получение статистики обработки
        
        Returns:
            Dict: Полная статистика
        """
        base_stats = self.stats.copy()
        
        # Добавляем статистику компонентов
        base_stats['organization_deduplicator'] = self.org_deduplicator.get_stats()
        base_stats['contact_filter'] = self.contact_filter.get_filter_stats([])
        base_stats['data_enricher'] = self.data_enricher.get_enrichment_stats()
        base_stats['data_normalizer'] = self.data_normalizer.get_normalization_stats()
        base_stats['contact_deduplicator'] = {
            'last_mapping_size': len(self.contact_mapping)
        }
        
        return base_stats
    
    def reset_stats(self) -> None:
        """Сброс статистики"""
        self.stats = {
            'processed_emails': 0,
            'total_organizations_processed': 0,
            'total_contacts_processed': 0,
            'organizations_deduplicated': 0,
            'contacts_filtered': 0,
            'contacts_enriched': 0,
            'data_normalized': 0
        }
        self.logger.info("📊 Статистика сброшена")


# Пример использования
if __name__ == "__main__":
    postprocessor = PostProcessor()
    
    # Тестовый LLM результат в новом формате
    test_llm_result = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "inn": "1901066506",
                "website": "dna-technology.ru",
                "city": "Москва",
                "address": "ул. Академика Королёва, д. 12",
                "emails": ["info@dna-technology.ru"],
                "phones": ["8 800 200-75-15"]
            },
            {
                "organization_id": 2,
                "name": "ООО ДНК-Технология",  # Дубликат
                "inn": "1901066506",
                "website": "https://dna-technology.ru",
                "emails": ["sales@dna-technology.ru"],
                "phones": []
            }
        ],
        "contacts": [
            {
                "contact_id": 101,
                "name": "Гоголева Мария",
                "organization_id": 1,
                "position": "Менеджер по продажам",
                "email": "m.gogoleva@dna-technology.ru",
                "phones": [{"type": "main", "number": "+7(495) 640-17-71"}],
                "city": None,  # Будет обогащен из организации
                "address": None,
                "confidence": 0.95
            },
            {
                "contact_id": 102,
                "name": None,  # Неценный контакт
                "organization_id": 2,
                "position": None,
                "email": "support@dna-technology.ru",
                "phones": [],
                "confidence": 0.5
            }
        ],
        "business_context": "Запрос коммерческого предложения",
        "summary": {
            "topic": "Коммерческое предложение",
            "communication_stage": "Коммерческие переговоры"
        },
        "key_points": ["Запрос КП на оборудование"],
        "commercial_offers": []
    }
    
    # Обработка
    processed_result = postprocessor.process_llm_response(test_llm_result)
    
    print("🎯 Результат постобработки:")
    print(f"Организации: {len(processed_result['organizations'])}")
    print(f"Контакты: {len(processed_result['contacts'])}")
    print(f"\n📊 Статистика: {postprocessor.get_processing_stats()}")
    
    # Детальный вывод
    print("\n🏢 Финальные организации:")
    for org in processed_result['organizations']:
        print(f"  ID {org['organization_id']}: {org['name']}")
    
    print("\n👤 Финальные контакты:")
    for contact in processed_result['contacts']:
        print(f"  {contact.get('name', 'Unknown')} (org_id: {contact.get('organization_id')})")
