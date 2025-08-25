#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки сценариев обработки писем
без использования LLM запросов

Сценарии:
1. JSON и вложения существуют - пропустить обработку
2. Только JSON существуют - загрузить недостающие вложения
3. Только вложения существуют - загрузить недостающие JSON
4. Ничего не существует - загрузить всё
"""

import os
import sys
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.append(str(Path(__file__).parent / 'src'))

from advanced_email_fetcher import AdvancedEmailFetcherV2, setup_logging

class EmailScenarioTester:
    """Класс для тестирования сценариев обработки писем"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.test_date = "2025-01-21"
        self.test_data_dir = base_dir / "data"
        self.test_emails_dir = self.test_data_dir / "emails" / self.test_date
        self.test_attachments_dir = self.test_data_dir / "attachments" / self.test_date
        
        # Создаем тестовые директории
        self.test_emails_dir.mkdir(parents=True, exist_ok=True)
        self.test_attachments_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройка логирования
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        start_date = datetime.strptime(self.test_date, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)
        self.logger = setup_logging(logs_dir, start_date, end_date)
        
        # Инициализация fetcher
        self.fetcher = AdvancedEmailFetcherV2(self.logger)
        
        # Тестовые данные
        self.test_message_id = "test_message_123@example.com"
        self.test_thread_id = "thread_test_123"
        
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        if self.test_emails_dir.exists():
            shutil.rmtree(self.test_emails_dir)
        if self.test_attachments_dir.exists():
            shutil.rmtree(self.test_attachments_dir)
        print("🧹 Тестовые данные очищены")
        
    def create_test_json(self):
        """Создание тестового JSON файла письма"""
        test_email_data = {
            "message_id": self.test_message_id,
            "thread_id": self.test_thread_id,
            "from": "test@example.com",
            "subject": "Тестовое письмо",
            "date": self.test_date,
            "body": "Это тестовое письмо для проверки сценариев",
            "attachments": [
                {
                    "filename": "test_document.pdf",
                    "size": 1024,
                    "content_type": "application/pdf"
                }
            ],
            "stats": {
                "saved_attachments": 1,
                "excluded_attachments": 0
            }
        }
        
        json_file = self.test_emails_dir / f"{self.test_thread_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_email_data, f, ensure_ascii=False, indent=2)
        
        print(f"📄 Создан тестовый JSON: {json_file}")
        return json_file
        
    def create_test_attachment(self):
        """Создание тестового файла вложения"""
        # Создаем файл с именем, включающим thread_id для корректного поиска
        attachment_file = self.test_attachments_dir / f"{self.test_thread_id}_test_document.pdf"
        with open(attachment_file, 'w') as f:
            f.write("Тестовое содержимое PDF файла")
        
        print(f"📎 Создано тестовое вложение: {attachment_file}")
        return attachment_file
        
    def test_scenario_1_both_exist(self):
        """Сценарий 1: JSON и вложения существуют - должно пропустить"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ СЦЕНАРИЯ 1: JSON и вложения существуют")
        print("="*60)
        
        # Создаем и JSON и вложение
        self.create_test_json()
        self.create_test_attachment()
        
        # Проверяем сценарий
        scenario = self.fetcher.get_processing_scenario(self.test_message_id, self.test_date)
        print(f"🔍 Определенный сценарий: {scenario}")
        
        expected = "skip_all"
        if scenario == expected:
            print(f"✅ УСПЕХ: Сценарий корректно определен как '{expected}'")
            return True
        else:
            print(f"❌ ОШИБКА: Ожидался '{expected}', получен '{scenario}'")
            return False
            
    def test_scenario_2_only_json(self):
        """Сценарий 2: Только JSON существует - должно загрузить вложения"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ СЦЕНАРИЯ 2: Только JSON существует")
        print("="*60)
        
        # Очищаем и создаем только JSON
        self.cleanup_test_data()
        self.test_emails_dir.mkdir(parents=True, exist_ok=True)
        self.test_attachments_dir.mkdir(parents=True, exist_ok=True)
        self.create_test_json()
        
        # Проверяем сценарий
        scenario = self.fetcher.get_processing_scenario(self.test_message_id, self.test_date)
        print(f"🔍 Определенный сценарий: {scenario}")
        
        expected = "download_attachments"
        if scenario == expected:
            print(f"✅ УСПЕХ: Сценарий корректно определен как '{expected}'")
            return True
        else:
            print(f"❌ ОШИБКА: Ожидался '{expected}', получен '{scenario}'")
            return False
            
    def test_scenario_3_only_attachments(self):
        """Сценарий 3: Только вложения существуют - должно загрузить JSON"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ СЦЕНАРИЯ 3: Только вложения существуют")
        print("="*60)
        
        # Очищаем и создаем только вложение
        self.cleanup_test_data()
        self.test_emails_dir.mkdir(parents=True, exist_ok=True)
        self.test_attachments_dir.mkdir(parents=True, exist_ok=True)
        self.create_test_attachment()
        
        # Проверяем сценарий
        scenario = self.fetcher.get_processing_scenario(self.test_message_id, self.test_date)
        print(f"🔍 Определенный сценарий: {scenario}")
        
        expected = "download_json"
        if scenario == expected:
            print(f"✅ УСПЕХ: Сценарий корректно определен как '{expected}'")
            return True
        else:
            print(f"❌ ОШИБКА: Ожидался '{expected}', получен '{scenario}'")
            return False
            
    def test_scenario_4_nothing_exists(self):
        """Сценарий 4: Ничего не существует - должно загрузить всё"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ СЦЕНАРИЯ 4: Ничего не существует")
        print("="*60)
        
        # Полная очистка
        self.cleanup_test_data()
        self.test_emails_dir.mkdir(parents=True, exist_ok=True)
        self.test_attachments_dir.mkdir(parents=True, exist_ok=True)
        
        # Проверяем сценарий
        scenario = self.fetcher.get_processing_scenario(self.test_message_id, self.test_date)
        print(f"🔍 Определенный сценарий: {scenario}")
        
        expected = "download_all"
        if scenario == expected:
            print(f"✅ УСПЕХ: Сценарий корректно определен как '{expected}'")
            return True
        else:
            print(f"❌ ОШИБКА: Ожидался '{expected}', получен '{scenario}'")
            return False
            
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ СЦЕНАРИЕВ ОБРАБОТКИ ПИСЕМ")
        print(f"📅 Тестовая дата: {self.test_date}")
        print(f"📁 Директория данных: {self.test_data_dir}")
        
        results = []
        
        # Запускаем все тесты
        results.append(self.test_scenario_1_both_exist())
        results.append(self.test_scenario_2_only_json())
        results.append(self.test_scenario_3_only_attachments())
        results.append(self.test_scenario_4_nothing_exists())
        
        # Итоговый отчет
        print("\n" + "="*60)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("="*60)
        
        passed = sum(results)
        total = len(results)
        
        print(f"✅ Пройдено тестов: {passed}/{total}")
        print(f"❌ Провалено тестов: {total - passed}/{total}")
        
        if passed == total:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        else:
            print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
            
        # Финальная очистка
        self.cleanup_test_data()
        
        return passed == total

def main():
    """Главная функция"""
    base_dir = Path(__file__).parent
    tester = EmailScenarioTester(base_dir)
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()