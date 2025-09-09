#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎛️ Менеджер провайдеров LLM (УСТАРЕВШИЙ)
Фаза 5+: Используйте UnifiedConfigManager вместо этого модуля

⚠️  ВНИМАНИЕ: Этот модуль оставлен для совместимости.
    Новая архитектура использует UnifiedConfigManager из config_manager.py
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from ..providers.base_provider import BaseProvider, ProviderConfig
from ..providers.openrouter import OpenRouterProvider
from ..providers.groq import GroqProvider
from ..providers.replicate import ReplicateProvider


@dataclass
class ProviderManagerConfig:
    """📋 Конфигурация менеджера провайдеров"""
    config_path: Optional[Path] = None
    fallback_enabled: bool = True
    circuit_breaker_enabled: bool = True
    max_fallback_attempts: int = 2


class ProviderManager:
    """🎛️ Менеджер для управления LLM провайдерами"""

    def __init__(self, config: ProviderManagerConfig):
        self.config = config
        self.providers: Dict[str, BaseProvider] = {}
        self.provider_configs: Dict[str, Dict[str, Any]] = {}

        # Загрузка конфигурации провайдеров
        self._load_provider_config()

        # Инициализация провайдеров
        self._initialize_providers()

        print(f"🎛️ ProviderManager инициализирован с {len(self.providers)} провайдерами")

    def _load_provider_config(self):
        """📁 Загрузка конфигурации провайдеров из providers.json"""
        config_path = self.config.config_path or Path(__file__).parent.parent.parent / "config" / "providers.json"

        if config_path.exists():
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.provider_configs = config_data.get('provider_settings', {})
                    print(f"✅ Загружена конфигурация провайдеров из {config_path}")
            except Exception as e:
                print(f"⚠️  Ошибка загрузки конфигурации провайдеров: {e}")
                self.provider_configs = {}
        else:
            print(f"⚠️  Файл конфигурации провайдеров не найден: {config_path}")
            self.provider_configs = {}

    def _initialize_providers(self):
        """🔧 Инициализация всех провайдеров из .env файла"""

        # OpenRouter - все настройки из .env
        openrouter_config = ProviderConfig(
            name="OpenRouter",
            api_key=os.getenv('OPENROUTER_API_KEY', ''),
            model=os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-235b-a22b:free'),
            base_url=os.getenv('OPENROUTER_BASE_URL', "https://openrouter.ai/api/v1/chat/completions"),
            priority=self.provider_configs.get('openrouter', {}).get('priority', 2),  # Изменен приоритет
            active=self.provider_configs.get('openrouter', {}).get('enabled', True)
        )

        if openrouter_config.api_key:
            self.providers['openrouter'] = OpenRouterProvider(openrouter_config)
            print(f"✅ Инициализирован провайдер: {openrouter_config.name}")
        else:
            print(f"⚠️  Пропущен провайдер OpenRouter: отсутствует API ключ")

        # Groq - все настройки из .env
        groq_config = ProviderConfig(
            name="Groq",
            api_key=os.getenv('GROQ_API_KEY', ''),
            model=os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant'),
            base_url=os.getenv('GROQ_BASE_URL', "https://api.groq.com/openai/v1/chat/completions"),
            priority=self.provider_configs.get('groq', {}).get('priority', 3),  # Изменен приоритет
            active=self.provider_configs.get('groq', {}).get('enabled', True)
        )

        if groq_config.api_key:
            self.providers['groq'] = GroqProvider(groq_config)
            print(f"✅ Инициализирован провайдер: {groq_config.name}")
        else:
            print(f"⚠️  Пропущен провайдер Groq: отсутствует API ключ")

        # Replicate - все настройки из .env
        replicate_config = ProviderConfig(
            name="Replicate",
            api_key=os.getenv('REPLICATE_API_KEY', ''),
            model=os.getenv('REPLICATE_MODEL', 'meta/llama-3.1-8b-instant'),
            base_url="https://api.replicate.com/v1/predictions",
            priority=self.provider_configs.get('replicate', {}).get('priority', 1),  # Высокий приоритет
            active=self.provider_configs.get('replicate', {}).get('enabled', True)
        )

        if replicate_config.api_key:
            self.providers['replicate'] = ReplicateProvider(replicate_config)
            print(f"✅ Инициализирован провайдер: {replicate_config.name}")
        else:
            print(f"⚠️  Пропущен провайдер Replicate: отсутствует API ключ")

        # Проверка доступности провайдеров
        active_count = sum(1 for p in self.providers.values() if p.is_available())
        print(f"📊 Активных провайдеров: {active_count}/{len(self.providers)}")

    def get_available_providers(self) -> List[BaseProvider]:
        """📋 Получить список доступных провайдеров"""
        available = [p for p in self.providers.values() if p.is_available()]
        # Сортировка по приоритету (высший приоритет первый)
        return sorted(available, key=lambda p: p.config.priority, reverse=True)

    def get_provider_by_name(self, name: str) -> Optional[BaseProvider]:
        """🔍 Получить провайдер по имени"""
        return self.providers.get(name.lower())

    def make_request_with_fallback(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        🚀 Выполнить запрос с fallback системой

        Args:
            prompt: Текст запроса
            **kwargs: Дополнительные параметры

        Returns:
            dict: Ответ от LLM

        Raises:
            RuntimeError: Если все провайдеры недоступны
        """
        available_providers = self.get_available_providers()

        if not available_providers:
            raise RuntimeError("❌ Нет доступных LLM провайдеров")

        errors = []

        for provider in available_providers:
            try:
                print(f"🔄 Попытка запроса к {provider.config.name}...")
                result = provider.make_request(prompt, **kwargs)

                # Добавление информации о провайдере в результат
                result['used_provider'] = provider.config.name
                result['fallback_used'] = len(errors) > 0

                print(f"✅ Успешный ответ от {provider.config.name}")
                return result

            except Exception as e:
                error_msg = f"{provider.config.name}: {str(e)}"
                errors.append(error_msg)
                print(f"❌ Ошибка {error_msg}")

                # Ограничение количества попыток fallback
                if len(errors) >= self.config.max_fallback_attempts:
                    break

        # Все провайдеры провалились
        error_summary = "; ".join(errors)
        raise RuntimeError(f"❌ Все провайдеры недоступны: {error_summary}")

    def get_stats(self) -> Dict[str, Any]:
        """📊 Получить статистику всех провайдеров"""
        stats = {}
        for name, provider in self.providers.items():
            stats[name] = provider.get_stats()
        return stats

    def reset_all_stats(self):
        """🔄 Сбросить статистику всех провайдеров"""
        for provider in self.providers.values():
            provider.reset_stats()
        print("✅ Статистика всех провайдеров сброшена")

    def reload_config(self):
        """🔄 Перезагрузить конфигурацию провайдеров"""
        self._load_provider_config()
        # Переинициализация провайдеров с новыми настройками
        self._initialize_providers()
        print("✅ Конфигурация провайдеров перезагружена")
