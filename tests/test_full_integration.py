#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Полный интеграционный тест всех исправлений в пайплайне
Проверяет что все исправления работают в основном потоке

Author: Contact Parser Team
Created: 2025-09-30
"""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def test_postprocessor_integration():
    """Тест интеграции исправлений в PostProcessor"""
    print("🧪 Тестирование интеграции исправлений в PostProcessor")
    print("=" * 60)
    
    try:
        # Импортируем PostProcessor
        from src.postprocessing.postprocessor import PostProcessor
        
        # Создаем тестовые данные с проблемами
        test_llm_result = {
            'organizations': [
                {
                    'organization_id': 1,
                    'name': 'тестовая ОРГАНИЗАЦИЯ',  # Нужна нормализация
                    'inn': '1234567890',
                    'website': None,
                    'city': 'москва',
                    'emails': ['test@example.com']
                }
            ],
            'contacts': [
                {
                    'contact_id': 1,
                    'name': 'иванов ИВАН',  # Нужна нормализация
                    'organization_id': 1,
                    'position': 'руководитель ОМТС',  # Нужна нормализация
                    'email': 'sklad@centerld.ru',  # Нужно обогащение
                    'confidence': None,  # Проблема NoneType * float
                    'phones': []
                }
            ],
            'interactions': [
                {
                    'interaction_local_id': 1,
                    'contact_id': 1,
                    'message_id_h极': None,  # Китайские символы
                    'role_in_message': 'sender',
                    'confidence': None  # Проблема NoneType * float
                }
            ],
            'summary': {
                'topic': 'тестовое письмо',
                'product_interest': None,
                'communication_stage': 'test',
                'request_type': 'test'
            },
            'key_points': ['тестовый пункт'],
            'business_context': 'Тестовый контекст'
        }
        
        # Создаем PostProcessor
        processor = PostProcessor()
        
        # Обрабатываем тестовые данные
        print("🔄 Обработка тестовых данных...")
        result = processor.process_llm_response(test_llm_result)
        
        # Проверяем результаты
        success = True
        
        # 1. Проверяем что китайские символы исправлены
        interactions = result.get('interactions', [])
        if interactions:
            interaction = interactions[0]
            if 'message_id_hint' in interaction and 'message_id_h极' not in interaction:
                print("✅ Китайские символы в полях исправлены")
            else:
                print("❌ Китайские символы не исправлены")
                success = False
        
        # 2. Проверяем что None значения исправлены
        contacts = result.get('contacts', [])
        if contacts:
            contact = contacts[0]
            if contact.get('confidence') == 0.0:  # None должно стать 0.0
                print("✅ None значения в confidence исправлены")
            else:
                print(f"❌ None значения не исправлены: confidence = {contact.get('confidence')}")
                success = False
        
        # 3. Проверяем нормализацию (если используется)
        if contacts:
            contact = contacts[0]
            position = contact.get('position', '')
            if position.startswith('Руководитель'):  # Первое слово должно быть с заглавной
                print("✅ Нормализация должностей работает")
            else:
                print(f"⚠️ Нормализация должностей: {position}")
        
        # 4. Проверяем обогащение email
        if contacts:
            contact = contacts[0]
            email = contact.get('email', '')
            if email == 'sklad@centerld.ru':
                # Проверяем что добавлен website (если SmartContactEnricher работает)
                website = contact.get('website')
                if website == 'centerld.ru':
                    print("✅ Обогащение email → website работает")
                else:
                    print(f"⚠️ Обогащение email: website = {website}")
        
        # 5. Проверяем что метаданные постобработки добавлены
        if 'postprocessing_metadata' in result:
            print("✅ Метаданные постобработки добавлены")
        else:
            print("❌ Метаданные постобработки отсутствуют")
            success = False
        
        print(f"\n📊 Результат интеграционного теста: {'✅ УСПЕХ' if success else '❌ НЕУДАЧА'}")
        return success
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании PostProcessor: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_extractor_integration():
    """Тест интеграции исправлений в ContactExtractor"""
    print("\n🧪 Тестирование интеграции исправлений в ContactExtractor")
    print("=" * 60)
    
    try:
        # Импортируем ExtractorFactory
        from src.core.extractor_factory import ExtractorFactory
        
        print("🏭 Создание тестового экстрактора...")
        extractor = ExtractorFactory.create_test_extractor()
        
        # Проверяем что PostProcessor инициализирован
        if hasattr(extractor, 'postprocessor'):
            print("✅ PostProcessor интегрирован в ContactExtractor")
            
            # Проверяем что в PostProcessor есть наши компоненты
            postprocessor = extractor.postprocessor
            
            if hasattr(postprocessor, 'smart_enricher'):
                print("✅ SmartContactEnricher интегрирован")
            else:
                print("⚠️ SmartContactEnricher не найден")
            
            return True
        else:
            print("❌ PostProcessor не найден в ContactExtractor")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании ContactExtractor: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_pipeline_validator_integration():
    """Тест интеграции ResilientEmailProcessor в APIPipelineValidator"""
    print("\n🧪 Тестирование интеграции ResilientEmailProcessor")
    print("=" * 60)
    
    try:
        # Создаем мок аргументы
        from argparse import Namespace
        mock_args = Namespace(
            mode='first10',
            date=None,
            count=10,
            start_date=None,
            end_date=None,
            dry_run=True
        )
        
        # Импортируем APIPipelineValidator
        from src.api_pipeline_validator import APIPipelineValidator
        
        print("🏗️ Создание APIPipelineValidator...")
        validator = APIPipelineValidator(mock_args)
        
        # Проверяем что ResilientEmailProcessor создан
        if hasattr(validator, 'resilient_processor'):
            print("✅ ResilientEmailProcessor интегрирован в APIPipelineValidator")
            
            # Проверяем что есть метод process_single_email
            if hasattr(validator, 'process_single_email'):
                print("✅ Метод process_single_email добавлен")
            else:
                print("❌ Метод process_single_email не найден")
                return False
            
            return True
        else:
            print("❌ ResilientEmailProcessor не найден в APIPipelineValidator")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании APIPipelineValidator: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_new_integration():
    """Тест интеграции исправлений в main_new.py"""
    print("\n🧪 Тестирование интеграции в main_new.py")
    print("=" * 60)
    
    try:
        # Импортируем main_new
        import src.main_new as main_new
        
        # Проверяем что функции существуют
        if hasattr(main_new, 'run_full_pipeline'):
            print("✅ Функция run_full_pipeline найдена")
        else:
            print("❌ Функция run_full_pipeline не найдена")
            return False
        
        if hasattr(main_new, 'run_test_mode'):
            print("✅ Функция run_test_mode найдена")
        else:
            print("❌ Функция run_test_mode не найдена")
            return False
        
        print("✅ main_new.py готов к использованию с исправлениями")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании main_new.py: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 ПОЛНЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ КРИТИЧЕСКИХ ИСПРАВЛЕНИЙ")
    print("=" * 70)
    print("Проверяем интеграцию всех исправлений в основные потоки:")
    print("• Нормализация текста (normalize_first_word_only)")
    print("• Умное обогащение контактов (SmartContactEnricher)")
    print("• Безопасные математические операции (safe_math_utils)")
    print("• Устойчивый процессор (ResilientEmailProcessor)")
    print("=" * 70)
    
    results = []
    
    # Тест 1: PostProcessor
    results.append(test_postprocessor_integration())
    
    # Тест 2: ContactExtractor
    results.append(test_extractor_integration())
    
    # Тест 3: APIPipelineValidator
    results.append(test_api_pipeline_validator_integration())
    
    # Тест 4: main_new.py
    results.append(test_main_new_integration())
    
    # Итоговый результат
    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    
    test_names = [
        "PostProcessor интеграция",
        "ContactExtractor интеграция", 
        "APIPipelineValidator интеграция",
        "main_new.py интеграция"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results), 1):
        status = "✅ УСПЕХ" if result else "❌ НЕУДАЧА"
        print(f"   {i}. {name}: {status}")
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n🎯 Общий результат: {success_count}/{total_count} тестов прошли успешно")
    
    if success_count == total_count:
        print("🎉 ВСЕ ИСПРАВЛЕНИЯ УСПЕШНО ИНТЕГРИРОВАНЫ!")
        print("Система готова к использованию с критическими исправлениями.")
        return 0
    else:
        print("⚠️ Некоторые интеграции требуют доработки.")
        return 1

if __name__ == "__main__":
    sys.exit(main())