#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔄 Модуль восстановления полных текстов писем
Исправляет проблему обрезанных текстов с пометкой "ТЕКСТ ОБРЕЗАН ДЛЯ ЭКОНОМИИ ТОКЕНОВ"
"""

import os
import re
import json
import imaplib
import email
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    from ..core.email_fetcher import EmailFetcher
    from ..core.connection_manager import ConnectionManager
    from ..storage.email_storage import EmailStorage
except ImportError:
    # Fallback для прямого запуска
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.fetcher.core.email_fetcher import EmailFetcher
    from src.fetcher.core.connection_manager import ConnectionManager
    from src.fetcher.storage.email_storage import EmailStorage


@dataclass
class RecoveryResult:
    """📊 Результат восстановления текста письма"""
    success: bool
    message_id: str
    file_path: str
    original_length: int
    recovered_length: int
    contacts_found: int
    error_message: Optional[str] = None
    recovery_method: str = "unknown"


class TextRecoveryModule:
    """🔄 Модуль восстановления полных текстов писем"""
    
    TRUNCATION_MARKER = "[ТЕКСТ ОБРЕЗАН ДЛЯ ЭКОНОМИИ ТОКЕНОВ]"
    
    def __init__(self, data_dir: Path, logger: Optional[logging.Logger] = None):
        """🔧 Инициализация модуля восстановления"""
        self.data_dir = data_dir
        self.emails_dir = data_dir / "emails"
        self.logger = logger or self._setup_logger()
        
        # Инициализация компонентов
        self.connection_manager = ConnectionManager(logger)
        self.email_storage = EmailStorage(data_dir, logger)
        
        # Статистика
        self.stats = {
            "total_scanned": 0,
            "truncated_found": 0,
            "recovery_success": 0,
            "recovery_failed": 0,
            "contacts_recovered": 0,
            "bytes_recovered": 0
        }
        
        # Реестр восстановленных писем
        self.recovery_registry = {}
    
    def _setup_logger(self) -> logging.Logger:
        """📝 Настройка логгера"""
        logger = logging.getLogger("TextRecovery")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def scan_truncated_emails(self) -> List[Dict]:
        """🔍 Сканирование JSON файлов на наличие обрезанных текстов"""
        self.logger.info("🔍 Начало сканирования обрезанных писем...")
        
        truncated_emails = []
        
        # Рекурсивный обход всех папок с письмами
        for date_folder in self.emails_dir.iterdir():
            if not date_folder.is_dir():
                continue
                
            self.logger.debug(f"📂 Сканирование папки: {date_folder.name}")
            
            for json_file in date_folder.glob("email_*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        email_data = json.load(f)
                    
                    # Проверка на обрезанный текст
                    body = email_data.get('body', '')
                    message_id = email_data.get('message_id', '')
                    
                    if self.TRUNCATION_MARKER in body:
                        truncated_emails.append({
                            'file_path': str(json_file),
                            'message_id': message_id,
                            'thread_id': email_data.get('thread_id', ''),
                            'date_folder': date_folder.name,
                            'subject': email_data.get('subject', ''),
                            'original_length': len(body),
                            'from': email_data.get('from', ''),
                            'to': email_data.get('to', '')
                        })
                        
                        self.stats["truncated_found"] += 1
                    
                    self.stats["total_scanned"] += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки файла {json_file}: {e}")
                    continue
        
        self.logger.info(f"📊 Сканирование завершено:")
        self.logger.info(f"   Всего проверено: {self.stats['total_scanned']}")
        self.logger.info(f"   Обрезанных найдено: {self.stats['truncated_found']}")
        
        return truncated_emails
    
    def recover_email_text(self, message_id: str, date_folder: str) -> RecoveryResult:
        """🔄 Восстановление полного текста письма по Message-ID"""
        
        # Поиск JSON файла
        json_file = self._find_json_file(message_id, date_folder)
        if not json_file:
            return RecoveryResult(
                success=False,
                message_id=message_id,
                file_path="",
                original_length=0,
                recovered_length=0,
                contacts_found=0,
                error_message="JSON файл не найден"
            )
        
        # Загрузка текущих данных
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
        except Exception as e:
            return RecoveryResult(
                success=False,
                message_id=message_id,
                file_path=str(json_file),
                original_length=0,
                recovered_length=0,
                contacts_found=0,
                error_message=f"Ошибка загрузки JSON: {e}"
            )
        
        original_body = email_data.get('body', '')
        original_length = len(original_body)
        
        # Попытка восстановления через IMAP
        try:
            recovered_body = self._recover_from_imap(message_id, date_folder)
            if recovered_body and self.TRUNCATION_MARKER not in recovered_body:
                return self._update_email_file(
                    json_file, email_data, recovered_body, 
                    original_length, "imap"
                )
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось восстановить через IMAP: {e}")
        
        # Попытка восстановления из .eml файла
        try:
            recovered_body = self._recover_from_eml(message_id, date_folder)
            if recovered_body and self.TRUNCATION_MARKER not in recovered_body:
                return self._update_email_file(
                    json_file, email_data, recovered_body,
                    original_length, "eml"
                )
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось восстановить из .eml: {e}")
        
        return RecoveryResult(
            success=False,
            message_id=message_id,
            file_path=str(json_file),
            original_length=original_length,
            recovered_length=0,
            contacts_found=0,
            error_message="Не удалось восстановить текст",
            recovery_method="failed"
        )
    
    def _find_json_file(self, message_id: str, date_folder: str) -> Optional[Path]:
        """🔍 Поиск JSON файла по Message-ID"""
        folder_path = self.emails_dir / date_folder
        
        for json_file in folder_path.glob("email_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    email_data = json.load(f)
                
                if email_data.get('message_id') == message_id:
                    return json_file
            except Exception:
                continue
        
        return None
    
    def _recover_from_imap(self, message_id: str, date_folder: str) -> Optional[str]:
        """🔄 Восстановление текста через IMAP сервер"""
        self.logger.info(f"🔄 Попытка восстановления через IMAP: {message_id}")
        
        # Подключение к IMAP
        if not self.connection_manager.connect():
            raise Exception("Не удалось подключиться к IMAP серверу")
        
        try:
            # Поиск письма по Message-ID
            search_criteria = f'HEADER "Message-ID" "{message_id}"'
            msg_ids = self.connection_manager.search(search_criteria)
            
            if not msg_ids:
                raise Exception(f"Письмо с Message-ID {message_id} не найдено")
            
            # Загрузка полного письма
            msg_id = msg_ids[0]
            raw_email = self.connection_manager.fetch_email(msg_id)
            
            if not raw_email:
                raise Exception("Не удалось загрузить письмо")
            
            # Парсинг и извлечение текста
            msg = email.message_from_bytes(raw_email)
            full_text = self._extract_full_text(msg)
            
            return full_text
            
        finally:
            self.connection_manager.disconnect()
    
    def _recover_from_eml(self, message_id: str, date_folder: str) -> Optional[str]:
        """📧 Восстановление текста из .eml файла"""
        self.logger.info(f"📧 Попытка восстановления из .eml: {message_id}")
        
        # Поиск .eml файла
        eml_file = self._find_eml_file(message_id, date_folder)
        if not eml_file:
            return None
        
        try:
            with open(eml_file, 'rb') as f:
                raw_email = f.read()
            
            msg = email.message_from_bytes(raw_email)
            full_text = self._extract_full_text(msg)
            
            return full_text
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка чтения .eml файла: {e}")
            return None
    
    def _find_eml_file(self, message_id: str, date_folder: str) -> Optional[Path]:
        """🔍 Поиск .eml файла по Message-ID"""
        # Проверяем различные места хранения .eml файлов
        eml_locations = [
            self.data_dir / "eml" / date_folder,
            self.data_dir / "raw_emails" / date_folder,
            self.data_dir / "attachments" / date_folder,  # иногда хранятся здесь
        ]
        
        for location in eml_locations:
            if not location.exists():
                continue
            
            for eml_file in location.glob("*.eml"):
                try:
                    with open(eml_file, 'rb') as f:
                        raw_email = f.read()
                    
                    msg = email.message_from_bytes(raw_email)
                    headers = msg.items()
                    
                    for header_name, header_value in headers:
                        if header_name.lower() == 'message-id':
                            if header_value.strip() == message_id:
                                return eml_file
                except Exception:
                    continue
        
        return None
    
    def _extract_full_text(self, msg: email.message.Message) -> str:
        """📄 Извлечение полного текста из email сообщения"""
        text_parts = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type in ("text/plain", "text/html"):
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            text = payload.decode(charset, errors="ignore")
                            
                            # Базовая очистка HTML
                            if content_type == "text/html":
                                text = self._clean_html(text)
                            
                            text_parts.append(text)
                    except Exception as e:
                        self.logger.warning(f"⚠️ Ошибка извлечения части: {e}")
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="ignore")
                    
                    if msg.get_content_type() == "text/html":
                        text = self._clean_html(text)
                    
                    text_parts.append(text)
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка извлечения текста: {e}")
        
        return "\n".join(text_parts).strip()
    
    def _clean_html(self, html_text: str) -> str:
        """🧹 Базовая очистка HTML текста"""
        # Удаление HTML тегов
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        
        # Удаление множественных пробелов и переносов
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        return clean_text.strip()
    
    def _update_email_file(
        self, 
        json_file: Path, 
        email_data: Dict, 
        new_body: str,
        original_length: int,
        recovery_method: str
    ) -> RecoveryResult:
        """💾 Обновление JSON файла с восстановленным текстом"""
        
        try:
            # Создание резервной копии
            backup_file = json_file.with_suffix('.json.backup')
            json_file.rename(backup_file)
            
            # Обновление данных
            email_data['body'] = new_body
            email_data['char_count'] = len(new_body)
            email_data['text_recovered_at'] = datetime.now().isoformat()
            email_data['text_recovery_method'] = recovery_method
            email_data['original_char_count'] = original_length
            
            # Сохранение обновленного файла
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(email_data, f, ensure_ascii=False, indent=2)
            
            # Подсчет контактов
            contacts_found = self._count_contacts(new_body)
            
            # Обновление статистики
            self.stats["recovery_success"] += 1
            self.stats["contacts_recovered"] += contacts_found
            self.stats["bytes_recovered"] += len(new_body) - original_length
            
            self.logger.info(f"✅ Текст восстановлен: {json_file.name}")
            self.logger.info(f"   Метод: {recovery_method}")
            self.logger.info(f"   Размер: {original_length} → {len(new_body)}")
            self.logger.info(f"   Контакты найдено: {contacts_found}")
            
            return RecoveryResult(
                success=True,
                message_id=email_data.get('message_id', ''),
                file_path=str(json_file),
                original_length=original_length,
                recovered_length=len(new_body),
                contacts_found=contacts_found,
                recovery_method=recovery_method
            )
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления файла {json_file}: {e}")
            
            # Попытка восстановления из бэкапа
            if backup_file.exists():
                backup_file.rename(json_file)
            
            return RecoveryResult(
                success=False,
                message_id=email_data.get('message_id', ''),
                file_path=str(json_file),
                original_length=original_length,
                recovered_length=0,
                contacts_found=0,
                error_message=f"Ошибка обновления: {e}",
                recovery_method="failed"
            )
    
    def _count_contacts(self, text: str) -> int:
        """👥 Подсчет количества контактов в тексте"""
        # Поиск email адресов
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Поиск телефонов (российские форматы)
        phone_pattern = r'(\+7|8)[\s-]?\(?[\d]{3,4}\)?[\s-]?[\d]{2,3}[\s-]?[\d]{2,3}[\s-]?[\d]{2,3}'
        phones = re.findall(phone_pattern, text)
        
        return len(emails) + len(phones)
    
    def batch_recovery(self, date_range: Optional[Tuple[str, str]] = None) -> List[RecoveryResult]:
        """🔄 Пакетное восстановление текстов"""
        self.logger.info("🔄 Начало пакетного восстановления...")
        
        # Сканирование обрезанных писем
        truncated_emails = self.scan_truncated_emails()
        
        if not truncated_emails:
            self.logger.info("✅ Обрезанных писем не найдено")
            return []
        
        # Фильтрация по диапазону дат
        if date_range:
            start_date, end_date = date_range
            truncated_emails = [
                email for email in truncated_emails
                if start_date <= email['date_folder'] <= end_date
            ]
        
        self.logger.info(f"📊 Найдено обрезанных писем: {len(truncated_emails)}")
        
        results = []
        for i, email_info in enumerate(truncated_emails, 1):
            self.logger.info(f"🔄 Обработка {i}/{len(truncated_emails)}: {email_info['message_id']}")
            
            result = self.recover_email_text(
                email_info['message_id'],
                email_info['date_folder']
            )
            
            results.append(result)
            
            if result.success:
                self.recovery_registry[result.message_id] = {
                    'recovered_at': datetime.now().isoformat(),
                    'method': result.recovery_method,
                    'original_length': result.original_length,
                    'recovered_length': result.recovered_length,
                    'contacts_found': result.contacts_found
                }
        
        # Сохранение реестра восстановления
        self._save_recovery_registry()
        
        # Вывод статистики
        self._print_final_stats()
        
        return results
    
    def _save_recovery_registry(self):
        """💾 Сохранение реестра восстановления"""
        registry_file = self.data_dir / "text_recovery_registry.json"
        
        try:
            with open(registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.recovery_registry, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 Реестр восстановления сохранен: {registry_file}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения реестра: {e}")
    
    def _print_final_stats(self):
        """📊 Вывод финальной статистики"""
        self.logger.info("=" * 70)
        self.logger.info("📊 СТАТИСТИКА ВОССТАНОВЛЕНИЯ ТЕКСТОВ")
        self.logger.info("=" * 70)
        self.logger.info(f"📧 Всего проверено: {self.stats['total_scanned']}")
        self.logger.info(f"✂️ Обрезанных найдено: {self.stats['truncated_found']}")
        self.logger.info(f"✅ Успешно восстановлено: {self.stats['recovery_success']}")
        self.logger.info(f"❌ Не удалось восстановить: {self.stats['recovery_failed']}")
        self.logger.info(f"👥 Контактов восстановлено: {self.stats['contacts_recovered']}")
        self.logger.info(f"📏 Байт восстановлено: {self.stats['bytes_recovered']}")
        
        if self.stats['truncated_found'] > 0:
            success_rate = (self.stats['recovery_success'] / self.stats['truncated_found']) * 100
            self.logger.info(f"📈 Успешность восстановления: {success_rate:.1f}%")
        
        self.logger.info("=" * 70)