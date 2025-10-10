#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный координатор постобработки данных LLM
Реализует полный алгоритм постобработки согласно мини-ТЗ

Author: Contact Parser Team
Created: 2025-09-13
"""

import copy
import logging
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
from .org_inn_resolver import OrganizationINNResolver
from .org_email_enricher import OrganizationEmailEnricher
from .attachment_evidence_extractor import AttachmentEvidenceExtractor
from .org_location_enrichment import OrgLocationEnrichment
from .contact_location_safety import ContactLocationSafety
from .contact_phone_enricher import ContactPhoneEnricher
from ..registry import GlobalIDRegistry

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent

SANITIZER_PREVIEW_LIMIT = 120
PHONE_OVERRIDES_FILENAME = "phone_overrides.yml"

AREA_CODE_CITY_MAP = {
    "495": "москва",
    "499": "москва",
    "383": "новосибирск",
    "812": "санкт-петербург",
    "343": "екатеринбург",
    "351": "челябинск",
    "861": "краснодар",
    "423": "владивосток",
    "391": "красноярск",
    "4722": "липецк",
    "831": "нижний новгород",
    "3462": "сургут",
}


def as_text(value: Any, *, default: str = "", strip: bool = True) -> str:
    """🔤 Безопасно приводит значение к строке."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip() if strip else value
    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8", errors="ignore")
        except Exception:  # pragma: no cover - крайне редкий случай
            text = str(value)
    else:
        text = str(value)
    return text.strip() if strip else text


