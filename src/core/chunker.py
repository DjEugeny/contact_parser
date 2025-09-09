#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✂️ Модуль для разбиения больших текстов на части
Фаза 5: Архитектурная оптимизация
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False
    print("⚠️ tiktoken не установлен, используется символьный chunking")


@dataclass
class ChunkingConfig:
    """📋 Конфигурация для chunking текста"""
    max_chunk_size: int = 8000
    overlap_size: int = 1000
    use_tokens: bool = True
    encoding_model: str = 'cl100k_base'
    max_chunks_per_text: int = 20
    min_chunk_size: int = 1000
    auto_adjust_chunk_size: bool = True
    smart_boundary_detection: bool = True
    chunk_alert_threshold: int = 20
    chunk_abort_threshold: int = 50
    allow_chunk_abort: bool = True
    memory_optimization: bool = True
    progressive_chunking: bool = True

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> 'ChunkingConfig':
        """📁 Загрузка конфигурации из файла"""
        if not config_path:
            config_path = Path(__file__).parent.parent.parent / "config" / "processing_config.json"

        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    chunking_config = config.get('chunking', {})

                # Создаем экземпляр с загруженными настройками
                return cls(**chunking_config)
            else:
                print(f"⚠️ Файл конфигурации не найден: {config_path}")
                return cls()
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации chunking: {e}")
            return cls()


