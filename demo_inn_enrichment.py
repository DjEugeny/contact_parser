#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ Демонстрация системы обогащения ИНН

Простое демо для проверки функциональности системы обогащения ИНН организаций.

Author: Contact Parser Team
Created: 2025-10-03
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.postprocessing.inn_validator import RussianINNValidator
from src.postprocessing.inn_search_normalizer import INNSearchNormalizer
from src.postprocessing.inn_cache_system import INNCacheManager, INNOverrideManager
from pathlib import Path
import tempfile


def demo_inn_validator():
    """Демо валидатора ИНН"""
    print("🔍 Демонстрация валидатора ИНН")
    print("=" * 50)
    
    validator = RussianINNValidator()
    
    test_inns = [
        "7723537840",  # Валидный ИНН Яндекса
        "7701234567",  # Тестовый ИНН
        "1234567890",  # Невалидный ИНН
        "123456789012",  # 12-значный ИНН (ИП)
        "invalid"      # Невалидный формат
    ]
    
    for inn in test_inns:
        result = validator.validate(inn)
        status = "✅" if result.valid else "❌"
        print(f"{status} ИНН: {inn}")
        print(f"   Валиден: {result.valid}")
        print(f"   Тип: {result.inn_type}")
        if result.error:
            print(f"   Ошибка: {result.error}")
        print()


def demo_normalizer():
    """Демо нормализатора"""
    print("🔧 Демонстрация нормализатора")
    print("=" * 50)
    
    normalizer = INNSearchNormalizer()
    
    test_cases = [
        ("ООО «Рога и копыта»", "normalize_organization_name"),
        ("ПАО \"Газпром\"", "normalize_organization_name"),
        ("г. Санкт-Петербург", "normalize_city_name"),
        ("СПб", "normalize_city_name"),
        ("https://www.example.com/page", "extract_domain"),
        ("subdomain.example.ru", "extract_domain")
    ]
    
    for test_input, method_name in test_cases:
        method = getattr(normalizer, method_name)
        result = method(test_input)
        print(f"📝 {method_name}:")
        print(f"   Исходно: {test_input}")
        print(f"   Результат: {result}")
        print()


def demo_cache_system():
    """Демо системы кэша"""
    print("💾 Демонстрация системы кэша")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "demo_cache.jsonl"
        cache_manager = INNCacheManager(cache_path, ttl_days=30)
        
        # Сохранение в кэш
        print("📤 Сохранение в кэш...")
        cache_manager.save_to_cache(
            name_norm="яндекс",
            city_norm="москва",
            inn="7723537840",
            source="demo",
            score=0.95,
            domain="yandex.ru"
        )
        
        # Получение из кэша
        print("📥 Получение из кэша...")
        cached_result = cache_manager.get_cached_inn(
            name_norm="яндекс",
            city_norm="москва",
            domain="yandex.ru"
        )
        
        if cached_result:
            print("✅ Данные найдены в кэше:")
            print(f"   ИНН: {cached_result['inn']}")
            print(f"   Источник: {cached_result['source']}")
            print(f"   Скор: {cached_result['score']}")
        else:
            print("❌ Данные не найдены в кэше")
        
        # Статистика кэша
        stats = cache_manager.get_cache_stats()
        print(f"\n📊 Статистика кэша:")
        print(f"   Всего записей: {stats['total_entries']}")
        print(f"   Валидных записей: {stats['valid_entries']}")


def demo_override_system():
    """Демо системы переопределений"""
    print("⚙️ Демонстрация системы переопределений")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        overrides_path = Path(temp_dir) / "demo_overrides.yml"
        override_manager = INNOverrideManager(overrides_path)
        
        # Добавление переопределения
        print("📝 Добавление переопределения...")
        success = override_manager.add_override(
            org_gid="demo-gid-123",
            inn="7723537840",
            reason="ручная проверка через ЕГРЮЛ",
            confirmed_by="demo_user"
        )
        
        if success:
            print("✅ Переопределение добавлено")
        else:
            print("❌ Ошибка при добавлении")
        
        # Получение переопределения
        print("🔍 Поиск переопределения...")
        override = override_manager.get_override(org_gid="demo-gid-123")
        
        if override:
            print("✅ Переопределение найдено:")
            print(f"   ИНН: {override.inn}")
            print(f"   Причина: {override.reason}")
            print(f"   Подтвердил: {override.confirmed_by}")
        else:
            print("❌ Переопределение не найдено")
        
        # Валидация
        validation = override_manager.validate_overrides()
        print(f"\n🔍 Валидация переопределений:")
        print(f"   Валидно: {validation['valid']}")
        print(f"   Всего записей: {validation['total_overrides']}")
        print(f"   Валидных: {validation['valid_overrides']}")


def main():
    """Главная функция демо"""
    print("🏛️ ДЕМОНСТРАЦИЯ СИСТЕМЫ ОБОГАЩЕНИЯ ИНН")
    print("=" * 60)
    print()
    
    try:
        demo_inn_validator()
        demo_normalizer()
        demo_cache_system()
        demo_override_system()
        
        print("🎉 Все демонстрации завершены успешно!")
        print("\n📋 Краткое описание системы:")
        print("   • Валидатор ИНН с проверкой контрольных сумм")
        print("   • Нормализатор для поиска организаций")
        print("   • Система кэширования с TTL")
        print("   • Система ручных переопределений")
        print("   • Интеграция с DaData API")
        print("   • Двухпороговая логика принятия решений")
        print("   • Полное отслеживание принятых решений")
        
    except Exception as e:
        print(f"❌ Ошибка в демонстрации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()