def as_int(value: Any) -> Optional[int]:
    """🔢 Конвертирует значение в int без исключений."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not (value == value):  # NaN check
            return None
        return int(value)
    text = as_text(value)
    if not text:
        return None
    cleaned = text.replace(" ", "")
    try:
        return int(cleaned)
    except ValueError:
        try:
            return int(float(cleaned.replace(",", ".")))
        except ValueError:
            return None


def as_float(value: Any) -> Optional[float]:
    """🌊 Конвертирует значение в float без исключений."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    text = as_text(value)
    if not text:
        return None
    cleaned = text.replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def as_bool(value: Any) -> Optional[bool]:
    """✅ Конвертирует значение в bool c учётом строк."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = as_text(value).lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return None


def as_list(value: Any) -> List[Any]:
    """📋 Обеспечивает список значений."""
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return [value]


def coerce_phone_list(value: Any) -> List[Any]:
    """📞 Приводит телефон(ы) к списку.
    
    КРИТИЧЕСКИ ВАЖНО: НЕ повреждает phone objects от LLM!
    Если получаем phone объекты - возвращаем как есть.
    
    Примечание: Эта функция больше не используется для организаций,
    чтобы избежать повреждения LLM phone objects.
    """
    phones: List[Any] = []
    for item in as_list(value):
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Проверяем, является ли item phone объектом от LLM
        if isinstance(item, dict) and 'type' in item and 'number' in item:
            # Это phone объект от LLM - сохраняем как есть
            phones.append(item)
        else:
            # Это строка или другой тип - конвертируем в строку
            text = as_text(item)
            if text:
                phones.append(text)
    return phones


def safe_regex_sub(pattern: str, repl: str, value: Any) -> str:
    """🧪 Безопасная обёртка над re.sub."""
    text = as_text(value, strip=False)
    try:
        return re.sub(pattern, repl, text)
    except re.error:
        return text


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
                 contact_deduplicator: Optional[AdvancedContactDeduplicator] = None,
                 phone_overrides_path: Optional[Path] = None):
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
        self.phone_overrides_path = (
            Path(phone_overrides_path)
            if phone_overrides_path is not None
            else PROJECT_ROOT / 'registry' / PHONE_OVERRIDES_FILENAME
        )

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
        self.gid_registry = GlobalIDRegistry()
        self.phone_overrides = self._load_phone_overrides()
        
        # Инициализация ИНН резолвера
        try:
            self.inn_resolver = OrganizationINNResolver()
            self.email_enricher = OrganizationEmailEnricher()
            self.logger.info("✅ INN resolver initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to initialize INN/Email enrichers: {e}")
            self.inn_resolver = None
            self.email_enricher = None
        
        # Инициализация компонентов обогащения локации из вложений (TASK-008A)
        try:
            self.attachment_evidence_extractor = AttachmentEvidenceExtractor()
            self.org_location_enrichment = OrgLocationEnrichment()
            self.logger.info("✅ Attachment evidence extractors initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to initialize attachment evidence extractors: {e}")
            self.attachment_evidence_extractor = None
            self.org_location_enrichment = None
        
        # Инициализация компонента безопасности локации контактов (TASK-008B)
        try:
            self.contact_location_safety = ContactLocationSafety()
            self.logger.info("✅ Contact location safety initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to initialize contact location safety: {e}")
            self.contact_location_safety = None
        
        # Инициализация компонента обогащения телефонов контактов
        try:
            self.contact_phone_enricher = ContactPhoneEnricher()
            self.logger.info("✅ Contact phone enricher initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to initialize contact phone enricher: {e}")
            self.contact_phone_enricher = None

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
        parsed = as_bool(raw_value)
        if parsed is None:
            return default
        return parsed

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

    def _load_phone_overrides(self) -> Dict[str, str]:
        overrides: Dict[str, str] = {}
        if not self.phone_overrides_path.exists():
            return overrides
        try:
            with self.phone_overrides_path.open('r', encoding='utf-8') as handle:
                data = yaml.safe_load(handle) or {}
        except Exception as exc:
            self.logger.warning("⚠️ Не удалось загрузить phone_overrides: %s", exc)
            return overrides

        for item in data.get('phone_overrides', []) or []:
            phone = self._normalize_phone_key(item.get('phone'))
            gid = as_text(item.get('owner_gid'))
            if phone and gid:
                overrides[phone] = gid
        return overrides

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

            updated_organizations, valuable_contacts, gid_metadata = self._assign_global_ids(
                updated_organizations,
                valuable_contacts,
            )

            # Этап 3.1: Обогащение ИНН организаций
            inn_enrichment_metadata = self._enrich_organizations_inn(updated_organizations)
            
            # Этап 3.2: Обогащение email-адресов организаций (TASK-007B)
            org_email_enrichment_metadata = self._enrich_organizations_emails(updated_organizations, email_data)

            # Этап 3.3: Обогащение локации организаций из вложений (TASK-008A)
            location_enrichment_metadata = self._enrich_organizations_location_from_attachments(
                updated_organizations, email_data
            )
            
            # Этап 3.4: Безопасное обогащение локации контактов (TASK-008B)
            contact_location_metadata = self._apply_contact_location_safety(
                valuable_contacts, email_data, updated_organizations
            )

            phone_conflicts = self._resolve_phone_conflicts(
                updated_organizations,
                valuable_contacts,
            )
            
            # Этап 3.5: Обогащение телефонов контактов от организаций
            # Добавленные телефоны будут нормализованы на этапе 5 (_normalize_data)
            contact_phone_enrichment_metadata = self._enrich_contacts_phones(
                valuable_contacts, updated_organizations
            )

            # Этап 3.1: Мягкий бэкфилл города/адреса из организации (управляемый)
            contacts_after_backfill, provenance = self._backfill_contact_city_address(
                valuable_contacts,
                updated_organizations
            )

            self._scrub_contact_addresses(contacts_after_backfill, updated_organizations, provenance)

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
            
            # Сбор статистики phone UI форматирования
            phone_ui_stats = self._collect_phone_ui_stats(
                final_organizations, final_contacts
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
                gid_metadata,
                phone_conflicts,
                inn_enrichment_metadata,
                org_email_enrichment_metadata,
                location_enrichment_metadata,
                phone_ui_stats,
                contact_phone_enrichment_metadata,
            )
            
            # Обновление статистики
            self._update_stats(llm_result, processed_result)
            
            self.logger.info("✅ Постобработка завершена успешно")
            return processed_result
            
        except Exception as e:
            import traceback
            self.logger.error(f"❌ Ошибка при постобработке: {str(e)}")
            self.logger.error(f"📚 Traceback:\n{traceback.format_exc()}")
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

        for org in organizations:
            if not isinstance(org, dict):
                continue
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: НЕ конвертируем phone objects от LLM в строки!
            # Оставляем phones как есть - DataNormalizer корректно их обработает
            # org['phones'] = coerce_phone_list(org.get('phones'))  # УДАЛЕНО!
            org_emails = as_list(org.get('emails'))
            org['emails'] = [as_text(email) for email in org_emails if as_text(email)]

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

    def _assign_global_ids(
        self,
        organizations: Dict[int, Dict[str, Any]],
        contacts: List[Dict[str, Any]],
    ) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        gid_assignments: List[Dict[str, Any]] = []
        gid_conflicts: List[Dict[str, Any]] = []
        org_gid_lookup: Dict[int, str] = {}

        for org_id, org_payload in organizations.items():
            try:
                result = self.gid_registry.resolve_organization(org_payload)
            except ValueError:
                continue
            org_payload['gid'] = result.gid
            org_gid_lookup[org_id] = result.gid
            gid_assignments.append(
                {
                    'entity': 'organization',
                    'local_id': org_id,
                    'gid': result.gid,
                    'match_rule': result.match_rule,
                    'key_tuple': list(result.key_tuple),
                    'alias_added': result.alias_added,
                    'source': result.source,
                }
            )
            for conflict in result.conflicts:
                conflict_entry = {
                    'entity': conflict.get('entity', 'organization'),
                    'key': conflict.get('key'),
                    'existing_gid': conflict.get('existing_gid'),
                    'target_gid': conflict.get('target_gid', result.gid),
                }
                gid_conflicts.append(conflict_entry)

        for contact in contacts:
            org_id = contact.get('organization_id')
            org_gid = org_gid_lookup.get(org_id)
            if not org_gid:
                continue
            try:
                result = self.gid_registry.resolve_contact(contact, org_gid)
            except ValueError:
                continue
            contact['gid'] = result.gid
            gid_assignments.append(
                {
                    'entity': 'contact',
                    'local_id': contact.get('contact_id'),
                    'organization_id': org_id,
                    'organization_gid': org_gid,
                    'gid': result.gid,
                    'match_rule': result.match_rule,
                    'key_tuple': list(result.key_tuple),
                    'alias_added': result.alias_added,
                    'source': result.source,
                }
            )
            for conflict in result.conflicts:
                conflict_entry = {
                    'entity': conflict.get('entity', 'contact'),
                    'key': conflict.get('key'),
                    'existing_gid': conflict.get('existing_gid'),
                    'target_gid': conflict.get('target_gid', result.gid),
                }
                gid_conflicts.append(conflict_entry)

        gid_metadata = {
            'assigned': gid_assignments,
            'conflicts': gid_conflicts,
        }
        return organizations, contacts, gid_metadata

    def _resolve_phone_conflicts(
        self,
        organizations: Dict[int, Dict[str, Any]],
        contacts: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        conflicts: Dict[str, List[Dict[str, Any]]] = {
            'resolved': [],
            'unresolved': [],
        }

        phone_map: Dict[str, List[Tuple[int, Dict[str, Any], Any]]] = {}
        for org_id, org in organizations.items():
            for phone_entry in org.get('phones', []) or []:
                # phone_entry может быть строкой или dict
                if isinstance(phone_entry, dict):
                    phone_value = phone_entry.get('normalized') or phone_entry.get('number')
                elif isinstance(phone_entry, str):
                    phone_value = phone_entry
                else:
                    continue
                    
                key = self._normalize_phone_key(phone_value)
                if not key:
                    continue
                phone_map.setdefault(key, []).append((org_id, org, phone_entry))

        if not phone_map:
            return conflicts

        contact_map = self._build_contact_phone_map(contacts)

        for phone_key, owners in phone_map.items():
            if len(owners) <= 1:
                continue

            override_gid = self.phone_overrides.get(phone_key)
            if override_gid:
                entry = self._apply_phone_override(phone_key, owners, override_gid)
                conflicts.setdefault(entry['status'], []).append(entry)
                continue

            owner_scores: List[Dict[str, Any]] = []
            for org_id, org, phone_entry in owners:
                score, reasons = self._score_phone_owner(
                    phone_key, org, org_id, contact_map
                )
                owner_scores.append(
                    {
                        'org_id': org_id,
                        'gid': org.get('gid'),
                        'score': score,
                        'reasons': reasons,
                    }
                )

            max_score = max(item['score'] for item in owner_scores)
            top = [item for item in owner_scores if item['score'] == max_score]

            if max_score > 0 and len(top) == 1:
                winner = top[0]
                removed_gids = self._remove_phone_from_others(
                    phone_key, owners, winner['org_id']
                )
                entry = {
                    'phone': phone_key,
                    'status': 'resolved',
                    'kept_gid': winner.get('gid'),
                    'removed_gids': removed_gids,
                    'reason': self._pick_reason(winner['reasons']),
                }
                conflicts['resolved'].append(entry)
            else:
                entry = {
                    'phone': phone_key,
                    'status': 'unresolved',
                    'owners': [org.get('gid') for _, org, _ in owners if org.get('gid')],
                    'reason': 'ambiguous',
                }
                conflicts['unresolved'].append(entry)

        return conflicts

    def _backfill_contact_city_address(
        self,
        contacts: List[Dict[str, Any]],
        organizations: Dict[int, Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, str]]]:
        """🌐 Мягкое обогащение города/адреса контактов из организации.
        
        TASK-008B: Не применяет backfill для контактов с внутренними доменами,
        чтобы предотвратить ложное обогащение HQ-адресами.
        """
        
        self.logger.info(f"🔍 TASK-008B: _backfill_contact_city_address вызван для {len(contacts)} контактов")

        if not contacts:
            return [], {}

        provenance: Dict[int, Dict[str, str]] = {}
        updated_contacts: List[Dict[str, Any]] = []
        
        # Получаем список внутренних доменов из конфигурации contact_location_safety
        internal_domains = set()
        if self.contact_location_safety:
            internal_domains = self.contact_location_safety.internal_domains

        for contact in contacts:
            normalized_contact = dict(contact)
            for field in ("name", "position", "email", "city", "address", "inn", "role_in_message"):
                if field in normalized_contact and normalized_contact[field] is not None:
                    coerced_value = as_text(normalized_contact[field])
                    normalized_contact[field] = coerced_value if coerced_value else None
            if isinstance(normalized_contact.get('phones'), list):
                for phone_entry in normalized_contact['phones']:
                    if not isinstance(phone_entry, dict):
                        continue
                    for phone_key in ("number", "formatted", "normalized", "original", "extension", "type"):
                        if phone_key in phone_entry and phone_entry[phone_key] is not None:
                            coerced_phone = as_text(phone_entry[phone_key], strip=True)
                            phone_entry[phone_key] = coerced_phone if coerced_phone else None
            cid = normalized_contact.get('contact_id')
            oid = normalized_contact.get('organization_id')
            organization = organizations.get(oid) if isinstance(oid, int) else None
            provenance_entry: Dict[str, str] = {}
            
            # TASK-008B: Проверяем, был ли контакт уже обработан contact_location_safety
            # Если у контакта уже есть city/address, значит они были применены безопасно
            # Если полей нет, значит персонального сигнала не было найдено
            # В этом случае НЕ применяем backfill, чтобы избежать HQ-протечек
            
            has_personal_location = (
                self._has_value(normalized_contact.get('city')) or 
                self._has_value(normalized_contact.get('address'))
            )
            
            # Backfill применяется только если:
            # 1. У контакта УЖЕ есть персональная локация (частичная) - можем дополнить
            # 2. ИЛИ это внешний контакт (не связан с организацией с HQ-адресом)
            allow_backfill = has_personal_location
            
            if not allow_backfill:
                self.logger.debug(
                    f"🔒 Контакт {normalized_contact.get('name', 'unknown')} без персональной локации. "
                    f"Backfill HQ-локации пропущен для предотвращения ложного обогащения."
                )

            if organization and allow_backfill:
                if self.backfill_city_from_org and not self._has_value(normalized_contact.get('city')):
                    org_city = as_text(organization.get('city'))
                    if org_city:
                        normalized_contact['city'] = org_city
                        provenance_entry['city_source'] = 'org_fallback'

                if self.backfill_address_from_org and not self._has_value(normalized_contact.get('address')):
                    org_address = as_text(organization.get('address'))
                    if org_address:
                        normalized_contact['address'] = org_address
                        provenance_entry['address_source'] = 'org_fallback'
            elif organization and not allow_backfill:
                # Для контактов без персональной локации записываем в provenance, что backfill был пропущен
                provenance_entry['backfill_skipped'] = 'no_personal_location_signal'

            if provenance_entry and isinstance(cid, int):
                provenance[cid] = provenance_entry

            updated_contacts.append(normalized_contact)

        return updated_contacts, provenance

    def _scrub_contact_addresses(
        self,
        contacts: List[Dict[str, Any]],
        organizations: Dict[int, Dict[str, Any]],
        provenance: Dict[int, Dict[str, str]],
    ) -> None:
        for contact in contacts:
            address = contact.get('address')
            if not address:
                continue
            org = organizations.get(contact.get('organization_id'))
            if not org:
                continue
            org_address = org.get('address')
            if not org_address:
                continue
            if self._normalized_equals(address, org_address):
                contact['address'] = None
                cid = contact.get('contact_id')
                if isinstance(cid, int):
                    entry = provenance.setdefault(cid, {})
                    entry['address_removed'] = 'org_hq_match'

    @staticmethod
    def _normalized_equals(left: str, right: str) -> bool:
        if not left or not right:
            return False
        return as_text(left).lower() == as_text(right).lower()

    @staticmethod
    def _normalize_phone_key(phone_value: Any) -> Optional[str]:
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

    @staticmethod
    def _normalize_city_label(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return as_text(value).strip().lower().replace('ё', 'е') or None

    def _extract_area_code(self, phone_key: str) -> Optional[str]:
        digits = re.sub(r'\D+', '', phone_key)
        if digits.startswith('7'):
            digits = digits[1:]
        for length in (4, 3):
            if len(digits) >= length:
                code = digits[:length]
                if code in AREA_CODE_CITY_MAP:
                    return code
        return None

    def _match_area_code(self, area_code: str, city: Optional[str]) -> bool:
        normalized_city = self._normalize_city_label(city)
        if not area_code or not normalized_city:
            return False
        expected = AREA_CODE_CITY_MAP.get(area_code)
        if not expected:
            return False
        return expected == normalized_city

    def _build_contact_phone_map(self, contacts: List[Dict[str, Any]]) -> Dict[str, Set[int]]:
        mapping: Dict[str, Set[int]] = defaultdict(set)
        for contact in contacts:
            org_id = contact.get('organization_id')
            if not isinstance(org_id, int):
                continue
            for phone_entry in contact.get('phones', []) or []:
                normalized = None
                if isinstance(phone_entry, dict):
                    normalized = phone_entry.get('normalized') or phone_entry.get('number')
                else:
                    normalized = phone_entry
                key = self._normalize_phone_key(normalized)
                if key:
                    mapping[key].add(org_id)
        return mapping

    def _score_phone_owner(
        self,
        phone_key: str,
        org: Dict[str, Any],
        org_id: int,
        contact_map: Dict[str, Set[int]],
    ) -> Tuple[int, List[str]]:
        score = 0
        reasons: List[str] = []

        area_code = self._extract_area_code(phone_key)
        if area_code and self._match_area_code(area_code, org.get('city')):
            score += 100
            reasons.append('area_match')

        contact_orgs = contact_map.get(phone_key, set())
        if org_id in contact_orgs:
            score += 20
            reasons.append('contact_match')

        return score, reasons

    def _remove_phone_from_others(
        self,
        phone_key: str,
        owners: List[Tuple[int, Dict[str, Any], Dict[str, Any]]],
        winner_org_id: int,
    ) -> List[str]:
        removed_gids: List[str] = []
        for org_id, org, _ in owners:
            if org_id == winner_org_id:
                continue
            phones = org.get('phones') or []
            new_list: List[Dict[str, Any]] = []
            removed = False
            for phone_entry in phones:
                entry_key = self._normalize_phone_key(
                    phone_entry.get('normalized') or phone_entry.get('number')
                )
                if not removed and entry_key == phone_key:
                    removed = True
                    continue
                new_list.append(phone_entry)
            if removed:
                org['phones'] = new_list
                gid = org.get('gid')
                if gid:
                    removed_gids.append(gid)
        return removed_gids

    def _apply_phone_override(
        self,
        phone_key: str,
        owners: List[Tuple[int, Dict[str, Any], Dict[str, Any]]],
        override_gid: str,
    ) -> Dict[str, Any]:
        kept = None
        winner_org_id = None
        for org_id, org, _ in owners:
            if org.get('gid') == override_gid:
                kept = override_gid
                winner_org_id = org_id
                break
        if kept is None:
            return {
                'phone': phone_key,
                'status': 'unresolved',
                'owners': [org.get('gid') for _, org, _ in owners if org.get('gid')],
                'reason': 'override_missing',
            }
        removed_gids = self._remove_phone_from_others(phone_key, owners, winner_org_id)
        return {
            'phone': phone_key,
            'status': 'resolved',
            'kept_gid': kept,
            'removed_gids': removed_gids,
            'reason': 'override',
        }

    @staticmethod
    def _pick_reason(reasons: List[str]) -> str:
        if not reasons:
            return 'unknown'
        if 'area_match' in reasons:
            return 'area_match'
        if 'contact_match' in reasons:
            return 'contact_match'
        return reasons[0]

    @staticmethod
    def _has_value(value: Any) -> bool:
        """🔍 Проверяет, что значение не пустое."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(as_text(value))
        return True

    def _enrich_organizations_inn(self, organizations: Dict[int, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Этап 3.1: Обогащение ИНН организаций
        
        Args:
            organizations: Словарь организаций для обогащения
            
        Returns:
            Dict: Метаданные обогащения ИНН
        """
        if not self.inn_resolver:
            self.logger.debug("INN resolver not available, skipping INN enrichment")
            return {}
        
        try:
            self.logger.info(f"🏛️ Начинаем обогащение ИНН для {len(organizations)} организаций")
            
            # Обогащение через INN resolver
            inn_metadata = self.inn_resolver.enrich_organizations(organizations)
            
            # Обновление статистики
            enriched_count = sum(1 for meta in inn_metadata.values() 
                               if meta.get('decision') == 'auto_accept')
            
            self.stats['organizations_inn_enriched'] = enriched_count
            
            self.logger.info(f"✅ Обогащение ИНН завершено: {enriched_count} организаций обогащено")
            return inn_metadata
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при обогащении ИНН: {e}")
            return {}
    
    def _enrich_organizations_emails(
        self, 
        organizations: Dict[int, Dict[str, Any]], 
        email_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Этап 3.2: Обогащение email-адресов организаций (TASK-007B)
        
        Args:
            organizations: Словарь организаций для обогащения
            email_data: Данные исходного email для извлечения адресов
            
        Returns:
            Dict: Метаданные обогащения email
        """
        if not self.email_enricher:
            self.logger.debug("Email enricher not available, skipping email enrichment")
            return {}
        
        if not email_data:
            self.logger.debug("No email data provided, skipping email enrichment")
            return {}
            
        try:
            self.logger.info(f"📧 Начинаем обогащение email для {len(organizations)} организаций")
            
            # Обогащение через email enricher
            email_metadata = self.email_enricher.enrich_organizations_emails(organizations, email_data)
            
            # Обновление статистики
            enriched_count = len([meta for meta in email_metadata.values() if meta.get('added')])
            
            self.stats['organizations_email_enriched'] = enriched_count
            
            self.logger.info(f"✅ Обогащение email завершено: {enriched_count} организаций обогащено")
            return email_metadata
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при обогащении email: {e}")
            return {}
    
    def _enrich_contacts_phones(
        self,
        contacts: List[Dict[str, Any]],
        organizations: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Этап 3.5: Обогащение телефонов контактов от связанных организаций
        
        ВАЖНО: Телефоны организаций нормализуются ДО обогащения контактов,
        чтобы избежать предупреждений о missing normalized field.
        
        Args:
            contacts: Список контактов для обогащения
            organizations: Словарь организаций
            
        Returns:
            Dict: Метаданные обогащения телефонов контактов
        """
        if not self.contact_phone_enricher:
            self.logger.debug("Contact phone enricher not available, skipping phone enrichment")
            return {}
        
        try:
            self.logger.info(f"📞 Начинаем обогащение телефонов для {len(contacts)} контактов")
            
            # Конвертируем organizations dict в list для enricher
            organizations_list = list(organizations.values())
            
            # КРИТИЧЕСКИ ВАЖНО: Нормализуем телефоны организаций ДО обогащения
            # Это предотвращает предупреждения "Телефон без normalized поля"
            self.logger.debug("🔧 Пре-нормализация телефонов организаций перед обогащением")
            organizations_normalized = self.data_normalizer.normalize_organizations(
                {org.get('organization_id'): org for org in organizations_list}
            )
            organizations_list = list(organizations_normalized.values())
            
            # Обогащение через contact phone enricher
            enrichment_result = self.contact_phone_enricher.enrich_contacts_phones(
                contacts, organizations_list
            )
            
            # Обновление статистики
            stats = enrichment_result.get('statistics', {})
            enriched_count = stats.get('contacts_enriched', 0)
            phones_added = stats.get('phones_added_total', 0)
            
            self.stats['contacts_phone_enriched'] = enriched_count
            self.stats['phones_added_to_contacts'] = phones_added
            
            self.logger.info(
                f"✅ Обогащение телефонов завершено: {enriched_count} контактов обогащено, "
                f"{phones_added} телефонов добавлено"
            )
            
            return enrichment_result
            
        except Exception as e:
            # Обработка ошибок с продолжением пайплайна (Requirement 6.5)
            self.logger.error(f"❌ Ошибка при обогащении телефонов контактов: {e}", exc_info=True)
            return {}

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

    def _collect_phone_ui_stats(self, organizations: Dict[int, Dict[str, Any]], 
                                contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Собирает статистику UI-форматирования телефонов
        
        Args:
            organizations: Словарь организаций
            contacts: Список контактов
            
        Returns:
            dict: Статистика обработки phone UI форматирования
        """
        stats = {
            'phones_processed': 0,
            'organizations_processed': 0,
            'contacts_processed': 0,
            'ui_format_applied': 0,
            'phones_sanitized': 0
        }
        
        # Подсчет для организаций
        for org in organizations.values():
            phones = org.get('phones', [])
            if phones:
                stats['organizations_processed'] += 1
                stats['phones_processed'] += len(phones)
                
                # Проверяем, что все phones имеют только whitelist поля
                for phone in phones:
                    if isinstance(phone, dict):
                        allowed_keys = {'type', 'number', 'normalized', 'original', 'extension'}
                        if set(phone.keys()).issubset(allowed_keys):
                            stats['phones_sanitized'] += 1
                        
                        # Проверяем, что number отформатирован из normalized
                        if phone.get('normalized') and phone.get('number'):
                            # Для RU номеров проверяем формат +7 (XXX)
                            if phone['normalized'].startswith('+7') and '(' in phone['number']:
                                stats['ui_format_applied'] += 1
                            # Для международных - просто наличие форматирования
                            elif not phone['normalized'].startswith('+7'):
                                stats['ui_format_applied'] += 1
        
        # Аналогично для контактов
        for contact in contacts:
            phones = contact.get('phones', [])
            if phones:
                stats['contacts_processed'] += 1
                stats['phones_processed'] += len(phones)
                
                for phone in phones:
                    if isinstance(phone, dict):
                        allowed_keys = {'type', 'number', 'normalized', 'original', 'extension'}
                        if set(phone.keys()).issubset(allowed_keys):
                            stats['phones_sanitized'] += 1
                        
                        if phone.get('normalized') and phone.get('number'):
                            if phone['normalized'].startswith('+7') and '(' in phone['number']:
                                stats['ui_format_applied'] += 1
                            elif not phone['normalized'].startswith('+7'):
                                stats['ui_format_applied'] += 1
        
        return stats

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
            role = as_text(item.get('role_in_message'), default='other').lower()
            item['role_in_message'] = role or 'other'

            interaction_type = as_text(item.get('interaction_type'), default='other').lower()
            if interaction_type not in allowed_types:
                interaction_type = 'other'
            item['interaction_type'] = interaction_type

            attachments_list = [
                as_text(att) for att in as_list(item.get('attachments')) if as_text(att)
            ]
            item['attachments'] = attachments_list

            confidence = as_float(item.get('confidence', 0.0))
            if confidence is None:
                confidence = 0.0
            item['confidence'] = max(0.0, min(1.0, confidence))

            if item.get('message_date'):
                item['message_date'] = as_text(item['message_date'])

            if item.get('message_subject'):
                item['message_subject'] = as_text(item['message_subject'])

            if item.get('message_id_hint'):
                item['message_id_hint'] = safe_regex_sub(r'[<>]', '', item['message_id_hint'])

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
                text = as_text(value)
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
            text = as_text(point)
            if text:
                sanitized.append(text)
            if len(sanitized) >= 5:
                break

        return sanitized

    def _filter_commercial_offers(self, offers: Any, email_metadata: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Фильтрация коммерческих предложений по наличию фактических КП."""
        if not isinstance(offers, list) or not offers:
            return []

        # ИСПРАВЛЕНО: Проверяем оба возможных имени полей для количества вложений
        attachments_count = 0
        if isinstance(email_metadata, dict):
            # Пробуем разные варианты имен полей
            attachments_count = (
                as_int(email_metadata.get('attachments_count')) or
                as_int(email_metadata.get('attachments')) or
                0
            )
        
        # ЛОГИКА КОРРЕКТНА: КП должны быть в вложениях, иначе это обсуждение
        if attachments_count <= 0:
            self.logger.info("   💼 КП отклонены: вложения отсутствуют (вероятно обсуждение КП)")
            return []
        
        # Вложения есть - возвращаем коммерческие предложения
        self.logger.info(f"   💼 КП одобрены: найдено {attachments_count} вложений, принято {len(offers)} предложений")
        return offers

    def _coerce_positive_float(self, value: Any) -> Optional[float]:
        """Безопасное преобразование значения в положительное число."""
        number = as_float(value)
        if number is None or number <= 0:
            return None
        return round(number, 2)
    
    def _build_final_result(self, original_result: Dict[str, Any],
                          final_contacts: List[Dict[str, Any]],
                          final_organizations: Dict[int, Dict[str, Any]],
                          interactions: List[Dict[str, Any]],
                          summary: Dict[str, Optional[str]],
                          key_points: List[str],
                          business_context: str,
                          commercial_offers: List[Dict[str, Any]],
                          provenance: Optional[Dict[int, Dict[str, str]]] = None,
                          email_classification: Optional[Dict[int, Dict[str, Any]]] = None,
                          gid_metadata: Optional[Dict[str, Any]] = None,
                          phone_conflicts: Optional[Dict[str, List[Dict[str, Any]]]] = None,
                          inn_enrichment_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
                          org_email_enrichment_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
                          location_enrichment_metadata: Optional[Dict[str, Any]] = None,
                          phone_ui_stats: Optional[Dict[str, Any]] = None,
                          contact_phone_enrichment_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        base_metadata: Dict[str, Any] = {}
        original_metadata = original_result.get('postprocessing_metadata')
        if isinstance(original_metadata, dict):
            base_metadata = copy.deepcopy(original_metadata)

        base_metadata.update({
            'processed_at': self._get_current_timestamp(),
            'stats': self.stats.copy(),
            'version': '1.3.0',
            'organization_mapping': self.organization_mapping,
            'contact_mapping': self.contact_mapping,
        })

        processed_result['postprocessing_metadata'] = base_metadata

        if provenance:
            processed_result['postprocessing_metadata']['provenance'] = {
                'contacts': provenance
            }
        if email_classification:
            processed_result['postprocessing_metadata']['email_classification'] = email_classification
        if gid_metadata is not None:
            processed_result['postprocessing_metadata']['gid'] = gid_metadata
        if phone_conflicts is not None:
            processed_result['postprocessing_metadata']['phone_conflicts'] = phone_conflicts
        if inn_enrichment_metadata is not None:
            processed_result['postprocessing_metadata']['enrichment'] = {
                'org_inn': inn_enrichment_metadata
            }
        
        if org_email_enrichment_metadata is not None:
            if 'enrichment' not in processed_result['postprocessing_metadata']:
                processed_result['postprocessing_metadata']['enrichment'] = {}
            processed_result['postprocessing_metadata']['enrichment']['org_email_enrichment'] = org_email_enrichment_metadata
        
        if location_enrichment_metadata is not None:
            if 'enrichment' not in processed_result['postprocessing_metadata']:
                processed_result['postprocessing_metadata']['enrichment'] = {}
            processed_result['postprocessing_metadata']['enrichment']['org_location_from_attachments'] = location_enrichment_metadata
        
        if phone_ui_stats is not None:
            processed_result['postprocessing_metadata']['phone_ui_formatting'] = phone_ui_stats
        
        if contact_phone_enrichment_metadata is not None:
            if 'enrichment' not in processed_result['postprocessing_metadata']:
                processed_result['postprocessing_metadata']['enrichment'] = {}
            processed_result['postprocessing_metadata']['enrichment']['contact_phone_enrichment'] = contact_phone_enrichment_metadata

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

    def _enrich_organizations_location_from_attachments(self, organizations: Dict[int, Dict[str, Any]], 
                                                      email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Обогащение локации организаций из вложений (TASK-008A)
        
        Args:
            organizations: Словарь организаций для обогащения
            email_data: Данные письма с вложениями
            
        Returns:
            Dict: Метаданные обогащения локации
        """
        if not self.attachment_evidence_extractor or not self.org_location_enrichment:
            self.logger.warning("⚠️ Attachment evidence extractors not initialized, skipping location enrichment")
            return {}
        
        # ОТЛАДКА: Логируем что получили
        self.logger.info(f"🔍 DEBUG: email_data type: {type(email_data)}")
        if email_data:
            self.logger.info(f"🔍 DEBUG: email_data keys: {list(email_data.keys())}")
            attachments = email_data.get('attachments')
            self.logger.info(f"🔍 DEBUG: attachments type: {type(attachments)}, value: {attachments if not isinstance(attachments, list) else f'list of {len(attachments)} items'}")
        
        if not email_data or not email_data.get('attachments'):
            self.logger.warning(f"📎 No attachments found in email_data, skipping location enrichment")
            return {}
        
        try:
            self.logger.info("🔍 Starting location enrichment from attachments")
            
            # Извлекаем доказательства локации из вложений
            evidence_list = self.attachment_evidence_extractor.extract(email_data)
            
            if not evidence_list:
                self.logger.info("📎 No location evidence found in attachments")
                return {}
            
            self.logger.info(f"📍 Found {len(evidence_list)} location evidence items")
            
            # Применяем обогащение к организациям
            postprocessing_metadata = {}
            enriched_organizations = self.org_location_enrichment.enrich_organizations(
                organizations, evidence_list, postprocessing_metadata
            )
            
            # Обновляем организации in-place
            for org_gid, enriched_org in enriched_organizations.items():
                if org_gid in organizations:
                    organizations[org_gid] = enriched_org
            
            # Получаем статистику
            enrichment_stats = self.org_location_enrichment.get_stats()
            self.logger.info(f"✅ Location enrichment completed: {enrichment_stats}")
            
            return {
                'evidence_count': len(evidence_list),
                'organizations_enriched': enrichment_stats.get('organizations_enriched', 0),
                'cities_added': enrichment_stats.get('cities_added', 0),
                'addresses_added': enrichment_stats.get('addresses_added', 0),
                'conflicts_detected': enrichment_stats.get('conflicts_detected', 0),
                'location_evidence': postprocessing_metadata.get('location_evidence', {})
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error during location enrichment from attachments: {e}")
            import traceback
            self.logger.error(f"📚 Traceback:\n{traceback.format_exc()}")
            return {}
    
    def _apply_contact_location_safety(
        self,
        contacts: List[Dict[str, Any]],
        email_data: Optional[Dict[str, Any]] = None,
        organizations: Optional[Dict[int, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Безопасное обогащение локации контактов (TASK-008B)
        
        Предотвращает ложное обогащение контактов локационными данными из HQ-блоков.
        Заполняет contacts.city/address только при явных персональных сигналах.
        
        Args:
            contacts: Список контактов для обработки
            email_data: Данные письма
            organizations: Словарь организаций (для определения HQ-блоков)
            
        Returns:
            Dict: Метаданные обогащения локации контактов
        """
        self.logger.info(f"🔍 TASK-008B: _apply_contact_location_safety вызван для {len(contacts) if contacts else 0} контактов")
        
        if not self.contact_location_safety:
            self.logger.warning("⚠️ Contact location safety not initialized, skipping")
            return {}
        
        if not contacts:
            self.logger.info("⚠️ No contacts to process for location safety")
            return {}
        
        try:
            self.logger.info(f"🔒 Starting contact location safety check for {len(contacts)} contacts")
            
            # Подготавливаем данные сообщения
            message = {
                'body': email_data.get('body', '') if email_data else '',
                'text': email_data.get('text', '') if email_data else '',
                'organizations': list(organizations.values()) if organizations else []
            }
            
            # Извлекаем персональные локационные сигналы
            # TODO: В будущем можно добавить signature_blocks_by_person из email_data
            evidence_map = self.contact_location_safety.extract_contact_location_evidence(
                message, contacts, signature_blocks_by_person=None
            )
            
            self.logger.info(f"📍 Found location evidence for {len(evidence_map)} contacts")
            
            # Применяем локацию к контактам
            postprocessing_metadata = {}
            applied_count = 0
            
            for contact in contacts:
                contact_gid = contact.get('gid', '')
                if not contact_gid:
                    continue
                
                evidence = evidence_map.get(contact_gid)
                if evidence:
                    applied = self.contact_location_safety.apply_contact_location(
                        contact, evidence, postprocessing_metadata
                    )
                    if applied:
                        applied_count += 1
            
            # Получаем статистику
            safety_stats = self.contact_location_safety.get_stats()
            self.logger.info(
                f"✅ Contact location safety completed: "
                f"{safety_stats.get('locations_applied', 0)} applied, "
                f"{safety_stats.get('locations_rejected', 0)} rejected, "
                f"{safety_stats.get('hq_blocks_detected', 0)} HQ blocks detected"
            )
            
            return {
                'contacts_processed': safety_stats.get('contacts_processed', 0),
                'locations_applied': safety_stats.get('locations_applied', 0),
                'locations_rejected': safety_stats.get('locations_rejected', 0),
                'hq_blocks_detected': safety_stats.get('hq_blocks_detected', 0),
                'location_evidence': postprocessing_metadata.get('location_evidence', {})
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error during contact location safety check: {e}")
            import traceback
            self.logger.error(f"📚 Traceback:\n{traceback.format_exc()}")
            return {}


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
