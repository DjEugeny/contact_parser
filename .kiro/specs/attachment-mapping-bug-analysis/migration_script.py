#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт миграции существующих данных в новую схему с реестром вложений
"""

import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

# Импортируем реестр вложений
from attachment_registry_spec import AttachmentRegistry


class AttachmentMigration:
    """Скрипт миграции существующих данных в новую схему"""
    
    def __init__(self, data_dir: Path, logger: Optional[logging.Logger] = None):
        """
        Инициализация миграции
        
        Args:
            data_dir: Базовая директория данных
            logger: Логгер для записи операций
        """
        self.data_dir = data_dir
        self.logger = logger or self._setup_logger()
        self.attachment_registry = AttachmentRegistry(data_dir, logger)
        self.emails_dir = data_dir / "emails"
        self.attachments_dir = data_dir / "attachments"
        
        # Статистика миграции
        self.migration_stats = {
            "processed_emails": 0,
            "migrated_attachments": 0,
            "errors": [],
            "warnings": [],
            "orphaned_attachments": 0,
            "duplicate_attachments": 0,
            "missing_files": 0,
            "start_time": None,
            "end_time": None
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Настройка логгера"""
        logger = logging.getLogger("AttachmentMigration")
        logger.setLevel(logging.INFO)
        
        # Обработчик для вывода в консоль
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Форматирование
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Добавляем обработчик
        if not logger.handlers:
            logger.addHandler(console_handler)
        
        return logger
    
    def create_backup(self) -> Path:
        """
        Создание резервной копии данных
        
        Returns:
            Путь к директории с резервной копией
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.data_dir / f"backup_before_migration_{timestamp}"
        
        self.logger.info(f"Создание резервной копии: {backup_dir}")
        
        try:
            # Копируем папки с письмами и вложениями
            if self.emails_dir.exists():
                backup_emails_dir = backup_dir / "emails"
                shutil.copytree(self.emails_dir, backup_emails_dir)
                self.logger.info(f"Скопирована папка с письмами: {self.emails_dir}")
            
            if self.attachments_dir.exists():
                backup_attachments_dir = backup_dir / "attachments"
                shutil.copytree(self.attachments_dir, backup_attachments_dir)
                self.logger.info(f"Скопирована папка с вложениями: {self.attachments_dir}")
            
            # Копируем реестр, если он существует
            registry_file = self.data_dir / "registry" / "attachment_registry.json"
            if registry_file.exists():
                backup_registry_dir = backup_dir / "registry"
                backup_registry_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(registry_file, backup_registry_dir / "attachment_registry.json")
                self.logger.info(f"Скопирован реестр вложений: {registry_file}")
            
            self.logger.info(f"Резервная копия создана успешно: {backup_dir}")
            return backup_dir
            
        except Exception as e:
            self.logger.error(f"Ошибка создания резервной копии: {e}")
            raise
    
    def migrate_existing_attachments(self) -> Dict:
        """
        Миграция существующих вложений в новую схему
        
        Returns:
            Результаты миграции
        """
        self.migration_stats["start_time"] = datetime.now()
        
        self.logger.info("=" * 70)
        self.logger.info("НАЧАЛО МИГРАЦИИ ВЛОЖЕНИЙ")
        self.logger.info("=" * 70)
        
        try:
            # Шаг 1: Анализ существующих данных
            self._analyze_existing_data()
            
            # Шаг 2: Миграция писем и вложений
            self._migrate_emails()
            
            # Шаг 3: Обработка осиротевших вложений
            self._process_orphaned_attachments()
            
            # Шаг 4: Очистка реестра от несуществующих файлов
            self._cleanup_registry()
            
            # Шаг 5: Валидация результатов миграции
            self._validate_migration()
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка миграции: {e}")
            self.migration_stats["errors"].append(f"Critical error: {e}")
        
        finally:
            self.migration_stats["end_time"] = datetime.now()
            self._log_migration_summary()
        
        return self.migration_stats
    
    def _analyze_existing_data(self):
        """Анализ существующих данных"""
        self.logger.info("Анализ существующих данных...")
        
        # Считаем письма
        total_emails = 0
        for date_dir in self.emails_dir.iterdir():
            if date_dir.is_dir():
                email_files = list(date_dir.glob("*.json"))
                total_emails += len(email_files)
        
        # Считаем вложения
        total_attachments = 0
        for date_dir in self.attachments_dir.iterdir():
            if date_dir.is_dir():
                attachment_files = list(date_dir.glob("*"))
                total_attachments += len(attachment_files)
        
        self.logger.info(f"Найдено писем: {total_emails}")
        self.logger.info(f"Найдено вложений: {total_attachments}")
        
        # Проверяем существующий реестр
        registry_file = self.data_dir / "registry" / "attachment_registry.json"
        registry_exists = registry_file.exists()
        
        if registry_exists:
            with open(registry_file, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            existing_attachments = len(registry_data.get("attachments", {}))
            self.logger.info(f"Существующий реестр содержит: {existing_attachments} вложений")
        
            if existing_attachments > 0:
                self.logger.warning("Реестр уже содержит данные. Миграция дополнит существующие данные.")
        else:
            self.logger.info("Реестр не найден, будет создан новый.")
    
    def _migrate_emails(self):
        """Миграция писем и вложений"""
        self.logger.info("Миграция писем и вложений...")
        
        processed_dates = 0
        
        for date_dir in sorted(self.emails_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            
            date_str = date_dir.name
            self.logger.info(f"Обработка даты: {date_str}")
            
            date_start_time = datetime.now()
            date_migration_count = 0
            
            # Обрабатываем все JSON файлы писем за эту дату
            for email_file in sorted(date_dir.glob("*.json")):
                try:
                    self._process_email_file(email_file, date_str)
                    self.migration_stats["processed_emails"] += 1
                    date_migration_count += 1
                    
                except Exception as e:
                    error_msg = f"Error processing {email_file}: {e}"
                    self.logger.error(error_msg)
                    self.migration_stats["errors"].append(error_msg)
            
            date_end_time = datetime.now()
            date_duration = date_end_time - date_start_time
            
            self.logger.info(f"Дата {date_str} обработана: {date_migration_count} писем за {date_duration}")
            processed_dates += 1
        
        self.logger.info(f"Обработано дат: {processed_dates}")
    
    def _process_email_file(self, email_file: Path, date_str: str):
        """Обработка одного файла письма"""
        try:
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            
            message_id = email_data.get("message_id")
            thread_id = email_data.get("thread_id")
            
            if not message_id:
                self.migration_stats["warnings"].append(f"Missing message_id in {email_file}")
                return
            
            # Обрабатываем вложения в письме
            attachments = email_data.get("attachments", [])
            updated_attachments = []
            
            for attachment in attachments:
                attachment_result = self._process_attachment(
                    attachment, message_id, thread_id, date_str, email_file
                )
                
                if attachment_result:
                    updated_attachments.append(attachment_result)
            
            # Обновляем информацию о вложениях в письме
            if updated_attachments != attachments:
                email_data["attachments"] = updated_attachments
                email_data["migration_info"] = {
                    "migrated_at": datetime.now().isoformat(),
                    "migration_version": "1.0"
                }
                
                # Сохраняем обновленные данные письма
                with open(email_file, 'w', encoding='utf-8') as f:
                    json.dump(email_data, f, ensure_ascii=False, indent=2)
                
                self.logger.debug(f"Обновлен файл письма: {email_file}")
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {email_file}: {e}"
            self.logger.error(error_msg)
            self.migration_stats["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"Error processing {email_file}: {e}"
            self.logger.error(error_msg)
            self.migration_stats["errors"].append(error_msg)
    
    def _process_attachment(self, attachment: Dict, message_id: str, thread_id: str, 
                           date_str: str, email_file: Path) -> Optional[Dict]:
        """Обработка одного вложения"""
        attachment_filename = attachment.get("saved_filename") or attachment.get("filename")
        
        if not attachment_filename:
            self.migration_stats["warnings"].append(f"Missing attachment filename in {email_file}")
            return attachment
        
        # Определяем путь к вложению
        attachment_path = self.attachments_dir / date_str / attachment_filename
        
        if not attachment_path.exists():
            self.migration_stats["missing_files"] += 1
            self.logger.warning(f"Файл вложения не найден: {attachment_path}")
            return attachment
        
        # Проверяем, не зарегистрировано ли уже это вложение
        existing_attachment = self.attachment_registry.find_attachment_file(message_id, attachment_filename)
        
        if existing_attachment:
            self.migration_stats["duplicate_attachments"] += 1
            self.logger.debug(f"Вложение уже зарегистрировано: {attachment_filename}")
            
            # Обновляем информацию о существующем вложении
            attachments = self.attachment_registry.get_attachments_by_message(message_id)
            for att in attachments:
                if att.get("attachment_filename") == attachment_filename:
                    attachment.update({
                        "attachment_id": att.get("attachment_id"),
                        "registered_at": att.get("registered_at"),
                        "migration_info": {
                            "migrated_at": datetime.now().isoformat(),
                            "migration_version": "1.0",
                            "status": "existing"
                        }
                    })
                    return attachment
        
        # Регистрируем новое вложение
        try:
            file_size = attachment_path.stat().st_size
            content_type = attachment.get("type", "application/octet-stream")
            is_inline = attachment.get("is_inline", False)
            
            attachment_id = self.attachment_registry.register_attachment(
                message_id=message_id,
                attachment_filename=attachment_filename,
                attachment_path=str(attachment_path),
                thread_id=thread_id,
                file_size=file_size,
                content_type=content_type,
                is_inline=is_inline
            )
            
            self.migration_stats["migrated_attachments"] += 1
            
            # Обновляем информацию о вложении
            updated_attachment = {
                **attachment,
                "attachment_id": attachment_id,
                "registered_at": datetime.now().isoformat(),
                "migration_info": {
                    "migrated_at": datetime.now().isoformat(),
                    "migration_version": "1.0",
                    "status": "migrated"
                }
            }
            
            self.logger.debug(f"Зарегистрировано вложение: {attachment_id}")
            return updated_attachment
            
        except Exception as e:
            error_msg = f"Error registering attachment {attachment_filename}: {e}"
            self.logger.error(error_msg)
            self.migration_stats["errors"].append(error_msg)
            return attachment
    
    def _process_orphaned_attachments(self):
        """Обработка осиротевших вложений"""
        self.logger.info("Обработка осиротевших вложений...")
        
        # Получаем все зарегистрированные файлы
        registered_files = set()
        for attachment_info in self.attachment_registry.registry["attachments"].values():
            registered_files.add(Path(attachment_info.get("attachment_path")))
        
        # Ищем файлы, которые не зарегистрированы
        orphaned_files = []
        
        for date_dir in self.attachments_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            for attachment_file in date_dir.glob("*"):
                if attachment_file.is_file() and attachment_file not in registered_files:
                    orphaned_files.append(attachment_file)
        
        self.logger.info(f"Найдено осиротевших вложений: {len(orphaned_files)}")
        
        if orphaned_files:
            self.logger.warning("Обнаружены осиротевшие вложения. Их нужно обработать вручную.")
            
            for orphaned_file in orphaned_files[:10]:  # Показываем первые 10
                self.logger.warning(f"  - {orphaned_file}")
            
            if len(orphaned_files) > 10:
                self.logger.warning(f"  ... и еще {len(orphaned_files) - 10} файлов")
            
            self.migration_stats["orphaned_attachments"] = len(orphaned_files)
    
    def _cleanup_registry(self):
        """Очистка реестра от несуществующих файлов"""
        self.logger.info("Очистка реестра от несуществующих файлов...")
        
        cleanup_result = self.attachment_registry.cleanup_orphaned_attachments()
        
        if cleanup_result["orphaned_count"] > 0:
            self.logger.info(f"Удалено записей о несуществующих вложениях: {cleanup_result['orphaned_count']}")
    
    def _validate_migration(self):
        """Валидация результатов миграции"""
        self.logger.info("Валидация результатов миграции...")
        
        # Проверяем статистику реестра
        registry_stats = self.attachment_registry.get_statistics()
        
        self.logger.info(f"Статистика реестра после миграции:")
        self.logger.info(f"  - Всего вложений: {registry_stats['total_attachments']}")
        self.logger.info(f"  - Всего сообщений: {registry_stats['total_messages']}")
        self.logger.info(f"  - Общий размер: {registry_stats['total_size_mb']} МБ")
        
        # Проверяем целостность данных
        messages_with_attachments = self.attachment_registry.get_messages_with_attachments()
        self.logger.info(f"Сообщений с вложениями: {len(messages_with_attachments)}")
        
        # Проверяем несколько случайных вложений
        import random
        
        if messages_with_attachments:
            sample_messages = random.sample(messages_with_attachments, min(5, len(messages_with_attachments)))
            
            for message_id in sample_messages:
                attachments = self.attachment_registry.get_attachments_by_message(message_id)
                
                for attachment in attachments:
                    attachment_path = Path(attachment.get("attachment_path"))
                    
                    if attachment_path.exists():
                        self.logger.debug(f"✓ Вложение существует: {attachment_path.name}")
                    else:
                        self.migration_stats["warnings"].append(
                            f"Registered attachment not found: {attachment_path}"
                        )
    
    def _log_migration_summary(self):
        """Вывод итоговой статистики миграции"""
        duration = self.migration_stats["end_time"] - self.migration_stats["start_time"]
        
        self.logger.info("=" * 70)
        self.logger.info("ИТОГИ МИГРАЦИИ")
        self.logger.info("=" * 70)
        self.logger.info(f"Время выполнения: {duration}")
        self.logger.info(f"Обработано писем: {self.migration_stats['processed_emails']}")
        self.logger.info(f"Сопоставлено вложений: {self.migration_stats['migrated_attachments']}")
        self.logger.info(f"Дубликатов вложений: {self.migration_stats['duplicate_attachments']}")
        self.logger.info(f"Отсутствующих файлов: {self.migration_stats['missing_files']}")
        self.logger.info(f"Осиротевших вложений: {self.migration_stats['orphaned_attachments']}")
        self.logger.info(f"Ошибок: {len(self.migration_stats['errors'])}")
        self.logger.info(f"Предупреждений: {len(self.migration_stats['warnings'])}")
        
        if self.migration_stats["errors"]:
            self.logger.error("ОШИБКИ МИГРАЦИИ:")
            for error in self.migration_stats["errors"][:10]:  # Показываем первые 10
                self.logger.error(f"  - {error}")
            
            if len(self.migration_stats["errors"]) > 10:
                self.logger.error(f"  ... и еще {len(self.migration_stats['errors']) - 10} ошибок")
        
        if self.migration_stats["warnings"]:
            self.logger.warning("ПРЕДУПРЕЖДЕНИЯ МИГРАЦИИ:")
            for warning in self.migration_stats["warnings"][:10]:  # Показываем первые 10
                self.logger.warning(f"  - {warning}")
            
            if len(self.migration_stats["warnings"]) > 10:
                self.logger.warning(f"  ... и еще {len(self.migration_stats['warnings']) - 10} предупреждений")
        
        self.logger.info("=" * 70)
    
    def generate_migration_report(self, output_path: Path):
        """
        Генерация отчета о миграции
        
        Args:
            output_path: Путь для сохранения отчета
        """
        report = {
            "migration_info": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "duration": str(self.migration_stats["end_time"] - self.migration_stats["start_time"])
            },
            "statistics": self.migration_stats,
            "registry_statistics": self.attachment_registry.get_statistics()
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Отчет о миграции сохранен: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения отчета: {e}")


def main():
    """Основная функция для запуска миграции"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Миграция вложений в новую схему с реестром")
    parser.add_argument("--data-dir", type=str, default="data", help="Директория с данными")
    parser.add_argument("--no-backup", action="store_true", help="Не создавать резервную копию")
    parser.add_argument("--dry-run", action="store_true", help="Тестовый запуск без изменений")
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    
    if not data_dir.exists():
        print(f"Ошибка: директория {data_dir} не существует")
        return 1
    
    # Настройка логгера
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger("AttachmentMigration")
    
    try:
        # Создаем мигратор
        migration = AttachmentMigration(data_dir, logger)
        
        if not args.no_backup and not args.dry_run:
            # Создаем резервную копию
            backup_dir = migration.create_backup()
            print(f"Резервная копия создана: {backup_dir}")
        
        if args.dry_run:
            print("ТЕСТОВЫЙ ЗАПУСК - изменения не будут применены")
            # TODO: Реализовать логику тестового запуска
            return 0
        
        # Выполняем миграцию
        result = migration.migrate_existing_attachments()
        
        # Генерируем отчет
        report_path = data_dir / "migration_report.json"
        migration.generate_migration_report(report_path)
        
        # Проверяем результат
        if len(result["errors"]) > 0:
            print(f"Миграция завершена с ошибками: {len(result['errors'])}")
            return 1
        else:
            print("Миграция успешно завершена")
            return 0
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 1


if __name__ == "__main__":
    exit(main())