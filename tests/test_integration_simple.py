#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Упрощенный интеграционный тест исправлений
Проверяет интеграцию без зависимостей от внешних библиотек

Author: Contact Parser Team
Created: 2025-09-30
"""

import sys
import importlib.util
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def load_module_from_file(module_name, file_path):
    """Загрузка модуля из файла без импорта зависимостей"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"⚠️ Ошибка загрузки {module_name}: {e}")
        return None

def test_safe_math_utils():
    """Тест safe_math_utils"""
    print("🧪 Тестирование safe_math_utils...")
    
    safe_math = load_module_from_file(
        'safe_math_utils', 
        PROJECT_ROOT / 'src' / 'core' / 'safe_math_utils.py'
    )
    
    if not safe_math:
        return False
    
    # Тест safe_multiply
    result = safe_math.safe_multiply(None, 1.5)
    if result != 0.0:
        print(f"❌ safe_multiply(None, 1.5) = {result}, ожидалось 0.0")
        return False
    
    # Тест sanitize_json_fields
    test_data = {'message_id_h极': 'test', 'normal': 'value'}
    result = safe_math.sanitize_json_fields(test_data)
    if 'message_id_hint' not in result or 'message_id_h极' in result:
        print(f"❌ sanitize_json_fields не исправил китайские символы: {result}")
        return False
    
    print("✅ safe_math_utils работает корректно")
    return True

def test_text_normalizer():
    """Тест text_normalizer"""
    print("🧪 Тестирование text_normalizer...")
    
    text_normalizer = load_module_from_file(
        'text_normalizer', 
        PROJECT_ROOT / 'src' / 'postprocessing' / 'text_normalizer.py'
    )
    
    if not text_normalizer:
        return False
    
    # Тест normalize_first_word_only
    test_cases = [
        ("руководитель ОМТС", "Руководитель ОМТС"),
        ("'менеджер по продажам'", "'Менеджер по продажам'"),
        ("\"директор\"", "\"Директор\""),
    ]
    
    for input_text, expected in test_cases:
        result = text_normalizer.normalize_first_word_only(input_text)
        if result != expected:
            print(f"❌ normalize_first_word_only('{input_text}') = '{result}', ожидалось '{expected}'")
            return False
    
    print("✅ text_normalizer работает корректно")
    return True

def test_resilient_processor():
    """Тест resilient_processor"""
    print("🧪 Тестирование resilient_processor...")
    
    resilient_processor = load_module_from_file(
        'resilient_processor', 
        PROJECT_ROOT / 'src' / 'postprocessing' / 'resilient_processor.py'
    )
    
    if not resilient_processor:
        return False
    
    # Проверяем что классы и перечисления существуют
    if not hasattr(resilient_processor, 'ProcessingStrategy'):
        print("❌ ProcessingStrategy не найден")
        return False
    
    if not hasattr(resilient_processor, 'ResilientEmailProcessor'):
        print("❌ ResilientEmailProcessor не найден")
        return False
    
    if not hasattr(resilient_processor, 'ProcessingResult'):
        print("❌ ProcessingResult не найден")
        return False
    
    # Проверяем стратегии
    strategies = resilient_processor.ProcessingStrategy
    if strategies.STANDARD.value != "standard":
        print("❌ ProcessingStrategy.STANDARD неверное значение")
        return False
    
    print("✅ resilient_processor структура корректна")
    return True

def test_postprocessor_imports():
    """Тест что PostProcessor содержит правильные импорты"""
    print("🧪 Тестирование импортов в PostProcessor...")
    
    # Читаем файл PostProcessor
    postprocessor_file = PROJECT_ROOT / 'src' / 'postprocessing' / 'postprocessor.py'
    
    if not postprocessor_file.exists():
        print("❌ Файл postprocessor.py не найден")
        return False
    
    content = postprocessor_file.read_text(encoding='utf-8')
    
    # Проверяем наличие импортов
    required_imports = [
        'from .smart_contact_enricher import SmartContactEnricher',
        'from ..core.safe_math_utils import fix_none_values_in_data, sanitize_json_fields'
    ]
    
    for import_line in required_imports:
        if import_line not in content:
            print(f"❌ Отсутствует импорт: {import_line}")
            return False
    
    # Проверяем наличие метода _apply_critical_fixes
    if 'def _apply_critical_fixes' not in content:
        print("❌ Метод _apply_critical_fixes не найден")
        return False
    
    # Проверяем использование SmartContactEnricher
    if 'self.smart_enricher' not in content:
        print("❌ SmartContactEnricher не используется")
        return False
    
    print("✅ PostProcessor содержит правильные импорты и методы")
    return True

