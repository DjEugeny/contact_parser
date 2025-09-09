#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Replicate провайдер
Фаза 5: Архитектурная оптимизация
"""

import requests
import json
import time
from typing import Dict, Any, Optional
from .base_provider import BaseProvider, ProviderConfig


class ReplicateProvider(BaseProvider):
    """🔧 Replicate LLM провайдер"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.session = requests.Session()
        # Replicate использует более длительные таймауты
        self.config.timeout = 120  # 2 минуты

    def _get_default_headers(self) -> Dict[str, str]:
        """📋 Стандартные headers для Replicate"""
        return {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
        }

    def make_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        🚀 Запрос к Replicate API

        Args:
            prompt: Текст для обработки
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ от LLM
        """
        if not self.is_available():
            raise RuntimeError(f"❌ Провайдер {self.config.name} недоступен")

        # Параметры запроса для Replicate
        temperature = kwargs.get('temperature', 0.1)
        max_tokens = kwargs.get('max_tokens', 4000)

        payload = {
            "version": self.config.model,
            "input": {
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 0.9,
                "system_prompt": "You are a helpful assistant that extracts contact information from text."
            }
        }

        try:
            start_time = time.time()

            # Создание предсказания
            response = self.session.post(
                self.config.base_url,
                json=payload,
                headers=self.config.headers,
                timeout=self.config.timeout
            )

            if response.status_code != 201:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.record_failure("http_error")
                raise RuntimeError(f"❌ Ошибка создания предсказания Replicate: {error_msg}")

            prediction = response.json()
            prediction_id = prediction.get('id')

            if not prediction_id:
                raise ValueError("❌ Не получен ID предсказания от Replicate")

            # Ожидание завершения предсказания
            result = self._wait_for_prediction(prediction_id)
            response_time = time.time() - start_time

            # Извлечение ответа
            if 'output' in result:
                content = result['output']

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

        except requests.exceptions.RequestException as e:
            self.record_failure("network_error")
            raise RuntimeError(f"❌ Сетевая ошибка Replicate: {str(e)}")
        except Exception as e:
            self.record_failure("unknown_error")
            raise RuntimeError(f"❌ Неожиданная ошибка Replicate: {str(e)}")

    def _wait_for_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """
        ⏳ Ожидание завершения предсказания Replicate

        Args:
            prediction_id: ID предсказания

        Returns:
            dict: Результат предсказания
        """
        status_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"

        while True:
            response = self.session.get(
                status_url,
                headers=self.config.headers,
                timeout=30
            )

            if response.status_code != 200:
                raise RuntimeError(f"❌ Ошибка проверки статуса: HTTP {response.status_code}")

            result = response.json()
            status = result.get('status')

            if status == 'succeeded':
                return result
            elif status == 'failed':
                error = result.get('error', 'Unknown error')
                raise RuntimeError(f"❌ Предсказание Replicate провалилось: {error}")
            elif status == 'cancelled':
                raise RuntimeError("❌ Предсказание Replicate отменено")

            # Ожидание перед следующей проверкой
            time.sleep(2)
