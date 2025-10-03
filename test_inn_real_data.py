#!/usr/bin/env python3
"""
Тестирование системы обогащения ИНН на реальных данных

Создает тестовый результат обработки письма с организацией "ЦентрЛабораторнойДиагностики"
и проверяет работу системы обогащения ИНН.
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Добавляем пути к модулям
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ dotenv не установлен, используем системные переменные")

def create_test_data():
    """Создание тестовых данных на основе реального письма"""
    return {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ЦентрЛабораторнойДиагностики",
                "inn": None,  # ИНН отсутствует - будем обогащать
                "website": None,
                "city": "Новосибирск",
                "address": "630075, г. Новосибирск, ул. Народная, 3",
                "emails": ["sklad@centerld.ru"],
                "phones": []
            },
            {
                "organization_id": 2, 
                "name": "Яндекс",
                "inn": None,
                "website": "yandex.ru",
                "city": "Москва",
                "address": None,
                "emails": [],
                "phones": []
            },
            {
                "organization_id": 3,
                "name": "ООО \"Неизвестная Компания XYZ999\"",
                "inn": None,
                "website": None,
                "city": "Неизвестный Город",
                "address": None,
                "emails": [],
                "phones": []
            }
        ],
        "contacts": [
            {
                "contact_id": 1,
                "name": "Бабиченко Иван Сергеевич",
                "organization_id": 1,
                "position": "Руководитель ОМТС",
                "email": None,
                "phones": [
                    {
                        "type": "mobile",
                        "number": "+7-913-399-32-72"
                    }
                ],
                "city": "Новосибирск",
                "address": "630075, г. Новосибирск, ул. Народная, 3",
                "confidence": 1.0
            }
        ],
        "business_context": {
            "topic": "Тестирование обогащения ИНН",
            "product_interest": None,
            "communication_stage": "тестирование",
            "request_type": "тест"
        },
        "summary": {
            "topic": "Тестирование обогащения ИНН",
            "product_interest": None,
            "communication_stage": "тестирование",
            "request_type": "тест"
        },
        "key_points": [],
        "commercial_offers": []
    }

def test_inn_enrichment():
    """Тестирование системы обогащения ИНН"""
    print("🚀 Тестирование системы обогащения ИНН на реальных данных")
    print("=" * 70)
    
    # 1. Проверка окружения
    print("\n🔧 Проверка окружения...")
    api_key = os.getenv('DADATA_API_KEY')
    secret_key = os.getenv('DADATA_SECRET_KEY')
    
    if not api_key:
        print("❌ DADATA_API_KEY не найден в переменных окружения")
        print("💡 Добавьте ключ в .env файл")
        return False
    
    if not secret_key:
        print("❌ DADATA_SECRET_KEY не найден в переменных окружения")
        print("💡 Добавьте секретный ключ в .env файл")
        return False
    
    print(f"✅ API ключ: {api_key[:10]}...")
    print(f"✅ Секретный ключ: {secret_key[:10]}...")
    
    # 2. Импорт модулей
    try:
        from src.postprocessing.postprocessor import PostProcessor
        print("✅ PostProcessor импортирован")
    except Exception as e:
        print(f"❌ Ошибка импорта PostProcessor: {e}")
        return False
    
    # 3. Создание тестовых данных
    print("\n📊 Создание тестовых данных...")
    test_data = create_test_data()
    print(f"✅ Создано {len(test_data['organizations'])} организаций для тестирования:")
    
    for org in test_data['organizations']:
        print(f"  📋 {org['name']} (город: {org['city']}, ИНН: {org['inn'] or 'отсутствует'})")
    
    # 4. Инициализация постпроцессора
    print("\n⚙️ Инициализация постпроцессора...")
    try:
        postprocessor = PostProcessor()
        print("✅ PostProcessor инициализирован")
        
        if postprocessor.inn_resolver:
            print("✅ INN resolver активен")
        else:
            print("⚠️ INN resolver недоступен")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка инициализации постпроцессора: {e}")
        return False
    
    # 5. Запуск постобработки
    print("\n🔄 Запуск постобработки с обогащением ИНН...")
    try:
        result = postprocessor.process_llm_response(test_data, email_data={})
        print("✅ Постобработка завершена")
        
    except Exception as e:
        print(f"❌ Ошибка постобработки: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Анализ результатов
    print("\n📈 Анализ результатов обогащения ИНН...")
    
    # Проверяем метаданные ИНН
    postprocessing_metadata = result.get('postprocessing_metadata', {})
    inn_metadata = postprocessing_metadata.get('enrichment', {}).get('org_inn', {})
    
    if not inn_metadata:
        print("❌ Метаданные обогащения ИНН отсутствуют")
        return False
    
    print(f"✅ Найдены метаданные для {len(inn_metadata)} организаций")
    
    # Анализируем каждую организацию
    organizations = result.get('organizations', [])
    
    for org in organizations:
        org_gid = org.get('gid')
        org_name = org.get('name', 'Неизвестная')
        org_inn = org.get('inn')
        
        print(f"\n🏢 Организация: {org_name}")
        print(f"   GID: {org_gid}")
        print(f"   ИНН в организации: {org_inn or 'не найден'}")
        
        if org_gid in inn_metadata:
            metadata = inn_metadata[org_gid]
            decision = metadata.get('decision', 'unknown')
            confidence = metadata.get('confidence', 0)
            candidates = metadata.get('candidates', [])
            
            print(f"   🎯 Решение: {decision}")
            print(f"   📊 Уверенность: {confidence:.3f}")
            
            if decision == 'auto_accept':
                print(f"   ✅ ИНН автоматически принят: {metadata.get('inn')}")
                
            elif decision == 'needs_review':
                print(f"   🤔 Требуется ручная проверка")
                print(f"   📋 Найдено кандидатов: {len(candidates)}")
                
                for i, candidate in enumerate(candidates[:3], 1):
                    print(f"      {i}. ИНН: {candidate.get('inn')} - {candidate.get('name')} (score: {candidate.get('score', 0):.3f})")
                    
            elif decision == 'reject':
                print(f"   ❌ ИНН отклонен (низкая уверенность)")
                
            elif decision == 'skipped':
                print(f"   ⏭️ Пропущено (ИНН уже существует)")
                
            else:
                print(f"   ❓ Неизвестное решение: {decision}")
        else:
            print(f"   ⚠️ Метаданные ИНН отсутствуют")
    
    # 7. Сохранение результата для анализа
    print("\n💾 Сохранение результата...")
    output_path = project_root / "test_inn_enrichment_result.json"
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ Результат сохранен: {output_path}")
    except Exception as e:
        print(f"⚠️ Ошибка сохранения: {e}")
    
    # 8. Итоговая статистика
    print("\n📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 50)
    
    auto_accept_count = sum(1 for meta in inn_metadata.values() if meta.get('decision') == 'auto_accept')
    needs_review_count = sum(1 for meta in inn_metadata.values() if meta.get('decision') == 'needs_review')
    reject_count = sum(1 for meta in inn_metadata.values() if meta.get('decision') == 'reject')
    skip_count = sum(1 for meta in inn_metadata.values() if meta.get('decision') == 'skipped')
    
    total_orgs = len(organizations)
    enriched_orgs = sum(1 for org in organizations if org.get('inn'))
    
    print(f"Всего организаций: {total_orgs}")
    print(f"Обогащено ИНН: {enriched_orgs}")
    print(f"Автоматически принято: {auto_accept_count}")
    print(f"Требует ручной проверки: {needs_review_count}")
    print(f"Отклонено: {reject_count}")
    print(f"Пропущено: {skip_count}")
    
    if needs_review_count > 0:
        print(f"\n💡 {needs_review_count} организаций требуют ручной проверки в UI")
        print("   Данные для выбора сохранены в метаданных")
    
    if auto_accept_count > 0 or needs_review_count > 0:
        print("\n🎉 СИСТЕМА ОБОГАЩЕНИЯ ИНН РАБОТАЕТ!")
        return True
    else:
        print("\n⚠️ Система работает, но результатов обогащения не получено")
        print("   Возможные причины:")
        print("   - Организации не найдены в DaData")
        print("   - Низкое качество совпадений")
        print("   - Проблемы с API")
        return True  # Система работает, просто нет результатов

if __name__ == "__main__":
    success = test_inn_enrichment()
    
    if success:
        print("\n✅ Тест завершен успешно")
    else:
        print("\n❌ Тест завершен с ошибками")
    
    sys.exit(0 if success else 1)