#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏢 OrgLocationEnrichment - обогащение организаций данными о местоположении
Реализация TASK-008A: применение доказательств локации к организациям

Author: Contact Parser Team
Created: 2025-09-29
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from .attachment_evidence_extractor import LocationEvidence


@dataclass
class OrgLocationEnrichmentConfig:
    """Конфигурация для обогащения локации организаций"""
    enabled: bool = True
    apply_if_empty_only: bool = True  # Заполнять только пустые поля
    prefer_fields: List[str] = field(default_factory=lambda: ["city", "address"])
    log_metadata: bool = True
    fuzzy_match_threshold: float = 0.7  # Снижен с 0.9 для лучшего matching
    max_conflicts_to_review: int = 3


@dataclass
class LocationEnrichmentMetadata:
    """Метаданные обогащения локации"""
    applied: bool = False
    city: Optional[str] = None
    address: Optional[str] = None
    source: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    needs_review: bool = False
    conflicts: List[Dict[str, Any]] = field(default_factory=list)


class OrgLocationEnrichment:
    """
    🏢 Обогащение организаций данными о местоположении
    
    Применяет доказательства локации из вложений к организациям,
    заполняя пустые поля city/address с записью метаданных.
    """
    
    def __init__(self, config: Optional[OrgLocationEnrichmentConfig] = None):
        """
        Инициализация обогащения
        
        Args:
            config: Конфигурация обогащения
        """
        self.config = config or OrgLocationEnrichmentConfig()
        self.logger = logging.getLogger(__name__)
        
        # Статистика обогащения
        self.stats = {
            'organizations_processed': 0,
            'organizations_enriched': 0,
            'cities_added': 0,
            'addresses_added': 0,
            'conflicts_detected': 0,
            'evidence_applied': 0
        }
    
    def enrich_organizations(self, organizations: Dict[int, Dict[str, Any]], 
                           evidence_list: List[LocationEvidence],
                           postprocessing_metadata: Optional[Dict[str, Any]] = None) -> Dict[int, Dict[str, Any]]:
        """
        Обогащение организаций данными о местоположении
        
        Args:
            organizations: Словарь организаций {gid: org_data}
            evidence_list: Список доказательств локации
            postprocessing_metadata: Метаданные постобработки
            
        Returns:
            Dict: Обогащенные организации
        """
        if not self.config.enabled or not evidence_list:
            return organizations
        
        self.logger.info(f"🏢 Обогащаем {len(organizations)} организаций из {len(evidence_list)} доказательств")
        
        # Инициализируем метаданные
        if postprocessing_metadata is None:
            postprocessing_metadata = {}
        if 'location_evidence' not in postprocessing_metadata:
            postprocessing_metadata['location_evidence'] = {}
        
        enriched_organizations = organizations.copy()
        
        for org_gid, org_data in enriched_organizations.items():
            self.stats['organizations_processed'] += 1
            
            try:
                # Находим подходящие доказательства для организации
                matching_evidence = self._find_matching_evidence(org_data, evidence_list)
                
                if matching_evidence:
                    # Применяем обогащение
                    enrichment_result = self._apply_enrichment(org_data, matching_evidence)
                    
                    # Обновляем организацию
                    enriched_organizations[org_gid] = enrichment_result['organization']
                    
                    # Записываем метаданные
                    if self.config.log_metadata:
                        postprocessing_metadata['location_evidence'][org_gid] = enrichment_result['metadata']
                    
                    # metadata теперь словарь, используем доступ по ключу
                    metadata_dict = enrichment_result['metadata']
                    if metadata_dict.get('applied'):
                        self.stats['organizations_enriched'] += 1
                        self.stats['evidence_applied'] += len(matching_evidence)
                        
                        if metadata_dict.get('city'):
                            self.stats['cities_added'] += 1
                        if metadata_dict.get('address'):
                            self.stats['addresses_added'] += 1
                    
                    if metadata_dict.get('needs_review'):
                        self.stats['conflicts_detected'] += 1
                        
            except Exception as e:
                self.logger.error(f"Ошибка обогащения организации {org_gid}: {e}")
        
        self.logger.info(f"✅ Обогащено {self.stats['organizations_enriched']} организаций")
        return enriched_organizations
    
    def _find_matching_evidence(self, org_data: Dict[str, Any], 
                              evidence_list: List[LocationEvidence]) -> List[LocationEvidence]:
        """Поиск подходящих доказательств для организации"""
        matching_evidence = []
        org_name = org_data.get('name', '')
        
        if not org_name:
            return matching_evidence
        
        # Нормализуем название организации
        org_name_norm = self._normalize_organization_name(org_name)
        
        for evidence in evidence_list:
            # Проверяем совпадение по нормализованному названию
            similarity = SequenceMatcher(None, org_name_norm, evidence.org_name_norm).ratio()
            
            if similarity >= self.config.fuzzy_match_threshold:
                matching_evidence.append(evidence)
                continue
            
            # Проверяем совпадение по домену email (если есть)
            if self._check_domain_match(org_data, evidence):
                matching_evidence.append(evidence)
        
        # Сортируем по уверенности
        matching_evidence.sort(key=lambda x: x.confidence, reverse=True)
        
        return matching_evidence
    
    def _check_domain_match(self, org_data: Dict[str, Any], evidence: LocationEvidence) -> bool:
        """Проверка совпадения по домену email"""
        # Пока не реализовано, можно добавить позже
        # Нужно извлекать домены из контактов организации и сравнивать с доменами в evidence
        return False
    
    def _apply_enrichment(self, org_data: Dict[str, Any], 
                         matching_evidence: List[LocationEvidence]) -> Dict[str, Any]:
        """Применение обогащения к организации"""
        enriched_org = org_data.copy()
        metadata = LocationEnrichmentMetadata()
        
        # Проверяем нужно ли обогащение
        current_city = org_data.get('city')
        current_address = org_data.get('address')
        
        if self.config.apply_if_empty_only:
            needs_city = not current_city
            needs_address = not current_address
        else:
            needs_city = True
            needs_address = True
        
        if not needs_city and not needs_address:
            return {'organization': enriched_org, 'metadata': metadata}
        
        # Собираем кандидатов для обогащения
        city_candidates = []
        address_candidates = []
        
        for evidence in matching_evidence:
            if evidence.city and needs_city:
                city_candidates.append({
                    'value': evidence.city,
                    'evidence': evidence,
                    'confidence': evidence.confidence
                })
            
            if evidence.address and needs_address:
                address_candidates.append({
                    'value': evidence.address,
                    'evidence': evidence,
                    'confidence': evidence.confidence
                })
        
        # Применяем обогащение города
        if city_candidates:
            city_result = self._resolve_candidates(city_candidates, 'city')
            if city_result['value'] and not city_result['conflict']:
                enriched_org['city'] = city_result['value']
                metadata.city = city_result['value']
                metadata.applied = True
            elif city_result['conflict']:
                metadata.needs_review = True
                metadata.conflicts.extend(city_result['conflicts'])
        
        # Применяем обогащение адреса
        if address_candidates:
            address_result = self._resolve_candidates(address_candidates, 'address')
            if address_result['value'] and not address_result['conflict']:
                address_value = address_result['value']
                
                # 🛡️ ЗАЩИТА: Фильтр "только индекс"
                # Если адрес состоит только из 6 цифр (индекс) - это не полный адрес
                import re
                if re.match(r'^\d{6}$', address_value.strip()):
                    self.logger.debug(f"Отклонен адрес-индекс при обогащении: {address_value}")
                    address_value = None
                
                # 🛡️ ЗАЩИТА: Фильтр "слишком короткий адрес"
                # Если адрес короче 20 символов и нет города - скорее всего это мусор
                if address_value and len(address_value) < 20 and not enriched_org.get('city'):
                    self.logger.debug(f"Отклонен короткий адрес без города при обогащении: {address_value}")
                    address_value = None
                
                # Применяем только если адрес прошел фильтры
                if address_value:
                    enriched_org['address'] = address_value
                    metadata.address = address_value
                    metadata.applied = True
            elif address_result['conflict']:
                metadata.needs_review = True
                metadata.conflicts.extend(address_result['conflicts'])
        
        # Записываем источник и уверенность
        if metadata.applied:
            best_evidence = max(matching_evidence, key=lambda x: x.confidence)
            metadata.source = best_evidence.source
            metadata.confidence = best_evidence.confidence
        
        # Преобразуем metadata в словарь для JSON-сериализации
        from dataclasses import asdict
        return {'organization': enriched_org, 'metadata': asdict(metadata)}
    
    def _resolve_candidates(self, candidates: List[Dict[str, Any]], field_type: str) -> Dict[str, Any]:
        """Разрешение конфликтов между кандидатами"""
        if not candidates:
            return {'value': None, 'conflict': False, 'conflicts': []}
        
        if len(candidates) == 1:
            return {
                'value': candidates[0]['value'],
                'conflict': False,
                'conflicts': []
            }
        
        # Группируем по значению
        value_groups = {}
        for candidate in candidates:
            value = candidate['value'].strip().lower()
            if value not in value_groups:
                value_groups[value] = []
            value_groups[value].append(candidate)
        
        # Если все кандидаты одинаковые - нет конфликта
        if len(value_groups) == 1:
            best_candidate = max(candidates, key=lambda x: x['confidence'])
            return {
                'value': best_candidate['value'],
                'conflict': False,
                'conflicts': []
            }
        
        # Есть конфликт - выбираем лучший по confidence или отмечаем для ревью
        if len(value_groups) <= self.config.max_conflicts_to_review:
            best_candidate = max(candidates, key=lambda x: x['confidence'])
            conflicts = [
                {
                    'field': field_type,
                    'value': candidate['value'],
                    'confidence': candidate['confidence'],
                    'source': candidate['evidence'].source
                }
                for candidate in candidates
            ]
            
            return {
                'value': best_candidate['value'],
                'conflict': True,
                'conflicts': conflicts
            }
        else:
            # Слишком много конфликтов - не применяем
            return {
                'value': None,
                'conflict': True,
                'conflicts': [{'field': field_type, 'reason': 'too_many_conflicts'}]
            }
    
    def _normalize_organization_name(self, org_name: str) -> str:
        """Нормализация названия организации для сравнения"""
        import re
        
        normalized = org_name.lower().strip()
        
        # Убираем кавычки
        normalized = re.sub(r'[«»""\'"]', '', normalized)
        
        # Убираем юридические формы
        legal_forms = ['ооо', 'зао', 'оао', 'пао', 'ао', 'ип', 'фбуз', 'гбуз']
        for form in legal_forms:
            pattern = r'\b' + re.escape(form) + r'\b'
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Нормализуем пробелы
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики обогащения"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            'organizations_processed': 0,
            'organizations_enriched': 0,
            'cities_added': 0,
            'addresses_added': 0,
            'conflicts_detected': 0,
            'evidence_applied': 0
        }


