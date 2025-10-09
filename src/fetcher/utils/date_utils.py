"""
Date utilities for email processing.

Утилиты для работы с датами в email.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

# Настройка местного времени UTC+7
LOCAL_TIMEZONE = timezone(timedelta(hours=7))


def get_local_time(dt: Optional[datetime] = None) -> datetime:
    """
    Получение местного времени UTC+7.
    
    Args:
        dt: Опциональная дата для конвертации
        
    Returns:
        Дата в местном часовом поясе
    """
    if dt is None:
        dt = datetime.now(LOCAL_TIMEZONE)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TIMEZONE)
    return dt


def parse_email_date(date_header: str) -> datetime:
    """
    Парсинг даты письма из заголовка с приведением к UTC+7.
    
    Args:
        date_header: Заголовок Date
        
    Returns:
        Дата в местном часовом поясе
    """
    try:
        import email.utils
        parsed_date = email.utils.parsedate_to_datetime(date_header)
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        local_date = parsed_date.astimezone(LOCAL_TIMEZONE)
        return local_date
    except Exception as e:
        # В случае ошибки возвращаем текущее время
        return get_local_time()


def format_email_date_for_log(date_header: str) -> str:
    """
    Форматирование даты письма для лога.
    
    Args:
        date_header: Заголовок Date
        
    Returns:
        Отформатированная строка даты
    """
    try:
        email_date = parse_email_date(date_header)
        return email_date.strftime("%Y.%m.%d %H:%M")
    except:
        return "неизвестная дата"


def parse_date_flexible(date_str: str) -> datetime:
    """
    Парсинг даты в различных форматах.
    
    Поддерживаемые форматы:
    - 2025-07-12 (ISO формат)
    - 12.07.2025 (точки)
    - 12-7-25 (короткий формат)
    - 12 июля 25 (текстовый формат на русском)
    
    Args:
        date_str: Строка с датой
        
    Returns:
        datetime объект
        
    Raises:
        ValueError: Если формат даты не распознан
    """
    date_str = date_str.strip()
    
    # Формат: 2025-07-12 (ISO)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass
    
    # Формат: 12.07.2025
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        pass
    
    # Формат: 12-7-25
    try:
        dt = datetime.strptime(date_str, "%d-%m-%y")
        # Корректируем год (25 → 2025)
        if dt.year < 2000:
            dt = dt.replace(year=dt.year + 2000)
        return dt
    except ValueError:
        pass
    
    # Формат: 12 июля 25
    months_ru = {
        "января": 1,
        "февраля": 2,
        "марта": 3,
        "апреля": 4,
        "мая": 5,
        "июня": 6,
        "июля": 7,
        "августа": 8,
        "сентября": 9,
        "октября": 10,
        "ноября": 11,
        "декабря": 12,
    }
    
    pattern = r"(\d{1,2})\s+(\w+)\s+(\d{2,4})"
    match = re.match(pattern, date_str.lower())
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))
        
        if month_name in months_ru:
            month = months_ru[month_name]
            if year < 100:
                year += 2000
            return datetime(year, month, day)
    
    raise ValueError(f"Не удалось распознать формат даты: {date_str}")