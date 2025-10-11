#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔌 Адаптер для интеграции PreCleaner в Email Fetcher.

Обеспечивает ленивую загрузку ядра предочистки, работу с YAML-конфигурацией
и сбор статистики по эффективности очистки.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .precleaner_core import PrecleanResult, preclean_email_for_llm


@dataclass
class PreCleanStats:
    """📊 Статистика работы PreCleaner"""
    original_length: int = 0
    cleaned_length: int = 0
    removed_signatures: int = 0
    removed_quotes: int = 0
    removed_disclaimers: int = 0
    tokens_saved: int = 0
    processing_time: float = 0.0
    thread_id: str = ""
    sender_email: str = ""
    timestamp: str = ""
    
    @property
    def reduction_percentage(self) -> float:
        """📈 Процент сокращения текста"""
        if self.original_length == 0:
            return 0.0
        return (self.original_length - self.cleaned_length) / self.original_length * 100
    
    @property
    def tokens_saved_estimate(self) -> int:
        """🪙 Оценка сэкономленных токенов (1 токен ~ 4 символа)"""
        return (self.original_length - self.cleaned_length) // 4


class ThreadCache:
    """🧵 Кэш паттернов для тредов"""

    def __init__(self):
        self.cache: Dict[str, Dict[str, int]] = {}
        self.logger = logging.getLogger(f"{__name__}.ThreadCache")

    def get_pattern_count(self, thread_id: str, pattern_hash: str) -> int:
        """Получить счетчик паттерна для треда"""
        return self.cache.get(thread_id, {}).get(pattern_hash, 0)

    def increment_pattern(self, thread_id: str, pattern_hash: str):
        """Увеличить счетчик паттерна для треда"""
        if thread_id not in self.cache:
            self.cache[thread_id] = {}
        self.cache[thread_id][pattern_hash] = self.cache[thread_id].get(pattern_hash, 0) + 1

        self.logger.debug(f"🧵 Thread {thread_id}: pattern {pattern_hash} count = {self.cache[thread_id][pattern_hash]}")

    def get_bucket(self, thread_id: str) -> Dict[str, int]:
        """📦 Возвращает (и создаёт при необходимости) кэш для треда."""
        if thread_id not in self.cache:
            self.cache[thread_id] = {}
        return self.cache[thread_id]

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        total_threads = len(self.cache)
        total_patterns = sum(len(patterns) for patterns in self.cache.values())
        total_entries = sum(sum(counts.values()) for counts in self.cache.values())
        
        return {
            "total_threads": total_threads,
            "total_patterns": total_patterns,
            "total_entries": total_entries,
            "cache_size": len(json.dumps(self.cache, ensure_ascii=False)),
        }


class SenderCache:
    """📧 Кэш паттернов для отправителей"""

    def __init__(self):
        self.cache: Dict[str, Dict[str, int]] = {}
        self.logger = logging.getLogger(f"{__name__}.SenderCache")

    def get_pattern_count(self, sender_email: str, pattern_hash: str) -> int:
        """Получить счетчик паттерна для отправителя"""
        return self.cache.get(sender_email, {}).get(pattern_hash, 0)

    def increment_pattern(self, sender_email: str, pattern_hash: str):
        """Увеличить счетчик паттерна для отправителя"""
        if sender_email not in self.cache:
            self.cache[sender_email] = {}
        self.cache[sender_email][pattern_hash] = self.cache[sender_email].get(pattern_hash, 0) + 1

        self.logger.debug(f"📧 Sender {sender_email}: pattern {pattern_hash} count = {self.cache[sender_email][pattern_hash]}")

    def get_bucket(self, sender_email: str) -> Dict[str, int]:
        """📥 Возвращает (и создаёт при необходимости) кэш для отправителя."""
        if sender_email not in self.cache:
            self.cache[sender_email] = {}
        return self.cache[sender_email]

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        total_senders = len(self.cache)
        total_patterns = sum(len(patterns) for patterns in self.cache.values())
        total_entries = sum(sum(counts.values()) for counts in self.cache.values())
        
        return {
            "total_senders": total_senders,
            "total_patterns": total_patterns,
            "total_entries": total_entries,
            "cache_size": len(json.dumps(self.cache, ensure_ascii=False)),
        }

class CacheBridge:
    """🧷 Прослойка между адаптером и ядром предочистки."""

    def __init__(self, thread_cache: ThreadCache, sender_cache: SenderCache):
        self._thread_cache = thread_cache
        self._sender_cache = sender_cache

    def get_thread_cache(self, thread_id: str) -> Dict[str, int]:
        """📂 Возвращает кэш паттернов для треда."""
        return self._thread_cache.get_bucket(thread_id)

    def get_sender_cache(self, sender_email: str) -> Dict[str, int]:
        """📨 Возвращает кэш паттернов для отправителя."""
        return self._sender_cache.get_bucket(sender_email.lower())


