#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тесты для pre_validate_llm_response.
"""

import logging

from src.core.pre_validator import pre_validate_llm_response


def test_pre_validation_fixes_missing_ids(caplog):
    """Проверяет, что None идентификаторы заменяются fallback значениями."""
    caplog.set_level(logging.INFO)
    payload = {
        "organizations": [{"organization_id": 3, "name": "Org"}],
        "contacts": [{"contact_id": 7, "name": "Alice"}],
        "interactions": [
            {
                "interaction_local_id": 1,
                "contact_id": None,
                "organization_id": None,
                "interaction_type": "info_request",
            }
        ],
    }

    corrected, fixes = pre_validate_llm_response(payload)

    assert corrected["interactions"][0]["contact_id"] == 7
    assert corrected["interactions"][0]["organization_id"] == 3
    assert corrected["interactions"][0]["interaction_type"] == "clarification"
    assert "contact_id" in fixes[0]
    assert "organization_id" in fixes[1]
    assert "interaction_type" in fixes[2]
    assert any("Pre-validation" in record.message for record in caplog.records)


def test_pre_validation_keeps_valid_values():
    """Проверяет, что валидные interaction_type остаются без изменений."""
    payload = {
        "organizations": [{"organization_id": 2}],
        "contacts": [{"contact_id": 5}],
        "interactions": [
            {
                "interaction_local_id": 1,
                "contact_id": 9,
                "organization_id": 4,
                "interaction_type": "sent_quote",
            }
        ],
    }

    corrected, fixes = pre_validate_llm_response(payload)

    assert corrected["interactions"][0]["contact_id"] == 9
    assert corrected["interactions"][0]["organization_id"] == 4
    assert corrected["interactions"][0]["interaction_type"] == "sent_quote"
    assert fixes == []


def test_pre_validation_sets_metadata():
    """Проверяет запись метаданных о правках."""
    payload = {
        "organizations": [],
        "contacts": [],
        "interactions": [
            {
                "interaction_local_id": 1,
                "contact_id": None,
                "organization_id": None,
                "interaction_type": "unknown_value",
            }
        ],
        "postprocessing_metadata": {},
    }

    corrected, fixes = pre_validate_llm_response(payload)

    assert corrected["interactions"][0]["interaction_type"] == "other"
    assert corrected["postprocessing_metadata"]["pre_validation"]["fixes"] == fixes
    assert corrected["postprocessing_metadata"]["pre_validation"]["version"] == "1.0.0"
