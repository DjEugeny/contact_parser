#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест запуска основных модулей системы
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Тестирование импортов основных модулей"""
    print("🔍 Тестирование импортов...")
    
    try:
        from google_sheets_bridge import LLM_Sheets_Bridge
        print("✅ LLM_Sheets_Bridge импортирован успешно")
    except Exception as e:
        print(f"❌ Ошибка импорта LLM_Sheets_Bridge: {e}")
        return False
    
    try:
        from integrated_llm_processor import IntegratedLLMProcessor
        print("✅ IntegratedLLMProcessor импортирован успешно")
    except Exception as e:
        print(f"❌ Ошибка импорта IntegratedLLMProcessor: {e}")
        return False
    
    try:
        from google_sheets_exporter import GoogleSheetsExporter
        print("✅ GoogleSheetsExporter импортирован успешно")
    except Exception as e:
        print(f"❌ Ошибка импорта GoogleSheetsExporter: {e}")
        return False
    
    try:
        from local_exporter import LocalDataExporter
        print("✅ LocalDataExporter импортирован успешно")
    except Exception as e:
        print(f"❌ Ошибка импорта LocalDataExporter: {e}")
        return False
    
    return True

def test_initialization():
    """Тестирование инициализации основных классов"""
    print("\n🔧 Тестирование инициализации...")
    
    try:
        from integrated_llm_processor import IntegratedLLMProcessor
        processor = IntegratedLLMProcessor(test_mode=True)
        print("✅ IntegratedLLMProcessor инициализирован в тестовом режиме")
    except Exception as e:
        print(f"❌ Ошибка инициализации IntegratedLLMProcessor: {e}")
        return False
    
    try:
        from local_exporter import LocalDataExporter
        exporter = LocalDataExporter()
        print("✅ LocalDataExporter инициализирован успешно")
    except Exception as e:
        print(f"❌ Ошибка инициализации LocalDataExporter: {e}")
        return False
    
    return True

def main():
    """Основная функция тестирования"""
    print("🚀 Быстрый тест системы Contact Parser")
    print("=" * 50)
    
    # Тест импортов
    if not test_imports():
        print("\n❌ Тестирование импортов провалено")
        return False
    
    # Тест инициализации
    if not test_initialization():
        print("\n❌ Тестирование инициализации провалено")
        return False
    
    print("\n✅ Все тесты пройдены успешно!")
    print("🎯 Система готова к работе")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)