class PreCleanerAdapter:
    """🔌 Адаптер для интеграции PreCleaner в Email Fetcher"""

    def __init__(self, logger: Optional[logging.Logger] = None, config_path: Optional[str] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.config_path = Path(config_path) if config_path else None
        self.config = self._load_config(self.config_path)

        # Инициализируем кэши
        self.thread_cache = ThreadCache()
        self.sender_cache = SenderCache()
        self.cache_bridge = CacheBridge(self.thread_cache, self.sender_cache)

        # Статистика
        self.stats: List[PreCleanStats] = []
        self.total_processed = 0
        self.total_tokens_saved = 0
        
        # Пути для сохранения статистики
        self.data_dir = Path("data")
        self.stats_dir = self.data_dir / "logs" / "precleaner"
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("🔌 PreCleanerAdapter инициализирован")
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """📋 Загружает YAML-конфигурацию PreCleaner."""
        default_config = {
            "max_signature_lines": 5,
            "fold_quote_over_chars": 1200,
            "fold_on_repeat": True,
            "keep_first_signature_per_sender": True,
            "keep_first_disclaimer_per_thread": True,
            "languages": ["ru", "en"],
            "sig_markers": ["--", "—", "с уважением", "best regards", "kind regards"],
            "disclaimer_markers": [
                "confidentiality notice", 
                "настоящее сообщение", 
                "this message may contain confidential",
                "unsubscribe", 
                "privacy policy"
            ],
        }

        if config_path and config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as handler:
                    loaded = yaml.safe_load(handler) or {}

                if not isinstance(loaded, dict):
                    raise ValueError("Некорректный формат YAML: ожидается словарь")

                user_section = loaded.get("precleaner", loaded)
                if not isinstance(user_section, dict):
                    raise ValueError("Секция precleaner в YAML должна быть словарём")

                default_config.update(user_section)
                self.logger.info(f"📋 Конфигурация PreCleaner загружена из {config_path}")
            except Exception as e:
                self.logger.warning(
                    "⚠️ Ошибка загрузки YAML-конфигурации PreCleaner: %s. Используем значения по умолчанию.",
                    e,
                )

        return default_config

    def preclean_text(self, text: str, thread_id: str, sender_email: str) -> 'PreCleanResult':
        """
        🔧 Основной метод пред-очистки текста
        
        Args:
            text: Исходный текст письма
            thread_id: ID треда
            sender_email: Email отправителя
            
        Returns:
            PreCleanResult с очищенным текстом и статистикой
        """
        start_time = time.time()
        
        # Создаем статистику для этой операции
        stats = PreCleanStats(
            original_length=len(text),
            thread_id=thread_id,
            sender_email=sender_email,
            timestamp=datetime.now().isoformat()
        )
        
        self.logger.debug(f"🔧 Начинаем пред-очистку текста ({stats.original_length} символов)")
        
        try:
            result: PrecleanResult = preclean_email_for_llm(
                raw_text=text,
                thread_id=thread_id,
                sender_email=sender_email,
                config=self.config,
                caches=self.cache_bridge,
            )
            
            # Обновляем статистику
            stats.cleaned_length = len(result.body_clean_llm)
            stats.processing_time = time.time() - start_time
            
            # Анализируем удаленные блоки
            if result.clean_spans and "spans" in result.clean_spans:
                for span in result.clean_spans["spans"]:
                    kind = span.get("kind", "unknown")
                    if kind == "signature":
                        stats.removed_signatures += 1
                    elif kind == "quote":
                        stats.removed_quotes += 1
                    elif kind == "disclaimer":
                        stats.removed_disclaimers += 1
            
            stats.tokens_saved = stats.tokens_saved_estimate
            
            # Обновляем общую статистику
            self.stats.append(stats)
            self.total_processed += 1
            self.total_tokens_saved += stats.tokens_saved
            
            self.logger.info(
                "✅ Пред-очистка завершена: %d → %d символов (%.1f%%, примерно -%d токенов)",
                stats.original_length,
                stats.cleaned_length,
                stats.reduction_percentage,
                stats.tokens_saved,
            )
            
            return result
            
        except ImportError as e:
            self.logger.error(f"❌ Не удалось импортировать PreCleaner: {e}")
            # Fallback - возвращаем оригинальный текст
            from types import SimpleNamespace
            
            fallback_result = SimpleNamespace(
                body_clean_llm=text,
                body_raw=text,
                clean_spans={"spans": []},
                attachments_index=[]
            )
            
            stats.cleaned_length = len(text)
            stats.processing_time = time.time() - start_time

            return fallback_result
        
        except Exception as e:
            self.logger.error(f"❌ Ошибка пред-очистки: {e}")
            # Fallback - возвращаем оригинальный текст
            from types import SimpleNamespace
            
            fallback_result = SimpleNamespace(
                body_clean_llm=text,
                body_raw=text,
                clean_spans={"spans": []},
                attachments_index=[]
            )
            
            stats.cleaned_length = len(text)
            stats.processing_time = time.time() - start_time

            return fallback_result

    def get_processing_stats(self) -> Dict[str, Any]:
        """📊 Получить общую статистику обработки"""
        if not self.stats:
            return {
                "total_processed": 0,
                "total_tokens_saved": 0,
                "average_reduction": 0.0,
                "cache_stats": {
                    "thread": self.thread_cache.get_stats(),
                    "sender": self.sender_cache.get_stats()
                }
            }
        
        total_original = sum(s.original_length for s in self.stats)
        total_cleaned = sum(s.cleaned_length for s in self.stats)
        average_reduction = (total_original - total_cleaned) / total_original * 100 if total_original > 0 else 0
        
        return {
            "total_processed": self.total_processed,
            "total_tokens_saved": self.total_tokens_saved,
            "average_reduction": average_reduction,
            "total_signatures_removed": sum(s.removed_signatures for s in self.stats),
            "total_quotes_removed": sum(s.removed_quotes for s in self.stats),
            "total_disclaimers_removed": sum(s.removed_disclaimers for s in self.stats),
            "average_processing_time": sum(s.processing_time for s in self.stats) / len(self.stats),
            "cache_stats": {
                "thread": self.thread_cache.get_stats(),
                "sender": self.sender_cache.get_stats()
            }
        }
    
    def save_stats(self, prefix: str = "precleaner_stats") -> str:
        """💾 Сохранить статистику в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.json"
        filepath = self.stats_dir / filename
        
        stats_data = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config,
            "processing_stats": self.get_processing_stats(),
            "detailed_stats": [
                {
                    "original_length": s.original_length,
                    "cleaned_length": s.cleaned_length,
                    "reduction_percentage": s.reduction_percentage,
                    "tokens_saved": s.tokens_saved,
                    "processing_time": s.processing_time,
                    "thread_id": s.thread_id,
                    "sender_email": s.sender_email,
                    "removed_signatures": s.removed_signatures,
                    "removed_quotes": s.removed_quotes,
                    "removed_disclaimers": s.removed_disclaimers,
                    "timestamp": s.timestamp
                }
                for s in self.stats[-100:]  # Последние 100 записей
            ]
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"📊 Статистика сохранена: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения статистики: {e}")
            return ""
    
    def reset_stats(self):
        """🔄 Сбросить статистику"""
        self.stats.clear()
        self.total_processed = 0
        self.total_tokens_saved = 0
        self.thread_cache.cache.clear()
        self.sender_cache.cache.clear()
        
        self.logger.info("🔄 Статистика и кэши сброшены")
    
    def print_summary(self):
        """📋 Вывести сводную статистику"""
        stats = self.get_processing_stats()
        
        print("\n" + "="*60)
        print("🧼 PRECLEANER СТАТИСТИКА")
        print("="*60)
        print(f"📧 Обработано писем: {stats['total_processed']:,}")
        print(f"🪙 Сэкономлено токенов: {stats['total_tokens_saved']:,}")
        print(f"📉 Среднее сокращение: {stats['average_reduction']:.1f}%")
        print(f"✂️ Удалено подписей: {stats['total_signatures_removed']:,}")
        print(f"💬 Удалено цитат: {stats['total_quotes_removed']:,}")
        print(f"📄 Удалено дисклеймеров: {stats['total_disclaimers_removed']:,}")
        print(f"⏱️ Среднее время обработки: {stats['average_processing_time']:.3f} сек")
        
        print(f"\n🧵 Статистика кэша тредов:")
        thread_stats = stats['cache_stats']['thread']
        print(f"   Тредов: {thread_stats['total_threads']:,}")
        print(f"   Паттернов: {thread_stats['total_patterns']:,}")
        print(f"   Записей: {thread_stats['total_entries']:,}")
        
        print(f"\n📧 Статистика кэша отправителей:")
        sender_stats = stats['cache_stats']['sender']
        print(f"   Отправителей: {sender_stats['total_senders']:,}")
        print(f"   Паттернов: {sender_stats['total_patterns']:,}")
        print(f"   Записей: {sender_stats['total_entries']:,}")
        
        print("="*60)
