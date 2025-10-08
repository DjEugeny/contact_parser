"""
📁 Attachment Scanner - Модуль для сканирования файловой структуры вложений

Этот модуль отвечает за обход директорий с вложениями и сбор информации о файлах.
"""

import os
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Generator
import logging

logger = logging.getLogger(__name__)


class AttachmentScanner:
    """Сканер директорий с вложениями электронной почты."""
    
    def __init__(self, base_directory: str = "data/attachments"):
        """
        Инициализация сканера.
        
        Args:
            base_directory: Базовая директория с вложениями
        """
        self.base_directory = Path(base_directory)
        self.supported_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'}
        
    def validate_directory(self) -> bool:
        """
        Проверка существования директории.
        
        Returns:
            True если директория существует, иначе False
        """
        if not self.base_directory.exists():
            logger.error(f"📂 Директория не существует: {self.base_directory}")
            return False
            
        if not self.base_directory.is_dir():
            logger.error(f"📂 Путь не является директорией: {self.base_directory}")
            return False
            
        logger.info(f"📂 Директория валидна: {self.base_directory}")
        return True
    
    def get_date_directories(self) -> List[Tuple[date, Path]]:
        """
        Получение списка директорий с датами.
        
        Returns:
            Список кортежей (дата, путь) для всех валидных директорий
        """
        date_dirs = []
        
        for item in self.base_directory.iterdir():
            if not item.is_dir():
                continue
                
            # Пропускаем служебные директории
            if item.name.startswith('.'):
                continue
                
            # Пытаемся распарсить дату из имени директории
            try:
                dir_date = datetime.strptime(item.name, "%Y-%m-%d").date()
                date_dirs.append((dir_date, item))
            except ValueError:
                logger.warning(f"⚠️ Пропуск директории с некорректной датой: {item.name}")
                continue
                
        # Сортируем по дате
        date_dirs.sort(key=lambda x: x[0])
        logger.info(f"📅 Найдено директорий с датами: {len(date_dirs)}")
        
        return date_dirs
    
    def get_files_in_directory(self, directory: Path, extensions: Optional[List[str]] = None) -> List[Path]:
        """
        Получение списка файлов в директории.
        
        Args:
            directory: Директория для сканирования
            extensions: Список разрешенных расширений (если None, используются поддерживаемые)
            
        Returns:
            Список путей к файлам
        """
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"⚠️ Директория не существует: {directory}")
            return []
            
        target_extensions = set(extensions) if extensions else self.supported_extensions
        files = []
        
        for item in directory.iterdir():
            if item.is_file() and item.suffix.lower() in target_extensions:
                files.append(item)
                
        logger.debug(f"📄 В директории {directory.name} найдено файлов: {len(files)}")
        return files
    
    def scan_date_range(
        self, 
        start_date: date, 
        end_date: date, 
        extensions: Optional[List[str]] = None
    ) -> Dict[date, List[Path]]:
        """
        Сканирование директорий в указанном диапазоне дат.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            extensions: Список разрешенных расширений файлов
            
        Returns:
            Словарь {дата: [список файлов]}
        """
        if start_date > end_date:
            logger.error("📅 Начальная дата не может быть позже конечной")
            return {}
            
        logger.info(f"🔍 Сканирование диапазона: {start_date} - {end_date}")
        
        date_dirs = self.get_date_directories()
        result = {}
        
        for dir_date, dir_path in date_dirs:
            if start_date <= dir_date <= end_date:
                files = self.get_files_in_directory(dir_path, extensions)
                if files:  # Добавляем только директории с файлами
                    result[dir_date] = files
                    
        total_files = sum(len(files) for files in result.values())
        logger.info(f"📊 Найдено файлов в диапазоне: {total_files}")
        
        return result
    
    def scan_all_dates(self, extensions: Optional[List[str]] = None) -> Dict[date, List[Path]]:
        """
        Сканирование всех доступных дат.
        
        Args:
            extensions: Список разрешенных расширений файлов
            
        Returns:
            Словарь {дата: [список файлов]}
        """
        logger.info("🔍 Сканирование всех доступных дат")
        
        date_dirs = self.get_date_directories()
        result = {}
        
        for dir_date, dir_path in date_dirs:
            files = self.get_files_in_directory(dir_path, extensions)
            if files:  # Добавляем только директории с файлами
                result[dir_date] = files
                
        total_files = sum(len(files) for files in result.values())
        logger.info(f"📊 Всего найдено файлов: {total_files}")
        
        return result
    
    def get_directory_info(self) -> Dict[str, any]:
        """
        Получение общей информации о директории с вложениями.
        
        Returns:
            Словарь с информацией о директории
        """
        if not self.validate_directory():
            return {}
            
        date_dirs = self.get_date_directories()
        
        if not date_dirs:
            return {"error": "Директории с датами не найдены"}
            
        # Считаем статистику
        total_files = 0
        extension_counts = {}
        date_range = {"start": date_dirs[0][0], "end": date_dirs[-1][0]}
        
        for dir_date, dir_path in date_dirs:
            files = self.get_files_in_directory(dir_path)
            total_files += len(files)
            
            for file_path in files:
                ext = file_path.suffix.lower()
                extension_counts[ext] = extension_counts.get(ext, 0) + 1
                
        return {
            "base_directory": str(self.base_directory),
            "date_directories_count": len(date_dirs),
            "date_range": date_range,
            "total_files": total_files,
            "file_types": extension_counts
        }
    
    def get_files_by_extension(
        self, 
        start_date: date, 
        end_date: date, 
        extension: str
    ) -> Dict[date, List[Path]]:
        """
        Получение файлов определенного типа в диапазоне дат.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            extension: Расширение файла (например, '.pdf')
            
        Returns:
            Словарь {дата: [список файлов]}
        """
        if not extension.startswith('.'):
            extension = '.' + extension
            
        return self.scan_date_range(start_date, end_date, [extension])