#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔄 Модуль миграции вложений из thread_id в message_id
Исправляет некорректный маппинг вложений в существующих данных
"""

import json
import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging


class AttachmentMigration:
    """🔄 Класс для миграции вложений из thread_id в message_id"""
    
    def __init__(self, data_dir: Path = None, logger=None):
        """Инициализация мигратора"""
        self.data_dir = data_dir or Path("data")
        self.emails_dir = self.data_dir / "emails"
        self.attachments_dir = self.data_dir / "attachments"
        self.logger = logger or logging.getLogger(__name__)
        
        # Статистика миграции
        self.stats = {
            "emails_processed": 0,
            "attachments_processed": 0,
            "attachments_moved": 0,
            "attachments_fixed": 0,
            "errors": 0,
            "orphaned_attachments": 0
        }
        
        # Бэкап директория
        self.backup_dir = self.data_dir / "migration_backup"
        
    def create_backup(self) -> bool:
        """📦 Создание резервной копии данных"""
        try:
            self.logger.info("📦 Создание резервной копии данных...")
            
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            
            # Копируем директории
            if self.emails_dir.exists():
                shutil.copytree(self.emails_dir, self.backup_dir / "emails")
                self.logger.info(f"✅ Письма скопированы в {self.backup_dir / 'emails'}")
            
            if self.attachments_dir.exists():
                shutil.copytree(self.attachments_dir, self.backup_dir / "attachments")
                self.logger.info(f"✅ Вложения скопированы в {self.backup_dir / 'attachments'}")
            
            # Сохраняем метаданные бэкапа
            backup_metadata = {
                "created_at": datetime.now().isoformat(),
                "original_emails_dir": str(self.emails_dir),
                "original_attachments_dir": str(self.attachments_dir),
                "backup_dir": str(self.backup_dir)
            }
            
            with open(self.backup_dir / "backup_metadata.json", "w", encoding="utf-8") as f:
                json.dump(backup_metadata, f, indent=2, ensure_ascii=False)
            
            self.logger.info("✅ Резервная копия создана успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания резервной копии: {e}")
            return False
    
    def load_email_data(self, email_path: Path) -> Optional[Dict]:
        """📧 Загрузка данных письма из JSON файла"""
        try:
            with open(email_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки письма {email_path}: {e}")
            return None
    
    def extract_message_id_from_filename(self, filename: str) -> Optional[str]:
        """🔍 Извлечение message_id из имени файла вложения"""
        try:
            # Имя файла имеет формат: {thread_id}_{timestamp}_{prefix}_{original_name}
            # Нам нужно найти соответствующее письмо и извлечь его message_id
            
            # Извлекаем thread_id из имени файла
            parts = filename.split("_")
            if len(parts) >= 3:
                thread_id = "_".join(parts[:3])  # Первые 3 части составляют thread_id
                
                # Ищем письмо с таким thread_id
                for email_file in self.emails_dir.rglob("*.json"):
                    try:
                        email_data = self.load_email_data(email_file)
                        if email_data and email_data.get("thread_id") == thread_id:
                            return email_data.get("message_id")
                    except Exception:
                        continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения message_id из {filename}: {e}")
            return None
    
    def find_correct_email_for_attachment(self, attachment_path: Path) -> Optional[Path]:
        """🔍 Поиск правильного письма для вложения"""
        try:
            attachment_filename = attachment_path.name
            
            # Извлекаем thread_id из имени файла
            parts = attachment_filename.split("_")
            if len(parts) < 3:
                return None
            
            thread_id = "_".join(parts[:3])
            
            # Ищем письма с таким thread_id
            candidate_emails = []
            for email_file in self.emails_dir.rglob("*.json"):
                try:
                    email_data = self.load_email_data(email_file)
                    if email_data and email_data.get("thread_id") == thread_id:
                        candidate_emails.append((email_file, email_data))
                except Exception:
                    continue
            
            if not candidate_emails:
                return None
            
            # Если одно письмо - возвращаем его
            if len(candidate_emails) == 1:
                return candidate_emails[0][0]
            
            # Если несколько писем - пытаемся найти наиболее подходящее
            # Сравниваем временные метки
            attachment_timestamp = self.extract_timestamp_from_filename(attachment_filename)
            if attachment_timestamp:
                best_email = None
                min_time_diff = float('inf')
                
                for email_file, email_data in candidate_emails:
                    try:
                        email_date = datetime.fromisoformat(email_data.get("date", ""))
                        time_diff = abs((email_date - attachment_timestamp).total_seconds())
                        
                        if time_diff < min_time_diff:
                            min_time_diff = time_diff
                            best_email = email_file
                    except Exception:
                        continue
                
                return best_email
            
            # Если не удалось определить по времени, берем первое
            return candidate_emails[0][0]
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска письма для вложения {attachment_path}: {e}")
            return None
    
    def extract_timestamp_from_filename(self, filename: str) -> Optional[datetime]:
        """🕒 Извлечение временной метки из имени файла"""
        try:
            parts = filename.split("_")
            if len(parts) >= 4:
                # Ищем временную метку в частях имени файла
                for part in parts:
                    if part.isdigit() and len(part) == 6:  # Формат HHMMSS
                        # Это может быть время, но без даты не очень полезно
                        pass
            
            return None
            
        except Exception:
            return None
    
    def migrate_attachment(self, attachment_path: Path, correct_email_path: Path) -> bool:
        """🔄 Перемещение вложения к правильному письму"""
        try:
            email_data = self.load_email_data(correct_email_path)
            if not email_data:
                return False
            
            message_id = email_data.get("message_id")
            if not message_id:
                return False
            
            # Создаем безопасный message_id для имени файла
            safe_message_id = self.sanitize_message_id(message_id)
            
            # Новое имя файла вложения
            original_name = "_".join(attachment_path.name.split("_")[3:])  # Пропускаем thread_id
            new_filename = f"{safe_message_id}_{original_name}"
            
            # Новая директория для вложения
            date_folder = email_data.get("date_folder", "unknown")
            new_attachment_dir = self.attachments_dir / date_folder
            new_attachment_dir.mkdir(parents=True, exist_ok=True)
            
            new_attachment_path = new_attachment_dir / new_filename
            
            # Перемещаем файл
            shutil.move(str(attachment_path), str(new_attachment_path))
            
            self.logger.info(f"✅ Вложение перемещено: {attachment_path.name} -> {new_filename}")
            
            self.stats["attachments_moved"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка перемещения вложения {attachment_path}: {e}")
            self.stats["errors"] += 1
            return False
    
    def sanitize_message_id(self, message_id: str) -> str:
        """🧹 Очистка message_id для использования в имени файла"""
        # Удаляем угловые скобки и спецсимволы
        clean_id = message_id.replace("<", "").replace(">", "").replace("@", "_at_")
        # Заменяем другие спецсимволы на подчеркивания
        clean_id = "".join(c if c.isalnum() or c in "._-" else "_" for c in clean_id)
        # Ограничиваем длину
        return clean_id[:50]
    
    def fix_email_attachments_data(self, email_path: Path) -> bool:
        """🔧 Исправление данных о вложениях в письме"""
        try:
            email_data = self.load_email_data(email_path)
            if not email_data:
                return False
            
            message_id = email_data.get("message_id")
            if not message_id:
                return False
            
            # Ищем реальные вложения для этого письма
            date_folder = email_data.get("date_folder", "unknown")
            attachment_dir = self.attachments_dir / date_folder
            
            if not attachment_dir.exists():
                return False
            
            # Ищем вложения с правильным message_id
            real_attachments = []
            safe_message_id = self.sanitize_message_id(message_id)
            
            for attachment_file in attachment_dir.glob(f"{safe_message_id}_*"):
                try:
                    # Извлекаем оригинальное имя файла
                    original_name = "_".join(attachment_file.name.split("_")[1:])
                    
                    attachment_info = {
                        "filename": original_name,
                        "saved_filename": attachment_file.name,
                        "size": attachment_file.stat().st_size,
                        "path": str(attachment_file.relative_to(self.data_dir)),
                        "status": "saved",
                        "type": "existing_attachment"
                    }
                    
                    real_attachments.append(attachment_info)
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка обработки вложения {attachment_file}: {e}")
            
            # Обновляем данные письма
            if real_attachments:
                email_data["attachments"] = real_attachments
                email_data["attachments_stats"] = {
                    "total": len(real_attachments),
                    "saved": len(real_attachments),
                    "excluded": 0,
                    "excluded_filenames": 0,
                    "excluded_by_size": 0,
                    "excluded_by_image_dimensions": 0,
                    "unsupported": 0,
                    "inline_images": 0
                }
                
                # Сохраняем обновленные данные
                with open(email_path, "w", encoding="utf-8") as f:
                    json.dump(email_data, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"✅ Обновлены данные о вложениях в письме: {email_path.name}")
                self.stats["attachments_fixed"] += 1
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка исправления данных письма {email_path}: {e}")
            self.stats["errors"] += 1
            return False
    
    def migrate_all_attachments(self) -> Dict:
        """🔄 Выполнение полной миграции всех вложений"""
        self.logger.info("🔄 НАЧАЛО МИГРАЦИИ ВЛОЖЕНИЙ")
        self.logger.info("=" * 60)
        
        # Шаг 1: Создание резервной копии
        if not self.create_backup():
            return {"status": "error", "message": "Не удалось создать резервную копию"}
        
        # Шаг 2: Анализ и миграция вложений
        self.logger.info("🔍 Анализ и миграция вложений...")
        
        if not self.attachments_dir.exists():
            self.logger.info("📭 Директория вложений не найдена")
            return {"status": "success", "message": "Вложения отсутствуют"}
        
        # Собираем все вложения
        all_attachments = list(self.attachments_dir.rglob("*"))
        all_attachments = [f for f in all_attachments if f.is_file()]
        
        self.logger.info(f"📎 Найдено вложений: {len(all_attachments)}")
        
        # Шаг 3: Миграция каждого вложения
        migrated_attachments = 0
        for attachment_path in all_attachments:
            self.stats["attachments_processed"] += 1
            
            # Ищем правильное письмо для вложения
            correct_email = self.find_correct_email_for_attachment(attachment_path)
            
            if correct_email:
                # Перемещаем вложение
                if self.migrate_attachment(attachment_path, correct_email):
                    migrated_attachments += 1
            else:
                self.logger.warning(f"⚠️ Не найдено письмо для вложения: {attachment_path.name}")
                self.stats["orphaned_attachments"] += 1
        
        # Шаг 4: Исправление данных в письмах
        self.logger.info("🔧 Исправление данных о вложениях в письмах...")
        
        if self.emails_dir.exists():
            for email_file in self.emails_dir.rglob("*.json"):
                self.stats["emails_processed"] += 1
                self.fix_email_attachments_data(email_file)
        
        # Шаг 5: Удаление пустых директорий
        self.cleanup_empty_directories()
        
        # Формируем результат
        result = {
            "status": "success",
            "stats": self.stats,
            "backup_location": str(self.backup_dir),
            "message": f"Миграция завершена. Перемещено вложений: {migrated_attachments}"
        }
        
        self.logger.info("=" * 60)
        self.logger.info("🎉 МИГРАЦИЯ ЗАВЕРШЕНА")
        self.logger.info(f"📊 Статистика:")
        self.logger.info(f"   Писем обработано: {self.stats['emails_processed']}")
        self.logger.info(f"   Вложений обработано: {self.stats['attachments_processed']}")
        self.logger.info(f"   Вложений перемещено: {self.stats['attachments_moved']}")
        self.logger.info(f"   Данных исправлено: {self.stats['attachments_fixed']}")
        self.logger.info(f"   Ошибок: {self.stats['errors']}")
        self.logger.info(f"   Осиротевших вложений: {self.stats['orphaned_attachments']}")
        self.logger.info(f"📦 Резервная копия: {self.backup_dir}")
        
        return result
    
    def cleanup_empty_directories(self):
        """🧹 Очистка пустых директорий"""
        try:
            for root, dirs, files in os.walk(self.attachments_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            self.logger.debug(f"🧹 Удалена пустая директория: {dir_path}")
                    except OSError:
                        pass
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка очистки пустых директорий: {e}")
    
    def rollback_migration(self) -> bool:
        """🔄 Откат миграции"""
        try:
            if not self.backup_dir.exists():
                self.logger.error("❌ Резервная копия не найдена")
                return False
            
            self.logger.info("🔄 ОТКАТ МИГРАЦИИ...")
            
            # Восстанавливаем из бэкапа
            if (self.backup_dir / "emails").exists():
                if self.emails_dir.exists():
                    shutil.rmtree(self.emails_dir)
                shutil.copytree(self.backup_dir / "emails", self.emails_dir)
                self.logger.info("✅ Письма восстановлены")
            
            if (self.backup_dir / "attachments").exists():
                if self.attachments_dir.exists():
                    shutil.rmtree(self.attachments_dir)
                shutil.copytree(self.backup_dir / "attachments", self.attachments_dir)
                self.logger.info("✅ Вложения восстановлены")
            
            self.logger.info("✅ Миграция успешно отменена")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отката миграции: {e}")
            return False


if __name__ == "__main__":
    # Пример использования
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    migrator = AttachmentMigration(logger=logger)
    result = migrator.migrate_all_attachments()
    
    if result["status"] == "success":
        print("✅ Миграция успешно завершена")
        print(f"📊 Статистика: {result['stats']}")
    else:
        print(f"❌ Ошибка миграции: {result['message']}")