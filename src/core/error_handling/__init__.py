"""Система обработки ошибок и автоматического восстановления.

Этот модуль предоставляет комплексную систему для:
- Обработки и классификации ошибок
- Автоматического восстановления после сбоев
- Повторных попыток с различными стратегиями
- Circuit Breaker pattern для защиты от каскадных сбоев
- Централизованного логирования и мониторинга ошибок

Основные компоненты:
- ErrorHandler: Основной обработчик ошибок с декораторами
- RetryManager: Управление повторными попытками
- CircuitBreaker: Защита от каскадных сбоев
- RecoveryManager: Автоматическое восстановление
- ErrorReporter: Централизованная отчетность

Пример использования:
    from src.core.error_handling import (
        ErrorHandler, handle_errors, retry, circuit_breaker
    )
    
    @handle_errors()
    @retry(max_attempts=3)
    @circuit_breaker(failure_threshold=5)
    def process_data(data):
        # Ваша логика обработки данных
        pass
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Импорт основных компонентов
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
    TimeoutError,
    CircuitBreakerOpenError,
    CriticalError
)

from .error_handler import ErrorHandler, handle_errors
from .retry_manager import RetryManager, BackoffStrategy, retry, async_retry
from .circuit_breaker import CircuitBreaker, CircuitState, circuit_breaker, async_circuit_breaker
from .recovery_manager import RecoveryManager, RecoveryStrategy
from .error_reporter import ErrorReporter

# Версия модуля
__version__ = "1.0.0"

# Экспорт основных компонентов
__all__ = [
    # Исключения
    "BaseProcessingError",
    "ErrorCategory",
    "ErrorSeverity",
    "NetworkError",
    "ProcessingError",
    "ValidationError",
    "ResourceError",
    "ConfigurationError",
    "AuthenticationError",
    "TimeoutError",
    "CircuitBreakerOpenError",
    "CriticalError",
    
    # Основные классы
    "ErrorHandler",
    "RetryManager",
    "CircuitBreaker",
    "RecoveryManager",
    "ErrorReporter",
    
    # Декораторы
    "handle_errors",
    "retry",
    "async_retry",
    "circuit_breaker",
    "async_circuit_breaker",
    
    # Перечисления
    "BackoffStrategy",
    "CircuitState",
    "RecoveryStrategy",
    
    # Утилиты
    "create_error_handling_system",
    "get_default_config",
    "setup_logging"
]

# Глобальные экземпляры (ленивая инициализация)
_error_handler: Optional[ErrorHandler] = None
_retry_manager: Optional[RetryManager] = None
_circuit_breaker: Optional[CircuitBreaker] = None
_recovery_manager: Optional[RecoveryManager] = None
_error_reporter: Optional[ErrorReporter] = None


def get_default_config() -> Dict[str, Any]:
    """Получение конфигурации по умолчанию для системы обработки ошибок."""
    
    config_file = Path("src/core/error_handling/error_handling_config.json")
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Не удалось загрузить конфигурацию: {e}")
    
    # Конфигурация по умолчанию
    return {
        "error_handler": {
            "log_level": "INFO",
            "include_stack_trace": True,
            "max_context_size": 1000,
            "enable_recovery": True
        },
        "retry": {
            "default_max_attempts": 3,
            "default_backoff_strategy": "exponential",
            "default_base_delay": 1.0,
            "default_max_delay": 60.0,
            "default_jitter": True
        },
        "circuit_breaker": {
            "default_failure_threshold": 5,
            "default_recovery_timeout": 60.0,
            "default_expected_exception": "Exception",
            "enable_monitoring": True
        },
        "recovery": {
            "max_recovery_attempts": 3,
            "recovery_timeout": 60.0,
            "enable_auto_recovery": True,
            "recovery_cooldown": 5.0,
            "enable_degraded_mode": True
        },
        "reporting": {
            "log_level": "INFO",
            "include_stack_trace": True,
            "max_context_size": 1000,
            "enable_metrics": True,
            "metrics_file": "logs/error_metrics.json"
        }
    }


def setup_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """Настройка логирования для системы обработки ошибок."""
    
    if config is None:
        config = get_default_config()
    
    log_level = config.get("reporting", {}).get("log_level", "INFO")
    
    # Создание директории для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настройка обработчика файлов
    file_handler = logging.FileHandler(log_dir / "error_handling.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Настройка логгера
    logger = logging.getLogger("src.core.error_handling")
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(file_handler)
    
    # Предотвращение дублирования логов
    logger.propagate = False


def create_error_handling_system(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Создание полной системы обработки ошибок.
    
    Args:
        config: Конфигурация системы. Если не указана, используется конфигурация по умолчанию.
    
    Returns:
        Словарь с экземплярами всех компонентов системы.
    """
    
    if config is None:
        config = get_default_config()
    
    # Настройка логирования
    setup_logging(config)
    
    # Создание компонентов
    error_reporter = ErrorReporter(config.get("reporting"))
    recovery_manager = RecoveryManager(config.get("recovery"))
    retry_manager = RetryManager(config.get("retry"))
    circuit_breaker = CircuitBreaker(
        failure_threshold=config.get("circuit_breaker", {}).get("default_failure_threshold", 5),
        recovery_timeout=config.get("circuit_breaker", {}).get("default_recovery_timeout", 60.0)
    )
    error_handler = ErrorHandler(
        config=config.get("error_handler"),
        error_reporter=error_reporter,
        recovery_manager=recovery_manager
    )
    
    return {
        "error_handler": error_handler,
        "retry_manager": retry_manager,
        "circuit_breaker": circuit_breaker,
        "recovery_manager": recovery_manager,
        "error_reporter": error_reporter,
        "config": config
    }


