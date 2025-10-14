"""
ConnectionManager - Управление IMAP соединениями.

Отвечает за установку, поддержание и восстановление соединений с почтовым сервером.
"""

import imaplib
import ssl
import time
import logging
import signal
from typing import List, Optional, Tuple

# Для обработки специфических ошибок подключения
try:
    from errno import ECONNRESET
    ConnectionResetByPeer = ConnectionResetError
except ImportError:
    ConnectionResetByPeer = ConnectionError

# Импорты конфигурации
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройки подключения
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_PORT = int(os.getenv("IMAP_PORT", 143))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

# Альтернативный порт для автоматического переключения
IMAP_SSL_PORT = 993

# Настройки устойчивости
MAX_RETRIES = 5
RETRY_DELAY = 5
REQUEST_DELAY = 0.5


class ConnectionManager:
    """
    Менеджер соединений с IMAP сервером.
    
    Обеспечивает:
    - Установку соединения с retry логикой
    - Проверку состояния соединения
    - Автоматическое переподключение
    - Безопасное получение данных с таймаутами
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Инициализация менеджера соединений.
        
        Args:
            logger: Экземпляр логгера
        """
        self.logger = logger
        self.mail: Optional[imaplib.IMAP4] = None
        self.last_connect_time = 0
        self.is_connected = False
        
        self.logger.info("🔌 ConnectionManager инициализирован")
    
    def connect(self) -> bool:
        """
        Установка соединения с сервером с автоматическим переключением на SSL.
        
        Returns:
            True если соединение установлено, иначе False
        """
        max_attempts = 3
        
        # Пробуем сначала основной порт, затем SSL порт если основной не работает
        ports_to_try = [
            (IMAP_PORT, False, f"IMAP+STARTTLS на порту {IMAP_PORT}"),
            (IMAP_SSL_PORT, True, f"IMAPS на порту {IMAP_SSL_PORT}")
        ]
        
        for port_index, (port, use_ssl, description) in enumerate(ports_to_try):
            if port_index > 0:
                self.logger.info(f"🔄 Переключаемся на {description} (порт {port})")
            
            for attempt in range(max_attempts):
                try:
                    # Закрываем предыдущее соединение если есть
                    if self.mail:
                        try:
                            self.mail.logout()
                        except:
                            pass
                    
                    self.logger.info(
                        f"🔌 Подключение к {IMAP_SERVER}:{port} ({description}) (попытка {attempt + 1}/{max_attempts})..."
                    )
                    
                    # Устанавливаем новое соединение
                    if use_ssl:
                        self.mail = imaplib.IMAP4_SSL(IMAP_SERVER, port)
                    else:
                        self.mail = imaplib.IMAP4(IMAP_SERVER, port)
                        self.mail.starttls(ssl.create_default_context())
                    
                    self.mail.login(IMAP_USER, IMAP_PASSWORD)
                    self.mail.select("INBOX")
                    
                    self.last_connect_time = time.time()
                    self.is_connected = True
                    
                    self.logger.info(f"✅ Соединение успешно установлено ({description})")
                    return True
                    
                except (ConnectionResetByPeer, ConnectionResetError, OSError) as e:
                    error_msg = str(e)
                    self.logger.error(f"❌ Ошибка подключения ({description}, попытка {attempt + 1}): {e}")
                    
                    # Если это Connection reset by peer и мы на основном порту, переключаемся на SSL
                    if "Connection reset by peer" in error_msg and port_index == 0:
                        self.logger.info(f"🔄 Сервер разрывает соединение на порту {port}, переключаемся на SSL...")
                        break  # Выходим из цикла попыток и переключаемся на следующий порт
                    
                    if attempt < max_attempts - 1:
                        time.sleep(RETRY_DELAY)
                        
                except Exception as e:
                    self.logger.error(f"❌ Ошибка подключения ({description}, попытка {attempt + 1}): {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(RETRY_DELAY)
        
        self.is_connected = False
        return False
    
    def close(self):
        """Закрытие соединения."""
        if self.mail:
            try:
                self.mail.logout()
                self.logger.info("🔐 Соединение закрыто")
            except:
                pass
            finally:
                self.mail = None
                self.is_connected = False
    
    def reconnect(self) -> bool:
        """
        Переподключение к серверу.
        
        Returns:
            True если переподключение успешно, иначе False
        """
        self.logger.info("🔄 Переподключение к серверу...")
        self.close()
        return self.connect()
    
    def check_connection(self) -> bool:
        """
        Проверка состояния соединения.
        
        Returns:
            True если соединение активно, иначе False
        """
        if not self.mail or not self.is_connected:
            return False
        
        try:
            # Проверяем соединение командой NOOP
            status, _ = self.mail.noop()
            return status == "OK"
        except:
            self.is_connected = False
            return False
    
    def ensure_connection(self) -> bool:
        """
        Убедиться что соединение активно, при необходимости переподключиться.
        
        Returns:
            True если соединение активно, иначе False
        """
        if not self.check_connection():
            return self.reconnect()
        return True
    
    def safe_search(self, criteria: str) -> List[bytes]:
        """
        Безопасный поиск писем с автоматическим переподключением.
        
        Args:
            criteria: Критерии поиска IMAP
            
        Returns:
            Список ID писем
        """
        for attempt in range(MAX_RETRIES):
            try:
                if not self.ensure_connection():
                    continue
                
                status, data = self.mail.search(None, criteria)
                if status == "OK":
                    return data[0].split() if data else []
                else:
                    raise Exception(f"IMAP search returned: {status}")
                    
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Ошибка поиска (попытка {attempt + 1}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    if not self.reconnect():
                        continue
                else:
                    self.logger.error("❌ Поиск не удался")
                    return []
        
        return []
    
    def safe_fetch(self, msg_id: bytes, flags: str = "(RFC822)") -> Optional[List]:
        """
        Безопасное получение письма с retry логикой и таймаутами.
        
        Args:
            msg_id: ID письма
            flags: Флаги получения
            
        Returns:
            Данные письма или None
        """
        for attempt in range(MAX_RETRIES):
            try:
                if not self.ensure_connection():
                    continue
                
                time.sleep(REQUEST_DELAY)
                
                # Устанавливаем таймаут
                timeout_seconds = 30 + (attempt * 15)
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(
                        f"Fetch операция превысила {timeout_seconds} секунд"
                    )
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)
                
                try:
                    fetch_start = time.time()
                    status, data = self.mail.fetch(msg_id, flags)
                    fetch_time = time.time() - fetch_start
                    signal.alarm(0)
                    
                    if status == "OK":
                        if data:
                            return data
                        else:
                            self.logger.warning("⚠️ Пустые данные в ответе")
                            return None
                    else:
                        raise Exception(f"IMAP fetch returned: {status}")
                        
                except TimeoutError:
                    signal.alarm(0)
                    raise
                    
            except TimeoutError as e:
                self.logger.error(f"⏰ ТАЙМАУТ на попытке {attempt + 1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    self.logger.info("🔄 Переподключение после таймаута...")
                    if not self.reconnect():
                        continue
                else:
                    self.logger.warning("⚠️ Все попытки исчерпаны")
                    return None
                    
            except (imaplib.IMAP4.abort, ssl.SSLError, OSError, ConnectionError) as e:
                self.logger.warning(f"⚠️ Сетевая ошибка (попытка {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    self.logger.info(f"🔄 Переподключение через {RETRY_DELAY} сек...")
                    time.sleep(RETRY_DELAY)
                    if not self.reconnect():
                        continue
                else:
                    return None
                    
            except Exception as e:
                self.logger.error(f"❌ Неожиданная ошибка: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    return None
        
        return None
    
    def fetch_headers(self, msg_id: bytes) -> Optional[List]:
        """
        Получение только заголовков письма.
        
        Args:
            msg_id: ID письма
            
        Returns:
            Заголовки письма или None
        """
        return self.safe_fetch(msg_id, "(BODY.PEEK[HEADER])")
    
    def fetch_bodystructure(self, msg_id: bytes) -> Optional[List]:
        """
        Получение структуры письма.
        
        Args:
            msg_id: ID письма
            
        Returns:
            Структура письма или None
        """
        return self.safe_fetch(msg_id, "(BODYSTRUCTURE)")
    
    def fetch_text_only(self, msg_id: bytes) -> Optional[List]:
        """
        Получение только текста письма (без вложений).
        
        Args:
            msg_id: ID письма
            
        Returns:
            Текст письма или None
        """
        return self.safe_fetch(msg_id, "(BODY.PEEK[HEADER] BODY.PEEK[TEXT])")
    
    def get_connection_info(self) -> dict:
        """
        Получение информации о соединении.
        
        Returns:
            Словарь с информацией о соединении
        """
        return {
            "server": IMAP_SERVER,
            "port": IMAP_PORT,
            "user": IMAP_USER,
            "is_connected": self.is_connected,
            "last_connect_time": self.last_connect_time,
            "connection_age": time.time() - self.last_connect_time if self.last_connect_time > 0 else 0
        }