#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 OCRManager - Унифицированный менеджер OCR обработки с кешированием

Основные возможности:
- Единая точка входа для всех OCR операций
- Кеширование результатов обработки
- Предотвращение дублирования вызовов
- Singleton паттерн для оптимизации ресурсов
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import threading
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Импорт существующего OCRProcessor
try:
    from src.ocr_processor import OCRProcessor
except ImportError:
    from ocr_processor import OCRProcessor

# Импорт системы кеширования результатов
try:
    from .result_cache import get_result_cache, CacheConfig
except ImportError:
    try:
        from result_cache import get_result_cache, CacheConfig
    except ImportError:
        # Fallback если система кеширования недоступна
        get_result_cache = None
        CacheConfig = None


class OCRManager:
    """
    🎯 Унифицированный менеджер OCR обработки
    
    Реализует Singleton паттерн для предотвращения множественных инициализаций
    тяжелых OCR компонентов и обеспечивает кеширование результатов.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(OCRManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Предотвращаем повторную инициализацию
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self._ocr_processor = None
        self._cache = {}
        self._cache_file = Path("data/cache/ocr_cache.json")
        self._setup_logging()
        self._load_cache()
        
        # ВРЕМЕННО ОТКЛЮЧЕНО: Инициализация новой системы кеширования
        self.result_cache = None
        # if get_result_cache and CacheConfig:
        #     try:
        #         cache_config = CacheConfig(
        #             ocr_ttl=86400,  # 24 часа для OCR результатов
        #             enable_local_cache=True,
        #             enable_compression=True
        #         )
        #         self.result_cache = get_result_cache(cache_config)
        #         self.logger.info("Новая система кеширования OCR подключена")
        #     except Exception as e:
        #         self.logger.warning(f"Не удалось подключить новую систему кеширования: {e}")
        self.logger.info("💾 OCR КЭШИРОВАНИЕ ОТКЛЮЧЕНО ДЛЯ ОТЛАДКИ")
        
        # Статистика использования
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_requests': 0,
            'processing_time_saved': 0.0,
            'new_cache_hits': 0,
            'old_cache_hits': 0
        }
        
        self.logger.info("OCRManager инициализирован")
    
    def _setup_logging(self):
        """Настройка логирования для OCRManager"""
        self.logger = logging.getLogger('OCRManager')
        self.logger.setLevel(logging.INFO)
        
        # Избегаем дублирования обработчиков
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _get_ocr_processor(self) -> OCRProcessor:
        """Ленивая инициализация OCRProcessor"""
        if self._ocr_processor is None:
            self.logger.info("Инициализация OCRProcessor...")
            self._ocr_processor = OCRProcessor()
        return self._ocr_processor
    
    def _generate_cache_key(self, file_path: str, date: str = None) -> str:
        """Генерация ключа кеша на основе пути файла и даты (старая система)"""
        # Используем путь файла и дату для создания уникального ключа
        key_data = f"{file_path}:{date or 'no_date'}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _generate_file_hash(self, file_path: str) -> str:
        """Генерация хеша файла для новой системы кеширования"""
        try:
            # Используем путь файла и время модификации для создания хеша
            file_stat = Path(file_path).stat()
            hash_data = f"{file_path}:{file_stat.st_mtime}:{file_stat.st_size}"
            return hashlib.md5(hash_data.encode()).hexdigest()
        except Exception:
            # Fallback на простой хеш пути
            return hashlib.md5(file_path.encode()).hexdigest()
    
    def _load_cache(self):
        """ВРЕМЕННО ОТКЛЮЧЕНО: Загрузка кеша из файла"""
        # try:
        #     if self._cache_file.exists():
        #         with open(self._cache_file, 'r', encoding='utf-8') as f:
        #             self._cache = json.load(f)
        #         self.logger.info(f"Загружен кеш с {len(self._cache)} записями")
        #     else:
        #         self._cache = {}
        #         # Создаем директорию для кеша
        #         self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        # except Exception as e:
        #     self.logger.error(f"Ошибка загрузки кеша: {e}")
        self._cache = {}
        self.logger.info("💾 OCR СТАРЫЙ КЭШ ОТКЛЮЧЕН ДЛЯ ОТЛАДКИ")
    
    def _save_cache(self):
        """Сохранение кеша в файл"""
        try:
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения кеша: {e}")
    
    def _is_cache_valid(self, cache_entry: Dict, file_path: str) -> bool:
        """Проверка валидности записи кеша"""
        try:
            # Проверяем существование файла
            if not os.path.exists(file_path):
                return False
            
            # Проверяем время модификации файла
            file_mtime = os.path.getmtime(file_path)
            cache_mtime = cache_entry.get('file_mtime', 0)
            
            return file_mtime <= cache_mtime
        except Exception:
            return False
    
    async def extract_text_from_file_async(self, file_path: str, date: str = None) -> Dict:
        """
        🎯 Асинхронный метод извлечения текста из файла с двухуровневым кешированием
        
        Args:
            file_path: Путь к файлу для обработки
            date: Дата для контекста обработки
            
        Returns:
            Dict с результатами обработки
        """
        # Используем ThreadPoolExecutor для выполнения синхронного метода
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(
                executor, 
                self.extract_text_from_file, 
                file_path, 
                date
            )
    
    def extract_text_from_file(self, file_path: str, date: str = None) -> Dict:
        """
        🎯 Основной метод извлечения текста из файла с двухуровневым кешированием
        
        Args:
            file_path: Путь к файлу для обработки
            date: Дата для контекста обработки
            
        Returns:
            Dict с результатами обработки
        """
        self.stats['total_requests'] += 1
        start_time = time.time()
        
        # Проверяем существование файла
        if not Path(file_path).exists():
            return {
                'success': False,
                'error': f'Файл не найден: {file_path}',
                'text': '',
                'processing_time': 0,
                'cached': False
            }
        
        # Генерируем хеш файла для новой системы кеширования
        file_hash = self._generate_file_hash(file_path)
        
        # ВРЕМЕННО ОТКЛЮЧЕНО: Проверяем новую систему кеширования
        # if self.result_cache:
        #     cached_text = self.result_cache.get_ocr_result(file_hash)
        #     if cached_text:
        #         self.stats['cache_hits'] += 1
        #         self.stats['new_cache_hits'] += 1
        #         processing_time = time.time() - start_time
        #         
        #         self.logger.info(f"New Cache HIT для {Path(file_path).name}")
        #         
        #         return {
        #             'success': True,
        #             'text': cached_text,
        #             'processing_time': processing_time,
        #             'cached': True,
        #             'cache_type': 'new_system'
        #         }
        
        # ВРЕМЕННО ОТКЛЮЧЕНО: Fallback на старую систему кеширования
        # cache_key = self._generate_cache_key(file_path, date)
        # 
        # if cache_key in self._cache:
        #     cache_entry = self._cache[cache_key]
        #     if self._is_cache_valid(cache_entry, file_path):
        #         self.stats['cache_hits'] += 1
        #         self.stats['old_cache_hits'] += 1
        #         processing_time = time.time() - start_time
        #         self.stats['processing_time_saved'] += cache_entry.get('original_processing_time', 0) - processing_time
        #         
        #         self.logger.info(f"Old Cache HIT для {Path(file_path).name}")
        #         
        #         # Мигрируем в новую систему кеширования
        #         if self.result_cache and 'result' in cache_entry and 'text' in cache_entry['result']:
        #             self.result_cache.cache_ocr_result(file_hash, cache_entry['result']['text'])
        #         
        #         return {
        #             **cache_entry['result'],
        #             'cached': True,
        #             'cache_retrieval_time': processing_time,
        #             'cache_type': 'old_system'
        #         }
        
        self.logger.info(f"💾 КЭШИРОВАНИЕ ОТКЛЮЧЕНО: Выполняем OCR для {Path(file_path).name}")
        
        # Кеш промах - выполняем обработку
        self.stats['cache_misses'] += 1
        self.logger.info(f"Кеш промах для {Path(file_path).name}, выполняем OCR обработку")
        
        try:
            # Получаем OCR процессор и выполняем обработку
            ocr_processor = self._get_ocr_processor()
            result = ocr_processor.extract_text_from_file(Path(file_path), date)
            
            processing_time = time.time() - start_time
            
            # ВРЕМЕННО ОТКЛЮЧЕНО: Кешируем в новой системе
            # if self.result_cache and result.get('success') and 'text' in result:
            #     self.result_cache.cache_ocr_result(file_hash, result['text'])
            
            # ВРЕМЕННО ОТКЛЮЧЕНО: Сохраняем результат в старый кеш для совместимости
            # try:
            #     file_mtime = os.path.getmtime(file_path)
            #     cache_key = self._generate_cache_key(file_path, date)
            #     self._cache[cache_key] = {
            #         'result': result,
            #         'timestamp': datetime.now().isoformat(),
            #         'file_mtime': file_mtime,
            #         'original_processing_time': processing_time,
            #         'file_path': file_path,
            #         'date': date
            #     }
            #     self._save_cache()
            # except Exception as e:
            #     self.logger.error(f"Ошибка сохранения в старый кеш: {e}")
            
            self.logger.info(f"💾 КЭШИРОВАНИЕ ОТКЛЮЧЕНО: Результат не сохраняется в кэш")
            
            return {
                **result,
                'cached': False,
                'processing_time': processing_time,
                'cache_type': 'none'
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка OCR обработки {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'processing_time': time.time() - start_time,
                'cached': False,
                'cache_type': 'none'
            }
    
    async def test_files_by_date_async(self, date: str, files_to_test: List[Path] = None, limit: int = None) -> Dict:
        """
        🎯 Асинхронная версия тестирования файлов по дате
        
        Args:
            date: Дата для фильтрации файлов
            files_to_test: Список файлов для тестирования (опционально)
            limit: Лимит количества файлов для обработки
            
        Returns:
            Dict с результатами тестирования
        """
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(
                executor,
                self.test_files_by_date,
                date,
                files_to_test,
                limit
            )
    
    def test_files_by_date(self, date: str, files_to_test: List[Path] = None, limit: int = None) -> Dict:
        """
        🎯 Обработка файлов по дате с использованием кеширования
        
        Args:
            date: Дата для обработки
            files_to_test: Список файлов для обработки (опционально)
            limit: Лимит файлов для обработки
            
        Returns:
            Dict со статистикой обработки
        """
        self.logger.info(f"Начало обработки файлов для даты {date}")
        
        # Получаем OCR процессор
        ocr_processor = self._get_ocr_processor()
        
        # Если файлы не указаны, получаем их из OCR процессора
        if files_to_test is None:
            files_to_test = ocr_processor.get_files_for_date(date)
        
        # Применяем лимит если указан
        if limit:
            files_to_test = files_to_test[:limit]
        
        # Обрабатываем файлы через унифицированный интерфейс
        results = []
        for file_path in files_to_test:
            result = self.extract_text_from_file(str(file_path), date)
            results.append(result)
        
        # Возвращаем статистику
        return {
            'date': date,
            'total_files': len(files_to_test),
            'processed_files': len(results),
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'processing_time_saved': self.stats['processing_time_saved']
        }
    
    def get_cache_stats(self) -> Dict:
        """Получение статистики кеширования"""
        cache_hit_rate = 0
        if self.stats['total_requests'] > 0:
            cache_hit_rate = (self.stats['cache_hits'] / self.stats['total_requests']) * 100
        
        return {
            'total_requests': self.stats['total_requests'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'cache_hit_rate': round(cache_hit_rate, 2),
            'processing_time_saved': round(self.stats['processing_time_saved'], 2),
            'cache_entries': len(self._cache)
        }
    
    def clear_cache(self):
        """Очистка кеша"""
        self._cache = {}
        try:
            if self._cache_file.exists():
                self._cache_file.unlink()
            self.logger.info("Кеш очищен")
        except Exception as e:
            self.logger.error(f"Ошибка очистки кеша: {e}")
    
    def cleanup_invalid_cache_entries(self):
        """Очистка недействительных записей кеша"""
        invalid_keys = []
        for key, entry in self._cache.items():
            file_path = entry.get('file_path', '')
            if not self._is_cache_valid(entry, file_path):
                invalid_keys.append(key)
        
        for key in invalid_keys:
            del self._cache[key]
        
        if invalid_keys:
            self._save_cache()
            self.logger.info(f"Удалено {len(invalid_keys)} недействительных записей кеша")


# Глобальный экземпляр для удобства использования
ocr_manager = OCRManager()


class AsyncOCRInterface:
    """
    🎯 Универсальный интерфейс для синхронного и асинхронного применения OCR алгоритмов
    
    Обеспечивает единообразное применение всех алгоритмов оптимизации
    (кэширование, предварительная обработка, параллельная обработка)
    как в синхронном, так и в асинхронном режиме.
    """
    
    def __init__(self, ocr_manager: OCRManager):
        self.ocr_manager = ocr_manager
    
    def extract_text(self, file_path: str, date: str = None, async_mode: bool = False) -> Dict:
        """
        🎯 Универсальный метод извлечения текста
        
        Args:
            file_path: Путь к файлу
            date: Дата для контекста
            async_mode: Флаг асинхронного режима
            
        Returns:
            Dict с результатами или корутину для async режима
        """
        if async_mode:
            return self.ocr_manager.extract_text_from_file_async(file_path, date)
        else:
            return self.ocr_manager.extract_text_from_file(file_path, date)
    
    def test_files_by_date(self, date: str, files_to_test: List[Path] = None, 
                          limit: int = None, async_mode: bool = False) -> Dict:
        """
        🎯 Универсальный метод тестирования файлов по дате
        
        Args:
            date: Дата для фильтрации
            files_to_test: Список файлов
            limit: Лимит файлов
            async_mode: Флаг асинхронного режима
            
        Returns:
            Dict с результатами или корутину для async режима
        """
        if async_mode:
            return self.ocr_manager.test_files_by_date_async(date, files_to_test, limit)
        else:
            return self.ocr_manager.test_files_by_date(date, files_to_test, limit)


def get_ocr_manager() -> OCRManager:
    """Функция для получения глобального экземпляра OCRManager"""
    return ocr_manager


def get_async_ocr_interface() -> AsyncOCRInterface:
    """Получить универсальный интерфейс для синхронного и асинхронного OCR"""
    return AsyncOCRInterface(ocr_manager)