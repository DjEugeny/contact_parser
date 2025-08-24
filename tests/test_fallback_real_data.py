#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование fallback-системы с реальными данными
Дата: 2025-07-29, первые 10 писем
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Добавляем src в путь
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from advanced_email_fetcher import AdvancedEmailFetcherV2
from integrated_llm_processor import IntegratedLLMProcessor

def test_fallback_with_real_data():
    """
    Тестирование fallback-системы с реальными данными
    """
    print("🚀 Запуск тестирования fallback-системы с реальными данными")
    print("📅 Дата: 2025-01-15")
    print("📧 Лимит: первые 10 писем")
    print("-" * 60)
    
    try:
        # Настройка логгера
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)
        
        # Инициализация email fetcher
        print("📥 Инициализация email fetcher...")
        email_fetcher = AdvancedEmailFetcherV2(logger)
        
        # Получение писем за указанную дату
        print("🔍 Получение писем за 2025-01-15...")
        from datetime import datetime
        start_date = datetime(2025, 1, 15)
        end_date = datetime(2025, 1, 15, 23, 59, 59)
        
        emails = email_fetcher.fetch_emails_by_date_range(
            start_date=start_date,
            end_date=end_date
        )
        
        # Ограничиваем первыми 10 письмами
        if len(emails) > 10:
            emails = emails[:10]
        
        print(f"📊 Получено писем: {len(emails)}")
        
        if not emails:
            print("⚠️ Письма за указанную дату не найдены")
            return
        
        # Инициализация LLM процессора (без тестового режима)
        print("🤖 Инициализация LLM процессора...")
        llm_processor = IntegratedLLMProcessor(test_mode=False)
        
        # Проверка статуса провайдеров перед началом
        print("\n🔍 Проверка статуса провайдеров:")
        health = llm_processor.contact_extractor.get_provider_health()
        print(f"Общее состояние: {health['overall_health']}")
        for provider_name, status in health['providers'].items():
            print(f"  {provider_name}: {status['status']}")
        
        # Обработка писем
        print("\n🔄 Начинаем обработку писем...")
        processed_count = 0
        contacts_found = 0
        
        for i, email in enumerate(emails, 1):
            print(f"\n📧 Обработка письма {i}/{len(emails)}")
            print(f"От: {email.get('from', 'Неизвестно')}")
            print(f"Тема: {email.get('subject', 'Без темы')[:50]}...")
            
            try:
                # Обработка письма через LLM
                result = llm_processor.process_email(email)
                processed_count += 1
                
                if result and result.get('contacts'):
                    contacts_found += len(result['contacts'])
                    print(f"✅ Найдено контактов: {len(result['contacts'])}")
                    
                    # Показываем первый контакт для примера
                    if result['contacts']:
                        contact = result['contacts'][0]
                        print(f"   Пример: {contact.get('name', 'Без имени')} - {contact.get('phone', 'Без телефона')}")
                else:
                    print("ℹ️ Контакты не найдены")
                    
            except Exception as e:
                print(f"❌ Ошибка при обработке письма: {e}")
                
                # Проверяем, сработал ли fallback
                health_after = llm_processor.contact_extractor.get_provider_health()
                if health_after['overall_health'] != 'healthy':
                    print("🔄 Обнаружено переключение на fallback провайдер")
                    for provider_name, status in health_after['providers'].items():
                        print(f"  {provider_name}: {status['status']}")
        
        # Финальная статистика
        print("\n" + "=" * 60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"📧 Обработано писем: {processed_count}/{len(emails)}")
        print(f"👥 Найдено контактов: {contacts_found}")
        
        # Финальный статус провайдеров
        final_health = llm_processor.contact_extractor.get_provider_health()
        print(f"\n🏥 Финальное состояние системы: {final_health['overall_health']}")
        
        for provider_name, status in final_health['providers'].items():
            print(f"  {provider_name}: {status['status']}")
            if 'error' in status:
                print(f"    Ошибка: {status['error']}")
        
        # Рекомендации
        if final_health.get('recommendations'):
            print("\n💡 Рекомендации:")
            for rec in final_health['recommendations']:
                print(f"  - {rec}")
        
        print("\n✅ Тестирование завершено успешно!")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fallback_with_real_data()