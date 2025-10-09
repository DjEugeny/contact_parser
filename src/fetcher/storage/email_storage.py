"""
EmailStorage - Хранение email данных.

Компонент для сохранения и обновления email данных с поддержкой
корректного маппинга вложений.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ...config.paths import DATA_DIR
from ..utils.date_utils import get_local_time


class EmailStorage:
    """
    Хранилище email данных с поддержкой message_id.
    
    Отвечает за:
    - Сохранение email данных в JSON
    - Обновление информации о вложениях
    - Поиск существующих писем по message_id
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Инициализация хранилища.
        
        Args:
            logger: Экземпляр логгера
        """
        self.logger = logger
        self.data_dir = DATA_DIR
        self.emails_dir = self.data_dir / "emails"
        self.emails_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("💾 EmailStorage инициализирован")
    
    def save_email(self, email_data: Dict) -> bool:
        """
        Сохранение email данных.
        
        Args:
            email_data: Данные письма
            
        Returns:
            True если успешно сохранено
        """
        try:
            date_folder = email_data.get("date_folder")
            if not date_folder:
                self.logger.error("❌ Отсутствует date_folder в данных письма")
                return False
            
            # Создаем директорию
            emails_date_dir = self.emails_dir / date_folder
            emails_date_dir.mkdir(exist_ok=True)
            
            # Генерируем имя файла
            email_filename = self._generate_email_filename(email_data, emails_date_dir)
            email_path = emails_date_dir / email_filename
            
            # Сохраняем данные
            with open(email_path, "w", encoding="utf-8") as f:
                json.dump(email_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ Сохранено: {email_filename}")
            self.logger.info(f"   Message-ID: {email_data.get('message_id', '')[:50]}...")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения письма: {e}")
            return False
    
    def update_email_attachments(
        self,
        message_id: str,
        date_folder: str,
        attachments: List[Dict],
        attachments_stats: Dict
    ) -> bool:
        """
        Обновление информации о вложениях в существующем письме.
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            attachments: Список вложений
            attachments_stats: Статистика вложений
            
        Returns:
            True если успешно обновлено
        """
        try:
            # Ищем существующий JSON файл по message_id
            json_file = self._find_email_by_message_id(message_id, date_folder)
            
            if not json_file:
                self.logger.warning(
                    f"⚠️ Не найден JSON файл для обновления вложений: {message_id}"
                )
                return False
            
            # Загружаем существующие данные
            with open(json_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            
            # Обновляем информацию о вложениях
            existing_data["attachments"] = attachments
            existing_data["attachments_stats"] = attachments_stats
            existing_data["processed_at"] = get_local_time().isoformat()
            
            # Сохраняем обновленные данные
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(
                f"✅ Обновлен JSON с вложениями: {json_file.name}"
            )
            self.logger.info(f"   Вложений: {attachments_stats.get('saved', 0)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления JSON с вложениями: {e}")
            return False
    
    def find_email_by_message_id(self, message_id: str, date_folder: str) -> Optional[Path]:
        """
        Поиск email файла по Message-ID.
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            
        Returns:
            Путь к файлу или None
        """
        return self._find_email_by_message_id(message_id, date_folder)
    
    def email_exists(self, message_id: str, date_folder: str) -> bool:
        """
        Проверка существования письма.
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            
        Returns:
            True если письмо существует
        """
        return self._find_email_by_message_id(message_id, date_folder) is not None
    
    def get_email_data(self, message_id: str, date_folder: str) -> Optional[Dict]:
        """
        Получение данных письма.
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            
        Returns:
            Данные письма или None
        """
        try:
            json_file = self._find_email_by_message_id(message_id, date_folder)
            
            if not json_file:
                return None
            
            with open(json_file, "r", encoding="utf-8") as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки письма: {e}")
            return None
    
    def list_emails_by_date(self, date_folder: str) -> List[Path]:
        """
        Список писем за дату.
        
        Args:
            date_folder: Папка даты
            
        Returns:
            Список путей к файлам писем
        """
        try:
            emails_date_dir = self.emails_dir / date_folder
            
            if not emails_date_dir.exists():
                return []
            
            return list(emails_date_dir.glob("email_*.json"))
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения списка писем: {e}")
            return []
    
    def get_storage_stats(self) -> Dict:
        """
        Получение статистики хранилища.
        
        Returns:
            Словарь со статистикой
        """
        try:
            stats = {
                "total_emails": 0,
                "total_dates": 0,
                "total_size_mb": 0,
                "dates": {},
            }
            
            if not self.emails_dir.exists():
                return stats
            
            # Обходим все папки с датами
            for date_dir in self.emails_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                date_str = date_dir.name
                email_files = list(date_dir.glob("email_*.json"))
                
                date_stats = {
                    "count": len(email_files),
                    "size_mb": 0,
                }
                
                # Считаем размер файлов
                for email_file in email_files:
                    try:
                        size = email_file.stat().st_size
                        date_stats["size_mb"] += size / (1024 * 1024)
                        stats["total_size_mb"] += size / (1024 * 1024)
                    except:
                        continue
                
                stats["dates"][date_str] = date_stats
                stats["total_emails"] += len(email_files)
                stats["total_dates"] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}
    
    def _generate_email_filename(self, email_data: Dict, emails_date_dir: Path) -> str:
        """
        Генерация имени файла для email.
        
        Args:
            email_data: Данные письма
            emails_date_dir: Директория с письмами
            
        Returns:
            Имя файла
        """
        # Извлекаем компоненты
        date_str = email_data.get("date_folder", "").replace("-", "")
        thread_id = email_data.get("thread_id", "unknown")
        message_id = email_data.get("message_id", "")
        
        # Находим следующий номер
        existing_files = list(emails_date_dir.glob("email_*.json"))
        next_num = len(existing_files) + 1
        
        # Генерируем имя файла
        filename = f"email_{next_num:03d}_{date_str}_{thread_id}.json"
        
        return filename
    
    def _find_email_by_message_id(self, message_id: str, date_folder: str) -> Optional[Path]:
        """
        Поиск email файла по Message-ID.
        
        Args:
            message_id: Message-ID письма
            date_folder: Папка даты
            
        Returns:
            Путь к файлу или None
        """
        try:
            emails_date_dir = self.emails_dir / date_folder
            
            if not emails_date_dir.exists():
                return None
            
            # Ищем в файлах
            json_files = list(emails_date_dir.glob("email_*.json"))
            
            for json_file in json_files:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        email_data = json.load(f)
                        stored_message_id = email_data.get("message_id", "")
                        
                        if stored_message_id == message_id:
                            return json_file
                            
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка проверки файла {json_file.name}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска письма: {e}")
            return None
    
    def cleanup_duplicates(self, date_folder: str) -> int:
        """
        Очистка дубликатов писем за дату.
        
        Args:
            date_folder: Папка даты
            
        Returns:
            Количество удаленных дубликатов
        """
        try:
            emails_date_dir = self.emails_dir / date_folder
            json_files = list(emails_date_dir.glob("email_*.json"))
            
            # Группируем по message_id
            message_groups = {}
            for json_file in json_files:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        email_data = json.load(f)
                        message_id = email_data.get("message_id", "")
                        
                        if message_id:
                            if message_id not in message_groups:
                                message_groups[message_id] = []
                            message_groups[message_id].append(json_file)
                except:
                    continue
            
            # Удаляем дубликаты (оставляем первый файл)
            removed_count = 0
            for message_id, files in message_groups.items():
                if len(files) > 1:
                    # Сортируем по времени модификации, оставляем самый новый
                    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    
                    # Удаляем все кроме первого
                    for duplicate_file in files[1:]:
                        try:
                            duplicate_file.unlink()
                            removed_count += 1
                            self.logger.info(f"🗑️ Удален дубликат: {duplicate_file.name}")
                        except Exception as e:
                            self.logger.error(f"❌ Ошибка удаления дубликата: {e}")
            
            if removed_count > 0:
                self.logger.info(f"🧹 Очистка завершена: удалено {removed_count} дубликатов")
            
            return removed_count
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка очистки дубликатов: {e}")
            return 0