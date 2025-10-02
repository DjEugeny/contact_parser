#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты нормализации порядка ФИО."""

import os
import sys

BASE_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from src.postprocessing.data_normalizer import DataNormalizer


def test_reorders_first_last_name():
    normalizer = DataNormalizer()
    contact = {
        'contact_id': 1,
        'organization_id': 1,
        'name': 'Елена Хаменкова',
        'phones': [],
        'email': None,
        'city': None,
        'address': None,
    }
    normalized = normalizer._normalize_single_contact(contact)
    assert normalized['name'] == 'Хаменкова Елена'
    assert normalized.get('name_original') == 'Елена Хаменкова'


def test_keeps_surname_first_form():
    normalizer = DataNormalizer()
    contact = {
        'contact_id': 2,
        'organization_id': 1,
        'name': 'Козлова Ольга',
        'phones': [],
        'email': None,
        'city': None,
        'address': None,
    }
    normalized = normalizer._normalize_single_contact(contact)
    assert normalized['name'] == 'Козлова Ольга'
