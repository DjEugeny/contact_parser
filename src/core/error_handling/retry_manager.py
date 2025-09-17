"""Менеджер повторных попыток с настраиваемыми стратегиями."""

import asyncio
import logging
import random
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime, timedelta

from .exceptions import BaseProcessingError, ErrorCategory


class BackoffStrategy(Enum):
    """Стратегии задержки между попытками."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    RANDOM = "random"


class RetryManager:
    """Менеджер повторных попыток с различными стратегиями."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or self._get_default_config()
        self.retry_stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "retries_by_strategy": {},
            "retries_by_error_type": {}
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию."""
        return {
            "max_attempts": 3,
            "base_delay": 1.0,
            "max_delay": 60.0,
            "exponential_base": 2.0,
            "jitter": True,
            "backoff_strategy": "exponential"
        }
    
    def retry(
        self,
        func: Callable,
        *args,
        max_attempts: Optional[int] = None,
        backoff_strategy: Optional[str] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        exceptions: Optional[List[Type[Exception]]] = None,
        on_retry: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Выполнение функции с повторными попытками."""
        
        # Параметры из конфигурации или переданные
        max_attempts = max_attempts or self.config.get("max_attempts", 3)
        backoff_strategy = backoff_strategy or self.config.get("backoff_strategy", "exponential")
        base_delay = base_delay or self.config.get("base_delay", 1.0)
        max_delay = max_delay or self.config.get("max_delay", 60.0)
        exceptions = exceptions or [Exception]
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                result = func(*args, **kwargs)
                
                # Обновление статистики при успехе
                if attempt > 0:
                    self.retry_stats["successful_retries"] += 1
                    self._update_retry_stats(backoff_strategy, type(last_exception).__name__, True)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Проверка, нужно ли повторять для этого типа исключения
                if not any(isinstance(e, exc_type) for exc_type in exceptions):
                    raise
                
                # Если это последняя попытка, не делаем задержку
                if attempt == max_attempts - 1:
                    self.retry_stats["failed_retries"] += 1
                    self._update_retry_stats(backoff_strategy, type(e).__name__, False)
                    raise
                
                # Обновление статистики
                self.retry_stats["total_retries"] += 1
                
                # Вызов callback при повторе
                if on_retry:
                    try:
                        on_retry(attempt + 1, e, context)
                    except Exception as callback_error:
                        self.logger.warning(f"Ошибка в callback on_retry: {callback_error}")
                
                # Вычисление задержки
                delay = self._calculate_delay(
                    attempt,
                    backoff_strategy,
                    base_delay,
                    max_delay
                )
                
                self.logger.info(
                    f"Попытка {attempt + 1}/{max_attempts} не удалась: {e}. "
                    f"Повтор через {delay:.2f} сек."
                )
                
                time.sleep(delay)
        
        # Это не должно выполниться, но на всякий случай
        raise last_exception
    
    async def async_retry(
        self,
        func: Callable,
        *args,
        max_attempts: Optional[int] = None,
        backoff_strategy: Optional[str] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        exceptions: Optional[List[Type[Exception]]] = None,
        on_retry: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Асинхронное выполнение функции с повторными попытками."""
        
        max_attempts = max_attempts or self.config.get("max_attempts", 3)
        backoff_strategy = backoff_strategy or self.config.get("backoff_strategy", "exponential")
        base_delay = base_delay or self.config.get("base_delay", 1.0)
        max_delay = max_delay or self.config.get("max_delay", 60.0)
        exceptions = exceptions or [Exception]
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                if attempt > 0:
                    self.retry_stats["successful_retries"] += 1
                    self._update_retry_stats(backoff_strategy, type(last_exception).__name__, True)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if not any(isinstance(e, exc_type) for exc_type in exceptions):
                    raise
                
                if attempt == max_attempts - 1:
                    self.retry_stats["failed_retries"] += 1
                    self._update_retry_stats(backoff_strategy, type(e).__name__, False)
                    raise
                
                self.retry_stats["total_retries"] += 1
                
                if on_retry:
                    try:
                        if asyncio.iscoroutinefunction(on_retry):
                            await on_retry(attempt + 1, e, context)
                        else:
                            on_retry(attempt + 1, e, context)
                    except Exception as callback_error:
                        self.logger.warning(f"Ошибка в async callback on_retry: {callback_error}")
                
                delay = self._calculate_delay(
                    attempt,
                    backoff_strategy,
                    base_delay,
                    max_delay
                )
                
                self.logger.info(
                    f"Асинхронная попытка {attempt + 1}/{max_attempts} не удалась: {e}. "
                    f"Повтор через {delay:.2f} сек."
                )
                
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(
        self,
        attempt: int,
        strategy: str,
        base_delay: float,
        max_delay: float
    ) -> float:
        """Вычисление задержки в зависимости от стратегии."""
        
        if strategy == BackoffStrategy.FIXED.value:
            delay = base_delay
        
        elif strategy == BackoffStrategy.LINEAR.value:
            delay = base_delay * (attempt + 1)
        
        elif strategy == BackoffStrategy.EXPONENTIAL.value:
            exponential_base = self.config.get("exponential_base", 2.0)
            delay = base_delay * (exponential_base ** attempt)
        
        elif strategy == BackoffStrategy.FIBONACCI.value:
            delay = base_delay * self._fibonacci(attempt + 1)
        
        elif strategy == BackoffStrategy.RANDOM.value:
            delay = random.uniform(base_delay, base_delay * 5)
        
        else:
            # По умолчанию экспоненциальная стратегия
            delay = base_delay * (2 ** attempt)
        
        # Ограничение максимальной задержки
        delay = min(delay, max_delay)
        
        # Добавление jitter если включено
        if self.config.get("jitter", True):
            jitter_range = delay * 0.1  # 10% от задержки
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def _fibonacci(self, n: int) -> int:
        """Вычисление числа Фибоначчи."""
        if n <= 1:
            return n
        return self._fibonacci(n - 1) + self._fibonacci(n - 2)
    
    def _update_retry_stats(
        self,
        strategy: str,
        error_type: str,
        success: bool
    ):
        """Обновление статистики повторов."""
        
        # Статистика по стратегиям
        if strategy not in self.retry_stats["retries_by_strategy"]:
            self.retry_stats["retries_by_strategy"][strategy] = {
                "total": 0,
                "successful": 0,
                "failed": 0
            }
        
        self.retry_stats["retries_by_strategy"][strategy]["total"] += 1
        if success:
            self.retry_stats["retries_by_strategy"][strategy]["successful"] += 1
        else:
            self.retry_stats["retries_by_strategy"][strategy]["failed"] += 1
        
        # Статистика по типам ошибок
        if error_type not in self.retry_stats["retries_by_error_type"]:
            self.retry_stats["retries_by_error_type"][error_type] = {
                "total": 0,
                "successful": 0,
                "failed": 0
            }
        
        self.retry_stats["retries_by_error_type"][error_type]["total"] += 1
        if success:
            self.retry_stats["retries_by_error_type"][error_type]["successful"] += 1
        else:
            self.retry_stats["retries_by_error_type"][error_type]["failed"] += 1
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """Получение статистики повторов."""
        return self.retry_stats.copy()
    
    def reset_stats(self):
        """Сброс статистики повторов."""
        self.retry_stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "retries_by_strategy": {},
            "retries_by_error_type": {}
        }


def retry(
    max_attempts: int = 3,
    backoff_strategy: str = "exponential",
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable] = None,
    retry_manager: Optional[RetryManager] = None
):
    """Декоратор для автоматических повторов."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = retry_manager or RetryManager()
            
            return manager.retry(
                func,
                *args,
                max_attempts=max_attempts,
                backoff_strategy=backoff_strategy,
                base_delay=base_delay,
                max_delay=max_delay,
                exceptions=exceptions,
                on_retry=on_retry,
                **kwargs
            )
        
        return wrapper
    return decorator


def async_retry(
    max_attempts: int = 3,
    backoff_strategy: str = "exponential",
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable] = None,
    retry_manager: Optional[RetryManager] = None
):
    """Декоратор для асинхронных автоматических повторов."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            manager = retry_manager or RetryManager()
            
            return await manager.async_retry(
                func,
                *args,
                max_attempts=max_attempts,
                backoff_strategy=backoff_strategy,
                base_delay=base_delay,
                max_delay=max_delay,
                exceptions=exceptions,
                on_retry=on_retry,
                **kwargs
            )
        
        return wrapper
    return decorator