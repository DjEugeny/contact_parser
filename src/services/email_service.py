#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📧 Email Service - обертка над advanced_email_fetcher.py
Фаза 5+: Интеграция существующих модулей
"""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

# Импорт существующего модуля
from ..advanced_email_fetcher import AdvancedEmailFetcherV2


class EmailService:
    """📧 Сервис для работы с загрузкой писем"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.fetcher = None

    def fetch_emails_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        📅 Загрузить письма за период

        Args:
            start_date: Начальная дата
            end_date: Конечная дата

        Returns:
            List[Dict]: Список загруженных писем
        """
        if not self.fetcher:
            self.fetcher = AdvancedEmailFetcherV2(self.logger)

        try:
            return self.fetcher.fetch_emails_by_date_range(start_date, end_date)
        finally:
            if self.fetcher:
                self.fetcher.close()

    def get_available_dates(self) -> List[str]:
        """📅 Получить доступные даты для обработки"""
        # Используем email_loader для получения доступных дат
        from ..email_loader import ProcessedEmailLoader
        loader = ProcessedEmailLoader()
        return loader.get_available_date_folders()

    def get_emails_count_by_date(self, date: str) -> int:
        """📊 Получить количество писем за дату"""
        from ..email_loader import ProcessedEmailLoader
        loader = ProcessedEmailLoader()
        emails = loader.load_emails_by_date(date)
        return len(emails)
