#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎛️ Унифицированный менеджер конфигурации
Фаза 5+: Устранение дублирования настроек
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json


@dataclass
class LLMProviderConfig:
    """📋 Конфигурация LLM провайдера"""
    name: str
    api_key: str
    model: str
    base_url: str
    priority: int
    active: bool
    max_retries: int = 3
    timeout: int = 30


@dataclass
class ProcessingConfig:
    """⚙️ Конфигурация обработки"""
    start_date: str = "2025-07-28"
    end_date: str = "2025-08-11"
    skip_processed: bool = True
    max_parallel: int = 3
    use_token_based_chunking: bool = True
    max_tokens_per_chunk: int = 4000
    overlap_tokens: int = 400


@dataclass
class ExportConfig:
    """📊 Конфигурация экспорта"""
    google_sheet_id: str = ""
    google_sheet_name: str = "CRM_from_Mail"
    confidence_threshold: float = 0.6
    data_dir: str = "data"


class UnifiedConfigManager:
    """🎛️ Унифицированный менеджер конфигурации"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self._env_loaded = False
        self._config_cache: Dict[str, Any] = {}

    def _ensure_env_loaded(self):
        """🔧 Гарантирует загрузку переменных окружения"""
        if not self._env_loaded:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent.parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                self._env_loaded = True
                print("✅ Переменные окружения загружены из .env")
            else:
                print("⚠️  Файл .env не найден")

    def get_llm_providers(self) -> List[LLMProviderConfig]:
        """
        🤖 Получить конфигурацию всех LLM провайдеров из .env

        Приоритеты:
        1. Replicate (самый быстрый)
        2. OpenRouter (хороший баланс)
        3. Groq (резервный)
        """
        self._ensure_env_loaded()

        providers = []

        # Replicate - приоритет 1 (самый быстрый)
        if replicate_key := os.getenv('REPLICATE_API_KEY'):
            providers.append(LLMProviderConfig(
                name="Replicate",
                api_key=replicate_key,
                model=os.getenv('REPLICATE_MODEL', 'meta/llama-3.1-8b-instant'),
                base_url="https://api.replicate.com/v1/predictions",
                priority=1,
                active=True
            ))

        # OpenRouter - приоритет 2
        if openrouter_key := os.getenv('OPENROUTER_API_KEY'):
            providers.append(LLMProviderConfig(
                name="OpenRouter",
                api_key=openrouter_key,
                model=os.getenv('OPENROUTER_MODEL', 'qwen/qwen3-235b-a22b:free'),
                base_url=os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1/chat/completions'),
                priority=2,
                active=True
            ))

        # Groq - приоритет 3 (резервный) - ВРЕМЕННО ОТКЛЮЧЕН
        # if groq_key := os.getenv('GROQ_API_KEY'):
        #     providers.append(LLMProviderConfig(
        #         name="Groq",
        #         api_key=groq_key,
        #         model=os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant'),
        #         base_url=os.getenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1/chat/completions'),
        #         priority=3,
        #         active=True
        #     ))

        # Сортировка по приоритету (выше приоритет - раньше в списке)
        providers.sort(key=lambda p: p.priority)

        print(f"🎛️ Загружено {len(providers)} LLM провайдеров из .env")
        for provider in providers:
            print(f"   {provider.priority}. {provider.name} ({provider.model})")

        return providers

    def get_processing_config(self) -> ProcessingConfig:
        """⚙️ Получить конфигурацию обработки"""
        self._ensure_env_loaded()

        # Сначала пробуем загрузить из processing_config.json
        config_path = self.config_dir / "processing_config.json"
        config_data = {}

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                print("✅ Загружена конфигурация обработки из processing_config.json")
            except Exception as e:
                print(f"⚠️  Ошибка загрузки processing_config.json: {e}")

        # Объединяем с переменными окружения (.env имеет приоритет)
        processing_config = ProcessingConfig()

        # Даты из .env или JSON
        processing_config.start_date = os.getenv('TEST_START_DATE',
            config_data.get('date_range', {}).get('start_date', processing_config.start_date))
        processing_config.end_date = os.getenv('TEST_END_DATE',
            config_data.get('date_range', {}).get('end_date', processing_config.end_date))

        # Настройки обработки
        processing_config.skip_processed = config_data.get('processing', {}).get('skip_processed',
            processing_config.skip_processed)
        processing_config.max_parallel = config_data.get('processing', {}).get('max_parallel',
            processing_config.max_parallel)

        # Настройки chunking
        chunking = config_data.get('chunking', {})
        processing_config.use_token_based_chunking = chunking.get('use_token_based',
            processing_config.use_token_based_chunking)
        processing_config.max_tokens_per_chunk = chunking.get('max_tokens_per_chunk',
            processing_config.max_tokens_per_chunk)
        processing_config.overlap_tokens = chunking.get('overlap_tokens',
            processing_config.overlap_tokens)

        return processing_config

    def get_export_config(self) -> ExportConfig:
        """📊 Получить конфигурацию экспорта"""
        self._ensure_env_loaded()

        config = ExportConfig()

        # Google Sheets настройки из .env
        config.google_sheet_id = os.getenv('GOOGLE_SHEET_ID', config.google_sheet_id)
        config.google_sheet_name = os.getenv('GOOGLE_SHEET_NAME', config.google_sheet_name)
        config.confidence_threshold = float(os.getenv('CONFIDENCE_REVIEW_THRESHOLD', config.confidence_threshold))
        config.data_dir = os.getenv('DATA_DIR', config.data_dir)

        return config

    def get_imap_config(self) -> Dict[str, Any]:
        """📧 Получить IMAP конфигурацию"""
        self._ensure_env_loaded()

        return {
            'server': os.getenv('IMAP_SERVER', ''),
            'port': int(os.getenv('IMAP_PORT', '143')),
            'user': os.getenv('IMAP_USER', ''),
            'password': os.getenv('IMAP_PASSWORD', ''),
            'use_ssl': os.getenv('IMAP_SSL', 'false').lower() == 'true'
        }

    def get_retry_config(self) -> Dict[str, Any]:
        """🔄 Получить конфигурацию повторных попыток"""
        self._ensure_env_loaded()

        return {
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
            'retry_delay': float(os.getenv('RETRY_DELAY', '1')),
            'rate_delay': float(os.getenv('RATE_DELAY', '1.2')),
            'retry_max': int(os.getenv('RETRY_MAX', '6')),
            'retry_base': float(os.getenv('RETRY_BASE', '1.6')),
            'retry_jitter': float(os.getenv('RETRY_JITTER', '0.4')),
            'fallback_to_replicate': os.getenv('FALLBACK_TO_REPLICATE', 'true').lower() == 'true'
        }

    def validate_configuration(self) -> Dict[str, Any]:
        """
        ✅ Валидация всей конфигурации

        Returns:
            Dict с результатами валидации
        """
        self._ensure_env_loaded()

        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'providers': {},
            'configs': {}
        }

        # Валидация провайдеров
        providers = self.get_llm_providers()
        if not providers:
            results['valid'] = False
            results['errors'].append("Не найдено ни одного активного LLM провайдера")

        results['providers']['count'] = len(providers)
        results['providers']['available'] = [p.name for p in providers]

        # Валидация IMAP
        imap_config = self.get_imap_config()
        if not imap_config['server'] or not imap_config['user']:
            results['warnings'].append("IMAP конфигурация неполная")

        # Валидация экспорта
        export_config = self.get_export_config()
        if not export_config.google_sheet_id:
            results['warnings'].append("Google Sheet ID не задан")

        results['configs']['imap'] = bool(imap_config['server'])
        results['configs']['export'] = bool(export_config.google_sheet_id)

        return results

    def print_config_summary(self):
        """📋 Вывести сводку по конфигурации"""
        print("\n🎛️ СВОДКА КОНФИГУРАЦИИ")
        print("=" * 50)

        # Провайдеры
        providers = self.get_llm_providers()
        print(f"🤖 LLM Провайдеры: {len(providers)}")
        for provider in providers:
            print(f"   {provider.priority}. {provider.name}: {provider.model}")

        # Обработка
        processing = self.get_processing_config()
        print(f"\n⚙️  Обработка: {processing.start_date} - {processing.end_date}")
        print(f"   Параллельность: {processing.max_parallel}")
        print(f"   Chunking: {processing.max_tokens_per_chunk} токенов")

        # Экспорт
        export = self.get_export_config()
        print(f"\n📊 Экспорт: {export.google_sheet_name}")
        print(f"   Confidence threshold: {export.confidence_threshold}")

        # IMAP
        imap = self.get_imap_config()
        if imap['server']:
            print(f"\n📧 IMAP: {imap['server']}:{imap['port']}")
        else:
            print("\n📧 IMAP: не настроен")
