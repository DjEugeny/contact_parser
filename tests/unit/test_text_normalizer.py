#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Unit тесты для text_normalizer.py
Тестирование функции normalize_first_word_only

Author: Contact Parser Team
Created: 2025-09-30
"""

import sys
import os

# Добавляем путь к src для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from postprocessing.text_normalizer import normalize_first_word_only


def run_test(test_name, test_func):
    """Запуск одного теста"""
    try:
        test_func()
        print(f"✅ {test_name}")
        return True
    except AssertionError as e:
        print(f"❌ {test_name}: {e}")
        return False
    except Exception as e:
        print(f"💥 {test_name}: Ошибка - {e}")
        return False


def test_basic_normalization():
    """Тест базовой нормализации - первое слово с заглавной буквы"""
    assert normalize_first_word_only("руководитель ОМТС") == "Руководитель ОМТС"
    assert normalize_first_word_only("заведующая клинико-диагностической лабораторией") == "Заведующая клинико-диагностической лабораторией"
    assert normalize_first_word_only("центр специализированной медицинской помощи") == "Центр специализированной медицинской помощи"


def test_preserve_abbreviations():
    """Тест сохранения аббревиатур в исходном регистре"""
    assert normalize_first_word_only("ведущий специалист по проектам Группы КДЛ") == "Ведущий специалист по проектам Группы КДЛ"
    assert normalize_first_word_only("специалист компании ООО \"Агрохим\"") == "Специалист компании ООО \"Агрохим\""
    assert normalize_first_word_only("менеджер отдела продаж ОМТС") == "Менеджер отдела продаж ОМТС"


def test_quoted_text():
    """Тест обработки текста в кавычках"""
    # Обычные кавычки
    assert normalize_first_word_only("менеджер отдела \"Оборудование для микробиологии\"") == "Менеджер отдела \"Оборудование для микробиологии\""
    assert normalize_first_word_only("\"центр гигиены и эпидемиологии\"") == "\"Центр гигиены и эпидемиологии\""
    
    # Кавычки-елочки
    assert normalize_first_word_only("департамент продаж «Медицина»") == "Департамент продаж «Медицина»"
    assert normalize_first_word_only("«центр гигиены и эпидемиологии»") == "«Центр гигиены и эпидемиологии»"


def test_complex_cases():
    """Тест сложных случаев из реальных данных"""
    # Длинные названия с аббревиатурами
    assert normalize_first_word_only("ведущий специалист по проектам Группы КДЛ Департамента продаж «Медицина»") == "Ведущий специалист по проектам Группы КДЛ Департамента продаж «Медицина»"
    
    # Организации с аббревиатурами
    assert normalize_first_word_only("ФБУЗ \"Центр Гигиены и Эпидемиологии в Республике Хакасия\"") == "ФБУЗ \"Центр Гигиены и Эпидемиологии в Республике Хакасия\""
    
    # Должности с сокращениями
    assert normalize_first_word_only("зам. начальника отдела продаж") == "Зам. начальника отдела продаж"


def test_edge_cases():
    """Тест граничных случаев"""
    # Пустые строки
    assert normalize_first_word_only("") == ""
    assert normalize_first_word_only("   ") == "   "
    
    # Одна буква
    assert normalize_first_word_only("а") == "А"
    assert normalize_first_word_only("А") == "А"
    
    # Пустые кавычки
    assert normalize_first_word_only("\"\"") == "\"\""
    assert normalize_first_word_only("«»") == "«»"
    
    # Только пробелы в кавычках
    assert normalize_first_word_only("\"   \"") == "\"   \""


def test_already_normalized():
    """Тест уже нормализованного текста"""
    # Уже правильно нормализованные строки должны остаться без изменений
    assert normalize_first_word_only("Руководитель ОМТС") == "Руководитель ОМТС"
    assert normalize_first_word_only("Заведующая клинико-диагностической лабораторией") == "Заведующая клинико-диагностической лабораторией"
    assert normalize_first_word_only("Центр специализированной медицинской помощи") == "Центр специализированной медицинской помощи"


def test_uppercase_first_word():
    """Тест когда первое слово уже в верхнем регистре"""
    assert normalize_first_word_only("РУКОВОДИТЕЛЬ отдела продаж") == "РУКОВОДИТЕЛЬ отдела продаж"
    assert normalize_first_word_only("ЦЕНТР медицинской помощи") == "ЦЕНТР медицинской помощи"


def test_mixed_case_preservation():
    """Тест сохранения смешанного регистра в остальных словах"""
    # Важно что остальные слова сохраняют исходный регистр
    assert normalize_first_word_only("менеджер По Продаже Оборудования") == "Менеджер По Продаже Оборудования"
    assert normalize_first_word_only("специалист компании ООО") == "Специалист компании ООО"
    assert normalize_first_word_only("директор Департамента КДЛ") == "Директор Департамента КДЛ"


def test_whitespace_handling():
    """Тест обработки пробелов"""
    # Ведущие и завершающие пробелы должны сохраняться при strip()
    result1 = normalize_first_word_only("  руководитель ОМТС  ")
    expected1 = "Руководитель ОМТС"  # strip() убирает ведущие/завершающие пробелы
    assert result1 == expected1, f"Expected '{expected1}', got '{result1}'"
    
    # Но внутренние пробелы не должны изменяться
    assert normalize_first_word_only("менеджер  по  продажам") == "Менеджер  по  продажам"


if __name__ == "__main__":
    print("🧪 Запуск unit-тестов для normalize_first_word_only")
    print("=" * 60)
    
    tests = [
        ("Базовая нормализация", test_basic_normalization),
        ("Сохранение аббревиатур", test_preserve_abbreviations),
        ("Текст в кавычках", test_quoted_text),
        ("Сложные случаи", test_complex_cases),
        ("Граничные случаи", test_edge_cases),
        ("Уже нормализованный текст", test_already_normalized),
        ("Первое слово в верхнем регистре", test_uppercase_first_word),
        ("Сохранение смешанного регистра", test_mixed_case_preservation),
        ("Обработка пробелов", test_whitespace_handling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1
    
    print("=" * 60)
    print(f"Результат: {passed}/{total} тестов прошли")
    
    if passed == total:
        print("🎉 Все тесты успешно пройдены!")
    else:
        print(f"⚠️  {total - passed} тестов не прошли")
        sys.exit(1)