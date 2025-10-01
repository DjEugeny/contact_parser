#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты классификатора почтовых ящиков."""

import os
import sys
import unittest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
SYS_SRC = os.path.join(PROJECT_ROOT, 'src')
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if SYS_SRC not in sys.path:
    sys.path.append(SYS_SRC)

from src.postprocessing.email_classifier import MailboxType, classify_mailbox

CONFIG = {
    'shared_mailboxes_prefixes': [
        'info', 'sales', 'support', 'torgi', 'sklad'
    ],
    'department_prefixes': ['marketing'],
    'technical_prefixes': ['noreply'],
    'group_alias_suffixes': ['-team', '-all'],
}
CORP_DOMAINS = {'dna-technology.ru'}


class TestEmailClassifier(unittest.TestCase):
    def test_shared_mailbox(self):
        result = classify_mailbox('info@dna-technology.ru', None, CORP_DOMAINS, CONFIG)
        self.assertEqual(result, MailboxType.SHARED_ORG)

    def test_department_mailbox(self):
        result = classify_mailbox('marketing@dna-technology.ru', None, CORP_DOMAINS, CONFIG)
        self.assertEqual(result, MailboxType.DEPARTMENT)

    def test_group_alias_mailbox(self):
        result = classify_mailbox('sales-team@dna-technology.ru', None, CORP_DOMAINS, CONFIG)
        self.assertEqual(result, MailboxType.GROUP_ALIAS)

    def test_personal_internal(self):
        result = classify_mailbox('s.voronova@dna-technology.ru', 'Светлана Воронова', CORP_DOMAINS, CONFIG)
        self.assertEqual(result, MailboxType.PERSONAL_INTERNAL)

    def test_personal_external(self):
        result = classify_mailbox('ivan.petrov@gmail.com', 'Иван Петров', CORP_DOMAINS, CONFIG)
        self.assertEqual(result, MailboxType.PERSONAL_EXTERNAL)

    def test_unknown(self):
        result = classify_mailbox('service@external-provider.com', None, CORP_DOMAINS, CONFIG)
        self.assertEqual(result, MailboxType.UNKNOWN)


if __name__ == '__main__':
    unittest.main()
