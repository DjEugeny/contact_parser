#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌍 Регионы и расчет приоритета контактов
"""

from typing import Dict, Any

# Приоритетные регионы для бизнеса
PRIORITY_REGIONS = [
    'Москва', 'Санкт-Петербург', 'Казань', 'Екатеринбург', 'Новосибирск',
    'Краснодар', 'Сочи', 'Ростов-на-Дону', 'Калининград', 'Владивосток'
]

# Отрасли с высоким приоритетом
PRIORITY_INDUSTRIES = [
    'медицина', 'фармацевтика', 'здравоохранение', 'лаборатория', 'диагностика',
    'клиника', 'больница', 'научный центр', 'исследовательский институт',
    'биотехнологии', 'цитогенетика', 'генетика'
]

# Должности с высоким приоритетом
PRIORITY_POSITIONS = [
    'директор', 'главный врач', 'заведующий', 'руководитель',
    'ceo', 'cto', 'начальник', 'глава', 'основатель', 'президент'
]

def calculate_contact_priority(contact: Dict[str, Any], business_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """🎯 Расчет приоритета контакта на основе данных"""
    
    score = 0.5  # Базовый средний приоритет
    reasons = []
    
    # 1. Анализ по городу/региону
    city = contact.get('city') or ''
    if city and isinstance(city, str):
        city_lower = city.lower()
        if any(region.lower() in city_lower for region in PRIORITY_REGIONS):
            score += 0.15
            reasons.append(f"приоритетный регион: {city}")
    
    # 2. Анализ по должности
    position = contact.get('position') or ''
    if position and isinstance(position, str):
        position_lower = position.lower()
        if any(pos in position_lower for pos in PRIORITY_POSITIONS):
            score += 0.2
            reasons.append(f"важная должность: {position}")
    
    # 3. Анализ по организации
    organization = contact.get('organization') or ''
    if organization and isinstance(organization, str):
        org_lower = organization.lower()
        if any(ind in org_lower for ind in PRIORITY_INDUSTRIES):
            score += 0.15
            reasons.append(f"приоритетная отрасль: {organization}")
    
    # 4. Анализ по бизнес-контексту
    if business_context and isinstance(business_context, dict):
        # 4.1 Срочность
        urgency = business_context.get('urgency') or ''
        if urgency and isinstance(urgency, str):
            urgency_lower = urgency.lower()
            if 'высок' in urgency_lower:
                score += 0.1
                reasons.append(f"высокая срочность")
        
        # 4.2 Интерес к продукту
        product_interest = business_context.get('product_interest') or ''
        if product_interest and isinstance(product_interest, str):
            product_lower = product_interest.lower()
            if 'амплификатор' in product_lower:
                score += 0.2
                reasons.append(f"интерес к ключевому продукту")
    
    # 5. Наличие контактной информации
    if contact.get('email'):
        score += 0.05
        if contact.get('phone'):
            score += 0.05
            reasons.append("полные контактные данные")
    
    # 6. Учет показателя confidence
    confidence = contact.get('confidence', 0)
    if confidence > 0.9:
        score += 0.05
        reasons.append("высокая достоверность данных")
    elif confidence < 0.7:
        score -= 0.1
        reasons.append("низкая достоверность данных")
    
    # Ограничиваем score диапазоном [0, 1]
    score = max(0, min(1, score))
    
    # Определяем текстовый уровень приоритета
    if score >= 0.8:
        level = "высокий"
    elif score >= 0.6:
        level = "средний"
    else:
        level = "низкий"
    
    return {
        "score": score,
        "level": level,
        "reasons": reasons
    }
