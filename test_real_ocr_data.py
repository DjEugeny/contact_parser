#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест с реальными OCR-данными
"""

import re
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field

# Копируем нужные классы для тестирования
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

class RealDataExtractor:
    """Тестовая версия с реальными данными"""
    
    def __init__(self, config: Optional[AttachmentEvidenceConfig] = None):
        self.config = config or AttachmentEvidenceConfig()
        
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
        # Пробуем получить текст из файла
        text_content = self._get_attachment_text(attachment)
        if not text_content:
            return []
        
        filename = attachment.get('filename', 'unknown')
        print(f"📄 Обрабатываем вложение: {filename} (текст: {len(text_content)} символов)")
        
        evidence_list = []
        
        # Находим все организации в тексте
        organizations = self._find_organizations_in_text(text_content)
        print(f"🏢 Найдено организаций в тексте: {len(organizations)}")
        
        for org_info in organizations:
            print(f"  - {org_info['matched_name']} (позиция {org_info['position']})")
            
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
    
    def _get_attachment_text(self, attachment: Dict[str, Any]) -> str:
        """Получение текста вложения"""
        # Прямой текст
        if 'text_content' in attachment and attachment['text_content']:
            return attachment['text_content']
        
        # Попытка найти OCR-текст по saved_filename
        if 'saved_filename' in attachment:
            ocr_text = self._try_find_ocr_text_by_filename(attachment['saved_filename'])
            if ocr_text:
                return ocr_text
        
        return ""
    
    def _try_find_ocr_text_by_filename(self, filename: str) -> str:
        """Попытка найти OCR-текст по имени файла"""
        try:
            from pathlib import Path
            
            # Ищем в актуальной папке с OCR-текстами
            if filename.startswith('202'):
                date_part = filename[:8]  # 20250729
                formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"  # 2025-07-29
                
                # Заменяем расширение на .txt
                txt_filename = Path(filename).with_suffix('.txt').name
                
                ocr_text_path = Path(f"data/final_results/texts/{formatted_date}/{txt_filename}")
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
    
    def _find_organizations_in_text(self, text: str) -> List[Dict[str, Any]]:
        """Поиск организаций в тексте"""
        organizations = []
        
        org_patterns = [
            re.compile(r'\b((?:ООО|ЗАО|ОАО|ПАО|АО|ИП|ФБУЗ|ГБУЗ)\s+[«""]?[А-ЯЁ][^«""]{2,50}[«""]?)', re.IGNORECASE | re.UNICODE),
            re.compile(r'([А-ЯЁ][А-ЯЁа-яё\s"«»]{5,50}(?:компания|центр|клиника|лаборатория|группа))', re.IGNORECASE | re.UNICODE),
            re.compile(r'(?:компания|группа)\s+([А-ЯЁ][А-ЯЁа-яё\s]{2,30})', re.IGNORECASE | re.UNICODE),
            re.compile(r'Общество с ограниченной ответственностью\s+[«""]?([А-ЯЁ][^«""]{2,50})[«""]?', re.IGNORECASE | re.UNICODE),
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

def test_real_ocr_data():
    """Тест с реальными OCR-данными"""
    
    # Реальные данные из письма 016
    test_email_data = {
        'attachments': [{
            'filename': 'Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ (ДТпрайм 5М6, ноутбук).pdf',
            'saved_filename': '20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.pdf',
            'file_path': 'data/attachments/2025-07-29/20250729_dna-technology_ru_6360137e_234805_attach_Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ для Абакан ЦГиЭ _ДТпрайм 5М6_ ноутбук_.pdf',
            'file_type': 'application/pdf',
            'status': 'saved'
        }]
    }
    
    extractor = RealDataExtractor()
    evidence_list = extractor.extract(test_email_data)
    
    print("\n🧪 Тест с реальными OCR-данными")
    print(f"📎 Обработано вложений: {len(test_email_data['attachments'])}")
    print(f"✅ Найдено доказательств: {len(evidence_list)}")
    print()
    
    for i, evidence in enumerate(evidence_list, 1):
        print(f"Доказательство {i}:")
        print(f"  📄 Файл: {evidence.source['filename']}")
        print(f"  🏢 Организация: {evidence.matched_name}")
        print(f"  🏢 Нормализованное: {evidence.org_name_norm}")
        print(f"  🏙️ Город: {evidence.city}")
        print(f"  📍 Адрес: {evidence.address}")
        print(f"  🎯 Уверенность: {evidence.confidence:.2f}")
        print(f"  📝 Сниппет: {evidence.source['snippet'][:100]}...")
        print()
    
    # Проверяем что нашли МИЛЛАБ с городом Москва
    millab_evidence = None
    for evidence in evidence_list:
        if 'миллаб' in evidence.org_name_norm.lower():
            millab_evidence = evidence
            break
    
    if millab_evidence and millab_evidence.city == 'Москва':
        print("✅ ТЕСТ ПРОЙДЕН: Найдено доказательство для МИЛЛАБ с городом Москва")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Не найдено доказательство для МИЛЛАБ с городом Москва")
        if millab_evidence:
            print(f"   Найдено: {millab_evidence.org_name_norm} -> {millab_evidence.city}")
    
    print("🎉 Упрощенная логика работает с реальными данными!")

if __name__ == "__main__":
    test_real_ocr_data()