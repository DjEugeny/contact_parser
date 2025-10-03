#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Структуры данных для системы обогащения ИНН

Общие классы и структуры данных, используемые в системе обогащения ИНН.

Author: Contact Parser Team
Created: 2025-10-03
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class INNCandidate:
    """Кандидат для ИНН обогащения"""
    inn: str
    ogrn: Optional[str]
    name: str
    name_norm: str
    city: Optional[str]
    address: Optional[str]
    opf: Optional[str]  # Организационно-правовая форма
    score: float
    provider: str
    link: Optional[str] = None


@dataclass
class INNEnrichmentResult:
    """Результат обогащения ИНН"""
    decision: str  # auto_accept | needs_review | reject | override | skipped
    inn: Optional[str]
    confidence: float
    source: str
    method: str
    score: float
    candidates: list  # List[INNCandidate]
    checked_at: str
    auto_accept_threshold: float
    review_threshold: float


# Экспорт основных классов
__all__ = ['INNCandidate', 'INNEnrichmentResult']