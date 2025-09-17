#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📧 Email Service - обертка над advanced_email_fetcher.py
Фаза 5+: Интеграция существующих модулей + Асинхронная обработка
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

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

    # 🚀 АСИНХРОННЫЕ МЕТОДЫ
    
    async def fetch_emails_by_date_range_async(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        🚀 Асинхронная загрузка писем за период
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            List[Dict]: Список загруженных писем
        """
        loop = asyncio.get_event_loop()
        
        # Выполняем синхронную операцию в отдельном потоке
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                self._fetch_emails_sync,
                start_date,
                end_date
            )
        
        return result
    
    def _fetch_emails_sync(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """🔄 Синхронная версия для executor"""
        if not self.fetcher:
            self.fetcher = AdvancedEmailFetcherV2(self.logger)
        
        try:
            return self.fetcher.fetch_emails_by_date_range(start_date, end_date)
        finally:
            if self.fetcher:
                self.fetcher.close()
    
    async def get_available_dates_async(self) -> List[str]:
        """🚀 Асинхронное получение доступных дат"""
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                self._get_available_dates_sync
            )
        
        return result
    
    def _get_available_dates_sync(self) -> List[str]:
        """🔄 Синхронная версия для executor"""
        from ..email_loader import ProcessedEmailLoader
        loader = ProcessedEmailLoader()
        return loader.get_available_date_folders()
    
    async def get_emails_count_by_date_async(self, date: str) -> int:
        """🚀 Асинхронное получение количества писем за дату"""
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                self._get_emails_count_sync,
                date
            )
        
        return result
    
    def _get_emails_count_sync(self, date: str) -> int:
        """🔄 Синхронная версия для executor"""
        from ..email_loader import ProcessedEmailLoader
        loader = ProcessedEmailLoader()
        emails = loader.load_emails_by_date(date)
        return len(emails)
    
    async def process_multiple_dates_async(self, dates: List[str]) -> Dict[str, List[Dict]]:
        """
        🚀 Параллельная обработка нескольких дат
        
        Args:
            dates: Список дат для обработки
            
        Returns:
            Dict[str, List[Dict]]: Результаты по датам
        """
        tasks = []
        
        for date in dates:
            # Создаем задачи для параллельного выполнения
            task = self._process_single_date_async(date)
            tasks.append(task)
        
        # Выполняем все задачи параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Формируем результат
        processed_results = {}
        for i, date in enumerate(dates):
            if isinstance(results[i], Exception):
                self.logger.error(f"Ошибка обработки даты {date}: {results[i]}")
                processed_results[date] = []
            else:
                processed_results[date] = results[i]
        
        return processed_results
    
    async def _process_single_date_async(self, date: str) -> List[Dict]:
        """🔄 Обработка одной даты асинхронно"""
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                self._load_emails_by_date_sync,
                date
            )
        
        return result
    
    def _load_emails_by_date_sync(self, date: str) -> List[Dict]:
        """🔄 Синхронная загрузка писем по дате"""
        from ..email_loader import ProcessedEmailLoader
        loader = ProcessedEmailLoader()
        return loader.load_emails_by_date(date)
