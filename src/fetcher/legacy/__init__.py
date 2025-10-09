"""
Legacy components for backward compatibility.

Модуль обеспечивает обратную совместимость с существующим кодом,
использующим старый интерфейс AdvancedEmailFetcherV2.
"""

from .legacy_email_fetcher import LegacyEmailFetcherV2

__all__ = [
    "LegacyEmailFetcherV2",
]