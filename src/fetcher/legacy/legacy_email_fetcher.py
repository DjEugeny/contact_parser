"""
LegacyEmailFetcherV2 - Фасад обратной совместимости.

Обеспечивает совместимость с существующим кодом, который использует
старый интерфейс AdvancedEmailFetcherV2, но внутри использует новую
архитектуру с корректным маппингом вложений.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..core.email_fetcher import EmailFetcher
from ..core.connection_manager import ConnectionManager
from ..core.email_processor import EmailProcessor
from ..filters.email_filters import EmailFilters
from ..parsers.email_parser import EmailParser
from ..storage.email_storage import EmailStorage
from ..attachments.attachment_registry import AttachmentRegistry
from ...text_cleaner import EmailTextCleaner
from ...config.paths import ensure_config_structure


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
        
        # Инициализируем компоненты новой архитектуры
        self.connection_manager = ConnectionManager(logger)
        self.email_storage = EmailStorage(logger)
        self.attachment_registry = AttachmentRegistry(logger)
        self.email_filters = EmailFilters(logger)
        self.email_parser = EmailParser(logger)
        self.text_cleaner = EmailTextCleaner(logger)
        
        # Создаем основной фасад
        self.email_fetcher = EmailFetcher(
            connection_manager=self.connection_manager,
            email_storage=self.email_storage,
            attachment_registry=self.attachment_registry,
            email_filters=self.email_filters,
            email_parser=self.email_parser,
            text_cleaner=self.text_cleaner,
            logger=logger
        )
        
        # Инициализируем обработчик писем
        self.email_processor = EmailProcessor(
            connection_manager=self.connection_manager,
            email_storage=self.email_storage,
            attachment_registry=self.attachment_registry,
            email_filters=self.email_filters,
            email_parser=self.email_parser,
            text_cleaner=self.text_cleaner,
            logger=logger
        )
        
        # Совместимость со старыми атрибутами
        self.stats = self.email_fetcher.stats.copy()
        self.enable_size_logging = False
        
        # Дополнительные атрибуты для совместимости
        self.data_dir = self.email_storage.data_dir
        self.emails_dir = self.email_storage.emails_dir
        self.attachments_dir = self.attachment_registry.attachments_dir
        self.logs_dir = self.email_storage.data_dir / "logs"
        self.config_dir = self.email_storage.data_dir.parent / "config"
        
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
        self.connection_manager.disconnect()
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
        email_data = self.email_processor.process_single_email(
            msg_id=msg_id,
            date_str=date_str,
            email_num_in_day=email_num_in_day,
            total_emails_in_day=total_emails_in_day,
            include_attachment_data=include_attachment_data
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
        return self.email_fetcher.check_email_processing_status(message_id, date_folder)
    
    def get_processing_scenario(self, message_id: str, date_folder: str) -> str:
        """
        Определение сценария обработки (совместимый метод).
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            
        Returns:
            Сценарий обработки
        """
        return self.email_fetcher.get_processing_scenario(message_id, date_folder)
    
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
        return self.email_fetcher.generate_thread_id(from_addr, subject, date)
    
    def get_local_time(self, dt: datetime = None) -> datetime:
        """
        Получение местного времени (совместимый метод).
        
        Args:
            dt: Дата
            
        Returns:
            Местное время
        """
        from ..utils.date_utils import get_local_time
        return get_local_time(dt)
    
    def parse_email_date(self, date_header: str) -> datetime:
        """
        Парсинг даты письма (совместимый метод).
        
        Args:
            date_header: Заголовок даты
            
        Returns:
            Дата
        """
        from ..utils.date_utils import parse_email_date
        return parse_email_date(date_header)
    
    def format_email_date_for_log(self, date_header: str) -> str:
        """
        Форматирование даты для лога (совместимый метод).
        
        Args:
            date_header: Заголовок даты
            
        Returns:
            Отформатированная дата
        """
        from ..utils.date_utils import format_email_date_for_log
        return format_email_date_for_log(date_header)
    
    def decode_header_value(self, val: str) -> str:
        """
        Декодирование заголовка (совместимый метод).
        
        Args:
            val: Значение заголовка
            
        Returns:
            Декодированное значение
        """
        from ..utils.email_utils import decode_header_value
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
        from ..utils.email_utils import parse_recipient
        return parse_recipient(recipients_str)
    
    def save_attachment_or_inline(
        self,
        part,
        thread_id: str,
        date_folder: str,
        is_inline: bool = False,
    ) -> Optional[Dict]:
        """
        Сохранение вложения (совместимый метод).
        
        Args:
            part: Часть письма
            thread_id: ID треда
            date_folder: Папка даты
            is_inline: Является ли встроенным
            
        Returns:
            Информация о вложении
        """
        # Используем реестр вложений с message_id
        # Для совместимости передаем thread_id, но реестр будет использовать message_id
        return self.attachment_registry.save_attachment(
            part=part,
            message_id=thread_id,  # Временно используем thread_id для совместимости
            date_folder=date_folder,
            is_inline=is_inline
        )
    
    def retry_skipped_emails(self):
        """
        Повторная обработка пропущенных писем (совместимый метод).
        """
        self.email_fetcher.retry_skipped_emails()
        self._update_stats_from_fetcher()
    
    def list_dead_letters(self):
        """
        Просмотр писем в мертвой очереди (совместимый метод).
        """
        return self.email_fetcher.list_dead_letters()
    
    def clear_dead_letters(self):
        """
        Очистка мертвой очереди (совместимый метод).
        """
        self.email_fetcher.clear_dead_letters()
    
    def print_final_stats(self):
        """
        Вывод итоговой статистики (совместимый метод).
        """
        self.email_fetcher.print_final_stats()
    
    def save_processing_stats(self, start_date: datetime, end_date: datetime):
        """
        Сохранение статистики обработки (совместимый метод).
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
        """
        self.email_fetcher.save_processing_stats(start_date, end_date)
    
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