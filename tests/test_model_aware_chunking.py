#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тесты для model-aware chunking

Проверяет, что ChunkingConfig.for_model() правильно создаёт
конфигурации для разных моделей.
"""

import pytest
from pathlib import Path
from src.core.chunker import ChunkingConfig


class TestModelAwareChunking:
    """Тесты model-aware chunking"""
    
    def test_gemini_2_0_flash_from_config(self):
        """✅ Загрузка конфигурации для Gemini 2.0 Flash из файла"""
        config = ChunkingConfig.for_model(
            model_name='google/gemini-2.0-flash-001',
            context_window=1000000
        )
        
        assert config.model_name == 'google/gemini-2.0-flash-001'
        assert config.model_context_window == 1000000
        assert config.max_chunk_size == 500000
        assert config.overlap_size == 5000
        assert config.max_chunks_per_text == 3
        assert config.chunk_alert_threshold == 5
        assert config.chunk_abort_threshold == 10
    
    def test_gemini_exp_from_config(self):
        """✅ Загрузка конфигурации для Gemini Experimental из файла"""
        config = ChunkingConfig.for_model(
            model_name='google/gemini-2.0-flash-exp:free',
            context_window=128000
        )
        
        assert config.model_name == 'google/gemini-2.0-flash-exp:free'
        assert config.model_context_window == 128000
        assert config.max_chunk_size == 60000
        assert config.overlap_size == 2000
        assert config.max_chunks_per_text == 5
    
    def test_unknown_model_fallback(self):
        """✅ Fallback для неизвестной модели (автоматический расчёт)"""
        config = ChunkingConfig.for_model(
            model_name='unknown/model',
            context_window=100000
        )
        
        assert config.model_name == 'unknown/model'
        assert config.model_context_window == 100000
        
        # Проверяем автоматический расчёт
        # safe_limit = 100000 * 0.8 = 80000
        # chunk_size = 80000 * 0.5 = 40000
        assert config.max_chunk_size == 40000
        
        # overlap = 40000 * 0.01 = 400, но минимум 1000
        assert config.overlap_size == 1000
        
        # Для 100K контекста: max_chunks = 10
        assert config.max_chunks_per_text == 10
        assert config.chunk_alert_threshold == 15
        assert config.chunk_abort_threshold == 30
    
    def test_large_context_window(self):
        """✅ Модель с очень большим контекстным окном (>1M)"""
        config = ChunkingConfig.for_model(
            model_name='test/large-model',
            context_window=2000000  # 2M
        )
        
        # safe_limit = 2000000 * 0.8 = 1600000
        # chunk_size = 1600000 * 0.5 = 800000, но макс 500000
        assert config.max_chunk_size == 500000
        
        # Для 1M+ контекста: max_chunks = 3
        assert config.max_chunks_per_text == 3
        assert config.chunk_alert_threshold == 5
        assert config.chunk_abort_threshold == 10
    
    def test_small_context_window(self):
        """✅ Модель с маленьким контекстным окном (<100K)"""
        config = ChunkingConfig.for_model(
            model_name='test/small-model',
            context_window=32000
        )
        
        # safe_limit = 32000 * 0.8 = 25600
        # chunk_size = 25600 * 0.5 = 12800
        assert config.max_chunk_size == 12800
        
        # Для <100K контекста: max_chunks = 20
        assert config.max_chunks_per_text == 20
        assert config.chunk_alert_threshold == 30
        assert config.chunk_abort_threshold == 50
    
    def test_medium_context_window_200k(self):
        """✅ Модель с средним контекстным окном (200K)"""
        config = ChunkingConfig.for_model(
            model_name='test/medium-model',
            context_window=200000
        )
        
        # safe_limit = 200000 * 0.8 = 160000
        # chunk_size = 160000 * 0.5 = 80000
        assert config.max_chunk_size == 80000
        
        # Для 200K+ контекста: max_chunks = 5
        assert config.max_chunks_per_text == 5
        assert config.chunk_alert_threshold == 10
        assert config.chunk_abort_threshold == 20
    
    def test_config_has_required_fields(self):
        """✅ Конфигурация содержит все необходимые поля"""
        config = ChunkingConfig.for_model(
            model_name='test/model',
            context_window=100000
        )
        
        # Проверяем обязательные поля
        assert config.use_tokens is True
        assert config.encoding_model == 'cl100k_base'
        assert config.auto_adjust_chunk_size is True
        assert config.smart_boundary_detection is True
        assert config.allow_chunk_abort is True
        assert config.memory_optimization is True
        assert config.progressive_chunking is True
    
    def test_overlap_minimum(self):
        """✅ Overlap не может быть меньше 1000"""
        config = ChunkingConfig.for_model(
            model_name='test/tiny-model',
            context_window=10000  # Очень маленькое окно
        )
        
        # safe_limit = 10000 * 0.8 = 8000
        # chunk_size = 8000 * 0.5 = 4000
        # overlap = 4000 * 0.01 = 40, но минимум 1000
        assert config.overlap_size == 1000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
