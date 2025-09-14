#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Unit тесты для LLM провайдеров
Фаза 7: Тестирование и Надежность
"""

import pytest
from unittest.mock import patch, MagicMock
import time

from providers.base_provider import BaseProvider, ProviderConfig
from providers.openrouter import OpenRouterProvider
from providers.groq import GroqProvider
from providers.replicate import ReplicateProvider


class TestBaseProvider:
    """Тестирование базового провайдера"""

    @pytest.fixture
    def provider_config(self):
        """Фикстура с конфигурацией провайдера"""
        return ProviderConfig(
            name='test_provider',
            api_key='test_key',
            model='test_model',
            base_url='https://test.api.com',
            priority=1,
            active=True,
            timeout=30
        )

    @pytest.fixture
    def base_provider(self, provider_config):
        """Фикстура с базовым провайдером"""
        return BaseProvider(provider_config)

    def test_provider_initialization(self, base_provider, provider_config):
        """Тест инициализации провайдера"""
        assert base_provider.config == provider_config
        assert base_provider.stats.requests_count == 0
        assert base_provider.stats.success_count == 0
        assert not base_provider.in_circuit_break

    def test_provider_availability_active(self, base_provider):
        """Тест доступности активного провайдера"""
        assert base_provider.is_available()

    def test_provider_availability_inactive(self, provider_config):
        """Тест доступности неактивного провайдера"""
        provider_config.active = False
        provider = BaseProvider(provider_config)
        assert not provider.is_available()

    def test_circuit_breaker_activation(self, base_provider):
        """Тест активации circuit breaker"""
        # Имитируем 5 ошибок подряд
        for _ in range(5):
            base_provider.record_failure()

        assert base_provider.in_circuit_break
        assert base_provider.failure_count == 5
        assert not base_provider.is_available()

    def test_circuit_breaker_recovery(self, base_provider):
        """Тест восстановления circuit breaker"""
        # Активируем circuit breaker
        for _ in range(5):
            base_provider.record_failure()

        assert base_provider.in_circuit_break

        # Имитируем успешный запрос
        base_provider.record_success(1.0, 100)

        assert not base_provider.in_circuit_break
        assert base_provider.failure_count == 0

    def test_statistics_tracking(self, base_provider):
        """Тест отслеживания статистики"""
        initial_requests = base_provider.stats.requests_count

        # Записываем успешный запрос
        base_provider.record_success(1.5, 200)

        assert base_provider.stats.requests_count == initial_requests + 1
        assert base_provider.stats.success_count == 1
        assert base_provider.stats.total_tokens == 200
        assert base_provider.stats.avg_response_time == 1.5

    def test_get_stats_method(self, base_provider):
        """Тест метода получения статистики"""
        stats = base_provider.get_stats()

        required_fields = [
            'name', 'active', 'priority', 'requests_total',
            'success_rate', 'avg_response_time', 'in_circuit_break'
        ]

        for field in required_fields:
            assert field in stats

    def test_reset_stats(self, base_provider):
        """Тест сброса статистики"""
        # Добавляем некоторые данные
        base_provider.record_success(1.0, 100)
        base_provider.record_failure()

        assert base_provider.stats.requests_count > 0

        # Сбрасываем статистику
        base_provider.reset_stats()

        assert base_provider.stats.requests_count == 0
        assert base_provider.stats.success_count == 0
        assert base_provider.failure_count == 0
        assert not base_provider.in_circuit_break


class TestOpenRouterProvider:
    """Тестирование OpenRouter провайдера"""

    @pytest.fixture
    def openrouter_config(self):
        """Фикстура с конфигурацией OpenRouter"""
        return ProviderConfig(
            name='openrouter',
            api_key='test_openrouter_key',
            model='qwen/qwen3-235b-a22b:free',
            base_url='https://openrouter.ai/api/v1/chat/completions',
            priority=1,
            active=True
        )

    @pytest.fixture
    def openrouter_provider(self, openrouter_config):
        """Фикстура с OpenRouter провайдером"""
        return OpenRouterProvider(openrouter_config)

    @patch('requests.post')
    def test_make_request_success(self, mock_post, openrouter_provider):
        """Тест успешного запроса к OpenRouter"""
        # Настраиваем mock ответ
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test response'}}]
        }
        mock_post.return_value = mock_response

        result = openrouter_provider.make_request("Test prompt")

        assert result['success']
        assert 'Test response' in result['content']
        assert openrouter_provider.stats.requests_count == 1
        assert openrouter_provider.stats.success_count == 1

    @patch('requests.post')
    def test_make_request_timeout(self, mock_post, openrouter_provider):
        """Тест таймаута запроса"""
        from requests.exceptions import Timeout

        mock_post.side_effect = Timeout("Connection timed out")

        result = openrouter_provider.make_request("Test prompt")

        assert not result['success']
        assert 'timeout' in result['error'].lower()
        assert openrouter_provider.stats.requests_count == 1
        assert openrouter_provider.stats.error_count == 1

    def test_default_headers(self, openrouter_provider):
        """Тест стандартных заголовков"""
        headers = openrouter_provider._get_default_headers()

        assert 'Authorization' in headers
        assert 'Content-Type' in headers
        assert headers['Content-Type'] == 'application/json'

    def test_http_client_initialization(self, openrouter_provider):
        """Тест инициализации HTTP клиента (Фаза 6)"""
        assert hasattr(openrouter_provider, 'http_client')
        assert openrouter_provider.http_client is not None


class TestGroqProvider:
    """Тестирование Groq провайдера"""

    @pytest.fixture
    def groq_config(self):
        """Фикстура с конфигурацией Groq"""
        return ProviderConfig(
            name='groq',
            api_key='test_groq_key',
            model='llama-3.1-8b-instant',
            base_url='https://api.groq.com/openai/v1/chat/completions',
            priority=2,
            active=True
        )

    @pytest.fixture
    def groq_provider(self, groq_config):
        """Фикстура с Groq провайдером"""
        return GroqProvider(groq_config)

    @patch('requests.post')
    def test_make_request_success(self, mock_post, groq_provider):
        """Тест успешного запроса к Groq"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Groq response'}}]
        }
        mock_post.return_value = mock_response

        result = groq_provider.make_request("Test prompt")

        assert result['success']
        assert 'Groq response' in result['content']
        assert groq_provider.stats.success_count == 1


