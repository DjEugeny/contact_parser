#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 DaData Provider для поиска ИНН

Адаптер для интеграции с API DaData для поиска организаций по названию, адресу
и другим параметрам с возвратом ИНН и дополнительной информации.

Author: Contact Parser Team
Created: 2025-10-03
"""

import logging
import time
import json
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import requests
from urllib.parse import quote

try:
    from .inn_data_types import INNCandidate
    from .inn_search_normalizer import INNSearchNormalizer
    from .inn_validator import RussianINNValidator
except ImportError:
    # For standalone usage
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from inn_data_types import INNCandidate
    from inn_search_normalizer import INNSearchNormalizer
    from inn_validator import RussianINNValidator


@dataclass 
class DaDataConfig:
    """Конфигурация DaData API"""
    api_key: str
    secret_key: Optional[str] = None
    timeout_ms: int = 3000
    max_retries: int = 3
    retry_delay: float = 1.0
    base_url: str = "https://suggestions.dadata.ru/suggestions/api/4_1/rs"


class DaDataAPIClient:
    """Клиент для работы с DaData API"""
    
    def __init__(self, config: DaDataConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = None
        
        # Инициализация компонентов
        self.normalizer = INNSearchNormalizer()
        self.inn_validator = RussianINNValidator()
        
        # Headers для API
        self.headers = {
            "Authorization": f"Token {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.config.secret_key:
            self.headers["X-Secret"] = self.config.secret_key
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_ms/1000),
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def search_organizations_sync(self, query: str, city: str = "", 
                                 address: str = "", limit: int = 10) -> List[INNCandidate]:
        """
        Синхронный поиск организаций
        
        Args:
            query: Название организации для поиска
            city: Город (фильтр)
            address: Адрес (фильтр)
            limit: Максимальное количество результатов
            
        Returns:
            List[INNCandidate]: Список найденных кандидатов
        """
        try:
            # Подготовка запроса
            request_data = {
                "query": query,
                "count": min(limit, 20)  # DaData лимит 20
            }
            
            # Добавление фильтров
            if city:
                request_data["locations"] = [{"city": city}]
            
            url = f"{self.config.base_url}/suggest/party"
            
            # Выполнение запроса
            response = requests.post(
                url,
                headers=self.headers,
                json=request_data,
                timeout=self.config.timeout_ms / 1000
            )
            
            if response.status_code != 200:
                self.logger.error(f"DaData API error: {response.status_code} - {response.text}")
                return []
            
            # Парсинг ответа
            data = response.json()
            candidates = self._parse_dadata_response(data)
            
            # Фильтрация по адресу если указан
            if address and candidates:
                candidates = self._filter_by_address(candidates, address)
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"Error searching organizations in DaData: {e}")
            return []
    
    async def search_organizations(self, query: str, city: str = "", 
                                  address: str = "", limit: int = 10) -> List[INNCandidate]:
        """
        Асинхронный поиск организаций
        
        Args:
            query: Название организации для поиска
            city: Город (фильтр)
            address: Адрес (фильтр)
            limit: Максимальное количество результатов
            
        Returns:
            List[INNCandidate]: Список найденных кандидатов
        """
        if not self.session:
            raise ValueError("Session not initialized. Use async context manager.")
        
        try:
            # Подготовка запроса
            request_data = {
                "query": query,
                "count": min(limit, 20)  # DaData лимит 20
            }
            
            # Добавление фильтров
            if city:
                request_data["locations"] = [{"city": city}]
            
            url = f"{self.config.base_url}/suggest/party"
            
            # Выполнение запроса с retry логикой
            candidates = []
            for attempt in range(self.config.max_retries):
                try:
                    async with self.session.post(url, json=request_data) as response:
                        if response.status == 200:
                            data = await response.json()
                            candidates = self._parse_dadata_response(data)
                            break
                        else:
                            error_text = await response.text()
                            self.logger.warning(f"DaData API error (attempt {attempt + 1}): {response.status} - {error_text}")
                            
                except asyncio.TimeoutError:
                    self.logger.warning(f"DaData API timeout (attempt {attempt + 1})")
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
            
            # Фильтрация по адресу если указан
            if address and candidates:
                candidates = self._filter_by_address(candidates, address)
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"Error searching organizations in DaData: {e}")
            return []
    
    def lookup_by_inn(self, inn: str) -> Optional[INNCandidate]:
        """
        Поиск организации по ИНН
        
        Args:
            inn: ИНН для поиска
            
        Returns:
            Optional[INNCandidate]: Найденная организация или None
        """
        try:
            # Валидация ИНН
            if not self.inn_validator.is_valid(inn):
                return None
            
            url = f"{self.config.base_url}/findById/party"
            request_data = {"query": inn}
            
            response = requests.post(
                url,
                headers=self.headers,
                json=request_data,
                timeout=self.config.timeout_ms / 1000
            )
            
            if response.status_code != 200:
                self.logger.error(f"DaData lookup error: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            candidates = self._parse_dadata_response(data)
            
            return candidates[0] if candidates else None
            
        except Exception as e:
            self.logger.error(f"Error looking up INN {inn} in DaData: {e}")
            return None
    
    def _parse_dadata_response(self, data: Dict[str, Any]) -> List[INNCandidate]:
        """
        Парсинг ответа от DaData API
        
        Args:
            data: JSON ответ от DaData
            
        Returns:
            List[INNCandidate]: Список кандидатов
        """
        candidates = []
        suggestions = data.get('suggestions', [])
        
        for suggestion in suggestions:
            try:
                candidate = self._parse_single_suggestion(suggestion)
                if candidate:
                    candidates.append(candidate)
            except Exception as e:
                self.logger.warning(f"Error parsing DaData suggestion: {e}")
                continue
        
        return candidates
    
    def _parse_single_suggestion(self, suggestion: Dict[str, Any]) -> Optional[INNCandidate]:
        """
        Парсинг одного предложения от DaData
        
        Args:
            suggestion: Одно предложение из ответа DaData
            
        Returns:
            Optional[INNCandidate]: Кандидат или None
        """
        try:
            data_section = suggestion.get('data', {})
            
            # Извлечение основной информации
            inn = data_section.get('inn')
            if not inn or not self.inn_validator.is_valid(inn):
                return None
            
            ogrn = data_section.get('ogrn')
            name = suggestion.get('value', '')
            
            # Нормализация названия
            name_norm = self.normalizer.normalize_organization_name(name)
            
            # Извлечение адреса
            address_data = data_section.get('address', {})
            city = None
            address = None
            
            if address_data:
                city = address_data.get('data', {}).get('city', '')
                if not city:
                    city = address_data.get('value', '').split(',')[0].strip()
                
                # Полный адрес
                address = address_data.get('value', '')
            
            # Организационно-правовая форма
            opf = data_section.get('opf', {}).get('short', '')
            
            # Статус организации
            state = data_section.get('state', {})
            status = state.get('status', 'ACTIVE') if state else 'ACTIVE'
            
            # Пропускаем ликвидированные организации
            if status in ['LIQUIDATED', 'LIQUIDATING']:
                return None
            
            # Создание кандидата
            candidate = INNCandidate(
                inn=inn,
                ogrn=ogrn,
                name=name,
                name_norm=name_norm,
                city=city,
                address=address,
                opf=opf,
                score=0.0,  # Будет рассчитан позже
                provider='dadata',
                link=f"https://egrul.nalog.ru/index.html?queryAll={inn}" if inn else None
            )
            
            return candidate
            
        except Exception as e:
            self.logger.error(f"Error parsing DaData suggestion: {e}")
            return None
    
    def _filter_by_address(self, candidates: List[INNCandidate], 
                          target_address: str) -> List[INNCandidate]:
        """
        Фильтрация кандидатов по адресу
        
        Args:
            candidates: Список кандидатов
            target_address: Целевой адрес для фильтрации
            
        Returns:
            List[INNCandidate]: Отфильтрованный список
        """
        if not target_address:
            return candidates
        
        target_norm = self.normalizer.normalize_address(target_address)
        if not target_norm:
            return candidates
        
        filtered = []
        for candidate in candidates:
            if not candidate.address:
                continue
            
            candidate_norm = self.normalizer.normalize_address(candidate.address)
            if self._addresses_similar(target_norm, candidate_norm):
                filtered.append(candidate)
        
        return filtered if filtered else candidates  # Если ничего не найдено, возвращаем все
    
    def _addresses_similar(self, addr1: str, addr2: str, threshold: float = 0.3) -> bool:
        """
        Проверка похожести адресов
        
        Args:
            addr1: Первый адрес
            addr2: Второй адрес
            threshold: Порог схожести
            
        Returns:
            bool: True если адреса похожи
        """
        if not addr1 or not addr2:
            return False
        
        words1 = set(addr1.lower().split())
        words2 = set(addr2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0.0
        return similarity >= threshold


class DaDataProviderAdapter:
    """Адаптер DaData для интеграции с INN Resolver"""
    
    def __init__(self, api_key: str, secret_key: Optional[str] = None, 
                 timeout_ms: int = 3000):
        self.config = DaDataConfig(
            api_key=api_key,
            secret_key=secret_key,
            timeout_ms=timeout_ms
        )
        self.client = DaDataAPIClient(self.config)
        self.logger = logging.getLogger(__name__)
    
    def search_candidates(self, name: str, city: str = "", 
                         address: str = "", domain: str = "") -> List[INNCandidate]:
        """
        Поиск кандидатов для обогащения ИНН
        
        Args:
            name: Название организации
            city: Город
            address: Адрес
            domain: Домен (не используется в DaData)
            
        Returns:
            List[INNCandidate]: Список кандидатов
        """
        if not name.strip():
            return []
        
        try:
            # Поиск по названию
            candidates = self.client.search_organizations_sync(
                query=name.strip(),
                city=city.strip() if city else "",
                address=address.strip() if address else "",
                limit=10
            )
            
            self.logger.info(f"DaData found {len(candidates)} candidates for '{name}'")
            return candidates
            
        except Exception as e:
            self.logger.error(f"DaData search error for '{name}': {e}")
            return []
    
    async def search_candidates_async(self, name: str, city: str = "", 
                                     address: str = "", domain: str = "") -> List[INNCandidate]:
        """Асинхронная версия поиска кандидатов"""
        if not name.strip():
            return []
        
        try:
            async with self.client as client:
                candidates = await client.search_organizations(
                    query=name.strip(),
                    city=city.strip() if city else "",
                    address=address.strip() if address else "",
                    limit=10
                )
            
            self.logger.info(f"DaData found {len(candidates)} candidates for '{name}'")
            return candidates
            
        except Exception as e:
            self.logger.error(f"DaData async search error for '{name}': {e}")
            return []
    
    def validate_inn(self, inn: str) -> Optional[INNCandidate]:
        """
        Валидация ИНН через DaData
        
        Args:
            inn: ИНН для проверки
            
        Returns:
            Optional[INNCandidate]: Информация об организации или None
        """
        try:
            return self.client.lookup_by_inn(inn)
        except Exception as e:
            self.logger.error(f"DaData INN validation error for '{inn}': {e}")
            return None
    
    def get_api_info(self) -> Dict[str, Any]:
        """Получение информации об API"""
        return {
            'provider': 'dadata',
            'base_url': self.config.base_url,
            'timeout_ms': self.config.timeout_ms,
            'has_secret': bool(self.config.secret_key)
        }


# Экспорт основных классов
__all__ = [
    'DaDataConfig',
    'DaDataAPIClient', 
    'DaDataProviderAdapter'
]