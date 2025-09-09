#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Базовый класс для LLM провайдеров
Фаза 5: Архитектурная оптимизация
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
from .http_optimizer import OptimizedHTTPClient


@dataclass
class ProviderConfig:
    """📋 Конфигурация провайдера"""
    name: str
    api_key: str
    model: str
    base_url: str
    priority: int
    active: bool
    timeout: int = 30
    max_retries: int = 3
    headers: Optional[Dict[str, str]] = None


@dataclass
class ProviderStats:
    """📊 Статистика провайдера"""
    requests_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_tokens: int = 0
    avg_response_time: float = 0.0
    last_request_time: Optional[float] = None


class BaseProvider(ABC):
    """🔧 Базовый класс LLM провайдера"""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.stats = ProviderStats()
        self.failure_count = 0
        self.last_failure_time = None
        self.in_circuit_break = False

        # 🚀 HTTP оптимизатор (Фаза 6)
        self.http_client = OptimizedHTTPClient()

        # Настройка headers по умолчанию
        if not self.config.headers:
            self.config.headers = self._get_default_headers()

    @abstractmethod
    def _get_default_headers(self) -> Dict[str, str]:
        """📋 Получить стандартные headers для провайдера"""
        pass

    @abstractmethod
    def make_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        🚀 Выполнить запрос к LLM

        Args:
            prompt: Текст запроса
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ LLM
        """
        pass

    def is_available(self) -> bool:
        """✅ Проверить доступность провайдера"""
        if not self.config.active:
            return False

        # Проверка Circuit Breaker
        if self.in_circuit_break:
            if time.time() - (self.last_failure_time or 0) > 300:  # 5 минут
                self.in_circuit_break = False
                self.failure_count = 0
            else:
                return False

        return True

    def record_success(self, response_time: float, tokens_used: int = 0):
        """✅ Записать успешный запрос"""
        self.stats.requests_count += 1
        self.stats.success_count += 1
        self.stats.total_tokens += tokens_used
        self.stats.last_request_time = time.time()

        # Обновить среднее время ответа
        if self.stats.requests_count == 1:
            self.stats.avg_response_time = response_time
        else:
            self.stats.avg_response_time = (
                (self.stats.avg_response_time * (self.stats.requests_count - 1) + response_time)
                / self.stats.requests_count
            )

        # Сброс счетчика ошибок при успехе
        self.failure_count = 0
        self.in_circuit_break = False

    def record_failure(self, error_type: str = "unknown"):
        """❌ Записать неудачный запрос"""
        self.stats.requests_count += 1
        self.stats.error_count += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        # Активация Circuit Breaker при 5 ошибках подряд
        if self.failure_count >= 5:
            self.in_circuit_break = True

    def get_stats(self) -> Dict[str, Any]:
        """📊 Получить статистику провайдера"""
        base_stats = {
            'name': self.config.name,
            'active': self.config.active,
            'priority': self.config.priority,
            'requests_total': self.stats.requests_count,
            'success_rate': (
                self.stats.success_count / self.stats.requests_count
                if self.stats.requests_count > 0 else 0
            ),
            'avg_response_time': self.stats.avg_response_time,
            'in_circuit_break': self.in_circuit_break,
            'failure_count': self.failure_count
        }

        # 🚀 Добавляем статистику HTTP клиента (Фаза 6)
        if hasattr(self, 'http_client'):
            http_stats = self.http_client.get_performance_stats()
            base_stats['http_stats'] = {
                'total_requests': http_stats.get('requests_total', 0),
                'success_rate': http_stats.get('success_rate', 0),
                'avg_request_time': http_stats.get('avg_request_time', 0),
                'connection_pools': http_stats.get('connection_pools', {})
            }

        return base_stats

    def reset_stats(self):
        """🔄 Сбросить статистику"""
        self.stats = ProviderStats()
        self.failure_count = 0
        self.last_failure_time = None
        self.in_circuit_break = False

        # 🚀 Сброс статистики HTTP клиента (Фаза 6)
        if hasattr(self, 'http_client'):
            self.http_client.reset_stats()
