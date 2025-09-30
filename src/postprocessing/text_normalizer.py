#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 Простой нормализатор текста
Функция для правильной нормализации регистра: только первое слово с заглавной буквы

Author: Contact Parser Team
Created: 2025-09-30
"""

import logging
from typing import Optional


def normalize_first_word_only(text: str) -> str:
    """
    Нормализует только первое слово - делает заглавной первую букву.
    Остальные слова остаются в исходном регистре.
    
    Примеры:
    - "руководитель ОМТС" → "Руководитель ОМТС"
    - "заведующая клинико-диагностической лабораторией" → "Заведующая клинико-диагностической лабораторией"
    - "центр специализированной медицинской помощи" → "Центр специализированной медицинской помощи"
    - "ФБУЗ \"Центр Гигиены и Эпидемиологии\"" → "ФБУЗ \"Центр Гигиены и Эпидемиологии\""
    
    Args:
        text: Исходный текст для нормализации
        
    Returns:
        str: Нормализованный текст с заглавной первой буквой первого слова
    """
    if not text or not text.strip():
        return text or ''
    
    text = text.strip()
    
    # Специальная обработка для текста в кавычках
    if text.startswith('"') and text.endswith('"') and len(text) > 2:
        # Для текста в кавычках нормализуем только содержимое
        inner_text = text[1:-1]
        if inner_text:
            normalized_inner = inner_text[0].upper() + inner_text[1:] if len(inner_text) > 1 else inner_text.upper()
            return f'"{normalized_inner}"'
        return text
    
    # Специальная обработка для текста в одинарных кавычках
    if text.startswith("'") and text.endswith("'") and len(text) > 2:
        inner_text = text[1:-1]
        if inner_text:
            normalized_inner = inner_text[0].upper() + inner_text[1:] if len(inner_text) > 1 else inner_text.upper()
            return f"'{normalized_inner}'"
        return text
    
    # Специальная обработка для текста в кавычках-елочках
    if text.startswith('«') and text.endswith('»') and len(text) > 2:
        inner_text = text[1:-1]
        if inner_text:
            normalized_inner = inner_text[0].upper() + inner_text[1:] if len(inner_text) > 1 else inner_text.upper()
            return f'«{normalized_inner}»'
        return text
    
    # Обычная нормализация - только первая буква заглавная
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()


# Пример использования и тестирование
if __name__ == "__main__":
    # Тестовые примеры из дизайна
    test_cases = [
        # Должности
        "руководитель ОМТС",
        "заведующая клинико-диагностической лабораторией", 
        "ведущий специалист по проектам Группы КДЛ Департамента продаж «Медицина»",
        "зам. начальника отдела продаж",
        "менеджер отдела \"Оборудование для микробиологии и биотехнологий\"",
        "специалист компании ООО \"Агрохим\"",
        
        # Организации
        "центр специализированной медицинской помощи детям имени В.Ф. Войно-Ясенецкого",
        "ФБУЗ \"Центр Гигиены и Эпидемиологии в Республике Хакасия\"",
        
        # Граничные случаи
        "",
        "   ",
        "а",
        "А",
        "\"\"",
        "«»",
    ]
    
    expected_results = [
        # Должности
        "Руководитель ОМТС",
        "Заведующая клинико-диагностической лабораторией",
        "Ведущий специалист по проектам Группы КДЛ Департамента продаж «Медицина»",
        "Зам. начальника отдела продаж", 
        "Менеджер отдела \"Оборудование для микробиологии и биотехнологий\"",
        "Специалист компании ООО \"Агрохим\"",
        
        # Организации
        "Центр специализированной медицинской помощи детям имени В.Ф. Войно-Ясенецкого",
        "ФБУЗ \"Центр Гигиены и Эпидемиологии в Республике Хакасия\"",
        
        # Граничные случаи
        "",
        "   ",
        "А",
        "А",
        "\"\"",
        "«»",
    ]
    
    print("📝 Тестирование normalize_first_word_only:")
    print("=" * 80)
    
    all_passed = True
    for i, (input_text, expected) in enumerate(zip(test_cases, expected_results)):
        result = normalize_first_word_only(input_text)
        status = "✅" if result == expected else "❌"
        
        if result != expected:
            all_passed = False
        
        print(f"{status} Тест {i+1:2d}: '{input_text}' → '{result}'")
        if result != expected:
            print(f"          Ожидалось: '{expected}'")
    
    print("=" * 80)
    print(f"Результат: {'✅ Все тесты прошли' if all_passed else '❌ Есть ошибки'}")