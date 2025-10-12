"""
EmailProcessor - Обработка писем с корректным маппингом вложений.

Отвечает за полную обработку отдельного письма:
- Применение фильтров
- Извлечение данных
- Обработка вложений с использованием message_id
- Сохранение результатов
"""

import email
import email.message
import email.utils
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Импорты из новой архитектуры
from ..utils.date_utils import get_local_time, parse_email_date, format_email_date_for_log
from ..utils.email_utils import decode_header_value, parse_recipients, generate_thread_id
from ..utils.enhanced_text_cleaner_with_precleaner import (
    EnhancedTextCleanerWithPreCleaner,
    create_text_cleaner,
)


class EmailProcessor:
    """
    Обработчик писем с корректным маппингом вложений.
    
    Ключевое отличие от оригинального кода:
    - Использует message_id для определения принадлежности вложений
    - Интегрируется с AttachmentRegistry для точного отслеживания
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        text_cleaner: Optional[EnhancedTextCleanerWithPreCleaner] = None,
    ):
        """🛠️ Подготавливает обработчик писем нового конвейера."""
        self.logger = logger
        self.logger.info("📧 EmailProcessor инициализирован")
        self.text_cleaner = text_cleaner or create_text_cleaner(logger, enable_precleaner=True)
    
    def process_email(
        self,
        msg_id: bytes,
        date_str: str,
        email_num_in_day: int,
        total_emails_in_day: int,
        include_attachment_data: bool = False,
        **kwargs
    ) -> Optional[Dict]:
        """
        Основной метод обработки одного письма.
        
        Args:
            msg_id: ID письма
            date_str: Строка даты
            email_num_in_day: Номер письма в дне
            total_emails_in_day: Всего писем в дне
            include_attachment_data: Включать данные вложений
            **kwargs: Дополнительные компоненты (connection_manager, attachment_registry, etc.)
            
        Returns:
            Обработанные данные письма или None
        """
        # Извлекаем компоненты из kwargs
        connection_manager = kwargs.get('connection_manager')
        attachment_registry = kwargs.get('attachment_registry')
        email_storage = kwargs.get('email_storage')
        email_parser = kwargs.get('email_parser')
        filters = kwargs.get('filters')
        text_cleaner = kwargs.get('text_cleaner')
        stats = kwargs.get('stats', {})
        
        if not all([connection_manager, attachment_registry, email_storage, email_parser, filters, text_cleaner]):
            self.logger.error("❌ Отсутствуют необходимые компоненты для обработки письма")
            return None
        
        stats["processed"] = stats.get("processed", 0) + 1
        self.logger.info("=" * 70)

        try:
            # ШАГ 1: Заголовки
            headers_msg = self._get_email_headers(msg_id, connection_manager)
            if not headers_msg:
                self.logger.error("❌ Не удалось загрузить заголовки")
                stats["errors"] = stats.get("errors", 0) + 1
                self.logger.info("=" * 70)
                return None

            # ШАГ 2: Базовая информация
            email_info = self._extract_header_info(headers_msg, date_str)
            email_info["email_num_in_day"] = email_num_in_day
            email_info["total_emails_in_day"] = total_emails_in_day

            filename_preview = (
                f"email_{email_num_in_day:03d}_"
                f"{email_info['date_folder'].replace('-', '')}_"
                f"{email_info['thread_id']}"
            )

            self.logger.info(
                "📧 ПИСЬМО %d/%d: %s.json",
                email_num_in_day,
                total_emails_in_day,
                filename_preview,
            )
            self.logger.info("   От: %s", email_info["from"])
            self.logger.info("   Тема: %s", email_info["subject"])
            self.logger.info("   Message-ID: %s", email_info["message_id"])

            # ШАГ 3: Сценарий
            processing_scenario = self._get_processing_scenario(
                email_info["message_id"],
                email_info["date_folder"],
                attachment_registry,
                email_storage,
            )

            # ШАГ 4: Фильтры
            filter_ok, filter_reason = self._apply_filters(email_info, filters, stats)
            if not filter_ok:
                self.logger.info("🚫 ПИСЬМО ПРОПУЩЕНО: %s", filter_reason)
                self.logger.info("=" * 70)
                return None

            # ШАГ 5: Проверка размера
            email_size = self._check_email_size(msg_id, connection_manager)
            if email_size and email_size > 100_000_000:  # 100MB
                self.logger.warning(
                    f"⚠️ Очень большое письмо ({email_size} байт), пропускаем"
                )
                stats["skipped_large_emails"] = stats.get("skipped_large_emails", 0) + 1
                self.logger.info("=" * 70)
                return None

            # ШАГ 6: Основная обработка
            return self._process_by_scenario(
                processing_scenario,
                msg_id,
                email_info,
                headers_msg,
                connection_manager,
                attachment_registry,
                email_storage,
                email_parser,
                text_cleaner,
                include_attachment_data,
                stats
            )
            
        except Exception as e:
            self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА обработки письма: {e}")
            stats["errors"] = stats.get("errors", 0) + 1
            self.logger.info("=" * 70)
            return None
    
    def _get_email_headers(self, msg_id: bytes, connection_manager) -> Optional[email.message.Message]:
        """Получение заголовков письма."""
        try:
            header_data = connection_manager.fetch_headers(msg_id)
            if not header_data:
                return None
            
            # Извлекаем сырые заголовки
            raw_headers = self._extract_raw_headers(header_data)
            if not raw_headers:
                return None
            
            return email.message_from_bytes(raw_headers)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения заголовков: {e}")
            return None
    
    def _extract_raw_headers(self, header_data) -> Optional[bytes]:
        """Извлечение сырых байтов заголовков."""
        try:
            if not header_data:
                return None
            
            if isinstance(header_data, (list, tuple)):
                for item in header_data:
                    if isinstance(item, tuple) and len(item) > 1:
                        for j in range(len(item)):
                            try:
                                element = item[j]
                                if isinstance(element, bytes) and j > 0 and len(element) > 50:
                                    return element
                            except IndexError:
                                continue
                    elif isinstance(item, bytes) and len(item) > 50:
                        return item
                
                # Проверяем первый элемент
                if len(header_data) > 0 and isinstance(header_data[0], bytes) and len(header_data[0]) > 50:
                    return header_data[0]
            
            elif isinstance(header_data, bytes):
                return header_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения заголовков: {e}")
            return None
    
    def _extract_header_info(self, headers_msg: email.message.Message, date_str: str) -> Dict:
        """Извлечение базовой информации из заголовков."""
        try:
            # Извлекаем основные поля
            from_addr = decode_header_value(headers_msg.get("From", ""))
            subject = decode_header_value(headers_msg.get("Subject", ""))
            date = decode_header_value(headers_msg.get("Date", date_str))
            message_id = headers_msg.get("Message-ID", "").strip()
            
            # Извлекаем получателей
            raw_to = headers_msg.get("To", "")
            raw_cc = headers_msg.get("Cc", "")
            
            from email.utils import getaddresses
            
            to_emails = [
                addr.lower().strip()
                for name, addr in getaddresses([raw_to])
                if addr
            ]
            cc_emails = [
                addr.lower().strip()
                for name, addr in getaddresses([raw_cc])
                if addr
            ]
            
            # Форматируем для обратной совместимости
            to_addr = ", ".join(to_emails[:3]) + ("..." if len(to_emails) > 3 else "")
            cc_addr = ", ".join(cc_emails[:3]) + ("..." if len(cc_emails) > 3 else "")
            
            # Вычисляем папку даты
            try:
                email_date = parse_email_date(date)
                date_folder = email_date.strftime("%Y-%m-%d")
                email_date_formatted = format_email_date_for_log(date)
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка парсинга даты: {e}")
                date_folder = get_local_time().strftime("%Y-%m-%d")
                email_date_formatted = "неизвестная дата"
            
            # Генерируем thread_id
            try:
                thread_id = generate_thread_id(from_addr, subject, date)
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка генерации thread_id: {e}")
                thread_id = f"unknown_{get_local_time().strftime('%Y%m%d_%H%M%S')}"
            
            return {
                "thread_id": thread_id,
                "message_id": message_id,
                "from": from_addr,
                "to": to_addr,
                "cc": cc_addr,
                "to_emails": to_emails,
                "cc_emails": cc_emails,
                "subject": subject,
                "date": date,
                "date_folder": date_folder,
                "email_date_formatted": email_date_formatted,
                "headers_msg": headers_msg
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения информации из заголовков: {e}")
            # Возвращаем базовую информацию
            return {
                "thread_id": f"unknown_{get_local_time().strftime('%Y%m%d_%H%M%S')}",
                "message_id": "",
                "from": "",
                "to": "",
                "cc": "",
                "to_emails": [],
                "cc_emails": [],
                "subject": "",
                "date": date_str,
                "date_folder": get_local_time().strftime("%Y-%m-%d"),
                "email_date_formatted": "неизвестная дата",
                "headers_msg": headers_msg
            }
    
    def _get_processing_scenario(
        self, 
        message_id: str, 
        date_folder: str,
        attachment_registry,
        email_storage
    ) -> str:
        """Определение сценария обработки письма."""
        # Проверяем статус через реестр вложений
        status = attachment_registry.check_email_processing_status(message_id, date_folder)
        
        if status["json_exists"] and status["attachments_exist"]:
            return "skip_all"  # JSON и вложения существуют - пропустить
        elif status["json_exists"] and not status["attachments_exist"]:
            return "download_attachments"  # Только JSON - загрузить вложения
        elif not status["json_exists"] and status["attachments_exist"]:
            self.logger.warning(
                f"⚠get_processing_scenario: attachments_exist=True для нового письма {message_id}"
            )
            return "download_json"  # Только вложения - загрузить JSON
        else:
            return "download_all"  # Ничего нет - загрузить всё
    
    def _apply_filters(self, email_info: Dict, filters, stats: Dict) -> Tuple[bool, Optional[str]]:
        """Применение фильтров к письму."""
        # Фильтр по теме
        subject_filter = filters.is_subject_filtered(email_info["subject"])
        if subject_filter:
            self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО ТЕМЕ: {subject_filter}")
            stats["filtered_subject"] = stats.get("filtered_subject", 0) + 1
            return False, subject_filter
        
        # Фильтр по черному списку
        blacklist_filter = filters.is_sender_blacklisted(email_info["from"])
        if blacklist_filter:
            self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО АДРЕСУ: {blacklist_filter}")
            stats["filtered_blacklist"] = stats.get("filtered_blacklist", 0) + 1
            return False, blacklist_filter
        
        # Фильтр массовых рассылок
        mass_mailing_filter = filters.is_internal_mass_mailing(
            email_info["from"], 
            email_info["to_emails"], 
            email_info["cc_emails"]
        )
        if mass_mailing_filter:
            self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО РАССЫЛКЕ: {mass_mailing_filter}")
            stats["filtered_mass_mailing"] = stats.get("filtered_mass_mailing", 0) + 1
            return False, mass_mailing_filter
        
        return True, None
    
    def _check_email_size(self, msg_id: bytes, connection_manager) -> Optional[int]:
        """Проверка размера письма."""
        try:
            status, data = connection_manager.mail.fetch(msg_id, "(RFC822.SIZE)")
            if status == "OK" and data:
                size_str = str(data[0])
                m = re.search(r"RFC822\.SIZE (\d+)", size_str)
                if m:
                    return int(m.group(1))
            return None
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка проверки размера письма: {e}")
            return None
    
    def _process_by_scenario(
        self,
        scenario: str,
        msg_id: bytes,
        email_info: Dict,
        headers_msg,
        connection_manager,
        attachment_registry,
        email_storage,
        email_parser,
        text_cleaner,
        include_attachment_data: bool,
        stats: Dict
    ) -> Optional[Dict]:
        """Обработка письма в зависимости от сценария."""
        
        if scenario == "skip_all":
            self.logger.info("📁 ✅ ПИСЬМО УЖЕ ПОЛНОСТЬЮ ОБРАБОТАНО")
            stats["already_exists"] = stats.get("already_exists", 0) + 1
            self.logger.info("=" * 70)
            return None
        elif scenario == "download_attachments":
            self.logger.info("📎 ⬇️ РЕЖИМ: только недостающие вложения")
        elif scenario == "download_json":
            self.logger.info("📄 РЕЖИМ: только JSON")
        else:  # download_all
            self.logger.info("📧📎 ⬇️ РЕЖИМ: JSON + вложения")
        
        # Получаем полное письмо
        fetch_data = connection_manager.safe_fetch(msg_id)
        if not fetch_data:
            self.logger.error("❌ Не удалось загрузить письмо")
            stats["errors"] = stats.get("errors", 0) + 1
            self.logger.info("=" * 70)
            return None
        
        # Извлекаем сырые данные
        raw_email = email_parser.extract_raw_email(fetch_data)
        if not raw_email:
            self.logger.error("❌ Не удалось извлечь сырой email")
            stats["errors"] = stats.get("errors", 0) + 1
            self.logger.info("=" * 70)
            return None
        
        # Парсим письмо
        try:
            msg = email.message_from_bytes(raw_email)
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга email: {e}")
            stats["errors"] = stats.get("errors", 0) + 1
            self.logger.info("=" * 70)
            return None
        
        # Сохраняем исходный .eml
        eml_relative_path = email_storage.save_eml(
            email_info.get("message_id", ""),
            email_info.get("date_folder", ""),
            raw_email,
        )
        
        # Извлекаем текст с использованием EnhancedTextCleanerWithPreCleaner БЕЗ ОБРЕЗКИ
        try:
            body_text = email_parser.extract_plain_text(msg, include_attachment_data)
            if body_text:
                clean_result = self.text_cleaner.clean_email_body_full(
                    body_text,
                    thread_id=email_info["thread_id"],
                    sender_email=email_info.get("from", ""),
                )
                cleaned_text = clean_result["cleaned_text"]
                
                # Логируем результат очистки
                self.logger.info(
                    "📝 Текст письма обработан: %d → %d символов",
                    clean_result["original_length"],
                    clean_result["final_length"],
                )
                self.logger.info(
                    "   📊 Сокращение: %.1f%%",
                    clean_result["reduction_percent"],
                )
                if clean_result.get("precleaner_enabled"):
                    self.logger.info("   🧼 PreCleaner активен")
                else:
                    self.logger.info("   🧼 PreCleaner отключен — используется базовая очистка")
                
                email_data = {
                    "thread_id": email_info["thread_id"],
                    "message_id": email_info["message_id"],
                    "email_num_in_day": email_info.get("email_num_in_day", 1),
                    "total_emails_in_day": email_info.get(
                        "total_emails_in_day", 1
                    ),
                    "from": email_info["from"],
                    "to": email_info["to"],
                    "cc": email_info["cc"],
                    "to_emails": email_info["to_emails"],
                    "cc_emails": email_info["cc_emails"],
                    "subject": email_info["subject"],
                    "date": email_info["date"],
                    "parsed_date": parse_email_date(email_info["date"]).isoformat()
                    if email_info["date"]
                    else None,
                    "body_raw": body_text,
                    "body_clean": cleaned_text,
                    "char_count": len(cleaned_text),
                    "attachments": [],  # временно, будет заполнено ниже
                    "attachments_stats": {},
                    "processed_at": get_local_time().isoformat(),
                    "raw_size": len(raw_email),
                    "date_folder": email_info["date_folder"],
                    "eml_path": eml_relative_path,
                }

                body_text = cleaned_text
            else:
                email_data = {
                    "thread_id": email_info["thread_id"],
                    "message_id": email_info["message_id"],
                    "email_num_in_day": email_info.get("email_num_in_day", 1),
                    "total_emails_in_day": email_info.get(
                        "total_emails_in_day", 1
                    ),
                    "from": email_info["from"],
                    "to": email_info["to"],
                    "cc": email_info["cc"],
                    "to_emails": email_info["to_emails"],
                    "cc_emails": email_info["cc_emails"],
                    "subject": email_info["subject"],
                    "date": email_info["date"],
                    "parsed_date": parse_email_date(email_info["date"]).isoformat()
                    if email_info["date"]
                    else None,
                    "body_raw": "",
                    "body_clean": "",
                    "char_count": 0,
                    "attachments": [],
                    "attachments_stats": {},
                    "processed_at": get_local_time().isoformat(),
                    "raw_size": len(raw_email),
                    "date_folder": email_info["date_folder"],
                    "eml_path": eml_relative_path,
                }
                
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка извлечения текста: {e}")
            body_text = "[ОШИБКА ИЗВЛЕЧЕНИЯ ТЕКСТА]"
            email_data = {
                "thread_id": email_info["thread_id"],
                "message_id": email_info["message_id"],
                "email_num_in_day": email_info.get("email_num_in_day", 1),
                "total_emails_in_day": email_info.get(
                    "total_emails_in_day", 1
                ),
                "from": email_info["from"],
                "to": email_info["to"],
                "cc": email_info["cc"],
                "to_emails": email_info["to_emails"],
                "cc_emails": email_info["cc_emails"],
                "subject": email_info["subject"],
                "date": email_info["date"],
                "parsed_date": parse_email_date(email_info["date"]).isoformat()
                if email_info["date"]
                else None,
                "body_raw": body_text,
                "body_clean": body_text,
                "char_count": len(body_text),
                "attachments": [],
                "attachments_stats": {},
                "processed_at": get_local_time().isoformat(),
                "raw_size": len(raw_email),
                "date_folder": email_info["date_folder"],
                "eml_path": eml_relative_path,
            }
        
        # Обрабатываем вложения
        attachments = []
        attachments_stats = {
            "total": 0,
            "saved": 0,
            "excluded": 0,
            "excluded_filenames": 0,
            "excluded_by_size": 0,
            "excluded_by_image_dimensions": 0,
            "unsupported": 0,
            "inline_images": 0,
        }
        
        if scenario in ["download_attachments", "download_all"]:
            attachments, attachments_stats = self._process_attachments(
                msg,
                msg_id,
                email_info["message_id"],
                email_info["thread_id"],
                email_info["date_folder"],
                attachment_registry,
                stats,
            )
        
        # Собираем данные письма
        email_data["attachments"] = attachments
        email_data["attachments_stats"] = attachments_stats
        email_data["char_count"] = len(email_data.get("body_clean", ""))

        # Сохраняем результаты
        saved = self._save_email_data(email_data, scenario, email_storage, attachment_registry)
        
        if saved:
            stats["saved"] = stats.get("saved", 0) + 1
            
            # Обновляем общую статистику вложений
            stats["saved_attachments"] = stats.get("saved_attachments", 0) + attachments_stats["saved"]
            stats["saved_inline_images"] = stats.get("saved_inline_images", 0) + attachments_stats["inline_images"]
            stats["excluded_attachments"] = stats.get("excluded_attachments", 0) + attachments_stats["excluded"]
            stats["excluded_filenames"] = stats.get("excluded_filenames", 0) + attachments_stats["excluded_filenames"]
            stats["excluded_by_size"] = stats.get("excluded_by_size", 0) + attachments_stats["excluded_by_size"]
            stats["excluded_by_image_dimensions"] = stats.get("excluded_by_image_dimensions", 0) + attachments_stats["excluded_by_image_dimensions"]
            stats["unsupported_attachments"] = stats.get("unsupported_attachments", 0) + attachments_stats["unsupported"]
            
            self._log_attachments_stats(attachments_stats)
            self.logger.info("✅ ПИСЬМО ПОЛНОСТЬЮ СОХРАНЕНО")
        self.logger.info("=" * 70)
        
        return email_data if saved else None
    
    def _process_attachments(
        self,
        msg: email.message.Message,
        msg_id: bytes,
        message_id: str,
        thread_id: str,
        date_folder: str,
        attachment_registry,
        stats: Dict,
        **kwargs
    ) -> Tuple[List[Dict], Dict]:
        """Обработка вложений с использованием message_id."""
        attachments = []
        attachments_stats = {
            "total": 0,
            "saved": 0,
            "excluded": 0,
            "excluded_filenames": 0,
            "excluded_by_size": 0,
            "excluded_by_image_dimensions": 0,
            "unsupported": 0,
            "inline_images": 0,
        }
        
        try:
            if msg.is_multipart():
                for part_num, part in enumerate(msg.walk()):
                    try:
                        content_disposition = part.get_content_disposition()
                        content_type = part.get_content_type()
                        
                        is_attachment = False
                        is_inline = False
                        
                        if content_disposition == "attachment":
                            is_attachment = True
                        elif (
                            content_disposition == "inline"
                            and content_type.startswith("image/")
                        ):
                            is_attachment = True
                            is_inline = True
                        elif (
                            not content_disposition
                            and content_type.startswith("image/")
                            and part.get_filename()
                        ):
                            # Дополнительные проверки для изображений
                            filename = part.get_filename()
                            content_id = part.get("Content-ID", "").strip("<>")
                            
                            if content_id or (filename and len(filename) > 5):
                                is_attachment = True
                                is_inline = True
                            else:
                                continue
                        
                        if is_attachment:
                            attachments_stats["total"] += 1
                            
                            # 🔄 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Используем message_id вместо thread_id
                            attachment_info = attachment_registry.save_attachment(
                                part=part,
                                message_id=message_id,  # Используем message_id!
                                thread_id=thread_id,  # Сохраняем thread_id для совместимости
                                date_folder=date_folder,
                                is_inline=is_inline
                            )
                            
                            if attachment_info:
                                attachments.append(attachment_info)
                                status = attachment_info.get("status", "unknown")
                                filename = attachment_info.get("original_filename", "unknown")
                                file_size = attachment_info.get("file_size", 0)
                                
                                # Детальное логирование каждого вложения
                                if status == "saved":
                                    attachments_stats["saved"] += 1
                                    if is_inline:
                                        attachments_stats["inline_images"] += 1
                                        self.logger.info(f"   📎 Вложение СОХРАНЕНО (встроенное): {filename} ({file_size} байт)")
                                    else:
                                        self.logger.info(f"   📎 Вложение СОХРАНЕНО: {filename} ({file_size} байт)")
                                elif status == "already_exists":
                                    attachments_stats["saved"] += 1
                                    self.logger.info(f"   📎 Вложение УЖЕ СУЩЕСТВУЕТ: {filename} ({file_size} байт)")
                                elif status in ["excluded", "excluded_by_filter", "excluded_inline_image"]:
                                    attachments_stats["excluded"] += 1
                                    reason = "встроенное изображение" if is_inline else "фильтр"
                                    self.logger.info(f"   🚫 Вложение ОТБРОШЕНО ({reason}): {filename} ({file_size} байт)")
                                elif status == "excluded_filename":
                                    attachments_stats["excluded_filenames"] += 1
                                    self.logger.info(f"   📝 Вложение ОТБРОШЕНО (имя файла): {filename} ({file_size} байт)")
                                elif status == "excluded_by_size":
                                    attachments_stats["excluded_by_size"] += 1
                                    self.logger.info(f"   📏 Вложение ОТБРОШЕНО (размер): {filename} ({file_size} байт)")
                                elif status == "excluded_by_image_dimensions":
                                    attachments_stats["excluded_by_image_dimensions"] += 1
                                    self.logger.info(f"   🖼️ Вложение ОТБРОШЕНО (размеры изображения): {filename} ({file_size} байт)")
                                elif status == "unsupported":
                                    attachments_stats["unsupported"] += 1
                                    self.logger.info(f"   ⚠️ Вложение НЕ ПОДДЕРЖИВАЕТСЯ: {filename} ({file_size} байт)")
                                else:
                                    self.logger.warning(f"   ❌ Неизвестный статус вложения '{status}': {filename} ({file_size} байт)")
                    
                    except Exception as e:
                        self.logger.warning(f"⚠️ Ошибка обработки части {part_num}: {e}")
                        continue
        
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки вложений: {e}")
        
        return attachments, attachments_stats
    
    def _save_email_data(
        self,
        email_data: Dict,
        scenario: str,
        email_storage,
        attachment_registry
    ) -> bool:
        """Сохранение данных письма."""
        try:
            if scenario in ["download_json", "download_all"]:
                return email_storage.save_email(email_data)
            elif scenario == "download_attachments":
                # Обновляем существующий файл с информацией о вложениях
                return email_storage.update_email_attachments(
                    email_data["message_id"],
                    email_data["date_folder"],
                    email_data["attachments"],
                    email_data["attachments_stats"]
                )
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения данных письма: {e}")
            return False
    
    def _log_attachments_stats(self, attachments_stats: Dict):
        """Логирование статистики вложений."""
        if attachments_stats["total"] > 0:
            inline_info = (
                f" + {attachments_stats['inline_images']}🖼️"
                if attachments_stats["inline_images"] > 0
                else ""
            )
            filename_excluded = (
                f" + {attachments_stats['excluded_filenames']}📝"
                if attachments_stats["excluded_filenames"] > 0
                else ""
            )
            size_excluded = (
                f" + {attachments_stats['excluded_by_size']}📏"
                if attachments_stats["excluded_by_size"] > 0
                else ""
            )
            dimensions_excluded = (
                f" + {attachments_stats['excluded_by_image_dimensions']}🖼️"
                if attachments_stats["excluded_by_image_dimensions"] > 0
                else ""
            )
            
            self.logger.info(
                f"📎 Вложений: {attachments_stats['saved']}✅ + {attachments_stats['excluded']}🚫 + {attachments_stats['unsupported']}⚠️{inline_info}{filename_excluded}{size_excluded}{dimensions_excluded} из {attachments_stats['total']}"
            )
            
            # Детальная статистика по причинам исключения
            if attachments_stats["excluded_filenames"] > 0:
                self.logger.info(f"   📝 Отброшено по имени файла: {attachments_stats['excluded_filenames']}")
            if attachments_stats["excluded_by_size"] > 0:
                self.logger.info(f"   📏 Отброшено по размеру: {attachments_stats['excluded_by_size']}")
            if attachments_stats["excluded_by_image_dimensions"] > 0:
                self.logger.info(f"   🖼️ Отброшено по размерам изображения: {attachments_stats['excluded_by_image_dimensions']}")
            if attachments_stats["unsupported"] > 0:
                self.logger.info(f"   ⚠️ Неподдерживаемых форматов: {attachments_stats['unsupported']}")
    
    def _log_processing_result(self, scenario: str, email_info: Dict):
        """Логирование результата обработки."""
        if scenario == "download_attachments":
            self.logger.info("✅ ВЛОЖЕНИЯ ЗАГРУЖЕНЫ")
        elif scenario == "download_json":
            self.logger.warning("⚠️ JSON СОХРАНЕН")
        elif scenario == "download_all":
            self.logger.info("✅ ПИСЬМО ПОЛНОСТЬЮ СОХРАНЕНО")
        
        self.logger.info(f"   Message-ID: {email_info['message_id']}")
        self.logger.info(f"   Папка: {email_info['date_folder']}")
