#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тесты для умной автокоррекции interaction_type

Проверяет, что автокоррекция правильно определяет типы взаимодействий
на основе контекста.
"""

import pytest
from src.core.validator import LLMResponseValidator


class TestInteractionTypeAutoCorrect:
    """Тесты автокоррекции interaction_type"""
    
    @pytest.fixture
    def validator(self):
        """Создаём валидатор"""
        return LLMResponseValidator()
    
    def test_sent_quote_detection(self, validator):
        """✅ Определение 'sent_quote' по контексту"""
        interactions = [
            {
                'interaction_local_id': 1,
                'summary': 'Отправлено коммерческое предложение на оборудование',
                'role_in_message': 'sender'
            }
        ]
        
        result = validator._auto_correct_missing_interaction_type(interactions)
        
        assert result[0]['interaction_type'] == 'sent_quote'
        assert result[0]['_auto_corrected'] is True
        assert 'sent_quote' in result[0]['_correction_reason']
    
    def test_requested_quote_detection(self, validator):
        """✅ Определение 'requested_quote' по контексту"""
        interactions = [
            {
                'interaction_local_id': 2,
                'summary': 'Прошу выслать КП на анализаторы',
                'role_in_message': 'recipient'
            }
        ]
        
        result = validator._auto_correct_missing_interaction_type(interactions)
        
        assert result[0]['interaction_type'] == 'requested_quote'
        assert result[0]['_auto_corrected'] is True
    
    def test_invoice_detection(self, validator):
        """✅ Определение 'invoice_sent' по контексту"""
        interactions = [
            {
                'interaction_local_id': 3,
                'summary': 'Выставлен счёт на оплату',
                'role_in_message': 'sender'
            }
        ]
        
        result = validator._auto_correct_missing_interaction_type(interactions)
        
        assert result[0]['interaction_type'] == 'invoice_sent'
    
    def test_complaint_detection(self, validator):
        """✅ Определение 'complaint' по контексту"""
        interactions = [
            {
                'interaction_local_id': 4,
                'summary': 'Жалоба на качество реагентов',
                'role_in_message': 'sender'
            }
        ]
        
        result = validator._auto_correct_missing_interaction_type(interactions)
        
        assert result[0]['interaction_type'] == 'complaint'
    
    def test_contract_detection(self, validator):
        """✅ Определение 'contract_sent' по контексту"""
        interactions = [
            {
                'interaction_local_id': 5,
                'summary': 'Направлен договор на подписание',
                'role_in_message': 'sender'
            }
        ]
        
        result = validator._auto_correct_missing_interaction_type(interactions)
        
        assert result[0]['interaction_type'] == 'contract_sent'
    
    def test_clarification_detection(self, validator):
        """✅ Определение 'clarification' по контексту"""
        interactions = [
            {
                'interaction_local_id': 6,
                'summary': 'Уточнение по срокам поставки',
                'role_in_message': 'recipient'
            }
        ]
        
        result = validator._auto_correct_missing_interaction_type(interactions)
        
        assert result[0]['interaction_type'] == 'clarification'
    
    def test_other_fallback(self, validator):
        """✅ Fallback на 'other' для неопределённого контекста"""
        interactions = [
            {
                'interaction_local_id': 7,
                'summary': 'Какой-то текст без ключевых слов',
                'role_in_message': 'sender'
            }
        ]
        
        result = validator._auto_correct_missing_interaction_type(interactions)
        
        assert result[0]['interaction_type'] == 'other'
    
    def test_existing_type_not_changed(self, validator):
        """✅ Существующий тип не изменяется"""
        interactions = [
            {
                'interaction_local_id': 8,
                'interaction_type': 'follow_up',
                'summary': 'Отправлено коммерческое предложение',
                'role_in_message': 'sender'
            }
        ]
        
        result = validator._auto_correct_missing_interaction_type(interactions)
        
        assert result[0]['interaction_type'] == 'follow_up'
        assert '_auto_corrected' not in result[0]
    
    def test_multiple_interactions(self, validator):
        """✅ Обработка нескольких взаимодействий"""
        interactions = [
            {
                'interaction_local_id': 1,
                'summary': 'Отправлено КП',
                'role_in_message': 'sender'
            },
            {
                'interaction_local_id': 2,
                'summary': 'Запрос на уточнение цены',
                'role_in_message': 'recipient'
            }
        ]
        
        result = validator._auto_correct_missing_interaction_type(interactions)
        
        assert result[0]['interaction_type'] == 'sent_quote'
        assert result[1]['interaction_type'] == 'requested_quote'
        assert all(i['_auto_corrected'] for i in result)
    
    def test_integration_with_normalize(self, validator):
        """✅ Интеграция с _normalize_interaction_types"""
        data = {
            'interactions': [
                {
                    'interaction_local_id': 1,
                    'summary': 'Отправлено коммерческое предложение',
                    'role_in_message': 'sender'
                }
            ]
        }
        
        result = validator._normalize_interaction_types(data)
        
        assert result['interactions'][0]['interaction_type'] == 'sent_quote'
        assert result['interactions'][0]['_auto_corrected'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
