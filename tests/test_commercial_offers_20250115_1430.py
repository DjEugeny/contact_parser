#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тесты для валидации коммерческих предложений
Создано: 2025-01-15 14:30 (UTC+07)
"""

import unittest
import sys
import os

# Добавляем путь к src для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.validator import LLMResponseValidator

class TestCommercialOffersValidation(unittest.TestCase):
    """🧪 Тесты валидации коммерческих предложений"""
    
    def setUp(self):
        """Настройка тестов"""
        self.validator = LLMResponseValidator()
    
    def test_valid_commercial_offer_found(self):
        """✅ Тест валидного найденного КП"""
        valid_offer = {
            "found": True,
            "offer_number": "КП-2024-001",
            "offer_date": "2024-12-15",
            "total_cost": 150000.0,
            "currency": "RUB",
            "end_user": "ООО Тестовая компания",
            "intermediary": "ООО Посредник",
            "equipment_items": [
                {
                    "name": "Сервер Dell",
                    "model": "PowerEdge R740",
                    "quantity": 2,
                    "unit_price": 75000.0,
                    "total_price": 150000.0
                }
            ]
        }
        
        is_valid, errors = self.validator.validate_commercial_offers([valid_offer])
        self.assertTrue(is_valid, f"Ошибки валидации: {errors}")
        self.assertEqual(len(errors), 0)
    
    def test_valid_commercial_offer_not_found(self):
        """✅ Тест валидного ненайденного КП"""
        not_found_offer = {
            "found": False,
            "reason": "КП не найдено в документе"
        }
        
        is_valid, errors = self.validator.validate_commercial_offers([not_found_offer])
        self.assertTrue(is_valid, f"Ошибки валидации: {errors}")
        self.assertEqual(len(errors), 0)
    
    def test_missing_required_field_found(self):
        """❌ Тест отсутствия обязательного поля found"""
        invalid_offer = {
            "offer_number": "КП-2024-001"
        }
        
        is_valid, errors = self.validator.validate_commercial_offers([invalid_offer])
        self.assertFalse(is_valid)
        self.assertTrue(any("'found' is a required property" in error for error in errors))
    
    def test_missing_required_fields_for_found_offer(self):
        """❌ Тест отсутствия обязательных полей для найденного КП"""
        invalid_offer = {
            "found": True
            # Отсутствуют offer_number, offer_date, total_cost
        }
        
        is_valid, errors = self.validator.validate_commercial_offers([invalid_offer])
        self.assertFalse(is_valid)
        
        # Проверяем, что есть ошибки для всех обязательных полей
        error_text = ' '.join(errors)
        self.assertIn("offer_number", error_text)
        self.assertIn("offer_date", error_text)
        self.assertIn("total_cost", error_text)
    
    def test_empty_equipment_items_for_found_offer(self):
        """❌ Тест пустого списка оборудования для найденного КП"""
        invalid_offer = {
            "found": True,
            "offer_number": "КП-2024-001",
            "offer_date": "2024-12-15",
            "total_cost": 150000.0,
            "equipment_items": []  # Пустой список
        }
        
        is_valid, errors = self.validator.validate_commercial_offers([invalid_offer])
        self.assertFalse(is_valid)
        self.assertTrue(any("должен быть список оборудования" in error for error in errors))
    
    def test_total_cost_mismatch(self):
        """❌ Тест несоответствия общей суммы и суммы позиций"""
        invalid_offer = {
            "found": True,
            "offer_number": "КП-2024-001",
            "offer_date": "2024-12-15",
            "total_cost": 200000.0,  # Неправильная сумма
            "equipment_items": [
                {
                    "name": "Сервер Dell",
                    "quantity": 2,
                    "unit_price": 75000.0,
                    "total_price": 150000.0  # Реальная сумма 150000
                }
            ]
        }
        
        is_valid, errors = self.validator.validate_commercial_offers([invalid_offer])
        self.assertFalse(is_valid)
        self.assertTrue(any("Несоответствие общей суммы" in error for error in errors))
    
    def test_postprocess_commercial_offers(self):
        """🔄 Тест постобработки коммерческих предложений"""
        offers = [
            {
                "found": True,
                "offer_number": "КП-2024-001",
                "offer_date": "2024-12-15",
                "total_cost": 100000.0,
                # currency отсутствует - должна быть добавлена RUB
                "equipment_items": [
                    {
                        "name": "Сервер",
                        "quantity": 2,
                        "unit_price": 60000.0
                        # total_price отсутствует - должна быть рассчитана
                    }
                ]
            }
        ]
        
        processed = self.validator.postprocess_commercial_offers(offers)
        
        # Проверяем добавление валюты по умолчанию
        self.assertEqual(processed[0]['currency'], 'RUB')
        
        # Проверяем расчет total_price для позиции
        item = processed[0]['equipment_items'][0]
        self.assertEqual(item['total_price'], 120000.0)  # 2 * 60000
        
        # Проверяем пересчет общей стоимости
        self.assertEqual(processed[0]['total_cost'], 120000.0)
    
    def test_validate_and_postprocess_integration(self):
        """🔄 Тест интеграции валидации и постобработки"""
        data = {
            "commercial_offers": [
                {
                    "found": True,
                    "offer_number": "КП-2024-001",
                    "offer_date": "2024-12-15",
                    "total_cost": 100000.0,
                    "equipment_items": [
                        {
                            "name": "Сервер",
                            "quantity": 1,
                            "unit_price": 100000.0,
                            "total_price": 100000.0
                        }
                    ]
                }
            ]
        }
        
        result = self.validator.validate_and_postprocess(data)
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertIn('commercial_offers', result['processed_data'])
        
        # Проверяем, что валюта была добавлена
        processed_offer = result['processed_data']['commercial_offers'][0]
        self.assertEqual(processed_offer['currency'], 'RUB')

if __name__ == '__main__':
    print("🧪 Запуск тестов валидации коммерческих предложений")
    print(f"Время создания: 2025-01-15 14:30 (UTC+07)")
    unittest.main(verbosity=2)