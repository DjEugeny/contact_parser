#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Интеграционный тест Global ID Registry
Проверяет работу реестра на реальных данных из pipeline
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List

import pytest

from src.registry import GlobalIDRegistry
from src.postprocessing.postprocessor import PostProcessor


def test_gid_stability_across_runs(tmp_path: Path):
    """✅ Проверка: повторный прогон даёт те же gid"""
    registry = GlobalIDRegistry(registry_dir=tmp_path)
    
    # Эмуляция данных от LLM (2 прогона одного письма)
    llm_data = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ООО ДНК-Технология",
                "inn": "7723537840",
                "website": "https://dna-technology.ru",
                "city": "Москва",
                "emails": ["info@dna-technology.ru"],
                "phones": ["8 800 200-75-15"]
            }
        ],
        "contacts": [
            {
                "contact_id": 101,
                "name": "Гоголева Мария Михайловна",
                "organization_id": 1,
                "position": "Менеджер по продажам",
                "email": "m.gogoleva@dna-technology.ru",
                "phones": [{"number": "+7(495) 640-17-71"}]
            }
        ],
        "interactions": [],
        "business_context": "Тест",
        "summary": {"topic": "Тест"},
        "key_points": [],
        "commercial_offers": []
    }
    
    # Первый прогон
    postprocessor1 = PostProcessor()
    postprocessor1.gid_registry = registry
    result1 = postprocessor1.process_llm_response(llm_data.copy())
    
    org_gid_1 = result1["organizations"][0]["gid"]
    contact_gid_1 = result1["contacts"][0]["gid"]
    
    # Второй прогон (новый постпроцессор, тот же реестр)
    postprocessor2 = PostProcessor()
    postprocessor2.gid_registry = registry
    result2 = postprocessor2.process_llm_response(llm_data.copy())
    
    org_gid_2 = result2["organizations"][0]["gid"]
    contact_gid_2 = result2["contacts"][0]["gid"]
    
    # Проверка стабильности
    assert org_gid_1 == org_gid_2, "GID организации должен быть стабильным"
    assert contact_gid_1 == contact_gid_2, "GID контакта должен быть стабильным"
    
    # Проверка метаданных
    gid_meta = result2["postprocessing_metadata"]["gid"]
    assert "assigned" in gid_meta
    assert "conflicts" in gid_meta
    assert len(gid_meta["assigned"]) == 2  # org + contact


def test_cross_email_deduplication(tmp_path: Path):
    """✅ Проверка: одна организация из разных писем → один gid"""
    registry = GlobalIDRegistry(registry_dir=tmp_path)

    # Письмо 1: полная информация
    email1 = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ООО МИЛЛАБ",
                "inn": "7708987654",
                "website": "https://millab.ru",
                "city": "Москва",
                "emails": ["info@millab.ru"]
            }
        ],
        "contacts": [
            {
                "contact_id": 1,
                "name": "Иванов Иван",
                "organization_id": 1,
                "email": "ivanov@millab.ru",
                "phones": []
            }
        ],
        "interactions": [],
        "business_context": "",
        "summary": {},
        "key_points": [],
        "commercial_offers": []
    }

    # Письмо 2: частичная информация (без ИНН)
    email2 = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "МИЛЛАБ",
                "inn": None,
                "website": "millab.ru",
                "city": "Москва",
                "emails": ["sales@millab.ru"]
            }
        ],
        "contacts": [
            {
                "contact_id": 1,
                "name": "Петров Пётр",
                "organization_id": 1,
                "email": "petrov@millab.ru",
                "phones": []
            }
        ],
        "interactions": [],
        "business_context": "",
        "summary": {},
        "key_points": [],
        "commercial_offers": []
    }

    postprocessor = PostProcessor()
    postprocessor.gid_registry = registry

    result1 = postprocessor.process_llm_response(email1)
    postprocessor._reset_runtime_state()
    result2 = postprocessor.process_llm_response(email2)

    org_gid_1 = result1["organizations"][0]["gid"]
    org_gid_2 = result2["organizations"][0]["gid"]

    assert org_gid_1 == org_gid_2, "Организация из разных писем должна иметь один gid"

    # Проверяем, что в реестре есть правильные ключи
    all_keys = registry.get_all_keys_for_gid(org_gid_1)
    assert any(key[1] == "INN" for key in all_keys), "Должен быть ключ ИНН"
    assert any(key[1] == "DOMAIN" for key in all_keys), "Должен быть ключ DOMAIN"
    assert any(key[1] == "NAME_CITY" for key in all_keys), "Должен быть ключ NAME_CITY"


