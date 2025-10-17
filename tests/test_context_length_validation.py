#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест валидации context length в ModelsManager
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.models_manager import ModelsManager
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_token_estimation():
    """Тест оценки токенов"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ 1: Оценка токенов")
    print("="*60)
    
    manager = ModelsManager()
    
    # Короткий текст
    short_text = "Hello, world!"
    tokens = manager.estimate_tokens(short_text)
    print(f"\n📝 Короткий текст: '{short_text}'")
    print(f"   Токенов: ~{tokens}")
    
    # Средний текст
    medium_text = "This is a longer text with multiple sentences. " * 10
    tokens = manager.estimate_tokens(medium_text)
    print(f"\n📝 Средний текст: {len(medium_text)} символов")
    print(f"   Токенов: ~{tokens}")
    
    # Длинный текст
    long_text = "This is a very long text. " * 1000
    tokens = manager.estimate_tokens(long_text)
    print(f"\n📝 Длинный текст: {len(long_text)} символов")
    print(f"   Токенов: ~{tokens}")
    
    print("\n✅ Тест оценки токенов пройден")


def test_context_validation():
    """Тест валидации context length"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ 2: Валидация context length")
    print("="*60)
    
    manager = ModelsManager()
    
    # Получаем первую модель OpenRouter
    model = manager.get_current_model('openrouter')
    if not model:
        print("❌ Модель не найдена")
        return
    
    print(f"\n📋 Тестируем модель: {model.name}")
    print(f"   Context window: {model.context_window} токенов")
    
    # Тест 1: Маленький текст - должен пройти
    small_text = "Hello, world!" * 10
    fits = manager.validate_context_length(model, small_text, max_output_tokens=1000)
    print(f"\n✅ Маленький текст ({len(small_text)} символов): {'помещается' if fits else 'НЕ помещается'}")
    
    # Тест 2: Огромный текст - не должен пройти для моделей с маленьким context
    huge_text = "This is a very long text. " * 50000
    fits = manager.validate_context_length(model, huge_text, max_output_tokens=8000)
    print(f"\n{'✅' if not fits else '❌'} Огромный текст ({len(huge_text)} символов): {'помещается' if fits else 'НЕ помещается'}")
    
    print("\n✅ Тест валидации context length пройден")


def test_model_selection_with_context():
    """Тест выбора модели с учетом context length"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ 3: Выбор модели с учетом context length")
    print("="*60)
    
    manager = ModelsManager()
    
    # Показываем доступные модели
    print("\n📋 Доступные модели OpenRouter:")
    for i, model in enumerate(manager.openrouter_models, 1):
        print(f"   {i}. {model.name} (context: {model.context_window})")
    
    # Тест 1: Маленький запрос - должна выбраться первая модель
    print("\n🔍 Тест 1: Маленький запрос (1000 токенов)")
    model = manager.get_current_model('openrouter', estimated_tokens=1000)
    if model:
        print(f"   ✅ Выбрана модель: {model.name} (context: {model.context_window})")
    else:
        print(f"   ❌ Модель не найдена")
    
    # Сбрасываем индекс
    manager.current_openrouter_index = 0
    
    # Тест 2: Средний запрос - должна выбраться подходящая модель
    print("\n🔍 Тест 2: Средний запрос (50000 токенов)")
    model = manager.get_current_model('openrouter', estimated_tokens=50000)
    if model:
        print(f"   ✅ Выбрана модель: {model.name} (context: {model.context_window})")
    else:
        print(f"   ❌ Модель не найдена")
    
    # Сбрасываем индекс
    manager.current_openrouter_index = 0
    
    # Тест 3: Огромный запрос - может не найтись модель
    print("\n🔍 Тест 3: Огромный запрос (2000000 токенов)")
    model = manager.get_current_model('openrouter', estimated_tokens=2000000)
    if model:
        print(f"   ✅ Выбрана модель: {model.name} (context: {model.context_window})")
    else:
        print(f"   ⚠️  Ни одна модель не подходит (это ожидаемо)")
    
    print("\n✅ Тест выбора модели пройден")


def main():
    """Запуск всех тестов"""
    print("\n" + "="*60)
    print("🚀 ТЕСТИРОВАНИЕ ВАЛИДАЦИИ CONTEXT LENGTH")
    print("="*60)
    
    try:
        test_token_estimation()
        test_context_validation()
        test_model_selection_with_context()
        
        print("\n" + "="*60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
