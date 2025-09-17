#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Унифицированный менеджер конфигурации
Фаза 5: Архитектурная оптимизация + Критические исправления
"""

import os
import json
import time
import logging
import random
import asyncio
import aiohttp
import structlog
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict, field
from dotenv import load_dotenv
from datetime import datetime, timedelta
from enum import Enum
from statistics import mean, median


@dataclass
class LLMProviderConfig:
    """📋 Конфигурация LLM провайдера"""
    name: str
    api_key: str
    model: str
    base_url: str
    priority: int
    active: bool
    max_retries: int = 3
    timeout: int = 30


@dataclass
class ProcessingConfig:
    """⚙️ Конфигурация обработки"""
    start_date: str = "2025-07-28"
    end_date: str = "2025-08-11"
    skip_processed: bool = True
    max_parallel: int = 3
    use_token_based_chunking: bool = True
    max_tokens_per_chunk: int = 4000
    overlap_tokens: int = 400


@dataclass
class ExportConfig:
    """📊 Конфигурация экспорта"""
    google_sheet_id: str = ""
    google_sheet_name: str = "CRM_from_Mail"
    confidence_threshold: float = 0.6
    data_dir: str = "data"


@dataclass
class RetryConfig:
    """⚙️ Конфигурация повторных попыток"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


class CircuitBreakerState(Enum):
    """🔄 Состояния Circuit Breaker"""
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Провайдер заблокирован
    HALF_OPEN = "half_open" # Тестирование восстановления


@dataclass
class CircuitBreakerConfig:
    """⚙️ Конфигурация Circuit Breaker"""
    failure_threshold: int = 5          # Количество ошибок для открытия
    recovery_timeout: int = 60          # Время до попытки восстановления (сек)
    half_open_max_calls: int = 3        # Максимум вызовов в half-open состоянии
    success_threshold: int = 2          # Успехов для закрытия circuit breaker


@dataclass
class ProviderMetrics:
    """📊 Детальные метрики провайдера"""
    response_times: List[float] = field(default_factory=list)  # Время ответа в секундах
    token_usage: List[int] = field(default_factory=list)       # Использование токенов
    error_types: Dict[str, int] = field(default_factory=dict)  # Типы ошибок
    success_rate: float = 0.0                                  # Процент успеха
    last_success: Optional[datetime] = None                    # Время последнего успеха
    avg_response_time: float = 0.0                            # Среднее время ответа
    median_response_time: float = 0.0                         # Медианное время ответа
    total_tokens_used: int = 0                                # Общее использование токенов
    requests_per_minute: float = 0.0                          # Запросов в минуту
    
    def update_response_time(self, response_time: float):
        """Обновить метрики времени ответа"""
        self.response_times.append(response_time)
        # Ограничиваем историю последними 100 запросами
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
        
        if self.response_times:
            self.avg_response_time = mean(self.response_times)
            self.median_response_time = median(self.response_times)
    
    def update_token_usage(self, tokens: int):
        """Обновить метрики использования токенов"""
        self.token_usage.append(tokens)
        self.total_tokens_used += tokens
        # Ограничиваем историю последними 100 запросами
        if len(self.token_usage) > 100:
            self.token_usage = self.token_usage[-100:]
    
    def record_error_type(self, error_type: str):
        """Записать тип ошибки"""
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
    
    @property
    def avg_tokens_per_request(self) -> float:
        """Среднее количество токенов на запрос"""
        if not self.token_usage:
            return 0.0
        return mean(self.token_usage)


