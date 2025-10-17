#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Юнит-тесты для ContactMentionsRepository.

Тестирует сохранение и получение упоминаний контактов без способов связи.
"""

import pytest
import tempfile
from pathlib import Path

from src.db.contact_mentions_repository import ContactMentionsRepository, ContactMention


@pytest.fixture
def temp_db():
    """Создаёт временную БД для тестов."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield f"sqlite:///{db_path}"
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def repo(temp_db):
    """Создаёт репозиторий с временной БД."""
    return ContactMentionsRepository(db_url=temp_db)


class TestContactMentionsRepository:
    """Тесты для ContactMentionsRepository."""
    
    def test_save_single_mention(self, repo):
        """Тест: сохранение одного упоминания."""
        mentions = [
            {
                "name": "Иванов Иван Иванович",
                "position": "Директор",
                "organization_id": 1,
                "role_in_message": "mentioned",
                "confidence": 0.85,
            }
        ]
        
        count = repo.save_contact_mentions(mentions, interaction_id=42, source_file="test.json")
        
        assert count == 1
    
    def test_save_multiple_mentions(self, repo):
        """Тест: сохранение нескольких упоминаний."""
        mentions = [
            {
                "name": "Иванов Иван",
                "position": "Директор",
                "organization_id": 1,
            },
            {
                "name": "Петрова Анна",
                "position": "Менеджер",
                "organization_id": 1,
            },
            {
                "name": "Сидоров Сергей",
                "organization_id": 2,
            },
        ]
        
        count = repo.save_contact_mentions(mentions, interaction_id=100)
        
        assert count == 3
    
    def test_save_empty_list(self, repo):
        """Тест: сохранение пустого списка."""
        count = repo.save_contact_mentions([], interaction_id=1)
        
        assert count == 0
    
    def test_save_mention_without_name(self, repo):
        """Тест: упоминание без имени пропускается."""
        mentions = [
            {
                "position": "Директор",
                "organization_id": 1,
            }
        ]
        
        count = repo.save_contact_mentions(mentions, interaction_id=1)
        
        assert count == 0
    
    def test_get_mentions_by_interaction(self, repo):
        """Тест: получение упоминаний по interaction_id."""
        mentions = [
            {"name": "Иванов Иван", "organization_id": 1},
            {"name": "Петрова Анна", "organization_id": 1},
        ]
        
        repo.save_contact_mentions(mentions, interaction_id=42)
        
        result = repo.get_mentions_by_interaction(42)
        
        assert len(result) == 2
        assert result[0].name in ["Иванов Иван", "Петрова Анна"]
        assert result[0].interaction_id == 42
    
    def test_get_mentions_by_organization(self, repo):
        """Тест: получение упоминаний по organization_id."""
        mentions = [
            {"name": "Иванов Иван", "organization_id": 1},
            {"name": "Петрова Анна", "organization_id": 1},
            {"name": "Сидоров Сергей", "organization_id": 2},
        ]
        
        repo.save_contact_mentions(mentions, interaction_id=1)
        
        result = repo.get_mentions_by_organization(1)
        
        assert len(result) == 2
        assert all(m.organization_id == 1 for m in result)
    
    def test_search_mentions_by_name(self, repo):
        """Тест: поиск упоминаний по имени."""
        mentions = [
            {"name": "Иванов Иван Иванович", "organization_id": 1},
            {"name": "Иванова Анна Петровна", "organization_id": 1},
            {"name": "Петров Пётр", "organization_id": 2},
        ]
        
        repo.save_contact_mentions(mentions, interaction_id=1)
        
        result = repo.search_mentions_by_name("%Иванов%")
        
        assert len(result) == 2
        assert all("Иванов" in m.name for m in result)
    
    def test_get_statistics(self, repo):
        """Тест: получение статистики."""
        mentions = [
            {"name": "Иванов Иван", "organization_id": 1, "mention_type": "signatory"},
            {"name": "Петрова Анна", "organization_id": 1, "mention_type": "signatory"},
            {"name": "Сидоров Сергей", "organization_id": 2, "mention_type": "mentioned"},
        ]
        
        repo.save_contact_mentions(mentions, interaction_id=1)
        
        stats = repo.get_statistics()
        
        assert stats["total_mentions"] == 3
        assert stats["by_mention_type"]["signatory"] == 2
        assert stats["by_mention_type"]["mentioned"] == 1
        assert 1 in stats["top_organizations"]
        assert 2 in stats["top_organizations"]
    
    def test_delete_mentions_by_interaction(self, repo):
        """Тест: удаление упоминаний по interaction_id."""
        mentions = [
            {"name": "Иванов Иван", "organization_id": 1},
            {"name": "Петрова Анна", "organization_id": 1},
        ]
        
        repo.save_contact_mentions(mentions, interaction_id=42)
        
        deleted_count = repo.delete_mentions_by_interaction(42)
        
        assert deleted_count == 2
        
        # Проверяем, что упоминания удалены
        result = repo.get_mentions_by_interaction(42)
        assert len(result) == 0
    
    def test_mention_with_context(self, repo):
        """Тест: сохранение упоминания с контекстом (город, адрес)."""
        mentions = [
            {
                "name": "Иванов Иван",
                "position": "Директор",
                "organization_id": 1,
                "city": "Москва",
                "address": "ул. Ленина, 1",
            }
        ]
        
        count = repo.save_contact_mentions(mentions, interaction_id=1)
        
        assert count == 1
        
        result = repo.get_mentions_by_interaction(1)
        assert len(result) == 1
        assert result[0].source_context is not None
        assert "Москва" in result[0].source_context
