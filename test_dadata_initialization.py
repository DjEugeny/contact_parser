#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест инициализации DaData

Проверяет:
1. Загрузку переменных окружения DADATA_API_KEY и DADATA_SECRET_KEY
2. Инициализацию DaData провайдера
3. Базовую работоспособность API
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_env_variables():
    """Тест 1: Проверка загрузки переменных окружения"""
    print("\n" + "=" * 80)
    print("ТЕСТ 1: Проверка переменных окружения")
    print("=" * 80)
    
    # Загрузка .env файла
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Файл .env найден: {env_path}")
    else:
        print(f"⚠️  Файл .env не найден: {env_path}")
    
    # Проверка DADATA_API_KEY
    api_key = os.getenv('DADATA_API_KEY')
    if api_key:
        print(f"✅ DADATA_API_KEY загружен: {api_key[:10]}...{api_key[-10:]}")
    else:
        print("❌ DADATA_API_KEY не найден в переменных окружения")
        return False
    
    # Проверка DADATA_SECRET_KEY
    secret_key = os.getenv('DADATA_SECRET_KEY')
    if secret_key:
        print(f"✅ DADATA_SECRET_KEY загружен: {secret_key[:10]}...{secret_key[-10:]}")
    else:
        print("⚠️  DADATA_SECRET_KEY не найден (опционально)")
    
    return True


def test_config_loading():
    """Тест 2: Проверка загрузки конфигурации из config/settings.py"""
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Проверка конфигурации INN_ENRICHMENT_CONFIG")
    print("=" * 80)
    
    try:
        from config.settings import INN_ENRICHMENT_CONFIG
        
        print("✅ INN_ENRICHMENT_CONFIG успешно импортирован")
        print(f"   - enabled: {INN_ENRICHMENT_CONFIG.get('enabled')}")
        print(f"   - auto_accept_threshold: {INN_ENRICHMENT_CONFIG.get('auto_accept_threshold')}")
        print(f"   - review_threshold: {INN_ENRICHMENT_CONFIG.get('review_threshold')}")
        
        # Проверка конфигурации DaData
        dadata_config = INN_ENRICHMENT_CONFIG.get('providers', {}).get('dadata', {})
        print(f"\n   DaData конфигурация:")
        print(f"   - enabled: {dadata_config.get('enabled')}")
        print(f"   - api_key: {'✅ Установлен' if dadata_config.get('api_key') else '❌ Не установлен'}")
        print(f"   - secret_key: {'✅ Установлен' if dadata_config.get('secret_key') else '⚠️  Не установлен'}")
        print(f"   - timeout_ms: {dadata_config.get('timeout_ms')}")
        
        if not dadata_config.get('api_key'):
            print("\n❌ ПРОБЛЕМА: api_key не загружен из переменных окружения!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при импорте конфигурации: {e}")
        return False


def test_dadata_provider_initialization():
    """Тест 3: Проверка инициализации DaData провайдера"""
    print("\n" + "=" * 80)
    print("ТЕСТ 3: Инициализация DaData провайдера")
    print("=" * 80)
    
    try:
        from src.postprocessing.dadata_provider import DaDataProviderAdapter
        from config.settings import INN_ENRICHMENT_CONFIG
        
        dadata_config = INN_ENRICHMENT_CONFIG.get('providers', {}).get('dadata', {})
        
        if not dadata_config.get('enabled'):
            print("⚠️  DaData отключен в конфигурации")
            return False
        
        api_key = dadata_config.get('api_key')
        secret_key = dadata_config.get('secret_key')
        timeout_ms = dadata_config.get('timeout_ms', 3000)
        
        if not api_key:
            print("❌ API ключ не найден в конфигурации")
            return False
        
        # Инициализация провайдера
        provider = DaDataProviderAdapter(
            api_key=api_key,
            secret_key=secret_key,
            timeout_ms=timeout_ms
        )
        
        print("✅ DaData провайдер успешно инициализирован")
        
        # Получение информации об API
        api_info = provider.get_api_info()
        print(f"\n   Информация об API:")
        print(f"   - provider: {api_info.get('provider')}")
        print(f"   - base_url: {api_info.get('base_url')}")
        print(f"   - timeout_ms: {api_info.get('timeout_ms')}")
        print(f"   - has_secret: {api_info.get('has_secret')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации провайдера: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dadata_api_call():
    """Тест 4: Проверка работы API (простой запрос)"""
    print("\n" + "=" * 80)
    print("ТЕСТ 4: Тестовый запрос к DaData API")
    print("=" * 80)
    
    try:
        from src.postprocessing.dadata_provider import DaDataProviderAdapter
        from config.settings import INN_ENRICHMENT_CONFIG
        
        dadata_config = INN_ENRICHMENT_CONFIG.get('providers', {}).get('dadata', {})
        
        provider = DaDataProviderAdapter(
            api_key=dadata_config.get('api_key'),
            secret_key=dadata_config.get('secret_key'),
            timeout_ms=dadata_config.get('timeout_ms', 3000)
        )
        
        # Тестовый запрос - поиск известной организации
        test_query = "ДНК Технология"
        test_city = "Новосибирск"
        
        print(f"   Поиск: '{test_query}' в городе '{test_city}'")
        
        candidates = provider.search_candidates(
            name=test_query,
            city=test_city
        )
        
        if candidates:
            print(f"✅ API работает! Найдено кандидатов: {len(candidates)}")
            print(f"\n   Первый кандидат:")
            first = candidates[0]
            print(f"   - ИНН: {first.inn}")
            print(f"   - ОГРН: {first.ogrn}")
            print(f"   - Название: {first.name}")
            print(f"   - Город: {first.city}")
            print(f"   - Адрес: {first.address}")
            print(f"   - Провайдер: {first.provider}")
        else:
            print("⚠️  API работает, но кандидаты не найдены")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при вызове API: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_inn_resolver_initialization():
    """Тест 5: Проверка инициализации OrganizationINNResolver"""
    print("\n" + "=" * 80)
    print("ТЕСТ 5: Инициализация OrganizationINNResolver")
    print("=" * 80)
    
    try:
        from src.postprocessing.org_inn_resolver import OrganizationINNResolver
        
        resolver = OrganizationINNResolver()
        
        print("✅ OrganizationINNResolver успешно инициализирован")
        print(f"   - auto_accept_threshold: {resolver.auto_accept_threshold}")
        print(f"   - review_threshold: {resolver.review_threshold}")
        print(f"   - Провайдеры: {list(resolver.providers.keys())}")
        
        if 'dadata' in resolver.providers:
            print("   ✅ DaData провайдер активен в resolver")
        else:
            print("   ⚠️  DaData провайдер НЕ активен в resolver")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации resolver: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 80)
    print("🧪 ТЕСТИРОВАНИЕ ИНИЦИАЛИЗАЦИИ DADATA")
    print("=" * 80)
    
    results = []
    
    # Тест 1: Переменные окружения
    results.append(("Переменные окружения", test_env_variables()))
    
    # Тест 2: Конфигурация
    results.append(("Конфигурация", test_config_loading()))
    
    # Тест 3: Инициализация провайдера
    results.append(("Инициализация провайдера", test_dadata_provider_initialization()))
    
    # Тест 4: API запрос
    results.append(("API запрос", test_dadata_api_call()))
    
    # Тест 5: INN Resolver
    results.append(("INN Resolver", test_inn_resolver_initialization()))
    
    # Итоги
    print("\n" + "=" * 80)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nВсего тестов: {total}")
    print(f"Пройдено: {passed}")
    print(f"Провалено: {total - passed}")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        return 0
    else:
        print("\n⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
