#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Валидатор конфигурации системы
Фаза 5: Архитектурная оптимизация
"""

import os
import socket
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .config_manager import UnifiedConfigManager
from .paths import PROJECT_ROOT, get_config_path


@dataclass
class ValidationResult:
    """📋 Результат валидации"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]


class ConfigValidator:
    """🔍 Валидатор конфигурации Contact Parser"""

    def __init__(self):
        # Получаем активные провайдеры из конфигурации
        self.config_manager = UnifiedConfigManager()
        
        # Маппинг провайдеров к переменным окружения
        self.provider_env_mapping = {
            'OpenRouter': 'OPENROUTER_API_KEY',
            'Groq': 'GROQ_API_KEY',
            'Replicate': 'REPLICATE_API_KEY'
        }
        
        self.optional_env_vars = [
            'OPENROUTER_MODEL',
            'GROQ_MODEL',
            'REPLICATE_MODEL',
            'OPENROUTER_BASE_URL',
            'GROQ_BASE_URL'
        ]

    def validate_all(self) -> ValidationResult:
        """
        🔍 Полная валидация всей конфигурации системы

        Returns:
            ValidationResult: Результат валидации
        """
        errors = []
        warnings = []
        info = []

        # 1. Валидация переменных окружения
        env_result = self.validate_environment_variables()
        errors.extend(env_result.errors)
        warnings.extend(env_result.warnings)
        info.extend(env_result.info)

        # 2. Валидация файлов конфигурации
        config_result = self.validate_config_files()
        errors.extend(config_result.errors)
        warnings.extend(config_result.warnings)
        info.extend(config_result.info)

        # 3. Валидация сетевых настроек
        network_result = self.validate_network_connectivity()
        errors.extend(network_result.errors)
        warnings.extend(network_result.warnings)
        info.extend(network_result.info)

        # 4. Валидация зависимостей
        deps_result = self.validate_dependencies()
        errors.extend(deps_result.errors)
        warnings.extend(deps_result.warnings)
        info.extend(deps_result.info)

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def validate_environment_variables(self) -> ValidationResult:
        """🔐 Валидация переменных окружения"""
        errors = []
        warnings = []
        info = []

        # Получаем активные провайдеры и проверяем только их ключи
        active_providers = self.config_manager.get_llm_providers()
        
        for provider in active_providers:
            if provider.active:
                env_key = self.provider_env_mapping.get(provider.name)
                if env_key:
                    value = os.getenv(env_key)
                    if not value:
                        errors.append(f"Отсутствует обязательная переменная окружения: {env_key}")
                    elif len(value.strip()) < 10:
                        warnings.append(f"Переменная окружения {env_key} выглядит слишком короткой")
                    else:
                        info.append(f"✅ {env_key}: установлена")

        # Проверка опциональных переменных
        for var in self.optional_env_vars:
            value = os.getenv(var)
            if value:
                info.append(f"ℹ️  {var}: установлена ({value})")
            else:
                info.append(f"ℹ️  {var}: используется значение по умолчанию")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def validate_config_files(self) -> ValidationResult:
        """📁 Валидация файлов конфигурации"""
        errors = []
        warnings = []
        info = []

        config_files = {
            'providers.json': get_config_path('providers.json'),
            'service_account.json': get_config_path('service_account.json'),
            '.env': PROJECT_ROOT / ".env"
        }

        required_files = ['providers.json', '.env']
        optional_files = ['service_account.json']

        # Проверка обязательных файлов
        for file_key in required_files:
            file_path = config_files[file_key]
            if not file_path.exists():
                errors.append(f"Отсутствует обязательный файл конфигурации: {file_path}")
            else:
                info.append(f"✅ {file_key}: найден")

                # Проверка размера файла
                if file_path.stat().st_size == 0:
                    warnings.append(f"Файл конфигурации пустой: {file_path}")

        # Проверка опциональных файлов
        for file_key in optional_files:
            file_path = config_files[file_key]
            if file_path.exists():
                info.append(f"✅ {file_key}: найден")
            else:
                warnings.append(f"Опциональный файл конфигурации отсутствует: {file_path}")

        # Специфическая валидация providers.json
        providers_path = config_files['providers.json']
        if providers_path.exists():
            providers_result = self._validate_providers_config(providers_path)
            errors.extend(providers_result.errors)
            warnings.extend(providers_result.warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def _validate_providers_config(self, config_path: Path) -> ValidationResult:
        """🔧 Специфическая валидация providers.json"""
        errors = []
        warnings = []

        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Проверка структуры
            if 'provider_settings' not in config:
                errors.append("В providers.json отсутствует секция 'provider_settings'")
                return ValidationResult(False, errors, warnings, [])

            provider_settings = config['provider_settings']

            # Проверка каждого провайдера
            required_providers = ['openrouter', 'groq', 'replicate']
            for provider in required_providers:
                if provider not in provider_settings:
                    warnings.append(f"В providers.json отсутствует настройка для провайдера: {provider}")
                    continue

                settings = provider_settings[provider]

                # Проверка обязательных полей
                if 'enabled' not in settings:
                    warnings.append(f"Для провайдера {provider} не указан статус enabled")
                if 'priority' not in settings:
                    warnings.append(f"Для провайдера {provider} не указан priority")

        except json.JSONDecodeError as e:
            errors.append(f"Ошибка парсинга providers.json: {e}")
        except Exception as e:
            errors.append(f"Неожиданная ошибка валидации providers.json: {e}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=[]
        )

    def validate_network_connectivity(self) -> ValidationResult:
        """🌐 Валидация сетевых настроек"""
        errors = []
        warnings = []
        info = []

        # Проверка DNS
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            info.append("✅ Сетевое подключение: доступно")
        except OSError as e:
            errors.append(f"Сетевое подключение недоступно: {e}")

        # Проверка доступа к основным API
        api_endpoints = [
            ("OpenRouter", "https://openrouter.ai"),
            ("Groq", "https://api.groq.com"),
            ("Replicate", "https://api.replicate.com")
        ]

        for name, url in api_endpoints:
            try:
                import requests
                response = requests.head(url, timeout=5)
                if response.status_code < 400:
                    info.append(f"✅ {name} API: доступен")
                else:
                    warnings.append(f"{name} API вернул статус {response.status_code}")
            except Exception as e:
                warnings.append(f"{name} API недоступен: {str(e)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def validate_dependencies(self) -> ValidationResult:
        """📦 Валидация Python зависимостей"""
        errors = []
        warnings = []
        info = []

        # Список критически важных зависимостей
        critical_deps = [
            'requests',
            'jsonschema',
            'phonenumbers',
            'pathlib'
        ]

        optional_deps = [
            'tiktoken',
            'google.cloud.vision'
        ]

        # Проверка критических зависимостей
        for dep in critical_deps:
            try:
                __import__(dep)
                info.append(f"✅ {dep}: установлена")
            except ImportError:
                errors.append(f"Отсутствует критическая зависимость: {dep}")

        # Проверка опциональных зависимостей
        for dep in optional_deps:
            try:
                __import__(dep.replace('.', '_'))
                info.append(f"✅ {dep}: установлена")
            except ImportError:
                warnings.append(f"Опциональная зависимость отсутствует: {dep}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )

    def print_validation_report(self, result: ValidationResult):
        """📊 Вывод отчета о валидации"""
        print("🔍 ОТЧЕТ ВАЛИДАЦИИ КОНФИГУРАЦИИ")
        print("=" * 50)

        if result.is_valid:
            print("✅ КОНФИГУРАЦИЯ ВАЛИДНА")
        else:
            print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ")

        if result.errors:
            print(f"\n❌ КРИТИЧЕСКИЕ ОШИБКИ ({len(result.errors)}):")
            for error in result.errors:
                print(f"   - {error}")

        if result.warnings:
            print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"   - {warning}")

        if result.info:
            print(f"\nℹ️  ИНФОРМАЦИЯ ({len(result.info)}):")
            for info_item in result.info:
                print(f"   - {info_item}")

        print("=" * 50)
