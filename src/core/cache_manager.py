#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💾 Многоуровневая система кэширования
Фаза 6: Оптимизации производительности
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any
from functools import lru_cache
import logging


class MultiLevelCache:
    """
    💾 Многоуровневая система кэширования

    Уровни кэширования:
    1. Memory cache (LRU) - быстрый доступ в памяти
    2. File cache -持久ное хранение на диске
    3. Compressed cache - сжатие больших объектов
    """

    def __init__(self, cache_dir: Optional[Path] = None, max_memory_items: int = 100):
        self.logger = logging.getLogger(__name__)

        # Настройка директории кэша
        self.cache_dir = cache_dir or Path("cache")
        self.cache_dir.mkdir(exist_ok=True)

        # Статистика кэша
        self.stats = {
            'memory_hits': 0,
            'memory_misses': 0,
            'file_hits': 0,
            'file_misses': 0,
            'total_requests': 0,
            'cache_size_mb': 0,
            'items_count': 0
        }

        self.max_memory_items = max_memory_items
        self.memory_cache: Dict[str, Dict[str, Any]] = {}

        # Очистка устаревших файлов кэша (старше 24 часов)
        self._cleanup_old_cache_files()

        self.logger.info(f"💾 MultiLevelCache инициализирован в {self.cache_dir}")

    def _get_cache_key(self, content: str, metadata: Optional[Dict] = None) -> str:
        """🔑 Генерировать ключ кэша на основе контента"""
        if metadata:
            # Добавляем метаданные для уникальности
            cache_content = f"{content}_{json.dumps(metadata, sort_keys=True)}"
        else:
            cache_content = content

        return hashlib.sha256(cache_content.encode('utf-8')).hexdigest()

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """📁 Получить путь к файлу кэша"""
        # Разбиваем на поддиректории для лучшей производительности
        subdir = cache_key[:2]
        cache_subdir = self.cache_dir / subdir
        cache_subdir.mkdir(exist_ok=True)

        return cache_subdir / f"{cache_key}.json"

    def _is_cache_valid(self, cache_file: Path, max_age_seconds: int = 86400) -> bool:
        """✅ Проверить валидность файла кэша по времени"""
        if not cache_file.exists():
            return False

        file_age = time.time() - cache_file.stat().st_mtime
        return file_age < max_age_seconds

    @lru_cache(maxsize=50)
    def get_prompt(self, prompt_name: str) -> Optional[str]:
        """
        📝 Получить промпт из кэша (LRU в памяти)

        Args:
            prompt_name: Имя промпта

        Returns:
            str или None если не найден
        """
        self.stats['total_requests'] += 1

        # Сначала проверяем в памяти
        if prompt_name in self.memory_cache:
            self.stats['memory_hits'] += 1
            cache_entry = self.memory_cache[prompt_name]

            if self._is_cache_valid(Path(cache_entry['file_path'])):
                return cache_entry['content']
            else:
                # Удаляем устаревший кэш
                del self.memory_cache[prompt_name]

        self.stats['memory_misses'] += 1

        # Загружаем из файла
        prompt_file = Path("prompts") / f"{prompt_name}.txt"
        if prompt_file.exists():
            try:
                content = prompt_file.read_text(encoding='utf-8')

                # Кэшируем в память
                self.memory_cache[prompt_name] = {
                    'content': content,
                    'file_path': str(prompt_file),
                    'cached_at': time.time()
                }

                return content
            except Exception as e:
                self.logger.error(f"Ошибка чтения промпта {prompt_name}: {e}")

        return None

    def get_llm_response(self, prompt_hash: str, provider: str,
                        max_age_seconds: int = 3600) -> Optional[Dict[str, Any]]:
        """
        🤖 Получить LLM ответ из кэша

        Args:
            prompt_hash: Хэш промпта
            provider: Имя провайдера
            max_age_seconds: Максимальный возраст кэша (по умолчанию 1 час)

        Returns:
            Dict с ответом или None
        """
        self.stats['total_requests'] += 1
        cache_key = f"{provider}_{prompt_hash}"

        # Проверяем в памяти
        if cache_key in self.memory_cache:
            self.stats['memory_hits'] += 1
            cache_entry = self.memory_cache[cache_key]

            if time.time() - cache_entry['cached_at'] < max_age_seconds:
                return cache_entry['data']
            else:
                # Удаляем устаревший кэш
                del self.memory_cache[cache_key]

        self.stats['memory_misses'] += 1

        # Проверяем на диске
        cache_file = self._get_cache_file_path(cache_key)
        if cache_file.exists() and self._is_cache_valid(cache_file, max_age_seconds):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)

                self.stats['file_hits'] += 1

                # Кэшируем в память
                self.memory_cache[cache_key] = {
                    'data': cached_data,
                    'cached_at': time.time(),
                    'file_path': str(cache_file)
                }

                return cached_data
            except Exception as e:
                self.logger.error(f"Ошибка чтения кэша {cache_key}: {e}")
        else:
            self.stats['file_misses'] += 1

        return None

    def set_llm_response(self, prompt_hash: str, provider: str,
                        response: Dict[str, Any], compress_large: bool = True):
        """
        💾 Сохранить LLM ответ в кэш

        Args:
            prompt_hash: Хэш промпта
            provider: Имя провайдера
            response: Ответ для кэширования
            compress_large: Сжимать большие ответы
        """
        cache_key = f"{provider}_{prompt_hash}"

        # Определяем размер ответа
        response_size = len(json.dumps(response, ensure_ascii=False))

        # Для очень больших ответов (>100KB) используем сжатие
        if compress_large and response_size > 100000:
            import gzip
            compressed_data = gzip.compress(
                json.dumps(response, ensure_ascii=False).encode('utf-8')
            )
            response['_compressed'] = True
            response['_original_size'] = response_size

        # Сохраняем в файл
        cache_file = self._get_cache_file_path(cache_key)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)

            # Кэшируем в память
            self.memory_cache[cache_key] = {
                'data': response,
                'cached_at': time.time(),
                'file_path': str(cache_file)
            }

            # Обновляем статистику размера
            self._update_cache_stats()

        except Exception as e:
            self.logger.error(f"Ошибка сохранения в кэш {cache_key}: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """📊 Получить статистику кэша"""
        stats = self.stats.copy()

        # Вычисляем процент попаданий
        if stats['total_requests'] > 0:
            stats['memory_hit_rate'] = (stats['memory_hits'] / stats['total_requests']) * 100
            stats['file_hit_rate'] = (stats['file_hits'] / stats['total_requests']) * 100
            stats['overall_hit_rate'] = ((stats['memory_hits'] + stats['file_hits']) /
                                        stats['total_requests']) * 100
        else:
            stats['memory_hit_rate'] = 0
            stats['file_hit_rate'] = 0
            stats['overall_hit_rate'] = 0

        # Количество элементов в памяти
        stats['memory_items'] = len(self.memory_cache)

        return stats

    def _update_cache_stats(self):
        """🔄 Обновить статистику размера кэша"""
        try:
            total_size = 0
            items_count = 0

            # Подсчитываем размер всех файлов кэша
            for cache_file in self.cache_dir.rglob("*.json"):
                total_size += cache_file.stat().st_size
                items_count += 1

            self.stats['cache_size_mb'] = total_size / (1024 * 1024)
            self.stats['items_count'] = items_count

        except Exception as e:
            self.logger.error(f"Ошибка обновления статистики кэша: {e}")

    def _cleanup_old_cache_files(self, max_age_hours: int = 24):
        """🧹 Очистить старые файлы кэша"""
        try:
            max_age_seconds = max_age_hours * 3600
            deleted_count = 0

            for cache_file in self.cache_dir.rglob("*.json"):
                if not self._is_cache_valid(cache_file, max_age_seconds):
                    cache_file.unlink()
                    deleted_count += 1

            if deleted_count > 0:
                self.logger.info(f"🧹 Удалено {deleted_count} устаревших файлов кэша")

        except Exception as e:
            self.logger.error(f"Ошибка очистки кэша: {e}")

    def clear_cache(self, cache_type: str = "all"):
        """
        🗑️ Очистить кэш

        Args:
            cache_type: Тип кэша ('memory', 'file', 'all')
        """
        if cache_type in ['memory', 'all']:
            self.memory_cache.clear()
            self.logger.info("🧹 Очищен кэш в памяти")

        if cache_type in ['file', 'all']:
            try:
                for cache_file in self.cache_dir.rglob("*.json"):
                    cache_file.unlink()
                self.logger.info("🧹 Очищены файлы кэша на диске")
            except Exception as e:
                self.logger.error(f"Ошибка очистки файлового кэша: {e}")

        self._update_cache_stats()

    def preload_frequent_prompts(self, prompt_names: list):
        """
        🚀 Предварительная загрузка часто используемых промптов

        Args:
            prompt_names: Список имен промптов для загрузки
        """
        for prompt_name in prompt_names:
            self.get_prompt(prompt_name)  # Автоматически кэширует

        self.logger.info(f"🚀 Предварительно загружено {len(prompt_names)} промптов")
