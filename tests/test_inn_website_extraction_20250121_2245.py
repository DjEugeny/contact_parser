#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест извлечения ИНН и сайтов из реальных данных
Создан: 2025-01-21 22:45 (UTC+07)
"""

import json
import os
import sys
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Добавляем корневую папку проекта
sys.path.insert(0, str(project_root))

# Импортируем модули напрямую
from src.llm_extractor import ContactExtractor

def test_inn_website_extraction_real_data():
    """
    Тестирует извлечение ИНН и сайтов на реальных email данных
    """
    print("\n=== Тест извлечения ИНН и сайтов из реальных данных ===")
    print(f"Время запуска: 2025-01-21 22:45 (UTC+07)")
    
    # Путь к тестовым данным
    data_dir = Path("/Users/evgenyzach/contact_parser/data/emails/2025-07-29")
    
    if not data_dir.exists():
        print(f"❌ Папка с данными не найдена: {data_dir}")
        return False
    
    # Получаем список email файлов
    email_files = list(data_dir.glob("email_*.json"))
    if not email_files:
        print(f"❌ Email файлы не найдены в {data_dir}")
        return False
    
    print(f"📧 Найдено {len(email_files)} email файлов")
    
    # Инициализируем экстрактор в тестовом режиме
    try:
        extractor = ContactExtractor(test_mode=True)
        print("✅ ContactExtractor инициализирован в тестовом режиме")
    except Exception as e:
        print(f"❌ Ошибка инициализации ContactExtractor: {e}")
        return False
    
    # Статистика
    stats = {
        'total_processed': 0,
        'inn_found': 0,
        'website_found': 0,
        'both_found': 0,
        'errors': 0
    }
    
    results = []
    
    # Тестируем первые 5 файлов для быстрой проверки
    test_files = email_files[:5]
    
    for email_file in test_files:
        try:
            print(f"\n📄 Обрабатываем: {email_file.name}")
            
            # Загружаем email данные
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            
            # Извлекаем текст для анализа
            text_content = email_data.get('body', '')
            if not text_content:
                print("⚠️ Пустое содержимое email")
                continue
            
            print(f"📝 Длина текста: {len(text_content)} символов")
            
            # Извлекаем контакты
            extracted_data = extractor.extract_all_data(text_content)
            
            if not extracted_data:
                print("⚠️ Данные не извлечены")
                stats['errors'] += 1
                continue
            
            # Анализируем результаты
            contacts = extracted_data.get('contacts', [])
            
            inn_found = False
            website_found = False
            
            for contact in contacts:
                if contact.get('inn'):
                    inn_found = True
                    print(f"🏢 ИНН найден: {contact['inn']}")
                
                if contact.get('website'):
                    website_found = True
                    print(f"🌐 Сайт найден: {contact['website']}")
            
            # Обновляем статистику
            stats['total_processed'] += 1
            if inn_found:
                stats['inn_found'] += 1
            if website_found:
                stats['website_found'] += 1
            if inn_found and website_found:
                stats['both_found'] += 1
            
            # Сохраняем результат
            result = {
                'file': email_file.name,
                'inn_found': inn_found,
                'website_found': website_found,
                'contacts_count': len(contacts),
                'text_length': len(text_content)
            }
            results.append(result)
            
            print(f"✅ Обработано: контактов={len(contacts)}, ИНН={inn_found}, сайт={website_found}")
            
        except Exception as e:
            print(f"❌ Ошибка обработки {email_file.name}: {e}")
            stats['errors'] += 1
    
    # Выводим итоговую статистику
    print("\n" + "="*60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*60)
    print(f"Всего обработано файлов: {stats['total_processed']}")
    print(f"Файлов с ИНН: {stats['inn_found']} ({stats['inn_found']/max(stats['total_processed'], 1)*100:.1f}%)")
    print(f"Файлов с сайтами: {stats['website_found']} ({stats['website_found']/max(stats['total_processed'], 1)*100:.1f}%)")
    print(f"Файлов с ИНН и сайтом: {stats['both_found']} ({stats['both_found']/max(stats['total_processed'], 1)*100:.1f}%)")
    print(f"Ошибок: {stats['errors']}")
    
    # Детальные результаты
    print("\n📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
    for result in results:
        status = "✅" if result['inn_found'] or result['website_found'] else "❌"
        print(f"{status} {result['file']}: контактов={result['contacts_count']}, ИНН={result['inn_found']}, сайт={result['website_found']}")
    
    # Оценка эффективности
    success_rate = (stats['inn_found'] + stats['website_found']) / max(stats['total_processed'] * 2, 1) * 100
    print(f"\n🎯 Общая эффективность извлечения: {success_rate:.1f}%")
    
    if success_rate < 30:
        print("⚠️ НИЗКАЯ ЭФФЕКТИВНОСТЬ - требуется оптимизация промптов")
    elif success_rate < 60:
        print("📈 СРЕДНЯЯ ЭФФЕКТИВНОСТЬ - есть потенциал для улучшения")
    else:
        print("🎉 ВЫСОКАЯ ЭФФЕКТИВНОСТЬ - промпты работают хорошо")
    
    return stats['total_processed'] > 0

if __name__ == "__main__":
    success = test_inn_website_extraction_real_data()
    if success:
        print("\n✅ Тест завершен успешно")
    else:
        print("\n❌ Тест завершен с ошибками")
        sys.exit(1)