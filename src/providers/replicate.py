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
import logging
from typing import Dict, Any, Optional
from .base_provider import BaseProvider, ProviderConfig
from .exceptions import EmptyResponseError

logger = logging.getLogger(__name__)


class ReplicateProvider(BaseProvider):
    """🔧 Replicate LLM провайдер"""

    def __init__(self, config: ProviderConfig, config_manager=None):
        super().__init__(config)
        self.config_manager = config_manager
        self.session = None  # Will be created in async context
        # Replicate использует более длительные таймауты
        self.config.timeout = 120  # 2 минуты

    def _get_default_headers(self) -> Dict[str, str]:
        """📋 Стандартные headers для Replicate"""
        return {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
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
        switched = self.config_manager.models_manager.report_error('replicate', error_message)
        
        # Также уведомляем config_manager для статистики
        # Но НЕ блокируем провайдер при ошибках модели
        if hasattr(self.config_manager, 'record_provider_failure'):
            self.config_manager.record_provider_failure(
                'Replicate',
                error_message,
                is_rate_limit=is_rate_limit,
                is_model_error=is_model_error
            )
        
        if switched:
            # Получаем новую модель
            new_model = self.config_manager.models_manager.get_current_model('replicate')
            if new_model:
                # Обновляем конфигурацию провайдера
                old_model = self.config.model
                self.config.model = new_model.name
                print(f"🔄 Replicate: переключение модели {old_model} → {new_model.name}")
                return True
        
        return False

    async def make_request(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        🚀 Запрос к Replicate API с автоматическим fallback

        Args:
            request_data: Данные запроса с prompt или messages
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
        raise RuntimeError(f"❌ Replicate: все модели fallback исчерпаны после {max_fallback_attempts} попыток")
    
    async def _make_single_request(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        🚀 Выполнение одного запроса к Replicate API

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
        
        # Валидация context length перед запросом
        if self.config_manager and hasattr(self.config_manager, 'models_manager'):
            if self.config_manager.models_manager:
                # Оцениваем размер входного текста (prompt + system_prompt)
                input_text = f"{system_prompt}\n{prompt}"
                estimated_input_tokens = self.config_manager.models_manager.estimate_tokens(input_text)
                total_tokens_needed = estimated_input_tokens + max_tokens
                
                logger.info(
                    f"📊 Context length check: ~{estimated_input_tokens} input tokens + "
                    f"{max_tokens} output tokens = {total_tokens_needed} total"
                )
                
                # Получаем модель с учетом context length
                suitable_model = self.config_manager.models_manager.get_current_model(
                    'replicate',
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
                
                # Проверка на пустой ответ
                if not content or len(content.strip()) == 0:
                    # Получаем информацию о запросе для логирования
                    request_id = prediction_id
                    input_length = len(prompt)
                    
                    logger.error(
                        f"❌ Empty response from Replicate model '{self.config.model}' "
                        f"(request_id: {request_id}, input_length: {input_length} chars)"
                    )
                    
                    # Выбрасываем EmptyResponseError
                    raise EmptyResponseError(
                        model_name=self.config.model,
                        request_id=request_id,
                        input_length=input_length
                    )

                # Подсчет токенов (примерная оценка)
                tokens_used = len(content.split()) * 1.3

                self.record_success(response_time, int(tokens_used))
                
                # Сброс на первую модель после успешного запроса
                if self.config_manager and hasattr(self.config_manager, 'models_manager'):
                    if self.config_manager.models_manager:
                        self.config_manager.models_manager.reset_to_first_model('replicate')

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
