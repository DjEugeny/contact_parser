#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Спецификация реестра вложений (Attachment Registry)
Централизованная система для отслеживания точных связей между письмами и вложениями
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime
import logging


class AttachmentRegistry:
    """
    Централизованный реестр для отслеживания связей между письмами и вложениями.
    
    Решает проблему некорректного сопоставления вложений, когда система использует
    thread_id вместо message_id для определения принадлежности вложений.
    """
    
    VERSION = "1.0"
    
    def __init__(self, data_dir: Path, logger: Optional[logging.Logger] = None):
        """
        Инициализация реестра вложений
        
        Args:
            data_dir: Базовая директория данных
            logger: Логгер для записи операций
        """
        self.data_dir = data_dir
        self.logger = logger or logging.getLogger(__name__)
        self.registry_file = data_dir / "registry" / "attachment_registry.json"
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.registry = self._load_registry()
        
        # Кэш для ускорения операций
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 минут
    
    def _load_registry(self) -> Dict:
        """Загрузка реестра из файла"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Проверка версии
                if data.get("version") != self.VERSION:
                    self.logger.warning(
                        f"Версия реестра ({data.get('version')}) отличается от текущей ({self.VERSION})"
                    )
                    # В реальном сценарии здесь может быть логика миграции
                
                return data
            else:
                self.logger.info(f"Создание нового реестра: {self.registry_file}")
                return self._create_empty_registry()
                
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Ошибка загрузки реестра вложений: {e}")
            return self._create_empty_registry()
    
    def _create_empty_registry(self) -> Dict:
        """Создание пустого реестра"""
        return {
            "version": self.VERSION,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "attachments": {},
            "statistics": {
                "total_attachments": 0,
                "total_messages": 0,
                "total_size_bytes": 0,
                "last_cleanup": None
            }
        }
    
    def _save_registry(self) -> bool:
        """Сохранение реестра в файл"""
        try:
            self.registry["last_updated"] = datetime.now().isoformat()
            
            # Обновление статистики
            self.registry["statistics"] = self._calculate_statistics()
            
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"Реестр сохранен: {self.registry_file}")
            return True
            
        except IOError as e:
            self.logger.error(f"Ошибка сохранения реестра вложений: {e}")
            return False
    
    def _calculate_statistics(self) -> Dict:
        """Расчет статистики реестра"""
        attachments = self.registry["attachments"]
        total_size = sum(att.get("file_size", 0) for att in attachments.values())
        unique_messages = len(set(att.get("message_id") for att in attachments.values()))
        
        return {
            "total_attachments": len(attachments),
            "total_messages": unique_messages,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "last_cleanup": self.registry.get("statistics", {}).get("last_cleanup")
        }
    
    def _generate_attachment_id(self, message_id: str, filename: str) -> str:
        """Генерация уникального ID вложения"""
        # Используем хэш для создания уникального, но воспроизводимого ID
        hash_input = f"{message_id}_{filename}"
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:16]
    
    def register_attachment(self, message_id: str, attachment_filename: str, 
                           attachment_path: str, thread_id: str = None,
                           file_size: int = None, content_type: str = None,
                           is_inline: bool = False) -> str:
        """
        Регистрация вложения для конкретного письма
        
        Args:
            message_id: Уникальный идентификатор письма
            attachment_filename: Имя сохраненного файла вложения
            attachment_path: Путь к файлу вложения
            thread_id: ID цепочки писем (для группировки)
            file_size: Размер файла в байтах
            content_type: MIME-тип файла
            is_inline: Является ли вложение встроенным изображением
            
        Returns:
            Уникальный ID вложения
        """
        if not message_id:
            raise ValueError("message_id не может быть пустым")
        
        if not attachment_filename:
            raise ValueError("attachment_filename не может быть пустым")
        
        attachment_id = self._generate_attachment_id(message_id, attachment_filename)
        
        # Определение размера файла, если не указан
        if file_size is None:
            try:
                file_path = Path(attachment_path)
                if file_path.exists():
                    file_size = file_path.stat().st_size
            except (OSError, AttributeError):
                file_size = 0
        
        attachment_info = {
            "attachment_id": attachment_id,
            "message_id": message_id,
            "attachment_filename": attachment_filename,
            "attachment_path": attachment_path,
            "thread_id": thread_id,
            "file_size": file_size,
            "content_type": content_type,
            "is_inline": is_inline,
            "registered_at": datetime.now().isoformat()
        }
        
        self.registry["attachments"][attachment_id] = attachment_info
        
        # Инвалидируем кэш
        self._invalidate_cache()
        
        # Сохраняем реестр
        self._save_registry()
        
        self.logger.debug(f"Зарегистрировано вложение: {attachment_id} для письма {message_id}")
        return attachment_id
    
    def get_attachments_by_message(self, message_id: str) -> List[Dict]:
        """
        Получение всех вложений для конкретного письма
        
        Args:
            message_id: Уникальный идентификатор письма
            
        Returns:
            Список информации о вложениях
        """
        if not message_id:
            return []
        
        # Проверяем кэш
        cache_key = f"message_{message_id}"
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]
        
        attachments = [
            att for att in self.registry["attachments"].values()
            if att.get("message_id") == message_id
        ]
        
        # Сохраняем в кэш
        self._cache[cache_key] = attachments
        
        return attachments
    
    def get_attachments_by_thread(self, thread_id: str) -> List[Dict]:
        """
        Получение всех вложений для цепочки писем
        
        Args:
            thread_id: ID цепочки писем
            
        Returns:
            Список информации о вложениях
        """
        if not thread_id:
            return []
        
        attachments = [
            att for att in self.registry["attachments"].values()
            if att.get("thread_id") == thread_id
        ]
        
        return attachments
    
    def get_attachment_info(self, attachment_id: str) -> Optional[Dict]:
        """
        Получение информации о конкретном вложении
        
        Args:
            attachment_id: Уникальный ID вложения
            
        Returns:
            Информация о вложении или None, если не найдено
        """
        return self.registry["attachments"].get(attachment_id)
    
    def find_attachment_file(self, message_id: str, attachment_filename: str) -> Optional[Path]:
        """
        Поиск файла вложения для конкретного письма
        
        Args:
            message_id: Уникальный идентификатор письма
            attachment_filename: Имя файла вложения
            
        Returns:
            Путь к файлу вложения или None, если не найдено
        """
        attachments = self.get_attachments_by_message(message_id)
        
        for attachment in attachments:
            if attachment.get("attachment_filename") == attachment_filename:
                return Path(attachment.get("attachment_path"))
        
        return None
    
    def update_attachment_info(self, attachment_id: str, updates: Dict) -> bool:
        """
        Обновление информации о вложении
        
        Args:
            attachment_id: Уникальный ID вложения
            updates: Словарь с обновляемыми полями
            
        Returns:
            True если успешно, False если вложение не найдено
        """
        if attachment_id not in self.registry["attachments"]:
            return False
        
        # Обновляем поля
        self.registry["attachments"][attachment_id].update(updates)
        self.registry["attachments"][attachment_id]["updated_at"] = datetime.now().isoformat()
        
        # Инвалидируем кэш
        self._invalidate_cache()
        
        # Сохраняем реестр
        return self._save_registry()
    
    def remove_attachment(self, attachment_id: str) -> bool:
        """
        Удаление вложения из реестра
        
        Args:
            attachment_id: Уникальный ID вложения
            
        Returns:
            True если успешно, False если вложение не найдено
        """
        if attachment_id not in self.registry["attachments"]:
            return False
        
        attachment_info = self.registry["attachments"][attachment_id]
        
        # Удаляем файл, если он существует
        try:
            attachment_path = Path(attachment_info.get("attachment_path"))
            if attachment_path.exists():
                attachment_path.unlink()
                self.logger.info(f"Удален файл вложения: {attachment_path}")
        except (OSError, AttributeError) as e:
            self.logger.warning(f"Ошибка удаления файла {attachment_path}: {e}")
        
        # Удаляем из реестра
        del self.registry["attachments"][attachment_id]
        
        # Инвалидируем кэш
        self._invalidate_cache()
        
        # Сохраняем реестр
        return self._save_registry()
    
    def cleanup_orphaned_attachments(self) -> Dict[str, int]:
        """
        Очистка реестра от несуществующих файлов
        
        Returns:
            Статистика очистки
        """
        orphaned_count = 0
        total_size_freed = 0
        
        orphaned_ids = []
        
        for attachment_id, attachment_info in self.registry["attachments"].items():
            attachment_path = Path(attachment_info.get("attachment_path"))
            
            if not attachment_path.exists():
                orphaned_ids.append(attachment_id)
                file_size = attachment_info.get("file_size", 0)
                total_size_freed += file_size
        
        # Удаляем несуществующие вложения
        for attachment_id in orphaned_ids:
            del self.registry["attachments"][attachment_id]
            orphaned_count += 1
        
        # Обновляем статистику
        self.registry["statistics"]["last_cleanup"] = datetime.now().isoformat()
        
        # Инвалидируем кэш
        self._invalidate_cache()
        
        # Сохраняем реестр
        self._save_registry()
        
        self.logger.info(f"Очистка завершена: удалено {orphaned_count} вложений, освобождено {total_size_freed} байт")
        
        return {
            "orphaned_count": orphaned_count,
            "total_size_freed": total_size_freed,
            "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2)
        }
    
    def get_statistics(self) -> Dict:
        """Получение статистики реестра"""
        return self.calculate_statistics()
    
    def _is_cache_valid(self) -> bool:
        """Проверка актуальности кэша"""
        if not self._cache_timestamp:
            return False
        
        import time
        return (time.time() - self._cache_timestamp) < self._cache_ttl
    
    def _invalidate_cache(self):
        """Инвалидация кэша"""
        self._cache = {}
        self._cache_timestamp = None
    
    def get_messages_with_attachments(self) -> List[str]:
        """
        Получение списка всех message_id, у которых есть вложения
        
        Returns:
            Список message_id
        """
        message_ids = set()
        
        for attachment_info in self.registry["attachments"].values():
            message_id = attachment_info.get("message_id")
            if message_id:
                message_ids.add(message_id)
        
        return list(message_ids)
    
    def export_to_csv(self, output_path: Path) -> bool:
        """
        Экспорт реестра в CSV формат
        
        Args:
            output_path: Путь для сохранения CSV файла
            
        Returns:
            True если успешно
        """
        try:
            import csv
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'attachment_id', 'message_id', 'thread_id', 'attachment_filename',
                    'attachment_path', 'file_size', 'content_type', 'is_inline',
                    'registered_at'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for attachment_info in self.registry["attachments"].values():
                    row = {field: attachment_info.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            
            self.logger.info(f"Реестр экспортирован в CSV: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта в CSV: {e}")
            return False


def create_sample_registry():
    """Создание тестового реестра для демонстрации"""
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        registry = AttachmentRegistry(data_dir)
        
        # Регистрируем тестовые вложения
        registry.register_attachment(
            message_id="test-message-1",
            attachment_filename="document.pdf",
            attachment_path=str(data_dir / "attachments" / "document.pdf"),
            thread_id="test-thread-1",
            file_size=1024000,
            content_type="application/pdf",
            is_inline=False
        )
        
        registry.register_attachment(
            message_id="test-message-2",
            attachment_filename="image.png",
            attachment_path=str(data_dir / "attachments" / "image.png"),
            thread_id="test-thread-1",
            file_size=256000,
            content_type="image/png",
            is_inline=True
        )
        
        # Выводим статистику
        print("Статистика реестра:")
        print(json.dumps(registry.get_statistics(), indent=2, ensure_ascii=False))
        
        # Получаем вложения для сообщения
        attachments = registry.get_attachments_by_message("test-message-1")
        print(f"\nВложения для test-message-1: {len(attachments)}")
        for att in attachments:
            print(f"  - {att['attachment_filename']} ({att['file_size']} байт)")


if __name__ == "__main__":
    create_sample_registry()