#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Юнит-тесты для iter_org_keys() с детерминированным fallback (GID v2).

Проверяет, что:
1. Случайный FALLBACK заменён на детерминированный NAME
2. Организации с одинаковым названием получают одинаковый ключ
3. Приоритет ключей: INN > DOMAIN > NAME_CITY > EMAIL_DOMAIN > NAME
"""

import pytest
from src.registry.global_registry import iter_org_keys


class TestIterOrgKeysV2:
    """Тесты для iter_org_keys() с детерминированным fallback."""
    
    # ========================================================================
    # Тесты для приоритета ключей
    # ========================================================================
    
    def test_priority_inn_first(self):
        """Тест: INN имеет наивысший приоритет."""
        org = {
            "name": "ООО Компания",
            "inn": "1234567890",
            "website": "company.com",
            "city": "Москва"
        }
        
        keys = list(iter_org_keys(org))
        
        # Первый ключ должен быть INN
        assert keys[0] == ("ORG", "INN", "1234567890")
    
    def test_priority_domain_second(self):
        """Тест: DOMAIN идёт после INN."""
        org = {
            "name": "ООО Компания",
            "website": "company.com"
        }
        
        keys = list(iter_org_keys(org))
        
        # Первый ключ — DOMAIN (нет INN)
        assert keys[0] == ("ORG", "DOMAIN", "company.com")
    
    def test_priority_name_city_third(self):
        """Тест: NAME_CITY идёт после DOMAIN."""
        org = {
            "name": "ООО Компания",
            "city": "Москва"
        }
        
        keys = list(iter_org_keys(org))
        
        # Проверяем, что есть NAME_CITY
        assert any(k[1] == "NAME_CITY" for k in keys)
    
    # ========================================================================
    # Тесты для детерминированного NAME (вместо FALLBACK)
    # ========================================================================
    
    def test_name_key_instead_of_fallback(self):
        """Тест: используется NAME вместо случайного FALLBACK."""
        org = {
            "name": "ООО Компания"
        }
        
        keys = list(iter_org_keys(org))
        
        # Проверяем, что есть ключ NAME (без ООО - нормализация)
        assert ("ORG", "NAME", "компания") in keys
        
        # Проверяем, что НЕТ ключа FALLBACK
        assert not any(k[1] == "FALLBACK" for k in keys)
    
    def test_name_key_deterministic(self):
        """Тест: NAME ключ детерминированный (одинаковое имя → одинаковый ключ)."""
        org1 = {"name": "ООО Компания"}
        org2 = {"name": "ООО Компания"}
        
        keys1 = list(iter_org_keys(org1))
        keys2 = list(iter_org_keys(org2))
        
        # Проверяем, что ключи одинаковые
        assert keys1 == keys2
        
        # Проверяем, что это NAME ключ (без ООО - нормализация)
        assert ("ORG", "NAME", "компания") in keys1
    
    def test_name_key_different_names(self):
        """Тест: разные имена → разные NAME ключи."""
        org1 = {"name": "ООО Компания А"}
        org2 = {"name": "ООО Компания Б"}
        
        keys1 = list(iter_org_keys(org1))
        keys2 = list(iter_org_keys(org2))
        
        # Проверяем, что ключи разные
        assert keys1 != keys2
        
        # Проверяем NAME ключи (без ООО - нормализация)
        assert ("ORG", "NAME", "компания а") in keys1
        assert ("ORG", "NAME", "компания б") in keys2
    
    def test_name_key_normalization(self):
        """Тест: NAME нормализуется (lowercase, без лишних пробелов)."""
        org = {"name": "  ООО  КОМПАНИЯ  "}
        
        keys = list(iter_org_keys(org))
        
        # Проверяем нормализацию (ООО удаляется, пробелы нормализуются)
        assert ("ORG", "NAME", "компания") in keys
    
    # ========================================================================
    # Тесты для полного набора ключей
    # ========================================================================
    
    def test_all_keys_present(self):
        """Тест: все ключи генерируются в правильном порядке."""
        org = {
            "name": "ООО Компания",
            "inn": "1234567890",
            "website": "company.com",
            "city": "Москва",
            "emails": ["info@company.com"]
        }
        
        keys = list(iter_org_keys(org))
        
        # Проверяем наличие всех типов ключей
        key_types = [k[1] for k in keys]
        
        assert "INN" in key_types
        assert "DOMAIN" in key_types
        assert "NAME_CITY" in key_types
        assert "EMAIL_DOMAIN" in key_types
        assert "NAME" in key_types
        
        # Проверяем, что FALLBACK отсутствует
        assert "FALLBACK" not in key_types
    
    def test_minimal_org_only_name(self):
        """Тест: минимальная организация (только имя) → только NAME ключ."""
        org = {"name": "ООО Компания"}
        
        keys = list(iter_org_keys(org))
        
        # Должен быть только один ключ — NAME (без ООО)
        assert len(keys) == 1
        assert keys[0] == ("ORG", "NAME", "компания")
    
    def test_org_without_name(self):
        """Тест: организация без имени → нет NAME ключа."""
        org = {
            "inn": "1234567890",
            "website": "company.com"
        }
        
        keys = list(iter_org_keys(org))
        
        # Проверяем, что есть INN и DOMAIN
        assert ("ORG", "INN", "1234567890") in keys
        assert ("ORG", "DOMAIN", "company.com") in keys
        
        # Проверяем, что НЕТ NAME ключа
        assert not any(k[1] == "NAME" for k in keys)
    
    # ========================================================================
    # Тесты для дедупликации
    # ========================================================================
    
    def test_no_duplicate_keys(self):
        """Тест: нет дубликатов ключей."""
        org = {
            "name": "ООО Компания",
            "website": "company.com",
            "emails": ["info@company.com", "sales@company.com"]
        }
        
        keys = list(iter_org_keys(org))
        
        # Проверяем, что нет дубликатов
        assert len(keys) == len(set(keys))
    
    def test_domain_deduplication(self):
        """Тест: домены дедуплицируются."""
        org = {
            "name": "ООО Компания",
            "website": "company.com",
            "emails": ["info@company.com"]  # Тот же домен
        }
        
        keys = list(iter_org_keys(org))
        
        # Проверяем, что DOMAIN встречается только один раз
        domain_keys = [k for k in keys if k[1] == "DOMAIN"]
        assert len(domain_keys) == 1
        assert domain_keys[0] == ("ORG", "DOMAIN", "company.com")
    
    # ========================================================================
    # Тесты для обратной совместимости
    # ========================================================================
    
    def test_name_city_still_works(self):
        """Тест: NAME_CITY ключ всё ещё работает."""
        org = {
            "name": "ООО Компания",
            "city": "Москва"
        }
        
        keys = list(iter_org_keys(org))
        
        # Проверяем, что есть NAME_CITY (без ООО)
        assert ("ORG", "NAME_CITY", "компания", "москва") in keys
        
        # Проверяем, что есть NAME (как fallback, без ООО)
        assert ("ORG", "NAME", "компания") in keys
    
    def test_inn_still_priority(self):
        """Тест: INN остаётся приоритетным ключом."""
        org = {
            "name": "ООО Компания",
            "inn": "1234567890"
        }
        
        keys = list(iter_org_keys(org))
        
        # INN должен быть первым
        assert keys[0] == ("ORG", "INN", "1234567890")
    
    # ========================================================================
    # Граничные случаи
    # ========================================================================
    
    def test_empty_org(self):
        """Тест: пустая организация → нет ключей."""
        org = {}
        
        keys = list(iter_org_keys(org))
        
        # Нет ключей
        assert len(keys) == 0
    
    def test_org_with_empty_name(self):
        """Тест: пустое имя → нет NAME ключа."""
        org = {"name": ""}
        
        keys = list(iter_org_keys(org))
        
        # Нет ключей
        assert len(keys) == 0
    
    def test_org_with_whitespace_name(self):
        """Тест: имя из пробелов → нет NAME ключа."""
        org = {"name": "   "}
        
        keys = list(iter_org_keys(org))
        
        # Нет ключей (пробелы удаляются при нормализации)
        assert len(keys) == 0