@dataclass
class ProviderStats:
    """📊 Статистика использования провайдера"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_errors: int = 0
    last_request_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    last_error: Optional[str] = None
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    circuit_breaker_opened_at: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    cooldown_until: Optional[datetime] = None
    metrics: ProviderMetrics = field(default_factory=ProviderMetrics)  # Расширенные метрики
    priority_score: float = 1.0  # Динамический приоритет на основе производительности


@dataclass
class FallbackConfig:
    """⚙️ Конфигурация системы Fallback"""
    enabled: bool = True
    max_fallback_attempts: int = 3
    fallback_delay: float = 1.0
    provider_priority: List[str] = field(default_factory=lambda: ["openai", "anthropic", "groq", "ollama"])


class UnifiedConfigManager:
    """🎛️ Унифицированный менеджер конфигурации"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self._env_loaded = False
        self._config_cache: Dict[str, Any] = {}
        
        # 🔧 Критические компоненты
        self.fallback_config = FallbackConfig()
        self.circuit_breaker_config = CircuitBreakerConfig()
        self.provider_stats: Dict[str, ProviderStats] = {}
        self.circuit_breaker_states: Dict[str, str] = {}  # Состояния circuit breaker для провайдеров
        self.retry_config = RetryConfig()
        
        # 🔧 Инициализированные провайдеры
        self.providers: Dict[str, Any] = {}  # Будет содержать объекты провайдеров
        
        # 📊 Структурированное логирование
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        self.logger = structlog.get_logger(__name__)
        self.std_logger = logging.getLogger(__name__)  # Для обратной совместимости
        
        # 🎯 Адаптивные пороги Circuit Breaker
        self.adaptive_thresholds = {
            "failure_threshold_min": 3,
            "failure_threshold_max": 10,
            "recovery_timeout_min": 30,
            "recovery_timeout_max": 300
        }
        
        self._initialize_provider_stats()
        self._initialize_providers()

    def _ensure_env_loaded(self):
        """🔧 Гарантирует загрузку переменных окружения"""
        if not self._env_loaded:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent.parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                self._env_loaded = True
                print("✅ Переменные окружения загружены из .env")
            else:
                print("⚠️  Файл .env не найден")

    def get_llm_providers(self) -> List[LLMProviderConfig]:
        """
        🤖 Получить конфигурацию всех LLM провайдеров из .env

        Приоритеты:
        1. Replicate (самый быстрый)
        2. OpenRouter (хороший баланс)
        3. Groq (резервный)
        """
        self._ensure_env_loaded()

        providers = []

        # Replicate - приоритет 1 (самый быстрый)
        if replicate_key := os.getenv('REPLICATE_API_KEY'):
            providers.append(LLMProviderConfig(
                name="Replicate",
                api_key=replicate_key,
                model=os.getenv('REPLICATE_MODEL', 'meta/llama-3.1-8b-instant'),
                base_url="https://api.replicate.com/v1/predictions",
                priority=1,
                active=True
            ))

        # OpenRouter - приоритет 2
        if openrouter_key := os.getenv('OPENROUTER_API_KEY'):
            providers.append(LLMProviderConfig(
                name="OpenRouter",
                api_key=openrouter_key,
                model=os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-235b-a22b:free'),
                base_url=os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1/chat/completions'),
                priority=2,
                active=True
            ))

        # Groq - приоритет 3 (резервный) - ВРЕМЕННО ОТКЛЮЧЕН
        # if groq_key := os.getenv('GROQ_API_KEY'):
        #     providers.append(LLMProviderConfig(
        #         name="Groq",
        #         api_key=groq_key,
        #         model=os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant'),
        #         base_url=os.getenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1/chat/completions'),
        #         priority=3,
        #         active=True
        #     ))

        # Сортировка по приоритету (выше приоритет - раньше в списке)
        providers.sort(key=lambda p: p.priority)

        print(f"🎛️ Загружено {len(providers)} LLM провайдеров из .env")
        for provider in providers:
            print(f"   {provider.priority}. {provider.name} ({provider.model})")

        return providers

    def get_processing_config(self) -> ProcessingConfig:
        """⚙️ Получить конфигурацию обработки"""
        self._ensure_env_loaded()

        # Сначала пробуем загрузить из processing_config.json
        config_path = self.config_dir / "processing_config.json"
        config_data = {}

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                print("✅ Загружена конфигурация обработки из processing_config.json")
            except Exception as e:
                print(f"⚠️  Ошибка загрузки processing_config.json: {e}")

        # Объединяем с переменными окружения (.env имеет приоритет)
        processing_config = ProcessingConfig()

        # Даты из .env или JSON
        processing_config.start_date = os.getenv('TEST_START_DATE',
            config_data.get('date_range', {}).get('start_date', processing_config.start_date))
        processing_config.end_date = os.getenv('TEST_END_DATE',
            config_data.get('date_range', {}).get('end_date', processing_config.end_date))

        # Настройки обработки
        processing_config.skip_processed = config_data.get('processing', {}).get('skip_processed',
            processing_config.skip_processed)
        processing_config.max_parallel = config_data.get('processing', {}).get('max_parallel',
            processing_config.max_parallel)

        # Настройки chunking
        chunking = config_data.get('chunking', {})
        processing_config.use_token_based_chunking = chunking.get('use_token_based',
            processing_config.use_token_based_chunking)
        processing_config.max_tokens_per_chunk = chunking.get('max_tokens_per_chunk',
            processing_config.max_tokens_per_chunk)
        processing_config.overlap_tokens = chunking.get('overlap_tokens',
            processing_config.overlap_tokens)

        return processing_config

    def get_export_config(self) -> ExportConfig:
        """📊 Получить конфигурацию экспорта"""
        self._ensure_env_loaded()

        config = ExportConfig()

        # Google Sheets настройки из .env
        config.google_sheet_id = os.getenv('GOOGLE_SHEET_ID', config.google_sheet_id)
        config.google_sheet_name = os.getenv('GOOGLE_SHEET_NAME', config.google_sheet_name)
        config.confidence_threshold = float(os.getenv('CONFIDENCE_REVIEW_THRESHOLD', config.confidence_threshold))
        config.data_dir = os.getenv('DATA_DIR', config.data_dir)

        return config

    def get_imap_config(self) -> Dict[str, Any]:
        """📧 Получить IMAP конфигурацию"""
        self._ensure_env_loaded()

        return {
            'server': os.getenv('IMAP_SERVER', ''),
            'port': int(os.getenv('IMAP_PORT', '143')),
            'user': os.getenv('IMAP_USER', ''),
            'password': os.getenv('IMAP_PASSWORD', ''),
            'use_ssl': os.getenv('IMAP_SSL', 'false').lower() == 'true'
        }

    def get_retry_config(self) -> Dict[str, Any]:
        """🔄 Получить конфигурацию повторных попыток"""
        self._ensure_env_loaded()

        return {
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
            'retry_delay': float(os.getenv('RETRY_DELAY', '1')),
            'rate_delay': float(os.getenv('RATE_DELAY', '1.2')),
            'retry_max': int(os.getenv('RETRY_MAX', '6')),
            'retry_base': float(os.getenv('RETRY_BASE', '1.6')),
            'retry_jitter': float(os.getenv('RETRY_JITTER', '0.4')),
            'fallback_to_replicate': os.getenv('FALLBACK_TO_REPLICATE', 'true').lower() == 'true'
        }

    def validate_configuration(self) -> Dict[str, Any]:
        """
        ✅ Валидация всей конфигурации

        Returns:
            Dict с результатами валидации
        """
        self._ensure_env_loaded()

        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'providers': {},
            'configs': {}
        }

        # Валидация провайдеров
        providers = self.get_llm_providers()
        if not providers:
            results['valid'] = False
            results['errors'].append("Не найдено ни одного активного LLM провайдера")

        results['providers']['count'] = len(providers)
        results['providers']['available'] = [p.name for p in providers]

        # Валидация IMAP
        imap_config = self.get_imap_config()
        if not imap_config['server'] or not imap_config['user']:
            results['warnings'].append("IMAP конфигурация неполная")

        # Валидация экспорта
        export_config = self.get_export_config()
        if not export_config.google_sheet_id:
            results['warnings'].append("Google Sheet ID не задан")

        results['configs']['imap'] = bool(imap_config['server'])
        results['configs']['export'] = bool(export_config.google_sheet_id)

        return results

    def print_config_summary(self):
        """📋 Вывести сводку по конфигурации"""
        print("\n🎛️ СВОДКА КОНФИГУРАЦИИ")
        print("=" * 50)

        # Провайдеры
        providers = self.get_llm_providers()
        print(f"🤖 LLM Провайдеры: {len(providers)}")
        for provider in providers:
            print(f"   {provider.priority}. {provider.name}: {provider.model}")

        # Обработка
        processing = self.get_processing_config()
        print(f"\n⚙️  Обработка: {processing.start_date} - {processing.end_date}")
        print(f"   Параллельность: {processing.max_parallel}")
        print(f"   Chunking: {processing.max_tokens_per_chunk} токенов")

        # Экспорт
        export = self.get_export_config()
        print(f"\n📊 Экспорт: {export.google_sheet_name}")
        print(f"   Confidence threshold: {export.confidence_threshold}")

        # IMAP
        imap = self.get_imap_config()
        if imap['server']:
            print(f"\n📧 IMAP: {imap['server']}:{imap['port']}")
        else:
            print("\n📧 IMAP: не настроен")

    def _initialize_provider_stats(self):
        """📊 Инициализация статистики провайдеров"""
        providers = self.get_llm_providers()
        for provider in providers:
            if provider.name not in self.provider_stats:
                self.provider_stats[provider.name] = ProviderStats()
                self.logger.info(f"📊 Инициализирована статистика для провайдера: {provider.name}")

    def _initialize_providers(self):
        """🔧 Инициализация объектов провайдеров"""
        from ..providers.replicate import ReplicateProvider
        from ..providers.groq import GroqProvider
        from ..providers.openrouter import OpenRouterProvider
        
        provider_classes = {
            'Replicate': ReplicateProvider,
            'Groq': GroqProvider,
            'OpenRouter': OpenRouterProvider
        }
        
        providers_config = self.get_llm_providers()
        for provider_config in providers_config:
            if provider_config.active and provider_config.name in provider_classes:
                try:
                    # Преобразуем LLMProviderConfig в ProviderConfig для базового провайдера
                    from ..providers.base_provider import ProviderConfig
                    base_config = ProviderConfig(
                        name=provider_config.name,
                        api_key=provider_config.api_key,
                        model=provider_config.model,
                        base_url=provider_config.base_url,
                        priority=provider_config.priority,
                        active=provider_config.active,
                        timeout=provider_config.timeout,
                        max_retries=provider_config.max_retries
                    )
                    
                    provider_class = provider_classes[provider_config.name]
                    self.providers[provider_config.name] = provider_class(base_config)
                    self.logger.info(f"🔧 Инициализирован провайдер: {provider_config.name}")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка инициализации провайдера {provider_config.name}: {e}")
                    continue

    def is_provider_available(self, provider_name: str) -> bool:
        """🔍 Проверка доступности провайдера через Circuit Breaker"""
        if provider_name not in self.provider_stats:
            return True
        
        stats = self.provider_stats[provider_name]
        now = datetime.now()
        
        # Проверка cooldown
        if stats.cooldown_until and now < stats.cooldown_until:
            return False
        
        # Логика Circuit Breaker
        if stats.circuit_breaker_state == CircuitBreakerState.OPEN:
            if stats.circuit_breaker_opened_at:
                time_since_open = (now - stats.circuit_breaker_opened_at).total_seconds()
                if time_since_open >= self.circuit_breaker_config.recovery_timeout:
                    # Переход в HALF_OPEN
                    stats.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                    stats.consecutive_successes = 0
                    self.logger.info(f"🔄 Circuit Breaker для {provider_name} переведен в HALF_OPEN")
                    return True
                return False
        
        return stats.circuit_breaker_state != CircuitBreakerState.OPEN

    def record_provider_success(self, provider_name: str):
        """✅ Записать успешный запрос к провайдеру"""
        if provider_name not in self.provider_stats:
            self.provider_stats[provider_name] = ProviderStats()
        
        stats = self.provider_stats[provider_name]
        stats.total_requests += 1
        stats.successful_requests += 1
        stats.consecutive_failures = 0
        stats.consecutive_successes += 1
        stats.last_request_time = datetime.now()
        
        # Логика Circuit Breaker для восстановления
        if stats.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
            if stats.consecutive_successes >= self.circuit_breaker_config.success_threshold:
                stats.circuit_breaker_state = CircuitBreakerState.CLOSED
                stats.circuit_breaker_opened_at = None
                self.logger.info(f"✅ Circuit Breaker для {provider_name} закрыт (восстановлен)")

    def record_provider_failure(self, provider_name: str, error: str, is_rate_limit: bool = False):
        """❌ Записать ошибку провайдера"""
        if provider_name not in self.provider_stats:
            self.provider_stats[provider_name] = ProviderStats()
        
        stats = self.provider_stats[provider_name]
        stats.total_requests += 1
        stats.failed_requests += 1
        stats.consecutive_successes = 0
        stats.consecutive_failures += 1
        stats.last_request_time = datetime.now()
        stats.last_error_time = datetime.now()
        stats.last_error = error
        
        if is_rate_limit:
            stats.rate_limit_errors += 1
            # Установка cooldown для rate limit
            stats.cooldown_until = datetime.now() + timedelta(seconds=60)
            self.logger.warning(f"⏳ Rate limit для {provider_name}, cooldown до {stats.cooldown_until}")
        
        # Логика Circuit Breaker
        if stats.consecutive_failures >= self.circuit_breaker_config.failure_threshold:
            if stats.circuit_breaker_state == CircuitBreakerState.CLOSED:
                stats.circuit_breaker_state = CircuitBreakerState.OPEN
                stats.circuit_breaker_opened_at = datetime.now()
                self.logger.error(f"🚨 Circuit Breaker для {provider_name} открыт после {stats.consecutive_failures} ошибок")

    def get_next_available_provider(self, exclude_providers: List[str] = None) -> Optional[LLMProviderConfig]:
        """🔄 Получить следующий доступный провайдер по приоритету"""
        if not self.fallback_config.enabled:
            return None
        
        exclude_providers = exclude_providers or []
        providers = self.get_llm_providers()
        
        for provider in providers:
            if provider.name in exclude_providers:
                continue
            
            if self.is_provider_available(provider.name):
                return provider
        
        return None

    def get_provider_stats_summary(self) -> Dict[str, Dict[str, Any]]:
        """📊 Получить сводку статистики всех провайдеров"""
        summary = {}
        for provider_name, stats in self.provider_stats.items():
            success_rate = (stats.successful_requests / stats.total_requests * 100) if stats.total_requests > 0 else 0
            
            summary[provider_name] = {
                "total_requests": stats.total_requests,
                "success_rate": round(success_rate, 2),
                "failed_requests": stats.failed_requests,
                "rate_limit_errors": stats.rate_limit_errors,
                "circuit_breaker_state": stats.circuit_breaker_state.value,
                "consecutive_failures": stats.consecutive_failures,
                "last_error": stats.last_error,
                "is_available": self.is_provider_available(provider_name)
            }
        
        return summary
    
    # 📊 РАСШИРЕННАЯ СИСТЕМА МЕТРИК
    
    def get_provider_metrics_summary(self, provider_name: str) -> Dict[str, Any]:
        """📊 Подробная сводка метрик провайдера"""
        if provider_name not in self.provider_stats:
            return {
                "provider": provider_name,
                "status": "no_data",
                "message": "No metrics available for this provider"
            }
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        # Вычисляем дополнительные метрики
        success_rate = stats.successful_requests / max(1, stats.total_requests)
        failure_rate = stats.failed_requests / max(1, stats.total_requests)
        
        # Анализ производительности
        performance_score = self._calculate_performance_score(provider_name)
        reliability_score = self._calculate_reliability_score(provider_name)
        
        return {
            "provider": provider_name,
            "status": "active" if stats.total_requests > 0 else "inactive",
            "performance": {
                "response_time": {
                    "avg": round(metrics.avg_response_time, 3),
                    "min": round(metrics.min_response_time, 3),
                    "max": round(metrics.max_response_time, 3),
                    "samples": len(metrics.response_times)
                },
                "token_usage": {
                    "total": metrics.total_tokens_used,
                    "avg_per_request": round(metrics.avg_tokens_per_request, 2),
                    "efficiency_score": self._calculate_token_efficiency(provider_name)
                },
                "performance_score": round(performance_score, 3)
            },
            "reliability": {
                "success_rate": round(success_rate, 3),
                "failure_rate": round(failure_rate, 3),
                "consecutive_failures": stats.consecutive_failures,
                "reliability_score": round(reliability_score, 3),
                "uptime_percentage": self._calculate_uptime_percentage(provider_name)
            },
            "requests": {
                "total": stats.total_requests,
                "successful": stats.successful_requests,
                "failed": stats.failed_requests,
                "last_request": stats.last_request_time.isoformat() if stats.last_request_time else None,
                "last_success": metrics.last_success.isoformat() if metrics.last_success else None,
                "last_failure": stats.last_failure_time.isoformat() if stats.last_failure_time else None
            },
            "errors": {
                "types": dict(metrics.error_types),
                "most_common_error": self._get_most_common_error(provider_name),
                "error_trend": self._analyze_error_trend(provider_name)
            },
            "priority": {
                "current_score": round(stats.priority_score, 3),
                "rank": self._get_provider_rank(provider_name)
            }
        }
    
    def get_all_metrics_summary(self) -> Dict[str, Any]:
        """📊 Сводка метрик всех провайдеров"""
        providers = self.get_llm_providers()
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_providers": len(providers),
            "active_providers": 0,
            "available_providers": 0,
            "overall_stats": {
                "total_requests": 0,
                "total_successful": 0,
                "total_failed": 0,
                "avg_response_time": 0,
                "total_tokens_used": 0
            },
            "providers": {},
            "rankings": {
                "by_performance": [],
                "by_reliability": [],
                "by_priority": []
            }
        }
        
        total_response_time = 0
        active_providers_count = 0
        
        for provider in providers:
            provider_summary = self.get_provider_metrics_summary(provider.name)
            summary["providers"][provider.name] = provider_summary
            
            if provider_summary["status"] == "active":
                summary["active_providers"] += 1
                active_providers_count += 1
                
                # Агрегируем статистику
                requests = provider_summary["requests"]
                performance = provider_summary["performance"]
                
                summary["overall_stats"]["total_requests"] += requests["total"]
                summary["overall_stats"]["total_successful"] += requests["successful"]
                summary["overall_stats"]["total_failed"] += requests["failed"]
                summary["overall_stats"]["total_tokens_used"] += performance["token_usage"]["total"]
                
                total_response_time += performance["response_time"]["avg"]
            
            if self.is_provider_available(provider.name):
                summary["available_providers"] += 1
        
        # Вычисляем средние значения
        if active_providers_count > 0:
            summary["overall_stats"]["avg_response_time"] = round(total_response_time / active_providers_count, 3)
        
        # Создаем рейтинги
        summary["rankings"] = self._create_provider_rankings()
        
        return summary
    
    def export_metrics_to_json(self, filepath: str = None) -> str:
        """📤 Экспорт метрик в JSON файл"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"provider_metrics_{timestamp}.json"
        
        metrics_data = {
            "export_timestamp": datetime.now().isoformat(),
            "config_summary": {
                "retry_config": {
                    "max_attempts": self.retry_config.max_attempts,
                    "base_delay": self.retry_config.base_delay,
                    "max_delay": self.retry_config.max_delay
                },
                "circuit_breaker_config": {
                    "failure_threshold": self.circuit_breaker_config.failure_threshold,
                    "recovery_timeout": self.circuit_breaker_config.recovery_timeout
                },
                "adaptive_thresholds": self.adaptive_thresholds
            },
            "metrics": self.get_all_metrics_summary(),
            "circuit_breaker_summary": self.get_circuit_breaker_summary()
        }
        
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info("metrics_exported",
                        filepath=filepath,
                        providers_count=len(self.get_llm_providers()))
        
        return filepath
    
    def analyze_provider_performance_trends(self, provider_name: str, hours: int = 24) -> Dict[str, Any]:
        """📈 Анализ трендов производительности провайдера за период"""
        if provider_name not in self.provider_stats:
            return {"error": "Provider not found"}
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        # Анализируем тренды (упрощенная версия)
        analysis = {
            "provider": provider_name,
            "analysis_period_hours": hours,
            "timestamp": datetime.now().isoformat(),
            "trends": {
                "response_time": {
                    "current_avg": round(metrics.avg_response_time, 3),
                    "trend": "stable",  # В реальной реализации здесь был бы анализ временных рядов
                    "recommendation": self._get_response_time_recommendation(metrics.avg_response_time)
                },
                "reliability": {
                    "current_success_rate": round(stats.successful_requests / max(1, stats.total_requests), 3),
                    "trend": "stable",
                    "recommendation": self._get_reliability_recommendation(provider_name)
                },
                "token_efficiency": {
                    "avg_tokens_per_request": round(metrics.avg_tokens_per_request, 2),
                    "efficiency_score": self._calculate_token_efficiency(provider_name),
                    "recommendation": self._get_efficiency_recommendation(provider_name)
                }
            },
            "alerts": self._generate_performance_alerts(provider_name),
            "recommendations": self._generate_optimization_recommendations(provider_name)
        }
        
        return analysis
    
    # 🔧 ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ МЕТРИК
    
    def _calculate_performance_score(self, provider_name: str) -> float:
        """🔧 Вычисление общего балла производительности"""
        if provider_name not in self.provider_stats:
            return 0.0
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        # Базовый балл
        score = 1.0
        
        # Фактор скорости ответа (чем быстрее, тем лучше)
        if metrics.avg_response_time > 0:
            # Нормализуем: 1 секунда = 1.0, 10 секунд = 0.1
            speed_factor = min(1.0, 1.0 / metrics.avg_response_time)
            score *= speed_factor
        
        # Фактор надежности
        if stats.total_requests > 0:
            reliability_factor = stats.successful_requests / stats.total_requests
            score *= reliability_factor
        
        # Фактор стабильности (штраф за consecutive failures)
        stability_factor = max(0.1, 1.0 - (stats.consecutive_failures * 0.1))
        score *= stability_factor
        
        return min(1.0, score)
    
    def _calculate_reliability_score(self, provider_name: str) -> float:
        """🔧 Вычисление балла надежности"""
        if provider_name not in self.provider_stats:
            return 0.0
        
        stats = self.provider_stats[provider_name]
        
        if stats.total_requests == 0:
            return 1.0  # Новый провайдер получает максимальный балл
        
        # Базовый success rate
        success_rate = stats.successful_requests / stats.total_requests
        
        # Штраф за consecutive failures
        consecutive_penalty = max(0.0, stats.consecutive_failures * 0.05)
        
        # Бонус за стабильность (если нет недавних ошибок)
        stability_bonus = 0.1 if stats.consecutive_failures == 0 and stats.total_requests > 10 else 0.0
        
        reliability_score = success_rate - consecutive_penalty + stability_bonus
        
        return max(0.0, min(1.0, reliability_score))
    
    def _calculate_token_efficiency(self, provider_name: str) -> float:
        """🔧 Вычисление эффективности использования токенов"""
        if provider_name not in self.provider_stats:
            return 0.0
        
        metrics = self.provider_stats[provider_name].metrics
        
        if metrics.avg_tokens_per_request == 0:
            return 1.0
        
        # Эффективность = обратно пропорциональна количеству токенов
        # Нормализуем: 100 токенов = 1.0, 1000 токенов = 0.1
        efficiency = min(1.0, 100.0 / metrics.avg_tokens_per_request)
        
        return efficiency
    
    def _calculate_uptime_percentage(self, provider_name: str) -> float:
        """🔧 Вычисление процента uptime"""
        if provider_name not in self.provider_stats:
            return 100.0
        
        stats = self.provider_stats[provider_name]
        
        if stats.total_requests == 0:
            return 100.0
        
        # Упрощенный расчет на основе success rate
        uptime = (stats.successful_requests / stats.total_requests) * 100
        
        return round(uptime, 2)
    
    def _get_most_common_error(self, provider_name: str) -> Optional[str]:
        """🔧 Получение самого частого типа ошибки"""
        if provider_name not in self.provider_stats:
            return None
        
        error_types = self.provider_stats[provider_name].metrics.error_types
        
        if not error_types:
            return None
        
        return max(error_types.items(), key=lambda x: x[1])[0]
    
    def _analyze_error_trend(self, provider_name: str) -> str:
        """🔧 Анализ тренда ошибок"""
        if provider_name not in self.provider_stats:
            return "no_data"
        
        stats = self.provider_stats[provider_name]
        
        if stats.consecutive_failures == 0:
            return "stable"
        elif stats.consecutive_failures < 3:
            return "minor_issues"
        elif stats.consecutive_failures < 5:
            return "concerning"
        else:
            return "critical"
    
    def _get_provider_rank(self, provider_name: str) -> int:
        """🔧 Получение ранга провайдера по приоритету"""
        providers = self._get_providers_by_priority()
        
        for i, provider in enumerate(providers):
            if provider.name == provider_name:
                return i + 1
        
        return len(providers) + 1
    
    def _create_provider_rankings(self) -> Dict[str, List[Dict[str, Any]]]:
        """🔧 Создание рейтингов провайдеров"""
        providers = self.get_llm_providers()
        
        # Рейтинг по производительности
        performance_ranking = []
        reliability_ranking = []
        priority_ranking = []
        
        for provider in providers:
            if provider.name in self.provider_stats:
                stats = self.provider_stats[provider.name]
                
                performance_score = self._calculate_performance_score(provider.name)
                reliability_score = self._calculate_reliability_score(provider.name)
                
                performance_ranking.append({
                    "provider": provider.name,
                    "score": round(performance_score, 3)
                })
                
                reliability_ranking.append({
                    "provider": provider.name,
                    "score": round(reliability_score, 3)
                })
                
                priority_ranking.append({
                    "provider": provider.name,
                    "score": round(stats.priority_score, 3)
                })
        
        # Сортируем по убыванию
        performance_ranking.sort(key=lambda x: x["score"], reverse=True)
        reliability_ranking.sort(key=lambda x: x["score"], reverse=True)
        priority_ranking.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "by_performance": performance_ranking,
            "by_reliability": reliability_ranking,
            "by_priority": priority_ranking
        }
    
    def _get_response_time_recommendation(self, avg_response_time: float) -> str:
        """🔧 Рекомендация по времени ответа"""
        if avg_response_time < 1.0:
            return "Excellent response time"
        elif avg_response_time < 3.0:
            return "Good response time"
        elif avg_response_time < 5.0:
            return "Acceptable response time, consider optimization"
        else:
            return "Slow response time, optimization required"
    
    def _get_reliability_recommendation(self, provider_name: str) -> str:
        """🔧 Рекомендация по надежности"""
        reliability_score = self._calculate_reliability_score(provider_name)
        
        if reliability_score > 0.95:
            return "Excellent reliability"
        elif reliability_score > 0.90:
            return "Good reliability"
        elif reliability_score > 0.80:
            return "Acceptable reliability, monitor closely"
        else:
            return "Poor reliability, investigate issues"
    
    def _get_efficiency_recommendation(self, provider_name: str) -> str:
        """🔧 Рекомендация по эффективности токенов"""
        efficiency = self._calculate_token_efficiency(provider_name)
        
        if efficiency > 0.8:
            return "Excellent token efficiency"
        elif efficiency > 0.6:
            return "Good token efficiency"
        elif efficiency > 0.4:
            return "Moderate token efficiency"
        else:
            return "Poor token efficiency, optimize prompts"
    
    def _generate_performance_alerts(self, provider_name: str) -> List[Dict[str, str]]:
        """🔧 Генерация алертов по производительности"""
        alerts = []
        
        if provider_name not in self.provider_stats:
            return alerts
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        # Алерт по времени ответа
        if metrics.avg_response_time > 5.0:
            alerts.append({
                "type": "warning",
                "message": f"High average response time: {metrics.avg_response_time:.2f}s"
            })
        
        # Алерт по consecutive failures
        if stats.consecutive_failures >= 3:
            alerts.append({
                "type": "error",
                "message": f"High consecutive failures: {stats.consecutive_failures}"
            })
        
        # Алерт по success rate
        success_rate = stats.successful_requests / max(1, stats.total_requests)
        if success_rate < 0.9 and stats.total_requests > 10:
            alerts.append({
                "type": "warning",
                "message": f"Low success rate: {success_rate:.1%}"
            })
        
        return alerts
    
    def _generate_optimization_recommendations(self, provider_name: str) -> List[str]:
        """🔧 Генерация рекомендаций по оптимизации"""
        recommendations = []
        
        if provider_name not in self.provider_stats:
            return recommendations
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        # Рекомендации по времени ответа
        if metrics.avg_response_time > 3.0:
            recommendations.append("Consider reducing request complexity or switching to faster model")
        
        # Рекомендации по надежности
        if stats.consecutive_failures > 2:
            recommendations.append("Investigate connection issues or API key validity")
        
        # Рекомендации по токенам
        if metrics.avg_tokens_per_request > 500:
            recommendations.append("Optimize prompts to reduce token usage")
        
        # Рекомендации по Circuit Breaker
        circuit_state = self.circuit_breaker_states.get(provider_name, "closed")
        if circuit_state == "open":
            recommendations.append("Provider is currently unavailable due to Circuit Breaker")
        
        return recommendations
    
    # 🎯 ПРИОРИТИЗАЦИЯ ПРОВАЙДЕРОВ ПО СКОРОСТИ ОТВЕТА
    
    def get_providers_by_priority(self) -> List[LLMProviderConfig]:
        """🎯 Получение провайдеров в порядке приоритета (лучшие первыми)"""
        providers = self.get_llm_providers()
        
        # Сортируем по priority_score (убывание) и доступности
        def sort_key(provider):
            if provider.name not in self.provider_stats:
                # Новые провайдеры получают средний приоритет
                return (0.5, provider.name)
            
            stats = self.provider_stats[provider.name]
            
            # Недоступные провайдеры идут в конец
            if not self.is_provider_available(provider.name):
                return (-1.0, provider.name)
            
            return (stats.priority_score, provider.name)
        
        sorted_providers = sorted(providers, key=sort_key, reverse=True)
        
        self.logger.debug("providers_sorted_by_priority",
                         providers=[p.name for p in sorted_providers[:5]],  # Топ-5
                         total_count=len(sorted_providers))
        
        return sorted_providers
    
    def get_best_available_provider(self) -> Optional[LLMProviderConfig]:
        """🎯 Получение лучшего доступного провайдера"""
        providers_by_priority = self.get_providers_by_priority()
        
        for provider in providers_by_priority:
            if self.is_provider_available(provider.name):
                stats = self.provider_stats.get(provider.name, ProviderStats())
                self.logger.debug("best_provider_selected",
                                provider=provider.name,
                                priority_score=stats.priority_score)
                return provider
        
        self.logger.warning("no_available_providers")
        return None
    
    def get_top_providers(self, count: int = 3) -> List[LLMProviderConfig]:
        """🎯 Получение топ-N провайдеров по приоритету"""
        providers_by_priority = self.get_providers_by_priority()
        available_providers = [p for p in providers_by_priority if self.is_provider_available(p.name)]
        
        top_providers = available_providers[:count]
        
        self.logger.debug("top_providers_selected",
                         providers=[p.name for p in top_providers],
                         requested_count=count,
                         available_count=len(available_providers))
        
        return top_providers
    
    def update_provider_priority_by_performance(self, provider_name: str) -> None:
        """🎯 Обновление приоритета провайдера на основе производительности"""
        if provider_name not in self.provider_stats:
            return
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        # Базовый приоритет
        priority = 0.5
        
        # Фактор скорости ответа (40% веса)
        if metrics.avg_response_time > 0:
            # Быстрые ответы (< 2 сек) получают бонус
            if metrics.avg_response_time < 2.0:
                speed_factor = 1.0
            elif metrics.avg_response_time < 5.0:
                speed_factor = 0.8
            elif metrics.avg_response_time < 10.0:
                speed_factor = 0.6
            else:
                speed_factor = 0.3
            
            priority += (speed_factor - 0.5) * 0.4
        
        # Фактор надежности (35% веса)
        if stats.total_requests > 0:
            success_rate = stats.successful_requests / stats.total_requests
            reliability_factor = success_rate
            
            # Штраф за consecutive failures
            if stats.consecutive_failures > 0:
                reliability_penalty = min(0.3, stats.consecutive_failures * 0.05)
                reliability_factor -= reliability_penalty
            
            priority += (reliability_factor - 0.5) * 0.35
        
        # Фактор эффективности токенов (15% веса)
        token_efficiency = self._calculate_token_efficiency(provider_name)
        priority += (token_efficiency - 0.5) * 0.15
        
        # Фактор стабильности (10% веса)
        if stats.total_requests > 10:
            # Бонус за стабильную работу
            if stats.consecutive_failures == 0:
                stability_bonus = 0.1
            else:
                stability_bonus = -0.05 * min(5, stats.consecutive_failures)
            
            priority += stability_bonus * 0.1
        
        # Ограничиваем диапазон [0.0, 1.0]
        priority = max(0.0, min(1.0, priority))
        
        old_priority = stats.priority_score
        stats.priority_score = priority
        
        # Логируем значительные изменения приоритета
        if abs(priority - old_priority) > 0.1:
            self.logger.info("provider_priority_updated",
                           provider=provider_name,
                           old_priority=round(old_priority, 3),
                           new_priority=round(priority, 3),
                           avg_response_time=round(metrics.avg_response_time, 3),
                           success_rate=round(stats.successful_requests / max(1, stats.total_requests), 3),
                           consecutive_failures=stats.consecutive_failures)
    
    def rebalance_provider_priorities(self) -> Dict[str, float]:
        """🎯 Перебалансировка приоритетов всех провайдеров"""
        providers = self.get_llm_providers()
        priority_changes = {}
        
        for provider in providers:
            if provider.name in self.provider_stats:
                old_priority = self.provider_stats[provider.name].priority_score
                self.update_provider_priority_by_performance(provider.name)
                new_priority = self.provider_stats[provider.name].priority_score
                
                if abs(new_priority - old_priority) > 0.05:  # Значительное изменение
                    priority_changes[provider.name] = {
                        "old": round(old_priority, 3),
                        "new": round(new_priority, 3),
                        "change": round(new_priority - old_priority, 3)
                    }
        
        if priority_changes:
            self.logger.info("provider_priorities_rebalanced",
                           changes_count=len(priority_changes),
                           significant_changes=priority_changes)
        
        return priority_changes
    
    def get_provider_priority_explanation(self, provider_name: str) -> Dict[str, Any]:
        """🎯 Объяснение приоритета провайдера"""
        if provider_name not in self.provider_stats:
            return {
                "provider": provider_name,
                "error": "Provider not found in statistics"
            }
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        # Вычисляем компоненты приоритета
        speed_score = 0.5
        if metrics.avg_response_time > 0:
            if metrics.avg_response_time < 2.0:
                speed_score = 1.0
            elif metrics.avg_response_time < 5.0:
                speed_score = 0.8
            elif metrics.avg_response_time < 10.0:
                speed_score = 0.6
            else:
                speed_score = 0.3
        
        reliability_score = 0.5
        if stats.total_requests > 0:
            reliability_score = stats.successful_requests / stats.total_requests
            if stats.consecutive_failures > 0:
                reliability_penalty = min(0.3, stats.consecutive_failures * 0.05)
                reliability_score -= reliability_penalty
        
        token_efficiency = self._calculate_token_efficiency(provider_name)
        
        stability_score = 0.5
        if stats.total_requests > 10:
            if stats.consecutive_failures == 0:
                stability_score = 0.6
            else:
                stability_score = 0.5 - (0.05 * min(5, stats.consecutive_failures))
        
        return {
            "provider": provider_name,
            "current_priority": round(stats.priority_score, 3),
            "rank": self._get_provider_rank(provider_name),
            "components": {
                "speed": {
                    "score": round(speed_score, 3),
                    "weight": 0.4,
                    "contribution": round((speed_score - 0.5) * 0.4, 3),
                    "avg_response_time": round(metrics.avg_response_time, 3)
                },
                "reliability": {
                    "score": round(reliability_score, 3),
                    "weight": 0.35,
                    "contribution": round((reliability_score - 0.5) * 0.35, 3),
                    "success_rate": round(stats.successful_requests / max(1, stats.total_requests), 3),
                    "consecutive_failures": stats.consecutive_failures
                },
                "token_efficiency": {
                    "score": round(token_efficiency, 3),
                    "weight": 0.15,
                    "contribution": round((token_efficiency - 0.5) * 0.15, 3),
                    "avg_tokens_per_request": round(metrics.avg_tokens_per_request, 2)
                },
                "stability": {
                    "score": round(stability_score, 3),
                    "weight": 0.1,
                    "contribution": round((stability_score - 0.5) * 0.1, 3),
                    "total_requests": stats.total_requests
                }
            },
            "recommendations": self._get_priority_improvement_recommendations(provider_name)
        }
    
    def _get_priority_improvement_recommendations(self, provider_name: str) -> List[str]:
        """🔧 Рекомендации по улучшению приоритета провайдера"""
        recommendations = []
        
        if provider_name not in self.provider_stats:
            return recommendations
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        # Рекомендации по скорости
        if metrics.avg_response_time > 5.0:
            recommendations.append("Improve response time by optimizing model parameters or switching to faster model")
        
        # Рекомендации по надежности
        success_rate = stats.successful_requests / max(1, stats.total_requests)
        if success_rate < 0.9:
            recommendations.append("Improve reliability by fixing connection issues or API configuration")
        
        if stats.consecutive_failures > 2:
            recommendations.append("Address consecutive failures to improve stability score")
        
        # Рекомендации по эффективности токенов
        if metrics.avg_tokens_per_request > 500:
            recommendations.append("Optimize token usage by refining prompts or using more efficient models")
        
        # Рекомендации по стабильности
        if stats.total_requests < 10:
            recommendations.append("Increase usage to build stability metrics")
        
        return recommendations
    
    def _get_provider_rank(self, provider_name: str) -> int:
        """🔧 Получение ранга провайдера среди всех провайдеров"""
        providers_by_priority = self.get_providers_by_priority()
        
        for i, provider in enumerate(providers_by_priority, 1):
            if provider.name == provider_name:
                return i
        
        return len(providers_by_priority) + 1  # Не найден - последнее место
    
    # 📊 СТРУКТУРИРОВАННОЕ ЛОГИРОВАНИЕ ДЛЯ АНАЛИТИКИ
    
    def log_request_analytics(self, 
                            provider_name: str, 
                            request_type: str,
                            response_time: float,
                            token_usage: int,
                            success: bool,
                            error_type: Optional[str] = None,
                            request_id: Optional[str] = None) -> None:
        """📊 Логирование аналитики запросов в структурированном формате"""
        
        analytics_data = {
            "event_type": "llm_request",
            "provider": provider_name,
            "request_type": request_type,
            "response_time_ms": round(response_time * 1000, 2),
            "token_usage": token_usage,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id or f"req_{int(time.time() * 1000)}"
        }
        
        if error_type:
            analytics_data["error_type"] = error_type
        
        # Добавляем контекстную информацию
        if provider_name in self.provider_stats:
            stats = self.provider_stats[provider_name]
            analytics_data.update({
                "provider_priority_score": round(stats.priority_score, 3),
                "provider_success_rate": round(stats.successful_requests / max(1, stats.total_requests), 3),
                "consecutive_failures": stats.consecutive_failures,
                "circuit_breaker_state": stats.circuit_breaker_state.value
            })
        
        self.logger.info("request_analytics", **analytics_data)
    
    def log_performance_metrics(self, provider_name: str) -> None:
        """📊 Логирование метрик производительности провайдера"""
        
        if provider_name not in self.provider_stats:
            return
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        performance_data = {
            "event_type": "performance_metrics",
            "provider": provider_name,
            "timestamp": datetime.now().isoformat(),
            "total_requests": stats.total_requests,
            "successful_requests": stats.successful_requests,
            "failed_requests": stats.failed_requests,
            "success_rate": round(stats.successful_requests / max(1, stats.total_requests), 3),
            "avg_response_time_ms": round(metrics.avg_response_time * 1000, 2),
            "median_response_time_ms": round(metrics.median_response_time * 1000, 2),
            "total_tokens_used": metrics.total_tokens_used,
            "avg_tokens_per_request": round(metrics.avg_tokens_per_request, 2),
            "requests_per_minute": round(metrics.requests_per_minute, 2),
            "priority_score": round(stats.priority_score, 3),
            "consecutive_failures": stats.consecutive_failures,
            "circuit_breaker_state": stats.circuit_breaker_state.value,
            "rate_limit_errors": stats.rate_limit_errors
        }
        
        # Добавляем информацию об ошибках
        if metrics.error_types:
            performance_data["error_distribution"] = dict(metrics.error_types)
            performance_data["most_common_error"] = max(metrics.error_types.items(), key=lambda x: x[1])[0]
        
        self.logger.info("performance_metrics", **performance_data)
    
    def log_circuit_breaker_event(self, 
                                 provider_name: str, 
                                 event_type: str, 
                                 old_state: CircuitBreakerState, 
                                 new_state: CircuitBreakerState,
                                 reason: Optional[str] = None) -> None:
        """📊 Логирование событий Circuit Breaker"""
        
        event_data = {
            "event_type": "circuit_breaker_event",
            "provider": provider_name,
            "cb_event_type": event_type,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "timestamp": datetime.now().isoformat(),
            "reason": reason or "state_transition"
        }
        
        if provider_name in self.provider_stats:
            stats = self.provider_stats[provider_name]
            event_data.update({
                "consecutive_failures": stats.consecutive_failures,
                "consecutive_successes": stats.consecutive_successes,
                "total_requests": stats.total_requests,
                "success_rate": round(stats.successful_requests / max(1, stats.total_requests), 3)
            })
        
        self.logger.warning("circuit_breaker_event", **event_data)
    
    def log_fallback_event(self, 
                          original_provider: str, 
                          fallback_provider: str, 
                          attempt_number: int,
                          reason: str) -> None:
        """📊 Логирование событий Fallback"""
        
        fallback_data = {
            "event_type": "fallback_event",
            "original_provider": original_provider,
            "fallback_provider": fallback_provider,
            "attempt_number": attempt_number,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.warning("fallback_event", **fallback_data)
    
    def log_priority_rebalance(self, changes: Dict[str, Dict[str, float]]) -> None:
        """📊 Логирование перебалансировки приоритетов"""
        
        rebalance_data = {
            "event_type": "priority_rebalance",
            "timestamp": datetime.now().isoformat(),
            "changes_count": len(changes),
            "priority_changes": changes
        }
        
        # Добавляем статистику изменений
        if changes:
            change_values = [change["change"] for change in changes.values()]
            rebalance_data.update({
                "max_priority_increase": round(max(change_values), 3),
                "max_priority_decrease": round(min(change_values), 3),
                "avg_priority_change": round(sum(change_values) / len(change_values), 3)
            })
        
        self.logger.info("priority_rebalance", **rebalance_data)
    
    def log_system_health(self) -> None:
        """📊 Логирование общего состояния системы"""
        
        providers = self.get_llm_providers()
        available_providers = [p for p in providers if self.is_provider_available(p.name)]
        
        health_data = {
            "event_type": "system_health",
            "timestamp": datetime.now().isoformat(),
            "total_providers": len(providers),
            "available_providers": len(available_providers),
            "availability_rate": round(len(available_providers) / max(1, len(providers)), 3)
        }
        
        # Статистика по состояниям Circuit Breaker
        cb_states = {}
        for provider in providers:
            if provider.name in self.provider_stats:
                state = self.provider_stats[provider.name].circuit_breaker_state.value
                cb_states[state] = cb_states.get(state, 0) + 1
        
        health_data["circuit_breaker_states"] = cb_states
        
        # Топ-3 провайдера по приоритету
        top_providers = self.get_top_providers(3)
        health_data["top_providers"] = [{
            "name": p.name,
            "priority_score": round(self.provider_stats.get(p.name, ProviderStats()).priority_score, 3)
        } for p in top_providers]
        
        self.logger.info("system_health", **health_data)
    
    def export_analytics_logs(self, hours: int = 24, output_file: Optional[str] = None) -> str:
        """📊 Экспорт аналитических логов за указанный период"""
        
        # Создаем сводку аналитики
        analytics_summary = {
            "export_timestamp": datetime.now().isoformat(),
            "period_hours": hours,
            "providers_summary": {},
            "system_summary": {
                "total_providers": len(self.get_llm_providers()),
                "available_providers": len([p for p in self.get_llm_providers() if self.is_provider_available(p.name)])
            }
        }
        
        # Добавляем данные по каждому провайдеру
        for provider_name, stats in self.provider_stats.items():
            analytics_summary["providers_summary"][provider_name] = {
                "total_requests": stats.total_requests,
                "success_rate": round(stats.successful_requests / max(1, stats.total_requests), 3),
                "avg_response_time_ms": round(stats.metrics.avg_response_time * 1000, 2),
                "priority_score": round(stats.priority_score, 3),
                "circuit_breaker_state": stats.circuit_breaker_state.value,
                "consecutive_failures": stats.consecutive_failures,
                "rate_limit_errors": stats.rate_limit_errors,
                "total_tokens_used": stats.metrics.total_tokens_used
            }
        
        # Сохраняем в файл
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"analytics_export_{timestamp}.json"
        
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analytics_summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info("analytics_exported", 
                        output_file=str(output_path),
                        period_hours=hours,
                        providers_count=len(analytics_summary["providers_summary"]))
        
        return str(output_path)
    
    # 🚀 НОВЫЕ МЕТОДЫ: Выполнение запросов с retry механизмом
    
    async def make_request_async(self, 
                               provider: LLMProviderConfig, 
                               request_data: Dict[str, Any],
                               request_id: Optional[str] = None) -> Dict[str, Any]:
        """🔄 Асинхронный запрос к провайдеру с retry механизмом"""
        request_id = request_id or f"req_{int(time.time() * 1000)}"
        start_time = time.time()
        
        self.logger.info("provider_request_start", 
                        provider=provider.name,
                        request_id=request_id,
                        model=provider.model)
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                # Проверка доступности провайдера
                if not self.is_provider_available(provider.name):
                    raise Exception(f"Provider {provider.name} is not available (Circuit Breaker)")
                
                # Выполнение запроса
                response = await self._execute_provider_request(provider, request_data)
                
                # Запись успешного результата
                response_time = time.time() - start_time
                self._record_successful_request(provider.name, response_time, response.get('token_usage', 0))
                
                self.logger.info("provider_request_success",
                               provider=provider.name,
                               request_id=request_id,
                               response_time=response_time,
                               attempt=attempt + 1)
                
                return response
                
            except Exception as e:
                error_type = self._classify_error(str(e))
                is_rate_limit = "429" in str(e) or "rate limit" in str(e).lower()
                
                self.logger.warning("provider_request_error",
                                  provider=provider.name,
                                  request_id=request_id,
                                  attempt=attempt + 1,
                                  error_type=error_type,
                                  error=str(e),
                                  is_rate_limit=is_rate_limit)
                
                # Запись ошибки
                self.record_provider_failure(provider.name, str(e), is_rate_limit)
                
                # Если это последняя попытка, поднимаем исключение
                if attempt == self.retry_config.max_attempts - 1:
                    raise e
                
                # Вычисление задержки с экспоненциальным backoff
                delay = self._calculate_retry_delay(attempt, is_rate_limit)
                
                self.logger.info("provider_request_retry",
                               provider=provider.name,
                               request_id=request_id,
                               delay=delay,
                               next_attempt=attempt + 2)
                
                await asyncio.sleep(delay)
    
    def make_request_sync(self, 
                         provider: LLMProviderConfig, 
                         request_data: Dict[str, Any],
                         request_id: Optional[str] = None) -> Dict[str, Any]:
        """🔄 Синхронный запрос к провайдеру с retry механизмом"""
        return asyncio.run(self.make_request_async(provider, request_data, request_id))
    
    async def make_request_with_fallback(self, 
                                       request_data: Dict[str, Any],
                                       exclude_providers: List[str] = None,
                                       request_id: Optional[str] = None) -> Dict[str, Any]:
        """🔄 Запрос с автоматическим fallback между провайдерами"""
        request_id = request_id or f"fallback_req_{int(time.time() * 1000)}"
        exclude_providers = exclude_providers or []
        
        self.logger.info("fallback_request_start",
                        request_id=request_id,
                        excluded_providers=exclude_providers)
        
        # Получаем провайдеров по приоритету (с учетом производительности)
        providers = self._get_providers_by_priority(exclude_providers)
        
        if not providers:
            raise Exception("No available providers for fallback")
        
        last_error = None
        
        for i, provider in enumerate(providers):
            try:
                self.logger.info("fallback_trying_provider",
                               request_id=request_id,
                               provider=provider.name,
                               attempt=i + 1,
                               total_providers=len(providers))
                
                response = await self.make_request_async(provider, request_data, request_id)
                
                self.logger.info("fallback_request_success",
                               request_id=request_id,
                               successful_provider=provider.name,
                               attempts_made=i + 1)
                
                return response
                
            except Exception as e:
                last_error = e
                self.logger.warning("fallback_provider_failed",
                                  request_id=request_id,
                                  provider=provider.name,
                                  error=str(e))
                
                # Добавляем провайдера в исключения для следующих попыток
                exclude_providers.append(provider.name)
                
                # Задержка между попытками fallback
                if i < len(providers) - 1:  # Не ждем после последней попытки
                    await asyncio.sleep(self.fallback_config.fallback_delay)
        
        # Все провайдеры не сработали
        self.logger.error("fallback_request_failed",
                         request_id=request_id,
                         total_attempts=len(providers),
                         last_error=str(last_error) if last_error else "Unknown error")
        
        raise Exception(f"All providers failed. Last error: {last_error}")
    
    # 🔧 ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    
    async def _execute_provider_request(self, provider: LLMProviderConfig, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """🔧 Выполнение запроса к провайдеру через объект провайдера"""
        if provider.name not in self.providers:
            raise Exception(f'Провайдер {provider.name} не инициализирован')
        
        provider_obj = self.providers[provider.name]
        result = await provider_obj.make_request(request_data)
        
        # Добавляем метаданные
        result['_metadata'] = {
            'provider': provider.name,
            'model': provider.model,
            'status_code': 200,
            'response_time': time.time()
        }
        
        return result
    
    def _calculate_retry_delay(self, attempt: int, is_rate_limit: bool = False) -> float:
        """🔧 Вычисление задержки для retry с экспоненциальным backoff"""
        if is_rate_limit:
            # Для rate limit используем более длительные задержки
            base_delay = self.retry_config.base_delay * 10
        else:
            base_delay = self.retry_config.base_delay
        
        # Экспоненциальный backoff
        delay = base_delay * (self.retry_config.exponential_base ** attempt)
        
        # Ограничиваем максимальной задержкой
        delay = min(delay, self.retry_config.max_delay)
        
        # Добавляем jitter для избежания thundering herd
        if self.retry_config.jitter:
            jitter = delay * 0.1 * random.random()
            delay += jitter
        
        return delay
    
    def _classify_error(self, error_message: str) -> str:
        """🔧 Классификация типа ошибки"""
        error_lower = error_message.lower()
        
        if "429" in error_message or "rate limit" in error_lower:
            return "rate_limit"
        elif "timeout" in error_lower:
            return "timeout"
        elif "connection" in error_lower:
            return "connection"
        elif "401" in error_message or "unauthorized" in error_lower:
            return "auth"
        elif "500" in error_message or "internal server" in error_lower:
            return "server_error"
        elif "400" in error_message or "bad request" in error_lower:
            return "client_error"
        else:
            return "unknown"
    
    def _record_successful_request(self, provider_name: str, response_time: float, token_usage: int):
        """🔧 Запись успешного запроса с метриками"""
        self.record_provider_success(provider_name)
        
        if provider_name in self.provider_stats:
            stats = self.provider_stats[provider_name]
            stats.metrics.update_response_time(response_time)
            stats.metrics.update_token_usage(token_usage)
            stats.metrics.last_success = datetime.now()
            
            # Обновляем приоритет на основе производительности
            self._update_provider_priority(provider_name)
    
    def _update_provider_priority(self, provider_name: str):
        """🎯 Обновление динамического приоритета провайдера"""
        if provider_name not in self.provider_stats:
            return
        
        stats = self.provider_stats[provider_name]
        metrics = stats.metrics
        
        # Базовый приоритет = 1.0
        priority_score = 1.0
        
        # Бонус за скорость ответа (чем быстрее, тем выше приоритет)
        if metrics.avg_response_time > 0:
            # Нормализуем время ответа (1-10 секунд -> 0.1-1.0 множитель)
            speed_multiplier = max(0.1, min(1.0, 10.0 / metrics.avg_response_time))
            priority_score *= speed_multiplier
        
        # Бонус за надежность (success rate)
        if stats.total_requests > 0:
            success_rate = stats.successful_requests / stats.total_requests
            priority_score *= success_rate
        
        # Штраф за недавние ошибки
        if stats.consecutive_failures > 0:
            failure_penalty = max(0.1, 1.0 - (stats.consecutive_failures * 0.2))
            priority_score *= failure_penalty
        
        stats.priority_score = priority_score
        
        self.logger.debug("provider_priority_updated",
                         provider=provider_name,
                         priority_score=priority_score,
                         avg_response_time=metrics.avg_response_time,
                         success_rate=stats.successful_requests / max(1, stats.total_requests))
    
    # 🎛️ УПРАВЛЕНИЕ СОСТОЯНИЕМ ПРОВАЙДЕРОВ
    
    def get_provider_state(self, provider_name: str) -> Dict[str, Any]:
        """🎛️ Получение полного состояния провайдера"""
        if provider_name not in self.provider_stats:
            return {
                "name": provider_name,
                "available": True,
                "circuit_breaker_state": "closed",
                "stats": None,
                "metrics": None,
                "priority_score": 1.0
            }
        
        stats = self.provider_stats[provider_name]
        circuit_state = self.circuit_breaker_states.get(provider_name, "closed")
        
        return {
            "name": provider_name,
            "available": self.is_provider_available(provider_name),
            "circuit_breaker_state": circuit_state,
            "stats": {
                "total_requests": stats.total_requests,
                "successful_requests": stats.successful_requests,
                "failed_requests": stats.failed_requests,
                "consecutive_failures": stats.consecutive_failures,
                "success_rate": stats.successful_requests / max(1, stats.total_requests),
                "last_request_time": stats.last_request_time.isoformat() if stats.last_request_time else None,
                "last_failure_time": stats.last_failure_time.isoformat() if stats.last_failure_time else None
            },
            "metrics": {
                "avg_response_time": stats.metrics.avg_response_time,
                "min_response_time": stats.metrics.min_response_time,
                "max_response_time": stats.metrics.max_response_time,
                "total_tokens_used": stats.metrics.total_tokens_used,
                "avg_tokens_per_request": stats.metrics.avg_tokens_per_request,
                "error_types": dict(stats.metrics.error_types),
                "last_success": stats.metrics.last_success.isoformat() if stats.metrics.last_success else None
            },
            "priority_score": stats.priority_score
        }
    
    def get_all_providers_state(self) -> Dict[str, Dict[str, Any]]:
        """🎛️ Получение состояния всех провайдеров"""
        providers = self.get_llm_providers()
        states = {}
        
        for provider in providers:
            states[provider.name] = self.get_provider_state(provider.name)
        
        return states
    
    def reset_provider_state(self, provider_name: str):
        """🔄 Сброс состояния провайдера (для восстановления после проблем)"""
        if provider_name in self.provider_stats:
            # Сбрасываем статистику ошибок, но сохраняем метрики производительности
            stats = self.provider_stats[provider_name]
            stats.consecutive_failures = 0
            stats.failed_requests = 0
            
            # Очищаем типы ошибок
            stats.metrics.error_types.clear()
            
            self.logger.info("provider_state_reset",
                           provider=provider_name,
                           reason="manual_reset")
        
        # Сбрасываем Circuit Breaker
        if provider_name in self.circuit_breaker_states:
            self.circuit_breaker_states[provider_name] = "closed"
            
        if provider_name in self.circuit_breaker_failure_times:
            del self.circuit_breaker_failure_times[provider_name]
    
    def force_provider_available(self, provider_name: str, duration_seconds: int = 300):
        """🔓 Принудительное включение провайдера на определенное время"""
        # Сбрасываем состояние
        self.reset_provider_state(provider_name)
        
        # Устанавливаем временное исключение
        force_until = datetime.now() + timedelta(seconds=duration_seconds)
        
        if not hasattr(self, 'forced_available_until'):
            self.forced_available_until = {}
        
        self.forced_available_until[provider_name] = force_until
        
        self.logger.info("provider_forced_available",
                        provider=provider_name,
                        duration_seconds=duration_seconds,
                        until=force_until.isoformat())
    
    def is_provider_available(self, provider_name: str) -> bool:
        """🔍 Проверка доступности провайдера с учетом всех факторов"""
        # Проверяем принудительное включение
        if hasattr(self, 'forced_available_until') and provider_name in self.forced_available_until:
            if datetime.now() < self.forced_available_until[provider_name]:
                return True
            else:
                # Время принудительного включения истекло
                del self.forced_available_until[provider_name]
        
        # Проверяем Circuit Breaker
        circuit_state = self.circuit_breaker_states.get(provider_name, "closed")
        
        if circuit_state == "closed":
            return True
        elif circuit_state == "open":
            # Проверяем, не пора ли перейти в half-open
            if provider_name in self.circuit_breaker_failure_times:
                failure_time = self.circuit_breaker_failure_times[provider_name]
                recovery_timeout = self.circuit_breaker_config.recovery_timeout
                
                # Адаптивный recovery timeout
                if provider_name in self.provider_stats:
                    stats = self.provider_stats[provider_name]
                    if stats.consecutive_failures > 5:
                        # Увеличиваем timeout для часто падающих провайдеров
                        recovery_timeout *= min(3.0, stats.consecutive_failures / 5.0)
                
                if datetime.now() - failure_time > timedelta(seconds=recovery_timeout):
                    self.circuit_breaker_states[provider_name] = "half-open"
                    self.logger.info("circuit_breaker_half_open",
                                   provider=provider_name,
                                   recovery_timeout=recovery_timeout)
                    return True
            return False
        elif circuit_state == "half-open":
            return True
        
        return False
    
    def update_circuit_breaker_state(self, provider_name: str, success: bool):
        """🔄 Обновление состояния Circuit Breaker"""
        current_state = self.circuit_breaker_states.get(provider_name, "closed")
        
        if success:
            if current_state == "half-open":
                # Успешный запрос в half-open состоянии - закрываем Circuit Breaker
                self.circuit_breaker_states[provider_name] = "closed"
                if provider_name in self.circuit_breaker_failure_times:
                    del self.circuit_breaker_failure_times[provider_name]
                
                self.logger.info("circuit_breaker_closed",
                               provider=provider_name,
                               reason="successful_recovery")
        else:
            # Неудачный запрос
            if provider_name not in self.provider_stats:
                return
            
            stats = self.provider_stats[provider_name]
            
            # Адаптируем пороги перед проверкой
            self._adapt_circuit_breaker_thresholds(provider_name)
            
            if current_state == "closed":
                # Проверяем, не пора ли открыть Circuit Breaker
                if stats.consecutive_failures >= self.circuit_breaker_config.failure_threshold:
                    self.circuit_breaker_states[provider_name] = "open"
                    self.circuit_breaker_failure_times[provider_name] = datetime.now()
                    
                    self.logger.warning("circuit_breaker_opened",
                                      provider=provider_name,
                                      consecutive_failures=stats.consecutive_failures,
                                      failure_threshold=self.circuit_breaker_config.failure_threshold)
            
            elif current_state == "half-open":
                # Неудача в half-open состоянии - снова открываем
                self.circuit_breaker_states[provider_name] = "open"
                self.circuit_breaker_failure_times[provider_name] = datetime.now()
                
                self.logger.warning("circuit_breaker_reopened",
                                  provider=provider_name,
                                  reason="failed_in_half_open")
    
    def get_circuit_breaker_summary(self) -> Dict[str, Any]:
        """📊 Сводка по состоянию Circuit Breaker всех провайдеров"""
        summary = {
            "total_providers": len(self.get_llm_providers()),
            "available_providers": 0,
            "circuit_breaker_states": {
                "closed": 0,
                "open": 0,
                "half_open": 0
            },
            "providers_detail": {},
            "adaptive_thresholds": self.adaptive_thresholds,
            "current_config": {
                "failure_threshold": self.circuit_breaker_config.failure_threshold,
                "recovery_timeout": self.circuit_breaker_config.recovery_timeout
            }
        }
        
        for provider in self.get_llm_providers():
            is_available = self.is_provider_available(provider.name)
            circuit_state = self.circuit_breaker_states.get(provider.name, "closed")
            
            if is_available:
                summary["available_providers"] += 1
            
            summary["circuit_breaker_states"][circuit_state] += 1
            
            provider_detail = {
                "available": is_available,
                "circuit_state": circuit_state,
                "consecutive_failures": 0,
                "last_failure_time": None
            }
            
            if provider.name in self.provider_stats:
                stats = self.provider_stats[provider.name]
                provider_detail["consecutive_failures"] = stats.consecutive_failures
                if stats.last_failure_time:
                    provider_detail["last_failure_time"] = stats.last_failure_time.isoformat()
            
            if provider.name in self.circuit_breaker_failure_times:
                provider_detail["circuit_failure_time"] = self.circuit_breaker_failure_times[provider.name].isoformat()
            
            summary["providers_detail"][provider.name] = provider_detail
        
        return summary
    
    def _get_providers_by_priority(self, exclude_providers: List[str] = None) -> List[LLMProviderConfig]:
        """🎯 Получение провайдеров отсортированных по динамическому приоритету"""
        exclude_providers = exclude_providers or []
        providers = self.get_llm_providers()
        
        # Фильтруем исключенных провайдеров
        available_providers = [
            p for p in providers 
            if p.name not in exclude_providers and self.is_provider_available(p.name)
        ]
        
        # Сортируем по динамическому приоритету (выше приоритет = раньше в списке)
        def get_priority_score(provider: LLMProviderConfig) -> float:
            if provider.name in self.provider_stats:
                return self.provider_stats[provider.name].priority_score
            return 1.0  # Базовый приоритет для новых провайдеров
        
        available_providers.sort(key=get_priority_score, reverse=True)
        
        return available_providers
    
    def _adapt_circuit_breaker_thresholds(self, provider_name: str):
        """🎯 Адаптация порогов Circuit Breaker на основе истории"""
        if provider_name not in self.provider_stats:
            return
        
        stats = self.provider_stats[provider_name]
        
        # Адаптируем пороги на основе исторической надежности
        if stats.total_requests >= 10:  # Достаточно данных для адаптации
            success_rate = stats.successful_requests / stats.total_requests
            
            if success_rate > 0.95:  # Очень надежный провайдер
                # Увеличиваем порог ошибок
                new_threshold = min(self.adaptive_thresholds["failure_threshold_max"], 
                                  self.circuit_breaker_config.failure_threshold + 2)
                self.circuit_breaker_config.failure_threshold = new_threshold
                
            elif success_rate < 0.8:  # Ненадежный провайдер
                # Уменьшаем порог ошибок
                new_threshold = max(self.adaptive_thresholds["failure_threshold_min"], 
                                  self.circuit_breaker_config.failure_threshold - 1)
                self.circuit_breaker_config.failure_threshold = new_threshold
        
        self.logger.debug("circuit_breaker_adapted",
                         provider=provider_name,
                         failure_threshold=self.circuit_breaker_config.failure_threshold,
                         success_rate=stats.successful_requests / max(1, stats.total_requests))
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить общую статистику провайдеров для совместимости с ContactExtractor."""
        return {
            "provider_stats": self.get_provider_stats_summary(),
            "total_providers": len(self.providers),
            "active_providers": len([p for p in self.providers.values() if p.config.active]),
            "circuit_breaker_states": {name: stats.circuit_breaker_state.value 
                                     for name, stats in self.provider_stats.items()},
            "total_requests": sum(stats.total_requests for stats in self.provider_stats.values()),
            "total_successful": sum(stats.successful_requests for stats in self.provider_stats.values()),
            "total_failed": sum(stats.failed_requests for stats in self.provider_stats.values())
        }
