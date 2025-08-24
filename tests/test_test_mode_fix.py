#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест исправления бага с test_mode в ContactExtractor
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Добавляем путь к src для импортов
sys.path.append(str(Path(__file__).parent.parent / "src"))

from integrated_llm_processor import IntegratedLLMProcessor
from llm_extractor import ContactExtractor


def test_test_mode_propagation():
    """
    🧪 Тест корректной передачи test_mode из IntegratedLLMProcessor в ContactExtractor
    """
    print("\n🧪 Тестирование передачи test_mode...")
    
    # Тест 1: test_mode=True должен передаваться в ContactExtractor
    print("\n1️⃣ Тест: test_mode=True")
    processor_test = IntegratedLLMProcessor(test_mode=True)
    assert processor_test.test_mode == True, "IntegratedLLMProcessor должен иметь test_mode=True"
    assert processor_test.contact_extractor.test_mode == True, "ContactExtractor должен иметь test_mode=True"
    print("   ✅ test_mode=True корректно передан в ContactExtractor")
    
    # Тест 2: test_mode=False должен передаваться в ContactExtractor
    print("\n2️⃣ Тест: test_mode=False")
    processor_prod = IntegratedLLMProcessor(test_mode=False)
    assert processor_prod.test_mode == False, "IntegratedLLMProcessor должен иметь test_mode=False"
    assert processor_prod.contact_extractor.test_mode == False, "ContactExtractor должен иметь test_mode=False"
    print("   ✅ test_mode=False корректно передан в ContactExtractor")
    
    print("\n✅ Все тесты передачи test_mode прошли успешно!")


def test_test_mode_behavior():
    """
    🧪 Тест поведения ContactExtractor в тестовом режиме
    """
    print("\n🧪 Тестирование поведения в тестовом режиме...")
    
    # Создаем ContactExtractor в тестовом режиме
    extractor = ContactExtractor(test_mode=True)
    
    # Тестовые данные (без метаданных, чтобы активировать тестовый режим)
    test_text = "Тестовое письмо от test@example.com"
    
    # Вызываем extract_contacts без метаданных для активации тестового режима
    result = extractor.extract_contacts(test_text, metadata=None)
    
    # Проверяем, что возвращаются тестовые данные
    assert 'contacts' in result, "Результат должен содержать поле 'contacts'"
    assert len(result['contacts']) > 0, "Должен быть хотя бы один тестовый контакт"
    assert result['contacts'][0]['name'] == 'Тестовый Контакт', "Должен возвращаться тестовый контакт"
    assert result['provider_used'] == 'Test Mode', "Должен использоваться Test Mode"
    
    print("   ✅ Тестовый режим работает корректно")
    print(f"   📊 Получен тестовый контакт: {result['contacts'][0]['name']}")
    
    print("\n✅ Тест поведения в тестовом режиме прошел успешно!")


def test_real_email_mode_override():
    """
    🧪 Тест временного отключения test_mode для реальных писем
    """
    print("\n🧪 Тестирование отключения test_mode для реальных писем...")
    
    # Создаем ContactExtractor в тестовом режиме
    extractor = ContactExtractor(test_mode=True)
    
    # Проверяем исходное состояние
    assert extractor.test_mode == True, "Исходно должен быть test_mode=True"
    
    # Тестовые данные реального письма (с метаданными)
    real_email_text = "Письмо от реального отправителя"
    real_metadata = {
        'from': 'real@company.com',
        'subject': 'Реальное письмо',
        'date': '2025-01-21'
    }
    
    # Мокаем LLM провайдеры, чтобы избежать реальных запросов
    with patch.object(extractor, 'providers', {}):
        result = extractor.extract_contacts(real_email_text, real_metadata)
    
    # Проверяем, что test_mode восстановлен после обработки
    assert extractor.test_mode == True, "test_mode должен быть восстановлен после обработки реального письма"
    
    print("   ✅ test_mode корректно восстанавливается после обработки реального письма")
    
    print("\n✅ Тест отключения test_mode для реальных писем прошел успешно!")


if __name__ == "__main__":
    print("🧪 Запуск тестов исправления бага с test_mode")
    
    try:
        test_test_mode_propagation()
        test_test_mode_behavior()
        test_real_email_mode_override()
        
        print("\n🎉 Все тесты прошли успешно!")
        print("✅ Баг с test_mode исправлен корректно")
        
    except Exception as e:
        print(f"\n❌ Тест провалился: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)