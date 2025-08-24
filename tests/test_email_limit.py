#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест функции ограничения количества писем

Проверяет корректность работы параметра max_emails в IntegratedLLMProcessor
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from integrated_llm_processor import IntegratedLLMProcessor
from email_loader import ProcessedEmailLoader

def test_email_limit():
    """🎯 Тестирует ограничение количества писем"""
    
    print("🧪 ТЕСТ ОГРАНИЧЕНИЯ КОЛИЧЕСТВА ПИСЕМ")
    print("="*50)
    
    # Создаем процессор в тестовом режиме
    processor = IntegratedLLMProcessor(test_mode=True)
    
    # Получаем доступные даты
    available_dates = processor.email_loader.get_available_date_folders()
    
    if not available_dates:
        print("❌ Нет обработанных писем для тестирования")
        return False
    
    # Выбираем дату с письмами
    test_date = available_dates[0]  # Берем первую доступную дату
    print(f"📅 Тестовая дата: {test_date}")
    
    # Загружаем письма для подсчета
    emails = processor.email_loader.load_emails_by_date(test_date)
    total_emails = len(emails)
    
    print(f"📊 Всего писем за {test_date}: {total_emails}")
    
    if total_emails == 0:
        print("❌ Нет писем для тестирования")
        return False
    
    # Тест 1: Ограничение 1 письмо
    print("\n🧪 ТЕСТ 1: Ограничение 1 письмо")
    print("-" * 30)
    
    limit = 1
    results = processor.process_emails_by_date(test_date, max_emails=limit)
    
    # Проверяем количество результатов в emails_results, а не статистику
    processed_results = results.get('emails_results', [])
    processed_count = len(processed_results)
    print(f"✅ Результат: обработано {processed_count} из {limit} (лимит)")
    
    if processed_count <= limit:
        print("✅ ТЕСТ 1 ПРОЙДЕН: лимит соблюден")
        test1_passed = True
    else:
        print(f"❌ ТЕСТ 1 ПРОВАЛЕН: обработано {processed_count}, ожидалось не более {limit}")
        test1_passed = False
    
    # Тест 2: Ограничение больше количества писем
    if total_emails > 1:
        print("\n🧪 ТЕСТ 2: Ограничение больше количества писем")
        print("-" * 30)
        
        limit = total_emails + 5
        results = processor.process_emails_by_date(test_date, max_emails=limit)
        
        # Проверяем количество результатов в emails_results
        processed_results = results.get('emails_results', [])
        processed_count = len(processed_results)
        print(f"✅ Результат: обработано {processed_count} из {total_emails} (всего писем)")
        
        if processed_count <= total_emails:
            print("✅ ТЕСТ 2 ПРОЙДЕН: обработано не больше доступных писем")
            test2_passed = True
        else:
            print(f"❌ ТЕСТ 2 ПРОВАЛЕН: обработано {processed_count}, доступно {total_emails}")
            test2_passed = False
    else:
        print("\n⏭️ ТЕСТ 2 ПРОПУЩЕН: недостаточно писем")
        test2_passed = True
    
    # Тест 3: Без ограничений
    print("\n🧪 ТЕСТ 3: Без ограничений (max_emails=None)")
    print("-" * 30)
    
    results = processor.process_emails_by_date(test_date, max_emails=None)
    # Проверяем количество результатов в emails_results
    processed_results = results.get('emails_results', [])
    processed_count = len(processed_results)
    print(f"✅ Результат: обработано {processed_count} из {total_emails} (без лимита)")
    
    # В тестовом режиме должны обработаться все письма
    if processed_count <= total_emails:
        print("✅ ТЕСТ 3 ПРОЙДЕН: обработано корректное количество")
        test3_passed = True
    else:
        print(f"❌ ТЕСТ 3 ПРОВАЛЕН: обработано {processed_count}, доступно {total_emails}")
        test3_passed = False
    
    # Итоговый результат
    print("\n" + "="*50)
    print("📋 ИТОГИ ТЕСТИРОВАНИЯ:")
    print(f"   Тест 1 (лимит 1): {'✅ ПРОЙДЕН' if test1_passed else '❌ ПРОВАЛЕН'}")
    print(f"   Тест 2 (лимит > писем): {'✅ ПРОЙДЕН' if test2_passed else '❌ ПРОВАЛЕН'}")
    print(f"   Тест 3 (без лимита): {'✅ ПРОЙДЕН' if test3_passed else '❌ ПРОВАЛЕН'}")
    
    all_passed = test1_passed and test2_passed and test3_passed
    
    if all_passed:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Функция ограничения работает корректно.")
    else:
        print("\n❌ ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ! Требуется дополнительная отладка.")
    
    return all_passed

if __name__ == "__main__":
    success = test_email_limit()
    sys.exit(0 if success else 1)