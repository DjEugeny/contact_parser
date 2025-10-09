"""
AttachmentRegistry - Реестр вложений с поддержкой message_id.

Централизованный реестр для точного отслеживания вложений
по message_id вместо thread_id.
"""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Импорты конфигурации
from PIL import Image
import io

# Импорты из существующих модулей
from ...attachment_registry.attachment_registry_spec import (
    AttachmentRegistry as BaseAttachmentRegistry,
)
from ...config.paths import DATA_DIR
from ..utils.date_utils import get_local_time

# Поддерживаемые типы вложений
SUPPORTED_ATTACHMENTS = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".webp": "image/webp",
}

# Исключенные расширения
EXCLUDED_EXTENSIONS = {
    ".zip",
    ".rar",
    ".7z",
    ".pptx",
    ".ppt",
    ".rt",
    ".rtf",
    ".trt",
    ".tr",
    ".r96",
    ".exe",
    ".msi",
    ".dmg",
    ".iso",
    ".img",
}


class AttachmentRegistry(BaseAttachmentRegistry):
    """
    Реестр вложений с корректным маппингом по message_id.
    
    Ключевое отличие от оригинальной логики:
    - Использует message_id для определения принадлежности вложений
    - Обеспечивает точное отслеживание вложений в тредах
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Инициализация реестра вложений.
        
        Args:
            logger: Экземпляр логгера
        """
        super().__init__(logger)
        
        # Директории
        self.data_dir = DATA_DIR
        self.attachments_dir = self.data_dir / "attachments"
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        
        # Специфические исключаемые файлы
        self.specific_excluded_files = {
            "WRD0004.jpg",
            "WRD000.jpg",
            "WRD00.jpg",
            "WRD0.jpg",
            "~WRD0004.jpg",
            "~WRD000.jpg",
            "~WRD00.jpg",
            "~WRD0.jpg",
            "_.jpg",
            "_.png",
            "_.gif",
            "blocked.gif",
            "image001.png",
            "image002.png",
            "image003.png",
            "image004.png",
            "image005.png",
            "image006.png",
            "image007.png",
        }
        
        self.logger.info("📎 AttachmentRegistry инициализирован с message_id маппингом")
    
    def save_attachment(
        self,
        part,
        message_id: str,
        thread_id: str,
        date_folder: str,
        is_inline: bool = False
    ) -> Optional[Dict]:
        """
        Сохранение вложения с привязкой к message_id.
        
        Args:
            part: Часть email с вложением
            message_id: Message-ID письма (КЛЮЧЕВОЕ ИЗМЕНЕНИЕ)
            thread_id: Thread-ID для совместимости
            date_folder: Папка даты
            is_inline: Является ли вложением inline
            
        Returns:
            Информация о сохраненном вложении или None
        """
        try:
            # Извлекаем информацию о файле
            filename = part.get_filename()
            content_type = part.get_content_type()
            
            # Обработка встроенных изображений без имени файла
            if not filename and is_inline and content_type.startswith("image/"):
                extension_map = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                    "image/bmp": ".bmp",
                    "image/tiff": ".tiff",
                    "image/webp": ".webp",
                }
                extension = extension_map.get(content_type, ".img")
                timestamp = get_local_time().strftime("%H%M%S_%f")
                filename = f"inline_image_{timestamp}{extension}"
                self.logger.info(f"🖼️ Встроенное изображение без имени, создаем: {filename}")
            
            if not filename:
                return None
            
            # Декодируем имя файла
            from ..utils.email_utils import decode_header_value
            filename = decode_header_value(filename)
            
            # Проверяем исключения
            exclusion_reason = self._check_exclusions(filename, part, is_inline)
            if exclusion_reason:
                return {
                    "original_filename": filename,
                    "status": "excluded",
                    "exclusion_reason": exclusion_reason,
                    "is_inline": is_inline,
                }
            
            # Создаем безопасное имя файла с message_id
            safe_filename = self._create_safe_filename(
                filename, message_id, thread_id, date_folder, is_inline
            )
            
            # Сохраняем файл
            file_path = self._save_attachment_file(
                part, safe_filename, date_folder
            )
            
            if not file_path:
                return None
            
            # Создаем метаданные
            metadata = AttachmentMetadata(
                message_id=message_id,  # 🔄 КЛЮЧЕВОЕ: message_id вместо thread_id
                thread_id=thread_id,    # Сохраняем для совместимости
                original_filename=filename,
                saved_filename=safe_filename,
                file_path=file_path,
                relative_path=f"attachments/{date_folder}/{safe_filename}",
                content_type=content_type,
                file_size=file_path.stat().st_size if file_path.exists() else 0,
                is_inline=is_inline,
                processed_at=get_local_time().isoformat(),
                status=AttachmentProcessingStatus.SAVED
            )
            
            # Регистрируем в реестре
            self.register_attachment(metadata)
            
            self.logger.info(
                f"✅ Вложение сохранено: {filename} -> {safe_filename}"
                f" (message_id: {message_id[:20]}...)"
            )
            
            return {
                "original_filename": filename,
                "saved_filename": safe_filename,
                "file_path": str(file_path),
                "relative_path": metadata.relative_path,
                "file_size": metadata.file_size,
                "file_type": content_type,
                "content_type": content_type,
                "saved_at": metadata.processed_at,
                "status": "saved",
                "is_inline": is_inline,
                "message_id": message_id,  # 🔄 Добавляем message_id
                "thread_id": thread_id,    # Сохраняем для совместимости
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения вложения: {e}")
            return None
    
    def _check_exclusions(
        self, filename: str, part, is_inline: bool
    ) -> Optional[str]:
        """
        Проверка исключений для вложения.
        
        Args:
            filename: Имя файла
            part: Часть email
            is_inline: Является ли inline
            
        Returns:
            Причина исключения или None
        """
        # Проверка специфических файлов
        if filename in self.specific_excluded_files:
            return f"имя файла в списке исключений"
        
        # Проверка расширения
        file_ext = Path(filename).suffix.lower()
        if file_ext in EXCLUDED_EXTENSIONS:
            return f"расширение {file_ext} исключено"
        
        # Проверка поддержки
        if file_ext not in SUPPORTED_ATTACHMENTS:
            return f"расширение {file_ext} не поддерживается"
        
        # Для inline изображений
        if is_inline:
            content_id = part.get("Content-ID", "").strip("<>")
            if content_id:
                return f"изображение с Content-ID: {content_id}"
            
            # Проверка_entropy и паттернов
            if len(filename) <= 3:
                return f"слишком короткое имя файла: {filename}"
            
            # Проверка на случайные имена
            name_without_ext = filename.rsplit(".", 1)[0] if "." in filename else filename
            if re.match(r"^[a-zA-Z0-9]+$", name_without_ext):
                if len(name_without_ext) <= 6 and name_without_ext not in ["img", "pic", "photo", "image"]:
                    return f"слишком короткое имя файла: {filename}"
                
                # Проверка энтропии
                unique_chars = len(set(name_without_ext.lower()))
                total_chars = len(name_without_ext)
                diversity_ratio = unique_chars / total_chars
                
                if diversity_ratio < 0.6:
                    return f"низкая энтропия символов, вероятно паттерн: {filename}"
                
                if len(name_without_ext) > 8 and diversity_ratio > 0.7:
                    return f"высокая энтропия символов, вероятно случайное имя: {filename}"
                
                if len(name_without_ext) > 12:
                    return f"слишком длинное имя файла: {filename}"
        
        return None
    
    def _create_safe_filename(
        self,
        original_filename: str,
        message_id: str,
        thread_id: str,
        date_folder: str,
        is_inline: bool
    ) -> str:
        """
        Создание безопасного имени файла с message_id.
        
        Args:
            original_filename: Оригинальное имя файла
            message_id: Message-ID письма
            thread_id: Thread-ID
            date_folder: Папка даты
            is_inline: Является ли inline
            
        Returns:
            Безопасное имя файла
        """
        # Создаем короткий хеш from message_id
        import hashlib
        message_hash = hashlib.md5(message_id.encode()).hexdigest()[:8]
        
        # Очищаем имя файла
        safe_filename = re.sub(r"[^\w\s\-\.]", "_", original_filename)
        
        # Создаем временной штамп
        timestamp = get_local_time().strftime("%H%M%S")
        
        # 🔄 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Используем message_hash вместо thread_id
        prefix = "inline" if is_inline else "attach"
        unique_filename = f"{date_folder.replace('-', '')}_{message_hash}_{timestamp}_{prefix}_{safe_filename}"
        
        return unique_filename
    
    def _save_attachment_file(
        self, part, safe_filename: str, date_folder: str
    ) -> Optional[Path]:
        """
        Сохранение файла вложения.
        
        Args:
            part: Часть email с вложением
            safe_filename: Безопасное имя файла
            date_folder: Папка даты
            
        Returns:
            Путь к сохраненному файлу или None
        """
        try:
            # Создаем директорию
            attachments_date_dir = self.attachments_dir / date_folder
            attachments_date_dir.mkdir(exist_ok=True)
            
            # Проверяем существование файла
            file_path = attachments_date_dir / safe_filename
            if file_path.exists():
                self.logger.info(f"📁 Файл уже существует: {safe_filename}")
                return file_path
            
            # Сохраняем файл
            payload = part.get_payload(decode=True)
            if payload:
                with open(file_path, "wb") as f:
                    f.write(payload)
                
                file_size = len(payload)
                self.logger.info(f"✅ Файл сохранен: {safe_filename} ({file_size} байт)")
                return file_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения файла {safe_filename}: {e}")
            return None
    
    def check_email_processing_status(
        self, message_id: str, date_folder: str
    ) -> Dict[str, any]:
        """
        Проверка статуса обработки письма по message_id.
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            
        Returns:
            Словарь со статусом обработки
        """
        status = {
            "json_exists": False,
            "attachments_exist": False,
            "json_file_path": None,
            "attachment_files": [],
        }
        
        try:
            # Проверяем существование JSON-файла письма
            email_path = self.data_dir / "emails" / date_folder
            
            if email_path.exists():
                # Ищем JSON файлы в папке
                json_files = list(email_path.glob("*.json"))
                
                for json_file in json_files:
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            email_data = json.load(f)
                            stored_message_id = email_data.get("message_id", "")
                            
                            if stored_message_id and stored_message_id == message_id:
                                status["json_exists"] = True
                                status["json_file_path"] = str(json_file)
                                
                                # 🔄 КЛЮЧЕВОЕ: Проверяем вложения по message_id
                                attachments = self.get_attachments_by_message_id(message_id)
                                if attachments:
                                    status["attachments_exist"] = True
                                    status["attachment_files"] = [
                                        str(att.file_path) for att in attachments
                                    ]
                                
                                break
                    
                    except Exception as e:
                        self.logger.warning(f"⚠️ Ошибка проверки файла {json_file.name}: {e}")
                        continue
            
            return status
            
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка проверки статуса письма: {e}")
            return status
    
    def get_attachments_by_message_id(self, message_id: str) -> List[Dict]:
        """
        Получение вложений по message_id.
        
        Args:
            message_id: Message-ID письма
            
        Returns:
            Список метаданных вложений
        """
        return super().get_attachments_by_message_id(message_id)
    
    def get_attachments_by_thread_id(self, thread_id: str) -> List[Dict]:
        """
        Получение вложений по thread_id (для обратной совместимости).
        
        Args:
            thread_id: Thread-ID письма
            
        Returns:
            Список метаданных вложений
        """
        return super().get_attachments_by_thread_id(thread_id)
    
    def migrate_thread_id_to_message_id(self, thread_id: str, message_id: str) -> int:
        """
        Миграция вложений от thread_id к message_id.
        
        Args:
            thread_id: Старый thread_id
            message_id: Новый message_id
            
        Returns:
            Количество обновленных вложений
        """
        updated_count = 0
        
        try:
            # Находим вложения с thread_id
            attachments = self.get_attachments_by_thread_id(thread_id)
            
            for attachment in attachments:
                # Обновляем message_id
                attachment.message_id = message_id
                self.register_attachment(attachment)
                updated_count += 1
            
            if updated_count > 0:
                self.logger.info(
                    f"🔄 Мигрировано {updated_count} вложений от thread_id к message_id"
                )
            
            return updated_count
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка миграции вложений: {e}")
            return 0