#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 Единая система логирования для всех модулей проекта
Обеспечивает сквозное логирование с единым форматом и уровнями
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
import os

class UnifiedLogger:
    """🎯 Унифицированный логгер для всех модулей проекта"""
    
    _loggers = {}
    _initialized = False
    _logs_dir = None
    _console_handler = None
    _file_handler = None
    
    @classmethod
    def setup(cls, logs_dir: Path = None, module_name: str = None):
        """🔧 Инициализация единой системы логирования"""
        
        if cls._initialized:
            return
            
        # Определяем директорию для логов
        if logs_dir is None:
            project_root = Path(__file__).parent.parent
            cls._logs_dir = project_root / "logs"
        else:
            cls._logs_dir = Path(logs_dir)
            
        cls._logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Консольный обработчик
        cls._console_handler = logging.StreamHandler(sys.stdout)
        cls._console_handler.setLevel(logging.INFO)
        cls._console_handler.setFormatter(formatter)
        
        # Файловый обработчик с ротацией
        log_filename = cls._logs_dir / f"unified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        cls._file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        cls._file_handler.setLevel(logging.DEBUG)
        cls._file_handler.setFormatter(formatter)
        
        cls._initialized = True
        
        # Логируем инициализацию
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(cls._console_handler)
        root_logger.addHandler(cls._file_handler)
        
        root_logger.info("📝 Единая система логирования инициализирована")
        root_logger.info(f"📁 Логи сохраняются в: {cls._logs_dir}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """📋 Получить логгер для конкретного модуля"""
        
        if not cls._initialized:
            cls.setup()
            
        if name in cls._loggers:
            return cls._loggers[name]
            
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # Добавляем обработчики если их еще нет
        if not logger.handlers:
            logger.addHandler(cls._console_handler)
            logger.addHandler(cls._file_handler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def add_console_handler(cls, logger: logging.Logger):
        """➕ Добавить консольный обработчик к существующему логгеру"""
        if cls._console_handler and cls._console_handler not in logger.handlers:
            logger.addHandler(cls._console_handler)
    
    @classmethod
    def remove_console_handler(cls, logger: logging.Logger):
        """➖ Удалить консольный обработчик из логгера"""
        if cls._console_handler and cls._console_handler in logger.handlers:
            logger.removeHandler(cls._console_handler)

# Глобальные функции для удобства использования
def get_logger(name: str) -> logging.Logger:
    """📋 Получить логгер для модуля"""
    return UnifiedLogger.get_logger(name)

def setup_logging(logs_dir: Path = None):
    """🔧 Инициализировать систему логирования"""
    UnifiedLogger.setup(logs_dir)

def add_module_logging(module_logger: logging.Logger):
    """➕ Добавить консольный вывод к логгеру модуля"""
    UnifiedLogger.add_console_handler(module_logger)

def remove_module_logging(module_logger: logging.Logger):
    """➖ Удалить консольный вывод из логгера модуля"""
    UnifiedLogger.remove_console_handler(module_logger)