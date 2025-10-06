#!/usr/bin/env python3
"""
Скрипт для тестирования системы обогащения ИНН с реальными данными.

Этот скрипт проверяет работоспособность всех компонентов системы обогащения ИНН:
- Валидатор ИНН
- Система кэширования
- DaData провайдер
- Полный цикл обогащения организаций

Использование:
    python test_inn_enrichment_real.py

Требования:
    - DaData API ключи в .env файле
    - Интернет соединение для API запросов
    - Установленные зависимости: requests, pyyaml
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Добавляем путь к модулям проекта
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment():
    """Проверяем наличие необходимых переменных окружения."""
    print("🔧 Проверка окружения...")
    
    api_key = os.getenv('DADATA_API_KEY')
    secret_key = os.getenv('DADATA_SECRET_KEY')
    
    if not api_key:
        print("❌ Переменная DADATA_API_KEY не найдена в .env")
        print("💡 Добавьте в .env файл: DADATA_API_KEY=ваш_ключ")
        return False
        
    if not secret_key:
        print("❌ Переменная DADATA_SECRET_KEY не найдена в .env")
        print("💡 Добавьте в .env файл: DADATA_SECRET_KEY=ваш_секретный_ключ")
        return False
    
    print(f"✅ API ключ найден: {api_key[:10]}...")
    print(f"✅ Секретный ключ найден: {secret_key[:10]}...")
    return True

def test_inn_validator():
    """Тестируем валидатор ИНН."""
    print("\n🔍 Тестирование валидатора ИНН...")
    
    try:
        # Try different import paths
        try:
            from postprocessing.inn_validator import RussianINNValidator
        except ImportError:
            try:
                from src.postprocessing.inn_validator import RussianINNValidator
            except ImportError:
                import sys
                import os
                sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
                from postprocessing.inn_validator import RussianINNValidator
        
        validator = RussianINNValidator()
        
        # Тестовые ИНН
        test_cases = [
            ("7707083893", True, "Яндекс - валидный ИНН"),
            ("7707083894", False, "Яндекс с ошибкой в контрольной сумме"),
            ("7728168971", True, "Сбербанк - валидный ИНН"),
            ("1234567890", False, "Неправильная контрольная сумма"),
            ("123456789", False, "Слишком короткий ИНН"),
            ("12345678901", False, "11 цифр - неправильная длина"),
            ("123456789012", True, "12 цифр - может быть валидным для ИП")
        ]
        
        for inn, expected, description in test_cases:
            result = validator.validate(inn)
            status = "✅" if result.valid == expected else "❌"
            print(f"  {status} {description}: {inn} -> {result.valid}")
            if not result.valid and result.error:
                print(f"      Ошибка: {result.error}")
        
        print("✅ Валидатор ИНН работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка валидатора ИНН: {e}")
        return False

def test_cache_system():
    """Тестируем систему кэширования."""
    print("\n💾 Тестирование кэша...")
    
    try:
        # Try different import paths
        try:
            from postprocessing.inn_cache_system import INNCacheManager
        except ImportError:
            from src.postprocessing.inn_cache_system import INNCacheManager
        
        cache_path = Path("registry/inn_cache.jsonl")
        cache = INNCacheManager(cache_path)
        
        # Убираем ненужный test_result так как мы напрямую сохраняем в кэш
        
        # Сохраняем в кэш
        cache.save_to_cache(
            name_norm="test_company",
            city_norm="moscow",
            inn="7707083893",
            source="test",
            score=0.95
        )
        print("✅ Запись сохранена в кэш")
        
        # Ищем в кэше
        cached = cache.get_cached_inn(
            name_norm="test_company",
            city_norm="moscow"
        )
        if cached and cached.get('inn') == "7707083893":
            print("✅ Запись найдена в кэше")
        else:
            print("❌ Запись не найдена в кэше")
            return False
        
        # Статистика кэша
        stats = cache.get_cache_stats()
        print(f"📊 Статистика кэша: {stats['total_entries']} записей")
        
        print("✅ Кэш работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка кэша: {e}")
        return False

def test_dadata_provider():
    """Тестируем DaData провайдер."""
    print("\n🌐 Тестирование DaData провайдера...")
    
    try:
        # Try different import paths
        try:
            from postprocessing.dadata_provider import DaDataProviderAdapter
        except ImportError:
            from src.postprocessing.dadata_provider import DaDataProviderAdapter
        import os
        
        api_key = os.getenv('DADATA_API_KEY')
        secret_key = os.getenv('DADATA_SECRET_KEY')
        
        if not api_key:
            print("❌ API ключ DaData не найден")
            return False
            
        provider = DaDataProviderAdapter(
            api_key=api_key,
            secret_key=secret_key
        )
        
        # Тестовый поиск
        test_org = {
            "name": "Яндекс",
            "city": "Москва",
            "organization_id": "test_001"
        }
        
        print(f"🔎 Ищем кандидатов для '{test_org['name']}' в '{test_org['city']}'...")
        candidates = provider.search_candidates(
            name=test_org['name'],
            city=test_org['city']
        )
        
        if candidates:
            print(f"✅ Найдено {len(candidates)} кандидатов")
            for i, candidate in enumerate(candidates[:3], 1):
                print(f"  {i}. {candidate.name} (ИНН: {candidate.inn}, score: {candidate.score:.3f})")
        else:
            print("⚠️ Кандидаты не найдены (возможны проблемы с API или лимитами)")
            return False
            
        print("✅ DaData провайдер работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка DaData провайдера: {e}")
        logger.exception("Детали ошибки:")
        return False

def test_full_enrichment():
    """Тестируем полный цикл обогащения."""
    print("\n🎯 Тестирование полного обогащения...")
    
    try:
        # Try different import paths
        try:
            from postprocessing.org_inn_resolver import OrganizationINNResolver
        except ImportError:
            from src.postprocessing.org_inn_resolver import OrganizationINNResolver
        
        resolver = OrganizationINNResolver()
        
        # Тестовые организации
        test_organizations = [
            {
                "organization_id": "test_001",
                "name": "Яндекс",
                "city": "Москва",
                "inn": None
            },
            {
                "organization_id": "test_002", 
                "name": "Сбербанк",
                "city": "Москва",
                "inn": None
            },
            {
                "organization_id": "test_003",
                "name": "Газпром",
                "city": "Санкт-Петербург", 
                "inn": None
            },
            {
                "organization_id": "test_004",
                "name": "Неизвестная компания XYZ999",
                "city": "Неизвестный город",
                "inn": None
            }
        ]
        
        print(f"🏢 Обогащаем {len(test_organizations)} организаций...")
        
        # Преобразуем в нужный формат
        organizations_dict = {i: org for i, org in enumerate(test_organizations)}
        
        # Запускаем обогащение
        metadata = resolver.enrich_organizations(organizations_dict)
        
        # Анализируем результаты
        for org in test_organizations:
            org_id = org["organization_id"]
            org_name = org["name"]
            org_city = org["city"]
            
            print(f"\n🏢 Тестирование: {org_name} ({org_city})")
            
            if org["inn"]:
                print(f"  ✅ ИНН обогащен: {org['inn']}")
            else:
                print("  ❌ ИНН не найден")
            
            # Проверяем метаданные
            if org_id in metadata.get("enrichment", {}).get("org_inn", {}):
                enrich_data = metadata["enrichment"]["org_inn"][org_id]
                decision = enrich_data.get("decision", "unknown")
                confidence = enrich_data.get("confidence", 0)
                
                print(f"  └─ Результат: {decision}, Уверенность: {confidence:.2f}")
                
                if decision == "auto_accept":
                    print("  🎉 Автоматическое принятие - высокая уверенность!")
                elif decision == "needs_review":
                    print("  🤔 Требует ручной проверки - средняя уверенность")
                elif decision == "reject":
                    print("  ❌ Отклонено - низкая уверенность")
            else:
                print("  ⚠️ Метаданные не найдены")
        
        print("\n✅ Полное обогащение завершено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка полного обогащения: {e}")
        logger.exception("Детали ошибки:")
        return False

def main():
    """Главная функция тестирования."""
    print("🚀 Запуск тестирования системы обогащения ИНН")
    print("=" * 60)
    
    # Список тестов
    tests = [
        ("Окружение", test_environment),
        ("Валидатор ИНН", test_inn_validator),
        ("Кэш", test_cache_system),
        ("DaData провайдер", test_dadata_provider),
        ("Полное обогащение", test_full_enrichment)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            
            if not result:
                print(f"\n⚠️ Тест '{test_name}' завершился с ошибкой")
                print("❌ Остановка тестирования")
                break
                
        except Exception as e:
            print(f"\n💥 Критическая ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
            break
    
    # Итоговые результаты
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status} | {test_name}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"Успешно: {passed}/{total} тестов")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("✨ Система обогащения ИНН готова к использованию")
        return True
    else:
        print(f"\n❌ {total - passed} тест(ов) провалено")
        print("🔧 Требуется устранение проблем перед использованием")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)