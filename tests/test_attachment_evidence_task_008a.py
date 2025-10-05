#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для TASK-008A: Attachment Evidence → Org City/Address
Проверка обогащения организаций данными о местоположении из вложений

Author: Contact Parser Team
Created: 2025-09-29
"""

import unittest
import sys
from pathlib import Path

# Добавляем путь к src для импорта
sys.path.append(str(Path(__file__).parent.parent / "src"))

from postprocessing.attachment_evidence_extractor import (
    AttachmentEvidenceExtractor, 
    AttachmentEvidenceConfig,
    LocationEvidence
)
from postprocessing.org_location_enrichment import (
    OrgLocationEnrichment,
    OrgLocationEnrichmentConfig
)
from postprocessing.postprocessor import PostProcessor


class TestAttachmentEvidenceExtractor(unittest.TestCase):
    """Тесты для AttachmentEvidenceExtractor"""
    
    def setUp(self):
        """Настройка тестов"""
        self.extractor = AttachmentEvidenceExtractor()
    
    def test_should_process_attachment_by_filename(self):
        """Тест классификации вложений по имени файла"""
        test_cases = [
            ("Коммерческое_предложение_МИЛЛАБ.txt", True),
            ("КП_для_клиента.pdf", True),
            ("Реквизиты_организации.doc", True),
            ("Счет_на_оплату.pdf", True),
            ("Commercial_offer.txt", True),
            ("Invoice_123.pdf", True),
            ("обычный_файл.txt", False),
            ("фото.jpg", False),
        ]
        
        for filename, expected in test_cases:
            with self.subTest(filename=filename):
                attachment = {'filename': filename, 'text_content': ''}
                result = self.extractor._should_process_attachment(attachment)
                self.assertEqual(result, expected, 
                    f"Файл {filename} должен {'обрабатываться' if expected else 'игнорироваться'}")
    
    def test_should_process_attachment_by_content(self):
        """Тест классификации вложений по содержимому"""
        test_cases = [
            ("ИНН: 7728123456 ОГРН: 1027739123456", True),
            ("ООО Рога и Копыта", True),
            ("Коммерческое предложение на поставку", True),
            ("Юридический адрес организации", True),
            ("Обычный текст без ключевых слов", False),
        ]
        
        for content, expected in test_cases:
            with self.subTest(content=content[:30]):
                attachment = {'filename': 'test.txt', 'text_content': content}
                result = self.extractor._should_process_attachment(attachment)
                self.assertEqual(result, expected)
    
    def test_find_organizations_in_text(self):
        """Тест поиска организаций в тексте"""
        text = """
        ООО "МИЛЛАБ"
        ИНН: 7728123456
        ОГРН: 1027739123456
        
        ЗАО МЕДИЦИНСКИЙ ЦЕНТР
        Клиника здоровья
        """
        
        organizations = self.extractor._find_organizations_in_text(text)
        
        self.assertGreater(len(organizations), 0)
        
        # Проверяем что найдена МИЛЛАБ
        org_names = [org['matched_name'] for org in organizations]
        self.assertTrue(any('МИЛЛАБ' in name for name in org_names))
    
    def test_find_location_near_organization(self):
        """Тест поиска локации рядом с организацией"""
        text = """
        ООО "МИЛЛАБ"
        Юридический адрес: 117105, г. Москва, Варшавское шоссе, д. 17
        ИНН: 7728123456
        Телефон: +7(495) 123-45-67
        """
        
        location_info = self.extractor._find_location_near_organization(
            text, 'ООО "МИЛЛАБ"', 10
        )
        
        self.assertIsNotNone(location_info['city'])
        self.assertIn('Москва', location_info['city'])
        self.assertIsNotNone(location_info['address'])
        self.assertIn('117105', location_info['address'])
    
    def test_normalize_organization_name(self):
        """Тест нормализации названий организаций"""
        test_cases = [
            ('ООО "МИЛЛАБ"', 'миллаб'),
            ('ЗАО Медицинский центр', 'медицинский центр'),
            ('АО «Рога и Копыта»', 'рога и копыта'),
            ('ИП Иванов И.И.', 'иванов и.и.'),
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.extractor._normalize_organization_name(input_name)
                self.assertEqual(result, expected)
    
    def test_extract_millab_example(self):
        """Тест извлечения на примере МИЛЛАБ"""
        email_data = {
            'attachments': [{
                'filename': 'Ком.пред.14.03.2025_для_Москва_Компания_МИЛЛАБ_для_Абакан_ЦГиЭ.txt',
                'text_content': '''
                ООО "МИЛЛАБ"
                Юридический адрес: 117105, г. Москва, Варшавское шоссе, д. 17
                ИНН: 7728123456
                ОГРН: 1027739123456
                
                Коммерческое предложение
                Поставка медицинского оборудования
                ''',
                'mime': 'text/plain'
            }]
        }
        
        evidence_list = self.extractor.extract(email_data)
        
        self.assertGreater(len(evidence_list), 0)
        
        # Находим доказательство для МИЛЛАБ
        millab_evidence = None
        for evidence in evidence_list:
            if 'миллаб' in evidence.org_name_norm.lower():
                millab_evidence = evidence
                break
        
        self.assertIsNotNone(millab_evidence, "Не найдено доказательство для МИЛЛАБ")
        self.assertEqual(millab_evidence.city, "Москва")
        self.assertIn("117105", millab_evidence.address)
        self.assertGreater(millab_evidence.confidence, 0.5)


class TestOrgLocationEnrichment(unittest.TestCase):
    """Тесты для OrgLocationEnrichment"""
    
    def setUp(self):
        """Настройка тестов"""
        self.enrichment = OrgLocationEnrichment()
    
    def test_find_matching_evidence(self):
        """Тест поиска подходящих доказательств"""
        org_data = {'name': 'ООО "МИЛЛАБ"'}
        evidence_list = [
            LocationEvidence(
                org_name_norm='миллаб',
                matched_name='ООО "МИЛЛАБ"',
                city='Москва',
                confidence=0.9
            ),
            LocationEvidence(
                org_name_norm='другая компания',
                matched_name='ООО "Другая"',
                city='Санкт-Петербург',
                confidence=0.8
            )
        ]
        
        matching = self.enrichment._find_matching_evidence(org_data, evidence_list)
        
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].org_name_norm, 'миллаб')
    
    def test_apply_enrichment_empty_fields(self):
        """Тест применения обогащения к пустым полям"""
        org_data = {
            'name': 'ООО "МИЛЛАБ"',
            'city': None,
            'address': None
        }
        
        evidence = LocationEvidence(
            org_name_norm='миллаб',
            matched_name='ООО "МИЛЛАБ"',
            city='Москва',
            address='117105, г. Москва, Варшавское шоссе, д. 17',
            confidence=0.9,
            source={'type': 'attachment', 'filename': 'КП.txt'}
        )
        
        result = self.enrichment._apply_enrichment(org_data, [evidence])
        
        enriched_org = result['organization']
        metadata = result['metadata']
        
        self.assertEqual(enriched_org['city'], 'Москва')
        self.assertIn('117105', enriched_org['address'])
        self.assertTrue(metadata.applied)
        self.assertEqual(metadata.confidence, 0.9)
    
    def test_apply_enrichment_preserve_existing(self):
        """Тест сохранения существующих данных"""
        org_data = {
            'name': 'ООО "МИЛЛАБ"',
            'city': 'Существующий город',
            'address': 'Существующий адрес'
        }
        
        evidence = LocationEvidence(
            org_name_norm='миллаб',
            matched_name='ООО "МИЛЛАБ"',
            city='Москва',
            address='117105, г. Москва, Варшавское шоссе, д. 17',
            confidence=0.9
        )
        
        result = self.enrichment._apply_enrichment(org_data, [evidence])
        
        enriched_org = result['organization']
        metadata = result['metadata']
        
        # Существующие данные должны сохраниться
        self.assertEqual(enriched_org['city'], 'Существующий город')
        self.assertEqual(enriched_org['address'], 'Существующий адрес')
        self.assertFalse(metadata.applied)
    
    def test_enrich_organizations_millab_example(self):
        """Тест обогащения на примере МИЛЛАБ"""
        organizations = {
            1: {
                'name': 'ООО "МИЛЛАБ"',
                'city': None,
                'address': None
            }
        }
        
        evidence_list = [
            LocationEvidence(
                org_name_norm='миллаб',
                matched_name='ООО "МИЛЛАБ"',
                city='Москва',
                address='117105, г. Москва, Варшавское шоссе, д. 17',
                confidence=0.9,
                source={
                    'type': 'attachment',
                    'filename': 'КП_МИЛЛАБ.txt',
                    'snippet': 'Юридический адрес: 117105, г. Москва...'
                }
            )
        ]
        
        metadata = {}
        enriched_orgs = self.enrichment.enrich_organizations(
            organizations, evidence_list, metadata
        )
        
        # Проверяем обогащение
        millab_org = enriched_orgs[1]
        self.assertEqual(millab_org['city'], 'Москва')
        self.assertIn('117105', millab_org['address'])
        
        # Проверяем метаданные
        self.assertIn('location_evidence', metadata)
        self.assertIn(1, metadata['location_evidence'])
        
        evidence_meta = metadata['location_evidence'][1]
        self.assertTrue(evidence_meta.applied)
        self.assertEqual(evidence_meta.city, 'Москва')
        self.assertEqual(evidence_meta.confidence, 0.9)


class TestIntegrationWithPostProcessor(unittest.TestCase):
    """Интеграционные тесты с PostProcessor"""
    
    def setUp(self):
        """Настройка тестов"""
        self.postprocessor = PostProcessor()
    
    def test_postprocessor_has_attachment_components(self):
        """Тест что PostProcessor имеет компоненты обогащения вложений"""
        self.assertIsNotNone(self.postprocessor.attachment_evidence_extractor)
        self.assertIsNotNone(self.postprocessor.org_location_enrichment)
    
    def test_full_pipeline_millab_example(self):
        """Тест полного пайплайна на примере МИЛЛАБ"""
        # Тестовые данные письма 016
        llm_result = {
            'organizations': [{
                'organization_id': 1,
                'name': 'ООО "МИЛЛАБ"',
                'city': None,
                'address': None,
                'inn': '7728123456'
            }],
            'contacts': [{
                'contact_id': 1,
                'name': 'Воронова С.С.',
                'organization_id': 1,
                'email': 'voronova@millab.ru',
                'city': None,
                'address': None
            }],
            'interactions': [],
            'summary': {'topic': 'Коммерческое предложение'},
            'key_points': ['Запрос КП'],
            'commercial_offers': []
        }
        
        email_data = {
            'attachments': [{
                'filename': 'Ком.пред.14.03.2025_для_Москва_Компания_МИЛЛАБ_для_Абакан_ЦГиЭ.txt',
                'text_content': '''
                ООО "МИЛЛАБ"
                Юридический адрес: 117105, г. Москва, Варшавское шоссе, д. 17
                ИНН: 7728123456
                ОГРН: 1027739123456
                
                Коммерческое предложение
                Поставка медицинского оборудования для Абакан ЦГиЭ
                ''',
                'mime': 'text/plain'
            }]
        }
        
        # Обрабатываем через PostProcessor
        result = self.postprocessor.process_llm_response(llm_result, email_data)
        
        # Проверяем что организация МИЛЛАБ получила город Москва
        organizations = result.get('organizations', [])
        self.assertGreater(len(organizations), 0)
        
        millab_org = None
        for org in organizations:
            if 'МИЛЛАБ' in org.get('name', ''):
                millab_org = org
                break
        
        self.assertIsNotNone(millab_org, "Организация МИЛЛАБ не найдена")
        self.assertEqual(millab_org.get('city'), 'Москва', 
            "Организация МИЛЛАБ должна получить город Москва из вложения")
        
        # Проверяем метаданные обогащения
        metadata = result.get('postprocessing_metadata', {})
        enrichment_meta = metadata.get('enrichment', {})
        location_meta = enrichment_meta.get('org_location_from_attachments', {})
        
        self.assertGreater(location_meta.get('evidence_count', 0), 0)
        self.assertGreater(location_meta.get('organizations_enriched', 0), 0)
        self.assertGreater(location_meta.get('cities_added', 0), 0)


if __name__ == '__main__':
    # Запуск тестов
    unittest.main(verbosity=2)