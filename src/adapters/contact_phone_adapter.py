#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Адаптер для Contact Phone Enrichment, обеспечивающий совместимость с новым реестром вложений
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Импортируем реестр вложений
from ..attachment_registry_spec import AttachmentRegistry


class ContactPhoneAdapter:
    """
    Адаптер для Contact Phone Enrichment с поддержкой реестра вложений.
    
    Обеспечивает корректное извлечение номеров телефонов из вложений,
    принадлежащих конкретному письму.
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
        self.contacts_dir = data_dir / "contacts"
        self.contacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Паттерны для поиска телефонов
        self.phone_patterns = [
            # Российские номера
            r'\+7\s*\(?(\d{3})\)?\s*(\d{3})[-\s]?(\d{2})[-\s]?(\d{2})',
            r'8\s*\(?(\d{3})\)?\s*(\d{3})[-\s]?(\d{2})[-\s]?(\d{2})',
            
            # Международные номера
            r'\+\d{1,3}\s*\(?(\d{1,3})\)?\s*(\d{1,4})[-\s]?(\d{1,4})[-\s]?(\d{1,4})',
            
            # Короткие номера
            r'\b\d{2,4}[-\s]?\d{2,4}\b',
            
            # Форматы с пробелами
            r'\b\d{1}\s\d{3}\s\d{3}\s\d{2}\s\d{2}\b',
            r'\b\d{1}\s\d{3}\s\d{2}\s\d{2}\b',
        ]
        
        # Кэш для результатов извлечения
        self._extraction_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 600  # 10 минут
    
    def find_attachments_for_contact(self, message_id: str, contact_name: str = None) -> List[Dict]:
        """
        Поиск вложений для конкретного контакта с использованием реестра
        
        Args:
            message_id: Уникальный идентификатор письма
            contact_name: Имя контакта для дополнительной фильтрации
            
        Returns:
            Список информации о вложениях для контакта
        """
        if not message_id:
            self.logger.warning("message_id не указан")
            return []
        
        attachments = self.attachment_registry.get_attachments_by_message(message_id)
        
        # Фильтруем вложения по типу (только документы и изображения)
        filtered_attachments = []
        for attachment in attachments:
            content_type = attachment.get("content_type", "")
            filename = attachment.get("attachment_filename", "")
            
            # Проверяем, что вложение подходит для извлечения телефонов
            if self._is_phone_extractable(content_type, filename):
                filtered_attachments.append(attachment)
        
        # Дополнительная фильтрация по имени контакта, если указано
        if contact_name:
            # Проверяем, есть ли имя контакта в имени файла
            contact_name_safe = re.sub(r'[^\w\s]', '', contact_name.lower())
            filtered_attachments = [
                att for att in filtered_attachments 
                if contact_name_safe in re.sub(r'[^\w\s]', '', att.get("attachment_filename", "").lower())
            ]
        
        return filtered_attachments
    
    def extract_phones_from_attachment(self, attachment_info: Dict) -> Dict:
        """
        Извлечение номеров телефонов из вложения
        
        Args:
            attachment_info: Информация о вложении
            
        Returns:
            Результаты извлечения телефонов
        """
        attachment_path = Path(attachment_info.get("attachment_path"))
        attachment_id = attachment_info.get("attachment_id")
        
        # Проверяем кэш
        cache_key = f"{attachment_id}_{attachment_path.stat().st_size}"
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        result = {
            "attachment_id": attachment_id,
            "attachment_path": str(attachment_path),
            "attachment_filename": attachment_info.get("attachment_filename"),
            "content_type": attachment_info.get("content_type"),
            "phones": [],
            "extraction_method": None,
            "extraction_time": None,
            "error": None
        }
        
        try:
            if attachment_path.exists():
                content_type = attachment_info.get("content_type", "")
                
                if content_type.startswith("image/"):
                    # Извлечение из изображения через OCR
                    phones = self._extract_phones_from_image(attachment_path)
                    result["extraction_method"] = "ocr"
                elif content_type == "text/plain":
                    # Извлечение из текстового файла
                    phones = self._extract_phones_from_text(attachment_path)
                    result["extraction_method"] = "text"
                elif content_type in ["application/pdf", "application/msword", 
                                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                    # Извлечение из документа
                    phones = self._extract_phones_from_document(attachment_path, content_type)
                    result["extraction_method"] = "document"
                else:
                    # Другие форматы не поддерживаются
                    result["error"] = f"Unsupported content type: {content_type}"
                
                result["phones"] = phones
                result["extraction_time"] = datetime.now().isoformat()
                
                # Сохраняем в кэш
                self._save_to_cache(cache_key, result)
                
            else:
                result["error"] = "Attachment file not found"
                
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"Ошибка извлечения телефонов из {attachment_path}: {e}")
        
        return result
    
    def _is_phone_extractable(self, content_type: str, filename: str) -> bool:
        """
        Проверка, подходит ли вложение для извлечения телефонов
        
        Args:
            content_type: MIME-тип файла
            filename: Имя файла
            
        Returns:
            True если подходит для извлечения
        """
        # Изображения (для OCR)
        if content_type.startswith("image/"):
            return True
        
        # Текстовые документы
        if content_type in ["text/plain"]:
            return True
        
        # PDF и Word документы
        if content_type in ["application/pdf", "application/msword", 
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return True
        
        # Проверка по расширению
        ext = Path(filename).suffix.lower()
        if ext in [".txt", ".pdf", ".doc", ".docx"]:
            return True
        
        return False
    
    def _extract_phones_from_image(self, image_path: Path) -> List[str]:
        """
        Извлечение телефонов из изображения через OCR
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Список найденных номеров телефонов
        """
        try:
            # Импортируем OCR Processor
            from ..ocr_processor import OCRProcessor
            
            # Создаем OCR процессор
            ocr_processor = OCRProcessor(self.logger)
            
            # Извлекаем текст из изображения
            text = ocr_processor.extract_text_from_image(image_path)
            
            # Ищем телефоны в тексте
            phones = self._find_phones_in_text(text)
            
            self.logger.debug(f"Извлечено {len(phones)} телефонов из изображения {image_path}")
            return phones
            
        except ImportError:
            self.logger.warning("OCR Processor недоступен, пропускаем извлечение из изображения")
            return []
        except Exception as e:
            self.logger.error(f"Ошибка OCR для {image_path}: {e}")
            return []
    
    def _extract_phones_from_text(self, text_path: Path) -> List[str]:
        """
        Извлечение телефонов из текстового файла
        
        Args:
            text_path: Путь к текстовому файлу
            
        Returns:
            Список найденных номеров телефонов
        """
        try:
            # Определяем кодировку
            encodings = ['utf-8', 'cp1251', 'latin-1']
            text = None
            
            for encoding in encodings:
                try:
                    with open(text_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if text is None:
                self.logger.warning(f"Не удалось прочитать файл {text_path}")
                return []
            
            # Ищем телефоны в тексте
            phones = self._find_phones_in_text(text)
            
            self.logger.debug(f"Извлечено {len(phones)} телефонов из текста {text_path}")
            return phones
            
        except Exception as e:
            self.logger.error(f"Ошибка чтения текста из {text_path}: {e}")
            return []
    
    def _extract_phones_from_document(self, doc_path: Path, content_type: str) -> List[str]:
        """
        Извлечение телефонов из документа
        
        Args:
            doc_path: Путь к файлу документа
            content_type: MIME-тип документа
            
        Returns:
            Список найденных номеров телефонов
        """
        try:
            # Импортируем OCR Processor для документов
            from ..ocr_processor import OCRProcessor
            
            # Создаем OCR процессор
            ocr_processor = OCRProcessor(self.logger)
            
            # Извлекаем текст из документа
            text = ocr_processor.extract_text_from_document(doc_path, content_type)
            
            # Ищем телефоны в тексте
            phones = self._find_phones_in_text(text)
            
            self.logger.debug(f"Извлечено {len(phones)} телефонов из документа {doc_path}")
            return phones
            
        except ImportError:
            self.logger.warning("OCR Processor недоступен, пропускаем извлечение из документа")
            return []
        except Exception as e:
            self.logger.error(f"Ошибка OCR для {doc_path}: {e}")
            return []
    
    def _find_phones_in_text(self, text: str) -> List[str]:
        """
        Поиск номеров телефонов в тексте
        
        Args:
            text: Текст для поиска
            
        Returns:
            Список найденных номеров телефонов
        """
        phones = []
        seen_phones = set()  # Для исключения дубликатов
        
        for pattern in self.phone_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    if match.groups():
                        # Форматированная группа (скобки)
                        phone = ''.join(match.groups())
                    else:
                        # Полное совпадение
                        phone = match.group(0)
                    
                    # Нормализуем номер телефона
                    normalized_phone = self._normalize_phone(phone)
                    
                    if normalized_phone and normalized_phone not in seen_phones:
                        phones.append(normalized_phone)
                        seen_phones.add(normalized_phone)
                        
                except (IndexError, AttributeError):
                    continue
        
        return phones
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Нормализация номера телефона
        
        Args:
            phone: Сырой номер телефона
            
        Returns:
            Нормализованный номер телефона или None
        """
        # Удаляем все нецифровые символы, кроме + и пробелов
        cleaned = re.sub(r'[^\d+\s]', '', phone)
        
        # Удаляем лишние пробелы
        cleaned = re.sub(r'\s+', '', cleaned)
        
        # Проверяем минимальную длину
        if len(cleaned) < 7:
            return None
        
        # Нормализуем российские номера
        if cleaned.startswith('8') and len(cleaned) == 11:
            # Заменяем 8 на +7
            cleaned = '+7' + cleaned[1:]
        elif not cleaned.startswith('+') and len(cleaned) == 10:
            # Добавляем +7 для российских номеров
            cleaned = '+7' + cleaned
        
        return cleaned
    
    def enrich_contact_with_phones(self, message_id: str, contact_info: Dict) -> Dict:
        """
        Обогащение информации о контакте номерами телефонов
        
        Args:
            message_id: Уникальный идентификатор письма
            contact_info: Информация о контакте
            
        Returns:
            Обогащенная информация о контакте
        """
        contact_name = contact_info.get("name", "")
        enriched_contact = contact_info.copy()
        
        # Находим вложения для контакта
        attachments = self.find_attachments_for_contact(message_id, contact_name)
        
        # Извлекаем телефоны из вложений
        all_phones = []
        phone_sources = []
        
        for attachment in attachments:
            extraction_result = self.extract_phones_from_attachment(attachment)
            
            if extraction_result.get("phones"):
                all_phones.extend(extraction_result["phones"])
                phone_sources.append({
                    "attachment_filename": extraction_result["attachment_filename"],
                    "extraction_method": extraction_result["extraction_method"],
                    "extraction_time": extraction_result["extraction_time"],
                    "phones": extraction_result["phones"]
                })
        
        # Удаляем дубликаты
        unique_phones = list(set(all_phones))
        
        # Обогащаем контакт
        enriched_contact["phones"] = unique_phones
        enriched_contact["phone_sources"] = phone_sources
        enriched_contact["phone_extraction_time"] = datetime.now().isoformat()
        
        # Сохраняем результаты в файл контакта
        if contact_info.get("id"):
            self._save_contact_phones(
                contact_info["id"], 
                message_id, 
                unique_phones, 
                phone_sources
            )
        
        self.logger.debug(f"Обогащен контакт '{contact_name}' {len(unique_phones)} телефонами")
        return enriched_contact
    
    def _save_contact_phones(self, contact_id: str, message_id: str, phones: List[str], sources: List[Dict]):
        """
        Сохранение информации о телефонах контакта
        
        Args:
            contact_id: ID контакта
            message_id: ID сообщения
            phones: Список номеров телефонов
            sources: Источники извлечения
        """
        try:
            contact_file = self.contacts_dir / f"{contact_id}_phones.json"
            
            # Загружаем существующие данные
            existing_data = {}
            if contact_file.exists():
                with open(contact_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            # Добавляем новые данные
            if "phones" not in existing_data:
                existing_data["phones"] = []
            
            if "sources" not in existing_data:
                existing_data["sources"] = []
            
            # Добавляем телефоны из этого сообщения
            message_data = {
                "message_id": message_id,
                "phones": phones,
                "sources": sources,
                "extracted_at": datetime.now().isoformat()
            }
            
            # Проверяем на дубликаты
            existing_message_ids = [src.get("message_id") for src in existing_data["sources"]]
            if message_id not in existing_message_ids:
                existing_data["phones"].extend(phones)
                existing_data["sources"].append(message_data)
                
                # Удаляем дубликаты
                existing_data["phones"] = list(set(existing_data["phones"]))
            
            # Сохраняем обновленные данные
            with open(contact_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения телефонов контакта {contact_id}: {e}")
    
    def get_contact_phones(self, contact_id: str) -> Dict:
        """
        Получение информации о телефонах контакта
        
        Args:
            contact_id: ID контакта
            
        Returns:
            Информация о телефонах контакта
        """
        try:
            contact_file = self.contacts_dir / f"{contact_id}_phones.json"
            
            if contact_file.exists():
                with open(contact_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "contact_id": contact_id,
                    "phones": [],
                    "sources": []
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка загрузки телефонов контакта {contact_id}: {e}")
            return {
                "contact_id": contact_id,
                "phones": [],
                "sources": [],
                "error": str(e)
            }
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """
        Загрузка результатов из кэша
        
        Args:
            cache_key: Ключ кэша
            
        Returns:
            Результаты извлечения или None
        """
        if not self._is_cache_valid():
            return None
        
        return self._extraction_cache.get(cache_key)
    
    def _save_to_cache(self, cache_key: str, result: Dict):
        """
        Сохранение результатов в кэш
        
        Args:
            cache_key: Ключ кэша
            result: Результаты извлечения
        """
        self._extraction_cache[cache_key] = result
        self._cache_timestamp = datetime.now()
    
    def _is_cache_valid(self) -> bool:
        """Проверка актуальности кэша"""
        if not self._cache_timestamp:
            return False
        
        import time
        return (time.time() - self._cache_timestamp.timestamp()) < self._cache_ttl
    
    def get_extraction_statistics(self) -> Dict:
        """
        Получение статистики извлечения телефонов
        
        Returns:
            Статистика извлечения телефонов
        """
        stats = {
            "total_contacts": 0,
            "contacts_with_phones": 0,
            "total_phones": 0,
            "unique_phones": 0,
            "extraction_methods": {},
            "last_updated": None
        }
        
        try:
            # Обходим все файлы контактов
            contact_files = list(self.contacts_dir.glob("*_phones.json"))
            stats["total_contacts"] = len(contact_files)
            
            all_phones = set()
            method_counts = {}
            
            for contact_file in contact_files:
                try:
                    with open(contact_file, 'r', encoding='utf-8') as f:
                        contact_data = json.load(f)
                    
                    phones = contact_data.get("phones", [])
                    sources = contact_data.get("sources", [])
                    
                    if phones:
                        stats["contacts_with_phones"] += 1
                        stats["total_phones"] += len(phones)
                        all_phones.update(phones)
                    
                    for source in sources:
                        method = source.get("extraction_method", "unknown")
                        method_counts[method] = method_counts.get(method, 0) + 1
                        
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки {contact_file}: {e}")
            
            stats["unique_phones"] = len(all_phones)
            stats["extraction_methods"] = method_counts
            stats["last_updated"] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Ошибка подсчета статистики: {e}")
        
        return stats


def test_contact_phone_adapter():
    """Тестирование адаптера Contact Phone"""
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        
        # Создаем тестовую структуру
        (data_dir / "emails" / "2025-07-23").mkdir(parents=True)
        (data_dir / "attachments" / "2025-07-23").mkdir(parents=True)
        (data_dir / "contacts").mkdir(parents=True)
        
        # Создаем тестовое вложение с текстом
        test_attachment = data_dir / "attachments" / "2025-07-23" / "contact_info.txt"
        test_content = """
        Контактная информация:
        Имя: Иванов Иван Иванович
        Телефон: +7 (495) 123-45-67
        Рабочий: 8 (916) 234-56-78
        Мобильный: +7 926 345 67 89
        """
        test_attachment.write_text(test_content, encoding='utf-8')
        
        # Инициализируем адаптер
        adapter = ContactPhoneAdapter(data_dir)
        
        # Регистрируем тестовое вложение
        attachment_id = adapter.attachment_registry.register_attachment(
            message_id="test-message-123",
            attachment_filename="contact_info.txt",
            attachment_path=str(test_attachment),
            thread_id="test-thread-456",
            file_size=len(test_content),
            content_type="text/plain"
        )
        
        # Тестируем извлечение телефонов
        attachment_info = {
            "attachment_id": attachment_id,
            "attachment_path": str(test_attachment),
            "attachment_filename": "contact_info.txt",
            "content_type": "text/plain"
        }
        
        extraction_result = adapter.extract_phones_from_attachment(attachment_info)
        print(f"Результат извлечения: {json.dumps(extraction_result, indent=2)}")
        
        # Тестируем обогащение контакта
        contact_info = {
            "id": "contact-123",
            "name": "Иванов Иван",
            "email": "ivanov@example.com"
        }
        
        enriched_contact = adapter.enrich_contact_with_phones("test-message-123", contact_info)
        print(f"Обогащенный контакт: {json.dumps(enriched_contact, indent=2)}")
        
        # Тестируем получение телефонов контакта
        contact_phones = adapter.get_contact_phones("contact-123")
        print(f"Телефоны контакта: {json.dumps(contact_phones, indent=2)}")
        
        # Получаем статистику
        stats = adapter.get_extraction_statistics()
        print(f"Статистика: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    test_contact_phone_adapter()