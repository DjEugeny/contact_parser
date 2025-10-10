#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗺️ Утилиты для работы с путями конфигурации проекта.

Включает централизованное управление путями к данным OCR
и автоматическую миграцию data/final_results → data/ocr.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import shutil
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR: Path = PROJECT_ROOT / "config"
DATA_DIR: Path = PROJECT_ROOT / "data"
LOGS_DIR: Path = DATA_DIR / "logs"


def get_config_path(*parts: str) -> Path:
    """🔍 Возвращает путь внутри папки `config`.

    Args:
        *parts: последовательность сегментов пути (например, "providers.json").

    Returns:
        Path: абсолютный путь до требуемого файла/директории конфигурации.
    """
    if not parts:
        return CONFIG_DIR
    return CONFIG_DIR.joinpath(*parts)


def ensure_config_structure() -> None:
    """🔧 Создаёт базовые директории (`config`, `data`, `logs`) при необходимости."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


class DataPaths:
    """Централизованная конфигурация путей к данным"""
    
    # Базовая директория данных
    BASE_DIR = DATA_DIR
    
    # OCR результаты (новое название)
    OCR_DIR = BASE_DIR / "ocr"
    OCR_TEXTS_DIR = OCR_DIR / "texts"
    OCR_REPORTS_DIR = OCR_DIR / "reports"
    
    # Устаревшее название (для обратной совместимости)
    LEGACY_FINAL_RESULTS_DIR = BASE_DIR / "final_results"
    
    # Флаг для отслеживания выполнения миграции
    _migration_checked = False
    
    @classmethod
    def migrate_if_needed(cls) -> bool:
        """
        Автоматическая миграция data/final_results → data/ocr при первом запуске.
        
        Returns:
            bool: True если миграция была выполнена, False если не требовалась
        """
        # Проверяем только один раз за сессию
        if cls._migration_checked:
            return False
            
        cls._migration_checked = True
        
        # Если новая структура уже существует, миграция не нужна
        if cls.OCR_DIR.exists():
            logger.debug(f"✅ Директория {cls.OCR_DIR} уже существует")
            return False
        
        # Если старая структура не существует, создаём новую
        if not cls.LEGACY_FINAL_RESULTS_DIR.exists():
            logger.info(f"📁 Создание новой структуры: {cls.OCR_DIR}")
            cls.OCR_TEXTS_DIR.mkdir(parents=True, exist_ok=True)
            cls.OCR_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            return False
        
        # Выполняем миграцию
        try:
            logger.info(f"🔄 Миграция: {cls.LEGACY_FINAL_RESULTS_DIR} → {cls.OCR_DIR}")
            
            # Подсчитываем файлы для проверки
            texts_before = len(list(cls.LEGACY_FINAL_RESULTS_DIR.glob("texts/**/*.txt")))
            reports_before = len(list(cls.LEGACY_FINAL_RESULTS_DIR.glob("reports/**/*")))
            
            logger.info(f"   Файлов texts: {texts_before}")
            logger.info(f"   Файлов reports: {reports_before}")
            
            # Переименовываем директорию
            shutil.move(str(cls.LEGACY_FINAL_RESULTS_DIR), str(cls.OCR_DIR))
            
            # Проверяем результат
            texts_after = len(list(cls.OCR_TEXTS_DIR.glob("**/*.txt")))
            reports_after = len(list(cls.OCR_REPORTS_DIR.glob("**/*")))
            
            if texts_before == texts_after and reports_before == reports_after:
                logger.info(f"✅ Миграция завершена успешно")
                logger.info(f"   Проверка: texts={texts_after}, reports={reports_after}")
                return True
            else:
                logger.warning(f"⚠️  Несоответствие количества файлов после миграции!")
                logger.warning(f"   До: texts={texts_before}, reports={reports_before}")
                logger.warning(f"   После: texts={texts_after}, reports={reports_after}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка при миграции: {e}")
            # Пытаемся откатить изменения
            if cls.OCR_DIR.exists() and not cls.LEGACY_FINAL_RESULTS_DIR.exists():
                try:
                    shutil.move(str(cls.OCR_DIR), str(cls.LEGACY_FINAL_RESULTS_DIR))
                    logger.info(f"↩️  Откат миграции выполнен")
                except Exception as rollback_error:
                    logger.error(f"❌ Ошибка при откате: {rollback_error}")
            raise
    
    @classmethod
    def ensure_directories(cls):
        """Создаёт необходимые директории, если они не существуют"""
        cls.migrate_if_needed()
        cls.OCR_TEXTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.OCR_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_ocr_text_path(cls, date_folder: str, filename: str) -> Path:
        """
        Получить путь к OCR тексту для конкретного файла.
        
        Args:
            date_folder: Папка с датой (например, "2025-07-29")
            filename: Имя файла (например, "document.txt")
            
        Returns:
            Path: Полный путь к файлу
        """
        cls.migrate_if_needed()
        return cls.OCR_TEXTS_DIR / date_folder / filename
    
    @classmethod
    def get_ocr_report_path(cls, date_folder: str, filename: str) -> Path:
        """
        Получить путь к OCR отчёту для конкретного файла.
        
        Args:
            date_folder: Папка с датой (например, "2025-07-29")
            filename: Имя файла отчёта
            
        Returns:
            Path: Полный путь к файлу отчёта
        """
        cls.migrate_if_needed()
        return cls.OCR_REPORTS_DIR / date_folder / filename


# Для удобства импорта
OCR_DIR = DataPaths.OCR_DIR
OCR_TEXTS_DIR = DataPaths.OCR_TEXTS_DIR
OCR_REPORTS_DIR = DataPaths.OCR_REPORTS_DIR
