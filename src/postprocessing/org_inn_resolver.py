#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ Обогащение ИНН организаций

Модуль для обогащения организаций ИНН с приоритетом официального источника ФНС
и прозрачным следом принятия решений.

Author: Contact Parser Team
Created: 2025-10-03
"""

import logging
import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import concurrent.futures
from dataclasses import dataclass

try:
    from config.settings import INN_ENRICHMENT_CONFIG
except ImportError:
    # Fallback configuration if import fails
    INN_ENRICHMENT_CONFIG = {
        'enabled': True,
        'auto_accept_threshold': 0.85,
        'review_threshold': 0.65,
        'providers': {
            'dadata': {'enabled': True, 'timeout_ms': 3000}
        },
        'cache': {'ttl_days': 180},
        'legal': {'allow_ip_inn': True}
    }

from .inn_search_normalizer import INNSearchNormalizer
from .inn_validator import RussianINNValidator
from .inn_data_types import INNCandidate, INNEnrichmentResult
from .inn_cache_system import INNCacheManager, INNOverrideManager


class OrganizationINNResolver:
    """Основной класс для обогащения ИНН организаций"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or INN_ENRICHMENT_CONFIG
        self.logger = logging.getLogger(__name__)
        
        # Инициализация компонентов
        self.normalizer = INNSearchNormalizer()
        self.inn_validator = RussianINNValidator()
        self.scorer = INNCandidateScorer()
        
        # Кэш и переопределения
        cache_path = Path(self.config.get('cache', {}).get('path', 'registry/inn_cache.jsonl'))
        ttl_days = self.config.get('cache', {}).get('ttl_days', 180)
        self.cache_manager = INNCacheManager(cache_path, ttl_days)
        
        overrides_path = Path(self.config.get('overrides_path', 'registry/inn_overrides.yml'))
        self.override_manager = INNOverrideManager(overrides_path)
        
        # Пороги для принятия решений
        self.auto_accept_threshold = self.config.get('auto_accept_threshold', 0.85)
        self.review_threshold = self.config.get('review_threshold', 0.65)
        
        # Инициализация провайдеров
        self.providers = self._initialize_providers()
        
        self.logger.info(f"INN Resolver initialized with auto_accept={self.auto_accept_threshold}, review={self.review_threshold}")
    
    def _initialize_providers(self) -> Dict[str, Any]:
        """Инициализация провайдеров для поиска ИНН"""
        providers = {}
        
        self.logger.info("🔧 Инициализация провайдеров для поиска ИНН...")
        
        # DaData провайдер
        dadata_config = self.config.get('providers', {}).get('dadata', {})
        
        # Детальное логирование конфигурации DaData
        self.logger.info(f"   DaData конфигурация:")
        self.logger.info(f"   - enabled: {dadata_config.get('enabled', False)}")
        
        if dadata_config.get('enabled', False):
            api_key = dadata_config.get('api_key')
            secret_key = dadata_config.get('secret_key')
            timeout_ms = dadata_config.get('timeout_ms', 3000)
            
            # Логирование статуса ключей
            self.logger.info(f"   - api_key: {'✅ Установлен' if api_key else '❌ Не установлен'}")
            self.logger.info(f"   - secret_key: {'✅ Установлен' if secret_key else '⚠️  Не установлен (опционально)'}")
            self.logger.info(f"   - timeout_ms: {timeout_ms}")
            
            if api_key:
                try:
                    from .dadata_provider import DaDataProviderAdapter
                    providers['dadata'] = DaDataProviderAdapter(
                        api_key=api_key,
                        secret_key=secret_key,
                        timeout_ms=timeout_ms
                    )
                    self.logger.info("   ✅ DaData provider успешно инициализирован")
                    
                    # Получение информации об API
                    api_info = providers['dadata'].get_api_info()
                    self.logger.info(f"   - base_url: {api_info.get('base_url')}")
                    
                except Exception as e:
                    self.logger.error(f"   ❌ Ошибка инициализации DaData provider: {e}")
                    import traceback
                    self.logger.debug(traceback.format_exc())
            else:
                self.logger.warning("   ⚠️  DaData включен, но API ключ не предоставлен")
                self.logger.warning("   💡 Проверьте переменную окружения DADATA_API_KEY в .env файле")
        else:
            self.logger.info("   ⏸️  DaData отключен в конфигурации")
        
        # TODO: Добавить другие провайдеры (ФНС, Rusprofile)
        
        # Итоговая статистика
        if providers:
            self.logger.info(f"✅ Инициализировано провайдеров: {len(providers)} ({', '.join(providers.keys())})")
        else:
            self.logger.warning("⚠️  Не инициализировано ни одного провайдера для поиска ИНН")
        
        return providers
    
    def enrich_organizations(self, organizations: Dict[int, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Обогащение списка организаций ИНН
        
        Args:
            organizations: Словарь организаций {org_id: org_data}
            
        Returns:
            Dict: Метаданные обогащения для postprocessing_metadata.enrichment.org_inn
        """
        if not self.config.get('enabled', True):
            self.logger.info("INN enrichment disabled in config")
            return {}
        
        enrichment_metadata = {}
        processed_count = 0
        
        for org_id, org_data in organizations.items():
            try:
                gid = org_data.get('gid')
                if not gid:
                    self.logger.warning(f"Organization {org_id} has no GID, skipping INN enrichment")
                    continue
                
                result = self._enrich_single_organization(org_data)
                
                if result.decision == 'auto_accept' and result.inn:
                    # Записываем ИНН в организацию
                    org_data['inn'] = result.inn
                    processed_count += 1
                
                # Сохраняем метаданные
                enrichment_metadata[gid] = {
                    'decision': result.decision,
                    'inn': result.inn,
                    'confidence': result.confidence,
                    'source': result.source,
                    'method': result.method,
                    'score': result.score,
                    'candidates': [
                        {
                            'inn': c.inn,
                            'ogrn': c.ogrn,
                            'name': c.name,
                            'name_norm': c.name_norm,
                            'city': c.city,
                            'address': c.address,
                            'opf': c.opf,
                            'score': c.score,
                            'provider': c.provider,
                            'link': c.link
                        } for c in result.candidates
                    ],
                    'checked_at': result.checked_at,
                    'auto_accept_threshold': result.auto_accept_threshold,
                    'review_threshold': result.review_threshold
                }
                
            except Exception as e:
                self.logger.error(f"Error enriching organization {org_id}: {e}")
                # Продолжаем обработку других организаций
                continue
        
        self.logger.info(f"INN enrichment completed: {processed_count} organizations enriched")
        return enrichment_metadata
    
    def _enrich_single_organization(self, org_data: Dict[str, Any]) -> INNEnrichmentResult:
        """Обогащение одной организации"""
        # 1. Skip rule: если ИНН уже валиден
        existing_inn = org_data.get('inn')
        if existing_inn and self.inn_validator.is_valid(str(existing_inn)):
            return INNEnrichmentResult(
                decision='skipped',
                inn=existing_inn,
                confidence=1.0,
                source='existing',
                method='existing_valid_inn',
                score=1.0,
                candidates=[],
                checked_at=datetime.now().isoformat(),
                auto_accept_threshold=self.auto_accept_threshold,
                review_threshold=self.review_threshold
            )
        
        # 2. Проверка переопределений
        gid = org_data.get('gid', '')
        override = self.override_manager.get_override(
            org_gid=gid,
            name_norm=self.normalizer.normalize_organization_name(org_data.get('name', '')),
            city_norm=self.normalizer.normalize_city_name(org_data.get('city', ''))
        )
        
        if override and override.inn and self.inn_validator.is_valid(override.inn):
            return INNEnrichmentResult(
                decision='override',
                inn=override.inn,
                confidence=1.0,
                source='local',
                method='manual_override',
                score=1.0,
                candidates=[],
                checked_at=datetime.now().isoformat(),
                auto_accept_threshold=self.auto_accept_threshold,
                review_threshold=self.review_threshold
            )
        
        # 3. Нормализация данных для поиска
        name_norm = self.normalizer.normalize_organization_name(org_data.get('name', ''))
        city_norm = self.normalizer.normalize_city_name(org_data.get('city', ''))
        address_norm = self.normalizer.normalize_address(org_data.get('address', ''))
        domain = self.normalizer.extract_domain(org_data.get('website', ''))
        
        if not name_norm:
            return INNEnrichmentResult(
                decision='reject',
                inn=None,
                confidence=0.0,
                source='none',
                method='empty_name',
                score=0.0,
                candidates=[],
                checked_at=datetime.now().isoformat(),
                auto_accept_threshold=self.auto_accept_threshold,
                review_threshold=self.review_threshold
            )
        
        # 4. Проверка кэша
        cached_result = self.cache_manager.get_cached_inn(name_norm, city_norm, domain)
        if cached_result:
            inn = cached_result.get('inn')
            if inn and self.inn_validator.is_valid(inn):
                return INNEnrichmentResult(
                    decision='auto_accept',
                    inn=inn,
                    confidence=cached_result.get('score', 0.9),
                    source='cache',
                    method='cache_lookup',
                    score=cached_result.get('score', 0.9),
                    candidates=[],
                    checked_at=datetime.now().isoformat(),
                    auto_accept_threshold=self.auto_accept_threshold,
                    review_threshold=self.review_threshold
                )
        
        # 5. Поиск через провайдеры
        candidates = self._search_candidates(name_norm, city_norm, address_norm, domain)
        
        if not candidates:
            return INNEnrichmentResult(
                decision='reject',
                inn=None,
                confidence=0.0,
                source='none',
                method='no_candidates_found',
                score=0.0,
                candidates=[],
                checked_at=datetime.now().isoformat(),
                auto_accept_threshold=self.auto_accept_threshold,
                review_threshold=self.review_threshold
            )
        
        # 6. Скоинг кандидатов
        for candidate in candidates:
            candidate.score = self.scorer.score_candidate(
                candidate, name_norm, city_norm, address_norm, domain
            )
        
        # Сортировка по скору
        candidates.sort(key=lambda c: c.score, reverse=True)
        best_candidate = candidates[0]
        
        # Логика принятия решений
        if (best_candidate.score >= self.auto_accept_threshold and 
            len([c for c in candidates if c.score >= self.auto_accept_threshold]) == 1):
            # Единственный кандидат с высоким скором - авто-принятие
            decision = 'auto_accept'
            
            # Сохранение в кэш
            self.cache_manager.save_to_cache(
                name_norm, city_norm, best_candidate.inn, 
                best_candidate.provider, best_candidate.score, domain
            )
            
        elif best_candidate.score >= self.review_threshold:
            # Средний скор или несколько кандидатов - ручной пересмотр
            decision = 'needs_review'
        else:
            # Низкий скор - отклонение
            decision = 'reject'
        
        return INNEnrichmentResult(
            decision=decision,
            inn=best_candidate.inn if decision == 'auto_accept' else None,
            confidence=best_candidate.score,
            source=best_candidate.provider,
            method='candidate_scoring',
            score=best_candidate.score,
            candidates=candidates,
            checked_at=datetime.now().isoformat(),
            auto_accept_threshold=self.auto_accept_threshold,
            review_threshold=self.review_threshold
        )
    
    def _search_candidates(self, name_norm: str, city_norm: str, 
                          address_norm: str, domain: str) -> List[INNCandidate]:
        """Поиск кандидатов через провайдеры"""
        all_candidates = []
        
        # Поиск через DaData
        if 'dadata' in self.providers:
            try:
                dadata_candidates = self.providers['dadata'].search_candidates(
                    name=name_norm,
                    city=city_norm,
                    address=address_norm,
                    domain=domain
                )
                all_candidates.extend(dadata_candidates)
                self.logger.debug(f"DaData returned {len(dadata_candidates)} candidates")
            except Exception as e:
                self.logger.error(f"Error searching via DaData: {e}")
        
        # TODO: Добавить поиск через другие провайдеры
        
        # Дедупликация по ИНН
        unique_candidates = self._deduplicate_candidates(all_candidates)
        
        self.logger.debug(f"Found {len(unique_candidates)} unique candidates after deduplication")
        return unique_candidates
    
    def _deduplicate_candidates(self, candidates: List[INNCandidate]) -> List[INNCandidate]:
        """Дедупликация кандидатов по ИНН"""
        seen_inns = set()
        unique_candidates = []
        
        for candidate in candidates:
            if candidate.inn not in seen_inns:
                seen_inns.add(candidate.inn)
                unique_candidates.append(candidate)
        
        return unique_candidates


class INNCandidateScorer:
    """Скоинг кандидатов для ИНН"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Веса для различных критериев
        self.weights = {
            'name_similarity': 0.4,
            'city_match': 0.25,
            'address_match': 0.15,
            'domain_match': 0.15,
            'legal_form_match': 0.05
        }
    
    def score_candidate(self, candidate: INNCandidate, 
                       search_name: str, search_city: str = "", 
                       search_address: str = "", search_domain: str = "") -> float:
        """Скоинг кандидата"""
        total_score = 0.0
        
        # 1. Схожесть названий
        name_score = self._calculate_name_similarity(search_name, candidate.name_norm)
        total_score += name_score * self.weights['name_similarity']
        
        # 2. Совпадение города
        city_score = self._calculate_city_match(search_city, candidate.city or "")
        total_score += city_score * self.weights['city_match']
        
        # 3. Совпадение адреса
        address_score = self._calculate_address_match(search_address, candidate.address or "")
        total_score += address_score * self.weights['address_match']
        
        # 4. Совпадение домена (пока не реализовано)
        domain_score = 0.0  # TODO: реализовать когда будет доступ к сайтам организаций
        total_score += domain_score * self.weights['domain_match']
        
        # 5. Совпадение юридической формы
        legal_form_score = self._calculate_legal_form_match(search_name, candidate.name)
        total_score += legal_form_score * self.weights['legal_form_match']
        
        return min(1.0, max(0.0, total_score))
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Расчет схожести названий"""
        if not name1 or not name2:
            return 0.0
        
        # Простое сравнение на основе общих слов
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_city_match(self, city1: str, city2: str) -> float:
        """Расчет совпадения городов"""
        if not city1 or not city2:
            return 0.0
        
        # Точное совпадение
        if city1.lower().strip() == city2.lower().strip():
            return 1.0
        
        # Частичное совпадение
        if city1.lower() in city2.lower() or city2.lower() in city1.lower():
            return 0.7
        
        return 0.0
    
    def _calculate_address_match(self, addr1: str, addr2: str) -> float:
        """Расчет совпадения адресов"""
        if not addr1 or not addr2:
            return 0.0
        
        # Простое сравнение на основе общих слов
        words1 = set(addr1.lower().split())
        words2 = set(addr2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        max_len = max(len(words1), len(words2))
        
        return intersection / max_len if max_len > 0 else 0.0
    
    def _calculate_legal_form_match(self, name1: str, name2: str) -> float:
        """Расчет совпадения юридических форм"""
        # Извлекаем юридические формы из названий
        forms1 = self._extract_legal_forms(name1)
        forms2 = self._extract_legal_forms(name2)
        
        if not forms1 or not forms2:
            return 0.0
        
        # Проверяем совпадения
        if forms1.intersection(forms2):
            return 1.0
        
        return 0.0
    
    def _extract_legal_forms(self, name: str) -> set:
        """Извлечение юридических форм из названия"""
        legal_forms = {'ооо', 'оао', 'пао', 'зао', 'ип', 'нко'}
        words = name.lower().split()
        return set(word.strip('.,()') for word in words if word.strip('.,()') in legal_forms)

