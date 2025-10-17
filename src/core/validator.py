#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 JSON Schema валидатор для новой структуры organizations/contacts
Поддерживает только новый формат согласно мини-ТЗ
"""

import copy
import json
import jsonschema
from typing import Dict, List, Optional, Any, Tuple, TypedDict, Sequence
from jsonschema import ValidationError, SchemaError

class InvalidStructureError(Exception):
    """Исключение для полностью невалидной структуры данных"""
    pass

class Participants(TypedDict, total=False):
    """🧑‍🤝‍🧑 Структура участников взаимодействия."""

    actor: Optional[str]
    audience: Optional[List[str]]


class LLMResponseValidator:
    """🔍 Валидатор JSON Schema для новой структуры organizations/contacts"""

    _SANITIZER_VERSION = "1.0.0"
    _SANITIZER_PREVIEW_LIMIT = 120

    _ROOT_ALLOWED_KEYS = {
        "organizations",
        "contacts",
        "business_context",
        "summary",
        "key_points",
        "commercial_offers",
        "interactions",
        "postprocessing_metadata",
        "original_response",
        "validation_error",
        "errors",
        "error",
        "processing_strategy",
        "fallback_reason",
        "success",
        "provider_used",
        "processing_time",
        "processing_time_seconds",
        "text_length",
        "chunks_processed",
        "total_contacts_found",
        "unique_contacts_found",
        "raw_llm_result",
        "resilient_processing",
        "stats",
        "pipeline_version",
        "quality_report",
        "diagnostics",
        "warnings",
        "source_file",
    }

    _ORGANIZATION_ALLOWED_KEYS = {
        "organization_id",
        "name",
        "inn",
        "inn_validated",
        "website",
        "website_confidence",
        "website_source",
        "website_method",
        "city",
        "address",
        "emails",
        "phones",
    }

    _CONTACT_ALLOWED_KEYS = {
        "contact_id",
        "name",
        "organization_id",
        "position",
        "email",
        "email_valid",
        "phones",
        "city",
        "address",
        "inn",
        "role_in_message",
        "confidence",
        "value_score",
        "priority",
    }

    _PHONE_ALLOWED_KEYS = {
        "type",
        "number",
        "formatted",
        "normalized",
        "original",
        "extension",
        "confidence",
    }

    _COMMERCIAL_OFFER_ALLOWED_KEYS = {
        "found",
        "offer_type",
        "offer_number",
        "offer_date",
        "end_user",
        "end_user_inn",
        "intermediary",
        "intermediary_date",
        "payment_terms",
        "delivery_time",
        "delivery_terms",
        "valid_until",
        "equipment_items",
        "total_cost",
        "currency",
        "comments",
        "reason",
    }

    _EQUIPMENT_ITEM_ALLOWED_KEYS = {
        "name",
        "model",
        "article",
        "quantity",
        "unit_price",
        "total_price",
        "vat",
    }

    _INTERACTION_ALLOWED_KEYS = {
        "interaction_local_id",
        "contact_id",
        "organization_id",
        "message_subject",
        "message_date",
        "message_id_hint",
        "role_in_message",
        "interaction_type",
        "summary",
        "attachments",
        "human_note",
        "participants",
        "confidence",
    }

    _PARTICIPANTS_ALLOWED_KEYS = {
        "actor",
        "audience",
    }

    _SUMMARY_ALLOWED_KEYS = {
        "topic",
        "product_interest",
        "communication_stage",
        "request_type",
    }

    def __init__(self):
        """Инициализация валидатора только для новой структуры"""
        self.phone_schema = self._create_phone_schema()
        self.organization_schema = self._create_organization_schema()
        self.contact_schema = self._create_contact_schema()
        self.commercial_offer_schema = self._create_commercial_offer_schema()
        self.participants_schema = self._create_participants_schema()
        self.interaction_schema = self._create_interaction_schema()
        self.full_response_schema = self._create_full_response_schema()

        print("✅ LLMResponseValidator инициализирован для новой структуры organizations/contacts")

    def _sanitize_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """🧼 Удаление неизвестных полей перед JSON Schema валидацией."""
        if not isinstance(payload, dict):
            return payload

        sanitized = copy.deepcopy(payload)
        removed: List[Dict[str, Any]] = []
        stats: Dict[str, int] = {"converted_to_string": 0}

        self._sanitize_root_level(sanitized, removed, stats)

        if removed:
            metadata = sanitized.get("postprocessing_metadata")
            if not isinstance(metadata, dict):
                metadata = {} if metadata is None else {"_original": self._make_value_preview(metadata)}
                sanitized["postprocessing_metadata"] = metadata

            sanitizer_meta = metadata.get("sanitizer")
            if not isinstance(sanitizer_meta, dict):
                sanitizer_meta = {}
                metadata["sanitizer"] = sanitizer_meta

            sanitizer_meta["version"] = self._SANITIZER_VERSION
            sanitizer_meta["removed_count"] = len(removed)
            sanitizer_meta["removed_props"] = removed
            sanitizer_meta["converted_to_string"] = stats["converted_to_string"]
        else:
            if stats["converted_to_string"]:
                metadata = sanitized.get("postprocessing_metadata")
                if not isinstance(metadata, dict):
                    metadata = {}
                    sanitized["postprocessing_metadata"] = metadata
                sanitizer_meta = metadata.get("sanitizer")
                if not isinstance(sanitizer_meta, dict):
                    sanitizer_meta = {}
                    metadata["sanitizer"] = sanitizer_meta
                sanitizer_meta["version"] = self._SANITIZER_VERSION
                sanitizer_meta["removed_count"] = sanitizer_meta.get("removed_count", 0)
                sanitizer_meta["removed_props"] = sanitizer_meta.get("removed_props", [])
                sanitizer_meta["converted_to_string"] = stats["converted_to_string"]

        return sanitized

    def _sanitize_root_level(self, payload: Dict[str, Any], removed: List[Dict[str, Any]], stats: Dict[str, int]) -> None:
        for key in list(payload.keys()):
            if key != "postprocessing_metadata" and key not in self._ROOT_ALLOWED_KEYS:
                value = payload.pop(key)
                self._register_removed_property(removed, [], key, value)
                continue

            if key == "organizations":
                organizations = payload.get(key)
                cleaned_list = self._sanitize_list_of_objects(
                    organizations,
                    self._ORGANIZATION_ALLOWED_KEYS,
                    ["organizations"],
                    removed,
                    stats,
                    item_sanitizer=self._sanitize_organization,
                )
                payload[key] = cleaned_list

            elif key == "contacts":
                contacts = payload.get(key)
                cleaned_list = self._sanitize_list_of_objects(
                    contacts,
                    self._CONTACT_ALLOWED_KEYS,
                    ["contacts"],
                    removed,
                    stats,
                    item_sanitizer=self._sanitize_contact,
                )
                payload[key] = cleaned_list

            elif key == "commercial_offers":
                offers = payload.get(key)
                cleaned_list = self._sanitize_list_of_objects(
                    offers,
                    self._COMMERCIAL_OFFER_ALLOWED_KEYS,
                    ["commercial_offers"],
                    removed,
                    stats,
                    item_sanitizer=self._sanitize_commercial_offer,
                )
                payload[key] = cleaned_list

            elif key == "interactions":
                interactions = payload.get(key)
                cleaned_list = self._sanitize_list_of_objects(
                    interactions,
                    self._INTERACTION_ALLOWED_KEYS,
                    ["interactions"],
                    removed,
                    stats,
                    item_sanitizer=self._sanitize_interaction,
                )
                payload[key] = cleaned_list

            elif key == "summary":
                summary_value = payload.get(key)
                sanitized_summary = self._sanitize_known_dict(
                    summary_value,
                    self._SUMMARY_ALLOWED_KEYS,
                    ["summary"],
                    removed,
                )
                for summary_field in list(sanitized_summary.keys()):
                    sanitized_summary[summary_field] = self._coerce_string(
                        sanitized_summary.get(summary_field),
                        stats,
                    )
                payload[key] = sanitized_summary

            elif key == "business_context":
                coerced = self._coerce_string(payload.get(key), stats)
                payload[key] = coerced

            elif key == "key_points":
                key_points = payload.get(key)
                if key_points is None:
                    payload[key] = []
                elif isinstance(key_points, list):
                    normalized_points = []
                    for idx, point in enumerate(key_points):
                        value = self._coerce_string(point, stats)
                        if value:
                            normalized_points.append(value)
                        else:
                            if point not in (None, ""):
                                self._register_removed_property(removed, ["key_points", idx], str(idx), point)
                    payload[key] = normalized_points
                else:
                    value = self._coerce_string(key_points, stats)
                    payload[key] = [value] if value else []

    def _sanitize_list_of_objects(
        self,
        value: Any,
        allowed_keys: Sequence[str],
        path: List[Any],
        removed: List[Dict[str, Any]],
        stats: Dict[str, int],
        item_sanitizer: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        if value is None:
            return []

        if not isinstance(value, list):
            value = [value]

        cleaned_items: List[Dict[str, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                self._register_removed_property(removed, path, str(index), item)
                continue

            cleaned_item = self._sanitize_known_dict(item, allowed_keys, path + [index], removed)
            if callable(item_sanitizer):
                cleaned_item = item_sanitizer(cleaned_item, path + [index], removed, stats)
            cleaned_items.append(cleaned_item)
        return cleaned_items

    def _sanitize_known_dict(
        self,
        value: Any,
        allowed_keys: Sequence[str],
        path: List[Any],
        removed: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(value, dict):
            if value is not None:
                self._register_removed_property(removed, path[:-1], str(path[-1]) if path else "", value)
            return {}

        allowed_set = set(allowed_keys)
        for key in list(value.keys()):
            if key not in allowed_set:
                self._register_removed_property(removed, path, key, value.pop(key))
        return value

    def _sanitize_organization(
        self,
        organization: Dict[str, Any],
        path: List[Any],
        removed: List[Dict[str, Any]],
        stats: Dict[str, int],
    ) -> Dict[str, Any]:
        emails = organization.get("emails")
        if emails is None:
            organization["emails"] = []
        elif not isinstance(emails, list):
            organization["emails"] = [emails]
        normalized_emails: List[str] = []
        for email in organization.get("emails", []):
            coerced = self._coerce_string(email, stats)
            if coerced:
                normalized_emails.append(coerced)
        organization["emails"] = normalized_emails

        phones = organization.get("phones")
        if phones is None:
            organization["phones"] = []
        elif not isinstance(phones, list):
            organization["phones"] = [phones]
        
        # Нормализуем телефоны: поддерживаем как строки, так и объекты
        normalized_phones: List[Any] = []
        for phone in organization.get("phones", []):
            if isinstance(phone, dict):
                # Объект телефона - оставляем как есть
                normalized_phones.append(phone)
            elif phone is not None:
                # Строка - преобразуем в объект
                coerced = self._coerce_string(phone, stats)
                if coerced:
                    normalized_phones.append({"number": coerced, "type": "main"})
        organization["phones"] = normalized_phones

        for key in ("name", "inn", "website", "website_source", "website_method", "city", "address"):
            if key in organization:
                organization[key] = self._coerce_string(organization.get(key), stats)

        return organization

    def _sanitize_contact(
        self,
        contact: Dict[str, Any],
        path: List[Any],
        removed: List[Dict[str, Any]],
        stats: Dict[str, int],
    ) -> Dict[str, Any]:
        phones = contact.get("phones")
        normalized_phones: List[Any] = []
        if phones is None:
            normalized_phones = []
        elif isinstance(phones, list):
            for phone_entry in phones:
                if isinstance(phone_entry, dict):
                    normalized_phones.append(phone_entry)
                elif phone_entry is not None:
                    normalized_phones.append({"number": phone_entry})
        else:
            coerced_single = self._coerce_string(phones, stats)
            normalized_phones = [{"number": coerced_single}] if coerced_single else []

        contact["phones"] = self._sanitize_list_of_objects(
            normalized_phones,
            self._PHONE_ALLOWED_KEYS,
            path + ["phones"],
            removed,
            stats,
            item_sanitizer=None,
        )

        for phone_entry in contact.get("phones", []):
            for phone_key in ("number", "formatted", "normalized", "original", "extension", "type"):
                if phone_key in phone_entry:
                    phone_entry[phone_key] = self._coerce_string(phone_entry.get(phone_key), stats)

        for field in ("name", "position", "email", "city", "address", "inn", "role_in_message"):
            if field in contact:
                contact[field] = self._coerce_string(contact.get(field), stats)

        return contact

    def _sanitize_commercial_offer(
        self,
        offer: Dict[str, Any],
        path: List[Any],
        removed: List[Dict[str, Any]],
        stats: Dict[str, int],
    ) -> Dict[str, Any]:
        offer["equipment_items"] = self._sanitize_list_of_objects(
            offer.get("equipment_items"),
            self._EQUIPMENT_ITEM_ALLOWED_KEYS,
            path + ["equipment_items"],
            removed,
            stats,
            item_sanitizer=None,
        )

        for item in offer.get("equipment_items", []):
            for key in ("name", "model", "article", "vat"):
                if key in item:
                    item[key] = self._coerce_string(item.get(key), stats)

        for offer_field in (
            "offer_type",
            "offer_number",
            "offer_date",
            "end_user",
            "end_user_inn",
            "intermediary",
            "intermediary_date",
            "payment_terms",
            "delivery_time",
            "delivery_terms",
            "valid_until",
            "currency",
            "comments",
            "reason",
        ):
            if offer_field in offer:
                offer[offer_field] = self._coerce_string(offer.get(offer_field), stats)

        return offer

    def _sanitize_interaction(
        self,
        interaction: Dict[str, Any],
        path: List[Any],
        removed: List[Dict[str, Any]],
        stats: Dict[str, int],
    ) -> Dict[str, Any]:
        attachments = interaction.get("attachments")
        if attachments is None:
            interaction["attachments"] = []
        elif not isinstance(attachments, list):
            interaction["attachments"] = [attachments]

        normalized_attachments: List[str] = []
        for item in interaction.get("attachments", []):
            coerced = self._coerce_string(item, stats)
            if coerced:
                normalized_attachments.append(coerced)
        interaction["attachments"] = normalized_attachments

        for field in ("summary", "message_subject", "message_date", "message_id_hint", "role_in_message"):
            if field in interaction:
                interaction[field] = self._coerce_string(interaction.get(field), stats)

        participants = interaction.get("participants")
        if isinstance(participants, dict):
            interaction["participants"] = self._sanitize_known_dict(
                participants,
                self._PARTICIPANTS_ALLOWED_KEYS,
                path + ["participants"],
                removed,
            )
            actor = interaction["participants"].get("actor")
            interaction["participants"]["actor"] = self._coerce_string(actor, stats)

            audience = interaction["participants"].get("audience")
            if isinstance(audience, list):
                normalized_audience: List[str] = []
                for member in audience:
                    coerced = self._coerce_string(member, stats)
                    if coerced:
                        normalized_audience.append(coerced)
                interaction["participants"]["audience"] = normalized_audience
            elif audience is not None:
                coerced_audience = self._coerce_string(audience, stats)
                interaction["participants"]["audience"] = [coerced_audience] if coerced_audience else []
        elif participants is not None:
            self._register_removed_property(removed, path, "participants", participants)
            interaction.pop("participants", None)

        return interaction

    def _coerce_string(self, value: Any, stats: Dict[str, int]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text if text else None
        stats["converted_to_string"] += 1
        text = str(value).strip()
        return text if text else None

    def _register_removed_property(
        self,
        removed: List[Dict[str, Any]],
        path: List[Any],
        key: str,
        value: Any,
    ) -> None:
        preview = self._make_value_preview(value)
        path_parts = list(path)
        if key:
            path_parts.append(key)
        path_str = "/" + "/".join(str(part) for part in path_parts) if path_parts else "/"
        removed.append({
            "path": path_str,
            "key": key,
            "value_preview": preview,
        })

    def _make_value_preview(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            text = value.strip()
            if len(text) > self._SANITIZER_PREVIEW_LIMIT:
                return text[: self._SANITIZER_PREVIEW_LIMIT - 3] + "..."
            return text
        if isinstance(value, list):
            return f"<list:{len(value)}>"
        if isinstance(value, dict):
            return f"<dict:{len(value)}>"
        return f"<{type(value).__name__}>"

    def _create_phone_schema(self) -> Dict[str, Any]:
        """📞 Создание схемы для телефона в новом формате"""
        return {
            "type": "object",
            "required": ["number"],
            "properties": {
                "type": {
                    "type": ["string", "null"],
                    "enum": ["main", "mobile", "office", "fax", "other", None],
                    "description": "Тип телефона"
                },
                "number": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Номер телефона"
                },
                "formatted": {
                    "type": ["string", "null"],
                    "description": "Форматированный номер"
                },
                "normalized": {
                    "type": ["string", "null"],
                    "description": "Нормализованный номер"
                },
                "formatted": {
                    "type": ["string", "null"],
                    "description": "Форматированный номер"
                },
                "original": {
                    "type": ["string", "null"],
                    "description": "Первоначальное значение номера"
                },
                "extension": {
                    "type": ["string", "null"],
                    "description": "Добавочный номер"
                },
                "confidence": {
                    "type": ["number", "null"],
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Уверенность в корректности номера"
                }
            },
            "additionalProperties": False
        }

    def _create_organization_schema(self) -> Dict[str, Any]:
        """🏢 Создание схемы для организации"""
        return {
            "type": "object",
            "required": ["organization_id", "name"],
            "properties": {
                "organization_id": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Уникальный ID организации"
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 300,
                    "description": "Название организации"
                },
                "inn": {
                    "type": ["string", "null"],
                    "pattern": "^[0-9]{10,12}$",
                    "description": "ИНН организации (10 или 12 цифр)"
                },
                "inn_validated": {
                    "type": ["boolean", "null"],
                    "description": "Результат валидации ИНН"
                },
                "website": {
                    "type": ["string", "null"],
                    "description": "Сайт организации"
                },
                "website_confidence": {
                    "type": ["number", "null"],
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Уверенность в сайте"
                },
                "city": {
                    "type": ["string", "null"],
                    "maxLength": 100,
                    "description": "Город организации"
                },
                "address": {
                    "type": ["string", "null"],
                    "maxLength": 500,
                    "description": "Адрес организации"
                },
                "emails": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "format": "email"
                    },
                    "uniqueItems": True,
                    "description": "Массив email адресов организации"
                },
                "phones": {
                    "type": "array",
                    "items": self.phone_schema,
                    "description": "Массив телефонов организации (объекты с полями number, normalized, extension)"
                }
            },
            "additionalProperties": False
        }

    def _create_contact_schema(self) -> Dict[str, Any]:
        """👤 Создание схемы для контакта"""
        return {
            "type": "object",
            "required": [
                "name",
                "role_in_message",
                "confidence"
            ],
            "properties": {
                "contact_id": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "description": "Уникальный ID контакта в рамках письма (null если не назначен)"
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Имя контактного лица"
                },
                "organization_id": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "description": "ID связанной организации (null для личных контактов)"
                },
                "position": {
                    "type": ["string", "null"],
                    "maxLength": 200,
                    "description": "Должность контакта"
                },
                "email": {
                    "type": ["string", "null"],
                    "format": "email",
                    "description": "Email контакта"
                },
                "email_valid": {
                    "type": ["boolean", "null"],
                    "description": "Результат валидации email"
                },
                "phones": {
                    "type": "array",
                    "items": self.phone_schema,
                    "description": "Массив телефонов контакта"
                },
                "city": {
                    "type": ["string", "null"],
                    "maxLength": 100,
                    "description": "Город контакта"
                },
                "address": {
                    "type": ["string", "null"],
                    "maxLength": 500,
                    "description": "Адрес контакта"
                },
                "inn": {
                    "type": ["string", "null"],
                    "pattern": "^[0-9]{10,12}$",
                    "description": "ИНН контакта"
                },
                "role_in_message": {
                    "type": ["string", "null"],
                    "minLength": 1,
                    "description": "Роль контакта в письме (null если неизвестно)"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Уверенность в контакте"
                },
                "value_score": {
                    "type": ["integer", "null"],
                    "minimum": 0,
                    "description": "Оценка ценности контакта"
                },
                "priority": {
                    "type": ["object", "null"],
                    "description": "Приоритет контакта"
                }
            },
            "additionalProperties": False
        }

    def _create_commercial_offer_schema(self) -> Dict[str, Any]:
        """💼 Создание схемы для коммерческого предложения"""
        return {
            "type": "object",
            "required": ["found"],
            "properties": {
                "found": {
                    "type": "boolean",
                    "description": "Найдено ли коммерческое предложение"
                },
                "offer_type": {
                    "type": ["string", "null"],
                    "enum": ["Приборы", "Наборы", "Другое", None],
                    "description": "Тип коммерческого предложения"
                },
                "offer_number": {
                    "type": ["string", "null"],
                    "description": "Номер коммерческого предложения"
                },
                "offer_date": {
                    "type": ["string", "null"],
                    "format": "date",
                    "description": "Дата коммерческого предложения"
                },
                "end_user": {
                    "type": ["string", "null"],
                    "description": "Конечный пользователь/заказчик"
                },
                "end_user_inn": {
                    "type": ["string", "null"],
                    "pattern": "^[0-9]{10,12}$",
                    "description": "ИНН конечного пользователя"
                },
                "intermediary": {
                    "type": ["string", "null"],
                    "description": "Посредник/контактное лицо"
                },
                "intermediary_date": {
                    "type": ["string", "null"],
                    "description": "Контактные данные посредника"
                },
                "payment_terms": {
                    "type": ["string", "null"],
                    "description": "Условия оплаты"
                },
                "delivery_time": {
                    "type": ["string", "null"],
                    "description": "Срок поставки"
                },
                "delivery_terms": {
                    "type": ["string", "null"],
                    "description": "Условия поставки"
                },
                "valid_until": {
                    "type": ["string", "null"],
                    "description": "Действительно до"
                },
                "equipment_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Название оборудования"
                            },
                            "model": {
                                "type": ["string", "null"],
                                "description": "Модель"
                            },
                            "article": {
                                "type": ["string", "null"],
                                "description": "Артикул"
                            },
                            "quantity": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Количество"
                            },
                            "unit_price": {
                                "type": ["number", "null"],
                                "minimum": 0,
                                "description": "Цена за единицу"
                            },
                            "total_price": {
                                "type": ["number", "null"],
                                "minimum": 0,
                                "description": "Общая стоимость позиции"
                            },
                            "vat": {
                                "type": ["string", "null"],
                                "description": "НДС"
                            }
                        },
                        "required": ["name", "quantity"],
                        "additionalProperties": False
                    },
                    "description": "Список оборудования в КП"
                },
                "total_cost": {
                    "type": ["number", "null"],
                    "minimum": 0,
                    "description": "Общая стоимость КП"
                },
                "currency": {
                    "type": ["string", "null"],
                    "default": "RUB",
                    "description": "Валюта"
                },
                "comments": {
                    "type": ["string", "null"],
                    "description": "Комментарии к КП"
                },
                "reason": {
                    "type": ["string", "null"],
                    "description": "Причина, по которой КП не найдено"
                }
            },
            "additionalProperties": True
        }

    def _create_participants_schema(self) -> Dict[str, Any]:
        """🧑‍🤝‍🧑 Создаёт схему блока участников."""
        return {
            "type": ["object", "null"],
            "description": "Участники взаимодействия",
            "properties": {
                "actor": {
                    "type": ["string", "null"],
                    "description": "Основной инициатор взаимодействия"
                },
                "audience": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "Целевая аудитория или получатели"
                }
            },
            "additionalProperties": False
        }

    def _create_interaction_schema(self) -> Dict[str, Any]:
        """🔁 Создание схемы для взаимодействий"""
        allowed_types = [
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
        ]

        return {
            "type": "object",
            "required": [
                "interaction_local_id",
                "role_in_message",
                "interaction_type",
                "summary",
                "confidence"
            ],
            "properties": {
                "interaction_local_id": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Локальный ID взаимодействия в рамках письма"
                },
                "contact_id": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "description": "Ссылка на контакт (null если контакт не определён)"
                },
                "organization_id": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "description": "Ссылка на организацию (null для личных контактов)"
                },
                "message_subject": {
                    "type": ["string", "null"],
                    "description": "Тема письма"
                },
                "message_date": {
                    "type": ["string", "null"],
                    "description": "Дата письма в ISO 8601"
                },
                "message_id_hint": {
                    "type": ["string", "null"],
                    "description": "Message-ID или подсказка"
                },
                "role_in_message": {
                    "type": ["string", "null"],
                    "minLength": 1,
                    "description": "Роль участника в переписке (null если неизвестно)"
                },
                "interaction_type": {
                    "type": "string",
                    "enum": allowed_types,
                    "description": "Тип взаимодействия"
                },
                "summary": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Краткое описание взаимодействия"
                },
                "attachments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Список вложений"
                },
                "human_note": {
                    "type": ["string", "null"],
                    "description": "Комментарий модератора или оператора"
                },
                "participants": self.participants_schema,
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Уверенность в корректности записи"
                }
            },
            "additionalProperties": False
        }

    def _create_full_response_schema(self) -> Dict[str, Any]:
        """📋 Создание полной схемы ответа в новом формате"""
        return {
            "type": "object",
            "required": [
                "organizations",
                "contacts",
                "business_context",
                "summary",
                "key_points",
                "commercial_offers",
                "interactions"
            ],
            "properties": {
                "organizations": {
                    "type": "array",
                    "items": self.organization_schema,
                    "description": "Массив организаций"
                },
                "contacts": {
                    "type": "array",
                    "items": self.contact_schema,
                    "description": "Массив контактов"
                },
                "business_context": {
                    "type": ["string", "null"],
                    "description": "Бизнес-контекст письма"
                },
                "summary": {
                    "type": "object",
                    "required": [
                        "topic",
                        "product_interest",
                        "communication_stage",
                        "request_type"
                    ],
                    "properties": {
                        "topic": {"type": ["string", "null"]},
                        "product_interest": {"type": ["string", "null"]},
                        "communication_stage": {"type": ["string", "null"]},
                        "request_type": {"type": ["string", "null"]}
                    },
                    "additionalProperties": False
                },
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ключевые моменты"
                },
                "commercial_offers": {
                    "type": "array",
                    "items": self.commercial_offer_schema,
                    "description": "Коммерческие предложения"
                },
                "interactions": {
                    "type": "array",
                    "items": self.interaction_schema,
                    "description": "Список взаимодействий"
                },
                "postprocessing_metadata": {
                    "type": ["object", "null"],
                    "properties": {
                        "processed_at": {"type": "string"},
                        "stats": {"type": "object"},
                        "version": {"type": "string"}
                    },
                    "additionalProperties": True,
                    "description": "Метаданные постобработки"
                }
            },
            "additionalProperties": True
        }

    def validate_llm_response(self, response: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """🔍 Валидация ответа LLM в новом формате organizations/contacts"""
        errors = []
        corrected_response = copy.deepcopy(response)
        corrected_response = self._upgrade_legacy_response(corrected_response)
        
        print("🔍 Валидация ответа в новом формате organizations/contacts")
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Нормализуем ключи с пробелами от Replicate LLM
        corrected_response = self._normalize_keys_with_spaces(corrected_response)
        
        # Санитизация структуры перед схемой
        corrected_response = self._sanitize_response(corrected_response)

        # Дополнительная нормализация типов взаимодействий
        corrected_response = self._normalize_interaction_types(corrected_response)
        
        try:
            # Проверяем новую схему
            jsonschema.validate(corrected_response, self.full_response_schema)
            print("✅ JSON Schema валидация прошла успешно")
            return True, [], corrected_response
            
        except ValidationError as e:
            print(f"❌ JSON Schema валидация не прошла: {e.message}")
            
            # Детальный анализ ошибки
            detailed_errors = self._analyze_validation_error(e)
            errors.extend(detailed_errors)
            
            # Попытка автокоррекции
            try:
                corrected_response = self._auto_correct_response(corrected_response, e)
                
                # Повторная валидация исправленного ответа
                jsonschema.validate(corrected_response, self.full_response_schema)
                print("✅ Автокоррекция успешна, валидация прошла")
                return True, errors, corrected_response
                
            except InvalidStructureError as structure_error:
                print(f"❌ Невалидная структура данных: {structure_error}")
                errors.append(f"Невалидная структура: {structure_error}")
                
                # Graceful degradation fallback
                fallback_response = self.graceful_degradation_fallback(response)
                return False, errors, fallback_response
                
            except (ValidationError, SchemaError) as correction_error:
                print(f"❌ Автокоррекция не удалась: {correction_error}")
                errors.append(f"Автокоррекция не удалась: {correction_error}")
                
                # Graceful degradation fallback
                fallback_response = self.graceful_degradation_fallback(response)
                return False, errors, fallback_response
                
        except SchemaError as e:
            print(f"❌ Ошибка в самой схеме: {e.message}")
            errors.append(f"Ошибка схемы: {e.message}")
            return False, errors, response

    def _analyze_validation_error(self, error: ValidationError) -> List[str]:
        """🔍 Детальный анализ ошибки валидации"""
        errors = []
        
        # Основная ошибка
        errors.append(f"Ошибка валидации: {error.message}")
        
        # Путь к ошибке
        if error.absolute_path:
            path = ' -> '.join(str(p) for p in error.absolute_path)
            errors.append(f"Путь к ошибке: {path}")
        
        # Значение, вызвавшее ошибку
        if hasattr(error, 'instance'):
            errors.append(f"Проблемное значение: {error.instance}")
        
        return errors

    def _upgrade_legacy_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """🕰️ Приводит ответы старого формата к новой структуре."""
        if not isinstance(payload, dict):
            return payload

        contacts = payload.get('contacts')
        if not isinstance(contacts, list):
            return payload

        legacy_contacts = [
            contact for contact in contacts
            if isinstance(contact, dict)
            and (contact.get('organization') is not None or contact.get('phone') is not None)
        ]

        has_legacy_structure = bool(legacy_contacts) or not isinstance(payload.get('organizations'), list)
        if not has_legacy_structure:
            return payload

        organizations = payload.get('organizations')
        if not isinstance(organizations, list):
            organizations = []
            payload['organizations'] = organizations

        org_by_name: Dict[str, Dict[str, Any]] = {}
        max_org_id = 0
        for org in organizations:
            if not isinstance(org, dict):
                continue
            org_id = org.get('organization_id')
            if isinstance(org_id, int):
                max_org_id = max(max_org_id, org_id)
            name = self._normalize_optional_string(org.get('name'))
            if name:
                org_by_name[name.lower()] = org

        if not organizations:
            max_org_id = 1
            default_org = {
                'organization_id': max_org_id,
                'name': 'Организация 1',
                'emails': [],
                'phones': [],
            }
            organizations.append(default_org)
            org_by_name[default_org['name'].lower()] = default_org

        for index, contact in enumerate(contacts):
            if not isinstance(contact, dict):
                continue

            legacy_org_name = self._normalize_optional_string(contact.pop('organization', None))
            if not isinstance(contact.get('organization_id'), int):
                resolved_org_id: Optional[int] = None
                if legacy_org_name:
                    lookup_key = legacy_org_name.lower()
                    if lookup_key in org_by_name:
                        resolved_org_id = org_by_name[lookup_key].get('organization_id')
                    else:
                        max_org_id += 1
                        new_org = {
                            'organization_id': max_org_id,
                            'name': legacy_org_name,
                            'emails': [],
                            'phones': [],
                        }
                        organizations.append(new_org)
                        org_by_name[lookup_key] = new_org
                        resolved_org_id = max_org_id
                if resolved_org_id is None:
                    resolved_org_id = organizations[0].get('organization_id', 1)
                contact['organization_id'] = resolved_org_id

            if not isinstance(contact.get('contact_id'), int):
                contact['contact_id'] = index + 1

            legacy_phone = contact.pop('phone', None)
            if legacy_phone and not contact.get('phones'):
                contact['phones'] = [{'number': str(legacy_phone).strip()}]
            elif 'phones' not in contact:
                contact['phones'] = []

            if 'role_in_message' not in contact:
                contact['role_in_message'] = 'other'

        if 'interactions' not in payload or not isinstance(payload['interactions'], list):
            payload['interactions'] = []
        if 'key_points' not in payload or not isinstance(payload['key_points'], list):
            payload['key_points'] = []
        if 'commercial_offers' not in payload or not isinstance(payload['commercial_offers'], list):
            payload['commercial_offers'] = []

        raw_business_context = payload.get('business_context')
        summary_defaults: Dict[str, Optional[str]] = {
            'topic': None,
            'product_interest': None,
            'communication_stage': None,
            'request_type': None,
        }

        if isinstance(raw_business_context, dict):
            summary_defaults['topic'] = self._normalize_optional_string(raw_business_context.get('topic'))
            summary_defaults['product_interest'] = self._normalize_optional_string(raw_business_context.get('product_interest'))
            summary_defaults['communication_stage'] = self._normalize_optional_string(raw_business_context.get('communication_stage'))
            summary_defaults['request_type'] = self._normalize_optional_string(raw_business_context.get('request_type'))
            payload['business_context'] = self._normalize_optional_string(raw_business_context.get('context')) or summary_defaults['topic'] or ''
        else:
            payload['business_context'] = self._normalize_optional_string(raw_business_context) or ''

        summary_block = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
        for key, value in summary_defaults.items():
            summary_block.setdefault(key, value)
        payload['summary'] = summary_block

        return payload

    def _auto_correct_response(self, response: Dict[str, Any], error: ValidationError) -> Dict[str, Any]:
        """🔧 Автокоррекция ответа"""
        corrected = copy.deepcopy(response)

        valid_fields = {"organizations", "contacts", "commercial_offers", "interactions"}
        if not any(field in corrected for field in valid_fields):
            raise InvalidStructureError("Полностью невалидная структура данных")

        changes_applied = False

        if self._ensure_base_structure(corrected):
            changes_applied = True

        if self._normalize_summary(corrected):
            changes_applied = True

        if self._normalize_business_context(corrected):
            changes_applied = True

        org_ids, orgs_changed = self._normalize_organizations(corrected)
        if orgs_changed:
            changes_applied = True

        contact_ids, contacts_changed = self._normalize_contacts(corrected, org_ids)
        if contacts_changed:
            changes_applied = True

        if self._normalize_interactions(corrected, org_ids, contact_ids):
            changes_applied = True

        if self._normalize_commercial_offers(corrected):
            changes_applied = True

        if self._normalize_key_points(corrected):
            changes_applied = True

        if changes_applied:
            corrected['auto_corrected'] = True
            corrected['validation_error'] = False

        return corrected

    def _ensure_base_structure(self, payload: Dict[str, Any]) -> bool:
        """🧱 Гарантирует наличие базовых структур в ответе."""
        changed = False

        list_fields = {
            'organizations': [],
            'contacts': [],
            'commercial_offers': [],
            'interactions': [],
            'key_points': [],
        }

        for field, default_value in list_fields.items():
            if not isinstance(payload.get(field), list):
                payload[field] = default_value.copy()
                print(f"🔧 Добавлена базовая структура для {field}")
                changed = True

        summary = payload.get('summary')
        if not isinstance(summary, dict):
            payload['summary'] = {
                'topic': None,
                'product_interest': None,
                'communication_stage': None,
                'request_type': None,
            }
            print("🔧 Добавлен объект summary по умолчанию")
            changed = True

        return changed

    def _normalize_summary(self, payload: Dict[str, Any]) -> bool:
        """📝 Нормализует блок summary."""
        summary = payload.get('summary')
        if not isinstance(summary, dict):
            return False

        changed = False
        for field in ('topic', 'product_interest', 'communication_stage', 'request_type'):
            value = summary.get(field)
            normalized = self._normalize_optional_string(value)
            if summary.get(field) != normalized:
                summary[field] = normalized
                changed = True
                print(f"🔧 Нормализовано поле summary.{field}")

        return changed

    def _normalize_business_context(self, payload: Dict[str, Any]) -> bool:
        """🏢 Приводит business_context к строке."""
        value = payload.get('business_context')
        normalized = self._normalize_optional_string(value) or ''
        if value != normalized:
            payload['business_context'] = normalized
            print("🔧 Нормализован business_context")
            return True
        return False

    def _normalize_organizations(self, payload: Dict[str, Any]) -> Tuple[List[int], bool]:
        """🏭 Нормализует организации и возвращает их ID."""
        organizations = payload.get('organizations', [])
        normalized_orgs: List[Dict[str, Any]] = []
        changed = False

        for index, organization in enumerate(organizations):
            if not isinstance(organization, dict):
                print(f"⚠️ Пропускаю невалидную организацию {index}")
                changed = True
                continue

            normalized = organization.copy()

            fallback_id = index + 1
            org_id, id_changed = self._coerce_positive_int(
                normalized.get('organization_id'),
                fallback=fallback_id,
                context=f"organization {index} organization_id",
            )
            normalized['organization_id'] = org_id
            changed = changed or id_changed

            name_value = normalized.get('name')
            normalized_name = self._normalize_optional_string(name_value) or f"Организация {org_id}"
            if normalized_name != name_value:
                normalized['name'] = normalized_name
                changed = True

            confidence_value = normalized.get('website_confidence')
            confidence, confidence_changed = self._coerce_float_in_range(
                confidence_value,
                minimum=0.0,
                maximum=1.0,
                fallback=None,
                context=f"organization {index} website_confidence",
            )
            if confidence_changed:
                normalized['website_confidence'] = confidence
                changed = True

            normalized_orgs.append(normalized)

        payload['organizations'] = normalized_orgs
        org_ids = [org['organization_id'] for org in normalized_orgs] or [1]
        return org_ids, changed

    def _normalize_contacts(self, payload: Dict[str, Any], available_org_ids: List[int]) -> Tuple[List[int], bool]:
        """👥 Нормализует контакты и возвращает их ID."""
        contacts = payload.get('contacts', [])
        normalized_contacts: List[Dict[str, Any]] = []
        changed = False
        primary_org_id = available_org_ids[0] if available_org_ids else 1

        for index, contact in enumerate(contacts):
            if not isinstance(contact, dict):
                print(f"⚠️ Пропускаю невалидный контакт {index}")
                changed = True
                continue

            normalized = contact.copy()

            contact_id, contact_changed = self._coerce_positive_int(
                normalized.get('contact_id'),
                fallback=index + 1,
                context=f"contact {index} contact_id",
            )
            normalized['contact_id'] = contact_id
            changed = changed or contact_changed

            organization_id, org_changed = self._coerce_positive_int(
                normalized.get('organization_id'),
                fallback=primary_org_id,
                context=f"contact {index} organization_id",
            )
            normalized['organization_id'] = organization_id
            changed = changed or org_changed

            name_value = normalized.get('name')
            normalized_name = self._normalize_optional_string(name_value) or f"Контакт {contact_id}"
            if normalized_name != name_value:
                normalized['name'] = normalized_name
                changed = True

            role_value = normalized.get('role_in_message')
            normalized_role = self._normalize_optional_string(role_value) or 'other'
            if normalized_role != role_value:
                normalized['role_in_message'] = normalized_role
                changed = True

            confidence_value = normalized.get('confidence')
            confidence, confidence_changed = self._coerce_float_in_range(
                confidence_value,
                minimum=0.0,
                maximum=1.0,
                fallback=0.5,
                context=f"contact {index} confidence",
            )
            if confidence_changed:
                normalized['confidence'] = confidence
                changed = True

            phones, phones_changed = self._normalize_phone_list(
                normalized.get('phones'),
                context=f"contact {index}",
            )
            if phones_changed:
                normalized['phones'] = phones
                changed = True

            value_score = normalized.get('value_score')
            if value_score is not None:
                score, score_changed = self._coerce_positive_int(
                    value_score,
                    fallback=0,
                    context=f"contact {index} value_score",
                )
                if score_changed:
                    normalized['value_score'] = score
                    changed = True

            normalized_contacts.append(normalized)

        payload['contacts'] = normalized_contacts
        contact_ids = [contact['contact_id'] for contact in normalized_contacts] or [1]
        return contact_ids, changed

    def _normalize_interactions(
        self,
        payload: Dict[str, Any],
        available_org_ids: List[int],
        available_contact_ids: List[int],
    ) -> bool:
        """🔁 Нормализует взаимодействия."""
        interactions = payload.get('interactions', [])
        normalized_interactions: List[Dict[str, Any]] = []
        changed = False

        primary_org_id = available_org_ids[0] if available_org_ids else 1
        primary_contact_id = available_contact_ids[0] if available_contact_ids else 1

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
            "other",
        }

        type_mapping = {
            'follow _up': 'follow_up',
            'follow _u p': 'follow_up',
            'info _request': 'clarification',
            'requested _quote': 'requested_quote',
            'sent _quote': 'sent_quote',
        }

        for index, interaction in enumerate(interactions):
            if not isinstance(interaction, dict):
                print(f"⚠️ Пропускаю невалидное взаимодействие {index}")
                changed = True
                continue

            normalized = interaction.copy()

            local_id, local_changed = self._coerce_positive_int(
                normalized.get('interaction_local_id'),
                fallback=index + 1,
                context=f"interaction {index} interaction_local_id",
            )
            normalized['interaction_local_id'] = local_id
            changed = changed or local_changed

            contact_id, contact_changed = self._coerce_positive_int(
                normalized.get('contact_id'),
                fallback=primary_contact_id,
                context=f"interaction {index} contact_id",
            )
            normalized['contact_id'] = contact_id
            changed = changed or contact_changed

            organization_id, org_changed = self._coerce_positive_int(
                normalized.get('organization_id'),
                fallback=primary_org_id,
                context=f"interaction {index} organization_id",
            )
            normalized['organization_id'] = organization_id
            changed = changed or org_changed

            role_value = normalized.get('role_in_message')
            normalized_role = self._normalize_optional_string(role_value) or 'other'
            if normalized_role != role_value:
                normalized['role_in_message'] = normalized_role
                changed = True

            interaction_type = normalized.get('interaction_type')
            normalized_type = type_mapping.get(interaction_type, interaction_type)
            if normalized_type not in allowed_types:
                normalized_type = 'other'
            if normalized_type != interaction_type:
                normalized['interaction_type'] = normalized_type
                changed = True

            summary_value = normalized.get('summary')
            summary_text = self._normalize_optional_string(summary_value) or ''
            if summary_text != summary_value:
                normalized['summary'] = summary_text
                changed = True

            attachments_value = normalized.get('attachments')
            if isinstance(attachments_value, str):
                attachments_value = [attachments_value]
            if not isinstance(attachments_value, list):
                attachments_value = []
            attachments = [
                str(attachment).strip()
                for attachment in attachments_value
                if not self._is_missing(attachment)
            ]
            if attachments != attachments_value:
                normalized['attachments'] = attachments
                changed = True

            confidence_value = normalized.get('confidence')
            confidence, confidence_changed = self._coerce_float_in_range(
                confidence_value,
                minimum=0.0,
                maximum=1.0,
                fallback=0.5,
                context=f"interaction {index} confidence",
            )
            if confidence_changed:
                normalized['confidence'] = confidence
                changed = True

            original_note = normalized.get('human_note')
            normalized_note = self._normalize_optional_string(original_note)
            if normalized_note is None:
                if original_note is not None:
                    normalized.pop('human_note', None)
                    changed = True
            else:
                if original_note != normalized_note:
                    normalized['human_note'] = normalized_note
                    changed = True

            original_participants = normalized.get('participants')
            participants_value = self._normalize_participants(original_participants)
            if participants_value is None:
                if original_participants is not None:
                    normalized.pop('participants', None)
                    changed = True
            else:
                if original_participants != participants_value:
                    normalized['participants'] = participants_value
                    changed = True

            normalized_interactions.append(normalized)

        payload['interactions'] = normalized_interactions
        return changed

    def _normalize_participants(self, value: Any) -> Optional[Participants]:
        """🧑‍🤝‍🧑 Нормализует структуру участников взаимодействия."""
        if value is None:
            return None
        if not isinstance(value, dict):
            return None

        normalized: Participants = {}

        actor = self._normalize_optional_string(value.get('actor'))
        if actor:
            normalized['actor'] = actor

        audience_raw = value.get('audience')
        audience: List[str] = []
        if isinstance(audience_raw, (list, tuple, set)):
            for entry in audience_raw:
                normalized_entry = self._normalize_optional_string(entry)
                if normalized_entry:
                    audience.append(normalized_entry)
        elif isinstance(audience_raw, str):
            normalized_entry = self._normalize_optional_string(audience_raw)
            if normalized_entry:
                audience.append(normalized_entry)

        if audience:
            normalized['audience'] = audience

        return normalized or None

    def _normalize_commercial_offers(self, payload: Dict[str, Any]) -> bool:
        """💼 Нормализует коммерческие предложения."""
        offers = payload.get('commercial_offers', [])
        normalized_offers: List[Dict[str, Any]] = []
        changed = False

        for index, offer in enumerate(offers):
            if not isinstance(offer, dict):
                print(f"⚠️ Пропускаю невалидное КП {index}")
                changed = True
                continue

            normalized = offer.copy()

            found_value = normalized.get('found')
            if not isinstance(found_value, bool):
                normalized['found'] = bool(found_value)
                changed = True
                print(f"🔧 Нормализован флаг found для КП {index}")

            equipment, equipment_changed, calculated_total = self._normalize_equipment_items(
                normalized.get('equipment_items'),
                offer_index=index,
            )
            if equipment_changed:
                normalized['equipment_items'] = equipment
                changed = True

            total_value = normalized.get('total_cost')
            if self._is_missing(total_value) and calculated_total is not None:
                normalized['total_cost'] = calculated_total
                changed = True
            elif not self._is_missing(total_value):
                coerced_total, total_changed = self._coerce_non_negative_float(
                    total_value,
                    fallback=calculated_total or 0.0,
                    context=f"commercial_offer {index} total_cost",
                )
                if total_changed:
                    normalized['total_cost'] = coerced_total
                    changed = True

            currency_value = normalized.get('currency')
            currency = self._normalize_optional_string(currency_value)
            if currency != currency_value:
                normalized['currency'] = currency
                changed = True

            normalized_offers.append(normalized)

        payload['commercial_offers'] = normalized_offers
        return changed

    def _normalize_equipment_items(
        self,
        equipment_items: Any,
        offer_index: int,
    ) -> Tuple[List[Dict[str, Any]], bool, Optional[float]]:
        """🧮 Нормализует позиции оборудования и возвращает рассчитанную сумму."""
        if not isinstance(equipment_items, list):
            return [], True, None

        normalized_items: List[Dict[str, Any]] = []
        changed = False
        total_cost = 0.0

        for index, item in enumerate(equipment_items):
            if not isinstance(item, dict):
                print(f"⚠️ Пропускаю невалидную позицию оборудования {offer_index}:{index}")
                changed = True
                continue

            normalized = item.copy()

            quantity, quantity_changed = self._coerce_positive_int(
                normalized.get('quantity'),
                fallback=1,
                context=f"equipment {offer_index}:{index} quantity",
            )
            if quantity_changed:
                normalized['quantity'] = quantity
                changed = True

            unit_price, unit_changed = self._coerce_non_negative_float(
                normalized.get('unit_price'),
                fallback=0.0,
                context=f"equipment {offer_index}:{index} unit_price",
            )
            if unit_changed:
                normalized['unit_price'] = unit_price
                changed = True

            total_price, total_changed = self._coerce_non_negative_float(
                normalized.get('total_price'),
                fallback=quantity * unit_price,
                context=f"equipment {offer_index}:{index} total_price",
            )
            if total_changed or self._is_missing(normalized.get('total_price')):
                normalized['total_price'] = total_price
                changed = True

            total_cost += total_price
            normalized_items.append(normalized)

        calculated_total = total_cost if normalized_items else None
        return normalized_items, changed, calculated_total

    def _normalize_key_points(self, payload: Dict[str, Any]) -> bool:
        """📌 Приводит key_points к списку строк."""
        key_points = payload.get('key_points', [])
        normalized_points: List[str] = []
        changed = False

        for index, point in enumerate(key_points):
            if self._is_missing(point):
                print(f"⚠️ Пропущена пустая запись key_points[{index}]")
                changed = True
                continue
            text = str(point).strip()
            if text != point:
                changed = True
            normalized_points.append(text)

        payload['key_points'] = normalized_points
        return changed

    def _normalize_phone_list(self, phones: Any, context: str) -> Tuple[List[Dict[str, Any]], bool]:
        """📞 Приведение массива телефонов к унифицированному виду."""
        if not isinstance(phones, list):
            return [], True

        normalized: List[Dict[str, Any]] = []
        changed = False

        for index, phone in enumerate(phones):
            if isinstance(phone, str):
                number = phone.strip()
                normalized.append({
                    'number': number,
                    'type': 'mobile',
                    'formatted': number,
                    'normalized': None,
                    'extension': None,
                    'confidence': 0.8,
                })
                changed = True
                print(f"🔧 Преобразован телефон {context}[{index}] из строки")
            elif isinstance(phone, dict):
                normalized.append(phone)
            else:
                changed = True
                print(f"⚠️ Пропускаю невалидный телефон {context}[{index}]")

        return normalized, changed

    def _coerce_positive_int(self, value: Any, fallback: int, context: str) -> Tuple[int, bool]:
        """🔢 Безопасное приведение числа к положительному целому."""
        original_value = value
        if self._is_missing(value):
            print(f"🔧 Установлено значение по умолчанию для {context}: {fallback}")
            return fallback, True

        try:
            if isinstance(value, bool):
                coerced = int(value)
            elif isinstance(value, (int, float)):
                coerced = int(round(value))
            elif isinstance(value, str):
                cleaned = value.replace(',', '.').strip()
                coerced = int(round(float(cleaned)))
            else:
                raise TypeError
        except (TypeError, ValueError):
            print(f"⚠️ Не удалось привести {context}='{original_value}', использую {fallback}")
            return fallback, True

        if coerced <= 0:
            coerced = abs(coerced) or fallback

        changed = coerced != original_value
        if changed:
            print(f"🔧 Нормализован {context}: {original_value} → {coerced}")
        return coerced, changed

    def _coerce_non_negative_float(self, value: Any, fallback: float, context: str) -> Tuple[float, bool]:
        """💰 Приведение значения к неотрицательному float."""
        original_value = value
        if self._is_missing(value):
            return fallback, True

        try:
            if isinstance(value, bool):
                coerced = float(int(value))
            elif isinstance(value, (int, float)):
                coerced = float(value)
            elif isinstance(value, str):
                cleaned = value.replace(',', '.').strip()
                coerced = float(cleaned)
            else:
                raise TypeError
        except (TypeError, ValueError):
            print(f"⚠️ Не удалось привести {context}='{original_value}', использую {fallback}")
            return fallback, True

        if coerced < 0:
            coerced = abs(coerced)

        changed = coerced != original_value
        if changed:
            print(f"🔧 Нормализован {context}: {original_value} → {coerced}")
        return coerced, changed

    def _coerce_float_in_range(
        self,
        value: Any,
        minimum: float,
        maximum: float,
        fallback: Optional[float],
        context: str,
    ) -> Tuple[Optional[float], bool]:
        """📈 Приведение float к допустимому диапазону."""
        if self._is_missing(value):
            if fallback is None:
                return None, False
            return fallback, True

        candidate, changed = self._coerce_non_negative_float(value, fallback if fallback is not None else 0.0, context)
        clamped = max(min(candidate, maximum), minimum)
        if clamped != candidate:
            changed = True
            candidate = clamped

        if fallback is None and candidate == 0.0:
            return None, changed

        return candidate, changed

    def _normalize_optional_string(self, value: Any) -> Optional[str]:
        """🪄 Приводит значение к строке или None."""
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        text = str(value).strip()
        return text or None

    def _is_missing(self, value: Any) -> bool:
        """❓ Проверяет, является ли значение отсутствующим."""
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ''
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False
    def graceful_degradation_fallback(self, invalid_response: Dict[str, Any]) -> Dict[str, Any]:
        """🛡️ Fallback для невалидных ответов"""
        print("🛡️ Применяем graceful degradation fallback")
        
        return {
            "organizations": [],
            "contacts": [],
            "business_context": "Ошибка валидации",
            "summary": {
                "topic": "Ошибка обработки",
                "product_interest": None,
                "communication_stage": None,
                "request_type": None
            },
            "key_points": [],
            "commercial_offers": [],
            "interactions": [],
            "validation_error": True,
            "original_response": invalid_response
        }

    def _normalize_keys_with_spaces(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """🔧 Нормализация ключей с пробелами от Replicate LLM"""
        if not isinstance(data, dict):
            return data
        
        normalized = {}
        
        # Маппинг проблемных ключей
        key_mappings = {
            # Основные ключи
            'organ izations': 'organizations',
            'organization _id': 'organization_id',
            'contact _id': 'contact_id',
            'business _context': 'business_context',
            'key _points': 'key_points',
            'commercial_offers': 'commercial_offers',
            'inter actions': 'interactions',
            
            # Ключи контактов
            'role _in _message': 'role_in_message',
            
            # Ключи summary
            'product _ interest': 'product_interest',
            'communication _st age': 'communication_stage',
            'communication _stage': 'communication_stage',
            'request _type': 'request_type',
            
            # Ключи взаимодействий
            'inter action _local _id': 'interaction_local_id',
            'interaction _local _id': 'interaction_local_id',
            'message _sub ject': 'message_subject',
            'message _date': 'message_date',
            'role _in _message': 'role_in_message',
            'inter action _type': 'interaction_type',
            'interaction _type': 'interaction_type',
            'att achments': 'attachments',
            'follow _up': 'follow_up',
            'follow _u p': 'follow_up',
            'info _request': 'clarification',
            'requested _quote': 'requested_quote',
            'sent _quote': 'sent_quote',
            
            # Ключи КП
            'offer _type': 'offer_type',
            'offer _number': 'offer_number',
            'offer _date': 'offer_date',
            'end _user': 'end_user',
            'end_user_inn': 'end_user_inn',
            'inter medi ary': 'intermediary',
            'inter medi ary _date': 'intermediary_date',
            'intermediary _date': 'intermediary_date',
            'payment _ terms': 'payment_terms',
            'payment _terms': 'payment_terms',
            'del ivery _time': 'delivery_time',
            'delivery _time': 'delivery_time',
            'delivery_terms': 'delivery_terms',
            'valid_until': 'valid_until',
            'equ ipment _items': 'equipment_items',
            'equipment _items': 'equipment_items',
            'total _cost': 'total_cost',
            'unit _price': 'unit_price',
            'total _price': 'total_price'
        }
        
        for key, value in data.items():
            # Нормализуем ключ
            normalized_key = key_mappings.get(key, key)
            
            # Если ключ не найден в маппинге, пробуем удалить пробелы
            if normalized_key == key and ' ' in key:
                # Удаляем все пробелы из ключа
                normalized_key = key.replace(' ', '')
                
                # Проверяем, есть ли такой ключ в ожидаемых
                expected_keys = {
                    'organizations', 'contacts', 'business_context', 'summary', 
                    'key_points', 'commercial_offers', 'interactions',
                    'organization_id', 'contact_id', 'role_in_message',
                    'product_interest', 'communication_stage', 'request_type',
                    'interaction_local_id', 'message_subject', 'message_date',
                    'interaction_type', 'attachments', 'offer_type', 'offer_number',
                    'offer_date', 'end_user', 'intermediary', 'intermediary_date',
                    'payment_terms', 'delivery_time', 'delivery_terms',
                    'valid_until', 'equipment_items', 'total_cost', 'unit_price',
                    'total_price'
                }
                
                if normalized_key not in expected_keys:
                    # Возвращаем исходный ключ, если нормализованный не ожидается
                    normalized_key = key
            
            # Рекурсивно обрабатываем вложенные структуры
            if isinstance(value, dict):
                normalized[normalized_key] = self._normalize_keys_with_spaces(value)
            elif isinstance(value, list):
                normalized[normalized_key] = [
                    self._normalize_keys_with_spaces(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                normalized[normalized_key] = value
        
        return normalized

    def _auto_correct_missing_interaction_type(self, interactions: List[Dict]) -> List[Dict]:
        """
        🔧 Умная автокоррекция отсутствующего interaction_type
        
        Анализирует контекст взаимодействия для выбора правильного типа
        """
        for interaction in interactions:
            if 'interaction_type' not in interaction or not interaction.get('interaction_type'):
                # Умная догадка на основе других полей
                context = str(interaction).lower()
                summary = interaction.get('summary', '').lower()
                
                # Проверяем запросы ПЕРЕД отправкой КП (приоритет выше)
                if any(word in context for word in ['запрос', 'прошу', 'хочу', 'нужно', 'можете', 'выслать']):
                    guessed_type = 'requested_quote'
                # Проверяем отправку КП/предложений
                elif any(word in context for word in ['коммерч', 'предложен', 'offer']) or \
                     ('кп' in summary and any(word in summary for word in ['отправ', 'направ', 'высла', 'sent'])):
                    guessed_type = 'sent_quote'
                elif any(word in context for word in ['жалоб', 'рекламац', 'complaint', 'проблем']):
                    guessed_type = 'complaint'
                elif any(word in context for word in ['счет', 'счёт', 'invoice', 'оплат']):
                    guessed_type = 'invoice_sent'
                elif any(word in context for word in ['договор', 'contract', 'подпис']):
                    guessed_type = 'contract_sent'
                elif any(word in context for word in ['уточн', 'вопрос', 'clarif', 'question']):
                    guessed_type = 'clarification'
                else:
                    guessed_type = 'other'
                
                interaction['interaction_type'] = guessed_type
                interaction['_auto_corrected'] = True
                interaction['_correction_reason'] = f'Автокоррекция на основе контекста → {guessed_type}'
                
                print(f"⚠️ Автокоррекция interaction_type:")
                print(f"   ID: {interaction.get('interaction_local_id')}")
                print(f"   Добавлено: {guessed_type}")
                summary = interaction.get('summary', '')
                if summary:
                    print(f"   Контекст: {summary[:100]}...")
        
        return interactions

    def _normalize_interaction_types(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """🔧 Нормализация типов взаимодействий с пробелами"""
        if not isinstance(data, dict):
            return data
        
        # Маппинг проблемных типов взаимодействий
        interaction_type_mapping = {
            'follow _up': 'follow_up',
            'follow _u p': 'follow_up',
            'info _request': 'clarification',
            'requested _quote': 'requested_quote',
            'sent _quote': 'sent_quote'
        }
        
        # Обрабатываем взаимодействия
        if 'interactions' in data and isinstance(data['interactions'], list):
            # Сначала умная автокоррекция отсутствующих типов
            data['interactions'] = self._auto_correct_missing_interaction_type(data['interactions'])
            
            # Затем нормализация проблемных типов
            for interaction in data['interactions']:
                if isinstance(interaction, dict) and 'interaction_type' in interaction:
                    interaction_type = interaction['interaction_type']
                    if interaction_type in interaction_type_mapping:
                        interaction['interaction_type'] = interaction_type_mapping[interaction_type]
                        print(f"🔧 Нормализован тип взаимодействия: {interaction_type} -> {interaction_type_mapping[interaction_type]}")
        
        return data

    def validate_organizations(self, organizations: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """🏢 Валидация массива организаций"""
        errors = []
        
        for i, org in enumerate(organizations):
            try:
                jsonschema.validate(org, self.organization_schema)
            except ValidationError as e:
                errors.append(f"Организация {i}: {e.message}")
        
        return len(errors) == 0, errors

    def validate_contacts(self, contacts: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """👤 Валидация массива контактов"""
        errors = []
        
        for i, contact in enumerate(contacts):
            try:
                jsonschema.validate(contact, self.contact_schema)
            except ValidationError as e:
                errors.append(f"Контакт {i}: {e.message}")
        
        return len(errors) == 0, errors

    def validate_commercial_offers(self, commercial_offers: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """💼 Валидация массива коммерческих предложений"""
        errors = []
        
        for i, offer in enumerate(commercial_offers):
            try:
                jsonschema.validate(offer, self.commercial_offer_schema)
                
                # Дополнительная бизнес-валидация
                validation_errors = self._validate_commercial_offer_business_rules(offer, i)
                errors.extend(validation_errors)
                
            except ValidationError as e:
                errors.append(f"КП {i}: {e.message}")
        
        return len(errors) == 0, errors

    def _validate_commercial_offer_business_rules(self, offer: Dict[str, Any], index: int) -> List[str]:
        """🔍 Валидация бизнес-правил для коммерческого предложения"""
        errors = []
        
        # Если КП найдено, должны быть заполнены ключевые поля
        if offer.get('found', False):
            required_fields = ['offer_number', 'offer_date', 'total_cost']
            for field in required_fields:
                if not offer.get(field):
                    errors.append(f"КП {index}: Для найденного КП обязательно поле '{field}'")
            
            # Проверка equipment_items
            equipment_items = offer.get('equipment_items', [])
            if not equipment_items:
                errors.append(f"КП {index}: Для найденного КП должен быть список оборудования")
            else:
                # Проверка соответствия total_cost сумме позиций
                total_from_items = sum(item.get('total_price', 0) for item in equipment_items)
                total_cost = offer.get('total_cost', 0)
                if total_cost and abs(total_from_items - total_cost) > 0.01:
                    errors.append(f"КП {index}: Несоответствие общей суммы ({total_cost}) и суммы позиций ({total_from_items})")
        
        return errors

    def postprocess_commercial_offers(self, commercial_offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """💼 Постобработка коммерческих предложений"""
        processed_offers = []
        
        for offer in commercial_offers:
            processed_offer = offer.copy()
            
            # Нормализация валюты
            if 'currency' not in processed_offer or not processed_offer['currency']:
                processed_offer['currency'] = 'RUB'
            
            # Валидация и исправление equipment_items
            if 'equipment_items' in processed_offer:
                processed_items = []
                for item in processed_offer['equipment_items']:
                    processed_item = item.copy()
                    
                    # Проверка соответствия total_price = quantity * unit_price
                    if all(k in processed_item for k in ['quantity', 'unit_price']):
                        calculated_total = processed_item['quantity'] * processed_item['unit_price']
                        if 'total_price' not in processed_item or abs(processed_item['total_price'] - calculated_total) > 0.01:
                            processed_item['total_price'] = calculated_total
                    
                    processed_items.append(processed_item)
                
                processed_offer['equipment_items'] = processed_items
                
                # Пересчет общей стоимости
                if processed_items:
                    calculated_total_cost = sum(item.get('total_price', 0) for item in processed_items)
                    processed_offer['total_cost'] = calculated_total_cost
            
            processed_offers.append(processed_offer)
        
        return processed_offers

    def validate_and_postprocess(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """🔄 Полная валидация и постобработка ответа LLM"""
        # 1. JSON Schema валидация с автокоррекцией
        is_valid, errors, corrected_data = self.validate_llm_response(data)
        
        if not is_valid:
            # Graceful degradation для невалидных данных
            print(f"⚠️ Валидация не пройдена, применяется graceful degradation. Ошибки: {errors}")
            return self.graceful_degradation_fallback(data)
        
        # 2. Постпроцессинг валидных данных
        try:
            from ..postprocessing.postprocessor import PostProcessor
            postprocessor = PostProcessor()
            
            print("🔄 Применяется постпроцессинг к валидным данным")
            processed_data = postprocessor.process_llm_response(corrected_data)
            
            return processed_data
            
        except Exception as e:
            print(f"❌ Ошибка постпроцессинга: {e}")
            # Возвращаем валидные данные без постпроцессинга
            return corrected_data

    def get_validation_stats(self) -> Dict[str, Any]:
        """📊 Получение статистики валидации"""
        return {
            "validator_version": "2.0.0",
            "supported_format": "organizations/contacts",
            "schemas_loaded": {
                "organization_schema": bool(self.organization_schema),
                "contact_schema": bool(self.contact_schema),
                "phone_schema": bool(self.phone_schema),
                "commercial_offer_schema": bool(self.commercial_offer_schema),
                "interaction_schema": bool(self.interaction_schema),
                "full_response_schema": bool(self.full_response_schema)
            }
        }


# Пример использования
if __name__ == "__main__":
    validator = LLMResponseValidator()
    
    # Тестовый ответ в новом формате
    test_response = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "inn": "1901066506",
                "city": "Москва",
                "emails": ["info@dna-technology.ru"],
                "phones": ["8 800 200-75-15"]
            }
        ],
        "contacts": [
            {
                "name": "Гоголева Мария",
                "organization_id": 1,
                "email": "m.gogoleva@dna-technology.ru",
                "phones": [
                    {
                        "type": "main",
                        "number": "+7(495) 640-17-71"
                    }
                ],
                "confidence": 0.95
            }
        ]
    }
    
    # Валидация
    is_valid, errors, corrected = validator.validate_llm_response(test_response)
    print(f"Валидация: {is_valid}")
    if errors:
        print(f"Ошибки: {errors}")
    
    # Статистика
    stats = validator.get_validation_stats()
    print(f"Статистика: {stats}")
