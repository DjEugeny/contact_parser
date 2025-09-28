#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🗺️ Региональная логика приоритизации контактов."""

from __future__ import annotations

from typing import Dict, Any

WIFE_REGIONS = {
    "high_priority": [
        "Новосибирск", "Томск", "Кемерово",
        "Барнаул", "Горно-Алтайск", "Новокузнецк",
        "Абакан", "Кызыл"
    ],
    "medium_priority": [
        "Улан-Удэ"
    ],
    "low_priority": [
        "Красноярск", "Иркутск"
    ],
}


def calculate_region_priority(region_text: str) -> Dict[str, Any]:
    """🎯 Рассчитывает приоритет региона."""
    if not region_text:
        return {"score": 0.1, "level": "unknown", "region": None}

    region_lower = region_text.lower().strip()

    high_regions = [
        'новосибирск', 'томск', 'кемерово', 'барнаул',
        'горно-алтайск', 'новокузнецк', 'абакан', 'кызыл'
    ]
    medium_regions = ['улан-удэ']
    low_regions = ['красноярск', 'иркутск']

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


def calculate_contact_priority(contact_data: Dict[str, Any], business_context: Dict[str, Any]) -> Dict[str, Any]:
    """🤝 Комплексный расчёт приоритета контакта."""
    score = 0.0
    factors = []

    if business_context is None:
        business_context = {}

    region_info = calculate_region_priority(business_context.get('region', ''))
    score += region_info['score'] * 0.4

    level_parts = region_info['level'].split()
    if len(level_parts) > 1:
        factors.append(f"region_{level_parts[1].lower()}")
    else:
        factors.append(f"region_{level_parts[0].lower()}")

    equipment = (business_context.get('equipment_type') or '').lower()
    dna_keywords = ['днк', 'амплификатор', 'проба-рапид', 'реагент', 'пцр']
    if any(keyword in equipment for keyword in dna_keywords):
        score += 0.3
        factors.append("equipment_relevant")

    if business_context.get('budget_mentioned'):
        score += 0.15
        factors.append("budget_mentioned")

    urgency = (business_context.get('urgency') or '').lower()
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
    """📊 Возвращает текстовый уровень приоритета."""
    if score >= 0.75:
        return "🔥 ВЫСОКИЙ"
    if score >= 0.5:
        return "⚡ СРЕДНИЙ"
    return "🌍 ОЧЕНЬ НИЗКИЙ"


__all__ = [
    "WIFE_REGIONS",
    "calculate_region_priority",
    "calculate_contact_priority",
]
