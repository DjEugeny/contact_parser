#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Email Body Extractor - централизованная утилита для извлечения body письма

Поддерживает:
- Legacy format: "body"
- New format: "body_raw", "body_clean"
- Alternative formats: "body_plain", "body_text", "text"

Создано: 2025-10-15
Задача: 2.2 из data-quality-regression-analysis-2025-10-15/tasks.md
"""

from typing import Dict, Any, Optional, List, Tuple


def extract_body_with_fallback(
    email_data: Dict[str, Any],
    prefer_clean: bool = True,
    return_source: bool = False
) -> Optional[str] | Tuple[Optional[str], Optional[str]]:
    """
    📝 Извлекает body письма с поддержкой legacy и новых форматов.
    
    Функция проверяет несколько возможных полей в порядке приоритета
    и возвращает первое найденное непустое значение.
    
    Args:
        email_data: Данные письма (dict)
        prefer_clean: Если True, приоритет у body_clean над body_raw
                     Если False, приоритет у body_raw над body_clean
        return_source: Если True, возвращает tuple (body, source_field_name)
                      Если False, возвращает только body
        
    Returns:
        str or None: Текст письма или None если не найдено
        или
        tuple(str or None, str or None): (body, source_field_name) если return_source=True
        
    Examples:
        >>> # Legacy format
        >>> email_data = {"body": "Hello world"}
        >>> extract_body_with_fallback(email_data)
        'Hello world'
        
        >>> # New format
        >>> email_data = {"body_clean": "Clean text", "body_raw": "Raw text"}
        >>> extract_body_with_fallback(email_data, prefer_clean=True)
        'Clean text'
        
        >>> # With source info
        >>> extract_body_with_fallback(email_data, return_source=True)
        ('Clean text', 'body_clean')
    """
    if prefer_clean:
        body_candidates = [
            ("body", email_data.get("body")),                    # legacy (для совместимости)
            ("body_clean", email_data.get("body_clean")),        # NEW (приоритет - очищенный)
            ("body_raw", email_data.get("body_raw")),            # NEW (fallback - сырой)
            ("body_plain", email_data.get("body_plain")),
            ("body_text", email_data.get("body_text")),
            ("text", email_data.get("text")),
        ]
    else:
        body_candidates = [
            ("body", email_data.get("body")),                    # legacy
            ("body_raw", email_data.get("body_raw")),            # NEW (приоритет - сырой)
            ("body_clean", email_data.get("body_clean")),        # NEW (fallback - очищенный)
            ("body_plain", email_data.get("body_plain")),
            ("body_text", email_data.get("body_text")),
            ("text", email_data.get("text")),
        ]
    
    for field_name, candidate in body_candidates:
        if candidate and isinstance(candidate, str) and candidate.strip():
            if return_source:
                return candidate, field_name
            return candidate
    
    if return_source:
        return None, None
    return None


def extract_all_text_sources(
    email_data: Dict[str, Any],
    include_plain_text: bool = True
) -> List[str]:
    """
    📝 Извлекает все доступные текстовые источники из письма.
    
    Полезно когда нужно искать информацию во всех возможных полях
    (например, при извлечении email-адресов из подписи).
    
    Args:
        email_data: Данные письма
        include_plain_text: Включать ли поле 'plain_text' в результат
        
    Returns:
        List[str]: Список всех найденных текстовых блоков
        
    Examples:
        >>> email_data = {
        ...     "body_clean": "Main text",
        ...     "body_raw": "Raw text",
        ...     "plain_text": "Plain text"
        ... }
        >>> extract_all_text_sources(email_data)
        ['Main text', 'Raw text', 'Plain text']
    """
    text_sources = []
    
    # Основное тело письма (берём первое найденное)
    body = extract_body_with_fallback(email_data, prefer_clean=True)
    if body:
        text_sources.append(body)
    
    # Дополнительно: plain_text если есть и отличается от body
    if include_plain_text:
        plain_text = email_data.get('plain_text')
        if plain_text and isinstance(plain_text, str) and plain_text.strip():
            # Добавляем только если это не дубликат
            if not body or plain_text != body:
                text_sources.append(plain_text)
    
    return text_sources


def get_body_field_priority(prefer_clean: bool = True) -> List[str]:
    """
    📋 Возвращает список полей в порядке приоритета.
    
    Полезно для документации и отладки.
    
    Args:
        prefer_clean: Приоритет clean над raw
        
    Returns:
        List[str]: Список имён полей в порядке приоритета
        
    Examples:
        >>> get_body_field_priority(prefer_clean=True)
        ['body', 'body_clean', 'body_raw', 'body_plain', 'body_text', 'text']
    """
    if prefer_clean:
        return ["body", "body_clean", "body_raw", "body_plain", "body_text", "text"]
    else:
        return ["body", "body_raw", "body_clean", "body_plain", "body_text", "text"]


def validate_email_data_structure(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ✅ Валидирует структуру email_data и возвращает отчёт.
    
    Проверяет наличие хотя бы одного поля body и возвращает
    детальную информацию о доступных полях.
    
    Args:
        email_data: Данные письма для проверки
        
    Returns:
        Dict с информацией:
        - has_body: bool - есть ли хотя бы одно поле body
        - available_fields: List[str] - список найденных полей
        - recommended_field: str or None - рекомендуемое поле для использования
        - warnings: List[str] - список предупреждений
        
    Examples:
        >>> email_data = {"body_clean": "text"}
        >>> result = validate_email_data_structure(email_data)
        >>> result['has_body']
        True
        >>> result['recommended_field']
        'body_clean'
    """
    body_fields = ["body", "body_clean", "body_raw", "body_plain", "body_text", "text"]
    
    available_fields = []
    for field in body_fields:
        value = email_data.get(field)
        if value and isinstance(value, str) and value.strip():
            available_fields.append(field)
    
    has_body = len(available_fields) > 0
    recommended_field = available_fields[0] if available_fields else None
    
    warnings = []
    if not has_body:
        warnings.append("⚠️ Не найдено ни одного поля body!")
    elif "body" not in available_fields and "body_clean" not in available_fields and "body_raw" not in available_fields:
        warnings.append("⚠️ Найдены только альтернативные поля (body_plain, body_text, text)")
    
    return {
        "has_body": has_body,
        "available_fields": available_fields,
        "recommended_field": recommended_field,
        "warnings": warnings,
        "field_count": len(available_fields)
    }


