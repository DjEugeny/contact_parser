#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест AttachmentEvidenceExtractor без сложных импортов
"""

import re
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field

# Копируем нужные классы напрямую для тестирования
@dataclass
class AttachmentEvidenceConfig:
    """Конфигурация для извлечения доказательств из вложений"""
    enabled: bool = True
    max_snippet_len: int = 240
    legal_forms: List[str] = field(default_factory=lambda: [
        "ооо", "зао", "оао", "пао", "ао", "ип", "фбуз", "гбуз", 
        "фгбу", "фгуп", "гуп", "муп", "нко", "llc", "ltd", "inc"
    ])

@dataclass
class LocationEvidence:
    """Доказательство локации организации из вложения"""
    org_name_norm: str          
    matched_name: str           
    city: Optional[str] = None  
    address: Optional[str] = None  
    source: Dict[str, Any] = field(default_factory=dict)  
    confidence: float = 0.0     

class SimpleAttachmentEvidenceExtractor:
    """Упрощенная версия для тестирования"""
    
    def __init__(self, config: Optional[AttachmentEvidenceConfig] = None):
        self.config = config or AttachmentEvidenceConfig()
        self.logger = logging.getLogger(__name__)
        
        # Компилируем регулярные выражения
        self._city_patterns = [
            re.compile(r'\bг\.?\s+([А-ЯЁ][а-яё\-\s]{2,30})', re.IGNORECASE | re.UNICODE),
            re.compile(r'город\s+([А-ЯЁ][а-яё\-\s]{2,30})', re.IGNORECASE | re.UNICODE),
            re.compile(r'\b([А-ЯЁ][а-яё\-\s]{2,30})\s+г\.?', re.IGNORECASE | re.UNICODE),
        ]
        
        self._address_patterns = [
            re.compile(r'(?:юридический\s+)?адрес[:\s]+(.{10,140})', re.IGNORECASE | re.UNICODE),
            re.compile(r'фактический\s+адрес[:\s]+(.{10,140})', re.IGNORECASE | re.UNICODE),
            re.compile(r'\b(\d{6}),?\s+([^,\n]{10,100})', re.UNICODE),
            re.compile(r'местонахождение[:\s]+(.{10,140})', re.IGNORECASE | re.UNICODE),
        ]
    
    def extract(self, email_data: Dict[str, Any]) -> List[LocationEvidence]:
        """Извлечение доказательств локации из вложений письма"""
        if not self.config.enabled:
            return []
        
        attachments = email_data.get('attachments', [])
        if not isinstance(attachments, list) or not attachments:
            return []
        
        print(f"🔍 Анализируем ВСЕ {len(attachments)} вложений для извлечения локации")
        
        evidence_list = []
        
        for attachment in attachments:
            try:
                attachment_evidence = self._extract_from_attachment(attachment)
                evidence_list.extend(attachment_evidence)
            except Exception as e:
                print(f"Ошибка обработки вложения {attachment.get('filename', 'unknown')}: {e}")
        
        print(f"✅ Извлечено {len(evidence_list)} доказательств локации")
        return evidence_list
    
    def _extract_from_attachment(self, attachment: Dict[str, Any]) -> List[LocationEvidence]:
        """Извлечение доказательств из одного вложения"""
        text_content = attachment.get('text_content', '')
        if not text_content:
            return []
        
        filename = attachment.get('filename', 'unknown')
        print(f"📄 Обрабатываем вложение: {filename} (текст: {len(text_content)} символов)")
        
        evidence_list = []
        
        # Находим все организации в тексте
        organizations = self._find_organizations_in_text(text_content)
        print(f"🏢 Найдено организаций в тексте: {len(organizations)}")
        
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
                    confidence=0.8
                )
                evidence_list.append(evidence)
                print(f"✅ Найдено доказательство для {org_info['matched_name']}: {location_info['city'] or location_info['address']}")
        
        return evidence_list
    
    def _find_organizations_in_text(self, text: str) -> List[Dict[str, Any]]:
        """Поиск организаций в тексте"""
        organizations = []
        
        org_patterns = [
            re.compile(r'\b((?:ООО|ЗАО|ОАО|ПАО|АО|ИП|ФБУЗ|ГБУЗ)\s+[«""]?[А-ЯЁ][^«""]{2,50}[«""]?)', re.IGNORECASE | re.UNICODE),
            re.compile(r'([А-ЯЁ][А-ЯЁа-яё\s"«»]{5,50}(?:компания|центр|клиника|лаборатория|группа))', re.IGNORECASE | re.UNICODE),
            re.compile(r'(?:компания|группа)\s+([А-ЯЁ][А-ЯЁа-яё\s]{2,30})', re.IGNORECASE | re.UNICODE),
        ]
        
        for pattern in org_patterns:
            for match in pattern.finditer(text):
                org_name = match.group(1).strip()
                if len(org_name) > 3:
                    organizations.append({
                        'matched_name': org_name,
                        'position': match.start(),
                        'end_position': match.end()
                    })
        
        return organizations
    
    def _find_location_near_organization(self, text: str, org_name: str, org_position: int) -> Dict[str, Any]:
        """Поиск локации рядом с организацией"""
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
                snippet = context[max(0, match.start()-50):match.end()+50]
                break
        
        # Ищем адрес
        for pattern in self._address_patterns:
            match = pattern.search(context)
            if match:
                address = match.group(1).strip()
                if not snippet:
                    snippet = context[max(0, match.start()-50):match.end()+50]
                break
        
        return {
            'city': city,
            'address': address,
            'snippet': snippet[:self.config.max_snippet_len] if snippet else ""
        }
    
    def _normalize_organization_name(self, org_name: str) -> str:
        """Нормализация названия организации"""
        normalized = org_name.lower().strip()
        normalized = re.sub(r'[«»""\'"]', '', normalized)
        
        for form in self.config.legal_forms:
            pattern = r'\b' + re.escape(form) + r'\b'
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        return ' '.join(normalized.split()).strip()

def test_simplified_logic():
    """Тест упрощенной логики - обрабатываем ВСЕ вложения"""
    
    test_email_data = {
        'attachments': [
            {
                'filename': 'random_document.pdf',  # НЕ деловой документ по имени
                'text_content': '''
                ООО "ТЕСТОВАЯ КОМПАНИЯ"
                Юридический адрес: 123456, г. Санкт-Петербург, ул. Тестовая, д. 1
                ИНН: 7812345678
                ''',
                'mime': 'application/pdf'
            },
            {
                'filename': 'image.jpg',  # Вообще не документ
                'text_content': '''
                Компания МИЛЛАБ
                г. Москва, Варшавское шоссе, 17
                Лаборатория медицинской диагностики
                ''',
                'mime': 'image/jpeg'
            },
            {
                'filename': 'empty_file.txt',  # Пустой файл
                'text_content': '',
                'mime': 'text/plain'
            },
            {
                'filename': 'no_orgs.txt',  # Нет организаций
                'text_content': 'Просто какой-то текст без организаций',
                'mime': 'text/plain'
            }
        ]
    }
    
    extractor = SimpleAttachmentEvidenceExtractor()
    evidence_list = extractor.extract(test_email_data)
    
    print("\n🧪 Тест упрощенной логики AttachmentEvidenceExtractor")
    print(f"📎 Обработано вложений: {len(test_email_data['attachments'])}")
    print(f"✅ Найдено доказательств: {len(evidence_list)}")
    print()
    
    for i, evidence in enumerate(evidence_list, 1):
        print(f"Доказательство {i}:")
        print(f"  📄 Файл: {evidence.source['filename']}")
        print(f"  🏢 Организация: {evidence.matched_name}")
        print(f"  🏙️ Город: {evidence.city}")
        print(f"  📍 Адрес: {evidence.address}")
        print(f"  🎯 Уверенность: {evidence.confidence:.2f}")
        print()
    
    # Проверяем что нашли доказательства из разных типов файлов
    filenames = [ev.source['filename'] for ev in evidence_list]
    print(f"📊 Файлы с найденными доказательствами: {filenames}")
    
    # Должны найти доказательства из random_document.pdf и image.jpg
    assert len(evidence_list) >= 2, f"Ожидали минимум 2 доказательства, получили {len(evidence_list)}"
    assert 'random_document.pdf' in filenames, "Должны обработать random_document.pdf"
    assert 'image.jpg' in filenames, "Должны обработать image.jpg"
    
    print("✅ Тест пройден! Упрощенная логика работает корректно")
    print("🎉 Обрабатываются ВСЕ вложения с OCR-текстом, независимо от имени файла")

if __name__ == "__main__":
    test_simplified_logic()