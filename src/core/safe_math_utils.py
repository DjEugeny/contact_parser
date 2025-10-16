#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔢 Утилиты для безопасных математических операций
Предотвращение ошибок типа "NoneType * float"

Author: Contact Parser Team
Created: 2025-09-30
"""

import logging
from typing import Union, Optional

logger = logging.getLogger(__name__)


def safe_multiply(value: Optional[Union[int, float]], multiplier: Optional[Union[int, float]], default: float = 0.0) -> float:
    """
    Безопасное умножение с проверкой на None
    
    Args:
        value: Первое значение (может быть None)
        multiplier: Множитель (может быть None)
        default: Значение по умолчанию если один из операндов None
        
    Returns:
        float: Результат умножения или значение по умолчанию
        
    Examples:
        >>> safe_multiply(0.8, 1.2)
        0.96
        >>> safe_multiply(None, 1.2)
        0.0
        >>> safe_multiply(0.8, None)
        0.0
        >>> safe_multiply(None, None, 0.5)
        0.5
    """
    if value is None or multiplier is None:
        logger.debug(f"safe_multiply: один из операндов None (value={value}, multiplier={multiplier}), возвращаем {default}")
        return default
    
    try:
        result = float(value) * float(multiplier)
        return result
    except (ValueError, TypeError) as e:
        logger.warning(f"safe_multiply: ошибка преобразования типов (value={value}, multiplier={multiplier}): {e}, возвращаем {default}")
        return default


def safe_divide(dividend: Optional[Union[int, float]], divisor: Optional[Union[int, float]], default: float = 0.0) -> float:
    """
    Безопасное деление с проверкой на None и ноль
    
    Args:
        dividend: Делимое (может быть None)
        divisor: Делитель (может быть None)
        default: Значение по умолчанию при ошибке
        
    Returns:
        float: Результат деления или значение по умолчанию
    """
    if dividend is None or divisor is None:
        logger.debug(f"safe_divide: один из операндов None (dividend={dividend}, divisor={divisor}), возвращаем {default}")
        return default
    
    try:
        divisor_float = float(divisor)
        if divisor_float == 0:
            logger.warning(f"safe_divide: деление на ноль (dividend={dividend}, divisor={divisor}), возвращаем {default}")
            return default
        
        result = float(dividend) / divisor_float
        return result
    except (ValueError, TypeError) as e:
        logger.warning(f"safe_divide: ошибка преобразования типов (dividend={dividend}, divisor={divisor}): {e}, возвращаем {default}")
        return default


def safe_add(value1: Optional[Union[int, float]], value2: Optional[Union[int, float]], default: float = 0.0) -> float:
    """
    Безопасное сложение с проверкой на None
    
    Args:
        value1: Первое значение (может быть None)
        value2: Второе значение (может быть None)
        default: Значение по умолчанию если оба операнда None
        
    Returns:
        float: Результат сложения
    """
    if value1 is None and value2 is None:
        return default
    
    try:
        val1 = float(value1) if value1 is not None else 0.0
        val2 = float(value2) if value2 is not None else 0.0
        return val1 + val2
    except (ValueError, TypeError) as e:
        logger.warning(f"safe_add: ошибка преобразования типов (value1={value1}, value2={value2}): {e}, возвращаем {default}")
        return default


def ensure_float(value: Optional[Union[int, float, str]], default: float = 0.0) -> float:
    """
    Безопасное преобразование в float
    
    Args:
        value: Значение для преобразования
        default: Значение по умолчанию при ошибке
        
    Returns:
        float: Преобразованное значение или значение по умолчанию
    """
    if value is None:
        return default
    
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"ensure_float: не удалось преобразовать {value} в float: {e}, возвращаем {default}")
        return default


def clamp(value: Optional[Union[int, float]], min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    Ограничение значения в заданном диапазоне
    
    Args:
        value: Значение для ограничения
        min_val: Минимальное значение
        max_val: Максимальное значение
        
    Returns:
        float: Ограниченное значение
    """
    if value is None:
        return min_val
    
    try:
        float_val = float(value)
        return max(min_val, min(max_val, float_val))
    except (ValueError, TypeError):
        return min_val


def fix_none_values_in_data(data, numeric_fields=None, integer_fields=None):
    """
    Исправление None значений в числовых полях данных
    
    Args:
        data: Данные для исправления (dict, list или примитив)
        numeric_fields: Список полей которые должны быть числовыми (float)
        integer_fields: Список полей которые должны быть целыми числами (int)
        
    Returns:
        Исправленные данные
    """
    if numeric_fields is None:
        numeric_fields = ['confidence', 'score', 'weight', 'value_score', 'similarity', 'probability']
    
    if integer_fields is None:
        # organization_id и contact_id теперь могут быть null - не включаем в автокоррекцию
        integer_fields = ['id', 'user_id', 'company_id']
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key in numeric_fields and value is None:
                data[key] = 0.0
                logger.debug(f"fix_none_values_in_data: исправлено {key}: None → 0.0")
            elif key in integer_fields and value is None:
                data[key] = 1  # Для ID полей используем 1 как значение по умолчанию
                logger.debug(f"fix_none_values_in_data: исправлено {key}: None → 1")
            elif isinstance(value, (dict, list)):
                fix_none_values_in_data(value, numeric_fields, integer_fields)
    elif isinstance(data, list):
        for item in data:
            fix_none_values_in_data(item, numeric_fields, integer_fields)
    
    return data


