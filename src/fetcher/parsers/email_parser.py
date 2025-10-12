"""
EmailParser - Парсинг email и извлечение текста.

Перенесенная логика парсинга из оригинального модуля с адаптацией
для новой архитектуры.
"""

import email
import email.message
import logging
from typing import Optional

from ..utils.email_utils import decode_header_value


class EmailParser:
    """
    Парсер email с переносом логики из оригинального модуля.
    
    Отвечает за:
    - Извлечение сырых байтов письма
    - Парсинг email структуры
    - Извлечение и очистку текста
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Инициализация парсера.
        
        Args:
            logger: Экземпляр логгера
        """
        self.logger = logger
        self.logger.info("📄 EmailParser инициализирован")
    
    def extract_raw_email(self, fetch_data) -> Optional[bytes]:
        """
        Извлечение сырых байтов письма из fetch_data.
        
        Args:
            fetch_data: Данные от IMAP fetch
            
        Returns:
            Сырые байты письма или None
        """
        try:
            if not fetch_data:
                self.logger.error("❌ fetch_data пустой")
                return None
            
            if isinstance(fetch_data, (list, tuple)):
                for i, item in enumerate(fetch_data):
                    if isinstance(item, tuple) and len(item) > 1:
                        for j in range(len(item)):
                            try:
                                element = item[j]
                                if isinstance(element, bytes) and len(element) > 500:
                                    return element
                            except IndexError:
                                continue
                    elif isinstance(item, bytes) and len(item) > 500:
                        return item
                
                # Правильная проверка первого элемента
                try:
                    if len(fetch_data) > 0:
                        first_item = fetch_data[0]
                        if isinstance(first_item, bytes) and len(first_item) > 500:
                            return first_item
                        elif isinstance(first_item, tuple) and len(first_item) > 1:
                            second_element = first_item[1]
                            if (
                                isinstance(second_element, bytes)
                                and len(second_element) > 500
                            ):
                                return second_element
                except (IndexError, TypeError):
                    pass
            
            elif isinstance(fetch_data, bytes):
                return fetch_data
            
            self.logger.error("❌ Не удалось найти байты письма в структуре данных")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка в extract_raw_email: {e}")
            return None
    
    def extract_plain_text(
        self, msg: email.message.Message, include_attachment_data: bool = False
    ) -> str:
        """
        Извлечение и очистка текста письма.
        
        Args:
            msg: Email сообщение
            include_attachment_data: Включать данные вложений
            
        Returns:
            Очищенный текст письма
        """
        max_len = 500_000
        plain_parts = []
        html_parts = []
        
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype in ("text/plain", "text/html"):
                        # Проверяем, является ли часть вложением
                        if not include_attachment_data:
                            disposition = part.get("Content-Disposition", "")
                            if disposition and (
                                "attachment" in disposition.lower()
                                or "inline" in disposition.lower()
                            ):
                                continue  # Пропускаем вложения
                        
                        try:
                            raw = part.get_payload(decode=True)
                            charset = part.get_content_charset() or "utf-8"
                            chunk = raw.decode(charset, errors="ignore") if raw else ""
                            
                            if not chunk:
                                continue
                            
                            if ctype == "text/plain":
                                stripped = chunk.strip()
                                if stripped:
                                    plain_parts.append(stripped)
                            else:  # text/html
                                html_parts.append(chunk)
                        except Exception as e:
                            self.logger.warning(f"⚠️ Ошибка извлечения текста: {e}")
                            continue
            else:
                try:
                    raw = msg.get_payload(decode=True)
                    if raw:
                        charset = msg.get_content_charset() or "utf-8"
                        chunk = raw.decode(charset, errors="ignore")
                        if not chunk:
                            chunk = ""
                        
                        ctype = msg.get_content_type()
                        if ctype == "text/plain":
                            stripped = chunk.strip()
                            if stripped:
                                plain_parts.append(stripped)
                        elif ctype == "text/html":
                            html_parts.append(chunk)
                        else:
                            stripped = chunk.strip()
                            if stripped:
                                plain_parts.append(stripped)
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка извлечения простого текста: {e}")
            
            selected_text = ""
            is_html = False
            if plain_parts:
                full_text = "\n\n".join(plain_parts)
                selected_text = self._basic_text_cleanup(full_text)
            elif html_parts:
                selected_text = "\n\n".join(html_parts)
                is_html = True
            else:
                selected_text = ""
            
            final_text = selected_text[:max_len]
            return final_text if is_html else final_text.strip()
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка извлечения текста: {e}")
            return ""
    
    def _basic_html_cleanup(self, html_text: str) -> str:
        """
        Базовая очистка HTML текста.
        
        Args:
            html_text: HTML текст
            
        Returns:
            Очищенный текст
        """
        try:
            import re
            import html as html_module
            
            text = html_text
            # Заменяем блочные теги на переносы строк
            text = re.sub(r'<\s*(br|/div|div|/p|p|/li|li|/tr|tr|/table|table)[^>]*>', '\n', text, flags=re.IGNORECASE)
            # Удаляем остальные теги
            text = re.sub(r'<[^>]+>', ' ', text)
            # Декодируем HTML сущности и небуквенные пробелы
            text = html_module.unescape(text)
            text = text.replace('\xa0', ' ')
            # Унифицируем переносы строк
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            # Заменяем множественные пробелы
            text = re.sub(r'[ \t]+', ' ', text)
            # Сжимаем лишние пустые строки
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка очистки HTML: {e}")
            return html_text
    
    def _basic_text_cleanup(self, text: str) -> str:
        """
        Базовая очистка текста.
        
        Args:
            text: Текст для очистки
            
        Returns:
            Очищенный текст
        """
        try:
            import re
            
            # Удаляем множественные переносы строк
            text = re.sub(r'\n\s*\n', '\n\n', text)
            
            # Удаляем лишние пробелы
            text = re.sub(r'[ \t]+', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка очистки текста: {e}")
            return text
    
    def parse_email_headers(self, raw_headers: bytes) -> Optional[email.message.Message]:
        """
        Парсинг заголовков письма.
        
        Args:
            raw_headers: Сырые заголовки
            
        Returns:
            Распарсенные заголовки или None
        """
        try:
            return email.message_from_bytes(raw_headers)
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга заголовков: {e}")
            return None
    
    def parse_email_message(self, raw_email: bytes) -> Optional[email.message.Message]:
        """
        Парсинг полного email сообщения.
        
        Args:
            raw_email: Сырые байты письма
            
        Returns:
            Распарсенное сообщение или None
        """
        try:
            return email.message_from_bytes(raw_email)
        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга email: {e}")
            return None
    
    def get_email_structure_info(self, msg: email.message.Message) -> dict:
        """
        Получение информации о структуре письма.
        
        Args:
            msg: Email сообщение
            
        Returns:
            Словарь с информацией о структуре
        """
        try:
            structure = {
                "is_multipart": msg.is_multipart(),
                "content_type": msg.get_content_type(),
                "parts_count": 0,
                "attachments_count": 0,
                "inline_images_count": 0,
            }
            
            if msg.is_multipart():
                parts = list(msg.walk())
                structure["parts_count"] = len(parts)
                
                for part in parts:
                    content_disposition = part.get_content_disposition()
                    content_type = part.get_content_type()
                    
                    if content_disposition == "attachment":
                        structure["attachments_count"] += 1
                    elif (
                        content_disposition == "inline"
                        and content_type.startswith("image/")
                    ):
                        structure["inline_images_count"] += 1
            
            return structure
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа структуры: {e}")
            return {}
    
    def extract_email_addresses(self, msg: email.message.Message) -> dict:
        """
        Извлечение email адресов из заголовков.
        
        Args:
            msg: Email сообщение
            
        Returns:
            Словарь с email адресами
        """
        try:
            addresses = {}
            
            # Извлекаем из разных полей
            for field in ["From", "To", "Cc", "Bcc", "Reply-To"]:
                value = msg.get(field, "")
                if value:
                    decoded = decode_header_value(value)
                    addresses[field.lower()] = decoded
            
            return addresses
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения адресов: {e}")
            return {}
