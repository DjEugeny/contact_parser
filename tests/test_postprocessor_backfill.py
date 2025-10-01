#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Юнит-тесты мягкого backfill города/адреса контактов."""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
SYS_SRC = os.path.join(PROJECT_ROOT, 'src')

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if SYS_SRC not in sys.path:
    sys.path.append(SYS_SRC)

from src.postprocessing.postprocessor import PostProcessor


class TestPostProcessorBackfill(unittest.TestCase):
    """Проверка сценариев A–E из спецификации contact-backfill."""

    def setUp(self) -> None:
        self.processor = PostProcessor()
        # Страхуемся от внешних флагов окружения
        self.processor.backfill_city_from_org = True
        self.processor.backfill_address_from_org = False

    def test_backfill_city_from_org(self) -> None:
        contacts = [
            {"contact_id": 1, "organization_id": 10, "city": None, "address": None},
        ]
        organizations = {10: {"city": "Москва", "address": "ул. HQ"}}

        updated, provenance = self.processor._backfill_contact_city_address(contacts, organizations)

        self.assertEqual(updated[0]['city'], "Москва")
        self.assertIsNone(updated[0].get('address'))
        self.assertEqual(provenance[1]['city_source'], 'org_fallback')
        self.assertNotIn('address_source', provenance[1])

    def test_backfill_preserves_existing_city(self) -> None:
        contacts = [
            {"contact_id": 2, "organization_id": 11, "city": "Новокузнецк", "address": None},
        ]
        organizations = {11: {"city": "Москва", "address": "ул. HQ"}}

        updated, provenance = self.processor._backfill_contact_city_address(contacts, organizations)

        self.assertEqual(updated[0]['city'], "Новокузнецк")
        self.assertFalse(provenance)

    def test_address_not_backfilled_by_default(self) -> None:
        contacts = [
            {"contact_id": 3, "organization_id": 12, "city": None, "address": None},
        ]
        organizations = {12: {"city": "Новосибирск", "address": "ул. Баумана"}}

        updated, provenance = self.processor._backfill_contact_city_address(contacts, organizations)

        self.assertEqual(updated[0]['city'], "Новосибирск")
        self.assertIsNone(updated[0]['address'])
        self.assertIn(3, provenance)
        self.assertNotIn('address_source', provenance[3])

    def test_address_backfill_when_enabled(self) -> None:
        self.processor.backfill_address_from_org = True
        contacts = [
            {"contact_id": 4, "organization_id": 13, "city": None, "address": None},
        ]
        organizations = {13: {"city": "Казань", "address": "ул. Баумана, 10"}}

        updated, provenance = self.processor._backfill_contact_city_address(contacts, organizations)

        self.assertEqual(updated[0]['address'], "ул. Баумана, 10")
        self.assertEqual(provenance[4]['address_source'], 'org_fallback')

    def test_provenance_is_added_to_metadata(self) -> None:
        final_contacts = [
            {
                "contact_id": 5,
                "organization_id": 14,
                "name": "Тест",
                "city": "Пермь",
                "address": None,
            }
        ]
        final_organizations = {
            14: {"organization_id": 14, "name": "Компания", "city": "Пермь", "address": "HQ"}
        }
        provenance = {5: {"city_source": "org_fallback"}}

        result = self.processor._build_final_result(
            original_result={
                "organizations": [],
                "contacts": [],
                "interactions": [],
                "summary": {},
                "key_points": [],
                "business_context": "",
                "commercial_offers": [],
            },
            final_contacts=final_contacts,
            final_organizations=final_organizations,
            interactions=[],
            summary={"topic": None, "product_interest": None, "communication_stage": None, "request_type": None},
            key_points=[],
            business_context="",
            commercial_offers=[],
            provenance=provenance,
        )

        provenance_block = result['postprocessing_metadata']['provenance']
        self.assertEqual(provenance_block['contacts'][5]['city_source'], 'org_fallback')

    def test_cleanup_organization_emails(self) -> None:
        orgs = {
            1: {
                'emails': [
                    'info@dna-technology.ru',
                    's.voronova@dna-technology.ru',
                    'noreply@dna-technology.ru',
                ]
            }
        }
        contacts = [
            {
                'contact_id': 10,
                'organization_id': 1,
                'email': 's.voronova@dna-technology.ru',
            }
        ]

        log = self.processor._cleanup_organization_emails(orgs, contacts)

        self.assertEqual(orgs[1]['emails'], ['info@dna-technology.ru', 'noreply@dna-technology.ru'])
        self.assertIn(1, log)
        self.assertIn('s.voronova@dna-technology.ru', log[1]['removed'])
        self.assertEqual(log[1]['removed_types']['s.voronova@dna-technology.ru'], 'personal_internal')


if __name__ == '__main__':
    unittest.main()
