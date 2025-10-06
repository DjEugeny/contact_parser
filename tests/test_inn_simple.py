#!/usr/bin/env python3
"""
Простой тест системы обогащения ИНН

Быстрая проверка работоспособности основных компонентов.
"""

import os
import sys
from pathlib import Path

# Настройка путей
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv не установлен, проверяем переменные окружения напрямую")

def test_basic_functionality():
    """Базовая проверка функциональности"""
    print("🚀 Простой тест системы обогащения ИНН")
    print("=" * 50)
    
    # 1. Проверка окружения
    print("\n🔧 Проверка окружения...")
    api_key = os.getenv('DADATA_API_KEY')
    secret_key = os.getenv('DADATA_SECRET_KEY')
    
    if not api_key:
        print("❌ DADATA_API_KEY не найден в переменных окружения")
        return False
    if not secret_key:
        print("❌ DADATA_SECRET_KEY не найден в переменных окружения")  
        return False
    
    print(f"✅ API ключ: {api_key[:10]}...")
    print(f"✅ Секретный ключ: {secret_key[:10]}...")
    
    # 2. Проверка импортов
    print("\n📦 Проверка модулей...")
    try:
        from src.postprocessing.inn_validator import RussianINNValidator
        print("✅ inn_validator импортирован")
    except Exception as e:
        print(f"❌ Ошибка импорта inn_validator: {e}")
        return False
    
    try:
        from src.postprocessing.inn_cache_system import INNCacheManager
        print("✅ inn_cache_system импортирован")
    except Exception as e:
        print(f"❌ Ошибка импорта inn_cache_system: {e}")
        return False
    
    try:
        from src.postprocessing.dadata_provider import DaDataProviderAdapter
        print("✅ dadata_provider импортирован")
    except Exception as e:
        print(f"❌ Ошибка импорта dadata_provider: {e}")
        return False
    
    # 3. Простой тест валидатора
    print("\n🔍 Тест валидатора ИНН...")
    try:
        validator = RussianINNValidator()
        
        # Тест валидного ИНН
        result = validator.validate("7707083893")  # Яндекс
        if result.valid:
            print("✅ Валидный ИНН прошел проверку")
        else:
            print("❌ Валидный ИНН не прошел проверку")
            return False
            
        # Тест невалидного ИНН  
        result = validator.validate("1234567890")
        if not result.valid:
            print("✅ Невалидный ИНН отклонен")
        else:
            print("❌ Невалидный ИНН прошел проверку")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка валидатора: {e}")
        return False
    
    # 4. Простой тест кэша
    print("\n💾 Тест кэша...")
    try:
        cache_path = Path("registry/test_cache.jsonl")
        cache_manager = INNCacheManager(cache_path, ttl_days=1)
        
        # Сохранение тестовой записи
        success = cache_manager.save_to_cache(
            name_norm="test_org",
            city_norm="moscow", 
            inn="7707083893",
            source="test",
            score=0.95
        )
        
        if success:
            print("✅ Запись в кэш успешна")
        else:
            print("❌ Ошибка записи в кэш")
            return False
            
        # Поиск записи
        cached = cache_manager.get_cached_inn("test_org", "moscow")
        if cached and cached.get('inn') == "7707083893":
            print("✅ Поиск в кэше работает")
        else:
            print("❌ Поиск в кэше не работает")
            return False
            
        # Очистка тестового файла
        if cache_path.exists():
            cache_path.unlink()
            
    except Exception as e:
        print(f"❌ Ошибка кэша: {e}")
        return False
    
    # 5. Простой тест DaData (без реальных запросов)
    print("\n🌐 Тест DaData провайдера...")
    try:
        provider = DaDataProviderAdapter(api_key=api_key, secret_key=secret_key)
        print("✅ DaData провайдер инициализирован")
        
        # Проверяем что API info работает
        info = provider.get_api_info()
        if info.get('provider') == 'dadata':
            print("✅ API информация получена")
        else:
            print("❌ Ошибка API информации")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка DaData провайдера: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 ВСЕ БАЗОВЫЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    print("✨ Система обогащения ИНН готова к использованию")
    print("\n💡 Для полного тестирования с реальными API запросами:")
    print("   python3 test_inn_enrichment_real.py")
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)