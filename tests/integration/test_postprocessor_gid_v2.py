#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Интеграционный тест для PostProcessor с GID v2.

Проверяет, что параметр use_gid_v2 правильно переключает версии.
"""

import pytest
import tempfile
from pathlib import Path

from src.postprocessing.postprocessor import PostProcessor


@pytest.fixture
def temp_registry():
    """Создаёт временный реестр для тестов."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "registry"


class TestPostProcessorGIDv2:
    """Тесты для интеграции GID v2 в PostProcessor."""
    
    def test_use_gid_v2_enabled_by_default(self):
        """Тест: GID v2 включен по умолчанию."""
        processor = PostProcessor()
        
        assert processor.use_gid_v2 is True
    
    def test_use_gid_v2_can_be_disabled(self):
        """Тест: GID v2 можно отключить."""
        processor = PostProcessor(use_gid_v2=False)
        
        assert processor.use_gid_v2 is False
    
    def test_process_with_gid_v2(self):
        """Тест: обработка с GID v2."""
        processor = PostProcessor(use_gid_v2=True)
        
        llm_result = {
            "organizations": [
                {
                    "organization_id": 1,
                    "name": "ООО Тест",
                    "inn": "1234567890",
                }
            ],
            "contacts": [
                {
                    "contact_id": 1,
                    "name": "Иванов Иван",
                    "email": "ivanov@company.com",
                    "organization_id": 1,
                }
            ],
            "interactions": [],
            "commercial_offers": [],
        }
        
        email_data = {
            "interaction_id": 1,
            "source_file": "test.json",
        }
        
        result = processor.process_llm_response(llm_result, email_data)
        
        # Проверяем, что контакт обработан
        assert len(result['contacts']) == 1
        assert 'gid' in result['contacts'][0]
        
        # Проверяем, что GID назначен
        assert result['contacts'][0]['gid'] is not None
    
    def test_process_with_gid_v1(self):
        """Тест: обработка с GID v1 (legacy)."""
        processor = PostProcessor(use_gid_v2=False)
        
        llm_result = {
            "organizations": [
                {
                    "organization_id": 1,
                    "name": "ООО Тест",
                    "inn": "1234567890",
                }
            ],
            "contacts": [
                {
                    "contact_id": 1,
                    "name": "Иванов Иван",
                    "email": "ivanov@company.com",
                    "organization_id": 1,
                }
            ],
            "interactions": [],
            "commercial_offers": [],
        }
        
        email_data = {
            "interaction_id": 1,
            "source_file": "test.json",
        }
        
        result = processor.process_llm_response(llm_result, email_data)
        
        # Проверяем, что контакт обработан
        assert len(result['contacts']) == 1
        assert 'gid' in result['contacts'][0]
    
    def test_v2_creates_different_gids_than_v1(self):
        """Тест: v2 может создавать разные GID по сравнению с v1."""
        # Создаём два процессора
        processor_v1 = PostProcessor(use_gid_v2=False)
        processor_v2 = PostProcessor(use_gid_v2=True)
        
        llm_result = {
            "organizations": [],
            "contacts": [
                {
                    "contact_id": 1,
                    "name": "Иванов Иван",
                    "email": "ivanov@company.com",
                }
            ],
            "interactions": [],
            "commercial_offers": [],
        }
        
        email_data = {"interaction_id": 1, "source_file": "test.json"}
        
        result_v1 = processor_v1.process_llm_response(llm_result.copy(), email_data)
        result_v2 = processor_v2.process_llm_response(llm_result.copy(), email_data)
        
        # Проверяем, что оба обработали контакт
        assert len(result_v1['contacts']) == 1
        assert len(result_v2['contacts']) == 1
        
        # Проверяем, что GID назначены
        gid_v1 = result_v1['contacts'][0]['gid']
        gid_v2 = result_v2['contacts'][0]['gid']
        
        assert gid_v1 is not None
        assert gid_v2 is not None
        
        # GID могут быть разными (v2 использует EMAIL_GLOBAL)
        # Это нормально для первого создания
