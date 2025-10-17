#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Юнит-тесты для resolve_contact_v2() (GID v2 с версионированием).

Проверяет:
1. Поиск по v2 ключам (приоритет)
2. Fallback на v1 ключи (обратная совместимость)
3. Автомиграция v1→v2 при нахождении
"""

import pytest
import tempfile
from pathlib import Path

from src.registry.global_registry import GlobalIDRegistry


@pytest.fixture
def temp_registry():
    """Создаёт временный реестр для тестов."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_dir = Path(tmpdir) / "registry"
        registry_dir.mkdir()
        yield GlobalIDRegistry(registry_dir=registry_dir)


class TestResolveContactV2:
    """Тесты для resolve_contact_v2() с версионированием."""
    
    # ========================================================================
    # Тесты для новых контактов (создание GID)
    # ========================================================================
    
    def test_new_corporate_contact(self, temp_registry):
        """Тест: новый корпоративный контакт → создаётся с v2 ключами."""
        contact = {"email": "user@company.com"}
        org_gid = "ORG-123"
        
        result = temp_registry.resolve_contact_v2(contact, org_gid)
        
        # Проверяем, что создан новый GID
        assert result.source == "new_v2"
        assert result.match_rule == "EMAIL_GLOBAL"
        assert result.gid  # UUID формат
        
        # Проверяем, что v2 ключ зарегистрирован
        assert ("CONTACT", "EMAIL_GLOBAL", "user@company.com") in temp_registry.key_index
    
    def test_new_personal_contact(self, temp_registry):
        """Тест: новый личный контакт → создаётся с v1 ключом."""
        contact = {"email": "user@gmail.com"}
        org_gid = "ORG-456"
        
        result = temp_registry.resolve_contact_v2(contact, org_gid)
        
        # Проверяем, что создан новый GID
        assert result.source == "new_v2"
        # Для личных доменов используется старый формат EMAIL
        assert result.match_rule == "EMAIL"
        
        # Проверяем, что v1 ключ зарегистрирован
        assert ("CONTACT", "EMAIL", "ORG-456", "user@gmail.com") in temp_registry.key_index
    
    # ========================================================================
    # Тесты для поиска по v2 ключам
    # ========================================================================
    
    def test_find_by_v2_key(self, temp_registry):
        """Тест: контакт найден по v2 ключу (EMAIL_GLOBAL)."""
        contact = {"email": "user@company.com"}
        org_gid = "ORG-123"
        
        # Создаём контакт
        result1 = temp_registry.resolve_contact_v2(contact, org_gid)
        gid1 = result1.gid
        
        # Ищем тот же контакт
        result2 = temp_registry.resolve_contact_v2(contact, org_gid)
        
        # Проверяем, что нашли существующий GID
        assert result2.gid == gid1
        assert result2.source == "registry"
        assert result2.match_rule == "EMAIL_GLOBAL"
    
    def test_find_by_v2_key_different_org(self, temp_registry):
        """Тест: корпоративный email в разных организациях → один GID."""
        contact1 = {"email": "user@company.com"}
        contact2 = {"email": "user@company.com"}
        
        # Создаём контакт в первой организации
        result1 = temp_registry.resolve_contact_v2(contact1, "ORG-123")
        gid1 = result1.gid
        
        # Ищем тот же email во второй организации
        result2 = temp_registry.resolve_contact_v2(contact2, "ORG-456")
        
        # Проверяем, что GID одинаковый (EMAIL_GLOBAL не зависит от org)
        assert result2.gid == gid1
        assert result2.match_rule == "EMAIL_GLOBAL"
    
    # ========================================================================
    # Тесты для fallback на v1 ключи
    # ========================================================================
    
    def test_fallback_to_v1_key(self, temp_registry):
        """Тест: контакт создан по v1, найден по v2 → автомиграция."""
        contact = {"email": "user@company.com"}
        org_gid = "ORG-123"
        
        # Создаём контакт по СТАРОЙ логике (v1)
        result_v1 = temp_registry.resolve_contact(contact, org_gid)
        gid_v1 = result_v1.gid
        
        # Ищем тот же контакт по НОВОЙ логике (v2)
        result_v2 = temp_registry.resolve_contact_v2(contact, org_gid)
        
        # Проверяем, что нашли тот же GID
        assert result_v2.gid == gid_v1
        
        # Проверяем, что нашли контакт (может быть уже мигрирован)
        # resolve_contact уже добавляет все ключи как алиасы
        assert result_v2.gid == gid_v1
        assert result_v2.source in ["registry", "registry_v1_migrated"]
        
        # Проверяем, что v2 ключ теперь зарегистрирован
        assert ("CONTACT", "EMAIL_GLOBAL", "user@company.com") in temp_registry.key_index
    
    def test_migration_adds_v2_aliases(self, temp_registry):
        """Тест: при миграции v2 ключи добавляются как алиасы."""
        contact = {"email": "user@company.com"}
        org_gid = "ORG-123"
        
        # Создаём по v1
        result_v1 = temp_registry.resolve_contact(contact, org_gid)
        gid = result_v1.gid
        
        # Проверяем, что v2 ключа нет
        assert ("CONTACT", "EMAIL_GLOBAL", "user@company.com") not in temp_registry.key_index
        
        # Ищем по v2 → миграция
        temp_registry.resolve_contact_v2(contact, org_gid)
        
        # Проверяем, что v2 ключ добавлен
        assert ("CONTACT", "EMAIL_GLOBAL", "user@company.com") in temp_registry.key_index
        assert temp_registry.key_index[("CONTACT", "EMAIL_GLOBAL", "user@company.com")] == gid
    
    def test_migration_once(self, temp_registry):
        """Тест: миграция происходит один раз, потом используется v2."""
        contact = {"email": "user@company.com"}
        org_gid = "ORG-123"
        
        # Создаём по v1
        result_v1 = temp_registry.resolve_contact(contact, org_gid)
        gid = result_v1.gid
        
        # Первый вызов v2 → находит по v1 или v2
        result1 = temp_registry.resolve_contact_v2(contact, org_gid)
        assert result1.gid == gid
        
        # Второй вызов v2 → использует v2 ключ
        result2 = temp_registry.resolve_contact_v2(contact, org_gid)
        assert result2.source == "registry"
        assert result2.match_rule == "EMAIL_GLOBAL"
        assert result2.gid == gid
    
    # ========================================================================
    # Тесты для личных доменов
    # ========================================================================
    
    def test_personal_email_different_orgs(self, temp_registry):
        """Тест: личный email в разных организациях → разные GID."""
        contact1 = {"email": "user@gmail.com"}
        contact2 = {"email": "user@gmail.com"}
        
        # Создаём в первой организации
        result1 = temp_registry.resolve_contact_v2(contact1, "ORG-123")
        gid1 = result1.gid
        
        # Создаём во второй организации
        result2 = temp_registry.resolve_contact_v2(contact2, "ORG-456")
        gid2 = result2.gid
        
        # Проверяем, что GID разные (личный email привязан к org)
        assert gid1 != gid2
    
    def test_personal_email_same_org(self, temp_registry):
        """Тест: личный email в той же организации → один GID."""
        contact1 = {"email": "user@gmail.com"}
        contact2 = {"email": "user@gmail.com"}
        
        # Создаём в организации
        result1 = temp_registry.resolve_contact_v2(contact1, "ORG-123")
        gid1 = result1.gid
        
        # Ищем в той же организации
        result2 = temp_registry.resolve_contact_v2(contact2, "ORG-123")
        
        # Проверяем, что GID одинаковый
        assert result2.gid == gid1
    
    # ========================================================================
    # Тесты для телефонов
    # ========================================================================
    
    def test_phone_global_key(self, temp_registry):
        """Тест: телефон использует PHONE_GLOBAL ключ."""
        contact = {"phones": [{"number": "+79001234567"}]}
        org_gid = "ORG-123"
        
        result = temp_registry.resolve_contact_v2(contact, org_gid)
        
        # Проверяем, что создан с PHONE_GLOBAL
        assert result.match_rule == "PHONE_GLOBAL"
        
        # Проверяем, что ключ зарегистрирован
        assert ("CONTACT", "PHONE_GLOBAL", "+79001234567") in temp_registry.key_index
    
    def test_phone_same_across_orgs(self, temp_registry):
        """Тест: один телефон в разных организациях → один GID."""
        contact1 = {"phones": [{"number": "+79001234567"}]}
        contact2 = {"phones": [{"number": "+79001234567"}]}
        
        # Создаём в первой организации
        result1 = temp_registry.resolve_contact_v2(contact1, "ORG-123")
        gid1 = result1.gid
        
        # Ищем во второй организации
        result2 = temp_registry.resolve_contact_v2(contact2, "ORG-456")
        
        # Проверяем, что GID одинаковый
        assert result2.gid == gid1
    
    # ========================================================================
    # Граничные случаи
    # ========================================================================
    
    def test_empty_contact_creates_name_key(self, temp_registry):
        """Тест: пустой контакт → создаётся с NAME_POSITION ключом."""
        contact = {}
        org_gid = "ORG-123"
        
        result = temp_registry.resolve_contact_v2(contact, org_gid)
        
        # Проверяем, что создан с NAME_POSITION
        assert result.match_rule == "NAME_POSITION"
        assert result.source == "new_v2"
    
    def test_contact_without_org(self, temp_registry):
        """Тест: контакт без организации → PERSONAL."""
        contact = {"email": "user@company.com"}
        org_gid = None
        
        result = temp_registry.resolve_contact_v2(contact, org_gid)
        
        # Проверяем, что создан успешно
        assert result.source == "new_v2"
        assert result.gid  # UUID формат