# Алиас для обратной совместимости с существующим кодом
def extract_email_body(email_data: Dict[str, Any]) -> str:
    """
    📝 Алиас для extract_body_with_fallback() с настройками по умолчанию.
    
    Для обратной совместимости с существующим кодом в file_tokens.py
    
    Args:
        email_data: Данные письма
        
    Returns:
        str: Текст письма или пустая строка
    """
    body = extract_body_with_fallback(email_data, prefer_clean=True)
    return body if body else ""


if __name__ == "__main__":
    # 🧪 Простые тесты для проверки
    print("🧪 Тестирование email_body_extractor.py\n")
    
    # Тест 1: Legacy format
    print("Тест 1: Legacy format")
    email_legacy = {"body": "Legacy body text"}
    result = extract_body_with_fallback(email_legacy, return_source=True)
    print(f"  Результат: {result}")
    assert result == ("Legacy body text", "body"), "Тест 1 провален!"
    print("  ✅ Пройден\n")
    
    # Тест 2: New format (prefer_clean=True)
    print("Тест 2: New format (prefer_clean=True)")
    email_new = {"body_clean": "Clean text", "body_raw": "Raw text"}
    result = extract_body_with_fallback(email_new, prefer_clean=True, return_source=True)
    print(f"  Результат: {result}")
    assert result == ("Clean text", "body_clean"), "Тест 2 провален!"
    print("  ✅ Пройден\n")
    
    # Тест 3: New format (prefer_clean=False)
    print("Тест 3: New format (prefer_clean=False)")
    result = extract_body_with_fallback(email_new, prefer_clean=False, return_source=True)
    print(f"  Результат: {result}")
    assert result == ("Raw text", "body_raw"), "Тест 3 провален!"
    print("  ✅ Пройден\n")
    
    # Тест 4: Пустые данные
    print("Тест 4: Пустые данные")
    email_empty = {}
    result = extract_body_with_fallback(email_empty)
    print(f"  Результат: {result}")
    assert result is None, "Тест 4 провален!"
    print("  ✅ Пройден\n")
    
    # Тест 5: extract_all_text_sources
    print("Тест 5: extract_all_text_sources")
    email_multi = {
        "body_clean": "Clean",
        "body_raw": "Raw",
        "plain_text": "Plain"
    }
    result = extract_all_text_sources(email_multi)
    print(f"  Результат: {result}")
    assert len(result) == 2, "Тест 5 провален!"  # body_clean + plain_text (body_raw пропущен)
    print("  ✅ Пройден\n")
    
    # Тест 6: validate_email_data_structure
    print("Тест 6: validate_email_data_structure")
    validation = validate_email_data_structure(email_new)
    print(f"  Результат: {validation}")
    assert validation['has_body'] == True, "Тест 6 провален!"
    assert validation['recommended_field'] == 'body_clean', "Тест 6 провален!"
    print("  ✅ Пройден\n")
    
    print("🎉 Все тесты пройдены!")
