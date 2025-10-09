"""
Email utilities for processing email headers and addresses.

Утилиты для работы с email заголовками и адресами.
"""

import re
import hashlib
from typing import List, Optional
from email.header import decode_header, make_header
from email.utils import getaddresses

from .date_utils import parse_email_date


def decode_header_value(val: str) -> str:
    """
    Декодирование MIME-заголовков с правильным извлечением email.
    
    Args:
        val: Значение заголовка
        
    Returns:
        Декодированное значение
    """
    try:
        decoded = str(make_header(decode_header(val or "")))
        
        # Правильное извлечение email из угловых скобок
        email_match = re.search(r"<([^>]+)>", decoded)
        if email_match:
            return email_match.group(1).strip()
        else:
            # Если нет скобок, ищем email в строке
            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            email_match = re.search(email_pattern, decoded)
            return email_match.group(0).strip() if email_match else decoded.strip()
    except Exception:
        return val or ""


def parse_recipients(recipients_str: str) -> List[str]:
    """
    Парсинг списка получателей.
    
    Args:
        recipients_str: Строка с получателями
        
    Returns:
        Список email адресов
    """
    if not recipients_str:
        return []
    
    # Простой парсинг email адресов
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_pattern, recipients_str)
    return emails


def generate_thread_id(from_addr: str, subject: str, date: str) -> str:
    """
    Генерация уникального ID треда.
    
    Args:
        from_addr: Email отправителя
        subject: Тема письма
        date: Дата письма
        
    Returns:
        Уникальный ID треда
    """
    try:
        clean_subject = re.sub(
            r"^(Re:|Fwd:|Fw:)\s*", "", subject, flags=re.IGNORECASE
        ).strip()
        sender_match = re.search(r"@([^>\s]+)", from_addr)
        domain = sender_match.group(1) if sender_match else "unknown"
        hash_base = f"{domain}_{clean_subject}_{date[:10]}"
        hash_obj = hashlib.md5(hash_base.encode("utf-8"))
        email_date = parse_email_date(date)
        date_part = email_date.strftime("%Y%m%d")
        short_hash = hash_obj.hexdigest()[:8]
        return f"{date_part}_{domain.replace('.', '_')}_{short_hash}"
    except:
        from .date_utils import get_local_time
        return f"unknown_{get_local_time().strftime('%Y%m%d_%H%M%S')}"


def extract_message_id(raw_message_id: str) -> str:
    """
    Извлечение чистого Message-ID из заголовка.
    
    Args:
        raw_message_id: Сырой Message-ID
        
    Returns:
        Чистый Message-ID
    """
    if not raw_message_id:
        return ""
    
    # Удаляем угловые скобки
    message_id = raw_message_id.strip("<>")
    
    # Дополнительная очистка
    message_id = message_id.strip()
    
    return message_id


def is_valid_email(email: str) -> bool:
    """
    Проверка корректности email адреса.
    
    Args:
        email: Email адрес для проверки
        
    Returns:
        True если адрес корректный
    """
    if not email:
        return False
    
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_pattern, email.strip()))


def extract_domain_from_email(email: str) -> Optional[str]:
    """
    Извлечение домена из email адреса.
    
    Args:
        email: Email адрес
        
    Returns:
        Домен или None
    """
    if not email:
        return None
    
    try:
        domain_match = re.search(r"@([^>\s]+)", email)
        return domain_match.group(1) if domain_match else None
    except:
        return None


def normalize_email_address(email: str) -> str:
    """
    Нормализация email адреса.
    
    Args:
        email: Email адрес
        
    Returns:
        Нормализованный email
    """
    if not email:
        return ""
    
    # Приводим к нижнему регистру и убираем пробелы
    email = email.lower().strip()
    
    # Удаляем лишние символы
    email = re.sub(r"[<>]", "", email)
    
    return email


def parse_email_list(email_string: str) -> List[str]:
    """
    Парсинг списка email адресов из строки.
    
    Args:
        email_string: Строка с email адресами
        
    Returns:
        Список нормализованных email адресов
    """
    if not email_string:
        return []
    
    # Используем email.utils для парсинга
    addresses = getaddresses([email_string])
    
    # Нормализуем каждый адрес
    normalized_emails = []
    for name, addr in addresses:
        if addr and is_valid_email(addr):
            normalized_emails.append(normalize_email_address(addr))
    
    return normalized_emails