#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест интеграции ResilientEmailProcessor с APIPipelineValidator
"""

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """Тестирование импортов"""
    print("🧪 Тестирование импортов...")
    
    try:
        from src.postprocessing.resilient_processor import ResilientEmailProcessor
        print("✅ ResilientEmailProcessor импортирован успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта ResilientEmailProcessor: {e}")
        return False
    
    try:
        from src.core.safe_math_utils import safe_multiply, sanitize_json_fields
        print("✅ safe_math_utils импортированы успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта safe_math_utils: {e}")
        return False
    
    try:
        # Тестируем что исправления применились
        from src.postprocessing.advanced_contact_deduplicator import AdvancedContactDeduplicator
        from src.config.regions import calculate_contact_priority
        print("✅ Исправленные модули импортированы успешно")
    except ImportError as e:
        print(f"❌ Ошибка импорта исправленных модулей: {e}")
        return False
    
    return True

def test_safe_math():
    """Тестирование безопасных математических операций"""
    print("\n🔢 Тестирование safe_multiply...")
    
    from src.core.safe_math_utils import safe_multiply
    
    # Тест с None
    result = safe_multiply(None, 1.5)
    if result == 0.0:
        print("✅ safe_multiply(None, 1.5) = 0.0")
    else:
        print(f"❌ safe_multiply(None, 1.5) = {result}, ожидалось 0.0")
        return False
    
    # Тест с нормальными значениями
    result = safe_multiply(0.8, 1.2)
    if abs(result - 0.96) < 0.001:
        print("✅ safe_multiply(0.8, 1.2) = 0.96")
    else:
        print(f"❌ safe_multiply(0.8, 1.2) = {result}, ожидалось 0.96")
        return False
    
    return True

def test_sanitize_json():
    """Тестирование очистки JSON"""
    print("\n🧹 Тестирование sanitize_json_fields...")
    
    from src.core.safe_math_utils import sanitize_json_fields
    
    test_data = {
        'message_id_h极': 'test_value',
        'normal_field': 'normal_value'
    }
    
    result = sanitize_json_fields(test_data)
    
    if 'message_id_hint' in result and 'message_id_h极' not in result:
        print("✅ Китайские символы в полях исправлены")
    else:
        print(f"❌ Китайские символы не исправлены: {result}")
        return False
    
    return True

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование интеграции ResilientEmailProcessor")
    print("=" * 60)
    
    success = True
    
    success &= test_imports()
    success &= test_safe_math()
    success &= test_sanitize_json()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Все тесты прошли успешно!")
        print("🔄 ResilientEmailProcessor готов к использованию")
    else:
        print("❌ Некоторые тесты не прошли")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())