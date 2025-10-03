#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Валидация ИНН

Модуль для валидации российских ИНН (Идентификационный Номер Налогоплательщика)
с поддержкой как юридических лиц (10 цифр), так и физических лиц/ИП (12 цифр).

Author: Contact Parser Team
Created: 2025-10-03
"""

import re
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class INNValidationResult:
    """Результат валидации ИНН"""
    valid: bool
    inn_type: Optional[str]  # 'legal' | 'individual' | None
    formatted_inn: Optional[str]
    error: Optional[str] = None


class RussianINNValidator:
    """Валидатор российских ИНН"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate(self, inn: str) -> INNValidationResult:
        """
        Валидация ИНН
        
        Args:
            inn: ИНН для валидации
            
        Returns:
            INNValidationResult: Результат валидации
        """
        if not inn:
            return INNValidationResult(
                valid=False,
                inn_type=None,
                formatted_inn=None,
                error="ИНН не задан"
            )
        
        # Очистка ИНН от пробелов и дефисов
        clean_inn = self._clean_inn(inn)
        
        # Проверка формата
        if not self._is_valid_format(clean_inn):
            return INNValidationResult(
                valid=False,
                inn_type=None,
                formatted_inn=None,
                error=f"Неверный формат ИНН: {inn}"
            )
        
        # Валидация по длине и контрольной сумме
        if len(clean_inn) == 10:
            # ИНН юридического лица
            if self._validate_legal_entity_inn(clean_inn):
                return INNValidationResult(
                    valid=True,
                    inn_type='legal',
                    formatted_inn=clean_inn
                )
            else:
                return INNValidationResult(
                    valid=False,
                    inn_type='legal',
                    formatted_inn=clean_inn,
                    error="Неверная контрольная сумма для ИНН юридического лица"
                )
        
        elif len(clean_inn) == 12:
            # ИНН физического лица/ИП
            if self._validate_individual_inn(clean_inn):
                return INNValidationResult(
                    valid=True,
                    inn_type='individual',
                    formatted_inn=clean_inn
                )
            else:
                return INNValidationResult(
                    valid=False,
                    inn_type='individual',
                    formatted_inn=clean_inn,
                    error="Неверная контрольная сумма для ИНН физического лица"
                )
        
        else:
            return INNValidationResult(
                valid=False,
                inn_type=None,
                formatted_inn=clean_inn,
                error=f"Неверная длина ИНН: {len(clean_inn)} (должно быть 10 или 12 цифр)"
            )
    
    def _clean_inn(self, inn: str) -> str:
        """Очистка ИНН от лишних символов"""
        # Удаляем все кроме цифр
        return re.sub(r'[^\d]', '', str(inn))
    
    def _is_valid_format(self, inn: str) -> bool:
        """Проверка базового формата ИНН"""
        # Должно содержать только цифры и быть нужной длины
        return inn.isdigit() and len(inn) in [10, 12]
    
    def _validate_legal_entity_inn(self, inn: str) -> bool:
        """
        Валидация ИНН юридического лица (10 цифр)
        
        Алгоритм проверки контрольной суммы для 10-значного ИНН:
        1. Умножаем каждую из первых 9 цифр на соответствующий коэффициент
        2. Складываем произведения
        3. Находим остаток от деления суммы на 11
        4. Если остаток больше 9, берем остаток от деления на 10
        5. Сравниваем с 10-й цифрой ИНН
        """
        if len(inn) != 10:
            return False
        
        # Коэффициенты для проверки 10-значного ИНН
        coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        
        try:
            # Вычисляем контрольную сумму
            check_sum = sum(
                int(inn[i]) * coefficients[i] 
                for i in range(9)
            ) % 11
            
            # Если остаток больше 9, берем остаток от деления на 10
            if check_sum > 9:
                check_sum %= 10
            
            # Сравниваем с последней цифрой
            return int(inn[9]) == check_sum
            
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Error validating legal entity INN {inn}: {e}")
            return False
    
    def _validate_individual_inn(self, inn: str) -> bool:
        """
        Валидация ИНН физического лица/ИП (12 цифр)
        
        Алгоритм проверки контрольных сумм для 12-значного ИНН:
        1. Проверяем 11-ю цифру используя первые 10 цифр
        2. Проверяем 12-ю цифру используя первые 11 цифр
        """
        if len(inn) != 12:
            return False
        
        try:
            # Первая контрольная сумма (11-я цифра)
            coefficients1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
            check_sum1 = sum(
                int(inn[i]) * coefficients1[i] 
                for i in range(10)
            ) % 11
            
            if check_sum1 > 9:
                check_sum1 %= 10
            
            if int(inn[10]) != check_sum1:
                return False
            
            # Вторая контрольная сумма (12-я цифра)
            coefficients2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
            check_sum2 = sum(
                int(inn[i]) * coefficients2[i] 
                for i in range(11)
            ) % 11
            
            if check_sum2 > 9:
                check_sum2 %= 10
            
            return int(inn[11]) == check_sum2
            
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Error validating individual INN {inn}: {e}")
            return False
    
    def is_valid(self, inn: str) -> bool:
        """
        Быстрая проверка валидности ИНН
        
        Args:
            inn: ИНН для проверки
            
        Returns:
            bool: True если ИНН валиден
        """
        return self.validate(inn).valid
    
    def get_inn_type(self, inn: str) -> Optional[str]:
        """
        Определение типа ИНН
        
        Args:
            inn: ИНН для анализа
            
        Returns:
            Optional[str]: 'legal' | 'individual' | None
        """
        result = self.validate(inn)
        return result.inn_type if result.valid else None
    
    def format_inn(self, inn: str) -> Optional[str]:
        """
        Форматирование ИНН (очистка от лишних символов)
        
        Args:
            inn: ИНН для форматирования
            
        Returns:
            Optional[str]: Отформатированный ИНН или None если невалиден
        """
        result = self.validate(inn)
        return result.formatted_inn if result.valid else None
    
    def validate_batch(self, inns: list) -> Dict[str, INNValidationResult]:
        """
        Валидация списка ИНН
        
        Args:
            inns: Список ИНН для валидации
            
        Returns:
            Dict[str, INNValidationResult]: Результаты валидации
        """
        results = {}
        
        for inn in inns:
            inn_str = str(inn) if inn is not None else ""
            results[inn_str] = self.validate(inn_str)
        
        return results


# Функции для обратной совместимости
def validate_inn(inn: str) -> bool:
    """Функция для обратной совместимости"""
    validator = RussianINNValidator()
    return validator.is_valid(inn)


def get_inn_info(inn: str) -> Dict[str, Any]:
    """Получение информации об ИНН"""
    validator = RussianINNValidator()
    result = validator.validate(inn)
    
    return {
        'valid': result.valid,
        'type': result.inn_type,
        'formatted': result.formatted_inn,
        'error': result.error
    }


# Экспорт основных классов и функций
__all__ = [
    'RussianINNValidator',
    'INNValidationResult', 
    'validate_inn',
    'get_inn_info'
]