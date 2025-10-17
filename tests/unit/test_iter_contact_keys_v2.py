#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Юнит-тесты для iter_contact_keys_v2() (GID v2).

Проверяет двухуровневую систему ключей:
- Личные домены → старая логика (EMAIL с org_gid)
- Корпоративные домены → новая логика (EMAIL_GLOBAL + EMAIL_IN_ORG)
"""

import pytest
from src.registry.global_registry import iter_contact_keys_v2


class TestIterContactKeysV2:
    """Тесты для iter_contact_keys_v2()."""
    
    # ========================================================================
    # Тесты для корпоративных email
    # ========================================================================
    
    def test_corporate_email_with_org(self):
        """Тест: корпоративный email с организацией → EMAIL_GLOBAL + EMAIL_IN_ORG."""
        contact = {"email": "ivanov@company.com"}
        org_gid = "ORG-123"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем первый ключ — EMAIL_GLOBAL
        assert keys[0] == ("CONTACT", "EMAIL_GLOBAL", "ivanov@company.com")
        
        # Проверяем второй ключ — EMAIL_IN_ORG
        assert keys[1] == ("CONTACT", "EMAIL_IN_ORG", "ORG-123", "ivanov@company.com")
    
    def test_corporate_email_without_org(self):
        """Тест: корпоративный email без организации → только EMAIL_GLOBAL."""
        contact = {"email": "ivanov@company.com"}
        org_gid = None
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем, что есть EMAIL_GLOBAL
        assert ("CONTACT", "EMAIL_GLOBAL", "ivanov@company.com") in keys
        
        # Проверяем, что НЕТ EMAIL_IN_ORG (нет организации)
        assert not any(k[1] == "EMAIL_IN_ORG" for k in keys)
    
    def test_corporate_email_priority(self):
        """Тест: EMAIL_GLOBAL имеет приоритет над EMAIL_IN_ORG."""
        contact = {"email": "user@company.com"}
        org_gid = "ORG-456"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # EMAIL_GLOBAL должен быть первым
        assert keys[0][1] == "EMAIL_GLOBAL"
        # EMAIL_IN_ORG должен быть вторым
        assert keys[1][1] == "EMAIL_IN_ORG"
    
    # ========================================================================
    # Тесты для личных email
    # ========================================================================
    
    def test_personal_email_gmail(self):
        """Тест: gmail.com → старая логика (EMAIL с org_gid)."""
        contact = {"email": "user@gmail.com"}
        org_gid = "ORG-789"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем, что используется старый формат EMAIL
        assert ("CONTACT", "EMAIL", "ORG-789", "user@gmail.com") in keys
        
        # Проверяем, что НЕТ EMAIL_GLOBAL
        assert not any(k[1] == "EMAIL_GLOBAL" for k in keys)
    
    def test_personal_email_yandex(self):
        """Тест: yandex.ru → старая логика."""
        contact = {"email": "user@yandex.ru"}
        org_gid = "ORG-ABC"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        assert ("CONTACT", "EMAIL", "ORG-ABC", "user@yandex.ru") in keys
        assert not any(k[1] == "EMAIL_GLOBAL" for k in keys)
    
    def test_personal_email_mail_ru(self):
        """Тест: mail.ru → старая логика."""
        contact = {"email": "user@mail.ru"}
        org_gid = "ORG-XYZ"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        assert ("CONTACT", "EMAIL", "ORG-XYZ", "user@mail.ru") in keys
        assert not any(k[1] == "EMAIL_GLOBAL" for k in keys)
    
    def test_personal_email_without_org(self):
        """Тест: личный email без организации → EMAIL с PERSONAL."""
        contact = {"email": "user@gmail.com"}
        org_gid = None
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        assert ("CONTACT", "EMAIL", "PERSONAL", "user@gmail.com") in keys
    
    # ========================================================================
    # Тесты для телефонов
    # ========================================================================
    
    def test_phone_global_with_org(self):
        """Тест: телефон → PHONE_GLOBAL + PHONE_IN_ORG."""
        contact = {
            "phones": [{"number": "+79001234567"}]
        }
        org_gid = "ORG-123"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем PHONE_GLOBAL
        assert ("CONTACT", "PHONE_GLOBAL", "+79001234567") in keys
        
        # Проверяем PHONE_IN_ORG
        assert ("CONTACT", "PHONE_IN_ORG", "ORG-123", "+79001234567") in keys
    
    def test_phone_global_without_org(self):
        """Тест: телефон без организации → только PHONE_GLOBAL."""
        contact = {
            "phones": [{"number": "+79001234567"}]
        }
        org_gid = None
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем PHONE_GLOBAL
        assert ("CONTACT", "PHONE_GLOBAL", "+79001234567") in keys
        
        # Проверяем, что НЕТ PHONE_IN_ORG
        assert not any(k[1] == "PHONE_IN_ORG" for k in keys)
    
    def test_multiple_phones(self):
        """Тест: несколько телефонов → все генерируют ключи."""
        contact = {
            "phones": [
                {"number": "+79001234567"},
                {"number": "+79009876543"}
            ]
        }
        org_gid = "ORG-456"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем, что оба телефона есть
        assert ("CONTACT", "PHONE_GLOBAL", "+79001234567") in keys
        assert ("CONTACT", "PHONE_GLOBAL", "+79009876543") in keys
        assert ("CONTACT", "PHONE_IN_ORG", "ORG-456", "+79001234567") in keys
        assert ("CONTACT", "PHONE_IN_ORG", "ORG-456", "+79009876543") in keys
    
    # ========================================================================
    # Комбинированные тесты
    # ========================================================================
    
    def test_corporate_email_and_phone(self):
        """Тест: корпоративный email + телефон."""
        contact = {
            "email": "user@company.com",
            "phones": [{"number": "+79001234567"}]
        }
        org_gid = "ORG-789"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Email ключи
        assert ("CONTACT", "EMAIL_GLOBAL", "user@company.com") in keys
        assert ("CONTACT", "EMAIL_IN_ORG", "ORG-789", "user@company.com") in keys
        
        # Phone ключи
        assert ("CONTACT", "PHONE_GLOBAL", "+79001234567") in keys
        assert ("CONTACT", "PHONE_IN_ORG", "ORG-789", "+79001234567") in keys
    
    def test_personal_email_and_phone(self):
        """Тест: личный email + телефон."""
        contact = {
            "email": "user@gmail.com",
            "phones": [{"number": "+79001234567"}]
        }
        org_gid = "ORG-ABC"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Email: старая логика
        assert ("CONTACT", "EMAIL", "ORG-ABC", "user@gmail.com") in keys
        
        # Phone: новая логика
        assert ("CONTACT", "PHONE_GLOBAL", "+79001234567") in keys
        assert ("CONTACT", "PHONE_IN_ORG", "ORG-ABC", "+79001234567") in keys
    
    def test_name_position_key(self):
        """Тест: имя + должность генерирует ключ NAME_POSITION."""
        contact = {
            "name": "Иванов Иван",
            "position": "Директор"
        }
        org_gid = "ORG-123"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем, что есть ключ NAME_POSITION
        assert any(k[1] == "NAME_POSITION" for k in keys)
        
        # Проверяем формат ключа
        name_key = [k for k in keys if k[1] == "NAME_POSITION"][0]
        assert name_key[0] == "CONTACT"
        assert name_key[2] == "ORG-123"  # org_key
    
    # ========================================================================
    # Граничные случаи
    # ========================================================================
    
    def test_empty_contact(self):
        """Тест: пустой контакт → только NAME_POSITION с пустыми значениями."""
        contact = {}
        org_gid = "ORG-123"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Должен быть хотя бы один ключ (NAME_POSITION)
        assert len(keys) >= 1
        assert keys[-1][1] == "NAME_POSITION"
    
    def test_no_duplicates(self):
        """Тест: нет дубликатов ключей."""
        contact = {
            "email": "user@company.com",
            "phones": [
                {"number": "+79001234567"},
                {"number": "+79001234567"}  # Дубликат
            ]
        }
        org_gid = "ORG-123"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем, что нет дубликатов
        assert len(keys) == len(set(keys))
    
    def test_email_normalization(self):
        """Тест: email нормализуется (lowercase, strip)."""
        contact = {"email": "  User@Company.COM  "}
        org_gid = "ORG-123"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем, что email нормализован
        assert ("CONTACT", "EMAIL_GLOBAL", "user@company.com") in keys
    
    def test_phone_normalization(self):
        """Тест: телефон нормализуется в E.164."""
        contact = {
            "phones": [{"number": "8 (900) 123-45-67"}]
        }
        org_gid = "ORG-123"
        
        keys = list(iter_contact_keys_v2(contact, org_gid))
        
        # Проверяем, что телефон нормализован
        assert any("+7900" in str(k) for k in keys)
