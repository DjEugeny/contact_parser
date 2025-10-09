"""
EmailFetcher - Главный фасад новой модульной архитектуры.

Основной класс для обработки email с корректным маппингом вложений.
Использует message_id вместо thread_id для определения принадлежности вложений.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Импорты из новой архитектуры
from .connection_manager import ConnectionManager
from .email_processor import EmailProcessor

# Импорты из оригинального модуля для совместимости
from ..filters.email_filters import EmailFilters
from ..attachments.attachment_registry import AttachmentRegistry
from ..storage.email_storage import EmailStorage
from ..parsers.email_parser import EmailParser
from ..utils.date_utils import parse_date_flexible, get_local_time

# Импорты конфигурации
from ...config.paths import DATA_DIR, LOGS_DIR, ensure_config_structure
from ...text_cleaner import EmailTextCleaner


class EmailFetcher:
    """
    Главный фасад для обработки email с корректным маппингом вложений.
    
    Ключевые особенности:
    - Использует message_id для маппинга вложений (вместо thread_id)
    - Модульная архитектура с четким разделением ответственности
    - Централизованный реестр вложений
    - Обратная совместимость с существующим кодом
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Инициализация EmailFetcher.
        
        Args:
            logger: Экземпляр логгера
        """
        self.logger = logger
        
        # Создаем необходимые директории
        ensure_config_structure()
        
        # Инициализация компонентов
        self.connection_manager = ConnectionManager(logger)
        self.email_processor = EmailProcessor(logger)
        self.attachment_registry = AttachmentRegistry(logger)
        self.email_storage = EmailStorage(logger)
        self.email_parser = EmailParser(logger)
        
        # Фильтры и очиститель текста
        self.filters = EmailFilters(logger)
        self.text_cleaner = EmailTextCleaner(logger)
        
        # Директории
        self.data_dir = DATA_DIR
        self.emails_dir = self.data_dir / "emails"
        self.attachments_dir = self.data_dir / "attachments"
        self.logs_dir = LOGS_DIR
        
        # Статистика
        self.stats = {
            "processed": 0,
            "saved": 0,
            "already_exists": 0,
            "filtered_subject": 0,
            "filtered_blacklist": 0,
            "filtered_mass_mailing": 0,
            "saved_attachments": 0,
            "saved_inline_images": 0,
            "excluded_attachments": 0,
            "excluded_filenames": 0,
            "excluded_by_size": 0,
            "excluded_by_image_dimensions": 0,
            "unsupported_attachments": 0,
            "skipped_large_emails": 0,
            "skipped_already_processed": 0,
            "errors": 0,
            "retry_successful": 0,
            "retry_failed": 0,
            "total_skipped": 0,
        }
        
        self.logger.info("🔧 EmailFetcher инициализирован с новой архитектурой")
        self.logger.info("✅ Используется message_id для маппинга вложений")
    
    def fetch_emails_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """
        Получение писем за период с использованием новой архитектуры.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Список обработанных писем
        """
        self.logger.info("🎯 ЗАГРУЗКА ПИСЕМ ЗА ПЕРИОД (НОВАЯ АРХИТЕКТУРА)")
        self.logger.info(f"   📅 С: {start_date.strftime('%Y-%m-%d')}")
        self.logger.info(f"   📅 До: {end_date.strftime('%Y-%m-%d')}")
        self.logger.info("   ✅ Корректный маппинг вложений по message_id")
        
        # Устанавливаем соединение
        if not self.connection_manager.connect():
            self.logger.error("❌ Не удалось подключиться к серверу")
            return []
        
        all_emails = []
        current_date = start_date
        processed_emails_total = 0
        total_saved = 0
        
        while current_date <= end_date:
            date_display = current_date.strftime("%Y-%m-%d")
            
            self.logger.info("=" * 70)
            self.logger.info(f"📬 Обработка {date_display}...")
            
            # Получаем письма за день
            emails = self._process_date_emails(current_date)
            
            if emails:
                all_emails.extend(emails)
                saved_today = len(emails)
                total_saved += saved_today
                
                self.logger.info(
                    f"📊 Итого сохранено писем за {date_display}: {saved_today}"
                )
            else:
                self.logger.info("📭 Писем не найдено")
            
            current_date += timedelta(days=1)
            time.sleep(0.1)  # Небольшая задержка
        
        # Закрываем соединение
        self.connection_manager.close()
        
        # Сохраняем статистику
        self._save_processing_stats(start_date, end_date)
        self._print_final_stats()
        
        self.logger.info("=" * 70)
        self.logger.info(f"🎯 ОБЩИЙ ИТОГ ЗА ВСЕ ДНИ: сохранено {total_saved} писем")
        
        return all_emails
    
    def process_single_email(
        self,
        msg_id: bytes,
        date_str: str,
        email_num_in_day: int,
        total_emails_in_day: int,
        include_attachment_data: bool = False,
    ) -> Optional[Dict]:
        """
        Обработка одного письма с корректным маппингом вложений.
        
        Args:
            msg_id: ID письма
            date_str: Строка даты
            email_num_in_day: Номер письма в дне
            total_emails_in_day: Всего писем в дне
            include_attachment_data: Включать данные вложений
            
        Returns:
            Обработанные данные письма или None
        """
        return self.email_processor.process_email(
            msg_id=msg_id,
            date_str=date_str,
            email_num_in_day=email_num_in_day,
            total_emails_in_day=total_emails_in_day,
            include_attachment_data=include_attachment_data,
            connection_manager=self.connection_manager,
            attachment_registry=self.attachment_registry,
            email_storage=self.email_storage,
            email_parser=self.email_parser,
            filters=self.filters,
            text_cleaner=self.text_cleaner,
            stats=self.stats
        )
    
    def _process_date_emails(self, date: datetime) -> List[Dict]:
        """
        Обработка писем за конкретную дату.
        
        Args:
            date: Дата обработки
            
        Returns:
            Список обработанных писем
        """
        date_imap = date.strftime("%d-%b-%Y")
        date_display = date.strftime("%Y-%m-%d")
        
        # Получаем список писем за дату
        msg_ids = self.connection_manager.search_emails(f'(ON "{date_imap}")')
        
        if not msg_ids:
            return []
        
        self.logger.info(f"   Найдено писем: {len(msg_ids)}")
        
        emails = []
        
        for day_email_num, msg_id in enumerate(msg_ids, 1):
            email_data = self.process_single_email(
                msg_id=msg_id,
                date_str=date_display,
                email_num_in_day=day_email_num,
                total_emails_in_day=len(msg_ids),
                include_attachment_data=False
            )
            
            if email_data:
                emails.append(email_data)
        
        return emails
    
    def _save_processing_stats(self, start_date: datetime, end_date: datetime):
        """Сохранение статистики обработки."""
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        stats = {
            "period": f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}",
            "processed_at": get_local_time().isoformat(),
            "stats": self.stats,
            "architecture": "v2.0 - message_id based attachment mapping",
        }
        
        stats_path = self.logs_dir / f"processing_stats_{start_str}_{end_str}.json"
        
        try:
            import json
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            self.logger.info(f"📊 Статистика сохранена: {stats_path}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения статистики: {e}")
    
    def _print_final_stats(self):
        """Вывод итоговой статистики."""
        self.logger.info("=" * 70)
        self.logger.info("📊 ИТОГОВАЯ СТАТИСТИКА (НОВАЯ АРХИТЕКТУРА)")
        self.logger.info("=" * 70)
        self.logger.info(f"📧 Обработано писем: {self.stats['processed']}")
        self.logger.info(f"✅ Сохранено писем: {self.stats['saved']}")
        self.logger.info(f"📁 Уже существовало писем: {self.stats.get('already_exists', 0)}")
        self.logger.info(f"⏭️ Пропущено уже обработанных: {self.stats.get('skipped_already_processed', 0)}")
        self.logger.info(f"🚫 Исключено по теме: {self.stats['filtered_subject']}")
        self.logger.info(f"🚫 Исключено по черному списку: {self.stats['filtered_blacklist']}")
        self.logger.info(f"🚫 Исключено массовых рассылок: {self.stats['filtered_mass_mailing']}")
        self.logger.info("")
        self.logger.info("📎 СТАТИСТИКА ВЛОЖЕНИЙ:")
        self.logger.info(f"✅ Скачано вложений: {self.stats['saved_attachments']}")
        self.logger.info(f"🖼️ Встроенных изображений: {self.stats['saved_inline_images']}")
        self.logger.info(f"🚫 Исключено по расширению: {self.stats['excluded_attachments']}")
        self.logger.info(f"📝 Исключено по имени файла: {self.stats['excluded_filenames']}")
        self.logger.info(f"📏 Исключено по размеру файла: {self.stats['excluded_by_size']}")
        self.logger.info(f"🖼️ Исключено по размерам изображения: {self.stats['excluded_by_image_dimensions']}")
        self.logger.info(f"⚠️ Неподдерживаемых: {self.stats['unsupported_attachments']}")
        self.logger.info("")
        self.logger.info(f"❌ Ошибок обработки: {self.stats['errors']}")
        self.logger.info(f"📏 Пропущено больших писем: {self.stats['skipped_large_emails']}")
        
        total_filtered = (
            self.stats["filtered_subject"]
            + self.stats["filtered_blacklist"]
            + self.stats["filtered_mass_mailing"]
        )
        self.logger.info(f"🚫 Всего писем исключено: {total_filtered}")
        
        if self.stats["processed"] > 0:
            save_rate = (self.stats["saved"] / self.stats["processed"]) * 100
            self.logger.info(f"📈 Процент сохранения писем: {save_rate:.1f}%")
        
        self.logger.info("=" * 70)
    
    def close(self):
        """Закрытие соединения и освобождение ресурсов."""
        self.connection_manager.close()
        self.logger.info("🔐 EmailFetcher закрыт")