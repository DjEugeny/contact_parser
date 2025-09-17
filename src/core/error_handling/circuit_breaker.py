"""Реализация паттерна Circuit Breaker для защиты от каскадных сбоев."""

import asyncio
import logging
import threading
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type
from datetime import datetime, timedelta

from .exceptions import BaseProcessingError, CircuitBreakerError


class CircuitState(Enum):
    """Состояния автомата защиты."""
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Блокировка вызовов
    HALF_OPEN = "half_open"  # Тестирование восстановления


class CircuitBreaker:
    """Автомат защиты для предотвращения каскадных сбоев."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception_types: Optional[List[Type[Exception]]] = None,
        half_open_max_calls: int = 3,
        name: str = "default"
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception_types = expected_exception_types or [Exception]
        self.half_open_max_calls = half_open_max_calls
        
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Состояние автомата
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        
        # Статистика
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_opens": 0,
            "circuit_closes": 0,
            "half_open_attempts": 0,
            "blocked_calls": 0,
            "state_changes": []
        }
        
        # Блокировка для thread-safety
        self._lock = threading.RLock()
    
    @property
    def state(self) -> CircuitState:
        """Текущее состояние автомата."""
        with self._lock:
            return self._state
    
    @property
    def failure_count(self) -> int:
        """Количество неудачных попыток."""
        with self._lock:
            return self._failure_count
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Выполнение функции через автомат защиты."""
        with self._lock:
            self.stats["total_calls"] += 1
            
            # Проверка состояния перед вызовом
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._change_state(CircuitState.HALF_OPEN)
                else:
                    self.stats["blocked_calls"] += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Calls blocked until {self._get_reset_time()}",
                        context={
                            "circuit_name": self.name,
                            "state": self._state.value,
                            "failure_count": self._failure_count,
                            "last_failure_time": self._last_failure_time
                        }
                    )
            
            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    self.stats["blocked_calls"] += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN. "
                        f"Maximum test calls ({self.half_open_max_calls}) reached",
                        context={
                            "circuit_name": self.name,
                            "state": self._state.value,
                            "half_open_calls": self._half_open_calls
                        }
                    )
                
                self._half_open_calls += 1
                self.stats["half_open_attempts"] += 1
        
        # Выполнение функции
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure(e)
            raise
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """Асинхронное выполнение функции через автомат защиты."""
        # Проверка состояния (аналогично синхронной версии)
        with self._lock:
            self.stats["total_calls"] += 1
            
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._change_state(CircuitState.HALF_OPEN)
                else:
                    self.stats["blocked_calls"] += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Calls blocked until {self._get_reset_time()}",
                        context={
                            "circuit_name": self.name,
                            "state": self._state.value,
                            "failure_count": self._failure_count
                        }
                    )
            
            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    self.stats["blocked_calls"] += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN. "
                        f"Maximum test calls reached"
                    )
                
                self._half_open_calls += 1
                self.stats["half_open_attempts"] += 1
        
        # Выполнение асинхронной функции
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _on_success(self):
        """Обработка успешного вызова."""
        with self._lock:
            self.stats["successful_calls"] += 1
            self._success_count += 1
            
            if self._state == CircuitState.HALF_OPEN:
                # Если в состоянии HALF_OPEN получили успех, закрываем автомат
                self._change_state(CircuitState.CLOSED)
                self._reset_counters()
                self.logger.info(
                    f"Circuit breaker '{self.name}' закрыт после успешного тестирования"
                )
            
            elif self._state == CircuitState.CLOSED:
                # В закрытом состоянии сбрасываем счетчик неудач при успехе
                if self._failure_count > 0:
                    self._failure_count = max(0, self._failure_count - 1)
    
    def _on_failure(self, exception: Exception):
        """Обработка неудачного вызова."""
        with self._lock:
            self.stats["failed_calls"] += 1
            
            # Проверяем, является ли исключение ожидаемым для автомата
            if not any(isinstance(exception, exc_type) for exc_type in self.expected_exception_types):
                return
            
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # В состоянии HALF_OPEN любая неудача открывает автомат
                self._change_state(CircuitState.OPEN)
                self.logger.warning(
                    f"Circuit breaker '{self.name}' открыт после неудачи в HALF_OPEN: {exception}"
                )
            
            elif self._state == CircuitState.CLOSED:
                # В закрытом состоянии открываем при превышении порога
                if self._failure_count >= self.failure_threshold:
                    self._change_state(CircuitState.OPEN)
                    self.logger.error(
                        f"Circuit breaker '{self.name}' открыт после {self._failure_count} неудач. "
                        f"Последняя ошибка: {exception}"
                    )
    
    def _should_attempt_reset(self) -> bool:
        """Проверка, можно ли попытаться сбросить автомат."""
        if self._last_failure_time is None:
            return True
        
        return time.time() - self._last_failure_time >= self.recovery_timeout
    
    def _get_reset_time(self) -> str:
        """Получение времени возможного сброса."""
        if self._last_failure_time is None:
            return "неизвестно"
        
        reset_time = self._last_failure_time + self.recovery_timeout
        return datetime.fromtimestamp(reset_time).strftime("%Y-%m-%d %H:%M:%S")
    
    def _change_state(self, new_state: CircuitState):
        """Изменение состояния автомата."""
        old_state = self._state
        self._state = new_state
        
        # Сброс счетчиков при изменении состояния
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self.stats["circuit_closes"] += 1
        elif new_state == CircuitState.OPEN:
            self.stats["circuit_opens"] += 1
        
        # Запись изменения состояния
        self.stats["state_changes"].append({
            "timestamp": datetime.now().isoformat(),
            "from_state": old_state.value,
            "to_state": new_state.value,
            "failure_count": self._failure_count
        })
        
        self.logger.info(
            f"Circuit breaker '{self.name}' изменил состояние: "
            f"{old_state.value} -> {new_state.value}"
        )
    
    def _reset_counters(self):
        """Сброс счетчиков."""
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None
    
    def force_open(self):
        """Принудительное открытие автомата."""
        with self._lock:
            self._change_state(CircuitState.OPEN)
            self.logger.warning(f"Circuit breaker '{self.name}' принудительно открыт")
    
    def force_close(self):
        """Принудительное закрытие автомата."""
        with self._lock:
            self._change_state(CircuitState.CLOSED)
            self._reset_counters()
            self.logger.info(f"Circuit breaker '{self.name}' принудительно закрыт")
    
    def force_half_open(self):
        """Принудительный переход в состояние HALF_OPEN."""
        with self._lock:
            self._change_state(CircuitState.HALF_OPEN)
            self.logger.info(f"Circuit breaker '{self.name}' переведен в HALF_OPEN")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики автомата."""
        with self._lock:
            return {
                **self.stats,
                "current_state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time,
                "next_reset_time": self._get_reset_time() if self._state == CircuitState.OPEN else None,
                "half_open_calls": self._half_open_calls,
                "config": {
                    "failure_threshold": self.failure_threshold,
                    "recovery_timeout": self.recovery_timeout,
                    "half_open_max_calls": self.half_open_max_calls,
                    "expected_exception_types": [exc.__name__ for exc in self.expected_exception_types]
                }
            }
    
    def reset_stats(self):
        """Сброс статистики."""
        with self._lock:
            self.stats = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "circuit_opens": 0,
                "circuit_closes": 0,
                "half_open_attempts": 0,
                "blocked_calls": 0,
                "state_changes": []
            }


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception_types: Optional[List[Type[Exception]]] = None,
    half_open_max_calls: int = 3,
    name: Optional[str] = None,
    breaker_instance: Optional[CircuitBreaker] = None
):
    """Декоратор для автоматической защиты функций."""
    
    def decorator(func: Callable) -> Callable:
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        breaker = breaker_instance or CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception_types=expected_exception_types,
            half_open_max_calls=half_open_max_calls,
            name=breaker_name
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        # Добавляем ссылку на автомат к функции для доступа к статистике
        wrapper.circuit_breaker = breaker
        
        return wrapper
    return decorator


def async_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception_types: Optional[List[Type[Exception]]] = None,
    half_open_max_calls: int = 3,
    name: Optional[str] = None,
    breaker_instance: Optional[CircuitBreaker] = None
):
    """Декоратор для автоматической защиты асинхронных функций."""
    
    def decorator(func: Callable) -> Callable:
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        breaker = breaker_instance or CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception_types=expected_exception_types,
            half_open_max_calls=half_open_max_calls,
            name=breaker_name
        )
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.async_call(func, *args, **kwargs)
        
        wrapper.circuit_breaker = breaker
        
        return wrapper
    return decorator