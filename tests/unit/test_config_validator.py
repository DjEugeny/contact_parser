#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Unit тесты для валидации конфигурации
Фаза 7: Тестирование и Надежность
"""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from config.config_validator import ConfigValidator
from config.config_manager import UnifiedConfigManager


class TestConfigValidator:
    """Тестирование ConfigValidator"""

    @pytest.fixture
    def config_validator(self):
        """Фикстура с валидатором конфигурации"""
        return ConfigValidator()

    @pytest.fixture
    def valid_env_vars(self):
        """Фикстура с валидными переменными окружения"""
        return {
            'OPENROUTER_API_KEY': 'sk-or-v1-test-key-123',
            'GROQ_API_KEY': 'gsk_test_key_456',
            'REPLICATE_API_KEY': 'r8_test_key_789',
            'IMAP_SERVER': 'mail.example.com',
            'IMAP_PORT': '993',
            'IMAP_USER': 'user@example.com',
            'GOOGLE_SHEET_ID': '1ABCDEFGH1234567890',
            'TEST_START_DATE': '2025-07-28',
            'TEST_END_DATE': '2025-07-31'
        }

    @pytest.fixture
    def invalid_env_vars(self):
        """Фикстура с невалидными переменными окружения"""
        return {
            'OPENROUTER_API_KEY': '',  # Пустой ключ
            'GROQ_API_KEY': 'invalid_key',
            'REPLICATE_API_KEY': 'r8_invalid',
            'IMAP_SERVER': '',
            'IMAP_PORT': 'invalid_port',
            'IMAP_USER': 'not_an_email',
        }

    def test_validate_env_vars_success(self, config_validator, valid_env_vars):
        """Тест успешной валидации переменных окружения"""
        with patch.dict(os.environ, valid_env_vars):
            result = config_validator.validate_environment_variables()

            assert result['valid'] is True
            assert len(result['missing']) == 0
            assert len(result['invalid']) == 0

    def test_validate_env_vars_missing_keys(self, config_validator):
        """Тест валидации с отсутствующими ключами"""
        # Очищаем переменные окружения
        with patch.dict(os.environ, {}, clear=True):
            result = config_validator.validate_environment_variables()

            assert result['valid'] is False
            assert len(result['missing']) > 0
            assert 'OPENROUTER_API_KEY' in result['missing']
            assert 'GROQ_API_KEY' in result['missing']
            assert 'REPLICATE_API_KEY' in result['missing']

    def test_validate_env_vars_invalid_format(self, config_validator, invalid_env_vars):
        """Тест валидации с некорректными значениями"""
        with patch.dict(os.environ, invalid_env_vars):
            result = config_validator.validate_environment_variables()

            assert result['valid'] is False
            assert len(result['invalid']) > 0

    def test_validate_json_config_valid(self, config_validator):
        """Тест валидации корректного JSON конфига"""
        valid_config = {
            "providers": {
                "openrouter": {
                    "model": "qwen/qwen3-235b-a22b:free",
                    "priority": 1,
                    "active": True
                },
                "groq": {
                    "model": "llama-3.1-8b-instant",
                    "priority": 2,
                    "active": True
                }
            },
            "processing": {
                "start_date": "2025-07-28",
                "end_date": "2025-07-31",
                "batch_size": 10
            }
        }

        result = config_validator.validate_json_config(valid_config)

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_validate_json_config_invalid(self, config_validator):
        """Тест валидации некорректного JSON конфига"""
        invalid_config = {
            "providers": {
                "openrouter": {
                    "model": "",  # Пустая модель
                    "priority": "not_a_number",  # Некорректный приоритет
                    "active": "not_a_boolean"  # Некорректный булевый
                }
            },
            "processing": {
                "start_date": "invalid_date",
                "end_date": "2025-07-31"
            }
        }

        result = config_validator.validate_json_config(invalid_config)

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_file_paths(self, config_validator, tmp_path):
        """Тест валидации путей к файлам"""
        # Создаем тестовые файлы
        existing_file = tmp_path / "existing.json"
        existing_file.write_text('{"test": "data"}')

        non_existing_file = tmp_path / "non_existing.json"

        # Тест существующего файла
        result_existing = config_validator.validate_file_path(str(existing_file))
        assert result_existing['exists'] is True

        # Тест несуществующего файла
        result_non_existing = config_validator.validate_file_path(str(non_existing_file))
        assert result_non_existing['exists'] is False

    def test_validate_network_connectivity(self, config_validator):
        """Тест валидации сетевого подключения"""
        # Тест с доступным хостом
        result = config_validator.validate_network_connectivity('google.com', 80, timeout=5)
        assert 'reachable' in result

        # Тест с недоступным хостом
        result = config_validator.validate_network_connectivity('invalid.host.that.does.not.exist', 80, timeout=1)
        assert result['reachable'] is False

    def test_full_validation_success(self, config_validator, valid_env_vars, tmp_path):
        """Тест полной валидации при успешных условиях"""
        with patch.dict(os.environ, valid_env_vars):
            # Создаем тестовый конфиг файл
            config_file = tmp_path / "test_config.json"
            config_data = {
                "providers": {
                    "openrouter": {"model": "qwen/qwen3-235b-a22b:free", "priority": 1, "active": True},
                    "groq": {"model": "llama-3.1-8b-instant", "priority": 2, "active": True}
                },
                "processing": {"start_date": "2025-07-28", "end_date": "2025-07-31"}
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f)

            result = config_validator.validate_full_config(str(config_file))

            assert result['overall_valid'] is True
            assert result['env_valid'] is True
            assert result['config_valid'] is True

    def test_full_validation_failure(self, config_validator, tmp_path):
        """Тест полной валидации при ошибках"""
        # Очищаем переменные окружения
        with patch.dict(os.environ, {}, clear=True):
            # Создаем некорректный конфиг файл
            config_file = tmp_path / "invalid_config.json"
            invalid_config = {
                "providers": {
                    "openrouter": {"model": "", "priority": "invalid", "active": "invalid"}
                },
                "processing": {"start_date": "invalid_date", "end_date": "2025-07-31"}
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(invalid_config, f)

            result = config_validator.validate_full_config(str(config_file))

            assert result['overall_valid'] is False
            assert result['env_valid'] is False
            assert result['config_valid'] is False


class TestUnifiedConfigManager:
    """Тестирование UnifiedConfigManager"""

    @pytest.fixture
    def config_manager(self):
        """Фикстура с менеджером конфигурации"""
        return UnifiedConfigManager()

    @pytest.fixture
    def mock_env_vars(self):
        """Mock переменные окружения"""
        return {
            'OPENROUTER_API_KEY': 'sk-or-v1-test-key',
            'GROQ_API_KEY': 'gsk_test_key',
            'REPLICATE_API_KEY': 'r8_test_key',
            'IMAP_SERVER': 'mail.test.com',
            'IMAP_PORT': '993',
            'GOOGLE_SHEET_ID': '1TEST123'
        }

    @pytest.fixture
    def mock_config_files(self, tmp_path):
        """Mock конфигурационные файлы"""
        # Создаем providers.json
        providers_file = tmp_path / "providers.json"
        providers_data = {
            "openrouter": {"model": "qwen/qwen3-235b-a22b:free", "priority": 1, "active": True},
            "groq": {"model": "llama-3.1-8b-instant", "priority": 2, "active": True}
        }

        with open(providers_file, 'w', encoding='utf-8') as f:
            json.dump(providers_data, f)

        # Создаем processing_config.json
        processing_file = tmp_path / "processing_config.json"
        processing_data = {
            "start_date": "2025-07-28",
            "end_date": "2025-07-31",
            "batch_size": 10
        }

        with open(processing_file, 'w', encoding='utf-8') as f:
            json.dump(processing_data, f)

        return {
            'providers_file': str(providers_file),
            'processing_file': str(processing_file)
        }

    def test_get_llm_providers_from_env(self, config_manager, mock_env_vars):
        """Тест получения провайдеров из переменных окружения"""
        with patch.dict(os.environ, mock_env_vars):
            providers = config_manager.get_llm_providers()

            assert len(providers) == 3
            assert 'openrouter' in [p.name for p in providers]
            assert 'groq' in [p.name for p in providers]
            assert 'replicate' in [p.name for p in providers]

    def test_get_processing_config_from_env(self, config_manager, mock_env_vars):
        """Тест получения конфигурации обработки из переменных окружения"""
        with patch.dict(os.environ, mock_env_vars):
            processing_config = config_manager.get_processing_config()

            assert processing_config.start_date == "2025-07-28"
            assert processing_config.end_date == "2025-07-31"
            assert processing_config.imap_server == "mail.test.com"
            assert processing_config.imap_port == 993

    def test_get_export_config_from_env(self, config_manager, mock_env_vars):
        """Тест получения конфигурации экспорта из переменных окружения"""
        with patch.dict(os.environ, mock_env_vars):
            export_config = config_manager.get_export_config()

            assert export_config.google_sheet_id == "1TEST123"

    def test_priority_env_over_json(self, config_manager, mock_env_vars, mock_config_files):
        """Тест приоритета .env над JSON файлами"""
        with patch.dict(os.environ, mock_env_vars):
            # Переопределяем переменную окружения
            test_env = mock_env_vars.copy()
            test_env['GOOGLE_SHEET_ID'] = '1ENV_OVERRIDE_123'

            with patch.dict(os.environ, test_env):
                export_config = config_manager.get_export_config()

                # Должна использоваться переменная из .env, а не из JSON
                assert export_config.google_sheet_id == '1ENV_OVERRIDE_123'

    def test_fallback_to_defaults(self, config_manager):
        """Тест fallback к значениям по умолчанию"""
        # Очищаем переменные окружения
        with patch.dict(os.environ, {}, clear=True):
            processing_config = config_manager.get_processing_config()

            # Должны использоваться значения по умолчанию
            assert processing_config.imap_port == 993  # Значение по умолчанию
            assert processing_config.batch_size == 10  # Значение по умолчанию

    def test_config_validation_integration(self, config_manager, mock_env_vars):
        """Тест интеграции с валидацией конфигурации"""
        with patch.dict(os.environ, mock_env_vars):
            # Попытка получить конфигурацию
            try:
                providers = config_manager.get_llm_providers()
                assert len(providers) > 0

                processing_config = config_manager.get_processing_config()
                assert processing_config is not None

            except Exception as e:
                # Если есть ошибки валидации, они должны быть понятными
                assert "API key" in str(e) or "configuration" in str(e).lower()

    def test_imap_config_extraction(self, config_manager, mock_env_vars):
        """Тест извлечения IMAP конфигурации"""
        with patch.dict(os.environ, mock_env_vars):
            imap_config = config_manager.get_imap_config()

            assert imap_config['server'] == 'mail.test.com'
            assert imap_config['port'] == 993
            assert imap_config['user'] == 'user@example.com'

    def test_error_handling_invalid_env(self, config_manager):
        """Тест обработки ошибок при некорректных переменных окружения"""
        invalid_env = {
            'OPENROUTER_API_KEY': '',  # Пустой ключ
            'IMAP_PORT': 'not_a_number',  # Некорректный порт
        }

        with patch.dict(os.environ, invalid_env):
            # Система должна gracefully обрабатывать ошибки
            try:
                config = config_manager.get_processing_config()
                # Даже при ошибках должна вернуть объект с defaults
                assert hasattr(config, 'imap_port')
            except Exception as e:
                # Ошибки должны быть информативными
                assert len(str(e)) > 0
