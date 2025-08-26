#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование обработки больших писем с провайдером Replicate
Дата создания: 2025-01-27 02:30 (UTC+07)
"""

import os
import sys
import json
import asyncio
from datetime import datetime

# Добавляем путь к модулям проекта
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from integrated_llm_processor import IntegratedLLMProcessor

def get_email_size_info(email_path):
    """Получить информацию о размере письма"""
    try:
        with open(email_path, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        body_size = len(email_data.get('body', ''))
        total_size = len(json.dumps(email_data, ensure_ascii=False))
        
        return {
            'path': email_path,
            'body_size': body_size,
            'total_size': total_size,
            'subject': email_data.get('subject', 'Без темы')[:50]
        }
    except Exception as e:
        return {'error': str(e), 'path': email_path}

def test_large_email_processing():
    """Тестирование обработки больших писем"""
    print(f"🧪 Тестирование обработки больших писем с Replicate")
    print(f"⏰ Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
    print("=" * 80)
    
    # Список больших писем для тестирования
    test_emails = [
        "data/emails/2025-08-01/email_009_20250801_20250801_dna-technology_ru_85384e9a.json",  # ~80KB
        "data/emails/2025-07-25/email_001_20250725_20250725_dna-technology_ru_ae879b4c.json",  # ~105KB
        "data/emails/2025-07-28/email_006_20250728_20250728_dna-technology_ru_da7eb20e.json",  # ~158KB
        "data/emails/2025-08-12/email_001_20250812_20250812_mail_ru_109d9715.json",           # ~274KB
        "data/emails/2025-07-07/email_006_20250707_20250707_dna-technology_ru_acd24939.json"   # ~506KB
    ]
    
    # Проверяем размеры писем
    print("📊 Анализ размеров тестовых писем:")
    for email_path in test_emails:
        if os.path.exists(email_path):
            info = get_email_size_info(email_path)
            if 'error' not in info:
                print(f"  📧 {os.path.basename(email_path)}")
                print(f"     Тема: {info['subject']}")
                print(f"     Размер тела: {info['body_size']:,} символов")
                print(f"     Общий размер: {info['total_size']:,} символов")
            else:
                print(f"  ❌ Ошибка чтения {email_path}: {info['error']}")
        else:
            print(f"  ❌ Файл не найден: {email_path}")
    
    print("\n" + "=" * 80)
    
    # Инициализируем процессор с тестовым режимом
    processor = IntegratedLLMProcessor(test_mode=True)
    
    results = []
    
    for i, email_path in enumerate(test_emails, 1):
        if not os.path.exists(email_path):
            print(f"⏭️  Пропускаем {email_path} - файл не найден")
            continue
            
        print(f"\n🔄 Тест {i}/{len(test_emails)}: {os.path.basename(email_path)}")
        
        try:
            # Загружаем письмо
            with open(email_path, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            
            info = get_email_size_info(email_path)
            print(f"   📏 Размер тела письма: {info['body_size']:,} символов")
            
            # Засекаем время обработки
            start_time = datetime.now()
            
            # Обрабатываем письмо
            result = processor.process_single_email(email_data)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            print(f"   ⏱️  Время обработки: {processing_time:.2f} секунд")
            
            if result and 'contacts' in result:
                contacts_count = len(result['contacts'])
                print(f"   ✅ Успешно извлечено контактов: {contacts_count}")
                
                # Показываем первые несколько контактов
                if contacts_count > 0:
                    print(f"   📋 Примеры контактов:")
                    for j, contact in enumerate(result['contacts'][:3], 1):
                        name = contact.get('name', 'Без имени')
                        phone = contact.get('phone', 'Нет телефона')
                        email = contact.get('email', 'Нет email')
                        print(f"      {j}. {name} | {phone} | {email}")
                    
                    if contacts_count > 3:
                        print(f"      ... и еще {contacts_count - 3} контактов")
            else:
                print(f"   ⚠️  Результат обработки пустой или некорректный")
            
            results.append({
                'email_path': email_path,
                'body_size': info['body_size'],
                'processing_time': processing_time,
                'contacts_count': len(result.get('contacts', [])) if result else 0,
                'success': result is not None and 'contacts' in result
            })
            
        except Exception as e:
            print(f"   ❌ Ошибка обработки: {str(e)}")
            results.append({
                'email_path': email_path,
                'body_size': info.get('body_size', 0),
                'processing_time': 0,
                'contacts_count': 0,
                'success': False,
                'error': str(e)
            })
    
    # Выводим итоговую статистику
    print("\n" + "=" * 80)
    print("📊 ИТОГОВАЯ СТАТИСТИКА ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    successful_tests = [r for r in results if r['success']]
    failed_tests = [r for r in results if not r['success']]
    
    print(f"✅ Успешных тестов: {len(successful_tests)}/{len(results)}")
    print(f"❌ Неудачных тестов: {len(failed_tests)}/{len(results)}")
    
    if successful_tests:
        avg_time = sum(r['processing_time'] for r in successful_tests) / len(successful_tests)
        total_contacts = sum(r['contacts_count'] for r in successful_tests)
        print(f"⏱️  Среднее время обработки: {avg_time:.2f} секунд")
        print(f"📋 Всего извлечено контактов: {total_contacts}")
        
        print("\n📈 Детальная статистика по размерам:")
        for result in successful_tests:
            filename = os.path.basename(result['email_path'])
            print(f"  {filename}:")
            print(f"    Размер: {result['body_size']:,} символов")
            print(f"    Время: {result['processing_time']:.2f}с")
            print(f"    Контакты: {result['contacts_count']}")
    
    if failed_tests:
        print("\n❌ Ошибки обработки:")
        for result in failed_tests:
            filename = os.path.basename(result['email_path'])
            error = result.get('error', 'Неизвестная ошибка')
            print(f"  {filename}: {error}")
    
    print(f"\n⏰ Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
    return results

if __name__ == "__main__":
    # Запускаем тестирование
    results = test_large_email_processing()
    
    # Сохраняем результаты в файл
    results_file = f"test_results_large_emails_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n💾 Результаты сохранены в файл: {results_file}")