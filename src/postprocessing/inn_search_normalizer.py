#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Нормализация данных для ИНН поиска

Модуль содержит утилиты для нормализации названий организаций, городов, адресов
и доменов для поиска ИНН в различных источниках.

Author: Contact Parser Team
Created: 2025-10-03
"""

import re
import logging
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse


class INNSearchNormalizer:
    """Продвинутая нормализация данных для поиска ИНН"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Расширенный список юридических форм
        self.legal_forms = self._build_legal_forms_set()
        
        # Словарь синонимов городов
        self.city_synonyms = self._build_city_synonyms()
        
        # Стоп-слова для адресов
        self.address_stop_words = self._build_address_stop_words()
        
        # Паттерны для очистки
        self.cleanup_patterns = self._build_cleanup_patterns()
    
    def _build_legal_forms_set(self) -> Set[str]:
        """Построение множества юридических форм для удаления"""
        forms = {
            # Основные формы
            'ооо', 'оао', 'пао', 'зао', 'нао', 'нко',
            'ип', 'чп', 'пбоюл',  # ИП и индивидуальные предприниматели
            
            # Государственные и муниципальные
            'фбуз', 'фгбу', 'фгуп', 'фгбоу', 'фгаоу', 'фгбну',
            'гбуз', 'гбоу', 'гаоу', 'гку', 'гуп',
            'мбу', 'мбоу', 'маоу', 'мку', 'муп', 'мгуп',
            
            # Некоммерческие
            'аноо', 'ано', 'нф', 'фонд', 'автономная некоммерческая организация',
            'некоммерческая организация', 'некоммерческое партнерство',
            'общественная организация', 'религиозная организация',
            
            # Учреждения
            'учреждение', 'бюджетное учреждение', 'казенное учреждение',
            'автономное учреждение',
            
            # Коммерческие формы
            'предприятие', 'компания', 'корпорация', 'группа', 'холдинг',
            'концерн', 'трест', 'синдикат', 'консорциум',
            
            # Объединения
            'союз', 'ассоциация', 'гильдия', 'палата', 'совет',
            
            # Иностранные формы
            'ltd', 'llc', 'inc', 'corp', 'co', 'gmbh', 'ag', 'sa', 'srl',
            
            # Сокращения и вариации
            'о.о.о', 'о.а.о', 'п.а.о', 'з.а.о',
            'и.п', 'ч.п',
            'ф.г.б.у', 'г.б.у.з', 'м.б.о.у'
        }
        
        # Добавляем варианты с точками
        additional_forms = set()
        for form in forms:
            if len(form) > 2 and '.' not in form:
                # Добавляем версию с точками: ооо -> о.о.о
                dotted = '.'.join(form) + '.'
                additional_forms.add(dotted)
        
        forms.update(additional_forms)
        return forms
    
    def _build_city_synonyms(self) -> Dict[str, str]:
        """Словарь синонимов и сокращений городов"""
        return {
            # Крупные города
            'спб': 'санкт-петербург',
            'питер': 'санкт-петербург',
            'ленинград': 'санкт-петербург',
            'мск': 'москва',
            'екб': 'екатеринбург',
            'свердловск': 'екатеринбург',
            'нск': 'новосибирск',
            'нсб': 'новосибирск',
            'нск-сибирь': 'новосибирск',
            
            # Нижний Новгород
            'н.новгород': 'нижний новгород',
            'нижний-новгород': 'нижний новгород',
            'горький': 'нижний новгород',
            
            # Ростов
            'ростов-на-дону': 'ростов-на-дону',
            'ростов н/д': 'ростов-на-дону',
            'ростов-дон': 'ростов-на-дону',
            
            # Области и регионы
            'московская область': 'московская обл',
            'мо': 'московская обл',
            'ленинградская область': 'ленинградская обл',
            'ло': 'ленинградская обл',
            'свердловская область': 'свердловская обл',
            'новосибирская область': 'новосибирская обл',
            
            # Другие города
            'волгоград': 'волгоград',
            'сталинград': 'волгоград',
            'царицын': 'волгоград',
            'тольятти': 'тольятти',
            'ставрополь': 'ставрополь',
            'краснодар': 'краснодар',
            'воронеж': 'воронеж',
            'пермь': 'пермь',
            'молотов': 'пермь',
            'уфа': 'уфа',
            'красноярск': 'красноярск',
            'саратов': 'саратов',
            'тюмень': 'тюмень',
            'тольятти': 'тольятти'
        }
    
    def _build_address_stop_words(self) -> Set[str]:
        """Стоп-слова для адресов (корпуса, офисы, квартиры)"""
        return {
            'корп.', 'корпус', 'к.', 'к',
            'стр.', 'строение', 'с.', 'с',
            'оф.', 'офис', 'офиса', 'офисе',
            'кв.', 'квартира', 'кварт.',
            'пом.', 'помещение', 'помещения',
            'комн.', 'комната', 'ком.',
            'эт.', 'этаж', 'этаже',
            'подъезд', 'п.',
            'лит.', 'литер', 'литера',
            'блок', 'секция', 'сек.',
            'тер.', 'территория'
        }
    
    def _build_cleanup_patterns(self) -> List[re.Pattern]:
        """Паттерны для очистки текста"""
        return [
            re.compile(r'\s+'),  # Множественные пробелы
            re.compile(r'[^\w\s\-\.]', re.UNICODE),  # Спецсимволы кроме дефиса и точки
            re.compile(r'\.{2,}'),  # Множественные точки
            re.compile(r'\-{2,}'),  # Множественные дефисы
        ]
    
    def normalize_organization_name(self, name: str) -> str:
        """
        Продвинутая нормализация названия организации
        
        Args:
            name: Исходное название
            
        Returns:
            str: Нормализованное название
        """
        if not name or not name.strip():
            return ""
        
        # Приведение к нижнему регистру
        normalized = name.lower().strip()
        
        # Удаление кавычек всех типов
        quotes = '«»""\'`""„"‚''‛‟'
        for quote in quotes:
            normalized = normalized.replace(quote, ' ')
        
        # Замена дефисов на пробелы для лучшего сравнения
        # "днк-технология" -> "днк технология"
        normalized = normalized.replace('-', ' ')
        
        # Удаление скобок и их содержимого в некоторых случаях
        # Оставляем скобки если они содержат важную информацию
        normalized = re.sub(r'\([^)]*\)', ' ', normalized)
        normalized = re.sub(r'\[[^\]]*\]', ' ', normalized)
        
        # Разбивка на слова
        words = normalized.split()
        filtered_words = []
        
        i = 0
        while i < len(words):
            word = words[i].strip('.,()[]{}!?;:')
            
            # Проверяем юридические формы
            if word in self.legal_forms:
                i += 1
                continue
            
            # Проверяем составные юридические формы (например, "общество с ограниченной ответственностью")
            if i < len(words) - 3:
                phrase = ' '.join(words[i:i+4])
                if phrase in self.legal_forms:
                    i += 4
                    continue
            
            if i < len(words) - 2:
                phrase = ' '.join(words[i:i+3])
                if phrase in self.legal_forms:
                    i += 3
                    continue
            
            if i < len(words) - 1:
                phrase = ' '.join(words[i:i+2])
                if phrase in self.legal_forms:
                    i += 2
                    continue
            
            # Фильтрация очень коротких слов (меньше 2 символов)
            if len(word) >= 2:
                filtered_words.append(word)
            
            i += 1
        
        result = ' '.join(filtered_words)
        
        # Применение паттернов очистки
        for pattern in self.cleanup_patterns:
            if pattern == self.cleanup_patterns[0]:  # Множественные пробелы
                result = pattern.sub(' ', result)
            else:
                result = pattern.sub('', result)
        
        return result.strip()
    
    def normalize_city_name(self, city: str) -> str:
        """
        Нормализация названия города
        
        Args:
            city: Исходное название города
            
        Returns:
            str: Нормализованное название города
        """
        if not city or not city.strip():
            return ""
        
        normalized = city.lower().strip()
        
        # Удаление префиксов
        prefixes = ['г.', 'город', 'гор.', 'г ', 'city']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        # Удаление суффиксов
        suffixes = ['обл.', 'область', 'оbl', 'респ.', 'республика', 'край', 'округ']
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        # Применение синонимов
        if normalized in self.city_synonyms:
            normalized = self.city_synonyms[normalized]
        
        # Очистка от спецсимволов
        normalized = re.sub(r'[^\w\s\-]', '', normalized, flags=re.UNICODE)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def normalize_address(self, address: str) -> str:
        """
        Нормализация адреса (извлечение улицы и дома)
        
        Args:
            address: Исходный адрес
            
        Returns:
            str: Нормализованный адрес (улица + дом)
        """
        if not address or not address.strip():
            return ""
        
        normalized = address.lower().strip()
        
        # Удаление города в начале адреса
        city_prefixes = ['г.', 'город', 'г ', 'гор.']
        for prefix in city_prefixes:
            if normalized.startswith(prefix):
                # Ищем запятую после города
                comma_idx = normalized.find(',', len(prefix))
                if comma_idx != -1:
                    normalized = normalized[comma_idx + 1:].strip()
                break
        
        # Поиск стоп-слов и обрезка
        words = normalized.split()
        filtered_words = []
        
        for word in words:
            clean_word = word.strip('.,()[]')
            if clean_word in self.address_stop_words:
                break  # Обрезаем на первом стоп-слове
            filtered_words.append(word)
        
        result = ' '.join(filtered_words).strip()
        
        # Очистка от лишних символов
        result = re.sub(r'[^\w\s\-\.]', ' ', result, flags=re.UNICODE)
        result = re.sub(r'\s+', ' ', result)
        
        return result.strip()
    
    def extract_domain(self, url_or_domain: str) -> str:
        """
        Извлечение и нормализация домена (e2LD)
        
        Args:
            url_or_domain: URL или домен
            
        Returns:
            str: Нормализованный домен второго уровня
        """
        if not url_or_domain or not url_or_domain.strip():
            return ""
        
        url = url_or_domain.strip().lower()
        
        # Добавляем схему если отсутствует для корректного парсинга
        if not url.startswith(('http://', 'https://', 'ftp://')):
            url = 'http://' + url
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
            
            # Удаление порта
            if ':' in domain:
                domain = domain.split(':')[0]
            
            # Удаление www и других поддоменов, оставляем e2LD
            parts = domain.split('.')
            if len(parts) >= 2:
                # Извлекаем домен второго уровня
                if len(parts) >= 3 and parts[0] in ['www', 'www2', 'www3', 'm', 'mobile', 'app']:
                    return f"{parts[-2]}.{parts[-1]}"
                else:
                    return f"{parts[-2]}.{parts[-1]}"
            
            return domain
            
        except Exception as e:
            self.logger.warning(f"Failed to parse domain from '{url_or_domain}': {e}")
            # Fallback: простое извлечение
            clean_domain = url_or_domain.strip().lower()
            for protocol in ['https://', 'http://', 'ftp://']:
                if clean_domain.startswith(protocol):
                    clean_domain = clean_domain[len(protocol):]
                    break
            
            if '/' in clean_domain:
                clean_domain = clean_domain.split('/')[0]
            
            return clean_domain
    
    def generate_search_variants(self, name: str) -> List[str]:
        """
        Генерация вариантов названия для поиска
        
        Args:
            name: Исходное название
            
        Returns:
            List[str]: Варианты для поиска
        """
        if not name:
            return []
        
        variants = set()
        
        # Основная нормализация
        normalized = self.normalize_organization_name(name)
        if normalized:
            variants.add(normalized)
        
        # Вариант без дефисов
        no_hyphens = normalized.replace('-', ' ')
        if no_hyphens != normalized:
            variants.add(no_hyphens)
        
        # Вариант с дефисами как один символ
        with_hyphens = normalized.replace(' ', '-')
        if with_hyphens != normalized and len(with_hyphens.split('-')) > 1:
            variants.add(with_hyphens)
        
        # Вариант только ключевых слов (без коротких слов)
        words = normalized.split()
        key_words = [w for w in words if len(w) > 3]
        if len(key_words) > 1:
            variants.add(' '.join(key_words))
        
        # Удаление пустых вариантов
        return [v for v in variants if v.strip()]
    
    def create_search_key(self, name: str, city: str = "", address: str = "", domain: str = "") -> str:
        """
        Создание ключа для поиска/кэширования
        
        Args:
            name: Название организации
            city: Город
            address: Адрес
            domain: Домен
            
        Returns:
            str: Хэш-ключ для поиска
        """
        normalized_name = self.normalize_organization_name(name)
        normalized_city = self.normalize_city_name(city)
        normalized_domain = self.extract_domain(domain)
        
        # Создаем составной ключ
        key_parts = [
            normalized_name,
            normalized_city,
            normalized_domain
        ]
        
        # Фильтруем пустые части
        key_parts = [part for part in key_parts if part.strip()]
        
        return '|'.join(key_parts)


# Экспорт основного класса
__all__ = ['INNSearchNormalizer']