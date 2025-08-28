#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностический скрипт для анализа логов OCR процессора
Выявляет конкретные ошибки обработки файлов
"""

import os
import re
from pathlib import Path
from datetime import datetime
import json

def find_log_files():
    """Поиск файлов логов OCR процессора"""
    log_patterns = [
        "/Users/evgenyzach/contact_parser/logs/*.log",
        "/Users/evgenyzach/contact_parser/*.log", 
        "/Users/evgenyzach/contact_parser/data/logs/*.log",
        "/Users/evgenyzach/contact_parser/ocr_processor.log",
        "/Users/evgenyzach/contact_parser/processing.log"
    ]
    
    log_files = []
    for pattern in log_patterns:
        if '*' in pattern:
            log_files.extend(Path(pattern.split('*')[0]).glob('*.log'))
        else:
            if os.path.exists(pattern):
                log_files.append(Path(pattern))
    
    return log_files

def analyze_log_file(log_path, target_dates=None):
    """Анализ конкретного лог файла"""
    print(f"\n📄 АНАЛИЗ ЛОГА: {log_path}")
    
    if not os.path.exists(log_path):
        print(f"   ❌ Файл не существует")
        return
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"   ❌ Ошибка чтения файла: {e}")
        return
    
    lines = content.split('\n')
    print(f"   📊 Всего строк в логе: {len(lines)}")
    
    # Поиск ошибок
    error_patterns = [
        r'ERROR',
        r'CRITICAL', 
        r'Exception',
        r'Traceback',
        r'Failed',
        r'Error processing',
        r'Could not process',
        r'Unable to',
        r'timeout',
        r'connection.*error',
        r'permission.*denied'
    ]
    
    errors_found = []
    for i, line in enumerate(lines):
        for pattern in error_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                errors_found.append((i+1, line.strip()))
                break
    
    print(f"   🚨 Найдено ошибок: {len(errors_found)}")
    
    # Анализ по датам если указаны
    if target_dates:
        print(f"\n   🎯 АНАЛИЗ ПО ЦЕЛЕВЫМ ДАТАМ: {', '.join(target_dates)}")
        for date_str in target_dates:
            date_errors = []
            for line_num, line in errors_found:
                if date_str in line:
                    date_errors.append((line_num, line))
            
            print(f"\n   📅 Дата {date_str}:")
            if date_errors:
                print(f"      🚨 Ошибок: {len(date_errors)}")
                for line_num, line in date_errors[:5]:  # Показываем первые 5
                    print(f"      {line_num:4d}: {line[:100]}...")
            else:
                print(f"      ✅ Ошибок не найдено")
    
    # Показываем последние ошибки
    if errors_found:
        print(f"\n   🔍 ПОСЛЕДНИЕ ОШИБКИ (до 10):")
        for line_num, line in errors_found[-10:]:
            print(f"      {line_num:4d}: {line[:150]}")
    
    # Поиск информации о файлах
    file_processing_patterns = [
        r'Processing file.*?([\w\-\.]+\.(pdf|docx|doc))',
        r'Обработка файла.*?([\w\-\.]+\.(pdf|docx|doc))',
        r'File processed.*?([\w\-\.]+\.(pdf|docx|doc))',
        r'Файл обработан.*?([\w\-\.]+\.(pdf|docx|doc))'
    ]
    
    processed_files = set()
    for line in lines:
        for pattern in file_processing_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    processed_files.add(match[0])
                else:
                    processed_files.add(match)
    
    print(f"\n   📁 Файлов в логе: {len(processed_files)}")
    if processed_files and len(processed_files) <= 20:
        for file in sorted(processed_files):
            print(f"      - {file}")

def check_recent_terminal_output():
    """Проверка недавнего вывода терминала"""
    print(f"\n🖥️  ПРОВЕРКА НЕДАВНЕЙ АКТИВНОСТИ ТЕРМИНАЛА")
    
    # Проверяем историю команд
    history_file = os.path.expanduser("~/.zsh_history")
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Ищем команды связанные с OCR
            ocr_commands = []
            for line in lines[-100:]:  # Последние 100 команд
                if any(keyword in line.lower() for keyword in ['ocr', 'process', 'python', 'contact_parser']):
                    ocr_commands.append(line.strip())
            
            print(f"   📊 Найдено связанных команд: {len(ocr_commands)}")
            if ocr_commands:
                print(f"   🔍 ПОСЛЕДНИЕ КОМАНДЫ:")
                for cmd in ocr_commands[-5:]:
                    print(f"      {cmd}")
        except Exception as e:
            print(f"   ⚠️  Не удалось прочитать историю: {e}")
    else:
        print(f"   ❌ Файл истории не найден")

def analyze_file_structure():
    """Анализ структуры файлов проекта"""
    print(f"\n📁 АНАЛИЗ СТРУКТУРЫ ПРОЕКТА")
    
    base_path = "/Users/evgenyzach/contact_parser"
    
    # Ключевые файлы для проверки
    key_files = [
        "ocr_processor.py",
        "integrated_llm_processor.py", 
        "main.py",
        "run_ocr.py",
        "config.py"
    ]
    
    print(f"   🔍 КЛЮЧЕВЫЕ ФАЙЛЫ:")
    for file in key_files:
        file_path = os.path.join(base_path, file)
        exists = os.path.exists(file_path)
        if exists:
            stat = os.stat(file_path)
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
            print(f"      ✅ {file} ({size} bytes, изменен: {mtime})")
        else:
            print(f"      ❌ {file} - НЕ НАЙДЕН")
    
    # Проверка папок данных
    data_folders = [
        "data/attachments",
        "data/final_results/texts",
        "data/logs",
        "logs"
    ]
    
    print(f"\n   📂 ПАПКИ ДАННЫХ:")
    for folder in data_folders:
        folder_path = os.path.join(base_path, folder)
        exists = os.path.exists(folder_path)
        if exists:
            try:
                items = len(os.listdir(folder_path))
                print(f"      ✅ {folder} ({items} элементов)")
            except:
                print(f"      ⚠️  {folder} (нет доступа)")
        else:
            print(f"      ❌ {folder} - НЕ НАЙДЕНА")

def main():
    """Основная функция диагностики"""
    print("🔍 ДИАГНОСТИКА ЛОГОВ OCR ПРОЦЕССОРА")
    print(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Проблемные даты из сообщения пользователя
    problem_dates = [
        "2025-08-25",
        "2025-07-15", 
        "2025-08-15",
        "2025-08-20",
        "2025-07-11"
    ]
    
    # Поиск и анализ лог файлов
    log_files = find_log_files()
    
    print(f"\n📄 НАЙДЕНО ЛОГ ФАЙЛОВ: {len(log_files)}")
    
    if log_files:
        for log_file in log_files:
            analyze_log_file(log_file, problem_dates)
    else:
        print("   ❌ Лог файлы не найдены")
        print("   💡 Возможные причины:")
        print("      - Логирование отключено")
        print("      - Логи записываются в другое место")
        print("      - Логи очищаются автоматически")
    
    # Дополнительные проверки
    check_recent_terminal_output()
    analyze_file_structure()
    
    print(f"\n{'='*80}")
    print("РЕКОМЕНДАЦИИ ПО ДИАГНОСТИКЕ:")
    print("1. Включите подробное логирование в OCR процессоре")
    print("2. Добавьте логирование ошибок с полными трейсбеками")
    print("3. Логируйте каждый этап обработки файла")
    print("4. Добавьте проверки существования файлов результатов")
    print("5. Реализуйте диагностическую таблицу в реальном времени")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()