def sanitize_json_fields(data):
    """
    Очистка полей JSON от некорректных символов (например, китайских символов)
    
    Args:
        data: Данные для очистки (dict, list или примитив)
        
    Returns:
        Очищенные данные
    """
    import re
    
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Очищаем ключи от некорректных символов
            clean_key = _sanitize_field_name(key)
            sanitized[clean_key] = sanitize_json_fields(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_json_fields(item) for item in data]
    elif isinstance(data, str):
        # Очищаем строковые значения от некорректных символов
        return _sanitize_string_value(data)
    else:
        return data


def _sanitize_field_name(field_name):
    """
    Очистка имени поля от некорректных символов
    
    Args:
        field_name: Имя поля для очистки
        
    Returns:
        Очищенное имя поля
    """
    import re
    
    # Известные проблемные замены
    replacements = {
        'message_id_h极': 'message_id_hint',
        'message_id_极': 'message_id_hint',
    }
    
    # Проверяем точные совпадения
    if field_name in replacements:
        logger.warning(f"sanitize_json_fields: исправлено поле {field_name} → {replacements[field_name]}")
        return replacements[field_name]
    
    # Удаляем китайские символы и другие некорректные символы
    # Оставляем только латинские буквы, цифры и подчеркивания
    clean_name = re.sub(r'[^\w]', '_', field_name)
    clean_name = re.sub(r'_+', '_', clean_name)  # Убираем множественные подчеркивания
    clean_name = clean_name.strip('_')  # Убираем подчеркивания в начале и конце
    
    if clean_name != field_name:
        logger.warning(f"sanitize_json_fields: очищено поле {field_name} → {clean_name}")
    
    return clean_name


def _sanitize_string_value(value):
    """
    Очистка строкового значения от некорректных символов
    
    Args:
        value: Строковое значение для очистки
        
    Returns:
        Очищенное значение
    """
    import re
    
    # Удаляем управляющие символы, но оставляем обычные символы включая кириллицу
    # Удаляем только действительно проблемные символы
    clean_value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
    
    # Удаляем китайские символы если они случайно попали
    clean_value = re.sub(r'[\u4e00-\u9fff]', '', clean_value)
    
    return clean_value


def fix_json_schema_validation_errors(data):
    """
    Исправление конкретных ошибок валидации JSON Schema
    
    Args:
        data: Данные для исправления
        
    Returns:
        Исправленные данные
    """
    if isinstance(data, dict):
        # Исправляем ошибки в секции interactions
        if 'interactions' in data and isinstance(data['interactions'], list):
            for interaction in data['interactions']:
                if isinstance(interaction, dict):
                    # organization_id и contact_id теперь могут быть null - НЕ исправляем
                    pass
        
        # Исправляем ошибки в других секциях
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                fix_json_schema_validation_errors(value)
    
    elif isinstance(data, list):
        for item in data:
            fix_json_schema_validation_errors(item)
    
    return data


# Тестирование функций
if __name__ == "__main__":
    # Настройка логирования для тестов
    logging.basicConfig(level=logging.DEBUG)
    
    print("🔢 Тестирование безопасных математических операций")
    print("=" * 60)
    
    # Тесты safe_multiply
    test_cases = [
        (0.8, 1.2, 0.96),
        (None, 1.2, 0.0),
        (0.8, None, 0.0),
        (None, None, 0.0),
        ("0.5", "2.0", 1.0),
        ("invalid", 1.0, 0.0)
    ]
    
    print("Тесты safe_multiply:")
    for value, multiplier, expected in test_cases:
        result = safe_multiply(value, multiplier)
        status = "✅" if abs(result - expected) < 0.001 else "❌"
        print(f"{status} safe_multiply({value}, {multiplier}) = {result} (ожидалось {expected})")
    
    # Тест fix_none_values_in_data
    print("\nТест fix_none_values_in_data:")
    test_data = {
        'contacts': [
            {'name': 'Test', 'confidence': None, 'score': 0.8},
            {'name': 'Test2', 'confidence': 0.9, 'score': None}
        ],
        'organizations': [
            {'name': 'Org', 'weight': None, 'value_score': 10}
        ]
    }
    
    print(f"До исправления: {test_data}")
    fixed_data = fix_none_values_in_data(test_data)
    print(f"После исправления: {fixed_data}")
    
    # Тест sanitize_json_fields
    print("\nТест sanitize_json_fields:")
    test_json = {
        'message_id_h极': 'test_value',
        'normal_field': 'normal_value',
        'interactions': [
            {'message_id_极': 'another_test'}
        ]
    }
    
    print(f"До очистки: {test_json}")
    sanitized_json = sanitize_json_fields(test_json)
    print(f"После очистки: {sanitized_json}")
    
    print("\n✅ Все тесты завершены")