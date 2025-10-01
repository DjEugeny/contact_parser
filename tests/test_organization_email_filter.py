#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты filtрации email в OrganizationDeduplicator."""

import os
import sys
import unittest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
SYS_SRC = os.path.join(PROJECT_ROOT, 'src')
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if SYS_SRC not in sys.path:
    sys.path.append(SYS_SRC)

from src.postprocessing.organization_deduplicator import OrganizationDeduplicator
from src.postprocessing.email_classifier import MailboxType

CFG = {
    'shared_mailboxes_prefixes': ['info'],
    'department_prefixes': ['sales'],
    'technical_prefixes': ['noreply'],
    'group_alias_suffixes': ['-team'],
}


class TestOrganizationEmailFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.deduplicator = OrganizationDeduplicator()
        self.deduplicator.configure_email_classifier(CFG, {'dna-technology.ru'}, {
            MailboxType.SHARED_ORG,
            MailboxType.DEPARTMENT,
            MailboxType.TECHNICAL,
            MailboxType.GROUP_ALIAS,
        })

    def test_personal_emails_removed(self):
        organizations = [
            {
                'organization_id': 1,
                'name': 'ООО "ДНК-Технология"',
                'emails': [
                    'info@dna-technology.ru',
                    's.voronova@dna-technology.ru',
                    'noreply@dna-technology.ru',
                ]
            }
        ]
        mapping = self.deduplicator.process_organizations(organizations)
        self.assertEqual(mapping[1], 1)
        stored = self.deduplicator.global_organizations[1]
        self.assertEqual(sorted(stored['emails']), ['info@dna-technology.ru', 'noreply@dna-technology.ru'])


if __name__ == '__main__':
    unittest.main()
