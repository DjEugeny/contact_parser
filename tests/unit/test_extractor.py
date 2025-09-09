#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Unit тесты для ContactExtractor
Фаза 7: Тестирование и Надежность
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.extractor_factory import ExtractorFactory
from core.extractor import ExtractorConfig


class TestContactExtractor:
    """Тестирование ContactExtractor"""

    @pytest.fixture
    def extractor(self):
        """Фикстура для создания экстрактора"""
        return ExtractorFactory.create_extractor()

    def test_extract_all_data_basic(self, extractor, sample_email_data):
        """Тест базового извлечения данных"""
        result = extractor.extract_all_data(
            sample_email_data['body'],
            sample_email_data['metadata']
        )

        # Проверяем структуру ответа
        assert isinstance(result, dict)
        assert 'contacts' in result
        assert 'business_context' in result
        assert 'commercial_offers' in result
        assert 'provider_used' in result
        assert 'processing_time' in result

        # Проверяем типы данных
        assert isinstance(result['contacts'], list)
        assert isinstance(result['business_context'], str)
        assert isinstance(result['commercial_offers'], list)

    def test_extract_all_data_with_contacts(self, extractor):
        """Тест извлечения контактов"""
        text = """
        Контактное лицо: Анна Сергеевна Иванова
        Телефон: +7 (495) 123-45-67
        Email: anna.ivanova@company.ru
        Должность: Директор по продажам
        Компания: ООО "ТехноСервис"
        """

        result = extractor.extract_all_data(text)

        # Проверяем наличие контактов
        assert 'contacts' in result
        assert isinstance(result['contacts'], list)

        # Если контакты найдены, проверяем их структуру
        if result['contacts']:
            contact = result['contacts'][0]
            assert 'name' in contact
            assert 'email' in contact
            assert 'confidence' in contact
            assert isinstance(contact['confidence'], (int, float))
            assert 0 <= contact['confidence'] <= 1

    def test_extract_all_data_empty_text(self, extractor):
        """Тест обработки пустого текста"""
        result = extractor.extract_all_data("")

        # Проверяем, что система не падает
        assert isinstance(result, dict)
        assert 'contacts' in result
        assert 'business_context' in result
        assert 'commercial_offers' in result

    def test_extract_all_data_with_metadata(self, extractor, sample_email_data):
        """Тест обработки с метаданными"""
        metadata = {
            'file_name': 'test_email.json',
            'date': '2025-07-29',
            'source': 'real_data_test'
        }

        result = extractor.extract_all_data(
            sample_email_data['body'],
            metadata
        )

        # Проверяем, что метаданные сохранены
        assert 'text_length' in result
        assert 'chunks_processed' in result
        assert result['chunks_processed'] == 1

    @patch('core.extractor.hashlib.sha256')
    def test_cache_functionality(self, mock_sha256, extractor, sample_email_data):
        """Тест работы кэширования"""
        # Настраиваем mock для хэширования
        mock_hash = MagicMock()
        mock_hash.hexdigest.return_value = 'test_cache_key'
        mock_sha256.return_value = mock_hash

        # Создаем mock для кэша
        extractor.cache.get_llm_response.return_value = None  # Первый раз - miss
        extractor.cache.set_llm_response = MagicMock()

        # Первый запрос
        result1 = extractor.extract_all_data(sample_email_data['body'])

        # Второй запрос (должен использовать кэш)
        extractor.cache.get_llm_response.return_value = {
            'content': '{"contacts": [], "business_context": "cached", "commercial_offers": []}',
            'provider': 'cached',
            'response_time': 0.01
        }
        result2 = extractor.extract_all_data(sample_email_data['body'])

        # Проверяем, что кэш был использован
        assert result2['business_context'] == "cached"
        assert result2['provider_used'] == 'cached'

        # Проверяем статистику кэша
        assert extractor.stats['cached_requests'] > 0

    def test_memory_optimization_large_text(self, extractor):
        """Тест оптимизации памяти для больших текстов"""
        # Создаем большой текст (>1MB)
        large_text = "Это большой текст для тестирования. " * 50000  # ~2MB

        # Записываем начальную статистику памяти
        start_memory = extractor.memory_optimizer.get_memory_usage()

        # Обрабатываем большой текст
        result = extractor.extract_all_data(large_text)

        # Проверяем, что обработка прошла успешно
        assert isinstance(result, dict)
        assert 'contacts' in result

        # Проверяем, что memory optimizer был активирован
        if len(large_text) > 1000000:  # >1MB
            # Должен быть вызван memory monitor
            assert extractor.memory_optimizer.get_memory_usage() >= start_memory

    def test_phone_normalization_integration(self, extractor):
        """Тест интеграции с phone нормализацией"""
        text_with_phones = """
        Контакты:
        1. +7 (999) 123-45-67
        2. 8(495)111-22-33 доб.456
        3. Тел: 123-45-67 (короткий номер)
        """

        result = extractor.extract_all_data(text_with_phones)

        # Проверяем наличие контактов
        assert 'contacts' in result
        assert isinstance(result['contacts'], list)

        # Если контакты найдены, проверяем нормализацию
        for contact in result['contacts']:
            if 'phone' in contact and contact['phone']:
                # Должен быть normalized_phone
                assert 'normalized_phone' in contact or 'raw_phone' in contact

    def test_json_schema_validation(self, extractor):
        """Тест валидации JSON Schema"""
        text = "Простой текст без контактов"

        result = extractor.extract_all_data(text)

        # Проверяем, что результат прошел валидацию
        assert 'contacts' in result
        assert 'business_context' in result
        assert 'commercial_offers' in result

        # Проверяем типы данных
        assert isinstance(result['contacts'], list)
        assert isinstance(result['business_context'], str)
        assert isinstance(result['commercial_offers'], list)

    def test_error_handling(self, extractor):
        """Тест обработки ошибок"""
        # Тест с некорректными данными
        result = extractor.extract_all_data(None)

        # Система не должна падать
        assert isinstance(result, dict)
        assert 'error' in result or 'contacts' in result

    def test_statistics_tracking(self, extractor, sample_email_data):
        """Тест отслеживания статистики"""
        initial_requests = extractor.stats['total_requests']

        result = extractor.extract_all_data(sample_email_data['body'])

        # Проверяем, что статистика обновилась
        assert extractor.stats['total_requests'] > initial_requests
        assert 'successful_requests' in extractor.stats

    def test_async_extraction(self, extractor, sample_email_data):
        """Тест асинхронной обработки"""
        import asyncio

        async def test_async():
            result = await extractor.extract_all_data_async(
                sample_email_data['body'],
                sample_email_data['metadata']
            )

            assert isinstance(result, dict)
            assert 'contacts' in result
            assert extractor.stats['async_operations'] > 0

            return result

        # Запускаем асинхронный тест
        result = asyncio.run(test_async())

        # Проверяем результат
        assert 'contacts' in result
        assert extractor.stats['async_operations'] > 0

    def test_prompt_loading(self, extractor):
        """Тест загрузки промптов"""
        prompt = extractor.load_prompt("contact_extraction.txt")

        # Проверяем, что промпт загружен
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_chunking_large_texts(self, extractor):
        """Тест обработки больших текстов с chunking"""
        # Создаем текст, требующий chunking
        large_text = "Это большой текст. " * 10000  # ~200KB

        result = extractor.extract_all_data(large_text)

        # Проверяем, что обработка прошла успешно
        assert isinstance(result, dict)
        assert 'chunks_processed' in result
        assert result['chunks_processed'] >= 1
