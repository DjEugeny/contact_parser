#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Unit тесты для TextChunker
Фаза 5+: Архитектурная оптимизация
"""

import pytest
from pathlib import Path
from src.core.chunker import TextChunker, ChunkingConfig


class TestTextChunker:
    """Тестирование TextChunker"""

    @pytest.fixture
    def chunker_config(self):
        """Фикстура с конфигурацией chunker"""
        return ChunkingConfig(
            max_chunk_size=1000,
            overlap_size=100,
            use_tokens=False,  # Для простоты тестирования
            max_chunks_per_text=5
        )

    @pytest.fixture
    def chunker(self, chunker_config):
        """Фикстура с TextChunker"""
        return TextChunker(chunker_config)

    def test_chunker_initialization(self, chunker, chunker_config):
        """Тест инициализации chunker"""
        assert chunker.config == chunker_config
        assert chunker.stats['total_chunks_created'] == 0
        assert chunker.stats['texts_chunked'] == 0

    def test_should_chunk_small_text(self, chunker):
        """Тест определения необходимости chunking для маленького текста"""
        small_text = "Это небольшой текст для тестирования"
        assert not chunker.should_chunk(small_text)

    def test_should_chunk_large_text(self, chunker):
        """Тест определения необходимости chunking для большого текста"""
        large_text = "Это большой текст для тестирования. " * 1000  # >1000 символов
        assert chunker.should_chunk(large_text)

    def test_create_chunks_small_text(self, chunker):
        """Тест создания чанков для маленького текста"""
        small_text = "Это небольшой текст"
        chunks = chunker.create_chunks(small_text)

        assert len(chunks) == 1
        assert chunks[0] == small_text
        assert chunker.stats['texts_not_chunked'] == 1
        assert chunker.stats['texts_chunked'] == 0

    def test_create_chunks_large_text(self, chunker):
        """Тест создания чанков для большого текста"""
        large_text = "Это большой текст для тестирования chunking. " * 100
        chunks = chunker.create_chunks(large_text)

        assert len(chunks) > 1
        assert len(chunks) <= chunker.config.max_chunks_per_text
        assert chunker.stats['texts_chunked'] == 1
        assert chunker.stats['character_based_chunks'] == len(chunks)

        # Проверяем что все чанки содержат текст
        for chunk in chunks:
            assert len(chunk.strip()) > 0

    def test_chunk_overlap(self, chunker):
        """Тест перекрытия чанков"""
        # Создаем текст где будет точно 2 чанка с перекрытием
        text = "A" * 800 + "B" * 300  # 1100 символов
        chunks = chunker.create_chunks(text)

        assert len(chunks) == 2

        # Извлекаем чистый текст из чанков (убираем метку чанка)
        # Формат: \n\n[ЧАСТЬ X ИЗ БОЛЬШОГО ТЕКСТА, СИМВОЛЫ start-end]\nтекст
        first_chunk_lines = chunks[0].split('\n')
        first_chunk_text = '\n'.join(first_chunk_lines[3:])  # Пропускаем 3 строки метки

        second_chunk_lines = chunks[1].split('\n')
        second_chunk_text = '\n'.join(second_chunk_lines[3:])  # Пропускаем 3 строки метки

        # Проверяем перекрытие - последний кусок первого чанка должен быть в начале второго
        first_chunk_end = first_chunk_text[-chunker.config.overlap_size:]
        second_chunk_start = second_chunk_text[:chunker.config.overlap_size]

        assert first_chunk_end == second_chunk_start

    def test_chunk_info_markers(self, chunker):
        """Тест маркеров информации о чанках"""
        large_text = "A" * 800 + "B" * 300  # 1100 символов
        chunks = chunker.create_chunks(large_text)

        # Каждый чанк должен содержать информацию о позиции
        for i, chunk in enumerate(chunks):
            assert f"[ЧАСТЬ {i+1} ИЗ" in chunk

    def test_max_chunks_limit(self, chunker):
        """Тест ограничения максимального количества чанков"""
        # Создаем очень большой текст
        very_large_text = "Очень большой текст для тестирования. " * 1000
        chunks = chunker.create_chunks(very_large_text)

        # Количество чанков не должно превышать максимум
        assert len(chunks) <= chunker.config.max_chunks_per_text

    def test_empty_text_handling(self, chunker):
        """Тест обработки пустого текста"""
        chunks = chunker.create_chunks("")
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_whitespace_only_text(self, chunker):
        """Тест обработки текста из одних пробелов"""
        whitespace_text = "   \n\t  "
        chunks = chunker.create_chunks(whitespace_text)
        assert len(chunks) == 1
        assert chunks[0] == whitespace_text

    def test_unicode_text_handling(self, chunker):
        """Тест обработки текста с unicode символами"""
        unicode_text = "Привет мир! 你好世界 🌍 Test 123"
        chunks = chunker.create_chunks(unicode_text)

        # Для маленького текста должен быть 1 чанк
        assert len(chunks) == 1
        assert chunks[0] == unicode_text

    def test_get_chunk_stats(self, chunker):
        """Тест получения статистики"""
        # Создаем несколько чанков
        large_text = "Тест статистики. " * 500
        chunks = chunker.create_chunks(large_text)

        stats = chunker.get_chunk_stats()

        assert 'chunker_stats' in stats
        assert 'config' in stats
        assert stats['chunker_stats']['texts_chunked'] > 0
        assert stats['config']['max_chunk_size'] == chunker.config.max_chunk_size

    def test_reset_stats(self, chunker):
        """Тест сброса статистики"""
        # Добавляем некоторые данные
        large_text = "Тест сброса статистики. " * 500
        chunker.create_chunks(large_text)

        assert chunker.stats['texts_chunked'] > 0

        # Сбрасываем статистику
        chunker.reset_stats()

        assert chunker.stats['texts_chunked'] == 0
        assert chunker.stats['total_chunks_created'] == 0


class TestChunkingConfig:
    """Тестирование ChunkingConfig"""

    def test_default_config(self):
        """Тест конфигурации по умолчанию"""
        config = ChunkingConfig()

        assert config.max_chunk_size == 8000
        assert config.overlap_size == 1000
        assert config.use_tokens == True
        assert config.max_chunks_per_text == 20

    def test_custom_config(self):
        """Тест пользовательской конфигурации"""
        config = ChunkingConfig(
            max_chunk_size=5000,
            overlap_size=500,
            use_tokens=False,
            max_chunks_per_text=10
        )

        assert config.max_chunk_size == 5000
        assert config.overlap_size == 500
        assert config.use_tokens == False
        assert config.max_chunks_per_text == 10

    def test_config_from_file(self, tmp_path):
        """Тест загрузки конфигурации из файла"""
        # Создаем тестовый файл конфигурации
        config_file = tmp_path / "test_config.json"
        config_data = {
            "chunking": {
                "max_chunk_size": 4000,
                "overlap_size": 400,
                "use_tokens": False,
                "max_chunks_per_text": 8
            }
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(config_data, f)

        # Загружаем конфигурацию
        config = ChunkingConfig.load_from_file(config_file)

        assert config.max_chunk_size == 4000
        assert config.overlap_size == 400
        assert config.use_tokens == False
        assert config.max_chunks_per_text == 8

    def test_config_from_file_not_exists(self):
        """Тест загрузки конфигурации когда файл не существует"""
        config = ChunkingConfig.load_from_file(Path("/non/existent/file.json"))

        # Должны вернуться значения по умолчанию
        assert config.max_chunk_size == 8000
        assert isinstance(config, ChunkingConfig)
