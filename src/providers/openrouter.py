#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 OpenRouter провайдер
Фаза 5: Архитектурная оптимизация
"""

import requests
import json
from typing import Dict, Any, Optional
from .base_provider import BaseProvider, ProviderConfig


class OpenRouterProvider(BaseProvider):
    """🔧 OpenRouter LLM провайдер"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.session = requests.Session()

    def _get_default_headers(self) -> Dict[str, str]:
        """📋 Стандартные headers для OpenRouter"""
        return {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://localhost:3000',
            'X-Title': 'Contact Extractor LLM'
        }

    def make_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        🚀 Запрос к OpenRouter API

        Args:
            prompt: Текст для обработки
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ от LLM
        """
        if not self.is_available():
            raise RuntimeError(f"❌ Провайдер {self.config.name} недоступен")

        # Параметры запроса для DeepSeek V3.1
        # Оптимизированы под контекстное окно 128K токенов
        temperature = kwargs.get('temperature', 0.2)  # Повышено для более креативных ответов
        max_tokens = kwargs.get('max_tokens', 8000)   # Увеличено под возможности модели
        top_p = kwargs.get('top_p', 0.95)             # Оптимизировано для качества
        stream = kwargs.get('stream', False)          # Поддержка стриминга

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream
        }

        try:
            import time
            start_time = time.time()

            response = self.session.post(
                self.config.base_url,
                json=payload,
                headers=self.config.headers,
                timeout=self.config.timeout
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()

                # Извлечение ответа
                if 'choices' in result and result['choices']:
                    content = result['choices'][0]['message']['content']

                    # Подсчет токенов (примерная оценка)
                    tokens_used = len(content.split()) * 1.3  # Грубая оценка

                    self.record_success(response_time, int(tokens_used))

                    return {
                        'content': content,
                        'provider': 'openrouter',
                        'model': self.config.model,
                        'tokens_used': int(tokens_used),
                        'response_time': response_time
                    }
                else:
                    raise ValueError("❌ Неверный формат ответа от OpenRouter")

            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.record_failure("http_error")
                raise RuntimeError(f"❌ Ошибка OpenRouter API: {error_msg}")

        except requests.exceptions.RequestException as e:
            self.record_failure("network_error")
            raise RuntimeError(f"❌ Сетевая ошибка OpenRouter: {str(e)}")
        except Exception as e:
            self.record_failure("unknown_error")
            raise RuntimeError(f"❌ Неожиданная ошибка OpenRouter: {str(e)}")
