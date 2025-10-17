#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐛 Отладка скоринга кандидатов
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from src.postprocessing.inn_search_normalizer import INNSearchNormalizer
from src.postprocessing.org_inn_resolver import INNCandidateScorer
from src.postprocessing.inn_data_types import INNCandidate

def test_normalization():
    """Тест нормализации названий"""
    print("\n" + "=" * 80)
    print("ТЕСТ НОРМАЛИЗАЦИИ")
    print("=" * 80)
    
    normalizer = INNSearchNormalizer()
    
    test_cases = [
        "ДНК Технология",
        "ООО \"ДНК-ТЕХНОЛОГИЯ\"",
        "ООО \"ДНК-ТЕХНОЛОГИЯ ТС\"",
        "ООО \"НПО ДНК-ТЕХНОЛОГИЯ\"",
        "Яндекс",
        "ООО \"ЯНДЕКС\"",
        "Сбербанк",
        "ПАО СБЕРБАНК"
    ]
    
    for name in test_cases:
        normalized = normalizer.normalize_organization_name(name)
        print(f"\nИсходное: '{name}'")
        print(f"Нормализованное: '{normalized}'")


def test_scoring():
    """Тест скоринга"""
    print("\n" + "=" * 80)
    print("ТЕСТ СКОРИНГА")
    print("=" * 80)
    
    normalizer = INNSearchNormalizer()
    scorer = INNCandidateScorer()
    
    # Тестовый случай: ДНК Технология
    search_name = normalizer.normalize_organization_name("ДНК Технология")
    search_city = normalizer.normalize_city_name("Новосибирск")
    
    print(f"\nПоисковый запрос:")
    print(f"  Название: '{search_name}'")
    print(f"  Город: '{search_city}'")
    
    # Кандидаты
    candidates = [
        INNCandidate(
            inn="7723537840",
            ogrn="1057746762105",
            name='ООО "ДНК-ТЕХНОЛОГИЯ"',
            name_norm=normalizer.normalize_organization_name('ООО "ДНК-ТЕХНОЛОГИЯ"'),
            city="Москва",
            address="г Москва, Варшавское шоссе, д 125Ж к 5, помещ 12",
            opf="ООО",
            score=0.0,
            provider="dadata",
            link=None
        ),
        INNCandidate(
            inn="5406789012",
            ogrn="1055406789012",
            name='ООО "ДНК-ТЕХНОЛОГИЯ"',
            name_norm=normalizer.normalize_organization_name('ООО "ДНК-ТЕХНОЛОГИЯ"'),
            city="Новосибирск",
            address="г Новосибирск, ул Тестовая, д 1",
            opf="ООО",
            score=0.0,
            provider="test",
            link=None
        )
    ]
    
    print(f"\nКандидаты:")
    for i, candidate in enumerate(candidates, 1):
        print(f"\n{i}. {candidate.name} ({candidate.city})")
        print(f"   Нормализованное название: '{candidate.name_norm}'")
        
        # Расчет скора
        score = scorer.score_candidate(
            candidate,
            search_name,
            search_city,
            "",  # address
            ""   # domain
        )
        
        print(f"   Score: {score:.2f}")
        
        # Детальный расчет
        name_score = scorer._calculate_name_similarity(search_name, candidate.name_norm)
        city_score = scorer._calculate_city_match(search_city, candidate.city or "")
        
        print(f"   - Name similarity: {name_score:.2f}")
        print(f"   - City match: {city_score:.2f}")
        
        # Анализ слов
        search_words = set(search_name.lower().split())
        candidate_words = set(candidate.name_norm.lower().split())
        
        print(f"   Слова в поиске: {search_words}")
        print(f"   Слова в кандидате: {candidate_words}")
        print(f"   Пересечение: {search_words.intersection(candidate_words)}")
        print(f"   Объединение: {search_words.union(candidate_words)}")


def main():
    test_normalization()
    test_scoring()


if __name__ == "__main__":
    main()