# Пример использования
if __name__ == "__main__":
    from .attachment_evidence_extractor import LocationEvidence
    
    # Тестовые данные
    test_organizations = {
        1: {
            'name': 'ООО "МИЛЛАБ"',
            'city': None,
            'address': None
        }
    }
    
    test_evidence = [
        LocationEvidence(
            org_name_norm='миллаб',
            matched_name='ООО "МИЛЛАБ"',
            city='Москва',
            address='117105, г. Москва, Варшавское шоссе, д. 17',
            source={
                'type': 'attachment',
                'filename': 'КП_МИЛЛАБ.txt',
                'snippet': 'Юридический адрес: 117105, г. Москва...'
            },
            confidence=0.9
        )
    ]
    
    enrichment = OrgLocationEnrichment()
    metadata = {}
    
    enriched_orgs = enrichment.enrich_organizations(
        test_organizations, test_evidence, metadata
    )
    
    print("🏢 Тестирование OrgLocationEnrichment:")
    for gid, org in enriched_orgs.items():
        print(f"  Организация {gid}: {org['name']}")
        print(f"  Город: {org.get('city', 'не указан')}")
        print(f"  Адрес: {org.get('address', 'не указан')}")
        
        if gid in metadata.get('location_evidence', {}):
            evidence_meta = metadata['location_evidence'][gid]
            print(f"  Применено: {evidence_meta.get('applied')}")
            print(f"  Уверенность: {evidence_meta.get('confidence')}")
        print()