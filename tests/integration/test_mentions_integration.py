#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Интеграционный тест для сохранения mentions в БД.

Проверяет полный цикл: фильтрация → сохранение в БД → чтение из БД.
"""

import pytest
import tempfile
from pathlib import Path

from src.postprocessing.postprocessor import PostProcessor
from src.db.contact_mentions_repository import ContactMentionsRepository


@pytest.fixture
def temp_db():
    """Создаёт временную БД для тестов."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield f"sqlite:///{db_path}"
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def postprocessor(temp_db):
    """Создаёт постпроцессор с временной БД."""
    # Создаём репозиторий с временной БД
    mentions_repo = ContactMentionsRepository(db_url=temp_db)
    
    # Создаём постпроцессор
    processor = PostProcessor()
    
    # Подменяем репозиторий на тестовый
    processor.mentions_repository = mentions_repo
    
    return processor


class TestMentionsIntegration:
    """Интеграционные тесты для сохранения mentions."""
    
    def test_filter_and_save_mentions(self, postprocessor, temp_db):
        """Тест: фильтрация контактов и сохранение mentions в БД."""
        # Подготовка данных
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
                    "email": "ivanov@test.ru",
                    "organization_id": 1,
                },
                {
                    "contact_id": 2,
                    "name": "Петров Пётр",
                    # Нет email и телефона → будет отфильтрован
                    "organization_id": 1,
                },
            ],
            "interactions": [],
            "commercial_offers": [],
        }
        
        email_data = {
            "interaction_id": 42,
            "source_file": "test_email.json",
            "message_id": "test-message-id",
        }
        
        # Обработка
        result = postprocessor.process_llm_response(llm_result, email_data)
        
        # Проверяем результат
        assert len(result['contacts']) == 1  # Только валидный контакт
        assert result['contacts'][0]['name'] == "Иванов Иван"
        
        assert len(result['contact_mentions']) == 1  # Один отфильтрованный
        assert result['contact_mentions'][0]['name'] == "Петров Пётр"
        
        # Проверяем сохранение в БД
        mentions_repo = ContactMentionsRepository(db_url=temp_db)
        saved_mentions = mentions_repo.get_mentions_by_interaction(42)
        
        assert len(saved_mentions) == 1
        assert saved_mentions[0].name == "Петров Пётр"
        assert saved_mentions[0].organization_id == 1
        assert saved_mentions[0].interaction_id == 42
    
    def test_multiple_mentions_save(self, postprocessor, temp_db):
        """Тест: сохранение нескольких mentions."""
        llm_result = {
            "organizations": [{"organization_id": 1, "name": "ООО Тест"}],
            "contacts": [
                {"contact_id": 1, "name": "Валидный", "email": "valid@test.ru", "organization_id": 1},
                {"contact_id": 2, "name": "Без контактов 1", "organization_id": 1},
                {"contact_id": 3, "name": "Без контактов 2", "organization_id": 1},
                {"contact_id": 4, "name": "Без контактов 3"},  # Без организации
            ],
            "interactions": [],
            "commercial_offers": [],
        }
        
        email_data = {"interaction_id": 100, "source_file": "test.json"}
        
        result = postprocessor.process_llm_response(llm_result, email_data)
        
        # Проверяем
        assert len(result['contacts']) == 1
        assert len(result['contact_mentions']) == 3
        
        # Проверяем БД
        mentions_repo = ContactMentionsRepository(db_url=temp_db)
        saved_mentions = mentions_repo.get_mentions_by_interaction(100)
        
        assert len(saved_mentions) == 3
        names = {m.name for m in saved_mentions}
        assert names == {"Без контактов 1", "Без контактов 2", "Без контактов 3"}
    
    def test_no_mentions_no_save(self, postprocessor, temp_db):
        """Тест: если нет mentions, ничего не сохраняется."""
        llm_result = {
            "organizations": [{"organization_id": 1, "name": "ООО Тест"}],
            "contacts": [
                {"contact_id": 1, "name": "Валидный 1", "email": "v1@test.ru", "organization_id": 1},
                {"contact_id": 2, "name": "Валидный 2", "email": "v2@test.ru", "organization_id": 1},
            ],
            "interactions": [],
            "commercial_offers": [],
        }
        
        email_data = {"interaction_id": 200, "source_file": "test.json"}
        
        result = postprocessor.process_llm_response(llm_result, email_data)
        
        # Проверяем
        assert len(result['contacts']) == 2
        assert len(result['contact_mentions']) == 0
        
        # Проверяем БД
        mentions_repo = ContactMentionsRepository(db_url=temp_db)
        saved_mentions = mentions_repo.get_mentions_by_interaction(200)
        
        assert len(saved_mentions) == 0
    
    def test_mentions_with_phones(self, postprocessor, temp_db):
        """Тест: контакты с телефонами не фильтруются."""
        llm_result = {
            "organizations": [{"organization_id": 1, "name": "ООО Тест"}],
            "contacts": [
                {
                    "contact_id": 1,
                    "name": "С телефоном",
                    "phones": [{"number": "+79001234567", "type": "mobile"}],
                    "organization_id": 1,
                },
                {
                    "contact_id": 2,
                    "name": "Без контактов",
                    "organization_id": 1,
                },
            ],
            "interactions": [],
            "commercial_offers": [],
        }
        
        email_data = {"interaction_id": 300, "source_file": "test.json"}
        
        result = postprocessor.process_llm_response(llm_result, email_data)
        
        # Контакт с телефоном остаётся валидным
        assert len(result['contacts']) == 1
        assert result['contacts'][0]['name'] == "С телефоном"
        
        # Контакт без контактов отфильтрован
        assert len(result['contact_mentions']) == 1
        assert result['contact_mentions'][0]['name'] == "Без контактов"
