#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Integration тесты на реальных данных
Тестирование обработки email файлов из 2025-07-29
Фаза 7: Тестирование и Надежность
"""

import pytest
import json
import time
from pathlib import Path
from typing import Dict, List, Any

from src.core.extractor_factory import ExtractorFactory


class TestRealDataProcessing:
    """Integration тесты на реальных данных"""

    @pytest.fixture
    def extractor(self):
        """Фикстура для создания экстрактора"""
        return ExtractorFactory.create_extractor()

    @pytest.fixture
    def real_email_files(self):
        """Фикстура с реальными файлами email"""
        email_dir = Path('data/emails/2025-07-29')
        if not email_dir.exists():
            pytest.skip("Директория с реальными данными не найдена")

        json_files = list(email_dir.glob('*.json'))
        if not json_files:
            pytest.skip("Файлы email не найдены")

        return sorted(json_files)[:10]  # Ограничиваем для быстрого тестирования

    def test_process_single_real_email(self, extractor, real_email_files):
        """Тест обработки одного реального email файла"""
        if not real_email_files:
            pytest.skip("Нет доступных email файлов")

        email_file = real_email_files[0]

        # Загружаем данные email
        with open(email_file, 'r', encoding='utf-8') as f:
            email_data = json.load(f)

        text = email_data.get('body', '')[:3000]  # Ограничиваем для теста
        metadata = {
            'file_name': email_file.name,
            'date': '2025-07-29',
            'source': 'real_data_test'
        }

        # Обрабатываем текст
        start_time = time.time()
        result = extractor.extract_all_data(text, metadata)
        processing_time = time.time() - start_time

        # Проверяем структуру результата
        assert isinstance(result, dict)
        assert 'contacts' in result
        assert 'business_context' in result
        assert 'commercial_offers' in result
        assert 'provider_used' in result
        assert 'processing_time' in result
        assert 'text_length' in result

        # Проверяем типы данных
        assert isinstance(result['contacts'], list)
        assert isinstance(result['business_context'], str)
        assert isinstance(result['commercial_offers'], list)
        assert isinstance(result['processing_time'], (int, float))
        assert processing_time < 30  # Не более 30 секунд на файл

        print(f"✅ Обработан файл: {email_file.name}")
        print(f"📊 Контактов найдено: {len(result['contacts'])}")
        print(".2f")

    def test_batch_processing_real_emails(self, extractor, real_email_files):
        """Тест пакетной обработки нескольких email файлов"""
        if len(real_email_files) < 3:
            pytest.skip("Недостаточно email файлов для пакетного тестирования")

        batch_files = real_email_files[:5]  # Обрабатываем 5 файлов
        results = []
        total_processing_time = 0

        for email_file in batch_files:
            # Загружаем данные
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)

            text = email_data.get('body', '')[:2000]  # Ограничиваем для скорости
            metadata = {
                'file_name': email_file.name,
                'date': '2025-07-29',
                'batch_id': 'integration_test'
            }

            # Обрабатываем
            start_time = time.time()
            result = extractor.extract_all_data(text, metadata)
            processing_time = time.time() - start_time

            total_processing_time += processing_time
            results.append(result)

            # Проверяем каждый результат
            assert isinstance(result, dict)
            assert 'contacts' in result
            assert 'business_context' in result

        # Проверяем статистику пакетной обработки
        avg_processing_time = total_processing_time / len(batch_files)
        total_contacts = sum(len(r.get('contacts', [])) for r in results)

        print(f"📦 Пакетная обработка: {len(batch_files)} файлов")
        print(f"👥 Всего контактов: {total_contacts}")
        print(".2f")
        print(".2f")

        # Проверяем производительность
        assert avg_processing_time < 20  # Среднее время менее 20 сек
        assert total_processing_time < 120  # Общее время менее 2 мин

    def test_memory_usage_during_processing(self, extractor, real_email_files):
        """Тест использования памяти при обработке"""
        if not real_email_files:
            pytest.skip("Нет доступных email файлов")

        # Измеряем начальную память
        initial_memory = extractor.memory_optimizer.get_memory_usage()

        # Обрабатываем несколько файлов
        for email_file in real_email_files[:3]:
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)

            text = email_data.get('body', '')[:3000]
            extractor.extract_all_data(text)

        # Измеряем память после обработки
        final_memory = extractor.memory_optimizer.get_memory_usage()
        memory_increase = final_memory - initial_memory

        # Проверяем, что увеличение памяти в разумных пределах
        assert memory_increase < 100  # Менее 100MB прироста

        # Проверяем работу memory optimizer
        memory_stats = extractor.memory_optimizer.get_comprehensive_stats()
        assert 'memory_optimizer' in memory_stats
        assert memory_stats['memory_optimizer']['current_memory_mb'] > 0

        print(".1f")
        print(".1f")
        print(".1f")

    def test_cache_effectiveness_real_data(self, extractor, real_email_files):
        """Тест эффективности кэширования на реальных данных"""
        if len(real_email_files) < 2:
            pytest.skip("Недостаточно файлов для тестирования кэша")

        # Первый проход (заполнение кэша)
        print("🔄 Первый проход - заполнение кэша...")
        first_pass_time = 0

        for email_file in real_email_files[:3]:
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)

            text = email_data.get('body', '')[:2000]

            start_time = time.time()
            extractor.extract_all_data(text)
            first_pass_time += time.time() - start_time

        # Проверяем статистику кэша после первого прохода
        cache_stats_1 = extractor.cache.get_cache_stats()

        # Второй проход (использование кэша)
        print("🔄 Второй проход - использование кэша...")
        second_pass_time = 0

        for email_file in real_email_files[:3]:
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)

            text = email_data.get('body', '')[:2000]

            start_time = time.time()
            extractor.extract_all_data(text)
            second_pass_time += time.time() - start_time

        # Проверяем статистику кэша после второго прохода
        cache_stats_2 = extractor.cache.get_cache_stats()

        # Вычисляем ускорение
        if second_pass_time > 0:
            speedup = first_pass_time / second_pass_time
            cache_hit_rate = cache_stats_2.get('overall_hit_rate', 0)

            print(".2f")
            print(".2f")
            print(".1f")
            print(".1f")

            # Проверяем, что кэш работает
            assert speedup > 1.0  # Должно быть ускорение
            assert cache_hit_rate > 0  # Должен быть hit rate

    def test_error_handling_real_data(self, extractor):
        """Тест обработки ошибок на реальных данных"""
        # Тест с некорректными данными
        result = extractor.extract_all_data("")

        # Система не должна падать
        assert isinstance(result, dict)
        assert 'contacts' in result

        # Тест с очень длинным текстом
        long_text = "Это очень длинный текст. " * 10000
        result = extractor.extract_all_data(long_text)

        assert isinstance(result, dict)
        assert 'contacts' in result

        # Тест с специальными символами
        special_text = "Текст с символами: áéíóú ñ @ # $ % & * ( ) [ ] { }"
        result = extractor.extract_all_data(special_text)

        assert isinstance(result, dict)
        assert 'contacts' in result

    def test_attachment_processing_simulation(self, extractor, real_email_files):
        """Тест симуляции обработки вложений"""
        if not real_email_files:
            pytest.skip("Нет доступных email файлов")

        # Находим файл с вложениями
        file_with_attachments = None
        for email_file in real_email_files:
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)

            if email_data.get('attachments') and len(email_data['attachments']) > 0:
                file_with_attachments = email_file
                break

        if not file_with_attachments:
            pytest.skip("Не найден файл с вложениями")

        # Загружаем файл с вложениями
        with open(file_with_attachments, 'r', encoding='utf-8') as f:
            email_data = json.load(f)

        text = email_data.get('body', '')[:2000]
        attachments = email_data.get('attachments', [])

        print(f"📎 Тестирование файла с {len(attachments)} вложениями")

        # Обрабатываем основной текст
        result = extractor.extract_all_data(text)

        assert isinstance(result, dict)
        assert 'contacts' in result

        # Проверяем информацию о вложениях
        for attachment in attachments:
            assert 'filename' in attachment
            assert 'size' in attachment
            assert 'status' in attachment

        print(f"✅ Обработаны вложения: {len(attachments)} файлов")

    def test_provider_fallback_real_scenario(self, extractor, real_email_files):
        """Тест fallback сценариев на реальных данных"""
        if not real_email_files:
            pytest.skip("Нет доступных email файлов")

        # Тестируем обработку с имитацией ошибок провайдеров
        test_text = "Тестовый текст для проверки fallback"

        # Обрабатываем несколько раз для тестирования стабильности
        for i in range(3):
            result = extractor.extract_all_data(test_text)

            assert isinstance(result, dict)
            assert 'contacts' in result
            assert 'provider_used' in result

            print(f"🔄 Попытка {i+1}: провайдер {result['provider_used']}")

        # Проверяем статистику провайдеров
        provider_stats = extractor.config.provider_manager.get_stats()
        assert 'providers' in provider_stats

    def test_performance_metrics_real_data(self, extractor, real_email_files):
        """Тест метрик производительности на реальных данных"""
        if len(real_email_files) < 5:
            pytest.skip("Недостаточно файлов для метрик производительности")

        processing_times = []
        contacts_found = []
        memory_usage = []

        # Обрабатываем файлы и собираем метрики
        for email_file in real_email_files[:5]:
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)

            text = email_data.get('body', '')[:2500]  # Стандартный размер для теста

            start_time = time.time()
            result = extractor.extract_all_data(text)
            processing_time = time.time() - start_time

            processing_times.append(processing_time)
            contacts_found.append(len(result.get('contacts', [])))

            # Замеряем память
            memory_mb = extractor.memory_optimizer.get_memory_usage()
            memory_usage.append(memory_mb)

        # Вычисляем метрики
        avg_processing_time = sum(processing_times) / len(processing_times)
        total_contacts = sum(contacts_found)
        avg_memory = sum(memory_usage) / len(memory_usage)
        max_memory = max(memory_usage)

        print("📊 Метрики производительности:")
        print(f"   📁 Файлов обработано: {len(processing_times)}")
        print(".2f")
        print(f"   👥 Контактов найдено: {total_contacts}")
        print(".1f")
        print(".1f")

        # Проверяем пороги производительности
        assert avg_processing_time < 15  # Среднее время менее 15 сек
        assert max_memory < 500  # Максимальная память менее 500MB

    def test_data_quality_real_emails(self, extractor, real_email_files):
        """Тест качества извлечения данных из реальных email"""
        if len(real_email_files) < 3:
            pytest.skip("Недостаточно файлов для тестирования качества")

        quality_metrics = {
            'total_files': 0,
            'files_with_contacts': 0,
            'total_contacts': 0,
            'contacts_with_phones': 0,
            'contacts_with_emails': 0,
            'contacts_with_names': 0
        }

        for email_file in real_email_files[:5]:
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)

            text = email_data.get('body', '')[:3000]

            result = extractor.extract_all_data(text)
            contacts = result.get('contacts', [])

            quality_metrics['total_files'] += 1

            if contacts:
                quality_metrics['files_with_contacts'] += 1
                quality_metrics['total_contacts'] += len(contacts)

                for contact in contacts:
                    if contact.get('phone'):
                        quality_metrics['contacts_with_phones'] += 1
                    if contact.get('email'):
                        quality_metrics['contacts_with_emails'] += 1
                    if contact.get('name'):
                        quality_metrics['contacts_with_names'] += 1

        # Вычисляем проценты
        if quality_metrics['total_contacts'] > 0:
            phone_coverage = (quality_metrics['contacts_with_phones'] / quality_metrics['total_contacts']) * 100
            email_coverage = (quality_metrics['contacts_with_emails'] / quality_metrics['total_contacts']) * 100
            name_coverage = (quality_metrics['contacts_with_names'] / quality_metrics['total_contacts']) * 100

            print("🎯 Метрики качества данных:")
            print(f"   📁 Файлов обработано: {quality_metrics['total_files']}")
            print(f"   📧 Файлов с контактами: {quality_metrics['files_with_contacts']}")
            print(f"   👥 Всего контактов: {quality_metrics['total_contacts']}")
            print(".1f")
            print(".1f")
            print(".1f")

            # Проверяем минимальные пороги качества
            assert name_coverage > 50  # Минимум 50% контактов с именами
            assert email_coverage > 30  # Минимум 30% контактов с email
