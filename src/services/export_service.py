#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Export Service - обертка над экспортными модулями
Фаза 5+: Интеграция существующих модулей
"""

from typing import Dict, Optional
import logging

# Импорт существующих модулей
from ..google_sheets_exporter import GoogleSheetsExporter
from ..local_exporter import LocalDataExporter


class ExportService:
    """📊 Сервис для экспорта данных"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.google_exporter = GoogleSheetsExporter()
        self.local_exporter = LocalDataExporter()

    def export_to_google_sheets(self, date: str, results: Optional[Dict] = None,
                               create_new_sheet: bool = False) -> bool:
        """
        📊 Экспорт в Google Sheets

        Args:
            date: Дата для экспорта
            results: Результаты для экспорта (опционально)
            create_new_sheet: Создать новую таблицу

        Returns:
            bool: Успешность экспорта
        """
        try:
            if create_new_sheet:
                spreadsheet_id = self.google_exporter.create_new_spreadsheet(f"Contact Parser - {date}")
                if not spreadsheet_id:
                    return False

            return self.google_exporter.export_results_by_date(date, results)
        except Exception as e:
            self.logger.error(f"❌ Ошибка экспорта в Google Sheets: {e}")
            return False

    def export_locally(self, date: str, results: Optional[Dict] = None,
                      formats: Optional[list] = None) -> bool:
        """
        💾 Локальный экспорт

        Args:
            date: Дата для экспорта
            results: Результаты для экспорта (опционально)
            formats: Форматы экспорта ['csv', 'json']

        Returns:
            bool: Успешность экспорта
        """
        if formats is None:
            formats = ['csv', 'json']

        try:
            success = True
            for fmt in formats:
                if fmt == 'csv':
                    success &= self.local_exporter.export_results_by_date(date, results)
                elif fmt == 'json':
                    # JSON экспорт можно добавить в LocalDataExporter
                    pass

            return success
        except Exception as e:
            self.logger.error(f"❌ Ошибка локального экспорта: {e}")
            return False

    def export_with_fallback(self, date: str, results: Optional[Dict] = None,
                           primary: str = 'google', create_new_sheet: bool = False) -> bool:
        """
        🔄 Экспорт с fallback

        Args:
            primary: Первичный метод ('google' или 'local')
            create_new_sheet: Создать новую таблицу (для Google)

        Returns:
            bool: Успешность экспорта
        """
        if primary == 'google':
            # Сначала пробуем Google Sheets
            if self.export_to_google_sheets(date, results, create_new_sheet):
                return True

            self.logger.warning("⚠️ Google Sheets недоступен, переключаемся на локальный экспорт")
            return self.export_locally(date, results)

        else:  # primary == 'local'
            # Сначала пробуем локальный экспорт
            if self.export_locally(date, results):
                return True

            self.logger.warning("⚠️ Локальный экспорт недоступен, переключаемся на Google Sheets")
            return self.export_to_google_sheets(date, results, create_new_sheet)

    def get_available_dates(self) -> list:
        """📅 Получить доступные даты для экспорта"""
        try:
            return self.google_exporter.get_available_dates()
        except AttributeError:
            # Fallback - используем локальный экспортер или возвращаем пустой список
            self.logger.warning("⚠️ GoogleSheetsExporter не имеет метода get_available_dates, используем fallback")
            try:
                return self.local_exporter.get_available_dates()
            except AttributeError:
                self.logger.warning("⚠️ LocalDataExporter также не имеет метода get_available_dates")
                return []
