#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 OpenRouter провайдер
Фаза 5: Архитектурная оптимизация
"""

import aiohttp
import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional
from .base_provider import BaseProvider, ProviderConfig
from .exceptions import EmptyResponseError

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseProvider):
    """🔧 OpenRouter LLM провайдер"""

    def __init__(self, config: ProviderConfig, config_manager=None):
        super().__init__(config)
        self.config_manager = config_manager
        # Убеждаемся что headers установлены правильно
        if not self.config.headers:
            self.config.headers = self._get_default_headers()
        # OpenRouter требует больше времени для длинных запросов
        if self.config.timeout < 120:
            self.config.timeout = 120  # 2 минуты для больших промптов

    def _get_default_headers(self) -> Dict[str, str]:
        """📋 Стандартные headers для OpenRouter"""
        return {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://localhost:3000',
            'X-Title': 'Contact Parser LLM Request'
        }
    
    def _handle_error_with_fallback(self, error_message: str) -> bool:
        """
        🔄 Обработка ошибки с автоматическим fallback
        
        Args:
            error_message: Сообщение об ошибке
            
        Returns:
            True если произошло переключение модели
        """
        if not self.config_manager or not hasattr(self.config_manager, 'models_manager'):
            return False
        
        if not self.config_manager.models_manager:
            return False
        
        # Классифицируем ошибку
        error_lower = error_message.lower()
        is_rate_limit = '429' in error_message or 'rate limit' in error_lower
        is_model_error = any(pattern in error_lower for pattern in [
            'data policy', 'empty response', 'context length', 'model not found',
            'invalid model', 'model error'
        ])
        
        # Сообщаем об ошибке в ModelsManager
        switched = self.config_manager.models_manager.report_error('openrouter', error_message)
        
        # Также уведомляем config_manager для статистики
        # Но НЕ блокируем провайдер при ошибках модели
        if hasattr(self.config_manager, 'record_provider_failure'):
            self.config_manager.record_provider_failure(
                'OpenRouter',
                error_message,
                is_rate_limit=is_rate_limit,
                is_model_error=is_model_error
            )
        
        if switched:
            # Получаем новую модель
            new_model = self.config_manager.models_manager.get_current_model('openrouter')
            if new_model:
                # Обновляем конфигурацию провайдера
                old_model = self.config.model
                self.config.model = new_model.name
                print(f"🔄 OpenRouter: переключение модели {old_model} → {new_model.name}")
                return True
        
        return False

    async def make_request(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        🚀 Запрос к OpenRouter API с автоматическим fallback

        Args:
            request_data: Данные запроса с messages
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ от LLM
        """
        max_fallback_attempts = 3
        attempt = 0
        
        while attempt < max_fallback_attempts:
            try:
                return await self._make_single_request(request_data, **kwargs)
            except Exception as e:
                error_message = str(e)
                
                # Пытаемся переключиться на следующую модель
                switched = self._handle_error_with_fallback(error_message)
                
                if switched:
                    attempt += 1
                    # Повторяем запрос с новой моделью
                    continue
                else:
                    # Нет доступных fallback моделей, пробрасываем ошибку
                    raise
        
        # Если все попытки исчерпаны
        raise RuntimeError(f"❌ OpenRouter: все модели fallback исчерпаны после {max_fallback_attempts} попыток")
    
    async def _make_single_request(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        🚀 Выполнение одного запроса к OpenRouter API

        Args:
            request_data: Данные запроса с messages
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ от LLM
        """
        try:
            # Проверка доступности провайдера
            if not self.is_available():
                error_msg = f"❌ Провайдер {self.config.name} недоступен (Circuit Breaker: {self.in_circuit_break}, Active: {self.config.active})"
                raise RuntimeError(error_msg)

            # Валидация входных данных
            if not isinstance(request_data, dict):
                error_msg = f"❌ request_data должен быть словарем, получен: {type(request_data)}"
                raise ValueError(error_msg)

            # Извлекаем messages из request_data
            messages = request_data.get('messages', [])
            if not messages:
                error_msg = f"❌ Не найдены messages в request_data. Доступные ключи: {list(request_data.keys())}"
                raise ValueError(error_msg)

            # Валидация messages
            if not isinstance(messages, list) or len(messages) == 0:
                error_msg = f"❌ messages должен быть непустым списком, получен: {type(messages)} с длиной {len(messages) if isinstance(messages, list) else 'N/A'}"
                raise ValueError(error_msg)

            # Параметры запроса для DeepSeek V3.1
            # Оптимизированы под контекстное окно 128K токенов
            temperature = request_data.get('temperature', kwargs.get('temperature', 0.2))
            max_tokens = request_data.get('max_tokens', kwargs.get('max_tokens', 8000))
            top_p = request_data.get('top_p', kwargs.get('top_p', 0.95))
            stream = request_data.get('stream', kwargs.get('stream', False))
            
            # Валидация context length перед запросом
            if self.config_manager and hasattr(self.config_manager, 'models_manager'):
                if self.config_manager.models_manager:
                    # Оцениваем размер входного текста
                    input_text = '\n'.join([msg.get('content', '') for msg in messages])
                    estimated_input_tokens = self.config_manager.models_manager.estimate_tokens(input_text)
                    total_tokens_needed = estimated_input_tokens + max_tokens
                    
                    logger.info(
                        f"📊 Context length check: ~{estimated_input_tokens} input tokens + "
                        f"{max_tokens} output tokens = {total_tokens_needed} total"
                    )
                    
                    # Получаем модель с учетом context length
                    suitable_model = self.config_manager.models_manager.get_current_model(
                        'openrouter',
                        estimated_tokens=total_tokens_needed
                    )
                    
                    if suitable_model:
                        # Обновляем модель если она изменилась
                        if suitable_model.name != self.config.model:
                            old_model = self.config.model
                            self.config.model = suitable_model.name
                            logger.info(
                                f"🔄 Модель изменена из-за context length: "
                                f"{old_model} → {suitable_model.name}"
                            )
                    else:
                        # Ни одна модель не подходит
                        error_msg = (
                            f"❌ Context length error: требуется ~{total_tokens_needed} токенов, "
                            f"но ни одна модель не имеет достаточного context window"
                        )
                        raise RuntimeError(error_msg)

            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "stream": stream
            }
            # Выполнение HTTP запроса
            start_time = time.time()

            # Формируем правильный URL
            url = self.config.base_url
            if not url.endswith('/chat/completions'):
                if url.endswith('/'):
                    url = url + 'chat/completions'
                else:
                    url = url + '/chat/completions'

            # Отправляем запрос к OpenRouter

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=self.config.headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            # JSON ответ получен
                            
                            # Проверяем наличие ошибки в ответе (OpenRouter может вернуть 200 с error)
                            if 'error' in result:
                                error_info = result.get('error', {})
                                error_message = error_info.get('message', 'Unknown error')
                                error_code = error_info.get('code', 'unknown')
                                error_metadata = error_info.get('metadata', {})
                                
                                # Специальная обработка для ошибок приватности
                                if 'data policy' in error_message.lower() or 'publish' in error_message.lower():
                                    error_msg = f"❌ OpenRouter data policy error: {error_message}. Проверьте настройки приватности в https://openrouter.ai/settings/integrations"
                                    self.record_failure("data_policy_error")
                                    raise RuntimeError(error_msg)
                                
                                # Общая обработка ошибок
                                error_msg = f"❌ OpenRouter API error: {error_message} (code: {error_code})"
                                if error_metadata:
                                    error_msg += f", metadata: {error_metadata}"
                                self.record_failure("api_error")
                                raise RuntimeError(error_msg)

                            # Извлечение ответа
                            if 'choices' in result and result['choices']:
                                content = result['choices'][0]['message']['content']
                                # Контент извлечен
                                
                                # Проверка на пустой ответ
                                if not content or len(content.strip()) == 0:
                                    # Получаем информацию о запросе для логирования
                                    request_id = result.get('id', 'unknown')
                                    input_length = sum(len(msg.get('content', '')) for msg in messages)
                                    
                                    logger.error(
                                        f"❌ Empty response from OpenRouter model '{self.config.model}' "
                                        f"(request_id: {request_id}, input_length: {input_length} chars)"
                                    )
                                    
                                    # Выбрасываем EmptyResponseError
                                    raise EmptyResponseError(
                                        model_name=self.config.model,
                                        request_id=request_id,
                                        input_length=input_length
                                    )

                                # Подсчет токенов из usage или примерная оценка
                                usage = result.get('usage', {})
                                tokens_used = usage.get('total_tokens', len(content.split()) * 1.3)

                                self.record_success(response_time, int(tokens_used))
                                # Успешный запрос записан
                                
                                # Сброс на первую модель после успешного запроса
                                if self.config_manager and hasattr(self.config_manager, 'models_manager'):
                                    if self.config_manager.models_manager:
                                        self.config_manager.models_manager.reset_to_first_model('openrouter')

                                return {
                                    'content': content,
                                    'provider': 'OpenRouter',
                                    'model': self.config.model,
                                    'usage': usage,
                                    'response_time': response_time
                                }
                            else:
                                error_msg = f"❌ Неверный формат ответа от OpenRouter. Ключи: {list(result.keys())}"
                                self.record_failure("response_format_error")
                                raise ValueError(error_msg)
                        
                        except json.JSONDecodeError as e:
                            error_msg = f"❌ Ошибка парсинга JSON ответа: {str(e)}"
                            self.record_failure("json_parse_error")
                            raise RuntimeError(error_msg)

                    else:
                        try:
                            error_text = await response.text()
                            error_msg = f"HTTP {response.status}: {error_text}"
                            self.record_failure("http_error")
                            raise RuntimeError(f"❌ Ошибка OpenRouter API: {error_msg}")
                        except Exception as e:
                            error_msg = f"HTTP {response.status}: Не удалось прочитать тело ответа ({str(e)})"
                            self.record_failure("http_error")
                            raise RuntimeError(f"❌ Ошибка OpenRouter API: {error_msg}")

        except asyncio.TimeoutError as e:
            self.record_failure("timeout_error")
            error_msg = f"❌ Таймаут OpenRouter: запрос превысил {self.config.timeout}с"
            raise RuntimeError(error_msg)
        
        except aiohttp.ClientError as e:
            self.record_failure("network_error")
            error_msg = f"❌ Сетевая ошибка OpenRouter: {str(e)} (тип: {type(e).__name__})"
            raise RuntimeError(error_msg)
        
        except (ValueError, RuntimeError) as e:
            # Эти ошибки уже обработаны выше, просто перебрасываем
            raise
        
        except Exception as e:
            self.record_failure("unknown_error")
            error_msg = f"❌ Неожиданная ошибка OpenRouter: {str(e)} (тип: {type(e).__name__})"
            raise RuntimeError(error_msg)
