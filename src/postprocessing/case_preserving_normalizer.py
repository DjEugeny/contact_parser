#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔤 Нормализатор с сохранением регистра
Интеллектуальная нормализация текста с сохранением важных паттернов регистра

Author: Contact Parser Team
Created: 2025-09-29
"""

import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class NormalizationConfig:
    """Конфигурация для нормализации с сохранением регистра"""
    preserve_abbreviations: bool = True
    preserve_titles: bool = True
    preserve_organization_names: bool = True
    preserve_positions: bool = True
    
    # Паттерны для сохранения регистра
    abbreviation_patterns: List[str] = field(default_factory=lambda: [
        r'\b[А-ЯЁ]{2,}\b',  # КДЛ, ОМТС, ООО, РФ
        r'\b[A-Z]{2,}\b',   # LLC, INC, CEO, USA
        r'\b[А-ЯЁ]{1,3}\.[А-ЯЁ]{1,3}\.?\b',  # И.О., А.С.
        r'\b[A-Z]{1,3}\.[A-Z]{1,3}\.?\b',     # J.D., Ph.D.
    ])
    
    title_patterns: List[str] = field(default_factory=lambda: [
        r'\b[А-ЯЁ][а-яё]+\b',  # Медицина, Заведующая, Директор
        r'\b[A-Z][a-z]+\b',    # Manager, Director, Medicine
    ])
    
    # Специальные случаи для сохранения
    special_cases: Dict[str, str] = field(default_factory=lambda: {
        # Аббревиатуры организаций
        'ооо': 'ООО',
        'зао': 'ЗАО', 
        'оао': 'ОАО',
        'пао': 'ПАО',
        'ао': 'АО',
        'ип': 'ИП',
        'тоо': 'ТОО',
        'llc': 'LLC',
        'ltd': 'Ltd',
        'inc': 'Inc',
        
        # Медицинские аббревиатуры
        'кдл': 'КДЛ',
        'омтс': 'ОМТС',
        'узи': 'УЗИ',
        'мрт': 'МРТ',
        'кт': 'КТ',
        'экг': 'ЭКГ',
        
        # Английские должности
        'ceo': 'CEO',
        'cto': 'CTO',
        'cfo': 'CFO',
        'hr': 'HR',
        'it': 'IT',
        'pr': 'PR',
        
        # Должности и отделы
        'медицина': 'Медицина',
        'заведующая': 'Заведующая',
        'заведующий': 'Заведующий',
        'директор': 'Директор',
        'менеджер': 'Менеджер',
        'руководитель': 'Руководитель',
    })


class CasePreservingNormalizer:
    """
    🔤 Нормализатор с сохранением регистра
    
    Выполняет интеллектуальную нормализацию текста, сохраняя важные
    паттерны регистра для аббревиатур, названий и должностей.
    """
    
    def __init__(self, config: Optional[NormalizationConfig] = None):
        """
        Инициализация нормализатора
        
        Args:
            config: Конфигурация нормализации
        """
        self.config = config or NormalizationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Компилируем регулярные выражения для производительности
        self._abbreviation_regexes = [
            re.compile(pattern, re.UNICODE) 
            for pattern in self.config.abbreviation_patterns
        ]
        self._title_regexes = [
            re.compile(pattern, re.UNICODE) 
            for pattern in self.config.title_patterns
        ]
    
    def normalize_preserving_case(self, text: str, field_type: str = 'general') -> str:
        """
        Нормализация с сохранением важного регистра
        
        Args:
            text: Исходный текст
            field_type: Тип поля ('position', 'organization', 'name', 'general')
            
        Returns:
            str: Нормализованный текст с сохраненным регистром
        """
        if not text or not isinstance(text, str):
            return ''
        
        # Убираем лишние пробелы
        normalized = ' '.join(text.strip().split())
        
        # Применяем специфичную для типа поля логику
        if field_type == 'position':
            normalized = self._normalize_position_preserving_case(normalized)
        elif field_type == 'organization':
            normalized = self._normalize_organization_preserving_case(normalized)
        elif field_type == 'name':
            normalized = self._normalize_name_preserving_case(normalized)
        else:
            normalized = self._normalize_general_preserving_case(normalized)
        
        return normalized
    
    def _normalize_position_preserving_case(self, text: str) -> str:
        """Нормализация должности с сохранением регистра"""
        if not self.config.preserve_positions:
            return text.lower().capitalize()
        
        # Сохраняем исходный текст для анализа
        original_words = text.split()
        normalized_words = []
        
        for word in original_words:
            # Проверяем специальные случаи
            word_lower = word.lower().rstrip('.,;:')
            if word_lower in self.config.special_cases:
                normalized_words.append(self.config.special_cases[word_lower])
            # Проверяем аббревиатуры
            elif self._is_abbreviation(word):
                normalized_words.append(word.upper())
            # Проверяем названия/титулы
            elif self._is_title(word):
                normalized_words.append(word.capitalize())
            else:
                # Обычное слово - первая буква заглавная
                normalized_words.append(word.lower().capitalize())
        
        return ' '.join(normalized_words)
    
    def _normalize_organization_preserving_case(self, text: str) -> str:
        """Нормализация названия организации с сохранением регистра"""
        if not self.config.preserve_organization_names:
            return text.lower()
        
        original_words = text.split()
        normalized_words = []
        
        for word in original_words:
            word_clean = word.lower().rstrip('.,;:"()[]')
            
            # Специальные случаи (ООО, ЗАО и т.д.) - только если сохранение включено
            if (self.config.preserve_abbreviations and 
                word_clean in self.config.special_cases and
                self.config.special_cases[word_clean].isupper()):
                normalized_words.append(self.config.special_cases[word_clean])
            # Специальные случаи для названий (Медицина и т.д.)
            elif (self.config.preserve_organization_names and 
                  word_clean in self.config.special_cases and
                  not self.config.special_cases[word_clean].isupper()):
                normalized_words.append(self.config.special_cases[word_clean])
            # Аббревиатуры
            elif self._is_abbreviation(word):
                normalized_words.append(word.upper())
            # Названия отделов/направлений
            elif self._is_title(word):
                normalized_words.append(word.capitalize())
            else:
                # Обычные слова в названиях организаций
                normalized_words.append(word.lower().capitalize())
        
        return ' '.join(normalized_words)
    
    def _normalize_name_preserving_case(self, text: str) -> str:
        """Нормализация имени с сохранением регистра"""
        if not self.config.preserve_titles:
            return text.lower()
        
        original_words = text.split()
        normalized_words = []
        
        for word in original_words:
            word_clean = word.lower().rstrip('.,;:')
            
            # Инициалы и аббревиатуры в именах
            if self._is_abbreviation(word) or '.' in word:
                normalized_words.append(word.upper())
            # Специальные случаи
            elif word_clean in self.config.special_cases:
                normalized_words.append(self.config.special_cases[word_clean])
            else:
                # Обычные части имени
                normalized_words.append(word.lower().capitalize())
        
        return ' '.join(normalized_words)
    
    def _normalize_general_preserving_case(self, text: str) -> str:
        """Общая нормализация с сохранением регистра"""
        original_words = text.split()
        normalized_words = []
        
        for word in original_words:
            word_clean = word.lower().rstrip('.,;:"()[]')
            
            # Специальные случаи
            if word_clean in self.config.special_cases:
                normalized_words.append(self.config.special_cases[word_clean])
            # Аббревиатуры
            elif self._is_abbreviation(word):
                normalized_words.append(word.upper())
            # Названия
            elif self._is_title(word):
                normalized_words.append(word.capitalize())
            else:
                normalized_words.append(word.lower())
        
        return ' '.join(normalized_words)
    
    def _is_abbreviation(self, word: str) -> bool:
        """Проверка является ли слово аббревиатурой"""
        if not self.config.preserve_abbreviations:
            return False
        
        # Убираем знаки препинания для проверки
        clean_word = word.rstrip('.,;:"()[]')
        
        # Проверяем специальные случаи сначала
        word_lower = clean_word.lower()
        if word_lower in self.config.special_cases:
            return True
        
        # Проверяем по регулярным выражениям
        for regex in self._abbreviation_regexes:
            if regex.match(clean_word):
                return True
        
        # Дополнительные эвристики
        # Короткие слова из заглавных букв
        if len(clean_word) <= 5 and clean_word.isupper() and clean_word.isalpha():
            return True
        
        # Слова с точками (инициалы)
        if '.' in clean_word and len(clean_word) <= 6:
            return True
        
        # Известные аббревиатуры в нижнем регистре
        known_abbreviations = ['ceo', 'cto', 'cfo', 'hr', 'it', 'pr']
        if word_lower in known_abbreviations:
            return True
        
        return False
    
    def _is_title(self, word: str) -> bool:
        """Проверка является ли слово названием/титулом"""
        if not self.config.preserve_titles:
            return False
        
        clean_word = word.rstrip('.,;:"()[]')
        
        # Проверяем по регулярным выражениям
        for regex in self._title_regexes:
            if regex.match(clean_word):
                return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики работы нормализатора"""
        return {
            'config': {
                'preserve_abbreviations': self.config.preserve_abbreviations,
                'preserve_titles': self.config.preserve_titles,
                'preserve_organization_names': self.config.preserve_organization_names,
                'preserve_positions': self.config.preserve_positions,
            },
            'patterns': {
                'abbreviation_patterns_count': len(self.config.abbreviation_patterns),
                'title_patterns_count': len(self.config.title_patterns),
                'special_cases_count': len(self.config.special_cases),
            }
        }


# Глобальный экземпляр для удобства использования
default_normalizer = CasePreservingNormalizer()


def normalize_preserving_case(text: str, field_type: str = 'general') -> str:
    """
    Удобная функция для нормализации с сохранением регистра
    
    Args:
        text: Исходный текст
        field_type: Тип поля ('position', 'organization', 'name', 'general')
        
    Returns:
        str: Нормализованный текст
    """
    return default_normalizer.normalize_preserving_case(text, field_type)


# Пример использования
if __name__ == "__main__":
    # Тестовые примеры
    test_cases = [
        ("КДЛ", "organization"),
        ("ОМТС", "organization"), 
        ("Медицина", "organization"),
        ("Заведующая", "position"),
        ("ООО Рога и Копыта", "organization"),
        ("Генеральный директор", "position"),
        ("И.И. Иванов", "name"),
    ]
    
    normalizer = CasePreservingNormalizer()
    
    print("🔤 Тестирование CasePreservingNormalizer:")
    for text, field_type in test_cases:
        result = normalizer.normalize_preserving_case(text, field_type)
        print(f"  {text} ({field_type}) → {result}")