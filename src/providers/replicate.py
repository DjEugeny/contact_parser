#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Replicate провайдер
Фаза 5: Архитектурная оптимизация
"""

import aiohttp
import asyncio
import json
import time
from typing import Dict, Any, Optional
from .base_provider import BaseProvider, ProviderConfig


class ReplicateProvider(BaseProvider):
    """🔧 Replicate LLM провайдер"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.session = None  # Will be created in async context
        # Replicate использует более длительные таймауты
        self.config.timeout = 120  # 2 минуты

    def _get_default_headers(self) -> Dict[str, str]:
        """📋 Стандартные headers для Replicate"""
        return {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
        }

    async def make_request(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        🚀 Запрос к Replicate API

        Args:
            request_data: Данные запроса с prompt или messages
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ от LLM
        """
        if not self.is_available():
            raise RuntimeError(f"❌ Провайдер {self.config.name} недоступен")

        # Извлекаем prompt из request_data
        prompt = request_data.get('prompt')
        if not prompt:
            # Если нет prompt, пытаемся извлечь из messages
            messages = request_data.get('messages', [])
            if isinstance(messages, list) and len(messages) > 0:
                # Берем последнее сообщение пользователя
                for msg in reversed(messages):
                    if msg.get('role') == 'user':
                        prompt = msg.get('content', '')
                        break
            
            if not prompt:
                raise ValueError("❌ Не найден prompt в request_data")

        # Параметры запроса для DeepSeek V3.1 на Replicate
        # Оптимизированы под контекстное окно 128K токенов
        temperature = request_data.get('temperature', kwargs.get('temperature', 0.2))  # Повышено для более креативных ответов
        max_tokens = request_data.get('max_tokens', kwargs.get('max_tokens', 8000))   # Увеличено под возможности модели
        top_p = request_data.get('top_p', kwargs.get('top_p', 0.95))             # Оптимизировано для качества
        system_prompt = request_data.get('system_prompt', kwargs.get('system_prompt', "You are a helpful assistant that extracts contact information from text."))

        payload = {
            "version": self.config.model,
            "input": {
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "system_prompt": system_prompt
            }
        }

        try:
            start_time = time.time()

            # Создание предсказания
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.base_url,
                    json=payload,
                    headers=self.config.headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 201:
                        error_text = await response.text()
                        error_msg = f"HTTP {response.status}: {error_text}"
                        self.record_failure("http_error")
                        raise RuntimeError(f"❌ Ошибка создания предсказания Replicate: {error_msg}")

                    prediction = await response.json()
                    prediction_id = prediction.get('id')

                    if not prediction_id:
                        raise ValueError("❌ Не получен ID предсказания от Replicate")

                # Ожидание завершения предсказания
                result = await self._wait_for_prediction(prediction_id)
            response_time = time.time() - start_time

            # Извлечение ответа
            if 'output' in result:
                content = result['output']
                
                # Обработка случая, когда content является списком
                if isinstance(content, list):
                    # ИСПРАВЛЕНИЕ: Replicate возвращает список символов, склеиваем БЕЗ пробелов
                    content = ''.join(str(item) for item in content)
                elif not isinstance(content, str):
                    content = str(content)

                # Подсчет токенов (примерная оценка)
                tokens_used = len(content.split()) * 1.3

                self.record_success(response_time, int(tokens_used))

                return {
                    'content': content,
                    'provider': 'replicate',
                    'model': self.config.model,
                    'tokens_used': int(tokens_used),
                    'response_time': response_time,
                    'prediction_id': prediction_id
                }
            else:
                raise ValueError("❌ Пустой output от Replicate")

        except aiohttp.ClientError as e:
            self.record_failure("network_error")
            raise RuntimeError(f"❌ Сетевая ошибка Replicate: {str(e)}")
        except Exception as e:
            self.record_failure("unknown_error")
            raise RuntimeError(f"❌ Неожиданная ошибка Replicate: {str(e)}")

    async def _wait_for_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """
        ⏳ Ожидание завершения предсказания Replicate

        Args:
            prediction_id: ID предсказания

        Returns:
            dict: Результат предсказания
        """
        status_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"

        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(
                    status_url,
                    headers=self.config.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(f"❌ Ошибка проверки статуса: HTTP {response.status}")

                    result = await response.json()
                    status = result.get('status')

                    if status == 'succeeded':
                        return result
                    elif status == 'failed':
                        error = result.get('error', 'Unknown error')
                        raise RuntimeError(f"❌ Предсказание Replicate провалилось: {error}")
                    elif status == 'cancelled':
                        raise RuntimeError("❌ Предсказание Replicate отменено")

                # Ожидание перед следующей проверкой
                await asyncio.sleep(2)
