#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧹 Pre-validation слой для ответов LLM перед строгой JSON Schema.
"""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

_PRE_VALIDATION_VERSION = "1.0.0"

_ALLOWED_INTERACTION_TYPES = {
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

_INTERACTION_TYPE_ALIASES = {
    "info_request": "clarification",
    "information_request": "clarification",
    "request_info": "clarification",
    "followup": "follow_up",
    "follow-up": "follow_up",
    "follow up": "follow_up",
    "clarify": "clarification",
    "clarification_request": "clarification",
    "quote_request": "requested_quote",
}


def _safe_int(value: Any) -> int | None:
    """🔢 Безопасное приведение к int."""
    if isinstance(value, bool):
        return 1 if value else None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _resolve_primary_id(items: Any, field_name: str) -> int:
    """🧭 Получение основного идентификатора из коллекции."""
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                candidate = _safe_int(item.get(field_name))
                if candidate:
                    return max(candidate, 1)
    return 1


def _normalize_interaction_type(raw_value: Any) -> Tuple[str | None, str | None]:
    """🎛️ Приводит interaction_type к допустимому значению."""
    if not isinstance(raw_value, str):
        return None, None

    normalized = raw_value.strip().lower()
    normalized = normalized.replace("-", "_").replace(" ", "_")

    if normalized in _ALLOWED_INTERACTION_TYPES:
        return normalized, None

    if normalized in _INTERACTION_TYPE_ALIASES:
        return _INTERACTION_TYPE_ALIASES[normalized], normalized

    return "other", normalized


def pre_validate_llm_response(payload: Any) -> Tuple[Any, List[str]]:
    """
    🧹 Предварительно нормализует ответ до JSON Schema, возвращает фиксы.

    Args:
        payload: Исходные данные от LLM.

    Returns:
        Кортеж из нормализованных данных и списка описаний исправлений.
    """
    if not isinstance(payload, dict):
        return payload, []

    corrected = copy.deepcopy(payload)
    corrections: List[str] = []

    fallback_org_id = _resolve_primary_id(corrected.get("organizations"), "organization_id")
    fallback_contact_id = _resolve_primary_id(corrected.get("contacts"), "contact_id")

    interactions = corrected.get("interactions")
    if not isinstance(interactions, list):
        return corrected, corrections

    for index, interaction in enumerate(interactions):
        if not isinstance(interaction, dict):
            continue

        if interaction.get("contact_id") is None:
            interaction["contact_id"] = fallback_contact_id
            message = f"interaction[{index}].contact_id → {fallback_contact_id}"
            corrections.append(message)
            logger.info("🔧 Pre-validation: %s", message)

        if interaction.get("organization_id") is None:
            interaction["organization_id"] = fallback_org_id
            message = f"interaction[{index}].organization_id → {fallback_org_id}"
            corrections.append(message)
            logger.info("🔧 Pre-validation: %s", message)

        normalized_type, original_type = _normalize_interaction_type(interaction.get("interaction_type"))
        if normalized_type and normalized_type != interaction.get("interaction_type"):
            interaction["interaction_type"] = normalized_type
            if original_type:
                message = (
                    f"interaction[{index}].interaction_type {original_type} → {normalized_type}"
                )
            else:
                message = (
                    f"interaction[{index}].interaction_type → {normalized_type}"
                )
            corrections.append(message)
            logger.info("🔧 Pre-validation: %s", message)

    if corrections:
        metadata = corrected.get("postprocessing_metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            corrected["postprocessing_metadata"] = metadata

        metadata["pre_validation"] = {
            "version": _PRE_VALIDATION_VERSION,
            "fixes": corrections,
        }

    return corrected, corrections


__all__ = ["pre_validate_llm_response"]
