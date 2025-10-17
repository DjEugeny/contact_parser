#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Утилита для определения личных email доменов.

Используется для различения личных и корпоративных email адресов
в системе дедупликации контактов (GID v2).
"""

from pathlib import Path
from typing import Set

# Путь к файлу с whitelist
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
PERSONAL_DOMAINS_FILE = CONFIG_DIR / "personal_email_domains.txt"


class PersonalEmailDomains:
    """
    📧 Менеджер списка личных email доменов.
    
    Загружает whitelist из config/personal_email_domains.txt
    и предоставляет быстрый метод проверки домена.
    """
    
    def __init__(self, domains_file: Path = PERSONAL_DOMAINS_FILE):
        """
        Инициализирует менеджер.
        
        Args:
            domains_file: Путь к файлу с whitelist доменов
        """
        self.domains_file = domains_file
        self._domains: Set[str] = set()
        self._load_domains()
    
    def _load_domains(self) -> None:
        """
        🔍 Загружает список доменов из файла.
        
        Игнорирует:
        - Пустые строки
        - Комментарии (начинаются с #)
        - Whitespace в начале/конце
        """
        if not self.domains_file.exists():
            # Если файл не найден, используем минимальный набор
            self._domains = {
                "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                "mail.ru", "yandex.ru", "ya.ru", "bk.ru", "inbox.ru"
            }
            return
        
        with open(self.domains_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                
                # Пропускаем пустые строки и комментарии
                if not line or line.startswith("#"):
                    continue
                
                # Нормализуем домен (lowercase)
                domain = line.lower()
                self._domains.add(domain)
    
    def is_personal(self, email: str) -> bool:
        """
        ✅ Проверяет, является ли email личным.
        
        Args:
            email: Email адрес для проверки
        
        Returns:
            True если домен в whitelist, False иначе
        
        Examples:
            >>> manager = PersonalEmailDomains()
            >>> manager.is_personal("user@gmail.com")
            True
            >>> manager.is_personal("user@company.com")
            False
        """
        if not email or "@" not in email:
            return False
        
        # Извлекаем домен
        domain = email.split("@")[-1].lower().strip()
        
        return domain in self._domains
    
    def is_corporate(self, email: str) -> bool:
        """
        🏢 Проверяет, является ли email корпоративным.
        
        Args:
            email: Email адрес для проверки
        
        Returns:
            True если домен НЕ в whitelist, False иначе
        """
        return not self.is_personal(email)
    
    def get_domain(self, email: str) -> str:
        """
        🔍 Извлекает домен из email.
        
        Args:
            email: Email адрес
        
        Returns:
            Домен в lowercase или пустая строка
        """
        if not email or "@" not in email:
            return ""
        
        return email.split("@")[-1].lower().strip()
    
    def reload(self) -> None:
        """
        🔄 Перезагружает список доменов из файла.
        
        Полезно если файл был обновлён во время работы программы.
        """
        self._domains.clear()
        self._load_domains()
    
    @property
    def domains(self) -> Set[str]:
        """Возвращает копию множества доменов."""
        return self._domains.copy()
    
    def __len__(self) -> int:
        """Возвращает количество доменов в whitelist."""
        return len(self._domains)
    
    def __contains__(self, domain: str) -> bool:
        """Позволяет использовать оператор 'in'."""
        return domain.lower() in self._domains


# Singleton instance для использования в других модулях
_personal_domains_instance: PersonalEmailDomains | None = None


def get_personal_domains() -> PersonalEmailDomains:
    """
    🌍 Возвращает singleton instance PersonalEmailDomains.
    
    Returns:
        Глобальный экземпляр менеджера доменов
    """
    global _personal_domains_instance
    
    if _personal_domains_instance is None:
        _personal_domains_instance = PersonalEmailDomains()
    
    return _personal_domains_instance


def is_personal_email(email: str) -> bool:
    """
    ✅ Быстрая проверка, является ли email личным.
    
    Args:
        email: Email адрес для проверки
    
    Returns:
        True если домен в whitelist, False иначе
    
    Examples:
        >>> is_personal_email("user@gmail.com")
        True
        >>> is_personal_email("user@company.com")
        False
    """
    return get_personal_domains().is_personal(email)


def is_corporate_email(email: str) -> bool:
    """
    🏢 Быстрая проверка, является ли email корпоративным.
    
    Args:
        email: Email адрес для проверки
    
    Returns:
        True если домен НЕ в whitelist, False иначе
    """
    return get_personal_domains().is_corporate(email)
