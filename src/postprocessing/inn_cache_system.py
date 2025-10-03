#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💾 Система кэша и переопределений для ИНН

Модуль для управления кэшем найденных ИНН и ручными переопределениями
с поддержкой TTL, атомарных операций и валидации.

Author: Contact Parser Team
Created: 2025-10-03
"""

import json
import yaml
import logging
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import fcntl
import os


@dataclass
class CacheEntry:
    """Запись в кэше ИНН"""
    key: str
    name_norm: str
    city_norm: str
    domain: str
    inn: str
    source: str
    score: float
    checked_at: str
    
    def is_expired(self, ttl_days: int) -> bool:
        """Проверка истечения TTL"""
        try:
            checked_date = datetime.fromisoformat(self.checked_at)
            return datetime.now() - checked_date > timedelta(days=ttl_days)
        except (ValueError, TypeError):
            return True  # Считаем истекшим если не можем распарсить дату


@dataclass
class OverrideEntry:
    """Запись переопределения ИНН"""
    org_gid: Optional[str] = None
    name_norm: Optional[str] = None
    city_norm: Optional[str] = None
    inn: str = ""
    reason: str = ""
    confirmed_by: str = ""
    confirmed_at: str = ""
    
    def matches_organization(self, org_gid: str = "", name_norm: str = "", 
                           city_norm: str = "") -> bool:
        """Проверка соответствия организации"""
        # Приоритет GID
        if self.org_gid and org_gid:
            return self.org_gid == org_gid
        
        # Резервный поиск по названию + городу
        if self.name_norm and self.city_norm and name_norm and city_norm:
            return (self.name_norm == name_norm and 
                   self.city_norm == city_norm)
        
        return False


class INNCacheManager:
    """Управление кэшем ИНН с поддержкой TTL и атомарных операций"""
    
    def __init__(self, cache_path: Path, ttl_days: int = 180):
        self.cache_path = cache_path
        self.ttl_days = ttl_days
        self.logger = logging.getLogger(__name__)
        
        # Создание директории если не существует
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Инициализация файла кэша если не существует
        if not self.cache_path.exists():
            self.cache_path.touch()
    
    def generate_cache_key(self, name_norm: str, city_norm: str, domain: str = "") -> str:
        """Генерация уникального ключа кэша"""
        key_data = f"{name_norm}|{city_norm}|{domain}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def get_cached_inn(self, name_norm: str, city_norm: str, domain: str = "") -> Optional[Dict[str, Any]]:
        """
        Получение ИНН из кэша
        
        Args:
            name_norm: Нормализованное название
            city_norm: Нормализованный город
            domain: Домен
            
        Returns:
            Optional[Dict]: Данные из кэша или None
        """
        cache_key = self.generate_cache_key(name_norm, city_norm, domain)
        
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                # Блокировка файла для чтения
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry_data = json.loads(line)
                        entry = CacheEntry(**entry_data)
                        
                        if entry.key == cache_key:
                            # Проверка TTL
                            if entry.is_expired(self.ttl_days):
                                self.logger.debug(f"Cache entry expired for key: {cache_key}")
                                return None
                            
                            self.logger.debug(f"Cache hit for key: {cache_key}")
                            return {
                                'inn': entry.inn,
                                'source': entry.source,
                                'score': entry.score,
                                'checked_at': entry.checked_at
                            }
                    except (json.JSONDecodeError, TypeError) as e:
                        self.logger.warning(f"Invalid cache entry: {line[:50]}... Error: {e}")
                        continue
                
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
        except FileNotFoundError:
            self.logger.debug("Cache file not found")
        except Exception as e:
            self.logger.error(f"Error reading cache: {e}")
        
        return None
    
    def save_to_cache(self, name_norm: str, city_norm: str, inn: str, 
                     source: str, score: float, domain: str = "") -> bool:
        """
        Сохранение ИНН в кэш
        
        Args:
            name_norm: Нормализованное название
            city_norm: Нормализованный город
            inn: ИНН
            source: Источник данных
            score: Скор доверия
            domain: Домен
            
        Returns:
            bool: Успешность операции
        """
        cache_key = self.generate_cache_key(name_norm, city_norm, domain)
        
        entry = CacheEntry(
            key=cache_key,
            name_norm=name_norm,
            city_norm=city_norm,
            domain=domain,
            inn=inn,
            source=source,
            score=score,
            checked_at=datetime.now().isoformat()
        )
        
        try:
            # Атомарная запись в файл
            with open(self.cache_path, 'a', encoding='utf-8') as f:
                # Блокировка файла для записи
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                f.write(json.dumps(asdict(entry), ensure_ascii=False) + '\n')
                f.flush()
                os.fsync(f.fileno())  # Принудительная синхронизация с диском
                
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            self.logger.debug(f"Saved to cache: {cache_key} -> {inn}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving to cache: {e}")
            return False
    
    def cleanup_expired_entries(self) -> int:
        """
        Очистка истекших записей из кэша
        
        Returns:
            int: Количество удаленных записей
        """
        if not self.cache_path.exists():
            return 0
        
        valid_entries = []
        expired_count = 0
        
        try:
            # Чтение всех записей
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry_data = json.loads(line)
                        entry = CacheEntry(**entry_data)
                        
                        if not entry.is_expired(self.ttl_days):
                            valid_entries.append(line)
                        else:
                            expired_count += 1
                    except (json.JSONDecodeError, TypeError):
                        expired_count += 1  # Невалидные записи тоже удаляем
                
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Перезапись файла без истекших записей
            if expired_count > 0:
                with open(self.cache_path, 'w', encoding='utf-8') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    
                    for entry in valid_entries:
                        f.write(entry + '\n')
                    
                    f.flush()
                    os.fsync(f.fileno())
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
                self.logger.info(f"Cleaned up {expired_count} expired cache entries")
            
            return expired_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        stats = {
            'total_entries': 0,
            'expired_entries': 0,
            'valid_entries': 0,
            'cache_file_size': 0,
            'oldest_entry': None,
            'newest_entry': None
        }
        
        if not self.cache_path.exists():
            return stats
        
        try:
            stats['cache_file_size'] = self.cache_path.stat().st_size
            
            oldest_date = None
            newest_date = None
            
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    stats['total_entries'] += 1
                    
                    try:
                        entry_data = json.loads(line)
                        entry = CacheEntry(**entry_data)
                        
                        if entry.is_expired(self.ttl_days):
                            stats['expired_entries'] += 1
                        else:
                            stats['valid_entries'] += 1
                        
                        # Отслеживание дат
                        try:
                            entry_date = datetime.fromisoformat(entry.checked_at)
                            if oldest_date is None or entry_date < oldest_date:
                                oldest_date = entry_date
                            if newest_date is None or entry_date > newest_date:
                                newest_date = entry_date
                        except (ValueError, TypeError):
                            pass
                            
                    except (json.JSONDecodeError, TypeError):
                        stats['expired_entries'] += 1  # Невалидные записи считаем истекшими
            
            if oldest_date:
                stats['oldest_entry'] = oldest_date.isoformat()
            if newest_date:
                stats['newest_entry'] = newest_date.isoformat()
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
        
        return stats


class INNOverrideManager:
    """Управление переопределениями ИНН"""
    
    def __init__(self, overrides_path: Path):
        self.overrides_path = overrides_path
        self.logger = logging.getLogger(__name__)
        
        # Создание директории если не существует
        self.overrides_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Инициализация файла переопределений если не существует
        if not self.overrides_path.exists():
            self._initialize_overrides_file()
    
    def _initialize_overrides_file(self):
        """Инициализация файла переопределений"""
        initial_content = {
            'org_overrides': [],
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'description': 'Ручные переопределения ИНН для организаций'
            }
        }
        
        try:
            with open(self.overrides_path, 'w', encoding='utf-8') as f:
                yaml.dump(initial_content, f, allow_unicode=True, default_flow_style=False)
            
            self.logger.info(f"Initialized overrides file: {self.overrides_path}")
        except Exception as e:
            self.logger.error(f"Error initializing overrides file: {e}")
    
    def get_override(self, org_gid: str = "", name_norm: str = "", 
                    city_norm: str = "") -> Optional[OverrideEntry]:
        """
        Получение переопределения для организации
        
        Args:
            org_gid: GID организации
            name_norm: Нормализованное название
            city_norm: Нормализованный город
            
        Returns:
            Optional[OverrideEntry]: Переопределение или None
        """
        try:
            with open(self.overrides_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            overrides = data.get('org_overrides', [])
            
            for override_data in overrides:
                try:
                    override = OverrideEntry(**override_data)
                    if override.matches_organization(org_gid, name_norm, city_norm):
                        self.logger.debug(f"Found override for org: {org_gid or name_norm}")
                        return override
                except TypeError as e:
                    self.logger.warning(f"Invalid override entry: {override_data}. Error: {e}")
                    continue
            
        except FileNotFoundError:
            self.logger.debug("Overrides file not found")
        except Exception as e:
            self.logger.error(f"Error reading overrides: {e}")
        
        return None
    
    def add_override(self, org_gid: str, inn: str, reason: str, 
                    confirmed_by: str = "system", name_norm: str = "", 
                    city_norm: str = "") -> bool:
        """
        Добавление нового переопределения
        
        Args:
            org_gid: GID организации
            inn: ИНН
            reason: Причина переопределения
            confirmed_by: Кто подтвердил
            name_norm: Нормализованное название (резерв)
            city_norm: Нормализованный город (резерв)
            
        Returns:
            bool: Успешность операции
        """
        try:
            # Чтение существующих данных
            try:
                with open(self.overrides_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
            except FileNotFoundError:
                data = {'org_overrides': [], 'metadata': {}}
            
            # Создание новой записи
            new_override = OverrideEntry(
                org_gid=org_gid,
                name_norm=name_norm or None,
                city_norm=city_norm or None,
                inn=inn,
                reason=reason,
                confirmed_by=confirmed_by,
                confirmed_at=datetime.now().isoformat()
            )
            
            # Проверка на дубликаты
            overrides = data.get('org_overrides', [])
            for i, existing in enumerate(overrides):
                existing_entry = OverrideEntry(**existing)
                if existing_entry.matches_organization(org_gid, name_norm, city_norm):
                    # Обновляем существующую запись
                    overrides[i] = asdict(new_override)
                    self.logger.info(f"Updated existing override for org: {org_gid}")
                    break
            else:
                # Добавляем новую запись
                overrides.append(asdict(new_override))
                self.logger.info(f"Added new override for org: {org_gid}")
            
            data['org_overrides'] = overrides
            data['metadata']['updated_at'] = datetime.now().isoformat()
            
            # Сохранение
            with open(self.overrides_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding override: {e}")
            return False
    
    def remove_override(self, org_gid: str = "", name_norm: str = "", 
                       city_norm: str = "") -> bool:
        """
        Удаление переопределения
        
        Args:
            org_gid: GID организации
            name_norm: Нормализованное название
            city_norm: Нормализованный город
            
        Returns:
            bool: Успешность операции
        """
        try:
            with open(self.overrides_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            overrides = data.get('org_overrides', [])
            original_count = len(overrides)
            
            # Фильтрация переопределений
            filtered_overrides = []
            for override_data in overrides:
                try:
                    override = OverrideEntry(**override_data)
                    if not override.matches_organization(org_gid, name_norm, city_norm):
                        filtered_overrides.append(override_data)
                except TypeError:
                    # Сохраняем невалидные записи как есть
                    filtered_overrides.append(override_data)
            
            removed_count = original_count - len(filtered_overrides)
            
            if removed_count > 0:
                data['org_overrides'] = filtered_overrides
                data['metadata']['updated_at'] = datetime.now().isoformat()
                
                with open(self.overrides_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
                
                self.logger.info(f"Removed {removed_count} override(s) for org: {org_gid or name_norm}")
                return True
            else:
                self.logger.info(f"No overrides found to remove for org: {org_gid or name_norm}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error removing override: {e}")
            return False
    
    def validate_overrides(self) -> Dict[str, Any]:
        """
        Валидация файла переопределений
        
        Returns:
            Dict: Результат валидации
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'total_overrides': 0,
            'valid_overrides': 0,
            'invalid_overrides': 0
        }
        
        try:
            with open(self.overrides_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            overrides = data.get('org_overrides', [])
            result['total_overrides'] = len(overrides)
            
            seen_gids = set()
            
            for i, override_data in enumerate(overrides):
                try:
                    override = OverrideEntry(**override_data)
                    
                    # Проверка обязательных полей
                    if not override.inn:
                        result['errors'].append(f"Override {i}: missing INN")
                        result['invalid_overrides'] += 1
                        continue
                    
                    if not override.org_gid and not (override.name_norm and override.city_norm):
                        result['errors'].append(f"Override {i}: missing org_gid or name+city")
                        result['invalid_overrides'] += 1
                        continue
                    
                    # Проверка дубликатов по GID
                    if override.org_gid:
                        if override.org_gid in seen_gids:
                            result['warnings'].append(f"Override {i}: duplicate org_gid {override.org_gid}")
                        else:
                            seen_gids.add(override.org_gid)
                    
                    result['valid_overrides'] += 1
                    
                except TypeError as e:
                    result['errors'].append(f"Override {i}: invalid structure - {e}")
                    result['invalid_overrides'] += 1
            
            if result['errors']:
                result['valid'] = False
            
        except FileNotFoundError:
            result['errors'].append("Overrides file not found")
            result['valid'] = False
        except Exception as e:
            result['errors'].append(f"Error reading overrides file: {e}")
            result['valid'] = False
        
        return result


# Экспорт основных классов
__all__ = [
    'CacheEntry',
    'OverrideEntry', 
    'INNCacheManager',
    'INNOverrideManager'
]