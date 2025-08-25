#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Прокси-модуль для совместимости: re-export классов/констант из advanced_email_fetcher.py
- Нужен для тестов и вспомогательных скриптов, ожидающих модуль `advanced_email_fetcher_fixed`
"""

# Не меняем поведение: просто реэкспортируем актуальные сущности
from .advanced_email_fetcher import AdvancedEmailFetcherV2, EXCLUDED_EXTENSIONS  # noqa: F401

__all__ = [
    "AdvancedEmailFetcherV2",
    "EXCLUDED_EXTENSIONS",
]