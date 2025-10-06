#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для модуля ContactPhoneEnricher
Проверяет scoring систему, фильтрацию, защиту от дублирования и edge cases
"""

import pytest
from datetime import datetime
from src.postprocessing.contact_phone_enricher import ContactPhoneEnricher


class TestContactPhoneEnricherScoring:
    """Тесты scoring системы с различными комбинациями факторов"""

    def test_scoring_corporate_email(self):
        """Тест: корпоративный email дает +0.3"""
        enricher = ContactPhoneEnricher()
        
        contact = {
            "gid": "contact_1",
            "name": "Иван Петров",
            "emails": [{"email": "ivan@company.ru"}],
        }
        
        organization = {
            "gid": "org_1",
            "name": "Company LLC",
            "domain": "company.ru",
        }
        
        confidence = enricher._calculate_enrichment_confidence(contact, organization)
        assert confidence == 0.3, f"Expected 0.3, got {confidence}"

    def test_scoring_position(self):
        """Тест: наличие должности дает +0.2"""
        enricher = ContactPhoneEnricher()
        
        contact = {
            "gid": "contact_1",
            "name": "Иван Петров",
            "position": "Менеджер",
        }
        
        organization = {
            "gid": "org_1",
            "name": "Company LLC",
        }
        
        confidence = enricher._calculate_enrichment_confidence(contact, organization)
        assert confidence == 0.2, f"Expected 0.2, got {confidence}"

    def test_scoring_role_sender(self):
        """Тест: role_in_message = sender дает +0.2"""
        enricher = ContactPhoneEnricher()
        
        contact = {
            "gid": "contact_1",
            "name": "Иван Петров",
            "role_in_message": "sender",
        }
        
        organization = {
            "gid": "org_1",
            "name": "Company LLC",
        }
        
        confidence = enricher._calculate_enrichment_confidence(contact, organization)
        assert confidence == 0.2, f"Expected 0.2, got {confidence}"

    def test_scoring_city_match(self):
        """Тест: совпадение города дает +0.15"""
        enricher = ContactPhoneEnricher()
        
        contact = {
            "gid": "contact_1",
            "name": "Иван Петров",
            "city": "Москва",
        }
        
        organization = {
            "gid": "org_1",
            "name": "Company LLC",
            "city": "Москва",
        }
        
        confidence = enricher._calculate_enrichment_confidence(contact, organization)
        assert confidence == 0.15, f"Expected 0.15, got {confidence}"

    def test_scoring_high_value_score(self):
        """Тест: value_score >= 7 дает +0.15"""
        enricher = ContactPhoneEnricher()
        
        contact = {
            "gid": "contact_1",
            "name": "Иван Петров",
            "value_score": 8,
        }
        
        organization = {
            "gid": "org_1",
            "name": "Company LLC",
        }
        
        confidence = enricher._calculate_enrichment_confidence(contact, organization)
        assert confidence == 0.15, f"Expected 0.15, got {confidence}"

    def test_scoring_all_factors(self):
        """Тест: все факторы вместе дают максимальный score"""
        enricher = ContactPhoneEnricher()
        
        contact = {
            "gid": "contact_1",
            "name": "Иван Петров",
            "emails": [{"email": "ivan@company.ru"}],
            "position": "Менеджер",
            "role_in_message": "sender",
            "city": "Москва",
            "value_score": 8,
        }
        
        organization = {
            "gid": "org_1",
            "name": "Company LLC",
            "domain": "company.ru",
            "city": "Москва",
        }
        
        confidence = enricher._calculate_enrichment_confidence(contact, organization)
        expected = 0.3 + 0.2 + 0.2 + 0.15 + 0.15  # 1.0
        assert confidence == expected, f"Expected {expected}, got {confidence}"

    def test_scoring_no_factors(self):
        """Тест: отсутствие факторов дает 0.0"""
        enricher = ContactPhoneEnricher()
        
        contact = {
            "gid": "contact_1",
            "name": "Иван Петров",
        }
        
        organization = {
            "gid": "org_1",
            "name": "Company LLC",
        }
        
        confidence = enricher._calculate_enrichment_confidence(contact, organization)
        assert confidence == 0.0, f"Expected 0.0, got {confidence}"


class TestContactPhoneEnricherPhoneTypeFiltering:
    """Тесты фильтрации типов телефонов"""

    def test_filter_allows_main_type(self):
        """Тест: тип 'main' разрешен"""
        enricher = ContactPhoneEnricher()
        
        phones = [
            {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": "main"}
        ]
        
        filtered = enricher._filter_organization_phones(phones)
        assert len(filtered) == 1
        assert filtered[0]["type"] == "main"

    def test_filter_allows_office_type(self):
        """Тест: тип 'office' разрешен"""
        enricher = ContactPhoneEnricher()
        
        phones = [
            {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": "office"}
        ]
        
        filtered = enricher._filter_organization_phones(phones)
        assert len(filtered) == 1
        assert filtered[0]["type"] == "office"

    def test_filter_allows_fax_type(self):
        """Тест: тип 'fax' разрешен"""
        enricher = ContactPhoneEnricher()
        
        phones = [
            {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": "fax"}
        ]
        
        filtered = enricher._filter_organization_phones(phones)
        assert len(filtered) == 1
        assert filtered[0]["type"] == "fax"

    def test_filter_blocks_mobile_type(self):
        """Тест: тип 'mobile' блокируется"""
        enricher = ContactPhoneEnricher()
        
        phones = [
            {"number": "+7 916 123-45-67", "normalized": "+79161234567", "type": "mobile"}
        ]
        
        filtered = enricher._filter_organization_phones(phones)
        assert len(filtered) == 0

    def test_filter_null_type_treated_as_main(self):
        """Тест: null тип обрабатывается как 'main' с пониженным confidence"""
        enricher = ContactPhoneEnricher()
        
        phones = [
            {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": None}
        ]
        
        filtered = enricher._filter_organization_phones(phones)
        assert len(filtered) == 1
        assert filtered[0]["type"] == "main"
        assert filtered[0]["confidence_adjustment"] == -0.1
        assert filtered[0]["_original_type"] is None

    def test_filter_mixed_types(self):
        """Тест: фильтрация смешанных типов"""
        enricher = ContactPhoneEnricher()
        
        phones = [
            {"number": "+7 495 111-11-11", "normalized": "+74951111111", "type": "main"},
            {"number": "+7 916 222-22-22", "normalized": "+79162222222", "type": "mobile"},
            {"number": "+7 495 333-33-33", "normalized": "+74953333333", "type": "office"},
            {"number": "+7 495 444-44-44", "normalized": "+74954444444", "type": None},
        ]
        
        filtered = enricher._filter_organization_phones(phones)
        assert len(filtered) == 3  # main, office, null (treated as main)
        
        types = [p["type"] for p in filtered]
        assert "main" in types
        assert "office" in types
        assert "mobile" not in types


class TestContactPhoneEnricherDuplicateProtection:
    """Тесты защиты от дублирования"""

    def test_duplicate_detection_by_normalized(self):
        """Тест: дубликат определяется по normalized полю"""
        enricher = ContactPhoneEnricher()
        
        contact_phones = [
            {"number": "+7 (495) 123-45-67", "normalized": "+74951234567", "source": "llm"}
        ]
        
        new_phone = {
            "number": "+7 495 123-45-67", "normalized": "+74951234567", "source": "org_enrichment"
        }
        
        result = enricher._check_phone_duplicate(contact_phones, new_phone)
        assert result["is_duplicate"] is True
        assert result["reason"] == "llm_source_priority"

    def test_llm_source_has_priority(self):
        """Тест: LLM источник имеет приоритет над org_enrichment"""
        enricher = ContactPhoneEnricher()
        
        contact_phones = [
            {"number": "+7 495 123-45-67", "normalized": "+74951234567", "source": "llm"}
        ]
        
        new_phone = {
            "number": "+7 495 123-45-67", "normalized": "+74951234567", "source": "org_enrichment"
        }
        
        result = enricher._check_phone_duplicate(contact_phones, new_phone)
        assert result["is_duplicate"] is True
        assert result["reason"] == "llm_source_priority"

    def test_no_duplicate_different_numbers(self):
        """Тест: разные номера не считаются дубликатами"""
        enricher = ContactPhoneEnricher()
        
        contact_phones = [
            {"number": "+7 495 111-11-11", "normalized": "+74951111111", "source": "llm"}
        ]
        
        new_phone = {
            "number": "+7 495 222-22-22", "normalized": "+74952222222", "source": "org_enrichment"
        }
        
        result = enricher._check_phone_duplicate(contact_phones, new_phone)
        assert result["is_duplicate"] is False

    def test_duplicate_without_normalized_field(self):
        """Тест: телефон без normalized поля считается дубликатом"""
        enricher = ContactPhoneEnricher()
        
        contact_phones = []
        new_phone = {"number": "+7 495 123-45-67"}
        
        result = enricher._check_phone_duplicate(contact_phones, new_phone)
        assert result["is_duplicate"] is True
        assert result["reason"] == "no_normalized_field"


class TestContactPhoneEnricherEdgeCases:
    """Тесты обработки edge cases"""

    def test_contact_without_organization_id(self):
        """Тест: контакт без organization_id пропускается"""
        enricher = ContactPhoneEnricher()
        
        contacts = [
            {"gid": "contact_1", "name": "Иван Петров"}
        ]
        
        organizations = []
        
        result = enricher.enrich_contacts_phones(contacts, organizations)
        
        assert result["statistics"]["contacts_processed"] == 1
        assert result["statistics"]["contacts_enriched"] == 0
        assert result["statistics"]["phones_skipped_by_reason"]["no_organization"] == 1

    def test_organization_not_found(self):
        """Тест: организация не найдена в списке"""
        enricher = ContactPhoneEnricher()
        
        contacts = [
            {"gid": "contact_1", "name": "Иван Петров", "organization_id": "org_999"}
        ]
        
        organizations = [
            {"gid": "org_1", "name": "Company LLC"}
        ]
        
        result = enricher.enrich_contacts_phones(contacts, organizations)
        
        assert result["statistics"]["contacts_processed"] == 1
        assert result["statistics"]["contacts_enriched"] == 0
        assert result["statistics"]["phones_skipped_by_reason"]["no_organization"] == 1

    def test_organization_without_phones(self):
        """Тест: организация без телефонов"""
        enricher = ContactPhoneEnricher()
        
        contacts = [
            {"gid": "contact_1", "name": "Иван Петров", "organization_id": "org_1"}
        ]
        
        organizations = [
            {"gid": "org_1", "name": "Company LLC", "phones": []}
        ]
        
        result = enricher.enrich_contacts_phones(contacts, organizations)
        
        assert result["statistics"]["contacts_processed"] == 1
        assert result["statistics"]["contacts_enriched"] == 0
        assert result["statistics"]["phones_skipped_by_reason"]["no_org_phones"] == 1

    def test_contact_phones_null_initialized(self):
        """Тест: phones = null инициализируется как пустой массив"""
        enricher = ContactPhoneEnricher()
        
        contacts = [
            {
                "gid": "contact_1",
                "name": "Иван Петров",
                "organization_id": "org_1",
                "emails": [{"email": "ivan@company.ru"}],
                "position": "Менеджер",  # Добавляем position для прохождения порога confidence
                "phones": None,
            }
        ]
        
        organizations = [
            {
                "gid": "org_1",
                "name": "Company LLC",
                "domain": "company.ru",
                "phones": [
                    {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": "main"}
                ],
            }
        ]
        
        result = enricher.enrich_contacts_phones(contacts, organizations)
        
        assert contacts[0]["phones"] is not None
        assert isinstance(contacts[0]["phones"], list)
        assert len(contacts[0]["phones"]) > 0

    def test_exception_handling_continues_processing(self):
        """Тест: исключение при обработке одного контакта не останавливает обработку других"""
        enricher = ContactPhoneEnricher()
        
        contacts = [
            {"gid": "contact_1", "name": "Иван Петров", "organization_id": "org_1"},
            {"gid": "contact_2", "name": "Петр Иванов", "organization_id": "org_2", "position": "Директор"},
        ]
        
        # Создаем организацию с некорректными данными для первого контакта
        organizations = [
            {"gid": "org_1", "name": "Bad Org", "phones": "not_a_list"},  # Некорректный формат
            {
                "gid": "org_2",
                "name": "Good Org",
                "phones": [
                    {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": "main"}
                ],
            },
        ]
        
        result = enricher.enrich_contacts_phones(contacts, organizations)
        
        # Проверяем, что обработка продолжилась
        assert result["statistics"]["contacts_processed"] == 2


class TestContactPhoneEnricherIntegration:
    """Тесты интеграции с PostProcessor"""

    def test_enrichment_metadata_structure(self):
        """Тест: структура метаданных обогащения"""
        enricher = ContactPhoneEnricher()
        
        contacts = [
            {
                "gid": "contact_1",
                "name": "Иван Петров",
                "organization_id": "org_1",
                "emails": [{"email": "ivan@company.ru"}],
                "phones": [],
            }
        ]
        
        organizations = [
            {
                "gid": "org_1",
                "name": "Company LLC",
                "domain": "company.ru",
                "phones": [
                    {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": "main"}
                ],
            }
        ]
        
        result = enricher.enrich_contacts_phones(contacts, organizations)
        
        # Проверяем структуру результата
        assert "contacts" in result
        assert "statistics" in result
        assert "timestamp" in result
        assert "config" in result
        
        # Проверяем метаданные контакта
        contact_meta = result["contacts"][0]
        assert "contact_gid" in contact_meta
        assert "phones_added" in contact_meta
        assert "phones_skipped" in contact_meta
        assert "confidence_scores" in contact_meta
        assert "decision" in contact_meta

    def test_enriched_phone_metadata(self):
        """Тест: метаданные добавленного телефона"""
        enricher = ContactPhoneEnricher()
        
        contacts = [
            {
                "gid": "contact_1",
                "name": "Иван Петров",
                "organization_id": "org_1",
                "emails": [{"email": "ivan@company.ru"}],
                "position": "Менеджер",  # Добавляем для прохождения порога confidence
                "phones": [],
            }
        ]
        
        organizations = [
            {
                "gid": "org_1",
                "name": "Company LLC",
                "domain": "company.ru",
                "phones": [
                    {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": "main"}
                ],
            }
        ]
        
        enricher.enrich_contacts_phones(contacts, organizations)
        
        # Проверяем метаданные добавленного телефона
        added_phone = contacts[0]["phones"][0]
        assert added_phone["source"] == "org_enrichment"
        assert added_phone["org_gid"] == "org_1"
        assert "confidence" in added_phone
        assert "enriched_at" in added_phone

    def test_statistics_tracking(self):
        """Тест: отслеживание статистики"""
        enricher = ContactPhoneEnricher()
        
        contacts = [
            {
                "gid": "contact_1",
                "name": "Иван Петров",
                "organization_id": "org_1",
                "emails": [{"email": "ivan@company.ru"}],
                "position": "Менеджер",  # Добавляем для прохождения порога confidence
                "phones": [],
            },
            {
                "gid": "contact_2",
                "name": "Петр Иванов",
                "organization_id": "org_2",
            },
        ]
        
        organizations = [
            {
                "gid": "org_1",
                "name": "Company LLC",
                "domain": "company.ru",
                "phones": [
                    {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": "main"}
                ],
            },
            {"gid": "org_2", "name": "No Phones LLC", "phones": []},
        ]
        
        result = enricher.enrich_contacts_phones(contacts, organizations)
        
        stats = result["statistics"]
        assert stats["contacts_processed"] == 2
        assert stats["contacts_enriched"] == 1
        assert stats["phones_added_total"] == 1
        assert stats["phones_skipped_by_reason"]["no_org_phones"] == 1

    def test_enrichment_modes(self):
        """Тест: различные режимы обогащения"""
        # Conservative mode
        enricher_conservative = ContactPhoneEnricher({"enrichment_mode": "conservative"})
        assert enricher_conservative.min_confidence_threshold >= 0.75
        
        # Balanced mode
        enricher_balanced = ContactPhoneEnricher({"enrichment_mode": "balanced"})
        assert enricher_balanced.min_confidence_threshold == 0.5
        
        # Aggressive mode
        enricher_aggressive = ContactPhoneEnricher({"enrichment_mode": "aggressive"})
        assert enricher_aggressive.min_confidence_threshold <= 0.4

    def test_disabled_enricher(self):
        """Тест: отключенный enricher не обогащает контакты"""
        enricher = ContactPhoneEnricher({"enabled": False})
        
        contacts = [
            {
                "gid": "contact_1",
                "name": "Иван Петров",
                "organization_id": "org_1",
                "emails": [{"email": "ivan@company.ru"}],
                "phones": [],
            }
        ]
        
        organizations = [
            {
                "gid": "org_1",
                "name": "Company LLC",
                "domain": "company.ru",
                "phones": [
                    {"number": "+7 495 123-45-67", "normalized": "+74951234567", "type": "main"}
                ],
            }
        ]
        
        result = enricher.enrich_contacts_phones(contacts, organizations)
        
        # Когда enricher отключен, возвращается "stats" вместо "statistics"
        assert result["stats"]["contacts_processed"] == 0
        assert result["stats"]["contacts_enriched"] == 0
        assert len(contacts[0]["phones"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