class TextChunker:
    """
    ✂️ Модуль для разбиения больших текстов на части

    Поддерживает:
    - Токен-ориентированное разбиение (tiktoken)
    - Символьное разбиение (fallback)
    - Автоматическую корректировку размера чанков
    - Контроль максимального числа чанков
    - Статистику операций
    """

    def __init__(self, config: ChunkingConfig):
        self.config = config
        self.stats = {
            'total_chunks_created': 0,
            'token_based_chunks': 0,
            'character_based_chunks': 0,
            'texts_chunked': 0,
            'texts_not_chunked': 0,
            'avg_chunk_size': 0,
            'max_chunks_in_text': 0,
            'alerts_triggered': 0,
            'aborts_triggered': 0
        }

        print("✂️ TextChunker инициализирован")
        print(f"   📏 Max chunk size: {self.config.max_chunk_size}")
        print(f"   🔄 Overlap: {self.config.overlap_size}")
        print(f"   🎯 Use tokens: {self.config.use_tokens and TIKTOKEN_AVAILABLE}")

    def create_chunks(self, text: str) -> List[str]:
        """
        🎯 Основной метод создания чанков

        Args:
            text: Исходный текст для разбиения

        Returns:
            List[str]: Список чанков текста
        """
        text_length = len(text)

        # Проверяем необходимость chunking
        if not self.should_chunk(text):
            self.stats['texts_not_chunked'] += 1
            return [text]

        self.stats['texts_chunked'] += 1

        # Выбираем метод chunking
        if self.config.use_tokens and TIKTOKEN_AVAILABLE:
            chunks = self._create_token_based_chunks(text)
            self.stats['token_based_chunks'] += len(chunks)
        else:
            chunks = self._create_character_based_chunks(text)
            self.stats['character_based_chunks'] += len(chunks)

        self.stats['total_chunks_created'] += len(chunks)

        # Обновляем статистику
        if chunks:
            self.stats['avg_chunk_size'] = sum(len(chunk) for chunk in chunks) / len(chunks)
            self.stats['max_chunks_in_text'] = max(self.stats['max_chunks_in_text'], len(chunks))

        print(f"✂️ Создано {len(chunks)} чанков из {text_length} символов")
        return chunks

    def _create_token_based_chunks(self, text: str) -> List[str]:
        """
        🎯 Токен-ориентированное разбиение текста

        Args:
            text: Исходный текст

        Returns:
            List[str]: Список чанков
        """
        try:
            # Инициализируем энкодер
            encoding = tiktoken.get_encoding(self.config.encoding_model)

            # Кодируем весь текст
            tokens = encoding.encode(text)
            total_tokens = len(tokens)

            print(f"   🎯 Токен-ориентированное разбиение: {total_tokens} токенов")

            # Параметры chunking
            max_tokens = min(self.config.max_chunk_size, 8000)  # Ограничение для безопасности
            overlap_tokens = min(self.config.overlap_size, max_tokens // 10)
            max_chunks = self.config.max_chunks_per_text

            # Предварительная оценка количества чанков
            estimated_chunks = max(1, total_tokens // (max_tokens - overlap_tokens))
            print(f"   📊 Предварительная оценка: ~{estimated_chunks} чанков")

            # Alert при превышении порога
            if estimated_chunks > self.config.chunk_alert_threshold:
                print(f"   ⚠️ ВНИМАНИЕ: Ожидается {estimated_chunks} чанков (>{self.config.chunk_alert_threshold})")
                print(f"   📈 Это может привести к высокому потреблению API токенов")
                self.stats['alerts_triggered'] += 1

            # Прерывание при критическом превышении
            if self.config.allow_chunk_abort and estimated_chunks > self.config.chunk_abort_threshold:
                print(f"   🚫 КРИТИЧЕСКОЕ ПРЕВЫШЕНИЕ: {estimated_chunks} чанков (>{self.config.chunk_abort_threshold})")
                print(f"   ⛔ Обработка прервана для защиты от чрезмерного потребления API")
                print(f"   💡 Рекомендация: увеличьте max_chunk_size или уменьшите размер текста")

                # Возвращаем только первые несколько чанков как fallback
                fallback_chunks = min(5, self.config.chunk_abort_threshold // 2)
                print(f"   🔄 Fallback: создаем только {fallback_chunks} чанков")
                max_chunks = fallback_chunks
                self.stats['aborts_triggered'] += 1

            # Автоматическая корректировка размера chunk для очень больших текстов
            if self.config.auto_adjust_chunk_size and total_tokens > max_tokens * max_chunks:
                adjusted_max_tokens = min(
                    self.config.max_chunk_size,
                    total_tokens // max_chunks + overlap_tokens
                )
                if adjusted_max_tokens > max_tokens:
                    max_tokens = adjusted_max_tokens
                    print(f"   📈 Автокорректировка: увеличен размер chunk до {max_tokens} токенов")

            # Создание чанков
            chunks = []
            start_token = 0

            while start_token < total_tokens and len(chunks) < max_chunks:
                # Определяем конец текущего chunk
                end_token = min(start_token + max_tokens, total_tokens)

                # Извлекаем токены для текущего chunk
                chunk_tokens = tokens[start_token:end_token]

                # Проверяем, что chunk не пустой
                if not chunk_tokens:
                    print(f"   ⚠️ Пустой chunk на позиции {start_token}-{end_token}, завершаем")
                    break

                # Декодируем обратно в текст
                chunk_text = encoding.decode(chunk_tokens)

                # Добавляем информацию о chunk
                chunk_info = f"\n\n[ЧАСТЬ {len(chunks) + 1} ИЗ БОЛЬШОГО ТЕКСТА, ТОКЕНЫ {start_token}-{end_token}]\n"
                chunk_with_info = chunk_info + chunk_text

                chunks.append(chunk_with_info)

                # Переходим к следующему chunk с учетом overlap
                if end_token < total_tokens:
                    start_token = end_token - overlap_tokens
                else:
                    break

            print(f"   ✅ Создано {len(chunks)} частей (токен-ориентированный метод)")
            return chunks

        except Exception as e:
            print(f"❌ Ошибка токен-ориентированного chunking: {e}")
            print("🔄 Переключение на символьный chunking")
            return self._create_character_based_chunks(text)

    def _create_character_based_chunks(self, text: str) -> List[str]:
        """
        📝 Символьное разбиение текста (fallback метод)

        Args:
            text: Исходный текст

        Returns:
            List[str]: Список чанков
        """
        chunk_size = min(self.config.max_chunk_size, 8000)  # Безопасное ограничение
        overlap = min(self.config.overlap_size, chunk_size // 10)
        max_chunks = self.config.max_chunks_per_text

        print(f"   📝 Символьное разбиение: {len(text)} символов, chunk_size={chunk_size}")

        chunks = []
        start = 0

        while start < len(text) and len(chunks) < max_chunks:
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]

            if not chunk.strip():
                print(f"   ⚠️ Пустой chunk на позиции {start}-{end}, завершаем")
                break

            # Добавляем информацию о chunk
            chunk_info = f"\n\n[ЧАСТЬ {len(chunks) + 1} ИЗ БОЛЬШОГО ТЕКСТА, СИМВОЛЫ {start}-{end}]\n"
            chunk_with_info = chunk_info + chunk

            chunks.append(chunk_with_info)

            # Переходим к следующему chunk с учетом overlap
            if end < len(text):
                start = end - overlap
            else:
                break

        print(f"   ✅ Создано {len(chunks)} частей (символьный метод)")
        return chunks

    def should_chunk(self, text: str) -> bool:
        """
        🤔 Определить необходимость chunking

        Args:
            text: Текст для проверки

        Returns:
            bool: True если нужен chunking
        """
        text_length = len(text)

        # Если текст маленький, chunking не нужен
        if text_length < self.config.min_chunk_size:
            return False

        # Если используем токены и tiktoken доступен, проверяем по токенам
        if self.config.use_tokens and TIKTOKEN_AVAILABLE:
            try:
                encoding = tiktoken.get_encoding(self.config.encoding_model)
                token_count = len(encoding.encode(text))
                return token_count > self.config.max_chunk_size
            except Exception:
                # При ошибке переходим к символьной проверке
                pass

        # Символьная проверка
        return text_length > self.config.max_chunk_size

    def get_chunk_stats(self) -> Dict[str, Any]:
        """
        📊 Получить статистику chunking операций

        Returns:
            Dict: Статистика операций
        """
        return {
            'chunker_stats': self.stats.copy(),
            'config': {
                'max_chunk_size': self.config.max_chunk_size,
                'overlap_size': self.config.overlap_size,
                'use_tokens': self.config.use_tokens,
                'tiktoken_available': TIKTOKEN_AVAILABLE
            }
        }

    def reset_stats(self):
        """🔄 Сбросить статистику"""
        self.stats = {
            'total_chunks_created': 0,
            'token_based_chunks': 0,
            'character_based_chunks': 0,
            'texts_chunked': 0,
            'texts_not_chunked': 0,
            'avg_chunk_size': 0,
            'max_chunks_in_text': 0,
            'alerts_triggered': 0,
            'aborts_triggered': 0
        }
        print("🔄 Статистика TextChunker сброшена")
