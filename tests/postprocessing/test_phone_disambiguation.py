#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для resolve_phone_conflicts в PostProcessor
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.postprocessing.postprocessor import PostProcessor
from src.registry.global_registry import GlobalIDRegistry


@pytest.fixture
def mock_registry():
    registry = Mock(spec=GlobalIDRegistry)
    registry.resolve_organization.return_value = Mock(gid="org_med", match_rule="INN")
    registry.resolve_contact.return_value = Mock(gid="contact_1")
    return registry


@pytest.fixture
def postprocessor(mock_registry):
    with patch('src.postprocessing.postprocessor.GlobalIDRegistry', return_value=mock_registry):
        return PostProcessor(phone_overrides_path=Path("tests/fixtures/phone_overrides_test.yml"))


def test_resolve_phone_conflicts_city_match(postprocessor):
    """Тест resolved по city_match (area_code)."""
    organizations = {
        1: {"gid": "org_dnk", "name": "ДНК-Технология", "city": "москва", "phones": [{"normalized": "+74951234567"}]},
        2: {"gid": "org_med", "name": "МЕД КОНГРЕСС", "city": "новосибирск", "phones": [{"normalized": "+73833802104"}]},
    }
    contacts = [{"organization_id": 1, "phones": [{"normalized": "+74951234567"}]}]  # contact_match для ДНК
    
    # Дублируем телефон +7(383) в ДНК (LLM error)
    organizations[1]["phones"].append({"normalized": "+73833802104"})
    
    conflicts = postprocessor._resolve_phone_conflicts(organizations, contacts)
    
    assert len(conflicts["resolved"]) == 1
    resolved = conflicts["resolved"][0]
    assert resolved["phone"] == "+73833802104"
    assert resolved["status"] == "resolved"
    assert resolved["kept_gid"] == "org_med"
    assert resolved["removed_gids"] == ["org_dnk"]
    assert resolved["reason"] == "area_match"  # city Novosibirsk matches 383
    
    # Проверить, что телефон удалён из ДНК
    assert len(organizations[1]["phones"]) == 1
    assert organizations[1]["phones"][0]["normalized"] == "+74951234567"
    assert len(organizations[2]["phones"]) == 1
    assert organizations[2]["phones"][0]["normalized"] == "+73833802104"


def test_resolve_phone_conflicts_unresolved(postprocessor):
    """Тест unresolved при равных scores."""
    organizations = {
        1: {"gid": "org1", "name": "Org1", "city": "москва", "phones": [{"normalized": "+74951234567"}]},
        2: {"gid": "org2", "name": "Org2", "city": "москва", "phones": [{"normalized": "+74951234567"}]},  # same city, no domain/contact diff
    }
    contacts = []  # no contact_match
    
    conflicts = postprocessor._resolve_phone_conflicts(organizations, contacts)
    
    assert len(conflicts["unresolved"]) == 1
    unresolved = conflicts["unresolved"][0]
    assert unresolved["phone"] == "+74951234567"
    assert unresolved["status"] == "unresolved"
    assert unresolved["owners"] == ["org1", "org2"]
    assert unresolved["reason"] == "ambiguous"
    
    # Телефоны не удалены
    assert len(organizations[1]["phones"]) == 1
    assert len(organizations[2]["phones"]) == 1


def test_resolve_phone_conflicts_override(postprocessor):
    """Тест resolved по override."""
    # Mock overrides: +73833802104 -> org_med
    with patch.object(postprocessor, 'phone_overrides', {'+73833802104': 'org_med'}):
        organizations = {
            1: {"gid": "org_dnk", "name": "ДНК-Технология", "city": "москва", "phones": [{"normalized": "+73833802104"}]},
            2: {"gid": "org_med", "name": "МЕД КОНГРЕСС", "city": "новосибирск", "phones": [{"normalized": "+73833802104"}]},
        }
        contacts = []
        
        conflicts = postprocessor._resolve_phone_conflicts(organizations, contacts)
        
        assert len(conflicts["resolved"]) == 1
        resolved = conflicts["resolved"][0]
        assert resolved["phone"] == "+73833802104"
        assert resolved["status"] == "resolved"
        assert resolved["kept_gid"] == "org_med"
        assert resolved["removed_gids"] == ["org_dnk"]
        assert resolved["reason"] == "override"
        
        # Телефон удалён из ДНК
        assert len(organizations[1]["phones"]) == 0
        assert len(organizations[2]["phones"]) == 1


def test_integration_email_018(postprocessor):
    """Интеграционный тест: email_018/019 - +7(383) remains at МЕД КОНГРЕСС, removed from ДНК."""
    llm_result = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "city": "Москва",
                "phones": [{"number": "+7 (495) 123-45-67", "normalized": "+74951234567"}],
                "emails": ["info@dna.ru"]
            },
            {
                "organization_id": 2,
                "name": "МЕД КОНГРЕСС",
                "city": "Новосибирск",
                "phones": [{"number": "+7 (383) 380-21-04", "normalized": "+73833802104"}],
                "emails": ["info@medcongress.ru"]
            }
        ],
        "contacts": [
            {"contact_id": 1, "organization_id": 1, "name": "Иванов И.", "phones": [{"normalized": "+74951234567"}]}
        ],
        "interactions": [],
        "summary": {},
        "key_points": [],
        "business_context": "",
        "commercial_offers": []
    }
    
    # Simulate LLM error: duplicate +7(383) in ДНК
    llm_result["organizations"][0]["phones"].append({"number": "+7 (383) 380-21-04", "normalized": "+73833802104"})
    
    processed = postprocessor.process_llm_response(llm_result)
    
    metadata = processed["postprocessing_metadata"]
    phone_conflicts = metadata.get("phone_conflicts", {})
    
    assert "resolved" in phone_conflicts
    resolved = [c for c in phone_conflicts["resolved"] if c["phone"] == "+73833802104"]
    assert len(resolved) == 1
    assert resolved[0]["kept_gid"] == "org_med"  # Assuming GID from mock
    assert "org_dnk" in resolved[0]["removed_gids"]
    
    # Check final orgs phones
    final_orgs = {org["name"]: org["phones"] for org in processed["organizations"]}
    assert len(final_orgs["ДНК-Технология"]) == 1  # Only +7495
    assert final_orgs["ДНК-Технология"][0]["normalized"] == "+74951234567"
    assert len(final_orgs["МЕД КОНГРЕСС"]) == 1  # +7383
    assert final_orgs["МЕД КОНГРЕСС"][0]["normalized"] == "+73833802104"