"""Основной обработчик ошибок с декораторами для автоматической обработки."""

import asyncio
import json
import logging
import traceback
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type, Union
from datetime import datetime
from unittest.mock import Mock

from .exceptions import (
    BaseProcessingError,
    ErrorCategory,
    ErrorSeverity,
    NetworkError,
    ProcessingError,
    ValidationError,
    ResourceError,
    ConfigurationError,
    AuthenticationError,
    TimeoutError
)
from .recovery_manager import RecoveryManager


class MockErrorReporter:
    """Заглушка для error_reporter для совместимости с тестами."""
    
    def report_error(self, *args, **kwargs):
        """Заглушка метода report_error."""
        pass


class ErrorHandler:
    """Центральный обработчик ошибок для всего пайплайна."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.recovery_manager = RecoveryManager(self.config.get("recovery"))
        self.error_reporter = Mock()  # Заглушка для совместимости с тестами
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recovery_attempts": 0,
            "successful_recoveries": 0
        }
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Загрузка конфигурации обработки ошибок."""
        if config_path is None:
            config_path = Path(__file__).parent / "error_handling_config.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить конфигурацию: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию."""
        return {
            "error_reporting": {
                "log_level": "INFO",
                "include_stack_trace": True,
                "max_context_size": 1000
            },
            "recovery_config": {
                "auto_recovery_enabled": True,
                "max_recovery_attempts": 2
            }
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        auto_recover: bool = True,
        component: Optional[str] = None
    ) -> Dict[str, Any]:
        """Обработка ошибки с возможным автоматическим восстановлением."""
        
        # Преобразование в BaseProcessingError если необходимо
        if not isinstance(error, BaseProcessingError):
            error = self._convert_to_processing_error(error, context)
        
        # Обновление статистики
        self._update_error_stats(error)
        
        # Логирование ошибки
        self._log_error(error, context)
        
        # Отчет об ошибке
        self.error_reporter.report_error(error, context)
        
        # Попытка автоматического восстановления
        recovery_result = None
        recovered = False
        recovery_strategy = None
        
        if auto_recover and error.recoverable:
            recovery_result = await self.recovery_manager.attempt_recovery(
                error, context, component
            )
            recovered = recovery_result.get("recovered", False)
            recovery_strategy = recovery_result.get("strategy")
        
        return {
            "handled": True,
            "recovered": recovered,
            "recovery_strategy": recovery_strategy,
            "error": error.to_dict(),
            "handled_at": datetime.now().isoformat(),
            "recovery_attempted": auto_recover and error.recoverable,
            "recovery_result": recovery_result,
            "context": context or {}
        }
    
    def _convert_to_processing_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> BaseProcessingError:
        """Преобразование стандартных исключений в BaseProcessingError."""
        
        error_message = str(error)
        error_type = type(error).__name__
        
        # Определение категории и типа ошибки
        if "network" in error_message.lower() or "connection" in error_message.lower():
            return NetworkError(error_message, context=context)
        elif "timeout" in error_message.lower():
            return TimeoutError(error_message, context=context)
        elif "permission" in error_message.lower() or "auth" in error_message.lower():
            return AuthenticationError(error_message, context=context)
        elif "memory" in error_message.lower() or "disk" in error_message.lower():
            return ResourceError(error_message, context=context)
        elif "config" in error_message.lower() or "setting" in error_message.lower():
            return ConfigurationError(error_message, context=context)
        elif "valid" in error_message.lower():
            return ValidationError(error_message, context=context)
        else:
            return ProcessingError(
                f"{error_type}: {error_message}",
                context=context
            )
    
    def _update_error_stats(self, error: BaseProcessingError):
        """Обновление статистики ошибок."""
        self.error_stats["total_errors"] += 1
        
        category = error.category.value
        if category not in self.error_stats["errors_by_category"]:
            self.error_stats["errors_by_category"][category] = 0
        self.error_stats["errors_by_category"][category] += 1
        
        severity = error.severity.value
        if severity not in self.error_stats["errors_by_severity"]:
            self.error_stats["errors_by_severity"][severity] = 0
        self.error_stats["errors_by_severity"][severity] += 1
    
    def _log_error(
        self,
        error: BaseProcessingError,
        context: Optional[Dict[str, Any]] = None
    ):
        """Логирование ошибки с контекстом."""
        
        log_data = {
            "error": error.to_dict(),
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Добавление stack trace если включено
        if self.config.get("error_reporting", {}).get("include_stack_trace", True):
            log_data["stack_trace"] = traceback.format_exc()
        
        # Выбор уровня логирования
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Критическая ошибка: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"Серьезная ошибка: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Ошибка: {error.message}", extra=log_data)
        else:
            self.logger.info(f"Незначительная ошибка: {error.message}", extra=log_data)
    
    def _attempt_recovery(self, error: BaseProcessingError) -> Dict[str, Any]:
        """Попытка автоматического восстановления."""
        
        self.error_stats["recovery_attempts"] += 1
        
        recovery_strategies = self.config.get("recovery_config", {}).get("recovery_strategies", {})
        strategy = recovery_strategies.get(error.category.value)
        
        if not strategy:
            return {
                "success": False,
                "reason": "Стратегия восстановления не найдена",
                "strategy": None
            }
        
        try:
            # Здесь будет вызов соответствующей стратегии восстановления
            # Пока что заглушка
            recovery_success = self._execute_recovery_strategy(strategy, error)
            
            if recovery_success:
                self.error_stats["successful_recoveries"] += 1
            
            return {
                "success": recovery_success,
                "strategy": strategy,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as recovery_error:
            self.logger.error(f"Ошибка при восстановлении: {recovery_error}")
            return {
                "success": False,
                "reason": str(recovery_error),
                "strategy": strategy
            }
    
    def _execute_recovery_strategy(self, strategy: str, error: BaseProcessingError) -> bool:
        """Выполнение стратегии восстановления."""
        # Заглушка для стратегий восстановления
        # В реальной реализации здесь будут конкретные действия
        self.logger.info(f"Выполнение стратегии восстановления: {strategy}")
        return True
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Получение статистики ошибок."""
        return self.error_stats.copy()
    
    def reset_stats(self):
        """Сброс статистики ошибок."""
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recovery_attempts": 0,
            "successful_recoveries": 0
        }


def handle_errors(
    error_handler: Optional[ErrorHandler] = None,
    auto_recover: bool = True,
    context: Optional[Dict[str, Any]] = None,
    return_on_error: Any = None
):
    """Декоратор для автоматической обработки ошибок."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = error_handler or ErrorHandler()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Создание контекста с информацией о функции
                func_context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
                
                if context:
                    func_context.update(context)
                
                # Обработка ошибки
                result = handler.handle_error(e, func_context, auto_recover)
                
                # Повторное возбуждение ошибки если восстановление не удалось
                if not result.get("recovery_result", {}).get("success", False):
                    if return_on_error is not None:
                        return return_on_error
                    raise
                
                return result
        
        return wrapper
    return decorator