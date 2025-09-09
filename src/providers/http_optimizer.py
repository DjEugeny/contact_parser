#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 HTTP Оптимизатор для LLM провайдеров
Фаза 6: Оптимизации производительности
"""

import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Optional, Any
import logging


class OptimizedHTTPClient:
    """
    🚀 Оптимизированный HTTP клиент с connection pooling

    Функциональность:
    - Connection pooling для повторного использования соединений
    - Индивидуальные таймауты для каждого провайдера
    - Автоматические retry с exponential backoff
    - Компрессия запросов и ответов
    - Подробное логирование производительности
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Создание сессии с оптимизациями
        self.session = requests.Session()

        # Настройка retry стратегии
        retry_strategy = Retry(
            total=3,                              # Максимум 3 попытки
            backoff_factor=0.5,                   # Экспоненциальная задержка: 0.5, 1, 2 сек
            status_forcelist=[429, 500, 502, 503, 504],  # Повторять при этих статусах
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )

        # Connection pooling адаптер
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,     # Количество пулов соединений (по хосту)
            pool_maxsize=20,         # Максимум соединений в пуле
            pool_block=False         # Не блокировать при достижении лимита
        )

        # Монтируем адаптер для HTTP и HTTPS
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

        # Индивидуальные таймауты для провайдеров
        self.provider_timeouts = {
            'openrouter': {'connect': 10, 'read': 60, 'total': 70},
            'groq': {'connect': 5, 'read': 30, 'total': 35},
            'replicate': {'connect': 15, 'read': 120, 'total': 135}
        }

        # Статистика производительности
        self.stats = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'retry_attempts': 0,
            'total_request_time': 0,
            'avg_request_time': 0,
            'connection_pool_stats': {},
            'errors_by_provider': {}
        }

        self.logger.info("🚀 OptimizedHTTPClient инициализирован с connection pooling")

    def make_request(self, provider_name: str, url: str, method: str = 'POST',
                    json_data: Optional[Dict] = None, headers: Optional[Dict] = None,
                    api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        🚀 Выполнить оптимизированный HTTP запрос

        Args:
            provider_name: Имя провайдера (для таймаутов)
            url: URL для запроса
            method: HTTP метод
            json_data: JSON данные для тела запроса
            headers: Дополнительные заголовки
            api_key: API ключ для авторизации

        Returns:
            Dict с результатами запроса
        """

        start_time = time.time()

        # Получаем таймауты для провайдера
        timeouts = self.provider_timeouts.get(provider_name, self.provider_timeouts['openrouter'])

        # Подготавливаем заголовки
        request_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',  # Компрессия
            'User-Agent': 'ContactParser/2.0'
        }

        if headers:
            request_headers.update(headers)

        if api_key:
            request_headers['Authorization'] = f'Bearer {api_key}'

        try:
            self.stats['requests_total'] += 1

            # Выполняем запрос
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                headers=request_headers,
                timeout=(timeouts['connect'], timeouts['read'])
            )

            request_time = time.time() - start_time
            self.stats['total_request_time'] += request_time

            # Обновляем среднее время
            if self.stats['requests_total'] > 0:
                self.stats['avg_request_time'] = self.stats['total_request_time'] / self.stats['requests_total']

            if response.status_code == 200:
                self.stats['requests_successful'] += 1
                self.logger.debug(f"✅ {provider_name}: {response.status_code} ({request_time:.2f}s)")

                return {
                    'success': True,
                    'status_code': response.status_code,
                    'data': response.json(),
                    'request_time': request_time,
                    'headers': dict(response.headers)
                }
            else:
                self.stats['requests_failed'] += 1
                self.logger.warning(f"❌ {provider_name}: {response.status_code} ({request_time:.2f}s)")

                # Увеличиваем счетчик ошибок для провайдера
                if provider_name not in self.stats['errors_by_provider']:
                    self.stats['errors_by_provider'][provider_name] = 0
                self.stats['errors_by_provider'][provider_name] += 1

                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text,
                    'request_time': request_time
                }

        except requests.exceptions.Timeout as e:
            request_time = time.time() - start_time
            self.stats['requests_failed'] += 1
            self.logger.error(f"⏰ {provider_name}: Timeout ({request_time:.2f}s) - {e}")

            return {
                'success': False,
                'error': f'Timeout: {e}',
                'request_time': request_time,
                'timeout_config': timeouts
            }

        except requests.exceptions.ConnectionError as e:
            request_time = time.time() - start_time
            self.stats['requests_failed'] += 1
            self.logger.error(f"🔌 {provider_name}: Connection error ({request_time:.2f}s) - {e}")

            return {
                'success': False,
                'error': f'Connection error: {e}',
                'request_time': request_time
            }

        except Exception as e:
            request_time = time.time() - start_time
            self.stats['requests_failed'] += 1
            self.logger.error(f"💥 {provider_name}: Unexpected error ({request_time:.2f}s) - {e}")

            return {
                'success': False,
                'error': f'Unexpected error: {e}',
                'request_time': request_time
            }

    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """📊 Получить статистику connection pool"""
        try:
            # Получаем информацию о пулах соединений
            pools = {}
            for adapter in self.session.adapters.values():
                if hasattr(adapter, 'pools'):
                    for key, pool in adapter.pools.items():
                        pools[str(key)] = {
                            'num_connections': pool.num_connections,
                            'num_requests': pool.num_requests,
                            'size': pool.size
                        }

            self.stats['connection_pool_stats'] = pools
            return pools

        except Exception as e:
            self.logger.error(f"Ошибка получения статистики пула: {e}")
            return {}

    def get_performance_stats(self) -> Dict[str, Any]:
        """📈 Получить статистику производительности"""
        stats = self.stats.copy()

        # Добавляем процент успешных запросов
        if stats['requests_total'] > 0:
            stats['success_rate'] = (stats['requests_successful'] / stats['requests_total']) * 100
        else:
            stats['success_rate'] = 0

        # Добавляем статистику пула соединений
        stats['connection_pools'] = self.get_connection_pool_stats()

        return stats

    def reset_stats(self):
        """🔄 Сбросить статистику"""
        self.stats = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'retry_attempts': 0,
            'total_request_time': 0,
            'avg_request_time': 0,
            'connection_pool_stats': {},
            'errors_by_provider': {}
        }
        self.logger.info("📊 Статистика HTTP клиента сброшена")

    def close(self):
        """🔒 Закрыть сессию и освободить ресурсы"""
        if self.session:
            self.session.close()
        self.logger.info("🔒 HTTP сессия закрыта")
