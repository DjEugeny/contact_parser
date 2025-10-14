"""
LegacyEmailFetcherV2 - Фасад обратной совместимости.

Обеспечивает совместимость с существующим кодом, который использует
старый интерфейс AdvancedEmailFetcherV2, но внутри использует новую
архитектуру с корректным маппингом вложений.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

try:
    from ..core.email_fetcher import EmailFetcher
    from ..utils.email_utils import generate_thread_id as build_thread_id
    try:
        from ...config.paths import CONFIG_DIR, ensure_config_structure
    except ImportError:
        # Fallback для прямого запуска
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from src.config.paths import CONFIG_DIR, ensure_config_structure
except ImportError:
    # Fallback для прямого запуска
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.fetcher.core.email_fetcher import EmailFetcher
    from src.fetcher.utils.email_utils import generate_thread_id as build_thread_id
    try:
        from src.config.paths import CONFIG_DIR, ensure_config_structure
    except ImportError:
        # Если и это не сработало, используем простые значения по умолчанию
        CONFIG_DIR = project_root / "config"
        def ensure_config_structure():
            """Упрощенная версия функции создания структуры директорий"""
            from pathlib import Path
            data_dir = project_root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            (data_dir / "emails").mkdir(parents=True, exist_ok=True)
            (data_dir / "attachments").mkdir(parents=True, exist_ok=True)


class LegacyEmailFetcherV2:
    """
    Legacy фасад для обратной совместимости с AdvancedEmailFetcherV2.
    
    Предоставляет тот же интерфейс, что и оригинальный класс,
    но использует новую архитектуру с исправленным маппингом вложений.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Инициализация legacy фасада.
        
        Args:
            logger: Экземпляр логгера
        """
        self.logger = logger
        
        # Создаем папки для данных
        ensure_config_structure()
        
        # Создаем основной фасад
        self.email_fetcher = EmailFetcher(logger)

        # Выгружаем компоненты для совместимости со старым кодом
        self.connection_manager = self.email_fetcher.connection_manager
        self.email_storage = self.email_fetcher.email_storage
        self.attachment_registry = self.email_fetcher.attachment_registry
        self.email_filters = self.email_fetcher.filters
        self.email_parser = self.email_fetcher.email_parser
        self.text_cleaner = self.email_fetcher.text_cleaner
        self.email_processor = self.email_fetcher.email_processor
        
        # Совместимость со старыми атрибутами
        self.stats = self.email_fetcher.stats.copy()
        self.enable_size_logging = False
        
        # Дополнительные атрибуты для совместимости
        self.data_dir = self.email_fetcher.data_dir
        self.emails_dir = self.email_fetcher.emails_dir
        self.attachments_dir = self.email_fetcher.attachments_dir
        self.logs_dir = self.email_fetcher.logs_dir
        self.config_dir = CONFIG_DIR
        
        # Фильтры
        self.filters = self.email_filters
        
        # Очиститель текста
        self.text_cleaner = self.email_fetcher.text_cleaner
        
        self.logger.info("🔄 LegacyEmailFetcherV2 инициализирован (совместимый режим)")
    
    def connect(self) -> bool:
        """
        Подключение к серверу (совместимый метод).
        
        Returns:
            True если подключение успешно
        """
        return self.connection_manager.connect()
    
    def close(self):
        """
        Закрытие соединения (совместимый метод).
        """
        self.email_fetcher.close()
        self.logger.info("🔐 Соединение закрыто (legacy режим)")
    
    def fetch_emails_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict]:
        """
        Получение писем за период (совместимый метод).
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Список писем
        """
        # Используем новый фасад
        emails = self.email_fetcher.fetch_emails_by_date_range(start_date, end_date)
        
        # Обновляем статистику для совместимости
        self.stats = self.email_fetcher.stats.copy()
        
        return emails
    
    def process_single_email(
        self,
        msg_id: bytes,
        date_str: str,
        email_num_in_day: int,
        total_emails_in_day: int,
        include_attachment_data: bool = False,
    ) -> Optional[Dict]:
        """
        Обработка одного письма (совместимый метод).
        
        Args:
            msg_id: ID письма
            date_str: Строка даты
            email_num_in_day: Номер письма в дне
            total_emails_in_day: Всего писем в дне
            include_attachment_data: Включать данные вложений
            
        Returns:
            Данные письма или None
        """
        # Используем новый обработчик
        email_data = self.email_processor.process_email(
            msg_id=msg_id,
            date_str=date_str,
            email_num_in_day=email_num_in_day,
            total_emails_in_day=total_emails_in_day,
            include_attachment_data=include_attachment_data,
            connection_manager=self.connection_manager,
            attachment_registry=self.attachment_registry,
            email_storage=self.email_storage,
            email_parser=self.email_parser,
            filters=self.email_filters,
            text_cleaner=self.text_cleaner,
            stats=self.stats
        )
        
        # Обновляем статистику для совместимости
        self._update_stats_from_processor()
        
        return email_data
    
    def check_email_already_saved(self, message_id: str, date_folder: str) -> bool:
        """
        Проверка существования письма (совместимый метод).
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            
        Returns:
            True если письмо существует
        """
        return self.email_storage.email_exists(message_id, date_folder)
    
    def check_email_processing_status(
        self, 
        message_id: str, 
        date_folder: str
    ) -> Dict[str, bool]:
        """
        Проверка статуса обработки письма (совместимый метод).
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            
        Returns:
            Статус обработки
        """
        return self.attachment_registry.check_email_processing_status(message_id, date_folder)
    
    def get_processing_scenario(self, message_id: str, date_folder: str) -> str:
        """
        Определение сценария обработки (совместимый метод).
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            
        Returns:
            Сценарий обработки
        """
        return self.email_processor._get_processing_scenario(  # noqa: SLF001 - совместимость
            message_id,
            date_folder,
            self.attachment_registry,
            self.email_storage,
        )
    
    def generate_thread_id(self, from_addr: str, subject: str, date: str) -> str:
        """
        Генерация ID треда (совместимый метод).
        
        Args:
            from_addr: Адрес отправителя
            subject: Тема письма
            date: Дата
            
        Returns:
            ID треда
        """
        return build_thread_id(from_addr, subject, date)
    
    def get_local_time(self, dt: datetime = None) -> datetime:
        """
        Получение местного времени (совместимый метод).
        
        Args:
            dt: Дата
            
        Returns:
            Местное время
        """
        try:
            from ..utils.date_utils import get_local_time
        except ImportError:
            # Fallback для прямого запуска
            import sys
            from pathlib import Path
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from src.fetcher.utils.date_utils import get_local_time
        return get_local_time(dt)
    
    def parse_email_date(self, date_header: str) -> datetime:
        """
        Парсинг даты письма (совместимый метод).
        
        Args:
            date_header: Заголовок даты
            
        Returns:
            Дата
        """
        try:
            from ..utils.date_utils import parse_email_date
        except ImportError:
            # Fallback для прямого запуска
            import sys
            from pathlib import Path
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from src.fetcher.utils.date_utils import parse_email_date
        return parse_email_date(date_header)
    
    def format_email_date_for_log(self, date_header: str) -> str:
        """
        Форматирование даты для лога (совместимый метод).
        
        Args:
            date_header: Заголовок даты
            
        Returns:
            Отформатированная дата
        """
        try:
            from ..utils.date_utils import format_email_date_for_log
        except ImportError:
            # Fallback для прямого запуска
            import sys
            from pathlib import Path
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from src.fetcher.utils.date_utils import format_email_date_for_log
        return format_email_date_for_log(date_header)
    
    def decode_header_value(self, val: str) -> str:
        """
        Декодирование заголовка (совместимый метод).
        
        Args:
            val: Значение заголовка
            
        Returns:
            Декодированное значение
        """
        try:
            from ..utils.email_utils import decode_header_value
        except ImportError:
            # Fallback для прямого запуска
            import sys
            from pathlib import Path
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from src.fetcher.utils.email_utils import decode_header_value
        return decode_header_value(val)
    
    def extract_plain_text(
        self, 
        msg, 
        include_attachment_data: bool = False
    ) -> str:
        """
        Извлечение текста письма (совместимый метод).
        
        Args:
            msg: Объект письма
            include_attachment_data: Включать данные вложений
            
        Returns:
            Текст письма
        """
        return self.email_parser.extract_plain_text(msg, include_attachment_data)
    
    def parse_recipient(self, recipients_str: str) -> List[str]:
        """
        Парсинг получателей (совместимый метод).
        
        Args:
            recipients_str: Строка получателей
            
        Returns:
            Список получателей
        """
        try:
            from ..utils.email_utils import parse_recipient
        except ImportError:
            # Fallback для прямого запуска
            import sys
            from pathlib import Path
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from src.fetcher.utils.email_utils import parse_recipient
        return parse_recipient(recipients_str)
    
    def save_attachment_or_inline(
        self,
        part,
        thread_id: str,
        date_folder: str,
        is_inline: bool = False,
        *,
        message_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Сохранение вложения (совместимый метод).
        
        Args:
            part: Часть письма
            thread_id: ID треда
            date_folder: Папка даты
            is_inline: Является ли встроенным
            message_id: Уникальный message-id письма (при наличии)
            
        Returns:
            Информация о вложении
        """
        effective_message_id = (message_id or thread_id or "unknown-message-id")
        if not message_id:
            self.logger.warning(
                "⚠️ message_id не передан в save_attachment_or_inline; fallback на thread_id %s",
                thread_id,
            )

        return self.attachment_registry.save_attachment(
            part=part,
            message_id=effective_message_id,
            thread_id=thread_id,
            date_folder=date_folder,
            is_inline=is_inline,
        )
    
    def retry_skipped_emails(self):
        """
        Повторная обработка пропущенных писем (совместимый метод).
        """
        self.logger.warning("⚠️ retry_skipped_emails пока не поддерживается в новой архитектуре")

    def list_dead_letters(self):
        """
        Просмотр писем в мертвой очереди (совместимый метод).
        """
        self.logger.warning("⚠️ list_dead_letters пока не поддерживается в новой архитектуре")
        return []

    def clear_dead_letters(self):
        """
        Очистка мертвой очереди (совместимый метод).
        """
        self.logger.warning("⚠️ clear_dead_letters пока не поддерживается в новой архитектуре")

    def print_final_stats(self):
        """
        Вывод итоговой статистики (совместимый метод).
        """
        self.email_fetcher._print_final_stats()  # noqa: SLF001

    def save_processing_stats(self, start_date: datetime, end_date: datetime):
        """
        Сохранение статистики обработки (совместимый метод).
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
        """
        self.email_fetcher._save_processing_stats(start_date, end_date)  # noqa: SLF001
    
    def _update_stats_from_processor(self):
        """Обновление статистики из процессора."""
        if hasattr(self.email_processor, 'stats'):
            self.stats.update(self.email_processor.stats)
    
    def _update_stats_from_fetcher(self):
        """Обновление статистики из фасада."""
        if hasattr(self.email_fetcher, 'stats'):
            self.stats.update(self.email_fetcher.stats)
    
    # Дополнительные методы для полной совместимости
    
    def safe_fetch(self, msg_id: bytes, flags: str = "(RFC822)") -> Optional[List]:
        """
        Безопасное получение письма (совместимый метод).
        
        Args:
            msg_id: ID письма
            flags: Флаги
            
        Returns:
            Данные письма
        """
        return self.connection_manager.safe_fetch(msg_id, flags)
    
    def safe_search(self, criteria: str) -> List[bytes]:
        """
        Безопасный поиск писем (совместимый метод).
        
        Args:
            criteria: Критерии поиска
            
        Returns:
            Список ID писем
        """
        return self.connection_manager.safe_search(criteria)
    
    def get_email_headers_only(self, msg_id: bytes):
        """
        Получение только заголовков письма (совместимый метод).
        
        Args:
            msg_id: ID письма
            
        Returns:
            Заголовки письма
        """
        return self.connection_manager.get_email_headers_only(msg_id)
    
    def check_email_size(self, msg_id: bytes) -> int:
        """
        Проверка размера письма (совместимый метод).
        
        Args:
            msg_id: ID письма
            
        Returns:
            Размер письма в байтах
        """
        return self.connection_manager.check_email_size(msg_id)
    
    def analyze_bodystructure(self, msg_id: bytes) -> Dict:
        """
        Анализ структуры письма (совместимый метод).
        
        Args:
            msg_id: ID письма
            
        Returns:
            Информация о структуре
        """
        return self.connection_manager.analyze_bodystructure(msg_id)
