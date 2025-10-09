#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Адаптер для OCR Processor, обеспечивающий совместимость с новым реестром вложений
"""

import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import logging

# Импортируем реестр вложений
from ..attachment_registry.attachment_registry_spec import AttachmentRegistry


class OCRProcessorAdapter:
    """
    Адаптер для OCR Processor, обеспечивающий совместимость с новым реестром вложений.
    
    Решает проблему, когда изменение схемы именования вложений может сделать 
    существующий кэш OCR-файлов невалидным.
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
        
        # Директории для OCR результатов
        self.ocr_results_dir = data_dir / "ocr_results"
        self.ocr_results_dir.mkdir(parents=True, exist_ok=True)
        
        # Кэш для результатов OCR
        self._ocr_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 600  # 10 минут
    
    def find_attachment_for_email(self, message_id: str, attachment_filename: str) -> Optional[Path]:
        """
        Поиск вложения для конкретного письма с использованием реестра
        
        Args:
            message_id: Уникальный идентификатор письма
            attachment_filename: Имя файла вложения
            
        Returns:
            Путь к файлу вложения или None, если не найдено
        """
        if not message_id or not attachment_filename:
            self.logger.warning("message_id или attachment_filename не указаны")
            return None
        
        # Сначала ищем в реестре
        attachments = self.attachment_registry.get_attachments_by_message(message_id)
        
        for attachment in attachments:
            if attachment.get("attachment_filename") == attachment_filename:
                attachment_path = Path(attachment.get("attachment_path"))
                if attachment_path.exists():
                    return attachment_path
                else:
                    self.logger.warning(f"Файл вложения не найден: {attachment_path}")
        
        # Fallback к старому поиску, если не найдено в реестре
        self.logger.info(f"Вложение не найдено в реестре, пытаюсь найти по старой схеме")
        return self._find_attachment_legacy(message_id, attachment_filename)
    
    def _find_attachment_legacy(self, message_id: str, attachment_filename: str) -> Optional[Path]:
        """
        Поиск вложения по старой схеме (fallback)
        
        Args:
            message_id: Уникальный идентификатор письма
            attachment_filename: Имя файла вложения
            
        Returns:
            Путь к файлу вложения или None, если не найдено
        """
        # Извлекаем thread_id из message_id (если возможно)
        thread_id = self._extract_thread_id_from_message_id(message_id)
        
        if not thread_id:
            return None
        
        # Ищем в директориях вложений
        attachments_dir = self.data_dir / "attachments"
        
        for date_dir in attachments_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            # Ищем файлы, содержащие thread_id в имени
            for attachment_file in date_dir.glob(f"*{thread_id}*{attachment_filename}"):
                if attachment_file.is_file():
                    self.logger.info(f"Найдено вложение по старой схеме: {attachment_file}")
                    return attachment_file
        
        return None
    
    def _extract_thread_id_from_message_id(self, message_id: str) -> Optional[str]:
        """
        Извлечение thread_id из message_id
        
        Args:
            message_id: Уникальный идентификатор письма
            
        Returns:
            thread_id или None, если не удалось извлечь
        """
        # Это упрощенная логика, в реальном сценарии может потребоваться
        # более сложное извлечение thread_id из message_id или поиск в JSON файлах
        
        # Пытаемся найти JSON файл с таким message_id
        emails_dir = self.data_dir / "emails"
        
        for date_dir in emails_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            for email_file in date_dir.glob("*.json"):
                try:
                    with open(email_file, 'r', encoding='utf-8') as f:
                        email_data = json.load(f)
                    
                    if email_data.get("message_id") == message_id:
                        return email_data.get("thread_id")
                
                except (json.JSONDecodeError, IOError):
                    continue
        
        return None
    
    def check_existing_results(self, file_path: Path, date: str, message_id: str = None) -> bool:
        """
        Обновленный метод проверки существующих результатов с использованием реестра
        
        Args:
            file_path: Путь к файлу вложения
            date: Дата письма
            message_id: Уникальный идентификатор письма
            
        Returns:
            True если результаты существуют
        """
        if message_id:
            # Используем реестр для определения правильного вложения
            attachment = self.attachment_registry.find_attachment_file(message_id, file_path.name)
            if attachment:
                # Проверяем существование результатов на основе attachment_id
                attachment_info = self.attachment_registry.get_attachments_by_message(message_id)
                for att in attachment_info:
                    if att.get("attachment_filename") == file_path.name:
                        attachment_id = att.get("attachment_id")
                        return self._check_existing_results_by_id(attachment_id, date)
        
        # Fallback к старой логике, если message_id не определен
        return self._check_existing_results_legacy(file_path, date)
    
    def _check_existing_results_by_id(self, attachment_id: str, date: str) -> bool:
        """
        Проверка результатов по attachment_id
        
        Args:
            attachment_id: Уникальный ID вложения
            date: Дата письма
            
        Returns:
            True если результаты существуют
        """
        if not attachment_id:
            return False
        
        # Проверяем существование результатов по attachment_id
        results_path = self.ocr_results_dir / date / f"{attachment_id}.json"
        
        if results_path.exists():
            self.logger.debug(f"Найдены существующие результаты OCR: {results_path}")
            return True
        
        return False
    
    def _check_existing_results_legacy(self, file_path: Path, date: str) -> bool:
        """
        Легаси проверка для обратной совместимости
        
        Args:
            file_path: Путь к файлу вложения
            date: Дата письма
            
        Returns:
            True если результаты существуют
        """
        # Старая логика проверки на основе имени файла
        results_path = self.ocr_results_dir / date / f"{file_path.stem}_ocr.json"
        
        if results_path.exists():
            self.logger.debug(f"Найдены существующие результаты OCR (legacy): {results_path}")
            return True
        
        return False
    
    def save_ocr_results(self, file_path: Path, date: str, ocr_results: Dict, 
                        message_id: str = None) -> bool:
        """
        Сохранение результатов OCR с поддержкой нового формата
        
        Args:
            file_path: Путь к файлу вложения
            date: Дата письма
            ocr_results: Результаты OCR
            message_id: Уникальный идентификатор письма
            
        Returns:
            True если успешно сохранено
        """
        try:
            # Создаем директорию для результатов
            date_dir = self.ocr_results_dir / date
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Определяем имя файла результатов
            if message_id:
                # Используем attachment_id для имени файла
                attachment_info = self.attachment_registry.find_attachment_file(message_id, file_path.name)
                if attachment_info:
                    attachments = self.attachment_registry.get_attachments_by_message(message_id)
                    for att in attachments:
                        if att.get("attachment_filename") == file_path.name:
                            attachment_id = att.get("attachment_id")
                            results_filename = f"{attachment_id}.json"
                            break
                    else:
                        # Fallback к старому формату
                        results_filename = f"{file_path.stem}_ocr.json"
                else:
                    results_filename = f"{file_path.stem}_ocr.json"
            else:
                # Старый формат
                results_filename = f"{file_path.stem}_ocr.json"
            
            results_path = date_dir / results_filename
            
            # Добавляем метаданные к результатам
            enhanced_results = {
                "ocr_data": ocr_results,
                "metadata": {
                    "source_file": str(file_path),
                    "processed_at": datetime.now().isoformat(),
                    "message_id": message_id,
                    "attachment_filename": file_path.name,
                    "processor_version": "2.0"
                }
            }
            
            # Сохраняем результаты
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_results, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Результаты OCR сохранены: {results_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения результатов OCR: {e}")
            return False
    
    def load_ocr_results(self, file_path: Path, date: str, message_id: str = None) -> Optional[Dict]:
        """
        Загрузка результатов OCR с поддержкой нового формата
        
        Args:
            file_path: Путь к файлу вложения
            date: Дата письма
            message_id: Уникальный идентификатор письма
            
        Returns:
            Результаты OCR или None, если не найдены
        """
        try:
            # Проверяем существование результатов
            if not self.check_existing_results(file_path, date, message_id):
                return None
            
            # Определяем путь к файлу результатов
            if message_id:
                # Используем attachment_id для имени файла
                attachments = self.attachment_registry.get_attachments_by_message(message_id)
                for att in attachments:
                    if att.get("attachment_filename") == file_path.name:
                        attachment_id = att.get("attachment_id")
                        results_path = self.ocr_results_dir / date / f"{attachment_id}.json"
                        break
                else:
                    # Fallback к старому формату
                    results_path = self.ocr_results_dir / date / f"{file_path.stem}_ocr.json"
            else:
                # Старый формат
                results_path = self.ocr_results_dir / date / f"{file_path.stem}_ocr.json"
            
            # Загружаем результаты
            with open(results_path, 'r', encoding='utf-8') as f:
                results_data = json.load(f)
            
            # Возвращаем данные в зависимости от формата
            if "ocr_data" in results_data:
                # Новый формат
                return results_data["ocr_data"]
            else:
                # Старый формат
                return results_data
                
        except Exception as e:
            self.logger.error(f"Ошибка загрузки результатов OCR: {e}")
            return None
    
    def get_ocr_statistics(self) -> Dict:
        """
        Получение статистики OCR
        
        Returns:
            Статистика обработки OCR
        """
        stats = {
            "total_processed": 0,
            "total_cached": 0,
            "total_size_mb": 0,
            "by_date": {},
            "by_type": {}
        }
        
        # Проходим по всем директориям с результатами
        for date_dir in self.ocr_results_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            date = date_dir.name
            stats["by_date"][date] = {
                "count": 0,
                "size_mb": 0
            }
            
            for results_file in date_dir.glob("*.json"):
                try:
                    file_size = results_file.stat().st_size
                    
                    stats["total_processed"] += 1
                    stats["total_size_mb"] += file_size / (1024 * 1024)
                    stats["by_date"][date]["count"] += 1
                    stats["by_date"][date]["size_mb"] += file_size / (1024 * 1024)
                    
                    # Определяем тип файла
                    if results_file.stem.endswith("_ocr"):
                        file_type = "legacy"
                    else:
                        file_type = "registry"
                    
                    stats["by_type"][file_type] = stats["by_type"].get(file_type, 0) + 1
                    
                except (OSError, AttributeError):
                    continue
        
        # Округляем значения
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        
        for date_data in stats["by_date"].values():
            date_data["size_mb"] = round(date_data["size_mb"], 2)
        
        return stats
    
    def cleanup_orphaned_results(self) -> Dict[str, int]:
        """
        Очистка результатов OCR для несуществующих вложений
        
        Returns:
            Статистика очистки
        """
        cleaned_count = 0
        total_size_freed = 0
        
        # Получаем все существующие вложения из реестра
        existing_attachments = set()
        for attachment_info in self.attachment_registry.registry["attachments"].values():
            attachment_path = Path(attachment_info.get("attachment_path"))
            if attachment_path.exists():
                existing_attachments.add(attachment_path.name)
        
        # Проходим по всем результатам OCR
        for date_dir in self.ocr_results_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            for results_file in date_dir.glob("*.json"):
                try:
                    # Определяем имя файла вложения
                    if results_file.stem.endswith("_ocr"):
                        # Старый формат
                        attachment_filename = results_file.stem[:-4] + ".pdf"  # Предполагаем PDF
                    else:
                        # Новый формат - ищем по attachment_id
                        attachment_id = results_file.stem
                        attachment_info = self.attachment_registry.get_attachment_info(attachment_id)
                        if attachment_info:
                            attachment_filename = attachment_info.get("attachment_filename")
                        else:
                            # Не удалось определить вложение
                            continue
                    
                    # Проверяем существует ли вложение
                    if attachment_filename not in existing_attachments:
                        file_size = results_file.stat().st_size
                        results_file.unlink()
                        cleaned_count += 1
                        total_size_freed += file_size
                        
                        self.logger.debug(f"Удален результат OCR для несуществующего вложения: {results_file}")
                
                except (OSError, AttributeError):
                    continue
        
        self.logger.info(f"Очистка результатов OCR: удалено {cleaned_count} файлов, освобождено {total_size_freed} байт")
        
        return {
            "cleaned_count": cleaned_count,
            "total_size_freed": total_size_freed,
            "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2)
        }


def test_ocr_adapter():
    """Тестирование адаптера OCR"""
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        
        # Создаем тестовую структуру
        (data_dir / "attachments" / "2025-07-23").mkdir(parents=True)
        (data_dir / "emails" / "2025-07-23").mkdir(parents=True)
        
        # Создаем тестовое вложение
        test_attachment = data_dir / "attachments" / "2025-07-23" / "test_document.pdf"
        test_attachment.write_bytes(b"test pdf content")
        
        # Создаем тестовое письмо
        test_email = {
            "message_id": "test-message-123",
            "thread_id": "test-thread-456",
            "subject": "Test Email"
        }
        
        test_email_file = data_dir / "emails" / "2025-07-23" / "email_001.json"
        with open(test_email_file, 'w', encoding='utf-8') as f:
            json.dump(test_email, f)
        
        # Инициализируем адаптер
        adapter = OCRProcessorAdapter(data_dir)
        
        # Регистрируем вложение
        attachment_id = adapter.attachment_registry.register_attachment(
            message_id="test-message-123",
            attachment_filename="test_document.pdf",
            attachment_path=str(test_attachment),
            thread_id="test-thread-456",
            file_size=len(b"test pdf content"),
            content_type="application/pdf"
        )
        
        # Тестируем поиск вложения
        found_attachment = adapter.find_attachment_for_email("test-message-123", "test_document.pdf")
        print(f"Найдено вложение: {found_attachment}")
        
        # Тестируем проверку результатов
        has_results = adapter.check_existing_results(test_attachment, "2025-07-23", "test-message-123")
        print(f"Существуют результаты OCR: {has_results}")
        
        # Тестируем сохранение результатов
        ocr_results = {"text": "extracted text from pdf", "confidence": 0.95}
        saved = adapter.save_ocr_results(test_attachment, "2025-07-23", ocr_results, "test-message-123")
        print(f"Результаты сохранены: {saved}")
        
        # Тестируем загрузку результатов
        loaded_results = adapter.load_ocr_results(test_attachment, "2025-07-23", "test-message-123")
        print(f"Загруженные результаты: {loaded_results}")
        
        # Получаем статистику
        stats = adapter.get_ocr_statistics()
        print(f"Статистика OCR: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    test_ocr_adapter()