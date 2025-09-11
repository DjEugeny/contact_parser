#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полномасштабное тестирование выбранного промпта на всех 35 письмах
Выбранный промпт: unified_contact_extraction_structured.txt

Автор: IMPLEMENT агент
Дата: 09.09.2025
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в путь для импорта модулей
sys.path.append(str(Path(__file__).parent.parent))

from src.prompt_tester import PromptTester
from src.report_generator import ReportGenerator

def get_all_email_files():
    """Получить список всех email файлов из директории 2025-07-29"""
    email_dir = Path("/Users/evgenyzach/contact_parser/data/emails/2025-07-29")
    
    if not email_dir.exists():
        print(f"❌ Директория не найдена: {email_dir}")
        return []
    
    # Получаем все .json файлы, отсортированные по имени
    email_files = sorted([f.name for f in email_dir.glob("email_*.json")])
    
    print(f"📧 Найдено {len(email_files)} email файлов для тестирования")
    return email_files

def test_full_dataset():
    """Основная функция тестирования полного датасета"""
    print("🚀 Запуск полномасштабного тестирования промпта")
    print("=" * 60)
    
    # Настройки
    prompt_file = "unified_contact_extraction_structured.txt"
    email_dir = "/Users/evgenyzach/contact_parser/data/emails/2025-07-29"
    
    # Получаем список всех email файлов
    email_files = get_all_email_files()
    
    if not email_files:
        print("❌ Не найдено email файлов для тестирования")
        return
    
    print(f"📋 Выбранный промпт: {prompt_file}")
    print(f"📁 Директория с письмами: {email_dir}")
    print(f"📊 Количество писем: {len(email_files)}")
    print()
    
    # Инициализация тестера и генератора отчетов
    try:
        tester = PromptTester()
        report_gen = ReportGenerator()
        
        print("✅ Компоненты инициализированы успешно")
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return
    
    # Запуск тестирования
    print("\n🔄 Начинаем тестирование...")
    print("-" * 40)
    
    results = []
    successful_tests = 0
    failed_tests = 0
    
    for i, email_file in enumerate(email_files, 1):
        print(f"[{i:2d}/{len(email_files)}] Тестирование {email_file}...", end=" ")
        
        try:
            # Тестирование одного письма
            result = tester.test_single_email(
                prompt_file=prompt_file,
                email_file=email_file,
                email_dir=email_dir
            )
            
            if result:
                results.append(result)
                successful_tests += 1
                print("✅")
            else:
                failed_tests += 1
                print("❌")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            failed_tests += 1
    
    print("-" * 40)
    print(f"📊 Результаты тестирования:")
    print(f"   ✅ Успешно: {successful_tests}")
    print(f"   ❌ Ошибки: {failed_tests}")
    print(f"   📈 Успешность: {successful_tests/(successful_tests+failed_tests)*100:.1f}%")
    
    if not results:
        print("❌ Нет результатов для генерации отчета")
        return
    
    # Генерация отчетов
    print("\n📝 Генерация отчетов...")
    
    try:
        # Создаем timestamp для уникальности файлов
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Генерируем сводный отчет
        summary_report = report_gen.generate_summary_report(
            results=results,
            prompt_file=prompt_file
        )
        
        # Сохраняем сводный отчет
        summary_filename = f"{timestamp}_full_dataset_testing_summary.md"
        summary_path = f"/Users/evgenyzach/contact_parser/memory-bank/reports/{summary_filename}"
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_report)
        
        print(f"✅ Сводный отчет сохранен: {summary_filename}")
        
        # Генерируем детальные отчеты для каждого письма
        detailed_reports_created = 0
        
        for result in results:
            try:
                detailed_report = report_gen.generate_detailed_email_report(result)
                
                # Создаем имя файла для детального отчета
                email_name = result.get('email_file', 'unknown').replace('.json', '')
                detailed_filename = f"{timestamp}_detailed_{email_name}.md"
                detailed_path = f"/Users/evgenyzach/contact_parser/memory-bank/reports/detailed/{detailed_filename}"
                
                # Создаем директорию если не существует
                os.makedirs(os.path.dirname(detailed_path), exist_ok=True)
                
                with open(detailed_path, 'w', encoding='utf-8') as f:
                    f.write(detailed_report)
                
                detailed_reports_created += 1
                
            except Exception as e:
                print(f"⚠️  Ошибка создания детального отчета для {result.get('email_file', 'unknown')}: {e}")
        
        print(f"✅ Создано {detailed_reports_created} детальных отчетов")
        
    except Exception as e:
        print(f"❌ Ошибка генерации отчетов: {e}")
        return
    
    print("\n🎉 Полномасштабное тестирование завершено!")
    print(f"📁 Отчеты сохранены в: /memory-bank/reports/")
    print(f"📊 Сводный отчет: {summary_filename}")
    print(f"📋 Детальные отчеты: /memory-bank/reports/detailed/")

if __name__ == "__main__":
    test_full_dataset()