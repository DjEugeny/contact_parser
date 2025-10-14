"""
Email Fetcher - Новая модульная архитектура.

Модуль для fetching электронных писем с исправленным маппингом вложений.
Архитектура разделена на компоненты для лучшей поддерживаемости.
"""

try:
    from .core.email_fetcher import EmailFetcher
    from .core.connection_manager import ConnectionManager
    from .core.email_processor import EmailProcessor
    from .filters.email_filters import EmailFilters
    from .parsers.email_parser import EmailParser
    from .storage.email_storage import EmailStorage
    from .attachments.attachment_registry import AttachmentRegistry
    from .legacy.legacy_email_fetcher import LegacyEmailFetcherV2
except ImportError:
    # Fallback для прямого запуска
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.fetcher.core.email_fetcher import EmailFetcher
    from src.fetcher.core.connection_manager import ConnectionManager
    from src.fetcher.core.email_processor import EmailProcessor
    from src.fetcher.filters.email_filters import EmailFilters
    from src.fetcher.parsers.email_parser import EmailParser
    from src.fetcher.storage.email_storage import EmailStorage
    from src.fetcher.attachments.attachment_registry import AttachmentRegistry
    from src.fetcher.legacy.legacy_email_fetcher import LegacyEmailFetcherV2

# Экспортируем основные компоненты
__all__ = [
    # Новая архитектура
    "EmailFetcher",
    "ConnectionManager",
    "EmailProcessor",
    "EmailFilters",
    "EmailParser",
    "EmailStorage",
    "AttachmentRegistry",
    
    # Legacy совместимость
    "LegacyEmailFetcherV2",
]

# Версия модуля
__version__ = "2.0.0"

# Информация об архитектуре
__architecture_info__ = {
    "version": "2.0.0",
    "description": "Модульная архитектура email fetcher с исправленным маппингом вложений",
    "components": {
        "core": [
            "EmailFetcher - Основной фасад",
            "ConnectionManager - Управление соединениями",
            "EmailProcessor - Обработка писем",
        ],
        "filters": [
            "EmailFilters - Фильтрация писем",
        ],
        "parsers": [
            "EmailParser - Парсинг писем",
        ],
        "storage": [
            "EmailStorage - Хранение писем",
        ],
        "attachments": [
            "AttachmentRegistry - Реестр вложений с message_id",
        ],
        "legacy": [
            "LegacyEmailFetcherV2 - Обратная совместимость",
        ],
        "cli": [
            "CLI интерфейс с интерактивным меню",
        ],
    },
    "key_fixes": [
        "Исправлен маппинг вложений: thread_id → message_id",
        "Модульная архитектура для лучшей поддерживаемости",
        "Сохранена обратная совместимость через LegacyEmailFetcherV2",
        "Добавлен CLI интерфейс для удобного запуска",
    ],
}