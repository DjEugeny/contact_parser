#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для генерации отчетов из существующих JSON результатов

Автор: IMPLEMENT агент
Дата: 2025-01-27
"""

import json
import os
from pathlib import Path
from datetime import datetime
import sys

# Добавляем src в путь для импорта
sys.path.append('/Users/evgenyzach/contact_parser/src')
from report_generator import ReportGenerator

def load_test_result(file_path: str) -> dict:
    """Загрузить результат теста из JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки {file_path}: {e}")
        return None

def convert_test_result_to_report_format(test_result: dict) -> dict:
    """Конвертировать формат test_result в формат для ReportGenerator"""
    if not test_result:
        return None
    
    # Создаем структуру, совместимую с ReportGenerator
    report_data = {
        'success': True,
        'email_file': test_result.get('filename', 'Unknown'),
        'timestamp': test_result.get('timestamp', datetime.now().isoformat()),
        'email_metadata': {
            'from': test_result.get('original_email', {}).get('from', 'Не указано'),
            'subject': test_result.get('original_email', {}).get('subject', 'Не указано'),
            'date': test_result.get('timestamp', 'Не указано'),
            'size': f"{test_result.get('original_email', {}).get('char_count', 0)} символов",
            'attachments_count': test_result.get('original_email', {}).get('attachments_count', 0)
        },
        'llm_response': test_result.get('extraction_result', {})
    }
    
    return report_data

def main():
    """Основная функция"""
    test_results_dir = Path('/Users/evgenyzach/contact_parser/test_results')
    reports_dir = Path('/Users/evgenyzach/contact_parser/memory-bank/reports')
    
    # Инициализируем генератор отчетов
    generator = ReportGenerator(str(reports_dir))
    
    # Найдем все файлы результатов тестов
    test_files = list(test_results_dir.glob('test_result_email_*.json'))
    
    if not test_files:
        print("Не найдено файлов результатов тестов")
        return
    
    print(f"Найдено {len(test_files)} файлов результатов")
    
    generated_reports = []
    
    for test_file in sorted(test_files):
        print(f"Обрабатываем: {test_file.name}")
        
        # Загружаем результат теста
        test_result = load_test_result(test_file)
        if not test_result:
            continue
        
        # Конвертируем в формат для генератора отчетов
        report_data = convert_test_result_to_report_format(test_result)
        if not report_data:
            continue
        
        # Генерируем отчет
        try:
            report_content = generator.generate_validation_report(report_data)
            
            # Создаем имя файла отчета
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            email_name = test_file.stem.replace('test_result_', '')
            report_filename = f"{timestamp}_{email_name}_detailed.md"
            
            # Сохраняем отчет
            report_path = generator.save_report(report_content, report_filename)
            generated_reports.append(report_filename)
            
            print(f"  ✅ Создан отчет: {report_filename}")
            
        except Exception as e:
            print(f"  ❌ Ошибка создания отчета для {test_file.name}: {e}")
    
    # Создаем индексный файл
    if generated_reports:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M (UTC+07)')
        index_content = f"""# Индекс детальных отчетов по тестовому датасету

**Дата создания:** {timestamp}
**Источник данных:** test_results/
**Количество отчетов:** {len(generated_reports)}

## Список отчетов

"""
        
        for i, report_name in enumerate(generated_reports, 1):
            email_num = report_name.split('_')[2] if len(report_name.split('_')) > 2 else str(i).zfill(3)
            index_content += f"{i}. [Письмо #{email_num}]({report_name})\n"
        
        index_content += f"\n---\n**Обновлено:** {timestamp}"
        
        index_path = generator.save_report(index_content, "detailed_reports_index.md")
        print(f"\n✅ Создан индексный файл: detailed_reports_index.md")
    
    print(f"\n🎉 Обработка завершена. Создано отчетов: {len(generated_reports)}")

if __name__ == '__main__':
    main()