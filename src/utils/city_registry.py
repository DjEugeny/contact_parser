#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🗺️ Реестр городов РФ для нормализации названий и столиц."""

from __future__ import annotations

import csv
import unicodedata
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = PROJECT_ROOT / 'config' / 'russian_cities.csv'

_REGION_TYPE_PREFIX = {
    'Респ': 'Республика',
    'край': 'край',
    'обл': 'область',
    'АО': 'Автономный округ',
    'Аобл': 'Автономная область',
    'г': 'город',
    'Чувашия': 'Чувашская Республика',
}

_PUBLIC_DOMAIN_PATTERN = re.compile(r'^(?:г\.?\s*)', re.IGNORECASE)


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize('NFKC', value)
    value = value.replace('ё', 'е').lower()
    value = value.replace('«', '').replace('»', '')
    value = value.replace('“', '').replace('”', '')
    value = re.sub(r'["\']', '', value)
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def _strip_city_prefix(value: str) -> str:
    value = value.strip()
    value = _PUBLIC_DOMAIN_PATTERN.sub('', value)
    replacements = [
        ('город ', ''),
        ('гор. ', ''),
        ('республика ', ''),
        ('респ. ', ''),
        ('р. ', ''),
        ('р.', ''),
    ]
    value_lower = value.lower()
    for prefix, repl in replacements:
        if value_lower.startswith(prefix):
            value = value[len(prefix):]
            break
    return value.strip()


class CityRecord:
    __slots__ = ('city', 'region', 'region_type', 'federal_district', 'capital_marker', 'population', 'timezone', 'geo_lat', 'geo_lon')

    def __init__(self, data: Dict[str, str]):
        self.city = data['city']
        self.region = data['region']
        self.region_type = data['region_type']
        self.federal_district = data['federal_district']
        self.capital_marker = data['capital_marker']
        self.population = data['population']
        self.timezone = data['timezone']
        self.geo_lat = data['geo_lat']
        self.geo_lon = data['geo_lon']

    @property
    def region_full_name(self) -> str:
        prefix = _REGION_TYPE_PREFIX.get(self.region_type, '').strip()
        if not prefix:
            return self.region
        if prefix == 'Чувашская Республика':
            return prefix
        return f"{prefix} {self.region}".strip()


class CityRegistry:
    """Класс-хранилище сведений о городах РФ."""

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or DATA_PATH
        self._city_index: Dict[str, CityRecord] = {}
        self._region_index: Dict[str, CityRecord] = {}
        self._load_data()

    def _load_data(self) -> None:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Не найден файл реестра городов: {self.data_path}")

        with self.data_path.open('r', encoding='utf-8') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                record = CityRecord(row)
                city_key = self._make_city_key(record.city)
                self._city_index[city_key] = record

                # Индексы региона
                region_keys = self._make_region_keys(record.region, record.region_type)
                if record.capital_marker == '2':  # столица субъекта
                    for key in region_keys:
                        self._region_index[key] = record

    def _make_city_key(self, city: str) -> str:
        return _normalize_text(_strip_city_prefix(city))

    def _make_region_keys(self, region: str, region_type: str) -> Iterable[str]:
        base = _normalize_text(region)
        keys = {base}
        prefix = _REGION_TYPE_PREFIX.get(region_type, '')
        if prefix and prefix != 'Чувашская Республика':
            keys.add(_normalize_text(f"{prefix} {region}"))
        if prefix.lower().startswith('республика'):
            keys.add(_normalize_text(f"респ {region}"))
        if region_type == 'Чувашия':
            keys.add(_normalize_text('чувашия'))
        return keys

    @lru_cache(maxsize=1024)
    def resolve_city(self, name: Optional[str]) -> Optional[CityRecord]:
        if not name:
            return None
        key = self._make_city_key(name)
        if not key:
            return None
        record = self._city_index.get(key)
        if record:
            return record
        # Возможно передан субъект Федерации
        record = self._region_index.get(key)
        if record:
            return record
        return None

    @lru_cache(maxsize=512)
    def resolve_region_capital(self, name: Optional[str]) -> Optional[CityRecord]:
        if not name:
            return None
        key = _normalize_text(_strip_city_prefix(name))
        if not key:
            return None
        return self._region_index.get(key)

    def is_same_city(self, resolved_name: Optional[str], original_name: Optional[str]) -> bool:
        """🔍 Проверяет, эквивалентны ли названия города."""
        if not resolved_name or not original_name:
            return False
        return self._make_city_key(resolved_name) == self._make_city_key(original_name)

    def normalize_city_value(self, value: Optional[str], fallback_region: Optional[str] = None) -> Optional[Dict[str, str]]:
        record = None
        if value:
            record = self.resolve_city(value)
        if record is None and fallback_region:
            record = self.resolve_region_capital(fallback_region)
        if record is None:
            return None
        return {
            'city': record.city,
            'region': record.region_full_name,
            'region_type': record.region_type,
            'federal_district': record.federal_district,
            'timezone': record.timezone,
        }


__all__ = [
    'CityRegistry',
]
