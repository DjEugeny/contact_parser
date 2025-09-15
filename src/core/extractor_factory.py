#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏭 Фабрика для создания ContactExtractor с Dependency Injection
Фаза 5: Архитектурная оптимизация
"""

from pathlib import Path
from typing import Optional
from .extractor import ContactExtractor, ExtractorConfig, RetryConfig
from .chunker import ChunkingConfig
from ..config import UnifiedConfigManager
from ..phone_normalizer import PhoneNormalizer
from .validator import LLMResponseValidator


class ExtractorFactory:
    """🏭 Фабрика для создания ContactExtractor с правильной инициализацией зависимостей"""

    @staticmethod
    def create_extractor(
        test_mode: bool = False,
        config_path: Optional[Path] = None,
        prompts_dir: Optional[Path] = None
    ) -> ContactExtractor:
        """
        🏗️ Создание ContactExtractor со всеми зависимостями

        Args:
            test_mode: Режим тестирования
            config_path: Путь к файлу конфигурации провайдеров
            prompts_dir: Директория с промптами

        Returns:
            ContactExtractor: Полностью настроенный экземпляр
        """

        # 1. Использование унифицированного конфигурационного менеджера
        unified_config = UnifiedConfigManager()

        # Получение настроек провайдеров из .env
        llm_providers = unified_config.get_llm_providers()

        # Создание ProviderManager на основе унифицированной конфигурации
        from ..config.provider_manager_old import ProviderManager, ProviderManagerConfig
        provider_config = ProviderManagerConfig(
            config_path=config_path,
            fallback_enabled=True,
            circuit_breaker_enabled=True,
            max_fallback_attempts=2
        )
        provider_manager = ProviderManager(provider_config)

        # Примечание: ProviderManager все еще использует старый подход с JSON,
        # но теперь он может быть обновлен для использования unified_config

        # 2. Создание нормализатора телефонов
        phone_normalizer = PhoneNormalizer()

        # 3. Создание JSON валидатора
        json_validator = LLMResponseValidator()

        # 4. Настройка конфигураций
        # Загружаем chunking конфигурацию из processing_config.json
        chunking_config = ChunkingConfig.load_from_file()

        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0
        )

        # 5. Создание основной конфигурации
        extractor_config = ExtractorConfig(
            provider_manager=provider_manager,
            phone_normalizer=phone_normalizer,
            json_validator=json_validator,
            chunking_config=chunking_config,
            retry_config=retry_config,
            prompts_dir=prompts_dir,
            test_mode=test_mode
        )

        # 6. Создание и возврат экстрактора
        return ContactExtractor(extractor_config)

    @staticmethod
    def create_test_extractor() -> ContactExtractor:
        """🧪 Создание экстрактора для тестирования"""
        return ExtractorFactory.create_extractor(
            test_mode=True,
            config_path=None,  # Используется конфигурация по умолчанию
            prompts_dir=None   # Используется директория по умолчанию
        )

    @staticmethod
    def validate_dependencies() -> bool:
        """
        ✅ Валидация всех зависимостей перед созданием экстрактора

        Returns:
            bool: True если все зависимости доступны
        """
        import os

        issues = []

        # Проверка API ключей только для активных провайдеров
        from ..config import UnifiedConfigManager
        unified_config = UnifiedConfigManager()
        llm_providers = unified_config.get_llm_providers()
        
        # Маппинг провайдеров к переменным окружения
        provider_key_mapping = {
            'OpenRouter': 'OPENROUTER_API_KEY',
            'Groq': 'GROQ_API_KEY', 
            'Replicate': 'REPLICATE_API_KEY'
        }
        
        missing_keys = []
        for provider in llm_providers:
            if provider.active:
                env_key = provider_key_mapping.get(provider.name)
                if env_key and not os.getenv(env_key):
                    missing_keys.append(env_key)

        if missing_keys:
            issues.append(f"Отсутствуют API ключи для активных провайдеров: {', '.join(missing_keys)}")

        # Проверка наличия промптов
        prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        required_prompts = [
            "unified_contact_extraction_structured.txt",
            "contact_extraction.txt"
        ]

        for prompt_file in required_prompts:
            prompt_path = prompts_dir / prompt_file
            if not prompt_path.exists():
                issues.append(f"Отсутствует промпт: {prompt_path}")

        # Проверка конфигурации провайдеров
        config_path = Path(__file__).parent.parent.parent / "config" / "providers.json"
        if not config_path.exists():
            issues.append(f"Отсутствует конфигурация провайдеров: {config_path}")

        if issues:
            print("❌ Проблемы с зависимостями:")
            for issue in issues:
                print(f"   - {issue}")
            return False

        print("✅ Все зависимости доступны")
        return True
