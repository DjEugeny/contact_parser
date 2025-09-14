#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тестирование API на датасете из 10 писем
Использует архитектуру main_new.py для реального тестирования провайдеров
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import os

# Загрузка переменных окружения из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv не установлен, используем системные переменные окружения")

# Добавление корневой директории проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.extractor_factory import ExtractorFactory
from src.config.config_validator import ConfigValidator

# Список файлов из тестового датасета
TEST_DATASET_FILES = [
    "email_001_20250729_20250729_centerld_ru_d03bd60b.json",
    "email_008_20250729_20250729_mail_ru_8f55fa3f.json",
    "email_022_20250729_20250729_dna-technology_ru_6360137e.json",
    "email_012_20250729_20250729_dna-technology_ru_6fd74dbf.json",
    "email_015_20250729_20250729_dna-technology_ru_41fbdf51.json",
    "email_004_20250729_20250729_dna-technology_ru_6e851453.json",
    "email_028_20250729_20250729_dna-technology_ru_46932b3d.json",
    "email_014_20250729_20250729_millab_ru_62cf1268.json",
    "email_016_20250729_20250729_dna-technology_ru_6360137e.json",
    "email_025_20250729_20250729_dna-technology_ru_4aee22c5.json"
]

class APIDatasetTester:
    """Тестер API на датасете из 10 писем"""
    
    def __init__(self):
        self.emails_dir = project_root / "data" / "emails" / "2025-07-29"
        self.results_dir = project_root / "test_results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Создание экстрактора
        self.extractor = None
        
    def validate_setup(self) -> bool:
        """Валидация настроек перед тестированием"""
        print("🔍 Валидация настроек...")
        
        # Проверка зависимостей
        if not ExtractorFactory.validate_dependencies():
            print("❌ Проблемы с зависимостями!")
            return False
            
        # Проверка конфигурации
        validator = ConfigValidator()
        validation_result = validator.validate_all()
        
        if not validation_result.is_valid:
            print("❌ Проблемы с конфигурацией!")
            validator.print_validation_report(validation_result)
            return False
            
        # Проверка директории с письмами
        if not self.emails_dir.exists():
            print(f"❌ Директория с письмами не найдена: {self.emails_dir}")
            return False
            
        print("✅ Валидация прошла успешно")
        return True
        
    def load_email(self, filename: str) -> Dict[str, Any]:
        """Загрузка письма из JSON файла"""
        email_path = self.emails_dir / filename
        
        if not email_path.exists():
            raise FileNotFoundError(f"Файл не найден: {email_path}")
            
        with open(email_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def extract_text_content(self, email_data: Dict[str, Any]) -> str:
        """Извлечение текстового содержимого письма"""
        content_parts = []
        
        # Основное тело письма
        if 'body' in email_data and email_data['body']:
            content_parts.append(f"Тело письма:\n{email_data['body']}")
            
        # Информация об отправителе
        if 'from' in email_data:
            content_parts.append(f"От: {email_data['from']}")
            
        # Тема письма
        if 'subject' in email_data:
            content_parts.append(f"Тема: {email_data['subject']}")
            
        # Информация о вложениях
        if 'attachments' in email_data and email_data['attachments']:
            attachments_info = "Вложения:\n"
            for att in email_data['attachments']:
                if isinstance(att, dict):
                    name = att.get('filename', 'Неизвестно')
                    size = att.get('size', 'Неизвестно')
                    attachments_info += f"- {name} ({size} байт)\n"
                    
                    # Добавляем содержимое вложения если есть
                    if 'content' in att and att['content']:
                        attachments_info += f"  Содержимое: {att['content'][:500]}...\n"
                        
            content_parts.append(attachments_info)
            
        return "\n\n".join(content_parts)
        
    def test_single_email(self, filename: str) -> Dict[str, Any]:
        """Тестирование одного письма"""
        print(f"\n📧 Тестирование: {filename}")
        
        try:
            # Загрузка письма
            email_data = self.load_email(filename)
            text_content = self.extract_text_content(email_data)
            
            print(f"   📄 Размер текста: {len(text_content)} символов")
            print(f"   📎 Вложений: {len(email_data.get('attachments', []))}")
            
            # Извлечение данных через API
            start_time = datetime.now()
            result = self.extractor.extract_all_data(text_content)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # Подготовка результата
            test_result = {
                "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": processing_time,
                "original_email": {
                    "from": email_data.get('from', ''),
                    "subject": email_data.get('subject', ''),
                    "attachments_count": len(email_data.get('attachments', [])),
                    "char_count": email_data.get('char_count', len(text_content))
                },
                "extraction_result": result,
                "success": True
            }
            
            print(f"   ✅ Успешно обработано за {processing_time:.2f}с")
            return test_result
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return {
                "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "success": False
            }
            
    def run_full_test(self) -> Dict[str, Any]:
        """Запуск полного тестирования датасета"""
        print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ API НА ДАТАСЕТЕ ИЗ 10 ПИСЕМ")
        print("=" * 60)
        
        # Валидация
        if not self.validate_setup():
            return {"error": "Валидация не прошла"}
            
        # Создание экстрактора
        try:
            print("\n🤖 Создание экстрактора...")
            self.extractor = ExtractorFactory.create_extractor()
            print("✅ Экстрактор создан")
        except Exception as e:
            print(f"❌ Ошибка создания экстрактора: {e}")
            return {"error": f"Не удалось создать экстрактор: {e}"}
            
        # Тестирование каждого письма
        results = []
        successful_tests = 0
        
        for i, filename in enumerate(TEST_DATASET_FILES, 1):
            print(f"\n📊 Прогресс: {i}/{len(TEST_DATASET_FILES)}")
            
            result = self.test_single_email(filename)
            results.append(result)
            
            if result.get('success', False):
                successful_tests += 1
                
            # Сохранение промежуточного результата
            result_filename = f"test_result_{filename.replace('.json', '')}.json"
            result_path = self.results_dir / result_filename
            
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
        # Сбор статистики экстрактора
        extractor_stats = self.extractor.get_stats() if self.extractor else {}
        
        # Итоговый отчет
        final_report = {
            "test_summary": {
                "total_emails": len(TEST_DATASET_FILES),
                "successful_tests": successful_tests,
                "failed_tests": len(TEST_DATASET_FILES) - successful_tests,
                "success_rate": (successful_tests / len(TEST_DATASET_FILES)) * 100,
                "timestamp": datetime.now().isoformat()
            },
            "extractor_stats": extractor_stats,
            "individual_results": results
        }
        
        # Сохранение итогового отчета
        report_path = self.results_dir / f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
            
        print(f"\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
        print(f"📊 Успешно: {successful_tests}/{len(TEST_DATASET_FILES)} ({(successful_tests/len(TEST_DATASET_FILES)*100):.1f}%)")
        print(f"📁 Результаты сохранены в: {self.results_dir}")
        print(f"📋 Итоговый отчет: {report_path}")
        
        return final_report


def main():
    """Главная функция"""
    tester = APIDatasetTester()
    result = tester.run_full_test()
    
    if "error" in result:
        print(f"❌ Критическая ошибка: {result['error']}")
        sys.exit(1)
        
    return result


if __name__ == "__main__":
    main()