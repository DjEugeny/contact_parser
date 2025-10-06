#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автономный тест AttachmentEvidenceExtractor без зависимостей
"""

import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from difflib import SequenceMatcher

# Копируем код AttachmentEvidenceExtractor без импортов
@dataclass
class AttachmentEvidenceConfig:
    """Конфигурация для извлечения доказательств из вложений"""
    enabled: bool = True
    
    # Паттерны имен файлов для включения в поиск
    filename_include_patterns: List[str] = field(default_factory=lambda: [
        "коммерчес", "кп", "реквизит", "счет", "договор", "пред",
        "offer", "invoice", "bill", "commercial", "proposal"
    ])
    
    # Сигнатуры текста для классификации документов
    text_signatures: List[str] = field(default_factory=lambda: [
        "инн", "огрн", "ооо", "ао", "коммерческое предложение", 
        "реквизиты", "юридический адрес", "фактический адрес"
    ])
    
    # Пороги для fuzzy-поиска
    fuzzy_ratio_threshold: float = 0.9
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
    """Извлекатель доказательств локации организаций из вложений"""
    
    def __init__(self, config: Optional[AttachmentEvidenceConfig] = None):
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
        """Извлечение доказательств локации из вложений письма"""
        if not self.config.enabled:
            return []
        
        attachments = email_data.get('attachments', [])
        if not attachments:
            return []
        
        print(f"🔍 Анализируем {len(attachments)} вложений для извлечения локации")
        
        evidence_list = []
        
        for attachment in attachments:
            try:
                if self._should_process_attachment(attachment):
                    attachment_evidence = self._extract_from_attachment(attachment)
                    evidence_list.extend(attachment_evidence)
            except Exception as e:
                print(f"Ошибка обработки вложения {attachment.get('filename', 'unknown')}: {e}")
        
        print(f"✅ Извлечено {len(evidence_list)} доказательств локации")
        return evidence_list
    
    def _should_process_attachment(self, attachment: Dict[str, Any]) -> bool:
        """Проверка нужно ли обрабатывать вложение"""
        filename = attachment.get('filename', '').lower()
        
        # Проверяем по паттернам имени файла
        for pattern in self.config.filename_include_patterns:
            if pattern.lower() in filename:
                return True
        
        # Проверяем по содержимому текста
        text_content = self._get_attachment_text(attachment)
        if text_content:
            text_lower = text_content.lower()
            for signature in self.config.text_signatures:
                if signature.lower() in text_lower:
                    return True
        
        return False
    
    def _get_attachment_text(self, attachment: Dict[str, Any]) -> str:
        """Получение текста вложения"""
        # Прямой текст
        if 'text_content' in attachment and attachment['text_content']:
            return attachment['text_content']
        
        # Текст по страницам
        if 'pages_text' in attachment and attachment['pages_text']:
            return '\n'.join(attachment['pages_text'])
        
        # Попытка найти OCR-текст по saved_filename
        if 'saved_filename' in attachment:
            ocr_text = self._try_find_ocr_text_by_filename(attachment['saved_filename'])
            if ocr_text:
                return ocr_text
        
        # Попытка найти OCR-текст по file_path
        if 'file_path' in attachment:
            ocr_text = self._try_find_ocr_text(attachment['file_path'])
            if ocr_text:
                return ocr_text
        
        return ""
    
    def _try_find_ocr_text_by_filename(self, filename: str) -> str:
        """Попытка найти OCR-текст по имени файла"""
        try:
            from pathlib import Path
            
            # Ищем в актуальной папке с OCR-текстами
            # Извлекаем дату из имени файла (формат: 20250729_...)
            if filename.startswith('202'):
                date_part = filename[:8]  # 20250729
                formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"  # 2025-07-29
                
                ocr_text_path = Path(f"data/final_results/texts/{formatted_date}/{filename}")
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
                        
        except Exception as e:
            print(f"Не удалось найти OCR-текст для {filename}: {e}")
        
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
                parts = file_path.split('/')
                for part in parts:
                    if part.startswith('2025-'):
                        date_folder = part
                        ocr_text_path = Path(f"data/final_results/texts/{date_folder}/{txt_filename}")
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
                        
        except Exception as e:
            print(f"Не удалось найти OCR-текст для {file_path}: {e}")
        
        return ""
    
    def _extract_from_attachment(self, attachment: Dict[str, Any]) -> List[LocationEvidence]:
        """Извлечение доказательств из одного вложения"""
        text_content = self._get_attachment_text(attachment)
        if not text_content:
            return []
        
        filename = attachment.get('filename', 'unknown')
        print(f"📄 Обрабатываем вложение: {filename}")
        
        evidence_list = []
        
        # Находим все организации в тексте
        organizations = self._find_organizations_in_text(text_content)
        
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
        
        return evidence_list
    
    def _find_organizations_in_text(self, text: str) -> List[Dict[str, Any]]:
        """Поиск организаций в тексте"""
        organizations = []
        
        # Паттерны для поиска организаций
        org_patterns = [
            re.compile(r'\b((?:ООО|ЗАО|ОАО|ПАО|АО|ИП|ФБУЗ|ГБУЗ)\s+[«""]?[А-ЯЁ][^«""]{2,50}[«""]?)', re.IGNORECASE | re.UNICODE),
            re.compile(r'\b([А-ЯЁ][А-ЯЁ\s]{10,50}(?:ООО|ЗАО|ОАО|ПАО|АО))', re.IGNORECASE | re.UNICODE),
            re.compile(r'([А-ЯЁ][А-ЯЁа-яё\s"«»]{5,50}(?:компания|центр|клиника|лаборатория|группа))', re.IGNORECASE | re.UNICODE),
            re.compile(r'(?:компания|группа)\s+([А-ЯЁ][А-ЯЁа-яё\s]{2,30})', re.IGNORECASE | re.UNICODE),  # Компания МИЛЛАБ
        ]
        
        for pattern in org_patterns:
            for match in pattern.finditer(text):
                org_name = match.group(1).strip()
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
                if not snippet:
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
        confidence = 0.5  # базовая уверенность
        
        # Повышаем за наличие города и адреса
        if location_info['city']:
            confidence += 0.2
        if location_info['address']:
            confidence += 0.2
        
        # Повышаем за тип файла
        filename = attachment.get('filename', '').lower()
        if any(pattern in filename for pattern in ['кп', 'коммерчес', 'реквизит']):
            confidence += 0.1
        
        # Повышаем за наличие ИНН/ОГРН в контексте
        snippet = location_info.get('snippet', '')
        if re.search(r'\b\d{10,12}\b', snippet):  # ИНН
            confidence += 0.1
        if re.search(r'\b\d{13}\b', snippet):     # ОГРН
            confidence += 0.1
        
        return min(1.0, confidence)


# Тестирование
if __name__ == "__main__":
    print("🧪 Тестирование AttachmentEvidenceExtractor")
    
    # Тестовые данные - реальная структура из письма 016
    email_data = {
        'attachments': [{
            'original_filename': 'Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ (ДТпрайм 5М6, ноутбук).pdf',
            'saved_filename': '20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.pdf',
            'file_path': 'data/attachments/2025-07-29/20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.pdf',
            'file_type': 'application/pdf',
            'status': 'saved'
        }]
    }
    
    # Создаем экстрактор и тестируем
    extractor = AttachmentEvidenceExtractor()
    
    # Отладка: проверяем что происходит с вложением
    attachment = email_data['attachments'][0]
    print(f"📋 Отладка вложения:")
    print(f"  Filename: {attachment.get('original_filename', 'N/A')}")
    print(f"  Saved filename: {attachment.get('saved_filename', 'N/A')}")
    print(f"  File path: {attachment.get('file_path', 'N/A')}")
    # Отладка классификации
    print(f"  Patterns: {extractor.config.filename_include_patterns}")
    
    filenames_to_check = [
        attachment.get('filename', ''),
        attachment.get('original_filename', ''),
        attachment.get('saved_filename', ''),
    ]
    print(f"  Filenames to check: {filenames_to_check}")
    
    for filename in filenames_to_check:
        if filename:
            filename_lower = filename.lower()
            print(f"    Checking: {filename_lower}")
            for pattern in extractor.config.filename_include_patterns:
                if pattern.lower() in filename_lower:
                    print(f"      MATCH: {pattern}")
                else:
                    print(f"      NO MATCH: '{pattern}' not in '{filename_lower}'")
    
    print(f"  Should process: {extractor._should_process_attachment(attachment)}")
    
    # Проверяем получение текста напрямую из файла
    print(f"  Trying to find OCR text...")
    
    # Прямая проверка файла OCR
    from pathlib import Path
    ocr_file_path = Path("data/final_results/texts/2025-07-29/20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.txt")
    if ocr_file_path.exists():
        print(f"    OCR file exists: {ocr_file_path}")
        with open(ocr_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"    OCR file length: {len(content)}")
            # Убираем заголовок
            lines = content.split('\n')
            text_start = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('====='):
                    text_start = i + 1
                    break
            clean_text = '\n'.join(lines[text_start:])
            print(f"    Clean text length: {len(clean_text)}")
            if clean_text:
                print(f"    Text preview: {clean_text[:200]}...")
    else:
        print(f"    OCR file NOT found: {ocr_file_path}")
    
    text_content = extractor._get_attachment_text(attachment)
    print(f"  Final text length: {len(text_content)}")
    if text_content:
        print(f"  Text preview: {text_content[:200]}...")
    
    evidence_list = extractor.extract(email_data)
    
    print(f"📎 Найдено {len(evidence_list)} доказательств локации")
    
    for evidence in evidence_list:
        print(f"  Организация: {evidence.matched_name}")
        print(f"  Нормализованное: {evidence.org_name_norm}")
        print(f"  Город: {evidence.city}")
        print(f"  Адрес: {evidence.address}")
        print(f"  Уверенность: {evidence.confidence}")
        print(f"  Источник: {evidence.source.get('filename', 'unknown')}")
        print()
    
    # Проверяем ключевые результаты
    if evidence_list:
        millab_evidence = None
        for evidence in evidence_list:
            if 'миллаб' in evidence.org_name_norm.lower():
                millab_evidence = evidence
                break
        
        if millab_evidence:
            print("✅ ТЕСТ ПРОЙДЕН: Найдено доказательство для МИЛЛАБ")
            if millab_evidence.city == "Москва":
                print("✅ ТЕСТ ПРОЙДЕН: Город Москва извлечен корректно")
            else:
                print(f"❌ ТЕСТ НЕ ПРОЙДЕН: Ожидался город Москва, получен {millab_evidence.city}")
            
            if "117105" in (millab_evidence.address or ""):
                print("✅ ТЕСТ ПРОЙДЕН: Адрес с индексом 117105 извлечен корректно")
            else:
                print(f"❌ ТЕСТ НЕ ПРОЙДЕН: Адрес не содержит 117105: {millab_evidence.address}")
        else:
            print("❌ ТЕСТ НЕ ПРОЙДЕН: Не найдено доказательство для МИЛЛАБ")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Не найдено ни одного доказательства")
    
    print("\n🎯 Тестирование завершено")