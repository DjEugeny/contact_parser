#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⏱️ Утилита для динамического расчёта таймаутов LLM запросов
Задача 9.1: Реализация calculate_dynamic_timeout
"""

from typing import Dict, Any, Optional


def calculate_dynamic_timeout(
    text_length: int,
    attachments_count: int = 0,
    has_ocr: bool = False,
    base_timeout: int = 60,
    max_timeout: int = 300,
    model_context_window: Optional[int] = None
) -> int:
    """
    ⏱️ Расчёт динамического таймаута на основе характеристик запроса
    
    Логика расчёта:
    - Базовый таймаут: 60 секунд
    - +1 сек на каждые 1000 символов текста
    - +30 сек на каждое вложение
    - +30 сек если есть OCR
    - Для больших контекстных окон (>100k токенов): увеличенный максимум
    - Максимум: 300 секунд (5 минут) для обычных моделей
    - Максимум: 600 секунд (10 минут) для моделей с большим контекстом
    
    Args:
        text_length: Длина текста в символах
        attachments_count: Количество вложений
        has_ocr: Есть ли OCR текст
        base_timeout: Базовый таймаут в секундах (по умолчанию 60)
        max_timeout: Максимальный таймаут в секундах (по умолчанию 300)
        model_context_window: Размер контекстного окна модели в токенах (опционально)
    
    Returns:
        int: Рассчитанный таймаут в секундах
    
    Examples:
        >>> calculate_dynamic_timeout(5000, 0, False)
        65  # 60 + 5 (за 5000 символов)
        
        >>> calculate_dynamic_timeout(10000, 2, True)
        160  # 60 + 10 (за 10000 символов) + 60 (2 вложения) + 30 (OCR)
        
        >>> calculate_dynamic_timeout(100000, 5, True)
        300  # Ограничено максимумом
        
        >>> calculate_dynamic_timeout(125000, 3, True, model_context_window=1000000)
        345  # Для больших моделей максимум выше (600с)
    """
    timeout = base_timeout
    
    # +1 сек на каждые 1000 символов текста
    text_overhead = text_length // 1000
    timeout += text_overhead
    
    # +30 сек на каждое вложение
    attachments_overhead = attachments_count * 30
    timeout += attachments_overhead
    
    # +30 сек если есть OCR
    if has_ocr:
        timeout += 30
    
    # Для моделей с большим контекстным окном увеличиваем максимум
    effective_max_timeout = max_timeout
    if model_context_window and model_context_window > 100000:
        # Для моделей типа Gemini Flash 2.0 (1M токенов) - до 10 минут
        effective_max_timeout = 600
        print(f"   ℹ️ Модель с большим контекстом ({model_context_window} токенов), "
              f"максимальный таймаут увеличен до {effective_max_timeout}с")
    
    # Ограничиваем максимумом
    timeout = min(timeout, effective_max_timeout)
    
    return timeout


def calculate_timeout_from_email_data(email_data: Dict[str, Any]) -> int:
    """
    ⏱️ Расчёт таймаута на основе данных письма
    
    Args:
        email_data: Словарь с данными письма, содержащий:
            - combined_text_length или text_length: длина текста
            - attachments_processed или attachments: количество вложений
            - has_ocr или attachments_details: наличие OCR
    
    Returns:
        int: Рассчитанный таймаут в секундах
    
    Examples:
        >>> email_data = {
        ...     'combined_text_length': 5000,
        ...     'attachments_processed': 2,
        ...     'has_ocr': True
        ... }
        >>> calculate_timeout_from_email_data(email_data)
        125  # 60 + 5 + 60 + 30
    """
    # Определяем длину текста
    text_length = email_data.get('combined_text_length', 0)
    if text_length == 0:
        text_length = email_data.get('text_length', 0)
    if text_length == 0 and 'text' in email_data:
        text_length = len(email_data['text'])
    
    # Определяем количество вложений
    attachments_count = email_data.get('attachments_processed', 0)
    if attachments_count == 0:
        attachments = email_data.get('attachments', [])
        if isinstance(attachments, list):
            attachments_count = len(attachments)
    
    # Определяем наличие OCR
    has_ocr = email_data.get('has_ocr', False)
    if not has_ocr:
        # Проверяем наличие OCR текста в деталях вложений
        attachments_details = email_data.get('attachments_details', [])
        if isinstance(attachments_details, list):
            has_ocr = any(
                detail.get('ocr_text') or detail.get('extracted_text')
                for detail in attachments_details
                if isinstance(detail, dict)
            )
    
    return calculate_dynamic_timeout(
        text_length=text_length,
        attachments_count=attachments_count,
        has_ocr=has_ocr
    )


def get_timeout_breakdown(
    text_length: int,
    attachments_count: int = 0,
    has_ocr: bool = False
) -> Dict[str, Any]:
    """
    📊 Получить детальную разбивку расчёта таймаута
    
    Полезно для логирования и отладки
    
    Args:
        text_length: Длина текста в символах
        attachments_count: Количество вложений
        has_ocr: Есть ли OCR текст
    
    Returns:
        dict: Детальная информация о расчёте таймаута
    
    Examples:
        >>> breakdown = get_timeout_breakdown(5000, 2, True)
        >>> print(breakdown)
        {
            'base_timeout': 60,
            'text_overhead': 5,
            'attachments_overhead': 60,
            'ocr_overhead': 30,
            'total_timeout': 155,
            'capped': False,
            'breakdown_str': '60 (base) + 5 (text) + 60 (attachments) + 30 (OCR) = 155s'
        }
    """
    base_timeout = 60
    text_overhead = text_length // 1000
    attachments_overhead = attachments_count * 30
    ocr_overhead = 30 if has_ocr else 0
    
    total_before_cap = base_timeout + text_overhead + attachments_overhead + ocr_overhead
    total_timeout = min(total_before_cap, 300)
    capped = total_before_cap > 300
    
    # Формируем строку разбивки
    parts = [f"{base_timeout} (base)"]
    if text_overhead > 0:
        parts.append(f"{text_overhead} (text)")
    if attachments_overhead > 0:
        parts.append(f"{attachments_overhead} (attachments)")
    if ocr_overhead > 0:
        parts.append(f"{ocr_overhead} (OCR)")
    
    breakdown_str = " + ".join(parts) + f" = {total_timeout}s"
    if capped:
        breakdown_str += " (capped at 300s)"
    
    return {
        'base_timeout': base_timeout,
        'text_overhead': text_overhead,
        'attachments_overhead': attachments_overhead,
        'ocr_overhead': ocr_overhead,
        'total_timeout': total_timeout,
        'capped': capped,
        'breakdown_str': breakdown_str
    }
