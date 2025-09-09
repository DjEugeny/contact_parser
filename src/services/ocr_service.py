#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 OCR Service - обертка над ocr_processor.py
Фаза 5+: Интеграция существующих модулей
"""

from pathlib import Path
from typing import Dict, List, Optional
import logging

# Импорт существующего модуля
from ..ocr_processor import OCRProcessor


class OCRService:
    """🔍 Сервис для OCR обработки документов"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.processor = OCRProcessor()

    def process_date(self, date: str) -> Dict:
        """
        📅 Обработать все файлы за указанную дату

        Args:
            date: Дата в формате YYYY-MM-DD

        Returns:
            Dict: Результаты обработки
        """
        return self.processor.process_date(date)

    def get_available_dates(self) -> List[str]:
        """📅 Получить доступные даты для обработки"""
        return self.processor.get_available_dates()

    def get_files_for_date(self, date: str) -> List[Path]:
        """📁 Получить файлы для обработки за дату"""
        return self.processor.get_files_for_date(date)

    def test_single_file(self, file_path: Path) -> Dict:
        """🧪 Протестировать обработку одного файла"""
        return self.processor.extract_text_from_file(file_path)

    def get_processing_stats(self, date: str) -> Dict:
        """📊 Получить статистику обработки"""
        # Можно расширить OCRProcessor для возврата статистики
        return {
            'date': date,
            'available_dates': len(self.get_available_dates()),
            'files_for_date': len(self.get_files_for_date(date))
        }