def get_error_handler(config: Optional[Dict[str, Any]] = None) -> ErrorHandler:
    """Получение глобального экземпляра ErrorHandler (ленивая инициализация)."""
    
    global _error_handler, _error_reporter, _recovery_manager
    
    if _error_handler is None:
        if config is None:
            config = get_default_config()
        
        if _error_reporter is None:
            _error_reporter = ErrorReporter(config.get("reporting"))
        
        if _recovery_manager is None:
            _recovery_manager = RecoveryManager(config.get("recovery"))
        
        _error_handler = ErrorHandler(
            config=config.get("error_handler"),
            error_reporter=_error_reporter,
            recovery_manager=_recovery_manager
        )
    
    return _error_handler


def get_retry_manager(config: Optional[Dict[str, Any]] = None) -> RetryManager:
    """Получение глобального экземпляра RetryManager (ленивая инициализация)."""
    
    global _retry_manager
    
    if _retry_manager is None:
        if config is None:
            config = get_default_config()
        
        _retry_manager = RetryManager(config.get("retry"))
    
    return _retry_manager


def get_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    config: Optional[Dict[str, Any]] = None
) -> CircuitBreaker:
    """Получение глобального экземпляра CircuitBreaker (ленивая инициализация)."""
    
    global _circuit_breaker
    
    if _circuit_breaker is None:
        if config is None:
            config = get_default_config()
        
        cb_config = config.get("circuit_breaker", {})
        _circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config.get("default_failure_threshold", failure_threshold),
            recovery_timeout=cb_config.get("default_recovery_timeout", recovery_timeout)
        )
    
    return _circuit_breaker


def get_recovery_manager(config: Optional[Dict[str, Any]] = None) -> RecoveryManager:
    """Получение глобального экземпляра RecoveryManager (ленивая инициализация)."""
    
    global _recovery_manager
    
    if _recovery_manager is None:
        if config is None:
            config = get_default_config()
        
        _recovery_manager = RecoveryManager(config.get("recovery"))
    
    return _recovery_manager


def get_error_reporter(config: Optional[Dict[str, Any]] = None) -> ErrorReporter:
    """Получение глобального экземпляра ErrorReporter (ленивая инициализация)."""
    
    global _error_reporter
    
    if _error_reporter is None:
        if config is None:
            config = get_default_config()
        
        _error_reporter = ErrorReporter(config.get("reporting"))
    
    return _error_reporter


def create_error_handling_system(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Создание полной системы обработки ошибок."""
    
    if config is None:
        config = get_default_config()
    
    return {
        "error_handler": ErrorHandler(),
        "retry_manager": get_retry_manager(config),
        "circuit_breaker": get_circuit_breaker(config),
        "recovery_manager": get_recovery_manager(config),
        "error_reporter": get_error_reporter(config)
    }


# Инициализация логирования при импорте модуля
setup_logging()

# Логирование успешной инициализации
logger = logging.getLogger(__name__)
logger.info(f"Система обработки ошибок инициализирована (версия {__version__})")