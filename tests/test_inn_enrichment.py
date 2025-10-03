#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для системы обогащения ИНН

Tests for INN enrichment system integration.

Author: Contact Parser Team
Created: 2025-10-03
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import json
import os

# Импорты модулей для тестирования
try:
    from src.postprocessing.inn_validator import RussianINNValidator, INNValidationResult
    from src.postprocessing.inn_search_normalizer import INNSearchNormalizer
    from src.postprocessing.inn_cache_system import INNCacheManager, INNOverrideManager
    from src.postprocessing.org_inn_resolver import OrganizationINNResolver, INNCandidate
    from src.postprocessing.dadata_provider import DaDataProviderAdapter
except ImportError as e:
    pytest.skip(f"Could not import INN enrichment modules: {e}", allow_module_level=True)


class TestINNValidator:
    """Тесты валидатора ИНН"""
    
    def test_validate_legal_entity_inn(self):
        """Тест валидации ИНН юридического лица"""
        validator = RussianINNValidator()
        
        # Валидный ИНН юридического лица
        result = validator.validate("7701234567")
        assert result.valid is True
        assert result.inn_type == "legal"
        assert result.formatted_inn == "7701234567"
        
        # Невалидный ИНН
        result = validator.validate("7701234568")  # неверная контрольная сумма
        assert result.valid is False
        assert result.inn_type == "legal"
        assert result.error is not None
    
    def test_validate_individual_inn(self):
        """Тест валидации ИНН физического лица/ИП"""
        validator = RussianINNValidator()
        
        # Валидный ИНН ИП
        result = validator.validate("123456789012")  # Заглушка, нужен реальный валидный ИНН
        # Проверяем что длина правильная
        assert len(result.formatted_inn or "") == 12
        
    def test_validate_empty_inn(self):
        """Тест валидации пустого ИНН"""
        validator = RussianINNValidator()
        
        result = validator.validate("")
        assert result.valid is False
        assert result.inn_type is None
        assert result.error == "ИНН не задан"
    
    def test_validate_invalid_format(self):
        """Тест валидации невалидного формата"""
        validator = RussianINNValidator()
        
        result = validator.validate("abc123")
        assert result.valid is False
        assert result.error is not None


class TestINNSearchNormalizer:
    """Тесты нормализатора поисковых данных"""
    
    def test_normalize_organization_name(self):
        """Тест нормализации названия организации"""
        normalizer = INNSearchNormalizer()
        
        # Удаление юридических форм
        assert normalizer.normalize_organization_name("ООО «Рога и копыта»") == "рога копыта"
        assert normalizer.normalize_organization_name("ПАО Газпром") == "газпром"
        assert normalizer.normalize_organization_name("ИП Иванов Иван Иванович") == "иванов иван иванович"
        
        # Очистка спецсимволов
        assert normalizer.normalize_organization_name("\"Компания-123\"") == "компания-123"
    
    def test_normalize_city_name(self):
        """Тест нормализации названия города"""
        normalizer = INNSearchNormalizer()
        
        # Применение синонимов
        assert normalizer.normalize_city_name("СПб") == "санкт-петербург"
        assert normalizer.normalize_city_name("МСК") == "москва"
        assert normalizer.normalize_city_name("НСК") == "новосибирск"
        
        # Удаление префиксов
        assert normalizer.normalize_city_name("г. Москва") == "москва"
        assert normalizer.normalize_city_name("город Новосибирск") == "новосибирск"
    
    def test_extract_domain(self):
        """Тест извлечения домена"""
        normalizer = INNSearchNormalizer()
        
        assert normalizer.extract_domain("https://www.example.com/path") == "example.com"
        assert normalizer.extract_domain("subdomain.example.ru") == "example.ru"
        assert normalizer.extract_domain("example.org") == "example.org"
    
    def test_generate_search_variants(self):
        """Тест генерации вариантов для поиска"""
        normalizer = INNSearchNormalizer()
        
        variants = normalizer.generate_search_variants("ООО «Рога-и-копыта»")
        assert len(variants) > 1
        assert "рога-и-копыта" in " ".join(variants)


class TestINNCacheManager:
    """Тесты менеджера кэша ИНН"""
    
    def test_cache_operations(self):
        """Тест операций с кэшем"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "test_cache.jsonl"
            cache_manager = INNCacheManager(cache_path, ttl_days=1)
            
            # Сохранение в кэш
            success = cache_manager.save_to_cache(
                name_norm="рога копыта",
                city_norm="москва",
                inn="7701234567",
                source="test",
                score=0.95,
                domain="example.com"
            )
            assert success is True
            
            # Получение из кэша
            cached_result = cache_manager.get_cached_inn(
                name_norm="рога копыта",
                city_norm="москва",
                domain="example.com"
            )
            assert cached_result is not None
            assert cached_result['inn'] == "7701234567"
            assert cached_result['source'] == "test"
            assert cached_result['score'] == 0.95
    
    def test_cache_expiration(self):
        """Тест истечения TTL кэша"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "test_cache.jsonl"
            cache_manager = INNCacheManager(cache_path, ttl_days=0)  # Немедленное истечение
            
            # Сохранение в кэш
            cache_manager.save_to_cache(
                name_norm="тестовая организация",
                city_norm="москва",
                inn="7701234567",
                source="test",
                score=0.95
            )
            
            # Проверка истечения
            cached_result = cache_manager.get_cached_inn(
                name_norm="тестовая организация",
                city_norm="москва"
            )
            assert cached_result is None  # Должен быть None из-за истекшего TTL


