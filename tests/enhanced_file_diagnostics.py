#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенная диагностика проблем с обработкой файлов
Анализирует конкретные проблемы:
1. Неточный подсчет файлов (показывает 10 вместо 8 для 2025-07-29)
2. Потерянные файлы при обработке
3. Проблемы с дубликатами
4. Ошибки обработки без детальной информации
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from src.file_utils import normalize_filename

# Функция normalize_filename импортирована из src.file_utils

def analyze_date_detailed(date_str):
    """Детальный анализ проблем для конкретной даты"""
    print(f"\n{'='*80}")
    print(f"🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ДАТЫ: {date_str}")
    print(f"{'='*80}")
    
    # Пути к папкам
    attachments_dir = f"/Users/evgenyzach/contact_parser/data/attachments/{date_str}"
    results_dir = f"/Users/evgenyzach/contact_parser/data/final_results/texts/{date_str}"
    
    # Анализ файлов во вложениях
    attachment_files = []
    if os.path.exists(attachments_dir):
        for file in os.listdir(attachments_dir):
            if file.lower().endswith(('.pdf', '.docx', '.doc')):
                attachment_files.append(file)
    
    # Анализ файлов в результатах
    result_files = []
    if os.path.exists(results_dir):
        for file in os.listdir(results_dir):
            if file.lower().endswith('.txt'):
                result_files.append(file)
    
    print(f"📁 ФАЙЛЫ ВО ВЛОЖЕНИЯХ: {len(attachment_files)}")
    for i, file in enumerate(attachment_files, 1):
        print(f"   {i:2d}. {file}")
    
    print(f"\n📄 ФАЙЛЫ В РЕЗУЛЬТАТАХ: {len(result_files)}")
    for i, file in enumerate(result_files, 1):
        print(f"   {i:2d}. {file}")
    
    # Анализ нормализованных имен
    print(f"\n🔄 АНАЛИЗ НОРМАЛИЗОВАННЫХ ИМЕН:")
    
    attachment_normalized = {}
    for file in attachment_files:
        normalized = normalize_filename(file)
        attachment_normalized[normalized] = file
        print(f"   📎 {file} → {normalized}")
    
    result_normalized = {}
    for file in result_files:
        # Убираем .txt и нормализуем
        base_name = file.replace('.txt', '')
        normalized = normalize_filename(base_name)
        result_normalized[normalized] = file
        print(f"   📄 {file} → {normalized}")
    
    # Поиск соответствий
    print(f"\n🔗 АНАЛИЗ СООТВЕТСТВИЙ:")
    matched = set()
    unmatched_attachments = []
    unmatched_results = []
    
    for norm_name, att_file in attachment_normalized.items():
        if norm_name in result_normalized:
            matched.add(norm_name)
            print(f"   ✅ {att_file} ↔ {result_normalized[norm_name]}")
        else:
            unmatched_attachments.append(att_file)
            print(f"   ❌ {att_file} → НЕТ РЕЗУЛЬТАТА")
    
    for norm_name, res_file in result_normalized.items():
        if norm_name not in attachment_normalized:
            unmatched_results.append(res_file)
            print(f"   ⚠️  {res_file} → НЕТ ИСХОДНОГО ФАЙЛА")
    
    # Анализ логов для этой даты
    print(f"\n📋 АНАЛИЗ ЛОГОВ:")
    analyze_logs_for_date(date_str)
    
    # Рекомендации
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    if len(unmatched_attachments) > 0:
        print(f"   🔧 Проверить обработку файлов: {', '.join(unmatched_attachments)}")
    if len(unmatched_results) > 0:
        print(f"   🧹 Возможные дубликаты или старые файлы: {', '.join(unmatched_results)}")
    if len(attachment_files) != len(result_files):
        print(f"   ⚖️  Несоответствие количества: {len(attachment_files)} вложений vs {len(result_files)} результатов")
    
    return {
        'date': date_str,
        'attachments_count': len(attachment_files),
        'results_count': len(result_files),
        'matched_count': len(matched),
        'unmatched_attachments': unmatched_attachments,
        'unmatched_results': unmatched_results
    }