def test_api_pipeline_validator_imports():
    """Тест что APIPipelineValidator содержит правильные импорты"""
    print("🧪 Тестирование импортов в APIPipelineValidator...")
    
    # Читаем файл APIPipelineValidator
    validator_file = PROJECT_ROOT / 'src' / 'api_pipeline_validator.py'
    
    if not validator_file.exists():
        print("❌ Файл api_pipeline_validator.py не найден")
        return False
    
    content = validator_file.read_text(encoding='utf-8')
    
    # Проверяем наличие импорта ResilientEmailProcessor
    if 'from src.postprocessing.resilient_processor import ResilientEmailProcessor' not in content:
        print("❌ Отсутствует импорт ResilientEmailProcessor")
        return False
    
    # Проверяем создание ResilientEmailProcessor
    if 'self.resilient_processor = ResilientEmailProcessor' not in content:
        print("❌ ResilientEmailProcessor не создается")
        return False
    
    # Проверяем метод process_single_email
    if 'def process_single_email' not in content:
        print("❌ Метод process_single_email не найден")
        return False
    
    # Проверяем использование в _process_date
    if 'resilient_processor.process_emails_with_retry' not in content:
        print("❌ ResilientEmailProcessor не используется в _process_date")
        return False
    
    print("✅ APIPipelineValidator содержит правильные интеграции")
    return True

def test_file_structure():
    """Тест структуры файлов"""
    print("🧪 Тестирование структуры файлов...")
    
    required_files = [
        'src/core/safe_math_utils.py',
        'src/postprocessing/text_normalizer.py',
        'src/postprocessing/resilient_processor.py',
        'src/postprocessing/smart_contact_enricher.py',
        'tests/test_critical_fixes_integration.py'
    ]
    
    for file_path in required_files:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            print(f"❌ Отсутствует файл: {file_path}")
            return False
    
    print("✅ Все необходимые файлы присутствуют")
    return True

def main():
    """Основная функция тестирования"""
    print("🚀 УПРОЩЕННЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ КРИТИЧЕСКИХ ИСПРАВЛЕНИЙ")
    print("=" * 70)
    print("Проверяем интеграцию исправлений без внешних зависимостей")
    print("=" * 70)
    
    tests = [
        ("Структура файлов", test_file_structure),
        ("safe_math_utils", test_safe_math_utils),
        ("text_normalizer", test_text_normalizer),
        ("resilient_processor", test_resilient_processor),
        ("PostProcessor импорты", test_postprocessor_imports),
        ("APIPipelineValidator импорты", test_api_pipeline_validator_imports),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Ошибка в тесте {test_name}: {e}")
            results.append(False)
    
    # Итоговый результат
    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    
    for i, (test_name, result) in enumerate(zip([t[0] for t in tests], results), 1):
        status = "✅ УСПЕХ" if result else "❌ НЕУДАЧА"
        print(f"   {i}. {test_name}: {status}")
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n🎯 Общий результат: {success_count}/{total_count} тестов прошли успешно")
    
    if success_count == total_count:
        print("🎉 ВСЕ ИСПРАВЛЕНИЯ УСПЕШНО ИНТЕГРИРОВАНЫ!")
        print("Система готова к использованию с критическими исправлениями.")
        return 0
    else:
        print("⚠️ Некоторые интеграции требуют доработки.")
        return 1

if __name__ == "__main__":
    sys.exit(main())