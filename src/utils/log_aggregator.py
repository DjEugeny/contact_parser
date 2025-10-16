#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Агрегатор логов для группировки однотипных сообщений

Позволяет собирать однотипные warnings и выводить их сгруппированно,
избегая засорения логов повторяющимися сообщениями.

Author: Contact Parser Team
Created: 2025-10-16
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional
from contextlib import contextmanager


class LogAggregator:
    """
    📊 Агрегатор логов для группировки однотипных сообщений
    
    Использование:
    ```python
    aggregator = LogAggregator()
    
    # Собираем warnings
    for item in items:
        if has_issue(item):
            aggregator.add_warning("missing_path", f"У вложения '{item}' отсутствует путь")
    
    # Выводим сгруппированные warnings
    aggregator.flush()
    ```
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Инициализация агрегатора
        
        Args:
            logger: Logger для вывода сообщений (если None, используется root logger)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.warnings: Dict[str, List[str]] = defaultdict(list)
        self.errors: Dict[str, List[str]] = defaultdict(list)
        self.info: Dict[str, List[str]] = defaultdict(list)
        self._enabled = True
    
    def add_warning(self, category: str, message: str):
        """
        Добавить warning в категорию
        
        Args:
            category: Категория warning (например, "missing_path", "validation_error")
            message: Сообщение warning
        """
        if self._enabled:
            self.warnings[category].append(message)
    
    def add_error(self, category: str, message: str):
        """
        Добавить error в категорию
        
        Args:
            category: Категория error
            message: Сообщение error
        """
        if self._enabled:
            self.errors[category].append(message)
    
    def add_info(self, category: str, message: str):
        """
        Добавить info в категорию
        
        Args:
            category: Категория info
            message: Сообщение info
        """
        if self._enabled:
            self.info[category].append(message)
    
    def flush(self, show_details: bool = False):
        """
        Вывести все накопленные сообщения сгруппированно
        
        Args:
            show_details: Показывать ли детали каждого сообщения
        """
        if not self._enabled:
            return
        
        # Выводим errors
        for category, messages in self.errors.items():
            count = len(messages)
            if count == 1:
                self.logger.error(f"❌ {messages[0]}")
            else:
                self.logger.error(f"❌ {category}: {count} ошибок")
                if show_details:
                    for msg in messages[:5]:  # Показываем первые 5
                        self.logger.error(f"   - {msg}")
                    if count > 5:
                        self.logger.error(f"   ... и ещё {count - 5} ошибок")
        
        # Выводим warnings
        for category, messages in self.warnings.items():
            count = len(messages)
            if count == 1:
                self.logger.warning(f"⚠️ {messages[0]}")
            else:
                self.logger.warning(f"⚠️ {category}: {count} предупреждений")
                if show_details:
                    for msg in messages[:5]:  # Показываем первые 5
                        self.logger.warning(f"   - {msg}")
                    if count > 5:
                        self.logger.warning(f"   ... и ещё {count - 5} предупреждений")
        
        # Выводим info (только если есть что-то важное)
        for category, messages in self.info.items():
            count = len(messages)
            if count > 0:
                self.logger.info(f"ℹ️ {category}: {count} сообщений")
        
        # Очищаем после вывода
        self.clear()
    
    def clear(self):
        """Очистить все накопленные сообщения"""
        self.warnings.clear()
        self.errors.clear()
        self.info.clear()
    
    def get_summary(self) -> Dict[str, int]:
        """
        Получить сводку по количеству сообщений
        
        Returns:
            Dict с количеством warnings, errors, info
        """
        return {
            'warnings': sum(len(msgs) for msgs in self.warnings.values()),
            'errors': sum(len(msgs) for msgs in self.errors.values()),
            'info': sum(len(msgs) for msgs in self.info.values()),
            'categories': {
                'warnings': len(self.warnings),
                'errors': len(self.errors),
                'info': len(self.info)
            }
        }
    
    def disable(self):
        """Отключить агрегатор (все сообщения будут игнорироваться)"""
        self._enabled = False
    
    def enable(self):
        """Включить агрегатор"""
        self._enabled = True


@contextmanager
def aggregate_logs(logger: Optional[logging.Logger] = None, show_details: bool = False):
    """
    Context manager для агрегации логов
    
    Использование:
    ```python
    with aggregate_logs(logger) as agg:
        for item in items:
            if has_issue(item):
                agg.add_warning("issue_type", f"Issue with {item}")
    # Автоматически выведет сгруппированные warnings при выходе из контекста
    ```
    
    Args:
        logger: Logger для вывода
        show_details: Показывать ли детали
        
    Yields:
        LogAggregator instance
    """
    aggregator = LogAggregator(logger)
    try:
        yield aggregator
    finally:
        aggregator.flush(show_details=show_details)


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Пример 1: Базовое использование
    print("\n=== Пример 1: Базовое использование ===")
    agg = LogAggregator(logger)
    
    for i in range(15):
        agg.add_warning("missing_path", f"У вложения 'file_{i}' отсутствует путь")
    
    for i in range(3):
        agg.add_error("validation", f"Ошибка валидации в письме {i}")
    
    agg.flush()
    
    # Пример 2: С деталями
    print("\n=== Пример 2: С деталями ===")
    agg2 = LogAggregator(logger)
    
    for i in range(10):
        agg2.add_warning("ocr_cache_miss", f"OCR кеш промах для файла_{i}.pdf")
    
    agg2.flush(show_details=True)
    
    # Пример 3: Context manager
    print("\n=== Пример 3: Context manager ===")
    with aggregate_logs(logger, show_details=True) as agg:
        for i in range(8):
            agg.add_warning("duplicate", f"Дубликат контакта: contact_{i}")
