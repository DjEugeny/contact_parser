#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗺️ Региональная логика для приоритизации (обновлено 10.08.2025)
"""

# 🎯 Региональные приоритеты Светы (финальная версия)
WIFE_REGIONS = {
    "high_priority": [
        "Новосибирск", "Томск", "Кемерово", 
        "Барнаул", "Горно-Алтайск", "Новокузнецк", 
        "Абакан", "Кызыл"  # 🔥 Кызыл теперь высокий приоритет
    ],
    "medium_priority": [
        "Улан-Удэ"  # 📍 Единственный средний приоритет
    ],
    "low_priority": [
        "Красноярск", "Иркутск"  # 🔻 Пониженный приоритет
    ]
    # 🌍 Все остальные регионы = very_low но обрабатываем!
}


def calculate_region_priority(region_text: str) -> dict:
    """Расчет регионального приоритета контакта"""
    
    if not region_text:
        return {"score": 0.1, "level": "unknown", "region": None}
    
    region_lower = region_text.lower().strip()
    
    # Словари для поиска (обновлены)
    high_regions = [
        'новосибирск', 'томск', 'кемерово', 'барнаул', 
        'горно-алтайск', 'новокузнецк', 'абакан', 'кызыл'  # 🔥 Кызыл добавлен
    ]
    medium_regions = ['улан-удэ']  # 📍 Теперь только Улан-Удэ
    low_regions = ['красноярск', 'иркутск']
    
    # Поиск совпадений
    for region in high_regions:
        if region in region_lower:
            return {
                "score": 0.9, 
                "level": "🔥 ВЫСОКИЙ",
                "region": region.title()
            }
    
    for region in medium_regions:
        if region in region_lower:
            return {
                "score": 0.6,
                "level": "⚡ СРЕДНИЙ", 
                "region": region.title()
            }
            
    for region in low_regions:
        if region in region_lower:
            return {
                "score": 0.3,
                "level": "🔻 НИЗКИЙ",
                "region": region.title()
            }
    
    return {
        "score": 0.1, 
        "level": "🌍 ОЧЕНЬ НИЗКИЙ",
        "region": region_text
    }


def calculate_contact_priority(contact_data: dict, business_context: dict) -> dict:
    """🎯 Комплексный расчет приоритета контакта"""
    
    score = 0.0
    factors = []
    
    # 1. Региональный фактор (40% веса)
    region_info = calculate_region_priority(business_context.get('region', ''))
    score += region_info['score'] * 0.4
    factors.append(f"region_{region_info['level'].split()[1].lower()}")
    
    # 2. ДНК-оборудование (30% веса)
    equipment = business_context.get('equipment_type', '').lower()
    dna_keywords = ['днк', 'амплификатор', 'проба-рапид', 'реагент', 'пцр']
    if any(keyword in equipment for keyword in dna_keywords):
        score += 0.3
        factors.append("equipment_relevant")
    
    # 3. Упоминание бюджета (15% веса)
    if business_context.get('budget_mentioned'):
        score += 0.15
        factors.append("budget_mentioned")
    
    # 4. Срочность (15% веса)  
    urgency = business_context.get('urgency', '').lower()
    if urgency in ['высокая', 'срочно', 'urgent']:
        score += 0.15
        factors.append("urgent_request")
    elif urgency in ['средняя', 'normal']:
        score += 0.08
        factors.append("normal_request")
    
    return {
        "score": min(score, 1.0),
        "level": _get_priority_level(score),
        "factors": factors,
        "region_info": region_info
    }


def _get_priority_level(score: float) -> str:
    """Определение текстового уровня приоритета"""
    if score >= 0.8:
        return "🔥 КРИТИЧЕСКИЙ"
    elif score >= 0.6:
        return "⚡ ВЫСОКИЙ" 
    elif score >= 0.4:
        return "📊 СРЕДНИЙ"
    elif score >= 0.2:
        return "🔻 НИЗКИЙ"
    else:
        return "❄️ МИНИМАЛЬНЫЙ"
