#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт миграции существующих данных в новую систему реестра вложений
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Импортируем реестр вложений
from ..attachment_registry.attachment_registry_spec import AttachmentRegistry


class AttachmentMigration:
    """
    Класс для миграции существующих данных в новую систему реестра вложений.
    
    Позволяет перенести информацию о вложениях из существующих JSON файлов
    писем в централизованный реестр.
    """
    
    def __init__(self, data_dir: Path, logger: Optional[logging.Logger] = None):
        """
        Инициализация миграции
        
        Args:
            data_dir: Базовая директория данных
            logger: Логгер для записи операций
        """
        self.data_dir = data_dir
        self.logger = logger or logging.getLogger(__name__)
        
        # Директории
        self.emails_dir = data_dir / "emails"
        self.attachments_dir = data_dir / "attachments"
        self.migration_log_dir = data_dir / "migration_logs"
        self.migration_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Инициализируем реестр
        self.attachment_registry = AttachmentRegistry(data_dir, logger)
        
        # Статистика миграции
        self.migration_stats = {
            "total_emails_processed": 0,
            "total_attachments_migrated": 0,
            "attachments_with_errors": 0,
            "orphaned_attachments_found": 0,
            "migration_start_time": None,
            "migration_end_time": None
        }
    
    def migrate_all_data(self, dry_run: bool = False) -> Dict:
        """
        Полная миграция всех данных
        
        Args:
            dry_run: Если True, только анализирует без изменений
            
        Returns:
            Статистика миграции
        """
        self.migration_stats["migration_start_time"] = datetime.now().isoformat()
        
        self.logger.info("Начало миграции данных в реестр вложений")
        if dry_run:
            self.logger.info("режим DRY RUN - изменения не будут применены")
        
        try:
            # Шаг 1: Миграция вложений из JSON файлов писем
            self._migrate_attachments_from_emails(dry_run)
            
            # Шаг 2: Поиск и регистрация осиротевших вложений
            self._register_orphaned_attachments(dry_run)
            
            # Шаг 3: Очистка реестра от несуществующих файлов
            if not dry_run:
                self.attachment_registry.cleanup_orphaned_attachments()
            
            # Шаг 4: Сохранение логов миграции
            self._save_migration_log(dry_run)
            
            self.migration_stats["migration_end_time"] = datetime.now().isoformat()
            
            self.logger.info("Миграция завершена успешно")
            
        except Exception as e:
            self.logger.error(f"Ошибка миграции: {e}")
            self.migration_stats["error"] = str(e)
        
        return self.migration_stats
    
    def _migrate_attachments_from_emails(self, dry_run: bool):
        """Миграция вложений из JSON файлов писем"""
        self.logger.info("Шаг 1: Миграция вложений из JSON файлов писем")
        
        if not self.emails_dir.exists():
            self.logger.warning(f"Директория с письмами не найдена: {self.emails_dir}")
            return
        
        # Обходим все директории с датами
        for date_dir in self.emails_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            date_str = date_dir.name
            self.logger.info(f"Обработка даты: {date_str}")
            
            # Обходим все JSON файлы писем
            for email_file in date_dir.glob("*.json"):
                try:
                    self._process_email_file(email_file, dry_run)
                    self.migration_stats["total_emails_processed"] += 1
                    
                except Exception as e:
                    self.logger.error(f"Ошибка обработки файла {email_file}: {e}")
                    continue
    
    def _process_email_file(self, email_file: Path, dry_run: bool):
        """Обработка одного JSON файла письма"""
        try:
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            
            message_id = email_data.get("message_id")
            thread_id = email_data.get("thread_id")
            date_folder = email_data.get("date_folder")
            
            if not message_id:
                self.logger.warning(f"В файле {email_file} отсутствует message_id")
                return
            
            # Получаем вложения из письма
            attachments = email_data.get("attachments", [])
            
            if not attachments:
                return  # Нет вложений для миграции
            
            self.logger.debug(f"Обработка письма {message_id}: {len(attachments)} вложений")
            
            for attachment in attachments:
                try:
                    self._migrate_attachment(attachment, message_id, thread_id, date_folder, dry_run)
                except Exception as e:
                    self.logger.error(f"Ошибка миграции вложения из {email_file}: {e}")
                    self.migration_stats["attachments_with_errors"] += 1
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка декодирования JSON в файле {email_file}: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка обработки файла {email_file}: {e}")
    
    def _migrate_attachment(self, attachment: Dict, message_id: str, thread_id: str, 
                           date_folder: str, dry_run: bool):
        """Миграция одного вложения"""
        filename = attachment.get("filename") or attachment.get("saved_filename")
        saved_filename = attachment.get("saved_filename")
        
        if not saved_filename:
            self.logger.warning(f"Вложение без имени файла в письме {message_id}")
            return
        
        # Определяем путь к файлу вложения
        if date_folder:
            attachment_path = self.attachments_dir / date_folder / saved_filename
        else:
            # Ищем файл по всей директории вложений
            attachment_path = self._find_attachment_file(saved_filename)
        
        if not attachment_path or not attachment_path.exists():
            self.logger.warning(f"Файл вложения не найден: {saved_filename}")
            return
        
        # Получаем дополнительную информацию о вложении
        file_size = attachment.get("size")
        content_type = attachment.get("type")
        is_inline = attachment.get("is_inline", False)
        
        # Если content_type отсутствует, определяем по расширению
        if not content_type:
            content_type = self._detect_content_type(attachment_path)
        
        # Регистрируем вложение
        if not dry_run:
            attachment_id = self.attachment_registry.register_attachment(
                message_id=message_id,
                attachment_filename=filename or saved_filename,
                attachment_path=str(attachment_path),
                thread_id=thread_id,
                file_size=file_size,
                content_type=content_type,
                is_inline=is_inline
            )
            
            self.logger.debug(f"Зарегистрировано вложение: {attachment_id}")
        
        self.migration_stats["total_attachments_migrated"] += 1
    
    def _find_attachment_file(self, filename: str) -> Optional[Path]:
        """Поиск файла вложения по имени"""
        for date_dir in self.attachments_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            attachment_path = date_dir / filename
            if attachment_path.exists():
                return attachment_path
        
        return None
    
    def _detect_content_type(self, file_path: Path) -> str:
        """Определение типа контента файла по расширению"""
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
    
    def _register_orphaned_attachments(self, dry_run: bool):
        """Регистрация осиротевших вложений (файлов без записей в JSON)"""
        self.logger.info("Шаг 2: Поиск и регистрация осиротевших вложений")
        
        if not self.attachments_dir.exists():
            self.logger.warning(f"Директория с вложениями не найдена: {self.attachments_dir}")
            return
        
        # Получаем все уже зарегистрированные файлы
        registered_files = set()
        for attachment_info in self.attachment_registry.registry["attachments"].values():
            attachment_path = Path(attachment_info.get("attachment_path"))
            if attachment_path.exists():
                registered_files.add(attachment_path.name)
        
        # Ищем файлы, которые не зарегистрированы
        for date_dir in self.attachments_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            for attachment_file in date_dir.iterdir():
                if not attachment_file.is_file():
                    continue
                
                if attachment_file.name not in registered_files:
                    self._register_orphaned_attachment(attachment_file, date_dir.name, dry_run)
                    self.migration_stats["orphaned_attachments_found"] += 1
    
    def _register_orphaned_attachment(self, attachment_file: Path, date_folder: str, dry_run: bool):
        """Регистрация осиротевшего вложения"""
        # Пытаемся найти письмо по шаблону имени файла
        filename = attachment_file.name
        
        # Извлекаем thread_id из имени файла
        thread_id = self._extract_thread_id_from_filename(filename)
        
        if thread_id:
            # Ищем письмо с таким thread_id
            message_id = self._find_message_by_thread_id(thread_id, date_folder)
            
            if message_id:
                file_size = attachment_file.stat().st_size
                content_type = self._detect_content_type(attachment_file)
                
                if not dry_run:
                    attachment_id = self.attachment_registry.register_attachment(
                        message_id=message_id,
                        attachment_filename=filename,
                        attachment_path=str(attachment_file),
                        thread_id=thread_id,
                        file_size=file_size,
                        content_type=content_type,
                        is_inline=False  # Предполагаем, что осиротевшие вложения не inline
                    )
                    
                    self.logger.debug(f"Зарегистрировано осиротевшее вложение: {attachment_id}")
                
                self.logger.info(f"Найдено осиротевшее вложение: {filename} -> {message_id}")
            else:
                self.logger.warning(f"Не найдено письмо для осиротевшего вложения: {filename}")
        else:
            self.logger.warning(f"Не удалось извлечь thread_id из имени файла: {filename}")
    
    def _extract_thread_id_from_filename(self, filename: str) -> Optional[str]:
        """Извлечение thread_id из имени файла вложения"""
        # Пытаемся найти паттерн: {thread_id}_{timestamp}_{prefix}_{filename}
        parts = filename.split("_")
        
        if len(parts) >= 3:
            # Предполагаем, что thread_id - это первая часть
            potential_thread_id = parts[0]
            
            # Проверяем, что это похоже на thread_id (содержит дату и домен)
            if len(potential_thread_id) >= 10 and any(c.isalpha() for c in potential_thread_id):
                return potential_thread_id
        
        return None
    
    def _find_message_by_thread_id(self, thread_id: str, date_folder: str) -> Optional[str]:
        """Поиск message_id по thread_id"""
        date_dir = self.emails_dir / date_folder
        
        if not date_dir.exists():
            return None
        
        for email_file in date_dir.glob("*.json"):
            try:
                with open(email_file, 'r', encoding='utf-8') as f:
                    email_data = json.load(f)
                
                if email_data.get("thread_id") == thread_id:
                    return email_data.get("message_id")
                    
            except (json.JSONDecodeError, IOError):
                continue
        
        return None
    
    def _save_migration_log(self, dry_run: bool):
        """Сохранение логов миграции"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"attachment_migration_{timestamp}{'_dryrun' if dry_run else ''}.json"
        log_path = self.migration_log_dir / log_filename
        
        # Дополняем статистику
        self.migration_stats["registry_stats"] = self.attachment_registry.get_statistics()
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(self.migration_stats, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Лог миграции сохранен: {log_path}")
    
    def validate_migration(self) -> Dict:
        """
        Валидация результатов миграции
        
        Returns:
            Результаты валидации
        """
        self.logger.info("Валидация результатов миграции")
        
        validation_results = {
            "total_messages_in_registry": 0,
            "total_attachments_in_registry": 0,
            "messages_without_attachments": 0,
            "attachments_without_files": 0,
            "total_files_in_attachments_dir": 0,
            "unregistered_files": 0,
            "validation_timestamp": datetime.now().isoformat()
        }
        
        # Статистика реестра
        registry_stats = self.attachment_registry.get_statistics()
        validation_results["total_messages_in_registry"] = registry_stats["total_messages"]
        validation_results["total_attachments_in_registry"] = registry_stats["total_attachments"]
        
        # Проверяем файлы в директории вложений
        total_files = 0
        registered_files = set()
        
        for attachment_info in self.attachment_registry.registry["attachments"].values():
            attachment_path = Path(attachment_info.get("attachment_path"))
            if attachment_path.exists():
                registered_files.add(attachment_path.name)
            else:
                validation_results["attachments_without_files"] += 1
        
        # Считаем все файлы в директории вложений
        for date_dir in self.attachments_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            for attachment_file in date_dir.iterdir():
                if attachment_file.is_file():
                    total_files += 1
                    
                    if attachment_file.name not in registered_files:
                        validation_results["unregistered_files"] += 1
        
        validation_results["total_files_in_attachments_dir"] = total_files
        
        # Сохраняем результаты валидации
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        validation_filename = f"migration_validation_{timestamp}.json"
        validation_path = self.migration_log_dir / validation_filename
        
        with open(validation_path, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Результаты валидации сохранены: {validation_path}")
        
        return validation_results


def run_migration(data_dir: Path, dry_run: bool = False) -> Dict:
    """
    Запуск миграции
    
    Args:
        data_dir: Базовая директория данных
        dry_run: Режим проверки без изменений
        
    Returns:
        Статистика миграции
    """
    # Настраиваем логирование
    logger = logging.getLogger("AttachmentMigration")
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    
    # Создаем и запускаем миграцию
    migration = AttachmentMigration(data_dir, logger)
    migration_stats = migration.migrate_all_data(dry_run)
    
    # Запускаем валидацию
    if not dry_run:
        validation_results = migration.validate_migration()
        migration_stats["validation_results"] = validation_results
    
    return migration_stats


if __name__ == "__main__":
    # Демонстрация работы
    from pathlib import Path
    import sys
    
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    else:
        data_dir = Path("data")  # Текущая директория по умолчанию
    
    dry_run = "--dry-run" in sys.argv
    
    print(f"Запуск миграции для директории: {data_dir}")
    if dry_run:
        print("режим DRY RUN - изменения не будут применены")
    
    stats = run_migration(data_dir, dry_run)
    
    print("\nРезультаты миграции:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))