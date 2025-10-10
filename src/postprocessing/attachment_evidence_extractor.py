#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📎 AttachmentEvidenceExtractor - извлечение доказательств локации организаций из вложений
Реализация TASK-008A: обогащение organizations.city/address из реальных вложений

УПРОЩЕННАЯ ЛОГИКА:
1. Берем ВСЕ вложения из конкретного письма
2. Ищем для них OCR-тексты в data/ocr/texts/YYYY-MM-DD/
3. Анализируем ВСЕ найденные тексты на предмет организаций и их локации
4. Обогащаем данные из любых найденных источников

Никакой фильтрации по именам файлов - обрабатываем все вложения с OCR-текстом!

Author: Contact Parser Team
Created: 2025-09-29
Updated: 2025-10-10 - миграция на data/ocr
"""

import re
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class AttachmentEvidenceConfig:
    """Конфигурация для извлечения доказательств из вложений"""
    enabled: bool = True
    
    # Пороги для поиска
    max_snippet_len: int = 240
    
    # Юридические формы для нормализации
    legal_forms: List[str] = field(default_factory=lambda: [
        "ооо", "зао", "оао", "пао", "ао", "ип", "фбуз", "гбуз", 
        "фгбу", "фгуп", "гуп", "муп", "нко", "llc", "ltd", "inc"
    ])


@dataclass
class LocationEvidence:
    """Доказательство локации организации из вложения"""
    org_name_norm: str          # нормализованное имя из вложения
    matched_name: str           # как встретилось в тексте
    city: Optional[str] = None  # найденный город
    address: Optional[str] = None  # найденный адрес
    source: Dict[str, Any] = field(default_factory=dict)  # источник
    confidence: float = 0.0     # уверенность в данных


class AttachmentEvidenceExtractor:
    """
    📎 Извлекатель доказательств локации организаций из вложений
    
    УПРОЩЕННАЯ ЛОГИКА: анализирует OCR-тексты ВСЕХ вложений письма
    и извлекает информацию о местоположении организаций.
    Никакой фильтрации - обрабатываем все вложения с OCR-текстом!
    """
    
    def __init__(self, config: Optional[AttachmentEvidenceConfig] = None):
        """
        Инициализация извлекателя
        
        Args:
            config: Конфигурация извлечения
        """
        self.config = config or AttachmentEvidenceConfig()
        self.logger = logging.getLogger(__name__)
        
        # Компилируем регулярные выражения для производительности
        self._city_patterns = [
            re.compile(r'\bг\.?\s+([А-ЯЁ][а-яё\-\s]{2,30})', re.IGNORECASE | re.UNICODE),
            re.compile(r'город\s+([А-ЯЁ][а-яё\-\s]{2,30})', re.IGNORECASE | re.UNICODE),
            re.compile(r'\b([А-ЯЁ][а-яё\-\s]{2,30})\s+г\.?', re.IGNORECASE | re.UNICODE),
        ]
        
        self._address_patterns = [
            re.compile(r'(?:юридический\s+)?адрес[:\s]+(.{10,140})', re.IGNORECASE | re.UNICODE),
            re.compile(r'фактический\s+адрес[:\s]+(.{10,140})', re.IGNORECASE | re.UNICODE),
            re.compile(r'\b(\d{6}),?\s+([^,\n]{10,100})', re.UNICODE),  # индекс + адрес
            re.compile(r'местонахождение[:\s]+(.{10,140})', re.IGNORECASE | re.UNICODE),
        ]
        
        # Паттерны для очистки адресов
        self._address_cleanup_patterns = [
            re.compile(r'\s*тел\.?[:\s].*$', re.IGNORECASE),
            re.compile(r'\s*телефон[:\s].*$', re.IGNORECASE),
            re.compile(r'\s*e-?mail[:\s].*$', re.IGNORECASE),
            re.compile(r'\s*факс[:\s].*$', re.IGNORECASE),
            re.compile(r'\s*сайт[:\s].*$', re.IGNORECASE),
        ]
    
    def extract(self, email_data: Dict[str, Any]) -> List[LocationEvidence]:
        """
        Извлечение доказательств локации из вложений письма
        
        УПРОЩЕННАЯ ЛОГИКА:
        1. Берем ВСЕ вложения из письма
        2. Ищем для них OCR-тексты в data/ocr/texts/YYYY-MM-DD/
        3. Анализируем ВСЕ найденные тексты на предмет организаций и их локации
        4. Обогащаем данные из любых найденных источников
        
        Args:
            email_data: Данные письма с вложениями
            
        Returns:
            List[LocationEvidence]: Список доказательств локации
        """
        if not self.config.enabled:
            self.logger.info("⚠️ AttachmentEvidenceExtractor disabled in config")
            return []
        
        # Безопасное получение attachments с проверкой типа
        attachments = email_data.get('attachments', [])
        
        # Проверяем что attachments это список, а не число или другой тип
        if not isinstance(attachments, list):
            self.logger.warning(f"⚠️ Attachments is not a list, got {type(attachments)}: {attachments}")
            return []
        
        if not attachments:
            self.logger.warning("📎 No attachments found in email_data")
            return []
        
        self.logger.info(f"🔍 Анализируем ВСЕ {len(attachments)} вложений для извлечения локации")
        self.logger.info(f"🔍 DEBUG: First attachment keys: {list(attachments[0].keys()) if attachments else 'N/A'}")
        
        evidence_list = []
        
        for attachment in attachments:
            try:
                # УПРОЩЕННАЯ ЛОГИКА: обрабатываем ВСЕ вложения с OCR-текстом
                attachment_evidence = self._extract_from_attachment(attachment)
                evidence_list.extend(attachment_evidence)
            except Exception as e:
                self.logger.error(f"Ошибка обработки вложения {attachment.get('filename', 'unknown')}: {e}")
        
        self.logger.info(f"✅ Извлечено {len(evidence_list)} доказательств локации")
        return evidence_list
    
    def _should_process_attachment(self, attachment: Dict[str, Any]) -> bool:
        """Проверка нужно ли обрабатывать вложение"""
        # УПРОЩЕННАЯ ЛОГИКА: обрабатываем ВСЕ вложения, для которых есть OCR-текст
        text_content = self._get_attachment_text(attachment)
        
        if text_content:
            self.logger.debug(f"📄 Найден OCR-текст для вложения, длина: {len(text_content)} символов")
            return True
        
        self.logger.debug("📄 OCR-текст не найден для вложения")
        return False
    

    
    def _get_attachment_text(self, attachment: Dict[str, Any]) -> str:
        """Получение текста вложения"""
        # Прямой текст
        if 'text_content' in attachment and attachment['text_content']:
            return attachment['text_content']
        
        # Текст по страницам
        if 'pages_text' in attachment and attachment['pages_text']:
            return '\n'.join(attachment['pages_text'])
        
        # Путь к текстовому файлу
        if 'text_path' in attachment:
            try:
                with open(attachment['text_path'], 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                self.logger.warning(f"Не удалось прочитать {attachment['text_path']}: {e}")
        
        # Попытка найти OCR-текст по пути к файлу
        if 'file_path' in attachment:
            ocr_text = self._try_find_ocr_text(attachment['file_path'])
            if ocr_text:
                return ocr_text
        
        # Попытка найти OCR-текст по saved_filename
        if 'saved_filename' in attachment:
            ocr_text = self._try_find_ocr_text_by_filename(attachment['saved_filename'])
            if ocr_text:
                return ocr_text
        
        # Попытка найти OCR-текст по original_filename
        if 'original_filename' in attachment:
            ocr_text = self._try_find_ocr_text_by_filename(attachment['original_filename'])
            if ocr_text:
                return ocr_text
        
        return ""
    
    def _try_find_ocr_text(self, file_path: str) -> str:
        """Попытка найти OCR-текст для файла"""
        try:
            from pathlib import Path
            
            # Пробуем найти в актуальной папке с OCR-текстами
            file_path_obj = Path(file_path)
            filename = file_path_obj.name
            
            # Заменяем расширение на .txt
            txt_filename = file_path_obj.with_suffix('.txt').name
            
            # Извлекаем дату из пути или имени файла
            if 'attachments' in file_path and '2025-' in file_path:
                # Извлекаем дату из пути: .../2025-07-29/...
                from config.paths import DataPaths
                DataPaths.migrate_if_needed()
                
                parts = file_path.split('/')
                for part in parts:
                    if part.startswith('2025-'):
                        date_folder = part
                        ocr_text_path = DataPaths.get_ocr_text_path(date_folder, txt_filename)
                        if ocr_text_path.exists():
                            with open(ocr_text_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Убираем заголовок с метаданными
                                lines = content.split('\n')
                                text_start = 0
                                for i, line in enumerate(lines):
                                    if line.strip().startswith('====='):
                                        text_start = i + 1
                                        break
                                return '\n'.join(lines[text_start:])
                        break
            
            # Пробуем заменить расширение на .txt в том же месте
            txt_path = file_path_obj.with_suffix('.txt')
            if txt_path.exists():
                with open(txt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Пробуем найти в папке cache или ocr
            cache_paths = [
                file_path_obj.parent / 'cache' / f"{file_path_obj.stem}.txt",
                file_path_obj.parent / 'ocr' / f"{file_path_obj.stem}.txt",
                file_path_obj.parent.parent / 'cache' / f"{file_path_obj.stem}.txt",
            ]
            
            for cache_path in cache_paths:
                if cache_path.exists():
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        return f.read()
                        
        except Exception as e:
            self.logger.debug(f"Не удалось найти OCR-текст для {file_path}: {e}")
        
        return ""
    
    def _try_find_in_ocr_cache_by_path(self, file_path: str) -> str:
        """Попытка найти OCR-текст в кэше по пути к файлу"""
        try:
            import json
            from pathlib import Path
            
            cache_path = Path("data/cache/ocr_cache.json")
            if not cache_path.exists():
                return ""
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Ищем по пути к файлу
            for cache_key, cache_entry in cache_data.items():
                if 'result' in cache_entry and cache_entry['result'].get('success'):
                    cached_path = cache_entry['result'].get('file_path', '')
                    if file_path == cached_path or Path(file_path).name in cached_path:
                        return cache_entry['result'].get('text', '')
                        
        except Exception as e:
            self.logger.debug(f"Не удалось найти в OCR кэше по пути {file_path}: {e}")
        
        return ""
    
    def _try_find_ocr_text_by_filename(self, filename: str) -> str:
        """Попытка найти OCR-текст по имени файла"""
        try:
            from pathlib import Path
            
            # Ищем в актуальной папке с OCR-текстами
            # Извлекаем дату из имени файла (формат: 20250729_...)
            if filename.startswith('202'):
                from config.paths import DataPaths
                DataPaths.migrate_if_needed()
                
                date_part = filename[:8]  # 20250729
                formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"  # 2025-07-29
                
                ocr_text_path = DataPaths.get_ocr_text_path(formatted_date, filename)
                if ocr_text_path.exists():
                    with open(ocr_text_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Убираем заголовок с метаданными, оставляем только текст
                        lines = content.split('\n')
                        text_start = 0
                        for i, line in enumerate(lines):
                            if line.strip().startswith('====='):
                                text_start = i + 1
                                break
                        return '\n'.join(lines[text_start:])
            
            # Ищем в других возможных местах
            possible_paths = [
                Path("data/cache") / f"{Path(filename).stem}.txt",
                Path("data/ocr") / f"{Path(filename).stem}.txt",
                Path("cache") / f"{Path(filename).stem}.txt",
            ]
            
            for path in possible_paths:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read()
                        
        except Exception as e:
            self.logger.debug(f"Не удалось найти OCR-текст для {filename}: {e}")
        
        return ""
    
    def _try_find_in_ocr_cache(self, filename: str) -> str:
        """Попытка найти OCR-текст в кэше"""
        try:
            import json
            from pathlib import Path
            
            cache_path = Path("data/cache/ocr_cache.json")
            if not cache_path.exists():
                return ""
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Ищем по имени файла
            for cache_key, cache_entry in cache_data.items():
                if 'result' in cache_entry and cache_entry['result'].get('success'):
                    cached_filename = cache_entry['result'].get('file_name', '')
                    if filename in cached_filename or cached_filename in filename:
                        return cache_entry['result'].get('text', '')
                        
        except Exception as e:
            self.logger.debug(f"Не удалось найти в OCR кэше для {filename}: {e}")
        
        return ""
    
    def _extract_from_attachment(self, attachment: Dict[str, Any]) -> List[LocationEvidence]:
        """Извлечение доказательств из одного вложения"""
        text_content = self._get_attachment_text(attachment)
        if not text_content:
            self.logger.debug(f"📄 Нет OCR-текста для вложения {attachment.get('filename', 'unknown')}")
            return []
        
        filename = attachment.get('filename', 'unknown')
        self.logger.debug(f"📄 Обрабатываем вложение: {filename} (текст: {len(text_content)} символов)")
        
        evidence_list = []
        
        # Находим все организации в тексте
        organizations = self._find_organizations_in_text(text_content)
        self.logger.debug(f"🏢 Найдено организаций в тексте: {len(organizations)}")
        
        for org_info in organizations:
            # Ищем локацию рядом с каждой организацией
            location_info = self._find_location_near_organization(
                text_content, org_info['matched_name'], org_info['position']
            )
            
            if location_info['city'] or location_info['address']:
                evidence = LocationEvidence(
                    org_name_norm=self._normalize_organization_name(org_info['matched_name']),
                    matched_name=org_info['matched_name'],
                    city=location_info['city'],
                    address=location_info['address'],
                    source={
                        'type': 'attachment',
                        'filename': filename,
                        'snippet': location_info['snippet'],
                        'offset': org_info['position']
                    },
                    confidence=self._calculate_confidence(org_info, location_info, attachment)
                )
                evidence_list.append(evidence)
                self.logger.debug(f"✅ Найдено доказательство для {org_info['matched_name']}: {location_info['city'] or location_info['address']}")
        
        return evidence_list
    
    def _find_organizations_in_text(self, text: str) -> List[Dict[str, Any]]:
        """Поиск организаций в тексте"""
        organizations = []
        
        # Стоп-слова: предлоги и слова, после которых название организации заканчивается
        stop_words = r'(?:\s+(?:для|от|в|на|по|с|к|из|о|у|при|через|про|без|до|после|перед|над|под|за|между|среди|[А-ЯЁ][а-яё]+ович[а-яё]*|[А-ЯЁ][а-яё]+евн[а-яё]*))'
        
        # Паттерны для поиска организаций (улучшенные)
        org_patterns = [
            # ООО/ЗАО/и т.д. + название (останавливаемся на предлогах)
            re.compile(r'\b((?:ООО|ЗАО|ОАО|ПАО|АО|ИП|ФБУЗ|ГБУЗ)\s+[«""]?[А-ЯЁ][^«""\n]{2,50}?)' + stop_words, re.IGNORECASE | re.UNICODE),
            re.compile(r'\b((?:ООО|ЗАО|ОАО|ПАО|АО|ИП|ФБУЗ|ГБУЗ)\s+[«""]?[А-ЯЁ][^«""\n]{2,50}[«""]?)', re.IGNORECASE | re.UNICODE),
            
            # Название + ООО/ЗАО/и т.д.
            re.compile(r'\b([А-ЯЁ][А-ЯЁ\s]{10,50}(?:ООО|ЗАО|ОАО|ПАО|АО))', re.IGNORECASE | re.UNICODE),
            
            # Название + компания/центр/и т.д. (останавливаемся на предлогах)
            re.compile(r'([А-ЯЁ][А-ЯЁа-яё\s"«»]{5,50}?(?:компания|центр|клиника|лаборатория|группа))(?=' + stop_words + r'|\s*\n|$)', re.IGNORECASE | re.UNICODE),
            
            # Компания/Группа + НАЗВАНИЕ (останавливаемся на предлогах и персоналиях)
            re.compile(r'(?:компания|группа)\s+([А-ЯЁ][А-ЯЁа-яё\s]{2,30}?)(?=' + stop_words + r'|\s*\n|$)', re.IGNORECASE | re.UNICODE),
        ]
        
        for pattern in org_patterns:
            for match in pattern.finditer(text):
                org_name = match.group(1).strip()
                
                # Постобработка: обрезаем название на предлогах и персоналиях
                org_name = self._trim_organization_name(org_name)
                
                if len(org_name) > 3:  # Минимальная длина названия
                    organizations.append({
                        'matched_name': org_name,
                        'position': match.start(),
                        'end_position': match.end()
                    })
        
        # Удаляем дубликаты и сортируем по позиции
        unique_orgs = {}
        for org in organizations:
            norm_name = self._normalize_organization_name(org['matched_name'])
            if norm_name not in unique_orgs:
                unique_orgs[norm_name] = org
        
        return list(unique_orgs.values())
    
    def _trim_organization_name(self, org_name: str) -> str:
        """
        Обрезает название организации на предлогах и персоналиях
        
        Примеры:
        - "МИЛЛАБ для Абакан ЦГиЭ" → "МИЛЛАБ"
        - "МИЛЛАБ Акутину Ивану" → "МИЛЛАБ"
        - "Компания для проекта" → "Компания"
        """
        # Предлоги и стоп-слова, на которых обрезаем название
        stop_patterns = [
            r'\s+для\s+',      # для
            r'\s+от\s+',       # от
            r'\s+в\s+',        # в
            r'\s+на\s+',       # на
            r'\s+по\s+',       # по
            r'\s+с\s+',        # с
            r'\s+к\s+',        # к
            r'\s+из\s+',       # из
            r'\s+о\s+',        # о
            r'\s+у\s+',        # у
            r'\s+при\s+',      # при
            r'\s+через\s+',    # через
            r'\s+про\s+',      # про
            r'\s+без\s+',      # без
            r'\s+до\s+',       # до
            r'\s+после\s+',    # после
            r'\s+перед\s+',    # перед
            # Персоналии (отчества)
            r'\s+[А-ЯЁ][а-яё]+ович[а-яё]*\s+',  # Иванович, Ивановича
            r'\s+[А-ЯЁ][а-яё]+евн[а-яё]*\s+',   # Ивановна, Ивановне
            # Имена (заглавная + строчные)
            r'\s+[А-ЯЁ][а-яё]+у\s+[А-ЯЁ][а-яё]+',  # Акутину Ивану
        ]
        
        trimmed = org_name
        for pattern in stop_patterns:
            match = re.search(pattern, trimmed, re.IGNORECASE | re.UNICODE)
            if match:
                # Обрезаем на найденном стоп-слове
                trimmed = trimmed[:match.start()].strip()
                break
        
        return trimmed
    
    def _find_location_near_organization(self, text: str, org_name: str, org_position: int) -> Dict[str, Any]:
        """Поиск локации рядом с организацией"""
        # Ищем в окрестности ±500 символов от организации
        start_pos = max(0, org_position - 500)
        end_pos = min(len(text), org_position + 500)
        context = text[start_pos:end_pos]
        
        city = None
        address = None
        snippet = ""
        
        # Ищем город
        for pattern in self._city_patterns:
            match = pattern.search(context)
            if match:
                city = match.group(1).strip()
                snippet = self._extract_snippet(context, match.start(), match.end())
                break
        
        # Ищем адрес
        for pattern in self._address_patterns:
            match = pattern.search(context)
            if match:
                raw_address = match.group(1).strip()
                address = self._clean_address(raw_address)
                
                # 🛡️ ЗАЩИТА: Фильтр "только индекс"
                # Если адрес состоит только из 6 цифр (индекс) - это не полный адрес
                if address and re.match(r'^\d{6}$', address.strip()):
                    self.logger.debug(f"Отклонен адрес-индекс: {address}")
                    address = None
                
                # 🛡️ ЗАЩИТА: Фильтр "слишком короткий адрес"
                # Если адрес короче 20 символов и нет города - скорее всего это мусор
                if address and len(address) < 20 and not city:
                    self.logger.debug(f"Отклонен короткий адрес без города: {address}")
                    address = None
                
                if not snippet and address:  # Только если адрес прошел фильтры
                    snippet = self._extract_snippet(context, match.start(), match.end())
                break
        
        return {
            'city': city,
            'address': address,
            'snippet': snippet[:self.config.max_snippet_len] if snippet else ""
        }
    
    def _clean_address(self, raw_address: str) -> str:
        """Очистка адреса от лишней информации"""
        cleaned = raw_address
        
        # Удаляем телефоны, email и прочее
        for pattern in self._address_cleanup_patterns:
            cleaned = pattern.sub('', cleaned)
        
        # Нормализуем пробелы
        cleaned = ' '.join(cleaned.split())
        
        # Обрезаем по знакам препинания
        for delimiter in [',', ';', '\n', '\r']:
            if delimiter in cleaned:
                parts = cleaned.split(delimiter)
                cleaned = parts[0].strip()
                break
        
        return cleaned.strip()
    
    def _extract_snippet(self, text: str, start: int, end: int) -> str:
        """Извлечение сниппета с контекстом"""
        snippet_start = max(0, start - 50)
        snippet_end = min(len(text), end + 50)
        return text[snippet_start:snippet_end].strip()
    
    def _normalize_organization_name(self, org_name: str) -> str:
        """Нормализация названия организации"""
        normalized = org_name.lower().strip()
        
        # Убираем кавычки
        normalized = re.sub(r'[«»""\'"]', '', normalized)
        
        # Убираем юридические формы
        for form in self.config.legal_forms:
            pattern = r'\b' + re.escape(form) + r'\b'
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Нормализуем пробелы
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()
    
    def _calculate_confidence(self, org_info: Dict[str, Any], location_info: Dict[str, Any], 
                            attachment: Dict[str, Any]) -> float:
        """Расчет уверенности в доказательстве"""
        confidence = 0.6  # базовая уверенность (повышена, т.к. обрабатываем все вложения)
        
        # Повышаем за наличие города и адреса
        if location_info['city']:
            confidence += 0.2
        if location_info['address']:
            confidence += 0.2
        
        # Повышаем за наличие ИНН/ОГРН в контексте (более важный критерий)
        snippet = location_info.get('snippet', '')
        if re.search(r'\b\d{10,12}\b', snippet):  # ИНН
            confidence += 0.15
        if re.search(r'\b\d{13}\b', snippet):     # ОГРН
            confidence += 0.15
        
        return min(1.0, confidence)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики работы извлекателя"""
        return {
            'config': {
                'enabled': self.config.enabled,
                'max_snippet_len': self.config.max_snippet_len,
            },
            'patterns': {
                'city_patterns_count': len(self._city_patterns),
                'address_patterns_count': len(self._address_patterns),
                'legal_forms_count': len(self.config.legal_forms),
            }
        }


# Пример использования
if __name__ == "__main__":
    # Тестовые данные
    test_email_data = {
        'attachments': [{
            'filename': 'Коммерческое_предложение_МИЛЛАБ.txt',
            'text_content': '''
            ООО "МИЛЛАБ"
            Юридический адрес: 117105, г. Москва, Варшавское шоссе, д. 17
            ИНН: 7728123456
            ОГРН: 1027739123456
            
            Коммерческое предложение
            Поставка медицинского оборудования
            ''',
            'mime': 'text/plain'
        }]
    }
    
    extractor = AttachmentEvidenceExtractor()
    evidence_list = extractor.extract(test_email_data)
    
    print("📎 Тестирование AttachmentEvidenceExtractor:")
    for evidence in evidence_list:
        print(f"  Организация: {evidence.matched_name}")
        print(f"  Нормализованное: {evidence.org_name_norm}")
        print(f"  Город: {evidence.city}")
        print(f"  Адрес: {evidence.address}")
        print(f"  Уверенность: {evidence.confidence}")
        print(f"  Источник: {evidence.source['filename']}")
        print()