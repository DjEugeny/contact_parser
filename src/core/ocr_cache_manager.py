#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 OCRCacheManager - Легковесный менеджер кеша OCR результатов

Проверяет наличие результатов OCR ПЕРЕД инициализацией тяжелого OCR модуля.
Использует файловую систему как кеш (data/ocr/texts/).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional


class OCRCacheManager:
    """
    Легковесный менеджер кеша OCR результатов
    
    Основная идея:
    - Проверяет наличие файлов результатов в data/ocr/texts/
    - НЕ инициализирует OCR модуль для проверки
    - Возвращает текст из файла если он есть
    - Возвращает None если файла нет (тогда нужен OCR)
    """
    
    def __init__(self, results_dir: str = None):
        """
        Инициализация менеджера кеша
        
        Args:
            results_dir: Путь к папке с результатами OCR (если None, используется DataPaths)
        """
        # Импортируем централизованные пути
        from config.paths import DataPaths
        
        # Выполняем автомиграцию если необходимо
        DataPaths.migrate_if_needed()
        
        # Используем централизованный путь если не указан явно
        if results_dir is None:
            self.results_dir = DataPaths.OCR_TEXTS_DIR
        else:
            self.results_dir = Path(results_dir)
            
        self._cache = {}  # In-memory кеш для быстрого доступа
        self.logger = logging.getLogger('OCRCacheManager')
        
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_checks': 0
        }
    
    def check_batch(self, filenames: List[str], date: str) -> Dict[str, Optional[str]]:
        """
        Batch-проверка кеша для нескольких файлов
        
        Args:
            filenames: Список имен файлов вложений
            date: Дата письма (для поиска в правильной папке)
            
        Returns:
            Dict[filename, text or None]
        """
        results = {}
        for filename in filenames:
            results[filename] = self.get_cached_result(filename, date)
        return results
    
    def get_cached_result(self, filename: str, date: str) -> Optional[str]:
        """
        Получить результат OCR из кеша
        
        Args:
            filename: Имя файла вложения (может быть с расширением .docx, .pdf и т.д.)
            date: Дата письма
            
        Returns:
            Текст из OCR или None если не найден
        """
        self.stats['total_checks'] += 1
        
        # Проверяем in-memory кеш
        cache_key = f"{date}:{filename}"
        if cache_key in self._cache:
            self.stats['cache_hits'] += 1
            return self._cache[cache_key]
        
        # Ищем файл результата в файловой системе
        date_folder = self.results_dir / date
        
        if not date_folder.exists():
            self.stats['cache_misses'] += 1
            return None
        
        # Убираем расширение из имени файла для поиска
        # "file.docx" -> "file"
        filename_without_ext = filename
        if '.' in filename:
            filename_without_ext = filename.rsplit('.', 1)[0]
        
        # Ищем файл по паттерну
        # Файлы результатов имеют формат: {date}_{domain}_{hash}_attach_{original_name}.txt
        # Ищем по окончанию имени файла
        for txt_file in date_folder.glob("*.txt"):
            # Проверяем заканчивается ли имя файла на наше имя
            txt_name = txt_file.stem  # Имя без .txt
            
            # Проверяем точное совпадение с оригинальным именем
            if txt_name.endswith(filename_without_ext):
                text = self._read_text_file(txt_file)
                if text:
                    self._cache[cache_key] = text
                    self.stats['cache_hits'] += 1
                    self.logger.debug(f"Найден результат OCR: {txt_file.name}")
                    return text
        
        self.stats['cache_misses'] += 1
        return None
    
    def _read_text_file(self, file_path: Path) -> Optional[str]:
        """
        Прочитать текстовый файл
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Текст или None при ошибке
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.warning(f"Ошибка чтения {file_path}: {e}")
            return None
    
    def warmup(self, date: str = None):
        """
        Предзагрузка кеша в память
        
        Args:
            date: Дата для загрузки (если None - загружаем все)
        """
        self.logger.info("🔥 Прогрев OCR кеша...")
        count = 0
        
        if date:
            # Загружаем только для конкретной даты
            date_folder = self.results_dir / date
            if date_folder.exists():
                count = self._warmup_folder(date_folder, date)
        else:
            # Загружаем все даты
            for date_folder in self.results_dir.iterdir():
                if date_folder.is_dir():
                    count += self._warmup_folder(date_folder, date_folder.name)
        
        self.logger.info(f"✅ Загружено {count} результатов OCR в кеш")
    
    def _warmup_folder(self, folder: Path, date: str) -> int:
        """Загрузка файлов из папки в кеш"""
        count = 0
        for txt_file in folder.glob("*.txt"):
            try:
                text = txt_file.read_text(encoding='utf-8')
                # Извлекаем оригинальное имя файла (без .txt)
                filename = txt_file.stem
                cache_key = f"{date}:{filename}"
                self._cache[cache_key] = text
                count += 1
            except Exception:
                pass
        return count
    
    def get_stats(self) -> Dict:
        """Получить статистику использования кеша"""
        hit_rate = 0
        if self.stats['total_checks'] > 0:
            hit_rate = (self.stats['cache_hits'] / self.stats['total_checks']) * 100
        
        return {
            'total_checks': self.stats['total_checks'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'hit_rate': round(hit_rate, 2),
            'cache_size': len(self._cache)
        }
    
    def clear_cache(self):
        """Очистить in-memory кеш"""
        self._cache = {}
        self.logger.info("Кеш очищен")
