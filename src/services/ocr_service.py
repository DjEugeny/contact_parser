#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 OCR Service - унифицированный сервис OCR обработки
Фаза 5+: Интеграция с OCRManager для устранения дублирования
"""

from pathlib import Path
from typing import Dict, List, Optional
import logging

# Импорт унифицированного OCR менеджера
from ..core.ocr_manager import get_ocr_manager
# Импорт для обратной совместимости
from ..ocr_processor import OCRProcessor


class OCRService:
    """🔍 Унифицированный сервис для OCR обработки документов с кешированием"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        # Используем унифицированный OCRManager
        self.ocr_manager = get_ocr_manager()
        # Сохраняем прямой доступ к процессору для обратной совместимости
        self.processor = self.ocr_manager._get_ocr_processor()

    def process_date(self, date: str) -> Dict:
        """
        📅 Обработать все файлы за указанную дату через OCRManager

        Args:
            date: Дата в формате YYYY-MM-DD

        Returns:
            Dict: Результаты обработки с кеш статистикой
        """
        try:
            files_to_process = self.processor.get_files_for_date(date)
            if not files_to_process:
                return {
                    'success': False,
                    'error': f'Нет файлов для обработки за дату {date}',
                    'processed_files': 0,
                    'total_files': 0
                }
            
            # Используем унифицированный OCRManager для обработки
            result = self.ocr_manager.test_files_by_date(date, files_to_process)
            
            return {
                'success': True,
                'processed_files': result['processed_files'],
                'total_files': result['total_files'],
                'date': date,
                'cache_stats': self.ocr_manager.get_cache_stats()
            }
        except Exception as e:
            self.logger.error(f"Ошибка при обработке файлов за дату {date}: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_files': 0,
                'total_files': 0
            }

    def get_available_dates(self) -> List[str]:
        """📅 Получить доступные даты для обработки"""
        return self.processor.get_available_dates()

    def get_files_for_date(self, date: str) -> List[Path]:
        """📁 Получить файлы для обработки за дату"""
        return self.processor.get_files_for_date(date)

    def test_single_file(self, file_path: Path, date: str = None) -> Dict:
        """🧪 Протестировать обработку одного файла через OCRManager"""
        return self.ocr_manager.extract_text_from_file(str(file_path), date)

    def get_processing_stats(self, date: str) -> Dict:
        """📊 Получить расширенную статистику обработки с кешированием"""
        cache_stats = self.ocr_manager.get_cache_stats()
        return {
            'date': date,
            'available_dates': len(self.get_available_dates()),
            'files_for_date': len(self.get_files_for_date(date)),
            'cache_stats': cache_stats
        }
    
    def get_cache_stats(self) -> Dict:
        """📈 Получить статистику кеширования OCR"""
        return self.ocr_manager.get_cache_stats()
    
    def clear_cache(self):
        """🗑️ Очистить кеш OCR обработки"""
        self.ocr_manager.clear_cache()
        self.logger.info("Кеш OCR обработки очищен")
    
    def cleanup_cache(self):
        """🧹 Очистить недействительные записи кеша"""
        self.ocr_manager.cleanup_invalid_cache_entries()
        self.logger.info("Недействительные записи кеша удалены")
