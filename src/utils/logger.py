#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Централизованная система логирования
Фаза 5: Архитектурная оптимизация + Критические исправления
"""

import os
import logging
import structlog
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
from datetime import datetime


class CentralizedLogger:
    """
    🎯 Централизованный логгер с ротацией файлов и структурированным форматом
    
    Особенности:
    - Структурированное логирование через structlog
    - Автоматическая ротация файлов
    - Разделение логов по уровням
    - Интеграция с существующей системой
    """
    
    _instance: Optional['CentralizedLogger'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'CentralizedLogger':
        """Singleton pattern для единого экземпляра логгера"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.log_dir = Path("/Users/evgenyzach/contact_parser/data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 🔧 Настройка структурированного логирования
        self._setup_structlog()
        
        # 📊 Создание логгеров для разных компонентов
        self.pipeline_logger = structlog.get_logger("pipeline")
        self.api_logger = structlog.get_logger("api")
        self.system_logger = structlog.get_logger("system")
        self.error_logger = structlog.get_logger("error")
        
        # 🎯 Настройка файловых хендлеров
        self._setup_file_handlers()
        
        self._initialized = True
    
    def _setup_structlog(self):
        """🔧 Настройка structlog с файловым выводом"""
        
        # Процессоры для структурированного логирования
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]
        
        # Добавляем JSON рендерер для файлов, обычный для консоли
        if os.getenv('LOG_FORMAT', 'json').lower() == 'json':
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())
        
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def _setup_file_handlers(self):
        """📁 Настройка файловых хендлеров с ротацией"""
        
        # Конфигурация для разных типов логов
        log_configs = {
            'pipeline': {
                'filename': self.log_dir / 'pipeline.log',
                'level': logging.INFO,
                'max_bytes': 10 * 1024 * 1024,  # 10MB
                'backup_count': 5
            },
            'api': {
                'filename': self.log_dir / 'api.log',
                'level': logging.INFO,
                'max_bytes': 5 * 1024 * 1024,   # 5MB
                'backup_count': 3
            },
            'system': {
                'filename': self.log_dir / 'system.log',
                'level': logging.INFO,
                'max_bytes': 5 * 1024 * 1024,   # 5MB
                'backup_count': 3
            },
            'error': {
                'filename': self.log_dir / 'errors.log',
                'level': logging.ERROR,
                'max_bytes': 10 * 1024 * 1024,  # 10MB
                'backup_count': 10
            }
        }
        
        # Создание хендлеров для каждого типа лога
        for logger_name, config in log_configs.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(config['level'])
            
            # Ротирующий файловый хендлер
            handler = RotatingFileHandler(
                filename=config['filename'],
                maxBytes=config['max_bytes'],
                backupCount=config['backup_count'],
                encoding='utf-8'
            )
            
            # Формат для файлового вывода
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            
            logger.addHandler(handler)
            
            # Предотвращаем дублирование в root logger
            logger.propagate = False
    
    def log_pipeline_start(self, pipeline_type: str, config: Dict[str, Any]):
        """📊 Логирование старта пайплайна"""
        self.pipeline_logger.info(
            "pipeline_started",
            pipeline_type=pipeline_type,
            config=config,
            timestamp=datetime.now().isoformat()
        )
    
    def log_pipeline_progress(self, pipeline_type: str, progress: Dict[str, Any]):
        """📊 Логирование прогресса пайплайна"""
        self.pipeline_logger.info(
            "pipeline_progress",
            pipeline_type=pipeline_type,
            progress=progress,
            timestamp=datetime.now().isoformat()
        )
    
    def log_pipeline_completion(self, pipeline_type: str, metrics: Dict[str, Any]):
        """📊 Логирование завершения пайплайна"""
        self.pipeline_logger.info(
            "pipeline_completed",
            pipeline_type=pipeline_type,
            metrics=metrics,
            timestamp=datetime.now().isoformat()
        )
    
    def log_api_request(self, provider: str, request_type: str, 
                       response_time: float, success: bool, 
                       error: Optional[str] = None):
        """🌐 Логирование API запросов"""
        log_data = {
            "event_type": "api_request",
            "provider": provider,
            "request_type": request_type,
            "response_time_ms": round(response_time * 1000, 2),
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        if error:
            log_data["error"] = error
            self.api_logger.error("api_request_failed", **log_data)
        else:
            self.api_logger.info("api_request_success", **log_data)
    
    def log_email_processing(self, email_id: str, status: str, 
                           processing_time: float, details: Dict[str, Any]):
        """📧 Логирование обработки email"""
        self.pipeline_logger.info(
            "email_processed",
            email_id=email_id,
            status=status,
            processing_time_ms=round(processing_time * 1000, 2),
            details=details,
            timestamp=datetime.now().isoformat()
        )
    
    def log_system_event(self, event_type: str, details: Dict[str, Any]):
        """🔧 Логирование системных событий"""
        self.system_logger.info(
            event_type,
            details=details,
            timestamp=datetime.now().isoformat()
        )
    
    def log_error(self, error_type: str, error_message: str, 
                 context: Optional[Dict[str, Any]] = None, 
                 exception: Optional[Exception] = None):
        """❌ Логирование ошибок"""
        error_data = {
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        if context:
            error_data["context"] = context
            
        if exception:
            error_data["exception_type"] = type(exception).__name__
            error_data["exception_details"] = str(exception)
        
        self.error_logger.error("system_error", **error_data)
    
    def log_performance_metrics(self, component: str, metrics: Dict[str, Any]):
        """📈 Логирование метрик производительности"""
        self.system_logger.info(
            "performance_metrics",
            component=component,
            metrics=metrics,
            timestamp=datetime.now().isoformat()
        )
    
    def get_logger(self, name: str) -> structlog.BoundLogger:
        """🎯 Получение именованного логгера"""
        return structlog.get_logger(name)
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """🧹 Очистка старых логов"""
        import time
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    self.system_logger.info(
                        "log_file_cleaned",
                        filename=str(log_file),
                        timestamp=datetime.now().isoformat()
                    )
                except Exception as e:
                    self.error_logger.error(
                        "log_cleanup_failed",
                        filename=str(log_file),
                        error=str(e),
                        timestamp=datetime.now().isoformat()
                    )


# 🎯 Глобальный экземпляр логгера
logger = CentralizedLogger()


# 🔧 Удобные функции для быстрого доступа
def log_pipeline_event(event_type: str, **kwargs):
    """Быстрое логирование событий пайплайна"""
    logger.pipeline_logger.info(event_type, **kwargs, timestamp=datetime.now().isoformat())


def log_api_event(event_type: str, **kwargs):
    """Быстрое логирование API событий"""
    logger.api_logger.info(event_type, **kwargs, timestamp=datetime.now().isoformat())


def log_system_event(event_type: str, **kwargs):
    """Быстрое логирование системных событий"""
    logger.system_logger.info(event_type, **kwargs, timestamp=datetime.now().isoformat())


def log_error_event(error_type: str, error_message: str, **kwargs):
    """Быстрое логирование ошибок"""
    logger.error_logger.error(
        error_type, 
        error_message=error_message, 
        **kwargs, 
        timestamp=datetime.now().isoformat()
    )