def test_contact_unique_per_org(tmp_path: Path):
    """✅ Проверка: контакты с одинаковым email, но разными орг → разные gid"""
    registry = GlobalIDRegistry(registry_dir=tmp_path)

    llm_data = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "Компания А",
                "inn": "1111111111",
                "city": "Москва",
                "emails": []
            },
            {
                "organization_id": 2,
                "name": "Компания Б",
                "inn": "2222222222",
                "city": "Санкт-Петербург",
                "emails": []
            }
        ],
        "contacts": [
            {
                "contact_id": 1,
                "name": "Иван Иванов",
                "organization_id": 1,
                "email": "ivan@example.com",
                "phones": []
            },
            {
                "contact_id": 2,
                "name": "Пётр Петров",  # Разное имя
                "organization_id": 2,
                "email": "ivan@example.com",  # Тот же email
                "phones": []
            }
        ],
        "interactions": [],
        "business_context": "",
        "summary": {},
        "key_points": [],
        "commercial_offers": []
    }

    postprocessor = PostProcessor()
    postprocessor.gid_registry = registry
    result = postprocessor.process_llm_response(llm_data)

    # Проверяем, что есть контакты
    assert len(result["contacts"]) >= 1, "Должен быть хотя бы один контакт"

    # Проверяем, что GID разных организаций действительно разные
    org1_gid = result["organizations"][0]["gid"]
    org2_gid = result["organizations"][1]["gid"]
    assert org1_gid != org2_gid, "Организации должны иметь разные GID"

    # Проверяем, что контакты привязаны к правильным организациям
    contact_org_gids = set()
    for contact in result["contacts"]:
        org_id = contact["organization_id"]
        org_gid = None
        for org in result["organizations"]:
            if org["organization_id"] == org_id:
                org_gid = org["gid"]
                break
        assert org_gid is not None, f"Не найдена организация для контакта {contact['contact_id']}"
        contact_org_gids.add(org_gid)

    # Должно быть 2 разных organization_gid у контактов
    assert len(contact_org_gids) == 2, "Контакты должны быть привязаны к разным организациям"


def test_match_rule_priority(tmp_path: Path):
    """✅ Проверка: приоритет ключей (ИНН > домен > название+город)"""
    registry = GlobalIDRegistry(registry_dir=tmp_path)
    
    # Организация с ИНН
    org_with_inn = {
        "organization_id": 1,
        "name": "ООО Тест",
        "inn": "7708123456",
        "website": "test.ru",
        "city": "Москва",
        "emails": []
    }
    
    result = registry.resolve_organization(org_with_inn)
    assert result.match_rule == "INN", "Первичный ключ должен быть ИНН"
    
    # Организация без ИНН, но с доменом
    org_with_domain = {
        "organization_id": 2,
        "name": "ООО Тест2",
        "inn": None,
        "website": "test2.ru",
        "city": "Москва",
        "emails": []
    }
    
    result2 = registry.resolve_organization(org_with_domain)
    assert result2.match_rule == "DOMAIN", "Первичный ключ должен быть DOMAIN"
    
    # Организация без ИНН и домена
    org_with_name_city = {
        "organization_id": 3,
        "name": "ООО Тест3",
        "inn": None,
        "website": None,
        "city": "Москва",
        "emails": []
    }
    
    result3 = registry.resolve_organization(org_with_name_city)
    assert result3.match_rule == "NAME_CITY", "Первичный ключ должен быть NAME_CITY"


def test_metadata_structure(tmp_path: Path):
    """✅ Проверка: структура метаданных gid соответствует спецификации"""
    registry = GlobalIDRegistry(registry_dir=tmp_path)
    
    llm_data = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ООО Тест",
                "inn": "7708123456",
                "city": "Москва",
                "emails": []
            }
        ],
        "contacts": [
            {
                "contact_id": 1,
                "name": "Тест Тестов",
                "organization_id": 1,
                "email": "test@test.ru",
                "phones": []
            }
        ],
        "interactions": [],
        "business_context": "",
        "summary": {},
        "key_points": [],
        "commercial_offers": []
    }
    
    postprocessor = PostProcessor()
    postprocessor.gid_registry = registry
    result = postprocessor.process_llm_response(llm_data)
    
    gid_meta = result["postprocessing_metadata"]["gid"]
    
    # Проверка структуры assigned
    assert "assigned" in gid_meta
    assert isinstance(gid_meta["assigned"], list)
    
    for assignment in gid_meta["assigned"]:
        assert "entity" in assignment
        assert "gid" in assignment
        assert "match_rule" in assignment
        assert "key_tuple" in assignment
        assert "alias_added" in assignment
        assert "source" in assignment
    
    # Проверка структуры conflicts
    assert "conflicts" in gid_meta
    assert isinstance(gid_meta["conflicts"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])