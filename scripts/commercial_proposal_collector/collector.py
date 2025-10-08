"""
📁 File Collector - Модуль для сбора и копирования файлов

Этот модуль отвечает за копирование найденных коммерческих предложений в целевую директорию.
"""

import os
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FileCollector:
    """Коллектор файлов для копирования коммерческих предложений."""
    
    def __init__(self, target_directory: str = "data/collected_proposals"):
        """
        Инициализация коллектора.
        
        Args:
            target_directory: Целевая директория для сбора файлов
        """
        self.target_directory = Path(target_directory)
        self.copied_files = []
        self.failed_copies = []
        self.total_size_copied = 0
        
    def ensure_target_directory(self) -> bool:
        """
        Создание целевой директории если она не существует.
        
        Returns:
            True если директория существует или создана успешно
        """
        try:
            self.target_directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Целевая директория готова: {self.target_directory}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка создания директории {self.target_directory}: {e}")
            return False
    
    def create_period_subdirectory(self, period_name: str) -> Path:
        """
        Создание подпапки для периода.
        
        Args:
            period_name: Название периода (например, "2025-Q3")
            
        Returns:
            Путь к созданной подпапке
        """
        subdirectory = self.target_directory / period_name
        
        try:
            subdirectory.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Создана подпапка периода: {subdirectory}")
            return subdirectory
        except Exception as e:
            logger.error(f"❌ Ошибка создания подпапки {subdirectory}: {e}")
            return self.target_directory
    
    def create_date_subdirectory(self, period_path: Path, file_date: date) -> Path:
        """
        Создание подпапки для конкретной даты.
        
        Args:
            period_path: Путь к папке периода
            file_date: Дата файлов
            
        Returns:
            Путь к созданной подпапке даты
        """
        date_str = file_date.strftime("%Y-%m-%d")
        date_subdirectory = period_path / date_str
        
        try:
            date_subdirectory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"📁 Создана подпапка даты: {date_subdirectory}")
            return date_subdirectory
        except Exception as e:
            logger.error(f"❌ Ошибка создания подпапки даты {date_subdirectory}: {e}")
            return period_path
    
    def copy_file(self, source: Path, target: Path, preserve_structure: bool = True) -> Tuple[bool, str]:
        """
        Копирование файла с обработкой конфликтов имен.
        
        Args:
            source: Исходный файл
            target: Целевой путь
            preserve_structure: Сохранять ли структуру подпапок по датам
            
        Returns:
            Кортеж (успех, сообщение)
        """
        if not source.exists():
            error_msg = f"Исходный файл не существует: {source}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
            
        try:
            # Обработка конфликтов имен
            if target.exists():
                base_name = target.stem
                extension = target.suffix
                counter = 1
                
                while target.exists():
                    new_name = f"{base_name}_copy{counter}{extension}"
                    target = target.parent / new_name
                    counter += 1
                
                logger.info(f"🔄 Файл переименован для избежания конфликта: {target.name}")
            
            # Копирование файла
            shutil.copy2(source, target)
            file_size = target.stat().st_size
            self.total_size_copied += file_size
            
            success_msg = f"Файл скопирован: {source.name} -> {target}"
            logger.info(f"✅ {success_msg}")
            
            self.copied_files.append({
                'source': source,
                'target': target,
                'size_bytes': file_size,
                'timestamp': datetime.now()
            })
            
            return True, success_msg
            
        except Exception as e:
            error_msg = f"Ошибка копирования файла {source.name}: {e}"
            logger.error(f"❌ {error_msg}")
            
            self.failed_copies.append({
                'source': source,
                'target': target,
                'error': str(e),
                'timestamp': datetime.now()
            })
            
            return False, error_msg
    
    def copy_proposals(
        self, 
        proposals_by_date: Dict[date, List[Dict]], 
        period_name: str,
        create_date_subfolders: bool = True
    ) -> Dict[str, int]:
        """
        Копирование всех найденных предложений.
        
        Args:
            proposals_by_date: Словарь {дата: [список предложений]}
            period_name: Название периода
            create_date_subfolders: Создавать ли подпапки по датам
            
        Returns:
            Статистика копирования
        """
        if not self.ensure_target_directory():
            return {'total': 0, 'success': 0, 'failed': 0}
            
        period_path = self.create_period_subdirectory(period_name)
        
        total_files = 0
        success_count = 0
        failed_count = 0
        
        for file_date, proposals in proposals_by_date.items():
            if not proposals:
                continue
                
            # Определяем целевую директорию
            if create_date_subfolders:
                target_dir = self.create_date_subdirectory(period_path, file_date)
            else:
                target_dir = period_path
                
            logger.info(f"📂 Обработка даты {file_date}: {len(proposals)} файлов")
            
            for proposal in proposals:
                source_path = proposal['file_path']
                target_path = target_dir / source_path.name
                
                total_files += 1
                success, _ = self.copy_file(source_path, target_path)
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
        
        stats = {
            'total': total_files,
            'success': success_count,
            'failed': failed_count,
            'total_size_mb': round(self.total_size_copied / (1024 * 1024), 2)
        }
        
        logger.info(f"📊 Статистика копирования: {stats}")
        return stats
    
    def copy_proposals_flat(
        self, 
        proposals_by_date: Dict[date, List[Dict]], 
        period_name: str
    ) -> Dict[str, int]:
        """
        Копирование всех найденных предложений в одну папку (без подпапок по датам).
        
        Args:
            proposals_by_date: Словарь {дата: [список предложений]}
            period_name: Название периода
            
        Returns:
            Статистика копирования
        """
        if not self.ensure_target_directory():
            return {'total': 0, 'success': 0, 'failed': 0}
            
        period_path = self.create_period_subdirectory(period_name)
        
        total_files = 0
        success_count = 0
        failed_count = 0
        
        logger.info(f"📂 Копирование всех файлов в одну папку: {period_path}")
        
        for file_date, proposals in proposals_by_date.items():
            if not proposals:
                continue
                
            logger.info(f"📂 Обработка даты {file_date}: {len(proposals)} файлов")
            
            for proposal in proposals:
                source_path = proposal['file_path']
                target_path = period_path / source_path.name
                
                total_files += 1
                success, _ = self.copy_file(source_path, target_path)
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
        
        stats = {
            'total': total_files,
            'success': success_count,
            'failed': failed_count,
            'total_size_mb': round(self.total_size_copied / (1024 * 1024), 2)
        }
        
        logger.info(f"📊 Статистика копирования: {stats}")
        return stats
    
    def copy_single_proposal(
        self, 
        proposal: Dict, 
        period_name: str,
        file_date: Optional[date] = None,
        create_date_subfolder: bool = True
    ) -> Tuple[bool, str]:
        """
        Копирование одного предложения.
        
        Args:
            proposal: Информация о предложении
            period_name: Название периода
            file_date: Дата файла (если нет, берется из метаданных)
            create_date_subfolder: Создавать ли подпапку по дате
            
        Returns:
            Кортеж (успех, сообщение)
        """
        if not self.ensure_target_directory():
            return False, "Не удалось создать целевую директорию"
            
        period_path = self.create_period_subdirectory(period_name)
        
        # Определяем целевую директорию
        if create_date_subfolder:
            # Определяем дату
            if file_date is None:
                # Пытаемся извлечь дату из пути к файлу
                try:
                    file_date = datetime.strptime(proposal['file_path'].parent.name, "%Y-%m-%d").date()
                except ValueError:
                    file_date = date.today()
            
            target_dir = self.create_date_subdirectory(period_path, file_date)
        else:
            target_dir = period_path
        
        target_path = target_dir / proposal['file_path'].name
        
        return self.copy_file(proposal['file_path'], target_path)
    
    def generate_copy_report(self) -> str:
        """
        Генерация отчета о копировании.
        
        Returns:
            Текст отчета
        """
        report_lines = [
            "ОТЧЕТ О КОПИРОВАНИИ ФАЙЛОВ",
            "=" * 50,
            f"Целевая директория: {self.target_directory}",
            f"Время выполнения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Всего файлов обработано: {len(self.copied_files) + len(self.failed_copies)}",
            f"Успешно скопировано: {len(self.copied_files)}",
            f"Ошибок копирования: {len(self.failed_copies)}",
            f"Общий размер скопированных файлов: {round(self.total_size_copied / (1024 * 1024), 2)} МБ",
            ""
        ]
        
        if self.copied_files:
            report_lines.extend([
                "УСПЕШНО СКОПИРОВАННЫЕ ФАЙЛЫ:",
                "-" * 30
            ])
            
            for file_info in self.copied_files:
                source_name = file_info['source'].name
                target_path = file_info['target']
                size_mb = round(file_info['size_bytes'] / (1024 * 1024), 2)
                report_lines.append(f"✅ {source_name} -> {target_path.parent.name}/ ({size_mb} МБ)")
            
            report_lines.append("")
        
        if self.failed_copies:
            report_lines.extend([
                "ОШИБКИ КОПИРОВАНИЯ:",
                "-" * 20
            ])
            
            for file_info in self.failed_copies:
                source_name = file_info['source'].name
                error = file_info['error']
                report_lines.append(f"❌ {source_name}: {error}")
            
            report_lines.append("")
        
        report_lines.extend([
            "СТАТИСТИКА ПО ДАТАМ:",
            "-" * 20
        ])
        
        # Группировка по датам
        date_stats = {}
        for file_info in self.copied_files:
            date_str = file_info['target'].parent.name
            date_stats[date_str] = date_stats.get(date_str, 0) + 1
        
        for date_str, count in sorted(date_stats.items()):
            report_lines.append(f"📅 {date_str}: {count} файлов")
        
        return "\n".join(report_lines)
    
    def save_report(self, period_name: str) -> Optional[Path]:
        """
        Сохранение отчета в файл.
        
        Args:
            period_name: Название периода
            
        Returns:
            Путь к файлу отчета или None в случае ошибки
        """
        if not self.ensure_target_directory():
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"report_{period_name}_{timestamp}.txt"
        report_path = self.target_directory / report_filename
        
        try:
            report_content = self.generate_copy_report()
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"📄 Отчет сохранен: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения отчета: {e}")
            return None
    
    def clear_statistics(self):
        """Очистка статистики копирования."""
        self.copied_files = []
        self.failed_copies = []
        self.total_size_copied = 0
        logger.info("📊 Статистика копирования очищена")
    
    def get_target_directory_info(self) -> Dict:
        """
        Получение информации о целевой директории.
        
        Returns:
            Словарь с информацией
        """
        if not self.target_directory.exists():
            return {"exists": False}
            
        total_size = 0
        file_count = 0
        dir_count = 0
        
        for item in self.target_directory.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
            elif item.is_dir():
                dir_count += 1
                
        return {
            "exists": True,
            "path": str(self.target_directory),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "directory_count": dir_count,
            "last_session_copied": len(self.copied_files),
            "last_session_failed": len(self.failed_copies)
        }