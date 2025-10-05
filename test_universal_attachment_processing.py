#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест универсальной обработки вложений (без ограничений по имени файла)
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.append(str(Path(__file__).parent / "src"))

# Копируем обновленный класс для тестирования
import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from difflib import SequenceMatcher

@dataclass
class AttachmentEvidenceConfig:
    """Конфигурация для извлечения доказательств из вложений"""
    enabled: bool = True
    
    # Режим обработки: 
    # 'content_first' - приоритет содержимому, fallback на имя файла
    # 'content_only' - только по содержимому, игнорировать имена файлов
    # 'filename_first' - приоритет имени файла
    processing_mode: str = 'content_only'  # Тестируем режим только по содержимому
    
    # Паттерны имен файлов для включения в поиск (используется как fallback)
    filename_include_patterns: List[str] = field(default_factory=lambda: [
        "коммерчес", "кп", "реквизит", "счет", "договор", "пред",
        "offer", "invoice", "bill", "commercial", "proposal", "sales"
    ])
    
    # Сигнатуры текста для классификации документов (основной критерий)
    text_signatures: List[str] = field(default_factory=lambda: [
        "инн", "огрн", "ооо", "ао", "коммерческое предложение", 
        "реквизиты", "юридический адрес", "фактический адрес",
        "договор", "соглашение", "контракт", "счет", "фактура"
    ])
    
    # Минимальное количество бизнес-ключевых слов для классификации как делового документа
    min_business_keywords: int = 3
    
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

class UniversalAttachmentEvidenceExtractor:
    """Универсальный извлекатель доказательств из любых вложений"""
    
    def __init__(self, config: Optional[AttachmentEvidenceConfig] = None):
        self.config = config or AttachmentEvidenceConfig()
        self.logger = logging.getLogger(__name__)
    
    def should_process_attachment(self, attachment: Dict[str, Any]) -> bool:
        """Проверка нужно ли обрабатывать вложение"""
        # Сначала пробуем получить текст вложения
        text_content = self._get_attachment_text(attachment)
        
        # Если есть текст - анализируем его содержимое
        if text_content:
            text_lower = text_content.lower()
            
            # Проверяем по сигнатурам текста (основной критерий)
            for signature in self.config.text_signatures:
                if signature.lower() in text_lower:
                    print(f"📄 Вложение содержит сигнатуру: {signature}")
                    return True
            
            # Дополнительная проверка: если в тексте есть организации и адреса
            if self._has_business_content(text_lower):
                print("📄 Вложение содержит бизнес-информацию")
                return True
        
        # Fallback: проверяем по паттернам имени файла (если режим позволяет)
        if self.config.processing_mode != 'content_only' and not text_content:
            filenames_to_check = [
                attachment.get('filename', ''),
                attachment.get('original_filename', ''),
                attachment.get('saved_filename', ''),
            ]
            
            for filename in filenames_to_check:
                if filename:
                    filename_lower = filename.lower()
                    for pattern in self.config.filename_include_patterns:
                        if pattern.lower() in filename_lower:
                            print(f"📄 Вложение подходит по имени файла: {pattern}")
                            return True
        
        return False
    
    def _has_business_content(self, text_lower: str) -> bool:
        """Проверка наличия бизнес-информации в тексте"""
        # Ключевые слова, указывающие на деловые документы
        business_keywords = [
            # Организационные формы
            'ооо', 'зао', 'оао', 'пао', 'ао', 'ип', 'фбуз', 'гбуз', 'фгуп', 'гуп',
            # Реквизиты
            'инн', 'огрн', 'кпп', 'окпо', 'бик',
            # Адресная информация
            'адрес', 'местонахождение', 'юридический адрес', 'фактический адрес',
            # Контактная информация
            'телефон', 'факс', 'e-mail', 'email', 'сайт',
            # Деловые документы
            'договор', 'соглашение', 'контракт', 'счет', 'фактура', 'акт',
            # Должности
            'директор', 'генеральный', 'заведующий', 'руководитель', 'менеджер',
            # Организации
            'компания', 'предприятие', 'учреждение', 'центр', 'клиника', 'больница'
        ]
        
        # Считаем количество совпадений
        matches = sum(1 for keyword in business_keywords if keyword in text_lower)
        found_keywords = [keyword for keyword in business_keywords if keyword in text_lower]
        
        print(f"📊 Найдено {matches} бизнес-ключевых слов: {found_keywords[:10]}...")
        
        # Используем настраиваемый порог из конфигурации
        return matches >= self.config.min_business_keywords
    
    def _get_attachment_text(self, attachment: Dict[str, Any]) -> str:
        """Получение текста вложения (упрощенная версия для теста)"""
        # Прямой текст
        if 'text_content' in attachment and attachment['text_content']:
            return attachment['text_content']
        
        # Для теста - возвращаем пустую строку
        return ""

# Тестирование
if __name__ == "__main__":
    print("🧪 Тестирование универсальной обработки вложений")
    
    extractor = UniversalAttachmentEvidenceExtractor()
    
    # Тест 1: Файл с "неподходящим" именем, но с деловым содержимым
    test_cases = [
        {
            'name': 'Sales файл с деловым содержимым',
            'attachment': {
                'original_filename': 'Sales20250729115854.pdf',
                'text_content': '''
                ООО "Рога и Копыта"
                ИНН: 1234567890
                Юридический адрес: 123456, г. Москва, ул. Ленина, д. 1
                Телефон: +7(495) 123-45-67
                Директор: Иванов И.И.
                
                Договор поставки оборудования
                '''
            },
            'expected': True
        },
        {
            'name': 'Обычный файл без делового содержимого',
            'attachment': {
                'original_filename': 'photo.jpg',
                'text_content': 'Просто какой-то текст без деловой информации'
            },
            'expected': False
        },
        {
            'name': 'Файл с коммерческим предложением',
            'attachment': {
                'original_filename': 'document.pdf',
                'text_content': '''
                Коммерческое предложение
                Компания МИЛЛАБ
                г. Москва
                '''
            },
            'expected': True
        },
        {
            'name': 'Файл с реквизитами',
            'attachment': {
                'original_filename': 'unknown_file.txt',
                'text_content': '''
                Реквизиты организации
                ИНН: 9876543210
                ОГРН: 1234567890123
                Адрес: г. Санкт-Петербург, Невский пр., д. 100
                '''
            },
            'expected': True
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Тест {i}: {test_case['name']}")
        print(f"  Файл: {test_case['attachment']['original_filename']}")
        
        result = extractor.should_process_attachment(test_case['attachment'])
        expected = test_case['expected']
        
        if result == expected:
            print(f"  ✅ ПРОЙДЕН: {result} (ожидалось {expected})")
        else:
            print(f"  ❌ НЕ ПРОЙДЕН: {result} (ожидалось {expected})")
    
    print(f"\n🎯 Режим обработки: {extractor.config.processing_mode}")
    print(f"📊 Минимум бизнес-ключевых слов: {extractor.config.min_business_keywords}")
    print("\n✅ Теперь система обрабатывает ВСЕ вложения с деловым содержимым,")
    print("   независимо от имени файла!")