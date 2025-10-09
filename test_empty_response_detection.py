#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки детекции пустых ответов в провайдерах
"""

import sys
import os

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Импортируем напрямую из файла, чтобы избежать проблем с относительными импортами
from src.providers.exceptions import EmptyResponseError


def test_empty_response_error_creation():
    """Тест создания EmptyResponseError"""
    print("🧪 Тест 1: Создание EmptyResponseError с полными параметрами")
    
    error = EmptyResponseError(
        model_name="test-model",
        request_id="req-123",
        input_length=1000
    )
    
    assert error.model_name == "test-model"
    assert error.request_id == "req-123"
    assert error.input_length == 1000
    assert "test-model" in str(error)
    assert "req-123" in str(error)
    assert "1000" in str(error)
    
    print(f"✅ Ошибка создана: {error}")
    print()


def test_empty_response_error_minimal():
    """Тест создания EmptyResponseError с минимальными параметрами"""
    print("🧪 Тест 2: Создание EmptyResponseError только с model_name")
    
    error = EmptyResponseError(model_name="minimal-model")
    
    assert error.model_name == "minimal-model"
    assert error.request_id is None
    assert error.input_length is None
    assert "minimal-model" in str(error)
    
    print(f"✅ Ошибка создана: {error}")
    print()


def test_empty_response_error_custom_message():
    """Тест создания EmptyResponseError с кастомным сообщением"""
    print("🧪 Тест 3: Создание EmptyResponseError с кастомным сообщением")
    
    custom_msg = "Модель вернула пустой ответ после 3 попыток"
    error = EmptyResponseError(
        model_name="custom-model",
        message=custom_msg
    )
    
    assert error.model_name == "custom-model"
    assert str(error) == custom_msg
    
    print(f"✅ Ошибка создана: {error}")
    print()


def test_empty_response_error_inheritance():
    """Тест что EmptyResponseError наследуется от Exception"""
    print("🧪 Тест 4: Проверка наследования от Exception")
    
    error = EmptyResponseError(model_name="test")
    
    assert isinstance(error, Exception)
    
    # Проверяем что можно выбросить и поймать
    try:
        raise error
    except EmptyResponseError as e:
        print(f"✅ Исключение успешно поймано: {e}")
    except Exception:
        print("❌ Исключение поймано как общий Exception")
        raise
    
    print()


def main():
    """Запуск всех тестов"""
    print("=" * 60)
    print("🚀 Тестирование EmptyResponseError")
    print("=" * 60)
    print()
    
    try:
        test_empty_response_error_creation()
        test_empty_response_error_minimal()
        test_empty_response_error_custom_message()
        test_empty_response_error_inheritance()
        
        print("=" * 60)
        print("✅ Все тесты пройдены успешно!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"❌ Тест провален: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
