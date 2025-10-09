"""
Core components of the email fetcher module.

Основная логика обработки email:
- EmailFetcher - главный фасад
- ConnectionManager - управление соединениями
- EmailProcessor - обработка писем
"""

from .email_fetcher import EmailFetcher
from .connection_manager import ConnectionManager
from .email_processor import EmailProcessor

__all__ = [
    'EmailFetcher',
    'ConnectionManager',
    'EmailProcessor'
]