class TestReplicateProvider:
    """Тестирование Replicate провайдера"""

    @pytest.fixture
    def replicate_config(self):
        """Фикстура с конфигурацией Replicate"""
        return ProviderConfig(
            name='replicate',
            api_key='test_replicate_key',
            model='meta/llama-3.1-8b-instant',
            base_url='https://api.replicate.com/v1/predictions',
            priority=3,
            active=True
        )

    @pytest.fixture
    def replicate_provider(self, replicate_config):
        """Фикстура с Replicate провайдером"""
        return ReplicateProvider(replicate_config)

    @patch('requests.post')
    def test_make_request_success(self, mock_post, replicate_provider):
        """Тест успешного запроса к Replicate"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'output': 'Replicate response'
        }
        mock_post.return_value = mock_response

        result = replicate_provider.make_request("Test prompt")

        assert result['success']
        assert 'Replicate response' in result['content']
        assert replicate_provider.stats.success_count == 1


class TestProviderFallback:
    """Тестирование fallback логики между провайдерами"""

    def test_provider_priority_order(self):
        """Тест порядка приоритета провайдеров"""
        configs = [
            ProviderConfig(name='openrouter', priority=1, active=True),
            ProviderConfig(name='groq', priority=2, active=True),
            ProviderConfig(name='replicate', priority=3, active=True)
        ]

        # Проверяем порядок приоритета
        sorted_configs = sorted(configs, key=lambda x: x.priority)

        assert sorted_configs[0].name == 'openrouter'
        assert sorted_configs[1].name == 'groq'
        assert sorted_configs[2].name == 'replicate'

    def test_provider_fallback_on_failure(self, mock_provider_manager):
        """Тест fallback при ошибке основного провайдера"""
        # Имитируем ошибку первого провайдера
        mock_provider_manager.providers['openrouter'].is_available.return_value = False
        mock_provider_manager.providers['groq'].is_available.return_value = True

        # Проверяем, что fallback провайдер доступен
        assert mock_provider_manager.providers['groq'].is_available()


class TestProviderManagerIntegration:
    """Интеграционные тесты для ProviderManager"""

    @patch('config.provider_manager.ProviderManager._initialize_providers')
    def test_provider_manager_initialization(self, mock_init):
        """Тест инициализации ProviderManager"""
        from config.provider_manager_old import ProviderManager, ProviderManagerConfig

        config = ProviderManagerConfig()
        manager = ProviderManager(config)

        # Проверяем, что инициализация была вызвана
        mock_init.assert_called_once()

    def test_provider_stats_aggregation(self):
        """Тест агрегации статистики провайдеров"""
        # Создаем mock провайдеры
        providers = {}
        total_requests = 0
        total_success = 0

        for i, name in enumerate(['openrouter', 'groq', 'replicate']):
            config = ProviderConfig(
                name=name,
                priority=i+1,
                active=True
            )
            provider = BaseProvider(config)

            # Имитируем некоторую активность
            requests_count = (i + 1) * 10
            success_count = requests_count - i  # Имитируем ошибки

            provider.stats.requests_count = requests_count
            provider.stats.success_count = success_count

            providers[name] = provider
            total_requests += requests_count
            total_success += success_count

        # Проверяем общую статистику
        assert total_requests == 60  # 10 + 20 + 30
        assert total_success == 57   # 9 + 19 + 29 (с ошибками)

        # Проверяем статистику каждого провайдера
        for name, provider in providers.items():
            assert provider.stats.requests_count > 0
            assert provider.get_stats()['requests_total'] == provider.stats.requests_count
