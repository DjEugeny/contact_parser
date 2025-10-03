"""Модуль постобработки данных LLM

Обеспечивает полный цикл постобработки ответов LLM согласно мини-ТЗ:
- Дедупликация и объединение организаций
- Фильтрация ценных контактов
- Обогащение данных
- Нормализация телефонов и email

Author: Contact Parser Team
Created: 2025-09-13
"""

from .postprocessor import PostProcessor
from .organization_deduplicator import OrganizationDeduplicator
from .contact_filter import ContactFilter
from .data_enricher import DataEnricher
from .data_normalizer import DataNormalizer
from .advanced_contact_deduplicator import AdvancedContactDeduplicator
from .org_inn_resolver import OrganizationINNResolver

__all__ = [
    'PostProcessor',
    'OrganizationDeduplicator', 
    'ContactFilter',
    'DataEnricher',
    'DataNormalizer',
    'AdvancedContactDeduplicator',
    'OrganizationINNResolver'
]

__version__ = '1.0.0'