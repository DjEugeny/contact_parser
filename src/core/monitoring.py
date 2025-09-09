#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Мониторинг и метрики производительности
Фаза 7: Тестирование и Надежность
"""

import time
import logging
import psutil
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Fallback классы для случаев, когда prometheus недоступен
    class Counter:
        def __init__(self, name, description, labelnames=None):
            self.name = name
            self.description = description
            self.labelnames = labelnames or []
            self._value = 0

        def labels(self, **kwargs):
            return self

        def inc(self, value=1):
            self._value += value

        @property
        def _samples(self):
            return []

    class Histogram:
        def __init__(self, name, description, labelnames=None, buckets=None):
            self.name = name
            self.description = description
            self.labelnames = labelnames or []
            self._sum = 0
            self._count = 0

        def labels(self, **kwargs):
            return self

        def observe(self, value):
            self._sum += value
            self._count += 1

    class Gauge:
        def __init__(self, name, description, labelnames=None):
            self.name = name
            self.description = description
            self.labelnames = labelnames or []
            self._value = 0

        def set(self, value):
            self._value = value

        def inc(self, value=1):
            self._value += value

        def dec(self, value=1):
            self._value -= value


class LLMMetricsCollector:
    """
    📊 Сборщик метрик для LLM операций

    Собирает и предоставляет метрики:
    - Количество запросов по провайдерам
    - Время ответа API
    - Использование токенов
    - Стоимость API запросов
    - Успешность запросов
    """

    def __init__(self):
        # Создаем registry для Prometheus
        self.registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None

        # Метрики по провайдерам
        self.provider_requests = Counter(
            'llm_provider_requests_total',
            'Total requests to LLM providers',
            ['provider', 'status'],
            registry=self.registry
        )

        # Время ответа API
        self.request_duration = Histogram(
            'llm_request_duration_seconds',
            'Request duration to LLM providers',
            ['provider'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )

        # Использование токенов
        self.tokens_used = Counter(
            'llm_tokens_used_total',
            'Total tokens used by LLM providers',
            ['provider', 'operation'],
            registry=self.registry
        )

        # Стоимость API
        self.api_cost = Counter(
            'llm_api_cost_usd_total',
            'Total API cost in USD',
            ['provider'],
            registry=self.registry
        )

        # Активные соединения
        self.active_connections = Gauge(
            'llm_active_connections',
            'Number of active connections',
            ['provider'],
            registry=self.registry
        )

        # Ошибки по типам
        self.errors_by_type = Counter(
            'llm_errors_total',
            'Errors by type',
            ['provider', 'error_type'],
            registry=self.registry
        )

        # Статистика кэширования
        self.cache_hits = Counter(
            'llm_cache_hits_total',
            'Cache hits',
            ['cache_type'],
            registry=self.registry
        )

        self.cache_misses = Counter(
            'llm_cache_misses_total',
            'Cache misses',
            ['cache_type'],
            registry=self.registry
        )

        # Системные метрики
        self.memory_usage = Gauge(
            'system_memory_mb',
            'System memory usage in MB',
            registry=self.registry
        )

        self.cpu_usage = Gauge(
            'system_cpu_percent',
            'System CPU usage percent',
            registry=self.registry
        )

        # История метрик
        self.metrics_history = []
        self.max_history_size = 1000

        # Настройка логирования
        self.logger = logging.getLogger(__name__)

        self.logger.info("📊 LLMMetricsCollector инициализирован")

    def record_request(self, provider: str, duration: float,
                      tokens: int = 0, cost: float = 0.0,
                      status: str = 'success', error_type: str = None):
        """
        📝 Запись метрик запроса

        Args:
            provider: Имя провайдера
            duration: Время выполнения в секундах
            tokens: Количество использованных токенов
            cost: Стоимость запроса в USD
            status: Статус запроса ('success', 'error', 'timeout')
            error_type: Тип ошибки (если есть)
        """
        # Основные метрики
        self.provider_requests.labels(provider=provider, status=status).inc()
        self.request_duration.labels(provider=provider).observe(duration)

        # Токены и стоимость
        if tokens > 0:
            self.tokens_used.labels(provider=provider, operation='extraction').inc(tokens)

        if cost > 0:
            self.api_cost.labels(provider=provider).inc(cost)

        # Ошибки
        if error_type:
            self.errors_by_type.labels(provider=provider, error_type=error_type).inc()

        # Системные метрики
        try:
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            cpu_percent = psutil.Process().cpu_percent()

            self.memory_usage.set(memory_mb)
            self.cpu_usage.set(cpu_percent)
        except Exception as e:
            self.logger.warning(f"Не удалось собрать системные метрики: {e}")

        # Логирование
        self.logger.info(".2f"
                        f"tokens={tokens}, cost=${cost:.4f}, status={status}")

        # Сохранение в историю
        self._add_to_history({
            'timestamp': time.time(),
            'provider': provider,
            'duration': duration,
            'tokens': tokens,
            'cost': cost,
            'status': status,
            'error_type': error_type
        })

    def record_cache_hit(self, cache_type: str = 'llm_response'):
        """💾 Запись попадания в кэш"""
        self.cache_hits.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str = 'llm_response'):
        """❌ Запись промаха кэша"""
        self.cache_misses.labels(cache_type=cache_type).inc()

    def set_active_connections(self, provider: str, count: int):
        """🔗 Установка количества активных соединений"""
        self.active_connections.labels(provider=provider).set(count)

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        📊 Получение сводной статистики

        Returns:
            Dict с основными метриками
        """
        # Вычисляем агрегированные метрики
        total_requests = sum(
            sample.value for sample in self.provider_requests._samples
        ) if hasattr(self.provider_requests, '_samples') else 0

        total_tokens = sum(
            sample.value for sample in self.tokens_used._samples
        ) if hasattr(self.tokens_used, '_samples') else 0

        total_cost = sum(
            sample.value for sample in self.api_cost._samples
        ) if hasattr(self.api_cost, '_samples') else 0

        # Среднее время ответа
        avg_response_time = (
            self.request_duration._sum / self.request_duration._count
            if self.request_duration._count > 0 else 0
        )

        return {
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'total_cost_usd': total_cost,
            'avg_response_time': avg_response_time,
            'cache_hit_rate': self._calculate_cache_hit_rate(),
            'error_rate': self._calculate_error_rate(),
            'system_memory_mb': self.memory_usage._value if hasattr(self.memory_usage, '_value') else 0,
            'system_cpu_percent': self.cpu_usage._value if hasattr(self.cpu_usage, '_value') else 0
        }

    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        📊 Получение статистики по провайдерам

        Returns:
            Dict с метриками по каждому провайдеру
        """
        providers = ['openrouter', 'groq', 'replicate']
        stats = {}

        for provider in providers:
            # Запросы
            provider_requests = sum(
                sample.value for sample in self.provider_requests._samples
                if sample.labels.get('provider') == provider
            ) if hasattr(self.provider_requests, '_samples') else 0

            # Успешные запросы
            successful_requests = sum(
                sample.value for sample in self.provider_requests._samples
                if sample.labels.get('provider') == provider and sample.labels.get('status') == 'success'
            ) if hasattr(self.provider_requests, '_samples') else 0

            # Токены
            provider_tokens = sum(
                sample.value for sample in self.tokens_used._samples
                if sample.labels.get('provider') == provider
            ) if hasattr(self.tokens_used, '_samples') else 0

            # Стоимость
            provider_cost = sum(
                sample.value for sample in self.api_cost._samples
                if sample.labels.get('provider') == provider
            ) if hasattr(self.api_cost, '_samples') else 0

            stats[provider] = {
                'total_requests': provider_requests,
                'successful_requests': successful_requests,
                'success_rate': (successful_requests / provider_requests * 100) if provider_requests > 0 else 0,
                'total_tokens': provider_tokens,
                'total_cost_usd': provider_cost
            }

        return stats

    def export_metrics(self, format: str = 'json') -> str:
        """
        📤 Экспорт метрик в различных форматах

        Args:
            format: Формат экспорта ('json', 'prometheus')

        Returns:
            str: Метрики в указанном формате
        """
        if format == 'json':
            return json.dumps({
                'summary': self.get_summary_stats(),
                'providers': self.get_provider_stats(),
                'history': self.metrics_history[-100:],  # Последние 100 записей
                'timestamp': datetime.now().isoformat()
            }, indent=2, ensure_ascii=False)

        elif format == 'prometheus' and PROMETHEUS_AVAILABLE:
            from prometheus_client import generate_latest
            return generate_latest(self.registry).decode('utf-8')

        else:
            return "Формат не поддерживается или Prometheus недоступен"

    def save_metrics_to_file(self, file_path: Optional[Path] = None):
        """
        💾 Сохранение метрик в файл

        Args:
            file_path: Путь к файлу (по умолчанию metrics.json)
        """
        if not file_path:
            file_path = Path('metrics.json')

        try:
            metrics_data = self.export_metrics('json')

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(metrics_data)

            self.logger.info(f"💾 Метрики сохранены в {file_path}")

        except Exception as e:
            self.logger.error(f"Ошибка сохранения метрик: {e}")

    def _calculate_cache_hit_rate(self) -> float:
        """Вычисление процента попаданий в кэш"""
        total_cache_requests = 0
        cache_hits = 0

        # Суммируем по всем типам кэша
        for sample in self.cache_hits._samples:
            cache_hits += sample.value
            total_cache_requests += sample.value

        for sample in self.cache_misses._samples:
            total_cache_requests += sample.value

        return (cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0

    def _calculate_error_rate(self) -> float:
        """Вычисление процента ошибок"""
        total_requests = sum(
            sample.value for sample in self.provider_requests._samples
        ) if hasattr(self.provider_requests, '_samples') else 0

        error_requests = sum(
            sample.value for sample in self.provider_requests._samples
            if sample.labels.get('status') != 'success'
        ) if hasattr(self.provider_requests, '_samples') else 0

        return (error_requests / total_requests * 100) if total_requests > 0 else 0

    def _add_to_history(self, record: Dict[str, Any]):
        """Добавление записи в историю"""
        self.metrics_history.append(record)

        # Ограничиваем размер истории
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]

    def reset_metrics(self):
        """🔄 Сброс всех метрик"""
        # Сброс счетчиков (в реальном Prometheus это не сработает)
        self.logger.info("🔄 Сброс метрик выполнен (симуляция)")

        # Очистка истории
        self.metrics_history.clear()

    def get_health_status(self) -> Dict[str, Any]:
        """
        🏥 Проверка статуса здоровья системы

        Returns:
            Dict со статусом компонентов
        """
        summary = self.get_summary_stats()

        # Определяем статус на основе метрик
        health_status = {
            'overall': 'healthy',
            'components': {
                'api_response_time': 'healthy' if summary['avg_response_time'] < 10 else 'warning',
                'error_rate': 'healthy' if self._calculate_error_rate() < 5 else 'critical',
                'cache_hit_rate': 'healthy' if self._calculate_cache_hit_rate() > 30 else 'warning',
                'memory_usage': 'healthy' if summary['system_memory_mb'] < 1000 else 'warning'
            },
            'metrics': summary,
            'last_check': datetime.now().isoformat()
        }

        # Определяем общий статус
        if any(status == 'critical' for status in health_status['components'].values()):
            health_status['overall'] = 'critical'
        elif any(status == 'warning' for status in health_status['components'].values()):
            health_status['overall'] = 'warning'

        return health_status
