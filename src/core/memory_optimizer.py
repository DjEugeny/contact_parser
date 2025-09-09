#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 Memory Оптимизатор для обработки больших текстов
Фаза 6: Оптимизации производительности
"""

import gc
import mmap
import psutil
from typing import Dict, Any, Optional, Iterator
from pathlib import Path
import logging
from contextlib import contextmanager


class MemoryOptimizer:
    """
    🧠 Оптимизатор памяти для обработки больших текстов и файлов

    Функциональность:
    - Streaming обработка больших файлов
    - Memory mapping для эффективного чтения
    - Оптимизация garbage collection
    - Мониторинг использования памяти
    - Автоматическая очистка больших объектов
    """

    def __init__(self, max_memory_mb: int = 500, gc_threshold_mb: int = 200):
        self.logger = logging.getLogger(__name__)

        self.max_memory_mb = max_memory_mb
        self.gc_threshold_mb = gc_threshold_mb

        # Статистика памяти
        self.memory_stats = {
            'peak_memory_mb': 0,
            'current_memory_mb': 0,
            'gc_collections': 0,
            'large_objects_cleaned': 0,
            'files_processed': 0,
            'memory_mapped_files': 0
        }

        # Настройки GC
        self._configure_gc()

        self.logger.info(f"🧠 MemoryOptimizer инициализирован (макс {max_memory_mb}MB)")

    def _configure_gc(self):
        """⚙️ Настройка garbage collector для оптимальной работы"""
        import gc

        # Устанавливаем пороги GC для более частой очистки
        gc.set_threshold(700, 10, 10)  # generation 0, 1, 2

        # Включаем отладку для отслеживания больших объектов
        gc.set_debug(gc.DEBUG_SAVEALL)  # Сохранять все объекты для анализа

        self.logger.debug("🗑️ GC настроен для оптимизации памяти")

    @contextmanager
    def memory_monitor(self):
        """
        📊 Контекстный менеджер для мониторинга использования памяти

        Использование:
        ```python
        with optimizer.memory_monitor():
            # Ваш код обработки данных
            result = process_large_data()
        ```
        """
        start_memory = self.get_memory_usage()
        start_objects = len(gc.get_objects())

        try:
            yield
        finally:
            end_memory = self.get_memory_usage()
            end_objects = len(gc.get_objects())

            memory_delta = end_memory - start_memory
            objects_delta = end_objects - start_objects

            self.logger.info(f"📊 Использование памяти: {memory_delta:.1f}MB, объектов: {objects_delta}")

            # Автоматическая очистка если превышен порог
            if end_memory > self.gc_threshold_mb:
                self.optimize_memory_usage()

    def get_memory_usage(self) -> float:
        """📏 Получить текущее использование памяти (MB)"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики памяти: {e}")
            return 0.0

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """
        🧹 Оптимизация использования памяти

        Returns:
            Dict со статистикой очистки
        """
        start_memory = self.get_memory_usage()

        # Принудительная сборка мусора
        collected = gc.collect()
        self.memory_stats['gc_collections'] += 1

        # Получение статистики после очистки
        end_memory = self.get_memory_usage()
        memory_freed = start_memory - end_memory

        # Анализ больших объектов
        large_objects = []
        for obj in gc.get_objects():
            try:
                size = len(obj) if hasattr(obj, '__len__') else 0
                if size > 1000000:  # > 1MB
                    large_objects.append({
                        'type': type(obj).__name__,
                        'size': size,
                        'size_mb': size / 1024 / 1024
                    })
            except:
                pass

        # Очистка больших объектов если необходимо
        cleaned_count = 0
        for obj_info in large_objects:
            if obj_info['size_mb'] > 50:  # > 50MB
                # Попытка очистить объект
                try:
                    del obj_info
                    cleaned_count += 1
                except:
                    pass

        self.memory_stats['large_objects_cleaned'] += cleaned_count

        stats = {
            'memory_before_mb': start_memory,
            'memory_after_mb': end_memory,
            'memory_freed_mb': memory_freed,
            'objects_collected': collected,
            'large_objects_found': len(large_objects),
            'large_objects_cleaned': cleaned_count
        }

        self.logger.info(f"🧹 GC очистил {collected} объектов, освободил {memory_freed:.1f}MB")
        return stats

    def process_large_file_stream(self, file_path: Path, chunk_size: int = 8192) -> Iterator[str]:
        """
        🌊 Streaming обработка большого файла

        Args:
            file_path: Путь к файлу
            chunk_size: Размер чанка в байтах

        Yields:
            str: Чанки текста файла
        """
        self.memory_stats['files_processed'] += 1

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                buffer = ""

                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break

                    buffer += chunk

                    # Если буфер стал слишком большим, обрабатываем
                    if len(buffer) > 50000:  # 50KB
                        yield buffer
                        buffer = ""

                # Обрабатываем остаток
                if buffer:
                    yield buffer

        except Exception as e:
            self.logger.error(f"Ошибка streaming файла {file_path}: {e}")
            yield ""

    def process_with_memory_map(self, file_path: Path) -> Optional[str]:
        """
        🗺️ Обработка файла с memory mapping

        Args:
            file_path: Путь к файлу

        Returns:
            str или None при ошибке
        """
        try:
            self.memory_stats['memory_mapped_files'] += 1

            with open(file_path, 'r', encoding='utf-8') as f:
                # Создаем memory map
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    # Читаем без загрузки всего файла в память
                    text = mm.read().decode('utf-8')

                    # Обновляем пиковое использование памяти
                    current_memory = self.get_memory_usage()
                    if current_memory > self.memory_stats['peak_memory_mb']:
                        self.memory_stats['peak_memory_mb'] = current_memory

                    return text

        except Exception as e:
            self.logger.error(f"Ошибка memory mapping файла {file_path}: {e}")
            return None

    def process_email_with_optimization(self, email_path: Path, attachment_paths: Optional[list] = None) -> Dict[str, Any]:
        """
        📧 Оптимизированная обработка email с вложениями

        Args:
            email_path: Путь к JSON файлу email
            attachment_paths: Список путей к файлам вложений

        Returns:
            Dict с оптимизированными данными
        """
        result = {
            'email_text': '',
            'attachments_text': [],
            'processing_stats': {},
            'memory_usage': {}
        }

        start_memory = self.get_memory_usage()

        try:
            # Загружаем основной текст email
            if email_path.exists():
                if email_path.stat().st_size > 10 * 1024 * 1024:  # > 10MB
                    # Используем memory mapping для больших файлов
                    email_text = self.process_with_memory_map(email_path)
                else:
                    # Обычная загрузка для небольших файлов
                    email_text = email_path.read_text(encoding='utf-8')

                if email_text:
                    result['email_text'] = email_text

            # Обрабатываем вложения
            if attachment_paths:
                for attachment_path in attachment_paths:
                    if attachment_path.exists():
                        if attachment_path.stat().st_size > 5 * 1024 * 1024:  # > 5MB
                            # Streaming для больших вложений
                            attachment_text = ""
                            for chunk in self.process_large_file_stream(attachment_path):
                                attachment_text += chunk
                        else:
                            # Обычная загрузка
                            attachment_text = attachment_path.read_text(encoding='utf-8')

                        if attachment_text:
                            result['attachments_text'].append(attachment_text)

            # Оптимизируем память после обработки
            processing_memory = self.get_memory_usage()
            result['processing_stats'] = {
                'email_size_mb': email_path.stat().st_size / 1024 / 1024 if email_path.exists() else 0,
                'attachments_count': len(attachment_paths) if attachment_paths else 0,
                'total_text_length': len(result['email_text']) + sum(len(att) for att in result['attachments_text'])
            }

            result['memory_usage'] = {
                'start_mb': start_memory,
                'processing_mb': processing_memory,
                'peak_mb': self.memory_stats['peak_memory_mb']
            }

            # Финальная оптимизация памяти
            self.optimize_memory_usage()

            return result

        except Exception as e:
            self.logger.error(f"Ошибка обработки email {email_path}: {e}")
            return result

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """📈 Получить полную статистику оптимизатора"""
        current_memory = self.get_memory_usage()

        stats = {
            'memory_optimizer': {
                'current_memory_mb': current_memory,
                'peak_memory_mb': self.memory_stats['peak_memory_mb'],
                'max_allowed_mb': self.max_memory_mb,
                'gc_threshold_mb': self.gc_threshold_mb,
                'memory_efficiency': (self.max_memory_mb - current_memory) / self.max_memory_mb * 100
            },
            'processing_stats': {
                'files_processed': self.memory_stats['files_processed'],
                'memory_mapped_files': self.memory_stats['memory_mapped_files'],
                'gc_collections': self.memory_stats['gc_collections'],
                'large_objects_cleaned': self.memory_stats['large_objects_cleaned']
            },
            'system_info': {
                'python_gc_stats': gc.get_stats(),
                'total_objects': len(gc.get_objects()),
                'process_memory_percent': psutil.Process().memory_percent()
            }
        }

        return stats

    def is_memory_critical(self) -> bool:
        """🚨 Проверить критическое использование памяти"""
        current_memory = self.get_memory_usage()
        return current_memory > self.max_memory_mb * 0.9  # > 90% от максимума

    def emergency_memory_cleanup(self):
        """🚨 Экстренная очистка памяти при критическом использовании"""
        self.logger.warning("🚨 Экстренная очистка памяти!")

        # Агрессивная сборка мусора
        for _ in range(3):
            gc.collect()

        # Очистка всех возможных кэшей
        try:
            import sys
            for module_name in list(sys.modules.keys()):
                if 'cache' in module_name.lower():
                    module = sys.modules[module_name]
                    if hasattr(module, 'clear'):
                        module.clear()
        except:
            pass

        self.logger.info(f"🚨 Экстренная очистка завершена, память: {self.get_memory_usage():.1f}MB")
