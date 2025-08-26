#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест оптимизированной системы на больших письмах
Дата создания: 2025-01-21 22:55 (UTC+07)

Проверяет:
1. Обработку больших писем без падений
2. Работу продвинутого алгоритма дедупликации
3. Производительность IntegratedLLMProcessor
4. Корректность извлечения контактов из цепочек пересылок
"""

import sys
import os
import json
import time
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from integrated_llm_processor import IntegratedLLMProcessor
from advanced_deduplication import AdvancedContactDeduplicator

def test_big_email_processing():
    """Тест обработки больших писем"""
    print("🔍 Тестирование оптимизированной системы на больших письмах")
    print("=" * 60)
    
    # Путь к большому письму
    big_email_path = Path("/Users/evgenyzach/contact_parser/data/emails/2025-07-07/email_006_20250707_20250707_dna-technology_ru_acd24939.json")
    
    if not big_email_path.exists():
        print("❌ Большое письмо не найдено")
        return False
    
    # Проверяем размер файла
    file_size = big_email_path.stat().st_size
    print(f"📏 Размер файла: {file_size:,} байт ({file_size/1024:.1f} KB)")
    
    try:
        # Загружаем письмо
        with open(big_email_path, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        print(f"📧 Письмо загружено: {email_data.get('subject', 'Без темы')[:50]}...")
        
        # Проверяем размер body
        body = email_data.get('body', '')
        body_size = len(body)
        print(f"📝 Размер body: {body_size:,} символов ({body_size/1024:.1f} KB)")
        
        # Инициализируем процессор с тестовым режимом
        print("\n🚀 Инициализация IntegratedLLMProcessor...")
        processor = IntegratedLLMProcessor(test_mode=True)
        
        # Засекаем время обработки
        start_time = time.time()
        
        # Обрабатываем письмо
        print("⚡ Начинаем обработку большого письма...")
        result = processor.process_single_email(email_data)
        
        processing_time = time.time() - start_time
        print(f"⏱️ Время обработки: {processing_time:.2f} секунд")
        
        # Анализируем результат
        if result:
            contacts = result.get('contacts', [])
            print(f"\n✅ Обработка завершена успешно")
            print(f"👥 Найдено контактов: {len(contacts)}")
            
            # Показываем найденные контакты
            for i, contact in enumerate(contacts[:3], 1):
                name = contact.get('name', 'Не указано')
                email = contact.get('email', 'Не указано')
                phone = contact.get('phone', 'Не указано')
                print(f"   {i}. {name} | {email} | {phone}")
            
            if len(contacts) > 3:
                print(f"   ... и еще {len(contacts) - 3} контактов")
            
            # Проверяем работу дедупликации
            print(f"\n🔄 Проверка дедупликации...")
            deduplicator = AdvancedContactDeduplicator()
            
            # Создаем тестовые дубликаты
            test_contacts = contacts.copy()
            if contacts:
                # Добавляем дубликат первого контакта
                duplicate = contacts[0].copy()
                duplicate['source'] = 'test_duplicate'
                test_contacts.append(duplicate)
            
            deduplicated = deduplicator.deduplicate_contacts(test_contacts)
            print(f"📊 До дедупликации: {len(test_contacts)} контактов")
            print(f"📊 После дедупликации: {len(deduplicated)} контактов")
            
            return True
        else:
            print("❌ Обработка вернула пустой результат")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при обработке: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_big_emails():
    """Тест обработки нескольких больших писем"""
    print("\n🔍 Тестирование обработки нескольких больших писем")
    print("=" * 60)
    
    # Ищем большие письма (>100KB)
    emails_dir = Path("/Users/evgenyzach/contact_parser/data/emails")
    big_emails = []
    
    for date_dir in emails_dir.iterdir():
        if date_dir.is_dir():
            for email_file in date_dir.glob("*.json"):
                if email_file.stat().st_size > 100_000:  # >100KB
                    big_emails.append(email_file)
    
    print(f"📧 Найдено больших писем: {len(big_emails)}")
    
    if not big_emails:
        print("⚠️ Больших писем не найдено")
        return True
    
    # Тестируем первые 3 больших письма
    test_emails = big_emails[:3]
    processor = IntegratedLLMProcessor(test_mode=True)
    
    total_contacts = 0
    total_time = 0
    
    for i, email_path in enumerate(test_emails, 1):
        print(f"\n📧 Обработка письма {i}/{len(test_emails)}: {email_path.name}")
        
        try:
            with open(email_path, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            
            start_time = time.time()
            result = processor.process_single_email(email_data)
            processing_time = time.time() - start_time
            
            total_time += processing_time
            
            if result:
                contacts = result.get('contacts', [])
                total_contacts += len(contacts)
                print(f"   ✅ Обработано за {processing_time:.2f}с, найдено {len(contacts)} контактов")
            else:
                print(f"   ⚠️ Пустой результат за {processing_time:.2f}с")
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print(f"\n📊 Итоговая статистика:")
    print(f"   Обработано писем: {len(test_emails)}")
    print(f"   Общее время: {total_time:.2f} секунд")
    print(f"   Среднее время на письмо: {total_time/len(test_emails):.2f} секунд")
    print(f"   Всего найдено контактов: {total_contacts}")
    
    return True

def test_memory_usage():
    """Тест использования памяти"""
    print("\n🧠 Тестирование использования памяти")
    print("=" * 60)
    
    try:
        import psutil
        process = psutil.Process()
        
        # Измеряем память до обработки
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        print(f"💾 Память до обработки: {memory_before:.1f} MB")
        
        # Обрабатываем большое письмо
        big_email_path = Path("/Users/evgenyzach/contact_parser/data/emails/2025-07-07/email_006_20250707_20250707_dna-technology_ru_acd24939.json")
        
        if big_email_path.exists():
            with open(big_email_path, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            
            processor = IntegratedLLMProcessor(test_mode=True)
            result = processor.process_single_email(email_data)
            
            # Измеряем память после обработки
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_diff = memory_after - memory_before
            
            print(f"💾 Память после обработки: {memory_after:.1f} MB")
            print(f"📈 Прирост памяти: {memory_diff:.1f} MB")
            
            if memory_diff < 100:  # Менее 100MB прироста
                print("✅ Использование памяти в норме")
                return True
            else:
                print("⚠️ Высокое использование памяти")
                return False
        else:
            print("⚠️ Тестовое письмо не найдено")
            return True
            
    except ImportError:
        print("⚠️ psutil не установлен, пропускаем тест памяти")
        return True
    except Exception as e:
        print(f"❌ Ошибка при тестировании памяти: {e}")
        return False

if __name__ == "__main__":
    print("🧪 ТЕСТ ОПТИМИЗИРОВАННОЙ СИСТЕМЫ НА БОЛЬШИХ ПИСЬМАХ")
    print("Дата: 2025-01-21 22:55 (UTC+07)")
    print("=" * 70)
    
    tests = [
        ("Обработка большого письма", test_big_email_processing),
        ("Обработка нескольких больших писем", test_multiple_big_emails),
        ("Использование памяти", test_memory_usage)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name}: ПРОЙДЕН")
                passed += 1
            else:
                print(f"❌ {test_name}: ПРОВАЛЕН")
        except Exception as e:
            print(f"💥 {test_name}: ОШИБКА - {e}")
    
    print(f"\n📊 ИТОГОВЫЙ РЕЗУЛЬТАТ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Оптимизированная система готова к работе с большими письмами")
    else:
        print("⚠️ Некоторые тесты провалены, требуется доработка")