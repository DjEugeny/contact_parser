"""
Валидатор российских ИНН
Реализует алгоритмы проверки ИНН юридических лиц и индивидуальных предпринимателей
согласно требованиям ФНС РФ.

Author: Contact Parser Team
Created: 2025-09-08
"""

from typing import Dict, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class RussianINNValidator:
    """
    Валидатор российских ИНН (Идентификационных номеров налогоплательщиков)
    
    Поддерживает:
    - ИНН юридических лиц (10 цифр)
    - ИНН индивидуальных предпринимателей (12 цифр)
    - Проверку контрольных сумм по алгоритму ФНС
    """
    
    # Весовые коэффициенты для проверки контрольных сумм
    ORGANIZATION_WEIGHTS = [2, 4, 10, 3, 5, 9, 4, 6, 8, 0]
    INDIVIDUAL_WEIGHTS_1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0]
    INDIVIDUAL_WEIGHTS_2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0]
    
    def __init__(self):
        """Инициализация валидатора"""
        self.logger = logging.getLogger(__name__)
    
    def validate_inn(self, inn: str) -> Dict[str, any]:
        """
        Полная валидация ИНН
        
        Args:
            inn (str): ИНН для проверки
            
        Returns:
            dict: Результат валидации с деталями
        """
        if not inn or not isinstance(inn, str):
            return {
                "is_valid": False,
                "type": None,
                "error": "ИНН не указан или имеет неверный тип",
                "inn": inn
            }
        
        # Очистка от пробелов и других символов
        inn_clean = re.sub(r'\D', '', inn)
        
        # Проверка длины
        if len(inn_clean) == 10:
            return self._validate_organization_inn(inn_clean)
        elif len(inn_clean) == 12:
            return self._validate_individual_inn(inn_clean)
        else:
            return {
                "is_valid": False,
                "type": "invalid",
                "error": f"ИНН должен содержать 10 или 12 цифр, получено: {len(inn_clean)}",
                "inn": inn,
                "cleaned_inn": inn_clean
            }
    
    def _validate_organization_inn(self, inn: str) -> Dict[str, any]:
        """
        Валидация ИНН юридического лица (10 цифр)
        
        Алгоритм ФНС:
        1. Каждая цифра умножается на весовой коэффициент
        2. Сумма произведений вычисляется по модулю 11
        3. Остаток должен совпадать с контрольной цифрой
        """
        if len(inn) != 10:
            return {
                "is_valid": False,
                "type": "organization",
                "error": "ИНН организации должен содержать 10 цифр",
                "inn": inn
            }
        
        try:
            digits = [int(d) for d in inn]
            
            # Расчет контрольной суммы
            control_sum = 0
            for i in range(9):  # Первые 9 цифр
                control_sum += digits[i] * self.ORGANIZATION_WEIGHTS[i]
            
            control_digit = control_sum % 11
            if control_digit > 9:
                control_digit = control_digit % 10
            
            # Проверка совпадения с 10-й цифрой
            is_valid = control_digit == digits[9]
            
            return {
                "is_valid": is_valid,
                "type": "organization",
                "inn": inn,
                "control_sum": control_sum,
                "calculated_control": control_digit,
                "actual_control": digits[9],
                "error": None if is_valid else f"Неверная контрольная цифра. Ожидалось: {control_digit}, получено: {digits[9]}"
            }
            
        except (ValueError, IndexError) as e:
            return {
                "is_valid": False,
                "type": "organization",
                "error": f"Ошибка при обработке ИНН: {str(e)}",
                "inn": inn
            }
    
    def _validate_individual_inn(self, inn: str) -> Dict[str, any]:
        """
        Валидация ИНН индивидуального предпринимателя (12 цифр)
        
        Алгоритм ФНС:
        1. Первая контрольная цифра рассчитывается по первым 10 цифрам
        2. Вторая контрольная цифра рассчитывается по всем 11 цифрам
        """
        if len(inn) != 12:
            return {
                "is_valid": False,
                "type": "individual",
                "error": "ИНН ИП должен содержать 12 цифр",
                "inn": inn
            }
        
        try:
            digits = [int(d) for d in inn]
            
            # Первая контрольная цифра (11-я позиция)
            control_sum_1 = 0
            for i in range(10):  # Первые 10 цифр
                control_sum_1 += digits[i] * self.INDIVIDUAL_WEIGHTS_1[i]
            
            control_digit_1 = control_sum_1 % 11
            if control_digit_1 > 9:
                control_digit_1 = control_digit_1 % 10
            
            # Вторая контрольная цифра (12-я позиция)
            control_sum_2 = 0
            for i in range(11):  # Все 11 цифр
                control_sum_2 += digits[i] * self.INDIVIDUAL_WEIGHTS_2[i]
            
            control_digit_2 = control_sum_2 % 11
            if control_digit_2 > 9:
                control_digit_2 = control_digit_2 % 10
            
            # Проверка обеих контрольных цифр
            is_valid = (control_digit_1 == digits[10] and 
                       control_digit_2 == digits[11])
            
            return {
                "is_valid": is_valid,
                "type": "individual",
                "inn": inn,
                "control_sum_1": control_sum_1,
                "control_sum_2": control_sum_2,
                "calculated_control_1": control_digit_1,
                "calculated_control_2": control_digit_2,
                "actual_control_1": digits[10],
                "actual_control_2": digits[11],
                "error": None if is_valid else "Неверные контрольные цифры"
            }
            
        except (ValueError, IndexError) as e:
            return {
                "is_valid": False,
                "type": "individual",
                "error": f"Ошибка при обработке ИНН: {str(e)}",
                "inn": inn
            }
    
    def is_organization_inn(self, inn: str) -> bool:
        """Проверка, является ли ИНН ИНН юридического лица"""
        result = self.validate_inn(inn)
        return result["valid"] and result["type"] == "organization"
    
    def is_individual_inn(self, inn: str) -> bool:
        """Проверка, является ли ИНН ИНН индивидуального предпринимателя"""
        result = self.validate_inn(inn)
        return result["valid"] and result["type"] == "individual"
    
    def get_inn_type(self, inn: str) -> Optional[str]:
        """Определение типа ИНН без полной валидации"""
        if not inn or not isinstance(inn, str):
            return None
        
        inn_clean = re.sub(r'\D', '', inn)
        
        if len(inn_clean) == 10:
            return "organization"
        elif len(inn_clean) == 12:
            return "individual"
        else:
            return "invalid"
    
    def format_inn(self, inn: str) -> str:
        """Форматирование ИНН для отображения"""
        if not inn:
            return ""
        
        inn_clean = re.sub(r'\D', '', inn)
        
        if len(inn_clean) == 10:
            return f"{inn_clean[:4]} {inn_clean[4:8]} {inn_clean[8:]}"
        elif len(inn_clean) == 12:
            return f"{inn_clean[:4]} {inn_clean[4:8]} {inn_clean[8:10]} {inn_clean[10:]}"
        else:
            return inn_clean


# Пример использования
if __name__ == "__main__":
    validator = RussianINNValidator()
    
    # Примеры валидации
    test_inns = [
        "1901066506",  # ИНН ФБУЗ (должен быть валидным)
        "1234567890",  # Пример ИНН организации
        "123456789012",  # Пример ИНН ИП
        "invalid",  # Неверный ИНН
    ]
    
    for inn in test_inns:
        result = validator.validate_inn(inn)
        print(f"ИНН {inn}: {'Валиден' if result['valid'] else 'Невалиден'}")
        if result['type']:
            print(f"  Тип: {result['type']}")
        if result.get('error'):
            print(f"  Ошибка: {result['error']}")
        print()
