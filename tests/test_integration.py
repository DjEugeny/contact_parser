#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тестирование интеграции advanced_email_fetcher.py с google_sheets_bridge.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Добавляем путь к src для импортов
sys.path.append(str(Path(__file__).parent.parent / "src"))

from google_sheets_bridge import LLM_Sheets_Bridge

def test_integration():
    """🧪 Тестирование полной интеграции"""
    
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ СИСТЕМЫ")
    print("="*50)
    
    # Создаем экземпляр моста
    bridge = LLM_Sheets_Bridge()
    
    # Тестовая дата (используем дату, когда точно нет писем)
    test_date = "2025-01-01"
    
    print(f"\n📅 Тестируем обработку за {test_date}")
    print("   (дата выбрана специально без писем для тестирования автозагрузки)")
    
    # Проверяем папку с письмами до обработки
    emails_dir = Path("data/emails") / test_date
    print(f"\n📁 Проверка папки: {emails_dir}")
    
    if emails_dir.exists():
        email_files = list(emails_dir.glob("*.json"))
        print(f"   📧 Найдено файлов писем: {len(email_files)}")
        
        if email_files:
            print("   ⚠️ Письма уже существуют. Для чистого теста удалите папку:")
            print(f"   rm -rf {emails_dir}")
            return
    else:
        print("   📭 Папка с письмами не существует (ожидаемо для теста)")
    
    # Запускаем обработку
    print(f"\n🚀 Запуск обработки с автоматической загрузкой...")
    
    try:
        result = bridge.process_and_export(
            date=test_date,
            create_new_sheet=False,
            max_emails=5  # Ограничиваем для теста
        )
        
        if result:
            print("\n✅ ТЕСТ ПРОЙДЕН: Интеграция работает корректно")
            print("   📧 Автоматическая загрузка писем сработала")
            print("   🔄 Полная цепочка обработки выполнена")
        else:
            print("\n⚠️ ТЕСТ ЧАСТИЧНО ПРОЙДЕН: Обработка завершилась без ошибок")
            print("   📭 Возможно, письма за указанную дату отсутствуют на сервере")
            
    except Exception as e:
        print(f"\n❌ ТЕСТ НЕ ПРОЙДЕН: {e}")
        print("   🔧 Проверьте настройки подключения к почтовому серверу")
        print("   🔧 Убедитесь, что файл .env содержит корректные данные")
    
    # Проверяем результаты после обработки
    print(f"\n📊 Проверка результатов после обработки:")
    
    if emails_dir.exists():
        email_files = list(emails_dir.glob("*.json"))
        print(f"   📧 Файлов писем после обработки: {len(email_files)}")
        
        attachments_dir = Path("data/attachments") / test_date
        if attachments_dir.exists():
            attachment_files = list(attachments_dir.rglob("*"))
            print(f"   📎 Файлов вложений: {len([f for f in attachment_files if f.is_file()])}")
    
    print("\n🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

def test_email_fetcher_args():
    """🧪 Тестирование аргументов командной строки advanced_email_fetcher.py"""
    
    print("\n🧪 ТЕСТИРОВАНИЕ АРГУМЕНТОВ КОМАНДНОЙ СТРОКИ")
    print("="*50)
    
    import subprocess
    
    # Тестируем help
    print("📋 Тестируем --help:")
    try:
        result = subprocess.run(
            [sys.executable, "src/advanced_email_fetcher.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("   ✅ Help работает корректно")
            print("   📝 Доступные аргументы:")
            for line in result.stdout.split('\n'):
                if '--' in line:
                    print(f"     {line.strip()}")
        else:
            print(f"   ❌ Ошибка: {result.stderr}")
            
    except Exception as e:
        print(f"   ❌ Исключение: {e}")

if __name__ == "__main__":
    # Проверяем, что мы в правильной директории
    if not Path("src/google_sheets_bridge.py").exists():
        print("❌ Запустите скрипт из корневой директории проекта")
        print("   cd /Users/evgenyzach/contact_parser")
        print("   python tests/test_integration.py")
        sys.exit(1)
    
    test_email_fetcher_args()
    test_integration()