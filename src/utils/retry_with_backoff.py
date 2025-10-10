#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔄 Утилита для retry с динамическим таймаутом и exponential backoff
Задача 9.2: Реализация retry_with_backoff
"""

import asyncio
import time
from typing import Callable, Any, Optional, Dict
from functools import wraps


class RetryConfig:
    """⚙️ Конфигурация retry механизма"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 2.0,
        timeout_multiplier: float = 1.5,
        exponential_base: float = 2.0,
        max_delay: float = 60.0
    ):
        """
        Args:
            max_attempts: Максимальное количество попыток (по умолчанию 3)
            base_delay: Базовая задержка между попытками в секундах (по умолчанию 2.0)
            timeout_multiplier: Множитель для увеличения таймаута (по умолчанию 1.5 = +50%)
            exponential_base: База для экспоненциального backoff (по умолчанию 2.0)
            max_delay: Максимальная задержка между попытками (по умолчанию 60.0)
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.timeout_multiplier = timeout_multiplier
        self.exponential_base = exponential_base
        self.max_delay = max_delay


async def retry_with_backoff_async(
    func: Callable,
    *args,
    initial_timeout: int = 60,
    config: Optional[RetryConfig] = None,
    logger: Optional[Any] = None,
    **kwargs
) -> Any:
    """
    🔄 Асинхронная функция retry с динамическим таймаутом и exponential backoff
    
    Логика:
    - Использует динамический таймаут
    - Увеличивает таймаут на 50% при каждой попытке
    - Exponential backoff между попытками (2, 4, 8 секунд)
    - Максимум 3 попытки
    - Логирует каждую попытку
    
    Args:
        func: Асинхронная функция для выполнения
        *args: Позиционные аргументы для функции
        initial_timeout: Начальный таймаут в секундах
        config: Конфигурация retry (опционально)
        logger: Логгер для записи попыток (опционально)
        **kwargs: Именованные аргументы для функции
    
    Returns:
        Результат выполнения функции
    
    Raises:
        Exception: Если все попытки исчерпаны
    
    Examples:
        >>> async def api_call(data):
        ...     # Вызов API
        ...     return response
        >>> 
        >>> result = await retry_with_backoff_async(
        ...     api_call,
        ...     data={'text': 'hello'},
        ...     initial_timeout=120
        ... )
    """
    if config is None:
        config = RetryConfig()
    
    current_timeout = initial_timeout
    last_error = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            if logger:
                logger.info(
                    f"🔄 Попытка {attempt}/{config.max_attempts}, таймаут: {current_timeout}с"
                )
            else:
                print(f"🔄 Попытка {attempt}/{config.max_attempts}, таймаут: {current_timeout}с")
            
            # Выполняем функцию с текущим таймаутом
            start_time = time.time()
            
            # Если функция поддерживает параметр timeout, передаём его
            if 'timeout' in kwargs or hasattr(func, '__code__') and 'timeout' in func.__code__.co_varnames:
                kwargs['timeout'] = current_timeout
            
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=current_timeout
            )
            
            elapsed_time = time.time() - start_time
            
            if logger:
                logger.info(
                    f"✅ Успешно выполнено за {elapsed_time:.2f}с (попытка {attempt})"
                )
            else:
                print(f"✅ Успешно выполнено за {elapsed_time:.2f}с (попытка {attempt})")
            
            return result
            
        except asyncio.TimeoutError as e:
            last_error = e
            elapsed_time = time.time() - start_time
            
            if logger:
                logger.warning(
                    f"⏰ Таймаут на попытке {attempt}/{config.max_attempts} "
                    f"(превышен лимит {current_timeout}с, прошло {elapsed_time:.2f}с)"
                )
            else:
                print(
                    f"⏰ Таймаут на попытке {attempt}/{config.max_attempts} "
                    f"(превышен лимит {current_timeout}с, прошло {elapsed_time:.2f}с)"
                )
            
            # Если это не последняя попытка
            if attempt < config.max_attempts:
                # Увеличиваем таймаут на 50%
                current_timeout = int(current_timeout * config.timeout_multiplier)
                
                # Вычисляем задержку с exponential backoff
                delay = min(
                    config.base_delay * (config.exponential_base ** (attempt - 1)),
                    config.max_delay
                )
                
                if logger:
                    logger.info(
                        f"⏳ Ожидание {delay:.1f}с перед следующей попыткой "
                        f"(новый таймаут: {current_timeout}с)"
                    )
                else:
                    print(
                        f"⏳ Ожидание {delay:.1f}с перед следующей попыткой "
                        f"(новый таймаут: {current_timeout}с)"
                    )
                
                await asyncio.sleep(delay)
            
        except Exception as e:
            last_error = e
            
            if logger:
                logger.error(
                    f"❌ Ошибка на попытке {attempt}/{config.max_attempts}: {type(e).__name__}: {str(e)}"
                )
            else:
                print(
                    f"❌ Ошибка на попытке {attempt}/{config.max_attempts}: {type(e).__name__}: {str(e)}"
                )
            
            # Если это не последняя попытка
            if attempt < config.max_attempts:
                # Увеличиваем таймаут на 50%
                current_timeout = int(current_timeout * config.timeout_multiplier)
                
                # Вычисляем задержку с exponential backoff
                delay = min(
                    config.base_delay * (config.exponential_base ** (attempt - 1)),
                    config.max_delay
                )
                
                if logger:
                    logger.info(
                        f"⏳ Ожидание {delay:.1f}с перед следующей попыткой "
                        f"(новый таймаут: {current_timeout}с)"
                    )
                else:
                    print(
                        f"⏳ Ожидание {delay:.1f}с перед следующей попыткой "
                        f"(новый таймаут: {current_timeout}с)"
                    )
                
                await asyncio.sleep(delay)
    
    # Все попытки исчерпаны
    error_msg = f"Все {config.max_attempts} попытки исчерпаны. Последняя ошибка: {last_error}"
    
    if logger:
        logger.error(f"❌ {error_msg}")
    else:
        print(f"❌ {error_msg}")
    
    raise Exception(error_msg)


def retry_with_backoff_sync(
    func: Callable,
    *args,
    initial_timeout: int = 60,
    config: Optional[RetryConfig] = None,
    logger: Optional[Any] = None,
    **kwargs
) -> Any:
    """
    🔄 Синхронная обёртка для retry_with_backoff_async
    
    Args:
        func: Асинхронная функция для выполнения
        *args: Позиционные аргументы для функции
        initial_timeout: Начальный таймаут в секундах
        config: Конфигурация retry (опционально)
        logger: Логгер для записи попыток (опционально)
        **kwargs: Именованные аргументы для функции
    
    Returns:
        Результат выполнения функции
    
    Examples:
        >>> async def api_call(data):
        ...     return response
        >>> 
        >>> result = retry_with_backoff_sync(
        ...     api_call,
        ...     data={'text': 'hello'},
        ...     initial_timeout=120
        ... )
    """
    return asyncio.run(
        retry_with_backoff_async(
            func,
            *args,
            initial_timeout=initial_timeout,
            config=config,
            logger=logger,
            **kwargs
        )
    )


def with_retry_backoff(
    initial_timeout: int = 60,
    config: Optional[RetryConfig] = None,
    logger: Optional[Any] = None
):
    """
    🎨 Декоратор для автоматического применения retry с backoff
    
    Args:
        initial_timeout: Начальный таймаут в секундах
        config: Конфигурация retry (опционально)
        logger: Логгер для записи попыток (опционально)
    
    Examples:
        >>> @with_retry_backoff(initial_timeout=120)
        >>> async def api_call(data):
        ...     return response
        >>> 
        >>> result = await api_call(data={'text': 'hello'})
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff_async(
                func,
                *args,
                initial_timeout=initial_timeout,
                config=config,
                logger=logger,
                **kwargs
            )
        return wrapper
    return decorator


# Вспомогательные функции для интеграции с существующим кодом

def get_retry_stats(attempts_made: int, config: RetryConfig) -> Dict[str, Any]:
    """
    📊 Получить статистику по retry попыткам
    
    Args:
        attempts_made: Количество сделанных попыток
        config: Конфигурация retry
    
    Returns:
        dict: Статистика retry
    """
    return {
        'attempts_made': attempts_made,
        'max_attempts': config.max_attempts,
        'success_rate': 1.0 if attempts_made <= config.max_attempts else 0.0,
        'retries_needed': max(0, attempts_made - 1)
    }
