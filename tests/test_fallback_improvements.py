#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест улучшений fallback обработки
Проверяет что fallback извлекает базовую информацию и отчеты показывают проблемы

Author: Contact Parser Team
Created: 2025-09-30
"""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def test_fallback_improvements():
    """Тест улучшений fallback обработки"""
    print("🧪 Тестирование улучшений fallback обработки")
    print("=" * 70)
    
    try:
        from src.postprocessing.resilient_processor import ResilientEmailProcessor
        
        # Создаем временную директорию для тестов
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Создаем тестовое письмо
            test_email = {
                "from": "test@example.com",
                "subject": "Тестовое письмо для fallback",
                "body": "Это тестовое письмо для проверки fallback обработки. Содержит важную информацию о продукте.",
                "date": "2025-09-30T14:00:00+07:00"
            }
            
            email_file = temp_path / "test_email.json"
            with open(email_file, 'w', encoding='utf-8') as f:
                json.dump(test_email, f, ensure_ascii=False, indent=2)
            
            # Создаем мок процессор который всегда падает
            class FailingProcessor:
                def process_single_email(self, email_file, simplified=False):
                    raise Exception("Тестовая ошибка для проверки fallback")
            
            # Создаем ResilientEmailProcessor с мок процессором
            resilient_processor = ResilientEmailProcessor(FailingProcessor())
            
            # Тестируем извлечение базовой информации
            print("📧 Тестируем извлечение базовой информации...")
            basic_info = resilient_processor._extract_basic_email_info(str(email_file))
            
            print(f"✅ Извлечена информация:")
            print(f"   📋 Тема: {basic_info.get('subject', 'Не найдена')}")
            print(f"   🏢 Организаций: {len(basic_info.get('organizations', []))}") 
            print(f"   👤 Контактов: {len(basic_info.get('contacts', []))}")
            print(f"   🔗 Взаимодействий: {len(basic_info.get('interactions', []))}")
            print(f"   📝 Ключевых моментов: {len(basic_info.get('key_points', []))}")
            
            # Проверяем что информация извлечена
            assert basic_info.get('subject') == "Тестовое письмо для fallback"
            assert len(basic_info.get('organizations', [])) == 1
            assert len(basic_info.get('contacts', [])) == 1
            assert len(basic_info.get('interactions', [])) == 1
            assert len(basic_info.get('key_points', [])) >= 1
            
            # Тестируем fallback обработку
            print("\\n🆘 Тестируем fallback обработку...")
            fallback_result = resilient_processor._process_fallback(str(email_file))
            
            print(f"✅ Fallback результат:")
            print(f"   📋 Контекст: {fallback_result.get('business_context', 'Не найден')}")
            print(f"   🏢 Организаций: {len(fallback_result.get('organizations', []))}") 
            print(f"   👤 Контактов: {len(fallback_result.get('contacts', []))}")
            print(f"   🔗 Взаимодействий: {len(fallback_result.get('interactions', []))}")
            print(f"   ✅ Успех: {fallback_result.get('success', False)}")
            print(f"   🔧 Стратегия: {fallback_result.get('processing_strategy', 'unknown')}")
            print(f"   📝 Причина fallback: {fallback_result.get('fallback_reason', 'Не указана')}")
            
            # Проверяем что fallback результат содержит данные
            assert fallback_result.get('success') == True
            assert fallback_result.get('processing_strategy') == 'fallback'
            assert len(fallback_result.get('organizations', [])) >= 1
            assert len(fallback_result.get('contacts', [])) >= 1
            assert fallback_result.get('fallback_reason') is not None
            
            print("\\n✅ Все проверки fallback прошли успешно!")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_report_improvements():
    """Тест улучшений отчетности"""
    print("\\n🧪 Тестирование улучшений отчетности")
    print("=" * 70)
    
    try:
        from src.reporting.report_generator import ReportGenerator
        
        # Создаем временную директорию для тестов
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Создаем ReportGenerator
            report_gen = ReportGenerator(base_dir=temp_path, date="2025-07-29")
            
            # Регистрируем обычное письмо
            report_gen.register_email_result(
                filename="normal_email.json",
                email_metadata={'subject': 'Обычное письмо'},
                llm_raw={},
                processed={'success': True, 'organizations': [{}], 'contacts': [{}], 'interactions': [{}]},
                processing_time_seconds=1.5,
                errors=[]
            )
            
            # Регистрируем письмо с fallback обработкой
            report_gen.register_email_result(
                filename="problematic_email.json",
                email_metadata={'subject': 'Проблемное письмо'},
                llm_raw={},
                processed={
                    'success': True, 
                    'organizations': [{}], 
                    'contacts': [{}], 
                    'interactions': [],
                    'processing_strategy': 'fallback',
                    'fallback_reason': 'Ошибка валидации JSON Schema'
                },
                processing_time_seconds=3.2,
                errors=['Исходная ошибка: None is not of type integer', 'Применена fallback стратегия']
            )
            
            # Финализируем отчет
            summary_payload = report_gen.finalize({})
            
            # Проверяем что информация о стратегиях сохранена
            entries = summary_payload.get('entries', [])
            assert len(entries) == 2
            
            normal_entry = next((e for e in entries if e['filename'] == 'normal_email.json'), None)
            problematic_entry = next((e for e in entries if e['filename'] == 'problematic_email.json'), None)
            
            assert normal_entry is not None
            assert problematic_entry is not None
            
            print(f"✅ Обычное письмо:")
            print(f"   🔧 Стратегия: {normal_entry.get('processing_strategy', 'standard')}")
            print(f"   🔄 Повторная обработка: {normal_entry.get('was_retried', False)}")
            
            print(f"✅ Проблемное письмо:")
            print(f"   🔧 Стратегия: {problematic_entry.get('processing_strategy', 'unknown')}")
            print(f"   🔄 Повторная обработка: {problematic_entry.get('was_retried', False)}")
            print(f"   📝 Причина fallback: {problematic_entry.get('fallback_reason', 'Не указана')}")
            
            # Проверяем markdown отчет
            summary_md_path = temp_path / f"_summary_2025-07-29.md"
            if summary_md_path.exists():
                content = summary_md_path.read_text(encoding='utf-8')
                
                if "## 🔄 Проблемные письма" in content:
                    print("✅ Секция 'Проблемные письма' найдена в отчете")
                else:
                    print("❌ Секция 'Проблемные письма' отсутствует в отчете")
                    return False
                
                if "fallback" in content:
                    print("✅ Информация о fallback найдена в отчете")
                else:
                    print("❌ Информация о fallback отсутствует в отчете")
                    return False
                    
                print("\\n📄 Фрагмент отчета:")
                lines = content.split('\\n')
                for i, line in enumerate(lines):
                    if "🔄 Проблемные письма" in line:
                        # Показываем 10 строк начиная с этой секции
                        for j in range(i, min(i+10, len(lines))):
                            print(f"   {lines[j]}")
                        break
                        
            else:
                print("❌ Markdown отчет не создан")
                return False
            
            print("\\n✅ Все проверки отчетности прошли успешно!")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании отчетности: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТ УЛУЧШЕНИЙ FALLBACK И ОТЧЕТНОСТИ")
    print("=" * 70)
    
    success1 = test_fallback_improvements()
    success2 = test_report_improvements()
    
    print("\\n" + "=" * 70)
    if success1 and success2:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("Fallback обработка и отчетность улучшены.")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("Требуется доработка.")
        return 1

if __name__ == "__main__":
    sys.exit(main())