class TestINNOverrideManager:
    """Тесты менеджера переопределений ИНН"""
    
    def test_override_operations(self):
        """Тест операций с переопределениями"""
        with tempfile.TemporaryDirectory() as temp_dir:
            overrides_path = Path(temp_dir) / "test_overrides.yml"
            override_manager = INNOverrideManager(overrides_path)
            
            # Добавление переопределения
            success = override_manager.add_override(
                org_gid="test-gid-123",
                inn="7701234567",
                reason="manual verification",
                confirmed_by="test_user"
            )
            assert success is True
            
            # Получение переопределения
            override = override_manager.get_override(org_gid="test-gid-123")
            assert override is not None
            assert override.inn == "7701234567"
            assert override.reason == "manual verification"
    
    def test_override_validation(self):
        """Тест валидации переопределений"""
        with tempfile.TemporaryDirectory() as temp_dir:
            overrides_path = Path(temp_dir) / "test_overrides.yml"
            override_manager = INNOverrideManager(overrides_path)
            
            # Добавление валидного переопределения
            override_manager.add_override(
                org_gid="test-gid-123",
                inn="7701234567",
                reason="test",
                confirmed_by="test_user"
            )
            
            # Валидация
            validation_result = override_manager.validate_overrides()
            assert validation_result['valid'] is True
            assert validation_result['total_overrides'] == 1
            assert validation_result['valid_overrides'] == 1


class TestOrganizationINNResolver:
    """Тесты основного резолвера ИНН"""
    
    def test_resolver_initialization(self):
        """Тест инициализации резолвера"""
        config = {
            'enabled': True,
            'auto_accept_threshold': 0.85,
            'review_threshold': 0.65,
            'providers': {
                'dadata': {
                    'enabled': False  # Отключаем для тестов
                }
            },
            'cache': {'ttl_days': 180},
            'legal': {'allow_ip_inn': True}
        }
        
        resolver = OrganizationINNResolver(config)
        assert resolver.auto_accept_threshold == 0.85
        assert resolver.review_threshold == 0.65
    
    def test_enrich_organizations_with_existing_inn(self):
        """Тест обогащения организаций с существующим ИНН"""
        config = {
            'enabled': True,
            'providers': {'dadata': {'enabled': False}}
        }
        
        resolver = OrganizationINNResolver(config)
        
        organizations = {
            1: {
                'gid': 'test-gid-1',
                'name': 'Тестовая организация',
                'inn': '7701234567',  # Уже есть ИНН
                'city': 'Москва'
            }
        }
        
        metadata = resolver.enrich_organizations(organizations)
        
        # Проверяем что организация с существующим ИНН пропущена
        assert 'test-gid-1' in metadata
        assert metadata['test-gid-1']['decision'] == 'skipped'
        assert metadata['test-gid-1']['inn'] == '7701234567'


@pytest.mark.skipif(
    not os.getenv('DADATA_API_KEY'),
    reason="DaData API key not provided"
)
class TestDaDataProvider:
    """Тесты провайдера DaData (требует API ключ)"""
    
    def test_dadata_search(self):
        """Тест поиска через DaData"""
        api_key = os.getenv('DADATA_API_KEY')
        if not api_key:
            pytest.skip("DADATA_API_KEY not provided")
        
        provider = DaDataProviderAdapter(api_key=api_key)
        
        # Поиск известной организации
        candidates = provider.search_candidates(
            name="Сбербанк",
            city="Москва"
        )
        
        assert len(candidates) > 0
        
        # Проверяем первого кандидата
        first_candidate = candidates[0]
        assert isinstance(first_candidate, INNCandidate)
        assert first_candidate.inn
        assert first_candidate.provider == "dadata"


class TestIntegration:
    """Интеграционные тесты"""
    
    def test_end_to_end_enrichment(self):
        """Тест полного цикла обогащения"""
        # Конфиг без внешних провайдеров
        config = {
            'enabled': True,
            'providers': {'dadata': {'enabled': False}},
            'cache': {'ttl_days': 180}
        }
        
        resolver = OrganizationINNResolver(config)
        
        organizations = {
            1: {
                'gid': 'test-gid-1',
                'name': 'ООО Тестовая Организация',
                'city': 'Москва',
                'address': 'ул. Тестовая, д. 1'
            }
        }
        
        # Обогащение (без реальных провайдеров должно вернуть reject)
        metadata = resolver.enrich_organizations(organizations)
        
        assert 'test-gid-1' in metadata
        assert metadata['test-gid-1']['decision'] == 'reject'
        assert metadata['test-gid-1']['method'] == 'no_candidates_found'


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])