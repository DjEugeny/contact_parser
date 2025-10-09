#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Адаптер для File Tokens, обеспечивающий совместимость с новым реестром вложений
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Импортируем реестр вложений
from ..attachment_registry.attachment_registry_spec import AttachmentRegistry


class FileTokensAdapter:
    """
    Адаптер для File Tokens с поддержкой реестра вложений.
    
    Обеспечивает корректный расчет статистики токенов на основе точных связей
    между письмами и вложениями.
    """
    
    def __init__(self, data_dir: Path, logger: Optional[logging.Logger] = None):
        """
        Инициализация адаптера
        
        Args:
            data_dir: Базовая директория данных
            logger: Логгер для записи операций
        """
        self.data_dir = data_dir
        self.logger = logger or logging.getLogger(__name__)
        self.attachment_registry = AttachmentRegistry(data_dir, logger)
        
        # Директории для данных
        self.emails_dir = data_dir / "emails"
        self.attachments_dir = data_dir / "attachments"
        self.tokens_dir = data_dir / "file_tokens"
        self.tokens_dir.mkdir(parents=True, exist_ok=True)
    
    def get_attachment_relationships(self, message_id: str) -> List[Dict]:
        """
        Получение точных связей между письмом и вложениями
        
        Args:
            message_id: Уникальный идентификатор письма
            
        Returns:
            Список информации о вложениях для письма
        """
        if not message_id:
            self.logger.warning("message_id не указан")
            return []
        
        attachments = self.attachment_registry.get_attachments_by_message(message_id)
        
        # Обогащаем информацию о вложениях дополнительными данными
        enriched_attachments = []
        
        for attachment in attachments:
            attachment_path = Path(attachment.get("attachment_path"))
            
            # Получаем информацию о токенах
            tokens_info = self._get_file_tokens_info(attachment_path)
            
            # Получаем информацию о файле
            file_info = self._get_file_info(attachment_path)
            
            enriched_attachment = {
                **attachment,
                "tokens_info": tokens_info,
                "file_info": file_info
            }
            
            enriched_attachments.append(enriched_attachment)
        
        return enriched_attachments
    
    def get_attachment_stats(self, message_id: str) -> Dict:
        """
        Получение статистики по вложениям для письма
        
        Args:
            message_id: Уникальный идентификатор письма
            
        Returns:
            Статистика по вложениям
        """
        attachments = self.get_attachment_relationships(message_id)
        
        if not attachments:
            return {
                "total": 0,
                "inline": 0,
                "regular": 0,
                "total_size": 0,
                "total_tokens": 0,
                "by_type": {}
            }
        
        stats = {
            "total": len(attachments),
            "inline": len([a for a in attachments if a.get("is_inline", False)]),
            "regular": len([a for a in attachments if not a.get("is_inline", False)]),
            "total_size": sum(a.get("file_size", 0) for a in attachments),
            "total_tokens": sum(a.get("tokens_info", {}).get("total_tokens", 0) for a in attachments),
            "by_type": {}
        }
        
        # Группировка по типам файлов
        for attachment in attachments:
            content_type = attachment.get("content_type", "unknown")
            file_size = attachment.get("file_size", 0)
            tokens_count = attachment.get("tokens_info", {}).get("total_tokens", 0)
            
            if content_type not in stats["by_type"]:
                stats["by_type"][content_type] = {
                    "count": 0,
                    "total_size": 0,
                    "total_tokens": 0
                }
            
            stats["by_type"][content_type]["count"] += 1
            stats["by_type"][content_type]["total_size"] += file_size
            stats["by_type"][content_type]["total_tokens"] += tokens_count
        
        # Округляем значения
        stats["total_size_mb"] = round(stats["total_size"] / (1024 * 1024), 2)
        stats["average_tokens_per_attachment"] = round(stats["total_tokens"] / stats["total"], 2) if stats["total"] > 0 else 0
        
        for type_stats in stats["by_type"].values():
            type_stats["total_size_mb"] = round(type_stats["total_size"] / (1024 * 1024), 2)
            type_stats["average_tokens"] = round(type_stats["total_tokens"] / type_stats["count"], 2) if type_stats["count"] > 0 else 0
        
        return stats
    
    def _get_file_tokens_info(self, file_path: Path) -> Dict:
        """
        Получение информации о токенах для файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Информация о токенах
        """
        # Проверяем кэш токенов
        cache_key = str(file_path)
        cached_tokens = self._load_tokens_from_cache(cache_key)
        
        if cached_tokens:
            return cached_tokens
        
        tokens_info = {
            "total_tokens": 0,
            "characters": 0,
            "words": 0,
            "lines": 0,
            "pages": 0,
            "tokens_by_type": {},
            "last_analyzed": None
        }
        
        try:
            if not file_path.exists():
                return tokens_info
            
            # Определяем тип файла и анализируем соответствующим образом
            content_type = self._detect_content_type(file_path)
            
            if content_type == "application/pdf":
                tokens_info = self._analyze_pdf_tokens(file_path)
            elif content_type.startswith("image/"):
                tokens_info = self._analyze_image_tokens(file_path)
            elif content_type.startswith("text/"):
                tokens_info = self._analyze_text_tokens(file_path)
            elif content_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                tokens_info = self._analyze_document_tokens(file_path)
            else:
                # Для неизвестных типов файлов
                tokens_info = {
                    "total_tokens": file_path.stat().st_size // 4,  # Приблизительная оценка
                    "characters": file_path.stat().st_size,
                    "last_analyzed": datetime.now().isoformat()
                }
            
            # Сохраняем в кэш
            self._save_tokens_to_cache(cache_key, tokens_info)
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа токенов для файла {file_path}: {e}")
        
        return tokens_info
    
    def _detect_content_type(self, file_path: Path) -> str:
        """
        Определение типа контента файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            MIME-тип файла
        """
        import mimetypes
        
        content_type, _ = mimetypes.guess_type(str(file_path))
        
        if content_type:
            return content_type
        
        # Определение по расширению
        ext = file_path.suffix.lower()
        
        if ext == ".pdf":
            return "application/pdf"
        elif ext in [".doc", ".docx"]:
            return "application/msword"
        elif ext in [".xls", ".xlsx"]:
            return "application/vnd.ms-excel"
        elif ext in [".txt", ".text"]:
            return "text/plain"
        elif ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
            return f"image/{ext[1:]}"
        
        return "application/octet-stream"
    
    def _analyze_pdf_tokens(self, file_path: Path) -> Dict:
        """Анализ токенов для PDF файла"""
        # Упрощенная реализация - в реальном сценарии здесь может быть
        # использование библиотеки pypdf2 или similar
        
        file_size = file_path.stat().st_size
        
        # Приблизительная оценка на основе размера файла
        estimated_chars = file_size // 2  # Приблизительно 2 байта на символ
        estimated_words = estimated_chars // 5  # Приблизительно 5 символов на слово
        estimated_tokens = estimated_words  # Приблизительно 1 токен на слово
        
        return {
            "total_tokens": estimated_tokens,
            "characters": estimated_chars,
            "words": estimated_words,
            "lines": estimated_words // 10,  # Приблизительно 10 слов на строку
            "pages": max(1, estimated_tokens // 300),  # Приблизительно 300 токенов на страницу
            "tokens_by_type": {
                "text": estimated_tokens,
                "formatting": estimated_tokens // 10
            },
            "last_analyzed": datetime.now().isoformat()
        }
    
    def _analyze_image_tokens(self, file_path: Path) -> Dict:
        """Анализ токенов для изображения"""
        # Для изображений токены обычно генерируются через OCR
        
        return {
            "total_tokens": 0,  # Будет заполнено после OCR
            "characters": 0,
            "words": 0,
            "lines": 0,
            "pages": 1,
            "tokens_by_type": {
                "image": 1,
                "text": 0  # Будет заполнено после OCR
            },
            "last_analyzed": datetime.now().isoformat(),
            "requires_ocr": True
        }
    
    def _analyze_text_tokens(self, file_path: Path) -> Dict:
        """Анализ токенов для текстового файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Пробуем другие кодировки
            try:
                with open(file_path, 'r', encoding='cp1252') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        characters = len(content)
        words = len(content.split())
        lines = content.count('\n') + 1
        
        # Приблизительная оценка токенов
        tokens = words  # Упрощенная оценка
        
        return {
            "total_tokens": tokens,
            "characters": characters,
            "words": words,
            "lines": lines,
            "pages": max(1, lines // 50),  # Приблизительно 50 строк на страницу
            "tokens_by_type": {
                "text": tokens,
                "whitespace": content.count(' ') + content.count('\n'),
                "punctuation": sum(1 for c in content if not c.isalnum() and not c.isspace())
            },
            "last_analyzed": datetime.now().isoformat()
        }
    
    def _analyze_document_tokens(self, file_path: Path) -> Dict:
        """Анализ токенов для документа Word"""
        # Упрощенная реализация - в реальном сценарии здесь может быть
        # использование библиотеки python-docx или similar
        
        file_size = file_path.stat().st_size
        
        # Приблизительная оценка на основе размера файла
        estimated_chars = file_size // 2
        estimated_words = estimated_chars // 5
        estimated_tokens = estimated_words
        
        return {
            "total_tokens": estimated_tokens,
            "characters": estimated_chars,
            "words": estimated_words,
            "lines": estimated_words // 8,
            "pages": max(1, estimated_tokens // 250),
            "tokens_by_type": {
                "text": estimated_tokens,
                "formatting": estimated_tokens // 8,
                "metadata": estimated_tokens // 20
            },
            "last_analyzed": datetime.now().isoformat()
        }
    
    def _get_file_info(self, file_path: Path) -> Dict:
        """
        Получение информации о файле
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Информация о файле
        """
        try:
            if not file_path.exists():
                return {
                    "exists": False,
                    "size": 0,
                    "created": None,
                    "modified": None,
                    "extension": file_path.suffix,
                    "name": file_path.name
                }
            
            stat = file_path.stat()
            
            return {
                "exists": True,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": file_path.suffix,
                "name": file_path.name,
                "stem": file_path.stem,
                "content_type": self._detect_content_type(file_path)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о файле {file_path}: {e}")
            return {
                "exists": False,
                "error": str(e)
            }
    
    def _load_tokens_from_cache(self, cache_key: str) -> Optional[Dict]:
        """
        Загрузка токенов из кэша
        
        Args:
            cache_key: Ключ кэша
            
        Returns:
            Информация о токенах или None
        """
        try:
            cache_file = self.tokens_dir / f"{hash(cache_key)}.json"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Проверяем актуальность кэша
            cache_time = datetime.fromisoformat(cache_data.get("cached_at", ""))
            file_path = Path(cache_key)
            
            if file_path.exists():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                # Если файл новее кэша, игнорируем кэш
                if file_time > cache_time:
                    return None
            
            return cache_data.get("tokens_info")
            
        except Exception as e:
            self.logger.warning(f"Ошибка загрузки токенов из кэша: {e}")
            return None
    
    def _save_tokens_to_cache(self, cache_key: str, tokens_info: Dict):
        """
        Сохранение токенов в кэш
        
        Args:
            cache_key: Ключ кэша
            tokens_info: Информация о токенах
        """
        try:
            cache_data = {
                "cache_key": cache_key,
                "cached_at": datetime.now().isoformat(),
                "tokens_info": tokens_info
            }
            
            cache_file = self.tokens_dir / f"{hash(cache_key)}.json"
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Ошибка сохранения токенов в кэш: {e}")
    
    def get_global_tokens_statistics(self) -> Dict:
        """
        Получение глобальной статистики токенов
        
        Returns:
            Глобальная статистика токенов
        """
        stats = {
            "total_messages": 0,
            "total_attachments": 0,
            "total_tokens": 0,
            "total_size_mb": 0,
            "average_tokens_per_message": 0,
            "average_tokens_per_attachment": 0,
            "by_date": {},
            "by_content_type": {},
            "top_messages_by_tokens": []
        }
        
        # Получаем все сообщения с вложениями
        messages_with_attachments = self.attachment_registry.get_messages_with_attachments()
        
        # Статистика по сообщениям
        message_tokens = []
        
        for message_id in messages_with_attachments:
            message_stats = self.get_attachment_stats(message_id)
            
            stats["total_messages"] += 1
            stats["total_attachments"] += message_stats["total"]
            stats["total_tokens"] += message_stats["total_tokens"]
            stats["total_size_mb"] += message_stats.get("total_size_mb", 0)
            
            # Сохраняем для сортировки
            message_tokens.append({
                "message_id": message_id,
                "total_tokens": message_stats["total_tokens"],
                "total_attachments": message_stats["total"]
            })
            
            # Статистика по типам контента
            for content_type, type_stats in message_stats.get("by_type", {}).items():
                if content_type not in stats["by_content_type"]:
                    stats["by_content_type"][content_type] = {
                        "count": 0,
                        "total_tokens": 0,
                        "total_size_mb": 0
                    }
                
                stats["by_content_type"][content_type]["count"] += type_stats["count"]
                stats["by_content_type"][content_type]["total_tokens"] += type_stats["total_tokens"]
                stats["by_content_type"][content_type]["total_size_mb"] += type_stats.get("total_size_mb", 0)
        
        # Вычисляем средние значения
        if stats["total_messages"] > 0:
            stats["average_tokens_per_message"] = round(stats["total_tokens"] / stats["total_messages"], 2)
        
        if stats["total_attachments"] > 0:
            stats["average_tokens_per_attachment"] = round(stats["total_tokens"] / stats["total_attachments"], 2)
        
        # Топ сообщений по количеству токенов
        stats["top_messages_by_tokens"] = sorted(
            message_tokens, 
            key=lambda x: x["total_tokens"], 
            reverse=True
        )[:10]  # Топ-10
        
        # Округляем значения
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        
        for content_type_stats in stats["by_content_type"].values():
            content_type_stats["total_size_mb"] = round(content_type_stats["total_size_mb"], 2)
            content_type_stats["average_tokens"] = round(
                content_type_stats["total_tokens"] / content_type_stats["count"], 2
            ) if content_type_stats["count"] > 0 else 0
        
        return stats
    
    def cleanup_orphaned_cache(self) -> Dict[str, int]:
        """
        Очистка кэша от несуществующих файлов
        
        Returns:
            Статистика очистки
        """
        cleaned_count = 0
        total_size_freed = 0
        
        for cache_file in self.tokens_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cache_key = cache_data.get("cache_key")
                if not cache_key:
                    continue
                
                file_path = Path(cache_key)
                
                # Проверяем существует ли файл
                if not file_path.exists():
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    cleaned_count += 1
                    total_size_freed += file_size
                    
                    self.logger.debug(f"Удален кэш для несуществующего файла: {cache_file}")
                
            except Exception as e:
                self.logger.warning(f"Ошибка обработки кэша {cache_file}: {e}")
                continue
        
        self.logger.info(f"Очистка кэша токенов: удалено {cleaned_count} файлов, освобождено {total_size_freed} байт")
        
        return {
            "cleaned_count": cleaned_count,
            "total_size_freed": total_size_freed,
            "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2)
        }


def test_file_tokens_adapter():
    """Тестирование адаптера File Tokens"""
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        
        # Создаем тестовую структуру
        (data_dir / "attachments" / "2025-07-23").mkdir(parents=True)
        
        # Создаем тестовое вложение
        test_attachment = data_dir / "attachments" / "2025-07-23" / "test_document.pdf"
        test_attachment.write_bytes(b"test pdf content with some text")
        
        # Инициализируем адаптер
        adapter = FileTokensAdapter(data_dir)
        
        # Регистрируем вложение
        attachment_id = adapter.attachment_registry.register_attachment(
            message_id="test-message-123",
            attachment_filename="test_document.pdf",
            attachment_path=str(test_attachment),
            thread_id="test-thread-456",
            file_size=len(b"test pdf content with some text"),
            content_type="application/pdf"
        )
        
        # Тестируем получение связей
        relationships = adapter.get_attachment_relationships("test-message-123")
        print(f"Связи вложений: {len(relationships)}")
        
        # Тестируем статистику
        stats = adapter.get_attachment_stats("test-message-123")
        print(f"Статистика вложений: {json.dumps(stats, indent=2)}")
        
        # Тестируем глобальную статистику
        global_stats = adapter.get_global_tokens_statistics()
        print(f"Глобальная статистика: {json.dumps(global_stats, indent=2)}")


if __name__ == "__main__":
    test_file_tokens_adapter()