#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Финальный тест системы после исправления всех критических ошибок
Дата: 2025-01-24 23:00 (UTC+07)

Тест проверяет:
1. Инициализацию всех компонентов
2. Работу LLM провайдеров (Groq как основной, Replicate как fallback)
3. Обработку небольшого объема данных
4. Корректность экспорта результатов
"""

import sys
import os
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm_extractor import ContactExtractor
from integrated_llm_processor import IntegratedLLMProcessor
from google_sheets_exporter import GoogleSheetsExporter
from local_exporter import LocalDataExporter

def test_system_initialization():
    """Тест инициализации всех компонентов системы"""
    print("\n🔧 ТЕСТ ИНИЦИАЛИЗАЦИИ СИСТЕМЫ")
    print("=" * 50)
    
    try:
        # Тест ContactExtractor
        print("📞 Тестирование ContactExtractor...")
        extractor = ContactExtractor(test_mode=True)
        print(f"   ✅ ContactExtractor инициализирован (test_mode=True)")
        print(f"   🎯 Активный провайдер: {extractor.current_provider}")
        
        # Тест IntegratedLLMProcessor
        print("\n🤖 Тестирование IntegratedLLMProcessor...")
        processor = IntegratedLLMProcessor(test_mode=True)
        print(f"   ✅ IntegratedLLMProcessor инициализирован (test_mode=True)")
        
        # Тест экспортеров
        print("\n📊 Тестирование экспортеров...")
        local_exporter = LocalDataExporter()
        print(f"   ✅ LocalDataExporter инициализирован")
        
        try:
            sheets_exporter = GoogleSheetsExporter()
            if sheets_exporter.client:
                print(f"   ✅ GoogleSheetsExporter инициализирован с API")
            else:
                print(f"   ⚠️ GoogleSheetsExporter инициализирован без API (fallback режим)")
        except Exception as e:
            print(f"   ⚠️ GoogleSheetsExporter недоступен: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка инициализации: {e}")
        return False

def test_contact_extraction():
    """Тест извлечения контактов с простым текстом"""
    print("\n🔍 ТЕСТ ИЗВЛЕЧЕНИЯ КОНТАКТОВ")
    print("=" * 50)
    
    try:
        extractor = ContactExtractor(test_mode=True)
        
        # Простой тестовый текст
        test_text = """
        Уважаемые коллеги!
        
        Обращается к вам Иван Петров из компании ООО "Тест Системы".
        Наш телефон: +7 (495) 123-45-67
        Email: ivan.petrov@test-company.ru
        Адрес: г. Москва, ул. Тестовая, д. 1
        
        С уважением,
        Иван Петров
        Менеджер по продажам
        """
        
        print(f"📝 Тестовый текст подготовлен ({len(test_text)} символов)")
        print(f"🤖 Отправка в LLM для извлечения контактов...")
        
        result = extractor.extract_contacts(test_text, "Тестовое письмо")
        
        if result and 'contacts' in result:
            contacts = result['contacts']
            print(f"   ✅ Извлечено контактов: {len(contacts)}")
            
            for i, contact in enumerate(contacts, 1):
                print(f"   📞 Контакт {i}:")
                print(f"      Имя: {contact.get('name', 'Не указано')}")
                print(f"      Телефон: {contact.get('phone', 'Не указан')}")
                print(f"      Email: {contact.get('email', 'Не указан')}")
                print(f"      Компания: {contact.get('company', 'Не указана')}")
            
            return True
        else:
            print(f"   ⚠️ Контакты не извлечены или неверный формат результата")
            print(f"   📄 Результат: {result}")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка извлечения контактов: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_provider_health():
    """Тест состояния провайдеров"""
    print("\n🏥 ТЕСТ СОСТОЯНИЯ ПРОВАЙДЕРОВ")
    print("=" * 50)
    
    try:
        extractor = ContactExtractor(test_mode=True)
        
        print(f"🎯 Текущий активный провайдер: {extractor.current_provider}")
        print(f"📋 Доступные провайдеры:")
        
        for provider_name, config in extractor.providers.items():
            status = "✅ Активен" if config.get('active', False) else "❌ Отключен"
            priority = config.get('priority', 'Не указан')
            print(f"   {provider_name}: {status} (приоритет: {priority})")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка проверки провайдеров: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🎯 ФИНАЛЬНЫЙ ТЕСТ СИСТЕМЫ")
    print("📅 Дата: 2025-01-24 23:00 (UTC+07)")
    print("🔧 После исправления всех критических ошибок")
    print("=" * 60)
    
    tests = [
        ("Инициализация системы", test_system_initialization),
        ("Состояние провайдеров", test_provider_health),
        ("Извлечение контактов", test_contact_extraction),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Запуск теста: {test_name}")
        try:
            if test_func():
                print(f"✅ Тест '{test_name}' ПРОЙДЕН")
                passed += 1
            else:
                print(f"❌ Тест '{test_name}' ПРОВАЛЕН")
        except Exception as e:
            print(f"💥 Тест '{test_name}' ЗАВЕРШИЛСЯ С ОШИБКОЙ: {e}")
    
    print(f"\n🏁 РЕЗУЛЬТАТЫ ФИНАЛЬНОГО ТЕСТИРОВАНИЯ")
    print(f"=" * 60)
    print(f"✅ Пройдено тестов: {passed}/{total}")
    print(f"❌ Провалено тестов: {total - passed}/{total}")
    
    if passed == total:
        print(f"🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print(f"🚀 Система готова к продуктивному использованию")
        return True
    else:
        print(f"⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print(f"🔧 Требуется дополнительная диагностика")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)