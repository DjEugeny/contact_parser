#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Groq провайдер
Фаза 5: Архитектурная оптимизация
"""

import requests
import json
from typing import Dict, Any, Optional
from .base_provider import BaseProvider, ProviderConfig


class GroqProvider(BaseProvider):
    """🔧 Groq LLM провайдер"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.session = requests.Session()

    def _get_default_headers(self) -> Dict[str, str]:
        """📋 Стандартные headers для Groq"""
        return {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
        }

    def make_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        🚀 Запрос к Groq API

        Args:
            prompt: Текст для обработки
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ от LLM
        """
        if not self.is_available():
            raise RuntimeError(f"❌ Провайдер {self.config.name} недоступен")

        # Параметры запроса
        temperature = kwargs.get('temperature', 0.1)
        max_tokens = kwargs.get('max_tokens', 4000)

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
            "top_p": 0.9,
            "stream": False
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
                        'provider': 'groq',
                        'model': self.config.model,
                        'tokens_used': int(tokens_used),
                        'response_time': response_time
                    }
                else:
                    raise ValueError("❌ Неверный формат ответа от Groq")

            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.record_failure("http_error")
                raise RuntimeError(f"❌ Ошибка Groq API: {error_msg}")

        except requests.exceptions.RequestException as e:
            self.record_failure("network_error")
            raise RuntimeError(f"❌ Сетевая ошибка Groq: {str(e)}")
        except Exception as e:
            self.record_failure("unknown_error")
            raise RuntimeError(f"❌ Неожиданная ошибка Groq: {str(e)}")