def analyze_logs_for_date(date_str):
    """Анализ логов для конкретной даты"""
    logs_dir = "/Users/evgenyzach/contact_parser/data/logs"
    
    # Поиск логов с упоминанием даты
    relevant_logs = []
    
    if os.path.exists(logs_dir):
        for log_file in os.listdir(logs_dir):
            if log_file.endswith('.log'):
                log_path = os.path.join(logs_dir, log_file)
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if date_str in content or date_str.replace('-', '.') in content:
                            relevant_logs.append(log_file)
                except Exception as e:
                    continue
    
    print(f"   📊 Найдено логов с упоминанием {date_str}: {len(relevant_logs)}")
    
    # Анализ последнего релевантного лога
    if relevant_logs:
        latest_log = sorted(relevant_logs)[-1]
        print(f"   📄 Последний лог: {latest_log}")
        
        log_path = os.path.join(logs_dir, latest_log)
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Поиск информации о количестве файлов
            files_found = []
            errors_found = []
            
            for line in lines:
                if date_str in line or date_str.replace('-', '.') in line:
                    if 'файл' in line.lower() or 'обработка' in line.lower():
                        files_found.append(line.strip())
                    if 'ошибка' in line.lower() or 'error' in line.lower() or 'failed' in line.lower():
                        errors_found.append(line.strip())
            
            if files_found:
                print(f"   📁 Информация о файлах ({len(files_found)} записей):")
                for info in files_found[-5:]:  # Последние 5 записей
                    print(f"      {info}")
            
            if errors_found:
                print(f"   ❌ Найдены ошибки ({len(errors_found)} записей):")
                for error in errors_found[-3:]:  # Последние 3 ошибки
                    print(f"      {error}")
            
        except Exception as e:
            print(f"   ⚠️  Ошибка чтения лога: {e}")

def find_file_count_discrepancies():
    """Поиск расхождений в подсчете файлов"""
    print(f"\n{'='*80}")
    print(f"🔍 ПОИСК РАСХОЖДЕНИЙ В ПОДСЧЕТЕ ФАЙЛОВ")
    print(f"{'='*80}")
    
    attachments_base = "/Users/evgenyzach/contact_parser/data/attachments"
    results_base = "/Users/evgenyzach/contact_parser/data/final_results/texts"
    
    discrepancies = []
    
    if os.path.exists(attachments_base):
        for date_folder in os.listdir(attachments_base):
            if re.match(r'\d{4}-\d{2}-\d{2}', date_folder):
                att_path = os.path.join(attachments_base, date_folder)
                res_path = os.path.join(results_base, date_folder)
                
                if os.path.isdir(att_path):
                    att_count = len([f for f in os.listdir(att_path) 
                                   if f.lower().endswith(('.pdf', '.docx', '.doc'))])
                    
                    res_count = 0
                    if os.path.exists(res_path):
                        res_count = len([f for f in os.listdir(res_path) 
                                       if f.lower().endswith('.txt')])
                    
                    if att_count != res_count:
                        discrepancies.append({
                            'date': date_folder,
                            'attachments': att_count,
                            'results': res_count,
                            'difference': att_count - res_count
                        })
    
    # Сортировка по разности
    discrepancies.sort(key=lambda x: abs(x['difference']), reverse=True)
    
    print(f"📊 Найдено расхождений: {len(discrepancies)}")
    print(f"\n{'Дата':<12} {'Вложения':<10} {'Результаты':<11} {'Разность':<9} {'Статус':<15}")
    print(f"{'-'*60}")
    
    for disc in discrepancies[:15]:  # Топ 15 расхождений
        status = "❌ Недообработка" if disc['difference'] > 0 else "⚠️ Лишние файлы"
        print(f"{disc['date']:<12} {disc['attachments']:<10} {disc['results']:<11} {disc['difference']:>+8} {status}")
    
    return discrepancies

def main():
    """Основная функция диагностики"""
    print("🔧 УЛУЧШЕННАЯ ДИАГНОСТИКА ПРОБЛЕМ С ОБРАБОТКОЙ ФАЙЛОВ")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Общий анализ расхождений
    discrepancies = find_file_count_discrepancies()
    
    # 2. Детальный анализ проблемных дат
    problem_dates = ['2025-07-29', '2025-08-25', '2025-07-15', '2025-08-15', '2025-08-20', '2025-07-11']
    
    results = []
    for date in problem_dates:
        result = analyze_date_detailed(date)
        results.append(result)
    
    # 3. Сводка
    print(f"\n{'='*80}")
    print(f"📋 СВОДКА АНАЛИЗА")
    print(f"{'='*80}")
    
    total_unmatched_att = sum(len(r['unmatched_attachments']) for r in results)
    total_unmatched_res = sum(len(r['unmatched_results']) for r in results)
    
    print(f"📊 Всего проанализировано дат: {len(results)}")
    print(f"📎 Необработанных вложений: {total_unmatched_att}")
    print(f"📄 Лишних результатов: {total_unmatched_res}")
    print(f"🔍 Всего расхождений в системе: {len(discrepancies)}")
    
    print(f"\n💡 ОСНОВНЫЕ РЕКОМЕНДАЦИИ:")
    print(f"1. Улучшить логирование процесса обработки файлов")
    print(f"2. Добавить проверку существования результатов после обработки")
    print(f"3. Реализовать механизм повторной обработки неудачных файлов")
    print(f"4. Добавить детальную диагностику в реальном времени")
    print(f"5. Проверить логику нормализации имен файлов")

if __name__ == "__main__":
    main()