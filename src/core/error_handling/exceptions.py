"""Базовые исключения для системы обработки ошибок."""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class ErrorSeverity(Enum):
    """Уровни критичности ошибок."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Категории ошибок для классификации."""
    NETWORK = "network"
    PROCESSING = "processing"
    VALIDATION = "validation"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class BaseProcessingError(Exception):
    """Базовый класс для всех ошибок обработки."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        retry_count: int = 0
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.recoverable = recoverable
        self.retry_count = retry_count
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование ошибки в словарь для логирования."""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "recoverable": self.recoverable,
            "retry_count": self.retry_count,
            "type": self.__class__.__name__
        }


class NetworkError(BaseProcessingError):
    """Ошибки сетевого взаимодействия."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ProcessingError(BaseProcessingError):
    """Ошибки обработки данных."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ValidationError(BaseProcessingError):
    """Ошибки валидации данных."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            recoverable=False,
            **kwargs
        )


class ResourceError(BaseProcessingError):
    """Ошибки нехватки ресурсов."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ConfigurationError(BaseProcessingError):
    """Ошибки конфигурации."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            **kwargs
        )


class AuthenticationError(BaseProcessingError):
    """Ошибки аутентификации."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class TimeoutError(BaseProcessingError):
    """Ошибки таймаута."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class CircuitBreakerError(BaseProcessingError):
    """Ошибка срабатывания Circuit Breaker."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class CircuitBreakerOpenError(BaseProcessingError):
    """Ошибка при открытом состоянии Circuit Breaker."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            **kwargs
        )


class CriticalError(BaseProcessingError):
    """Критическая ошибка, требующая немедленного внимания."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            **kwargs
        )