#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты для EnhancedContactEnricher"""

import logging
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent))

from src.core.contact_enricher import (  # type: ignore pylint:disable=import-error
    EnhancedContactEnricher,
    EnrichmentErrorHandler,
)


class DummyINNValidator:
    """🧪 Тестовый валидатор ИНН"""

    def validate_inn(self, inn: str):  # pylint:disable=unused-argument
        return {'valid': True, 'type': 'organization', 'inn': inn}


class DummyWebsiteExtractor:
    """🌐 Тестовый извлекатель сайтов"""

    def extract_from_email_body(self, text):  # pylint:disable=unused-argument
        return []

    def extract_from_email_domain(self, email: str):
        domain = email.split('@')[1].lower()
        return {
            'url': f'https://{domain}',
            'domain': domain,
            'confidence': 0.7,
            'source': 'email_domain',
            'method': 'domain_extraction',
        }

    def validate_website(self, url: str):  # pylint:disable=unused-argument
        return True


class RaisingWebsiteExtractor(DummyWebsiteExtractor):
    """🔥 Извлекатель сайтов, вызывающий ошибку"""

    def extract_from_email_body(self, text):  # pylint:disable=unused-argument
        raise RuntimeError('boom')

    def extract_from_email_domain(self, email):  # pylint:disable=unused-argument
        raise RuntimeError('boom-domain')


@pytest.fixture
def enricher():
    """🔧 Создаёт экземпляр расширенного обогатителя"""

    return EnhancedContactEnricher(
        inn_validator=DummyINNValidator(),
        website_extractor=DummyWebsiteExtractor(),
    )


def test_centerld_domain_extraction(enricher):
    """🔗 Проверяет извлечение сайта из домена sklad@centerld.ru"""

    contacts = [{
        'name': 'Test User',
        'email': 'sklad@centerld.ru',
    }]

    enriched = enricher.enrich_contacts(contacts)

    assert len(enriched) == 1
    contact = enriched[0]

    assert 'centerld.ru' in contact.get('website', '')
    assert contact.get('website_source') == 'email_domain'
    stats = enricher.get_enrichment_stats()
    assert stats['websites_extracted'] == 1


def test_diagnostic_info_contains_stats(enricher):
    """📊 Проверяет, что диагностика возвращает статистику"""

    contacts = [{
        'name': 'Мария Гоголева',
        'email': 'm.gogoleva@dna-technology.ru',
        'inn': '1901066506',
        'inn_validated': True,
        'organization_type': 'russian_company',
    }]

    enricher.enrich_contacts(contacts)
    diagnostics = enricher.get_diagnostic_info()

    assert diagnostics['contacts_processed'] >= 1
    assert 'diagnostic_timestamp' in diagnostics
    assert diagnostics['last_run']['contacts_returned'] == 1


def test_error_handler_returns_original_contact():
    """🛡️ Проверяет graceful degradation при ошибке"""

    handler = EnrichmentErrorHandler(logging.getLogger(__name__))
    enricher = EnhancedContactEnricher(
        inn_validator=DummyINNValidator(),
        website_extractor=RaisingWebsiteExtractor(),
        error_handler=handler,
    )

    contacts = [{
        'name': 'Проблемный Контакт',
        'email': 'test@example.com',
    }]

    enriched = enricher.enrich_contacts(contacts)

    assert enriched == contacts
    stats = enricher.get_enrichment_stats()
    assert stats['errors'] == 1
    assert 'RuntimeError' in stats['error_types']
