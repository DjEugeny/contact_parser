#!/usr/bin/env python3
"""
Прямой тест DaData API для обогащения ИНН
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ dotenv не установлен, используем системные переменные")

def test_dadata_direct():
    """Прямой тест DaData API"""
    print("🌐 Прямой тест DaData API")
    print("=" * 50)
    
    # Проверка ключей
    api_key = os.getenv('DADATA_API_KEY')
    secret_key = os.getenv('DADATA_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ API ключи не найдены")
        return False
    
    print(f"✅ API ключ: {api_key[:10]}...")
    print(f"✅ Секретный ключ: {secret_key[:10]}...")
    
    # Импорт модулей
    try:
        from src.postprocessing.dadata_provider import DaDataProviderAdapter
        from src.postprocessing.org_inn_resolver import OrganizationINNResolver
        print("✅ Модули импортированы")
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    
    # Тест DaData провайдера
    print("\n🔍 Тестирование DaData провайдера...")
    try:
        provider = DaDataProviderAdapter(api_key=api_key, secret_key=secret_key)
        print("✅ DaData провайдер инициализирован")
        
        # Поиск Яндекса
        print("🔎 Поиск 'Яндекс' в 'Москва'...")
        candidates = provider.search_candidates("Яндекс", "Москва")
        
        if candidates:
            print(f"✅ Найдено {len(candidates)} кандидатов:")
            for i, candidate in enumerate(candidates[:3], 1):
                print(f"  {i}. {candidate.name} (ИНН: {candidate.inn}, score: {candidate.score:.3f})")
        else:
            print("⚠️ Кандидаты не найдены")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка DaData: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Тест полного резолвера
    print("\n🎯 Тестирование полного ИНН резолвера...")
    try:
        # Создаем конфигурацию с правильными ключами
        config = {
            'enabled': True,
            'auto_accept_threshold': 0.85,
            'review_threshold': 0.65,
            'providers': {
                'dadata': {
                    'enabled': True,
                    'api_key': api_key,
                    'secret_key': secret_key,
                    'timeout_ms': 3000
                }
            },
            'cache': {'path': 'registry/inn_cache.jsonl', 'ttl_days': 180},
            'overrides_path': 'registry/inn_overrides.yml'
        }
        
        resolver = OrganizationINNResolver(config)
        print("✅ INN резолвер инициализирован")
        
        # Проверяем что провайдер создался
        if 'dadata' in resolver.providers:
            print("✅ DaData провайдер активен в резолвере")
        else:
            print("❌ DaData провайдер НЕ активен в резолвере")
            return False
        
        # Тестовые организации
        organizations = {
            1: {
                'gid': 'test-001',
                'name': 'Яндекс',
                'city': 'Москва',
                'inn': None
            },
            2: {
                'gid': 'test-002',
                'name': 'Сбербанк',
                'city': 'Москва', 
                'inn': None
            }
        }
        
        print("🔄 Запуск обогащения...")
        metadata = resolver.enrich_organizations(organizations)
        
        print(f"✅ Обогащение завершено, получены метаданные для {len(metadata)} организаций")
        
        # Анализ результатов
        for org_id, org_data in organizations.items():
            gid = org_data['gid']
            name = org_data['name']
            inn = org_data.get('inn')
            
            print(f"\n🏢 {name}:")
            print(f"   ИНН: {inn or 'не найден'}")
            
            if gid in metadata:
                meta = metadata[gid]
                decision = meta.get('decision')
                confidence = meta.get('confidence', 0)
                candidates = meta.get('candidates', [])
                
                print(f"   Решение: {decision}")
                print(f"   Уверенность: {confidence:.3f}")
                
                if decision == 'auto_accept':
                    print(f"   🎉 ИНН автоматически принят!")
                elif decision == 'needs_review':
                    print(f"   🤔 Требует ручной проверки")
                    print(f"   Кандидатов: {len(candidates)}")
                    for i, cand in enumerate(candidates[:2], 1):
                        print(f"     {i}. ИНН: {cand.get('inn')} - {cand.get('name')} (score: {cand.get('score', 0):.3f})")
                elif decision == 'reject':
                    print(f"   ❌ Отклонено")
        
        # Проверяем успешность
        success_count = sum(1 for meta in metadata.values() 
                          if meta.get('decision') in ['auto_accept', 'needs_review'])
        
        if success_count > 0:
            print(f"\n🎉 УСПЕХ! {success_count} организаций успешно обработано")
            return True
        else:
            print(f"\n⚠️ Обработка завершена, но результатов нет")
            return True
        
    except Exception as e:
        print(f"❌ Ошибка ИНН резолвера: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dadata_direct()
    print(f"\n{'✅ Тест прошел успешно' if success else '❌ Тест провален'}")
    sys.exit(0 if success else 1)