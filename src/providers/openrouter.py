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
from typing import Dict, Any, Optional
from .base_provider import BaseProvider, ProviderConfig


class OpenRouterProvider(BaseProvider):
    """🔧 OpenRouter LLM провайдер"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
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

    async def make_request(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        🚀 Запрос к OpenRouter API

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

                            # Извлечение ответа
                            if 'choices' in result and result['choices']:
                                content = result['choices'][0]['message']['content']
                                # Контент извлечен

                                # Подсчет токенов из usage или примерная оценка
                                usage = result.get('usage', {})
                                tokens_used = usage.get('total_tokens', len(content.split()) * 1.3)

                                self.record_success(response_time, int(tokens_used))
                                # Успешный запрос записан

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
