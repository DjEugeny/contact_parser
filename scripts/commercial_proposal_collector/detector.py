"""
🔍 Proposal Detector - Модуль для определения коммерческих предложений

Этот модуль отвечает за анализ имен файлов и определение, является ли файл коммерческим предложением.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ProposalDetector:
    """Детектор коммерческих предложений."""
    
    def __init__(self):
        """Инициализация детектора."""
        # Ключевые слова для определения КП (русские)
        self.ru_keywords = [
            r'ком\.?\s*пред\.?',  # Ком.пред., Ком пред
            r'коммерческое\s+предложение',
            r'коммерческий\s+предлож',
            r'стоимость',
            r'расчет',
            r'цена',
            r'прайс',
            r'предложение',
            r'оферта',
        ]
        
        # Ключевые слова для определения КП (английские)
        self.en_keywords = [
            r'commercial\s+proposal',
            r'price\s+proposal',
            r'sales\s+proposal',
            r'price\s+offer',
            r'quote',
            r'quotation',
            r'estimate',
            r'pricing',
            r'offer',
            r'proposal',
            r'sales',
            r'price',
            r'cost',
        ]
        
        # Комбинированные паттерны
        self.combined_keywords = self.ru_keywords + self.en_keywords
        
        # Дополнительные паттерны для специфических форматов
        self.special_patterns = [
            r'КП\d*',  # КП123, КП-2025
            r'Sales\d+',  # Sales20250729
            r'Price\d+',
            r'Offer\d+',
            r'Quote\d+',
        ]
        
        # Паттерны для исключения (не КП)
        self.exclude_patterns = [
            r'счет\s+на\s+оплату',  # Счет на оплату
            r'invoice',  # Invoice
            r'акт\s+выполненных\s+работ',  # Акт выполненных работ
            r'document',
            r'договор',
            r'contract',
            r'справка',
            r'certificate',
        ]
        
        # Компилируем регулярные выражения для производительности
        self.compiled_include_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.combined_keywords + self.special_patterns
        ]
        
        self.compiled_exclude_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.exclude_patterns
        ]
    
    def is_commercial_proposal(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Определение, является ли файл коммерческим предложением.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Кортеж (является_КП, найденный_паттерн)
        """
        if not file_path or not file_path.exists():
            return False, None
            
        # Получаем имя файла без расширения
        filename = file_path.stem
        
        # Сначала проверяем исключения
        for pattern in self.compiled_exclude_patterns:
            if pattern.search(filename):
                logger.debug(f"❌ Файл исключен по паттерну: {file_path.name} (паттерн: {pattern.pattern})")
                return False, pattern.pattern
        
        # Затем проверяем включения
        for pattern in self.compiled_include_patterns:
            if pattern.search(filename):
                logger.debug(f"✅ Найдено КП: {file_path.name} (паттерн: {pattern.pattern})")
                return True, pattern.pattern
                
        return False, None
    
    def find_proposals_in_files(self, files: List[Path]) -> List[Dict]:
        """
        Поиск коммерческих предложений в списке файлов.
        
        Args:
            files: Список путей к файлам
            
        Returns:
            Список словарей с информацией о найденных КП
        """
        proposals = []
        
        for file_path in files:
            is_proposal, pattern = self.is_commercial_proposal(file_path)
            
            if is_proposal:
                proposals.append({
                    'file_path': file_path,
                    'filename': file_path.name,
                    'pattern': pattern,
                    'size_bytes': file_path.stat().st_size if file_path.exists() else 0,
                    'extension': file_path.suffix.lower(),
                })
                
        logger.info(f"🔍 Найдено КП: {len(proposals)} из {len(files)} файлов")
        return proposals
    
    def analyze_proposal_patterns(self, proposals: List[Dict]) -> Dict[str, int]:
        """
        Анализ паттернов в найденных КП.
        
        Args:
            proposals: Список найденных КП
            
        Returns:
            Словарь {паттерн: количество}
        """
        pattern_counts = {}
        
        for proposal in proposals:
            pattern = proposal.get('pattern', 'unknown')
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
        return pattern_counts
    
    def extract_proposal_metadata(self, file_path: Path) -> Dict[str, str]:
        """
        Извлечение метаданных из имени файла КП.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Словарь с метаданными
        """
        filename = file_path.stem
        metadata = {}
        
        # Попытка извлечь дату из имени файла
        date_patterns = [
            r'(\d{4}\d{2}\d{2})',  # 20250729
            r'(\d{2}\.\d{2}\.\d{4})',  # 29.07.2025
            r'(\d{4}-\d{2}-\d{2})',  # 2025-07-29
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                date_str = match.group(1)
                metadata['date_string'] = date_str
                break
                
        # Попытка извлечь организацию
        org_patterns = [
            r'для\s+([^_]+)',  # для Организация
            r'_([^_]+)_',  # _Организация_
        ]
        
        for pattern in org_patterns:
            match = re.search(pattern, filename)
            if match:
                org = match.group(1).strip()
                metadata['organization'] = org
                break
                
        # Извлечение директории (даты)
        if file_path.parent.name:
            metadata['directory_date'] = file_path.parent.name
            
        return metadata
    
    def get_proposal_statistics(self, proposals: List[Dict]) -> Dict:
        """
        Получение статистики по найденным КП.
        
        Args:
            proposals: Список найденных КП
            
        Returns:
            Словарь со статистикой
        """
        if not proposals:
            return {
                'total_count': 0,
                'total_size_mb': 0,
                'file_types': {},
                'patterns': {},
                'directories': {},
            }
            
        total_size = sum(p['size_bytes'] for p in proposals)
        file_types = {}
        patterns = {}
        directories = {}
        
        for proposal in proposals:
            # Типы файлов
            ext = proposal['extension']
            file_types[ext] = file_types.get(ext, 0) + 1
            
            # Паттерны
            pattern = proposal['pattern']
            patterns[pattern] = patterns.get(pattern, 0) + 1
            
            # Директории
            dir_name = proposal['file_path'].parent.name
            directories[dir_name] = directories.get(dir_name, 0) + 1
            
        return {
            'total_count': len(proposals),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_types': file_types,
            'patterns': patterns,
            'directories': directories,
        }
    
    def add_custom_keyword(self, keyword: str, language: str = 'ru') -> bool:
        """
        Добавление пользовательского ключевого слова.
        
        Args:
            keyword: Новое ключевое слово
            language: Язык ('ru' или 'en')
            
        Returns:
            True если слово добавлено, иначе False
        """
        if not keyword or keyword.strip() == '':
            return False
            
        pattern = re.escape(keyword.strip())
        
        if language == 'ru':
            self.ru_keywords.append(pattern)
        elif language == 'en':
            self.en_keywords.append(pattern)
        else:
            return False
            
        # Перекомпилируем паттерны
        self.combined_keywords = self.ru_keywords + self.en_keywords
        self.compiled_include_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.combined_keywords + self.special_patterns
        ]
        
        logger.info(f"➕ Добавлено ключевое слово: {keyword} ({language})")
        return True