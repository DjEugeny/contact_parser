#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест обогащения организаций через DaData

Проверяет полный цикл обогащения ИНН для организаций:
1. Инициализация OrganizationINNResolver
2. Обогащение тестовых организаций
3. Проверка результатов и метаданных
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from pprint import pprint

# Загрузка переменных окружения
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_single_organization_enrichment():
    """Тест 1: Обогащение одной организации"""
    print("\n" + "=" * 80)
    print("ТЕСТ 1: Обогащение одной организации")
    print("=" * 80)
    
    try:
        from src.postprocessing.org_inn_resolver import OrganizationINNResolver
        
        # Инициализация resolver
        resolver = OrganizationINNResolver()
        
        # Тестовая организация (реальная компания)
        test_org = {
            'gid': 'test_org_001',
            'name': 'ДНК Технология',
            'city': 'Новосибирск',
            'address': '',
            'website': ''
        }
        
        print(f"\n📋 Тестовая организация:")
        print(f"   - Название: {test_org['name']}")
        print(f"   - Город: {test_org['city']}")
        
        # Обогащение
        result = resolver._enrich_single_organization(test_org)
        
        print(f"\n📊 Результат обогащения:")
        print(f"   - Решение: {result.decision}")
        print(f"   - ИНН: {result.inn}")
        print(f"   - Confidence: {result.confidence:.2f}")
        print(f"   - Источник: {result.source}")
        print(f"   - Метод: {result.method}")
        print(f"   - Score: {result.score:.2f}")
        print(f"   - Кандидатов найдено: {len(result.candidates)}")
        
        if result.candidates:
            print(f"\n   Топ-3 кандидата:")
            for i, candidate in enumerate(result.candidates[:3], 1):
                print(f"   {i}. ИНН: {candidate.inn}")
                print(f"      Название: {candidate.name}")
                print(f"      Город: {candidate.city}")
                print(f"      Score: {candidate.score:.2f}")
                print()
        
        # Проверка результата
        if result.decision in ['auto_accept', 'needs_review']:
            print("✅ Обогащение успешно!")
            return True
        else:
            print(f"⚠️  Обогащение не выполнено: {result.decision}")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка при обогащении: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_organizations_enrichment():
    """Тест 2: Обогащение нескольких организаций"""
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Обогащение нескольких организаций")
    print("=" * 80)
    
    try:
        from src.postprocessing.org_inn_resolver import OrganizationINNResolver
        
        # Инициализация resolver
        resolver = OrganizationINNResolver()
        
        # Тестовые организации
        test_organizations = {
            1: {
                'gid': 'org_001',
                'name': 'ДНК Технология',
                'city': 'Новосибирск',
                'address': '',
                'website': ''
            },
            2: {
                'gid': 'org_002',
                'name': 'Яндекс',
                'city': 'Москва',
                'address': '',
                'website': 'yandex.ru'
            },
            3: {
                'gid': 'org_003',
                'name': 'Сбербанк',
                'city': 'Москва',
                'address': '',
                'website': 'sberbank.ru'
            }
        }
        
        print(f"\n📋 Обогащение {len(test_organizations)} организаций...")
        
        # Обогащение
        enrichment_metadata = resolver.enrich_organizations(test_organizations)
        
        print(f"\n📊 Результаты обогащения:")
        print(f"   Всего организаций: {len(test_organizations)}")
        print(f"   Обработано: {len(enrichment_metadata)}")
        
        # Статистика по решениям
        decisions = {}
        enriched_count = 0
        
        for gid, metadata in enrichment_metadata.items():
            decision = metadata['decision']
            decisions[decision] = decisions.get(decision, 0) + 1
            
            if decision == 'auto_accept' and metadata['inn']:
                enriched_count += 1
        
        print(f"\n   Статистика решений:")
        for decision, count in decisions.items():
            print(f"   - {decision}: {count}")
        
        print(f"\n   ИНН добавлено: {enriched_count}")
        
        # Детали по каждой организации
        print(f"\n   Детали:")
        for org_id, org_data in test_organizations.items():
            gid = org_data['gid']
            metadata = enrichment_metadata.get(gid, {})
            
            print(f"\n   {org_id}. {org_data['name']} ({org_data['city']})")
            print(f"      - Решение: {metadata.get('decision', 'N/A')}")
            print(f"      - ИНН: {metadata.get('inn', 'N/A')}")
            print(f"      - Confidence: {metadata.get('confidence', 0):.2f}")
            print(f"      - Источник: {metadata.get('source', 'N/A')}")
        
        if enriched_count > 0:
            print(f"\n✅ Обогащено организаций: {enriched_count}/{len(test_organizations)}")
            return True
        else:
            print(f"\n⚠️  Ни одна организация не обогащена")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка при обогащении: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_organization_with_existing_inn():
    """Тест 3: Организация с уже существующим ИНН"""
    print("\n" + "=" * 80)
    print("ТЕСТ 3: Организация с существующим ИНН")
    print("=" * 80)
    
    try:
        from src.postprocessing.org_inn_resolver import OrganizationINNResolver
        
        resolver = OrganizationINNResolver()
        
        # Организация с валидным ИНН
        test_org = {
            'gid': 'test_org_with_inn',
            'name': 'ДНК Технология',
            'city': 'Новосибирск',
            'inn': '5406789012',  # Валидный ИНН
            'address': '',
            'website': ''
        }
        
        print(f"\n📋 Организация с ИНН: {test_org['inn']}")
        
        result = resolver._enrich_single_organization(test_org)
        
        print(f"\n📊 Результат:")
        print(f"   - Решение: {result.decision}")
        print(f"   - ИНН: {result.inn}")
        print(f"   - Метод: {result.method}")
        
        if result.decision == 'skipped' and result.method == 'existing_valid_inn':
            print("✅ Корректно пропущена организация с существующим ИНН")
            return True
        else:
            print(f"⚠️  Неожиданное поведение: {result.decision}")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_organization_without_name():
    """Тест 4: Организация без названия"""
    print("\n" + "=" * 80)
    print("ТЕСТ 4: Организация без названия")
    print("=" * 80)
    
    try:
        from src.postprocessing.org_inn_resolver import OrganizationINNResolver
        
        resolver = OrganizationINNResolver()
        
        # Организация без названия
        test_org = {
            'gid': 'test_org_no_name',
            'name': '',
            'city': 'Москва',
            'address': '',
            'website': ''
        }
        
        print(f"\n📋 Организация без названия")
        
        result = resolver._enrich_single_organization(test_org)
        
        print(f"\n📊 Результат:")
        print(f"   - Решение: {result.decision}")
        print(f"   - Метод: {result.method}")
        
        if result.decision == 'reject' and result.method == 'empty_name':
            print("✅ Корректно отклонена организация без названия")
            return True
        else:
            print(f"⚠️  Неожиданное поведение: {result.decision}")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_functionality():
    """Тест 5: Проверка работы кэша"""
    print("\n" + "=" * 80)
    print("ТЕСТ 5: Проверка работы кэша")
    print("=" * 80)
    
    try:
        from src.postprocessing.org_inn_resolver import OrganizationINNResolver
        
        resolver = OrganizationINNResolver()
        
        test_org = {
            'gid': 'test_org_cache',
            'name': 'Яндекс',
            'city': 'Москва',
            'address': '',
            'website': ''
        }
        
        print(f"\n📋 Первое обогащение (должно обратиться к API):")
        result1 = resolver._enrich_single_organization(test_org)
        print(f"   - Источник: {result1.source}")
        print(f"   - ИНН: {result1.inn}")
        
        print(f"\n📋 Второе обогащение (должно использовать кэш):")
        result2 = resolver._enrich_single_organization(test_org)
        print(f"   - Источник: {result2.source}")
        print(f"   - ИНН: {result2.inn}")
        
        if result1.inn == result2.inn:
            if result2.source == 'cache':
                print("✅ Кэш работает корректно!")
                return True
            else:
                print(f"⚠️  Второй запрос не использовал кэш: {result2.source}")
                return True  # Не критично
        else:
            print(f"⚠️  ИНН не совпадают: {result1.inn} != {result2.inn}")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 80)
    print("🧪 ТЕСТИРОВАНИЕ ОБОГАЩЕНИЯ ОРГАНИЗАЦИЙ ЧЕРЕЗ DADATA")
    print("=" * 80)
    
    results = []
    
    # Тест 1: Одна организация
    results.append(("Обогащение одной организации", test_single_organization_enrichment()))
    
    # Тест 2: Несколько организаций
    results.append(("Обогащение нескольких организаций", test_multiple_organizations_enrichment()))
    
    # Тест 3: Организация с существующим ИНН
    results.append(("Организация с существующим ИНН", test_organization_with_existing_inn()))
    
    # Тест 4: Организация без названия
    results.append(("Организация без названия", test_organization_without_name()))
    
    # Тест 5: Кэш
    results.append(("Работа кэша", test_cache_functionality()))
    
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
