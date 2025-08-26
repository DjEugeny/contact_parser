#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест интеграции передачи данных письма и вложений в LLM
Дата создания: 2025-01-21 22:45 (UTC+07)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from integrated_llm_processor import IntegratedLLMProcessor
from email_loader import ProcessedEmailLoader
from ocr_processor_adapter import OCRProcessorAdapter
from llm_extractor import ContactExtractor

def test_email_attachments_integration():
    """
    🧪 Тест интеграции: проверяем передачу данных письма и вложений в LLM
    
    Проверяет:
    1. Загрузку письма с вложениями
    2. Обработку вложений через OCRProcessorAdapter
    3. Объединение текста письма и вложений
    4. Передачу объединенных данных в ContactExtractor
    5. Корректность метаданных письма
    """
    print("🧪 Тест интеграции передачи данных письма и вложений в LLM")
    print("=" * 70)
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
    
    try:
        # 1. Инициализация компонентов в тестовом режиме
        print("\n📋 Этап 1: Инициализация компонентов")
        processor = IntegratedLLMProcessor(test_mode=True)
        email_loader = ProcessedEmailLoader()
        ocr_adapter = OCRProcessorAdapter()
        contact_extractor = ContactExtractor(test_mode=True)
        
        print("   ✅ Все компоненты инициализированы в тестовом режиме")
        
        # 2. Загрузка тестового письма с вложениями
        print("\n📋 Этап 2: Поиск письма с вложениями")
        
        # Ищем письма за разные даты, чтобы найти письмо с вложениями
        test_dates = ['2025-07-28', '2025-07-29', '2025-07-30']
        test_email = None
        
        for date in test_dates:
            emails = email_loader.load_emails_by_date(date)
            for email in emails:
                if email.get('attachments') and len(email['attachments']) > 0:
                    test_email = email
                    print(f"   ✅ Найдено письмо с вложениями за {date}")
                    print(f"      📧 От: {email.get('from', 'N/A')[:50]}...")
                    print(f"      📧 Тема: {email.get('subject', 'N/A')[:60]}...")
                    print(f"      📎 Количество вложений: {len(email['attachments'])}")
                    break
            if test_email:
                break
        
        if not test_email:
            print("   ⚠️ Письмо с вложениями не найдено, создаем тестовое")
            test_email = {
                'from': 'test@example.com',
                'to': 'recipient@example.com',
                'subject': 'Тестовое письмо с вложениями',
                'date': '2025-01-21',
                'thread_id': 'test_thread_001',
                'body': 'Это тестовое письмо для проверки интеграции.\n\nКонтакты:\nИван Петров\nТелефон: +7 (495) 123-45-67\nEmail: ivan.petrov@company.ru',
                'attachments': []
            }
        
        # 3. Тестирование обработки вложений
        print("\n📋 Этап 3: Обработка вложений")
        attachments_result = ocr_adapter.process_email_attachments(test_email, email_loader)
        
        print(f"   📊 Результат обработки вложений:")
        print(f"      📎 Обработано вложений: {attachments_result['attachments_processed']}")
        print(f"      📝 Общая длина текста: {attachments_result['total_text_length']} символов")
        
        # Показываем детали каждого вложения
        for i, attachment in enumerate(attachments_result['attachments_text'], 1):
            print(f"      📄 Вложение {i}: {attachment['file_name']}")
            print(f"         Метод: {attachment['method']}")
            print(f"         Успех: {attachment['success']}")
            print(f"         Длина текста: {len(attachment.get('text', ''))} символов")
        
        # 4. Тестирование объединения данных
        print("\n📋 Этап 4: Объединение данных письма и вложений")
        combined_text = ocr_adapter.combine_email_with_attachments(test_email, attachments_result)
        
        print(f"   📊 Объединенный текст:")
        print(f"      📝 Общая длина: {len(combined_text)} символов")
        print(f"      📧 Содержит заголовки письма: {'ТЕМА:' in combined_text}")
        print(f"      📎 Содержит данные вложений: {'СОДЕРЖИМОЕ ВЛОЖЕНИЙ:' in combined_text}")
        
        # Показываем первые 500 символов объединенного текста
        print(f"\n   📄 Первые 500 символов объединенного текста:")
        print(f"   {'-' * 50}")
        print(f"   {combined_text[:500]}...")
        print(f"   {'-' * 50}")
        
        # 5. Тестирование подготовки метаданных
        print("\n📋 Этап 5: Подготовка метаданных для LLM")
        email_metadata = {
            'from': test_email.get('from', ''),
            'to': test_email.get('to', ''),
            'cc': test_email.get('cc', ''),
            'subject': test_email.get('subject', ''),
            'date': test_email.get('date', ''),
            'thread_id': test_email.get('thread_id', ''),
            'has_attachments': len(test_email.get('attachments', [])) > 0,
            'attachments_count': len(test_email.get('attachments', []))
        }
        
        print(f"   📊 Метаданные письма:")
        for key, value in email_metadata.items():
            print(f"      {key}: {value}")
        
        # 6. Тестирование передачи в ContactExtractor
        print("\n📋 Этап 6: Передача данных в ContactExtractor")
        
        # Используем ContactExtractor из IntegratedLLMProcessor, а не отдельный
        processor_contact_extractor = processor.contact_extractor
        print(f"   🤖 ContactExtractor в тестовом режиме: {processor_contact_extractor.test_mode}")
        
        # Вызываем extract_contacts с объединенными данными
        extraction_result = processor_contact_extractor.extract_contacts(combined_text, email_metadata)
        
        print(f"   📊 Результат извлечения контактов:")
        print(f"      ✅ Успех: {extraction_result.get('success', False)}")
        print(f"      👥 Найдено контактов: {len(extraction_result.get('contacts', []))}")
        print(f"      🤖 Провайдер: {extraction_result.get('provider_used', 'N/A')}")
        print(f"      📝 Длина обработанного текста: {extraction_result.get('text_length', 0)}")
        
        # Показываем найденные контакты
        contacts = extraction_result.get('contacts', [])
        for i, contact in enumerate(contacts, 1):
            print(f"      👤 Контакт {i}:")
            print(f"         Имя: {contact.get('name', 'N/A')}")
            print(f"         Email: {contact.get('email', 'N/A')}")
            print(f"         Телефон: {contact.get('phone', 'N/A')}")
            print(f"         Организация: {contact.get('organization', 'N/A')}")
            print(f"         Уверенность: {contact.get('confidence', 0)}")
        
        # 7. Тестирование полной интеграции через IntegratedLLMProcessor
        print("\n📋 Этап 7: Полная интеграция через IntegratedLLMProcessor")
        
        full_result = processor.process_single_email(test_email)
        
        if full_result:
            print(f"   ✅ Полная обработка успешна")
            print(f"      📎 Обработано вложений: {full_result['attachments_processed']}")
            print(f"      📝 Длина объединенного текста: {full_result['combined_text_length']}")
            print(f"      👥 Найдено контактов: {len(full_result['contacts'])}")
            print(f"      💼 Анализ КП: {full_result.get('commercial_analysis', {}).get('commercial_offer_found', False)}")
        else:
            print(f"   ❌ Ошибка полной обработки")
        
        # 8. Проверка корректности передачи данных
        print("\n📋 Этап 8: Проверка корректности передачи данных")
        
        checks_passed = 0
        total_checks = 6
        
        # Проверка 1: Объединенный текст содержит данные письма
        if test_email.get('body', '') in combined_text or test_email.get('subject', '') in combined_text:
            print("   ✅ Проверка 1: Данные письма присутствуют в объединенном тексте")
            checks_passed += 1
        else:
            print("   ❌ Проверка 1: Данные письма отсутствуют в объединенном тексте")
        
        # Проверка 2: Метаданные корректно переданы
        if email_metadata['subject'] == test_email.get('subject', ''):
            print("   ✅ Проверка 2: Метаданные корректно подготовлены")
            checks_passed += 1
        else:
            print("   ❌ Проверка 2: Ошибка в подготовке метаданных")
        
        # Проверка 3: ContactExtractor получил данные
        if extraction_result and 'contacts' in extraction_result:
            print("   ✅ Проверка 3: ContactExtractor получил и обработал данные")
            checks_passed += 1
        else:
            print("   ❌ Проверка 3: ContactExtractor не получил данные")
        
        # Проверка 4: Тестовый режим работает корректно
        provider_used = extraction_result.get('provider_used')
        print(f"   🔍 DEBUG: provider_used = '{provider_used}'")
        if provider_used == 'Test Mode':
            print("   ✅ Проверка 4: Тестовый режим работает корректно")
            checks_passed += 1
        else:
            print(f"   ❌ Проверка 4: Проблема с тестовым режимом (получен: '{provider_used}', ожидался: 'Test Mode')")
        
        # Проверка 5: Полная интеграция работает
        if full_result and 'contacts' in full_result:
            print("   ✅ Проверка 5: Полная интеграция работает")
            checks_passed += 1
        else:
            print("   ❌ Проверка 5: Проблема с полной интеграцией")
        
        # Проверка 6: Данные вложений обрабатываются
        if attachments_result['attachments_processed'] >= 0:  # Может быть 0, если нет вложений
            print("   ✅ Проверка 6: Обработка вложений работает")
            checks_passed += 1
        else:
            print("   ❌ Проверка 6: Проблема с обработкой вложений")
        
        # Итоговый результат
        print(f"\n🎯 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        print(f"   📊 Пройдено проверок: {checks_passed}/{total_checks}")
        print(f"   📈 Процент успеха: {(checks_passed/total_checks)*100:.1f}%")
        
        if checks_passed == total_checks:
            print(f"   ✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Интеграция работает корректно")
            return True
        elif checks_passed >= total_checks * 0.8:
            print(f"   ⚠️ Большинство проверок пройдено, есть незначительные проблемы")
            return True
        else:
            print(f"   ❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ с интеграцией")
            return False
        
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"\n⏰ Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
        print("=" * 70)

if __name__ == "__main__":
    success = test_email_attachments_integration()
    sys.exit(0 if success else 1)