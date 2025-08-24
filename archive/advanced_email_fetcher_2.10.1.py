
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 Продвинутый IMAP-парсер v2.10.1 - ИСПРАВЛЕНИЕ КРИТИЧЕСКИХ БАГОВ И УЛУЧШЕНИЯ
Исправлено: черный список, извлечение email адресов, дублированный код, extract_raw_email
"""

import os
import re
import ssl
import imaplib
import email
import email.message
import email.utils
import json
import time
import hashlib
import logging
import fnmatch
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
from dotenv import load_dotenv
from PIL import Image

# Загружаем переменные окружения
load_dotenv()

# Настройки подключения
IMAP_SERVER = os.getenv('IMAP_SERVER')
IMAP_PORT = int(os.getenv('IMAP_PORT', 143))
IMAP_USER = os.getenv('IMAP_USER')
IMAP_PASSWORD = os.getenv('IMAP_PASSWORD')
COMPANY_DOMAIN = os.getenv('COMPANY_DOMAIN', 'dna-technology.ru')
WIFE_EMAIL = os.getenv('IMAP_USER')

# Настройки устойчивости
MAX_RETRIES = 5 # Увеличено до 5 попыток
RETRY_DELAY = 5
BATCH_SIZE = 50
REQUEST_DELAY = 0.5

# 🆕 ПОДДЕРЖИВАЕМЫЕ типы вложений (только разрешенные)
SUPPORTED_ATTACHMENTS = {
    # Документы
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
    # Excel файлы (все варианты)
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xlsm': 'application/vnd.ms-excel.sheet.macroEnabled.12',
    # Изображения (все форматы)
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.webp': 'image/webp',
}

# 🚫 ИСКЛЮЧЕННЫЕ расширения (НЕ скачиваем вообще)
EXCLUDED_EXTENSIONS = {
    '.zip', '.rar', '.7z',  # Архивы
    '.pptx', '.ppt',  # PowerPoint презентации
    '.rt', '.rtf',  # Rich Text (устаревший)
    '.trt', '.tr','.r96',  # Технические форматы
    '.exe', '.msi', '.dmg',  # Исполняемые файлы
    '.iso', '.img',  # Образы дисков
}

# Настройка местного времени UTC+7
LOCAL_TIMEZONE = timezone(timedelta(hours=7))

def setup_logging(logs_dir: Path, start_date: datetime, end_date: datetime):
    """📝 Настройка логирования в файл и консоль одновременно"""
    # Создаем папку для логов
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем имя файла лога на основе диапазона дат
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    timestamp = int(time.time())
    log_filename = f"email_processing_{start_str}_{end_str}_{timestamp}.log"
    log_path = logs_dir / log_filename
    
    # Настраиваем форматирование
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y.%m.%d %H:%M:%S'
    
    # Создаем логгер
    logger = logging.getLogger('EmailFetcher')
    logger.setLevel(logging.DEBUG)
    
    # Очищаем существующие обработчики
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Обработчик для файла
    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Добавляем обработчики к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Первая запись в лог
    logger.info("="*70)
    logger.info(f"📧 ЗАПУСК ОБРАБОТКИ ПИСЕМ ЗА ПЕРИОД {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"📝 Лог файл: {log_path}")
    logger.info(f"🕒 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)
    
    return logger

class EmailFilters:
    """🚫 Класс для управления фильтрами исключений"""

    def __init__(self, config_dir: Path, logger):
        self.config_dir = config_dir
        self.logger = logger
        self.subject_filters: Set[str] = set()
        self.blacklist: Set[str] = set()
        self.filename_excludes: List[str] = []
        self.load_filters()

    def load_filters(self):
        """📋 Загрузка фильтров из файлов"""
        # Загружаем фильтры тем
        filters_file = self.config_dir / 'filters.txt'
        if filters_file.exists():
            try:
                with open(filters_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.subject_filters.add(line.lower())
                self.logger.info(f"✅ Загружено {len(self.subject_filters)} фильтров тем")
            except Exception as e:
                self.logger.error(f"❌ Ошибка загрузки фильтров: {e}")

        # Загружаем черный список
        blacklist_file = self.config_dir / 'blacklist.txt'
        if blacklist_file.exists():
            try:
                with open(blacklist_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            self.blacklist.add(line.lower())
                self.logger.info(f"✅ Загружено {len(self.blacklist)} адресов в черном списке")
                self.logger.info(f"   Примеры: {list(self.blacklist)[:3]}")
            except Exception as e:
                self.logger.error(f"❌ Ошибка загрузки черного списка: {e}")

        # Загружаем исключения по именам файлов
        filename_excludes_file = self.config_dir / 'attachment_filename_excludes.txt'
        if filename_excludes_file.exists():
            try:
                with open(filename_excludes_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if line == '****':
                                self.logger.warning(f"⚠️ Пропускаем проблемный паттерн: {line}")
                                continue
                            self.filename_excludes.append(line)
                self.logger.info(f"✅ Загружено {len(self.filename_excludes)} исключений по именам файлов")
            except Exception as e:
                self.logger.error(f"❌ Ошибка загрузки исключений имён файлов: {e}")

    def is_subject_filtered(self, subject: str) -> Optional[str]:
        """🚫 Проверка темы письма на исключение"""
        if not subject:
            return None
        subject_lower = subject.lower()
        for filter_word in self.subject_filters:
            if filter_word in subject_lower:
                return f"тема содержит '{filter_word}'"
        return None

    def is_sender_blacklisted(self, from_addr: str) -> Optional[str]:
        """🚫 ИСПРАВЛЕННАЯ проверка отправителя в черном списке"""
        if not from_addr:
            return None
        
        from_addr_lower = from_addr.lower().strip()
        
        # 🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: добавляем отладочный лог
        self.logger.debug(f"Проверяем адрес '{from_addr_lower}' против {len(self.blacklist)} правил")
        
        for blacklisted in self.blacklist:
            blacklisted = blacklisted.strip().lower()
            
            if blacklisted.endswith('*'):
                # Маски типа info@*, newsletter@*, marketing@*
                prefix = blacklisted[:-1]  # убираем звездочку
                if from_addr_lower.startswith(prefix):
                    return f"адрес начинается с '{prefix}' (в черном списке)"
                    
            elif blacklisted.startswith('*@'):
                # Маски типа *@domain.com
                domain = blacklisted[2:]  # убираем *@
                if from_addr_lower.endswith(f"@{domain}"):
                    return f"домен в черном списке ({domain})"
                    
            else:
                # Точные совпадения
                if from_addr_lower == blacklisted:
                    return f"адрес в черном списке"
        
        return None

    def is_filename_excluded(self, filename: str) -> Optional[str]:
        """🚫 ИСПРАВЛЕННАЯ проверка имени файла с диагностикой"""
        if not filename or not self.filename_excludes:
            return None

        # ✅ ДОБАВИТЬ: диагностика для отладки
        self.logger.debug(f"🔍 Проверка файла '{filename}' против {len(self.filename_excludes)} паттернов")

        for exclude_pattern in self.filename_excludes:
            if '*' in exclude_pattern:
                # Wildcard паттерн
                if fnmatch.fnmatch(filename.lower(), exclude_pattern.lower()):
                    self.logger.info(f"🚫 ФАЙЛ ИСКЛЮЧЕН ПО ПАТТЕРНУ: {filename} → {exclude_pattern}")
                    return f"имя файла соответствует паттерну '{exclude_pattern}'"
            else:
                # Точное совпадение
                if filename == exclude_pattern:
                    self.logger.info(f"🚫 ФАЙЛ ИСКЛЮЧЕН ПО ТОЧНОМУ ИМЕНИ: {filename}")
                    return f"имя файла точно соответствует '{exclude_pattern}'"

        # ✅ ДОБАВИТЬ: лог если фильтр не сработал
        self.logger.debug(f"✅ Файл '{filename}' прошел все фильтры имен")
        return None


    def is_internal_mass_mailing(self, from_addr: str, to_addrs: List[str], cc_addrs: List[str] = None) -> Optional[str]:
        """🚫 Проверка на внутреннюю массовую рассылку"""
        if not from_addr or f"@{COMPANY_DOMAIN}" not in from_addr.lower():
            return None

        all_recipients = []
        all_recipients.extend(to_addrs or [])
        all_recipients.extend(cc_addrs or [])

        internal_recipients = 0
        for recipient in all_recipients:
            if f"@{COMPANY_DOMAIN}" in recipient.lower():
                internal_recipients += 1

        if internal_recipients >= 10:
            return f"массовая внутренняя рассылка ({internal_recipients} получателей)"

        return None

class AdvancedEmailFetcherV2:
    """🔥 Продвинутый парсер v2.10.1 - ИСПРАВЛЕНИЕ КРИТИЧЕСКИХ БАГОВ"""

    def __init__(self, logger):
        self.mail = None
        self.logger = logger
        self.last_connect_time = 0

        # Создаем папки для данных
        self.data_dir = Path("data")
        self.emails_dir = self.data_dir / "emails"
        self.attachments_dir = self.data_dir / "attachments"
        self.logs_dir = self.data_dir / "logs"
        self.config_dir = Path("config")

        for dir_path in [self.emails_dir, self.attachments_dir, self.logs_dir, self.config_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Инициализируем фильтры
        self.filters = EmailFilters(self.config_dir, self.logger)

        # Счетчики для статистики
        self.stats = {
            'processed': 0,
            'saved': 0,
            'filtered_subject': 0,
            'filtered_blacklist': 0,
            'filtered_mass_mailing': 0,
            'saved_attachments': 0,
            'saved_inline_images': 0,
            'excluded_attachments': 0,
            'excluded_filenames': 0,
            'excluded_by_size': 0,
            'excluded_by_image_dimensions': 0,
            'unsupported_attachments': 0,
            'skipped_large_emails': 0,
            'errors': 0,
            'retry_successful': 0,  # ✅ ДОБАВИТЬ
            'retry_failed': 0,      # ✅ ДОБАВИТЬ
            'total_skipped': 0      # ✅ ДОБАВИТЬ
        }

        # ✅ ДОБАВИТЬ: Флаг управления детальным логированием
        self.enable_size_logging = False  # По умолчанию отключено для продакшена (False), для диагностики - True

    def safe_parse_size(self, size_str) -> int:
        """🛡️ Безопасное преобразование БЕЗ спама в логах"""
        try:
            size = int(size_str)
            if 0 <= size < 1_000_000_000:
                return size
            else:
                if size > 1_000_000_000:
                    self.logger.warning(f"   ⚠️ Подозрительно большой размер: {size} байт")
                return 0
        except (ValueError, TypeError):
            return 0
    
    def check_email_size(self, msg_id: bytes) -> int:
        """📏 Проверка размера письма в байтах"""
        try:
            status, data = self.mail.fetch(msg_id, '(RFC822.SIZE)')
            
            # ✅ УСЛОВНОЕ ЛОГИРОВАНИЕ
            if self.enable_size_logging:
                self.logger.info(f"📡 RFC822.SIZE - статус: {status}, данные: {data}")

            if status == 'OK' and data:
                size_str = str(data[0])
                import re
                m = re.search(r'RFC822\.SIZE (\d+)', size_str)
                
                if m:
                    real_size = int(m.group(1))
                    
                    if real_size == 0:
                        if self.enable_size_logging:
                            self.logger.warning("⚠️ Сервер вернул нулевой размер письма")
                        return -1
                    
                    if self.enable_size_logging:
                        self.logger.info(f"🔍 Общий размер письма: {real_size} байт ({real_size/1024:.1f} КБ)")
                    
                    return real_size
                else:
                    if self.enable_size_logging:
                        self.logger.warning(f"⚠️ Не удалось распарсить размер письма из строки: {size_str}")
                    return -1
                    
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения размера письма: {e}")
        
        return -1



    def save_skipped_email(self, msg_id: bytes, date_str: str, reason: str = "unknown"):
        """💾 Сохранение пропущенного письма для повторной обработки"""
        skipped_path = self.data_dir / 'skipped_emails.json'
        
        # Загружаем существующий список
        skipped = {}
        if skipped_path.exists():
            try:
                with open(skipped_path, 'r', encoding='utf-8') as f:
                    skipped = json.load(f)
            except Exception:
                skipped = {}
        
        # Добавляем новое пропущенное письмо
        key = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
        attempts = skipped.get(key, {}).get('attempts', 0)
        
        # Ограничиваем количество попыток
        if attempts >= 3:
            self.logger.warning(f"⚠️ Письмо {key} уже имеет {attempts} попыток, не добавляем в очередь")
            return
        
        skipped[key] = {
            'date': date_str,
            'reason': reason,
            'attempts': attempts + 1,
            'last_attempt': self.get_local_time().isoformat()
        }
        
        with open(skipped_path, 'w', encoding='utf-8') as f:
            json.dump(skipped, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"💾 Письмо {key} сохранено для повторной обработки (попытка {attempts + 1}/3, причина: {reason})")

    def load_skipped_emails(self) -> Dict[str, dict]:
        """📋 Загрузка списка пропущенных писем"""
        skipped_path = self.data_dir / 'skipped_emails.json'
        if skipped_path.exists():
            try:
                with open(skipped_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def remove_skipped_email(self, msg_id: bytes):
        """🗑️ Удаление письма из списка пропущенных"""
        skipped_path = self.data_dir / 'skipped_emails.json'
        if not skipped_path.exists():
            return
        
        key = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
        skipped = self.load_skipped_emails()
        
        if key in skipped:
            del skipped[key]
            # ✅ ИСПРАВЛЕНО: обязательно сохраняем файл после удаления
            with open(skipped_path, 'w', encoding='utf-8') as f:
                json.dump(skipped, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ Письмо удалено из очереди повтора: {key}")

    def retry_skipped_emails(self):
        """🔄 Повторная обработка пропущенных писем"""
        skipped = self.load_skipped_emails()
        
        if not skipped:
            self.logger.info("📭 Нет пропущенных писем для повторной обработки")
            return
        
        self.logger.info("=" * 70)
        self.logger.info(f"🔄 ПОВТОРНАЯ ОБРАБОТКА ПРОПУЩЕННЫХ ПИСЕМ: {len(skipped)} в очереди")
        self.logger.info("=" * 70)
        
        successful_retries = 0
        failed_retries = 0
        
        # ✅ ИСПРАВЛЕНО: работаем с копией ключей
        for key in list(skipped.keys()):
            info = skipped[key]
            attempts = info.get('attempts', 0)
            date_str = info.get('date', '')
            reason = info.get('reason', 'unknown')
            
            if attempts >= 3:
                self.logger.warning(f"⚠️ Превышено число попыток для письма {key}")
                failed_retries += 1
                continue
            
            self.logger.info(f"🔄 Повторная попытка {attempts}/3: {key} за {date_str}")
            self.logger.info(f"   Причина пропуска: {reason}")
            
            try:
                msg_id = key.encode() if isinstance(key, str) else key
                email_data = self.process_single_email(msg_id, date_str, 1, 1)
                
                if email_data:
                    # ✅ ИСПРАВЛЕНО: удаляем из файла И из локального словаря
                    self.remove_skipped_email(msg_id)
                    skipped.pop(key, None)  # Удаляем из локальной копии
                    self.logger.info(f"✅ Письмо {key} успешно обработано при повторе!")
                    successful_retries += 1
                else:
                    self.logger.warning(f"❌ Письмо {key} снова не удалось обработать")
                    # ✅ УВЕЛИЧИВАЕМ СЧЕТЧИК ПОПЫТОК
                    skipped[key]['attempts'] = attempts + 1
                    skipped[key]['last_attempt'] = self.get_local_time().isoformat()
                    failed_retries += 1
                    
            except Exception as e:
                self.logger.error(f"❌ Ошибка при повторе письма {key}: {e}")
                failed_retries += 1
        
        # ✅ ИСПРАВЛЕНО: сохраняем обновленный список в файл
        skipped_path = self.data_dir / 'skipped_emails.json'
        with open(skipped_path, 'w', encoding='utf-8') as f:
            json.dump(skipped, f, ensure_ascii=False, indent=2)
        
        self.logger.info("=" * 70)
        self.logger.info(f"📊 ИТОГИ ПОВТОРНОЙ ОБРАБОТКИ:")
        self.logger.info(f"✅ Успешно обработано: {successful_retries}")
        self.logger.info(f"❌ Осталось в очереди: {len(skipped)}")
        self.logger.info("=" * 70)


    def get_local_time(self, dt: datetime = None) -> datetime:
        """🕒 Получение местного времени UTC+7"""
        if dt is None:
            dt = datetime.now(LOCAL_TIMEZONE)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=LOCAL_TIMEZONE)
        return dt

    def parse_email_date(self, date_header: str) -> datetime:
        """📅 Парсинг даты письма из заголовка с приведением к UTC+7"""
        try:
            parsed_date = email.utils.parsedate_to_datetime(date_header)
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            local_date = parsed_date.astimezone(LOCAL_TIMEZONE)
            return local_date
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка парсинга даты '{date_header}': {e}")
            return self.get_local_time()

    def format_email_date_for_log(self, date_header: str) -> str:
        """📅 Форматирование даты письма для лога"""
        email_date = self.parse_email_date(date_header)
        return email_date.strftime('%Y.%m.%d %H:%M')

    def connect(self) -> bool:
        """🔌 Подключение к серверу"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if self.mail:
                    try:
                        self.mail.logout()
                    except:
                        pass

                self.logger.info(f"🔌 Подключение к {IMAP_SERVER} (попытка {attempt + 1}/{max_attempts})...")
                self.mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
                self.mail.starttls(ssl.create_default_context())
                self.mail.login(IMAP_USER, IMAP_PASSWORD)
                self.mail.select('INBOX')
                self.last_connect_time = time.time()
                self.logger.info(f"✅ Подключение успешно")
                return True

            except Exception as e:
                self.logger.error(f"❌ Ошибка подключения (попытка {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    time.sleep(RETRY_DELAY)

        return False

    def safe_fetch(self, msg_id: bytes, flags: str = '(RFC822)') -> Optional[List]:
        """🛡️ УЛУЧШЕННОЕ получение письма с fallback стратегиями"""
        for attempt in range(MAX_RETRIES):
            try:
                time.sleep(REQUEST_DELAY)
                
                try:
                    status, response = self.mail.noop()
                except Exception as e:
                    self.logger.warning(f"   ⚠️ NOOP failed: {e}")
                    raise ConnectionError("IMAP connection lost")

                timeout_seconds = 30 + (attempt * 15)  # 30, 45, 60 секунд
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Fetch операция превысила {timeout_seconds} секунд")

                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)

                try:
                    fetch_start = time.time()
                    status, data = self.mail.fetch(msg_id, flags)
                    fetch_time = time.time() - fetch_start
                    signal.alarm(0)

                    if status == 'OK':
                        if data:
                            return data
                        else:
                            self.logger.warning(f"   ⚠️ Пустые данные в ответе")
                            return None
                    else:
                        raise Exception(f"IMAP fetch returned: {status}")

                except TimeoutError:
                    signal.alarm(0)
                    raise

            except TimeoutError as e:
                self.logger.error(f"   ⏰ ТАЙМАУТ на попытке {attempt + 1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    self.logger.info(f"   🔄 Переподключение после таймаута...")
                    if not self.connect():
                        continue
                else:
                    self.logger.warning(f"   ⚠️ Все попытки исчерпаны, пробуем fallback...")
                    return self.try_fallback_fetch(msg_id)

            except (imaplib.IMAP4.abort, ssl.SSLError, OSError, ConnectionError) as e:
                self.logger.warning(f"   ⚠️ Сетевая ошибка (попытка {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    self.logger.info(f"   🔄 Переподключение через {RETRY_DELAY} сек...")
                    time.sleep(RETRY_DELAY)
                    if not self.connect():
                        continue
                else:
                    return None

            except Exception as e:
                self.logger.error(f"   ❌ Неожиданная ошибка: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    return None

        return None

    def try_fallback_fetch(self, msg_id: bytes) -> Optional[List]:
        """🔧 Улучшенный fallback: загрузка без вложений"""
        try:
            self.logger.info("   🆘 Пробуем загрузить только заголовки и текст...")
            
            # Попытка 1: Только заголовки и текст без вложений
            status, data = self.mail.fetch(msg_id, '(BODY.PEEK[HEADER] BODY.PEEK[TEXT])')
            if status == 'OK' and data:
                self.logger.info("   ✅ Fallback успешен - загружены заголовки и текст")
                return data
                
            # Попытка 2: Только заголовки
            self.logger.info("   🆘 Пробуем загрузить только заголовки...")
            status, data = self.mail.fetch(msg_id, '(BODY.PEEK[HEADER])')
            if status == 'OK' and data:
                self.logger.info("   ✅ Fallback частично успешен - загружены только заголовки")
                return [(b'FALLBACK', b'HEADERS_ONLY')]
                
            return None
            
        except Exception as e:
            self.logger.error(f"   ❌ Fallback не сработал: {e}")
            return None


    def extract_raw_email(self, fetch_data) -> Optional[bytes]:
        """🔧 ИСПРАВЛЕННОЕ извлечение сырых байтов письма из fetch_data"""
        try:
            if not fetch_data:
                self.logger.error(f"   ❌ fetch_data пустой")
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

                # 🔧 ИСПРАВЛЕНО: правильная проверка первого элемента
                try:
                    if len(fetch_data) > 0:
                        first_item = fetch_data[0]
                        if isinstance(first_item, bytes) and len(first_item) > 500:
                            return first_item
                        elif isinstance(first_item, tuple) and len(first_item) > 1:
                            second_element = first_item[1]
                            if isinstance(second_element, bytes) and len(second_element) > 500:
                                return second_element
                except (IndexError, TypeError):
                    pass

            elif isinstance(fetch_data, bytes):
                return fetch_data

            self.logger.error(f"   ❌ Не удалось найти байты письма в структуре данных")
            return None

        except Exception as e:
            self.logger.error(f"   ❌ Критическая ошибка в extract_raw_email: {e}")
            return None

    def safe_search(self, criteria: str) -> List[bytes]:
        """🔍 Безопасный поиск писем"""
        for attempt in range(MAX_RETRIES):
            try:
                status, data = self.mail.search(None, criteria)
                if status == 'OK':
                    return data[0].split() if data else []
                else:
                    raise Exception(f"IMAP search returned: {status}")
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка поиска (попытка {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    if not self.connect():
                        continue
                else:
                    self.logger.error(f"❌ Поиск не удался")
                    return []
        return []

    def get_email_headers_only(self, msg_id: bytes) -> Optional[email.message.Message]:
        """📋 УСТОЙЧИВАЯ загрузка заголовков с переподключением"""
        for attempt in range(MAX_RETRIES):
            try:
                status, header_data = self.mail.fetch(msg_id, '(BODY.PEEK[HEADER])')
                if status != 'OK':
                    raise Exception(f"Ошибка загрузки заголовков: {status}")

                raw_headers = self.safe_extract_headers(header_data)
                if raw_headers is None:
                    self.logger.error(f"   ❌ Не удалось извлечь сырые заголовки из ответа IMAP")
                    return None

                headers_msg = email.message_from_bytes(raw_headers)
                return headers_msg

            except (OSError, imaplib.IMAP4.error) as e:
                self.logger.warning(f"   ⚠️ Сетевая ошибка загрузки заголовков (попытка {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    self.logger.info(f"   🔄 Переподключение...")
                    if self.connect():
                        continue
                return None

            except Exception as e:
                self.logger.error(f"   ❌ Ошибка в get_email_headers_only: {e}")
                return None

        return None

    def safe_extract_headers(self, header_data):
        """🛡️ МАКСИМАЛЬНО защищенное извлечение заголовков"""
        try:
            if not header_data:
                self.logger.error(f"   ❌ header_data пустой")
                return None

            if isinstance(header_data, (list, tuple)):
                for i, item in enumerate(header_data):
                    if isinstance(item, tuple):
                        for j in range(len(item)):
                            try:
                                element = item[j]
                                if isinstance(element, bytes) and j > 0:
                                    if len(element) > 50:
                                        return element
                            except IndexError:
                                continue
                    elif isinstance(item, bytes) and len(item) > 50:
                        return item

                try:
                    if len(header_data) > 0 and isinstance(header_data[0], bytes) and len(header_data) > 50:
                        return header_data
                except (IndexError, TypeError):
                    pass

            elif isinstance(header_data, bytes):
                return header_data

            self.logger.error(f"   ❌ Не удалось найти заголовки в структуре данных")
            return None

        except Exception as e:
            self.logger.error(f"   ❌ Критическая ошибка в safe_extract_headers: {e}")
            return None

    def analyze_bodystructure(self, msg_id: bytes) -> Dict:
        """🔍 ИСПРАВЛЕННЫЙ анализ структуры письма"""
        try:
            status, structure_data = self.mail.fetch(msg_id, '(BODYSTRUCTURE)')
            if status != 'OK':
                return {'has_large_attachments': False, 'structure': ''}

            structure_str = ''
            if structure_data and len(structure_data) > 0:
                structure_item = structure_data[0]
                if isinstance(structure_item, bytes):
                    structure_str = structure_item.decode('utf-8', errors='ignore')
                elif isinstance(structure_item, str):
                    structure_str = structure_item
                else:
                    structure_str = str(structure_item)

            has_large = self.detect_large_attachments_from_structure(structure_str)
            return {
                'has_large_attachments': has_large,
                'structure': structure_str
            }

        except Exception as e:
            self.logger.warning(f"   ⚠️ Ошибка анализа структуры: {e}")
            return {'has_large_attachments': False, 'structure': ''}

    def detect_large_attachments_from_structure(self, structure_str: str) -> bool:
        """🔍 ИСПРАВЛЕННОЕ определение больших вложений из структуры"""
        try:
            if not structure_str:
                return False

            structure_lower = structure_str.lower()
            
            # ✅ УСЛОВНОЕ ЛОГИРОВАНИЕ
            if self.enable_size_logging:
                self.logger.info(f"🔍 Анализ структуры письма...")
                self.logger.info(f"📋 Начальные символы структуры: {structure_str[:500]}...")

            if 'attachment' not in structure_lower and 'application' not in structure_lower:
                if self.enable_size_logging:
                    self.logger.info(f"📋 Нет вложений в структуре")
                return False

            # Поиск больших файлов по типу
            large_indicators = [
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/zip',
                'application/x-zip-compressed',
                'video/',
                'audio/',
            ]

            for indicator in large_indicators:
                if indicator in structure_lower:
                    if self.enable_size_logging:
                        self.logger.info(f"⚠️ Обнаружен потенциально большой файл: {indicator}")
                    return True

            # Анализ размеров с фильтрацией boundary ID
            import re
            size_matches = re.findall(r'(\d+)', structure_lower)
            
            valid_sizes = []
            suspicious_numbers = []
            
            for size_str in size_matches:
                size = self.safe_parse_size(size_str)
                
                # Пропускаем boundary ID
                if len(size_str) == 8 and 'boundary' in structure_lower and size_str in structure_lower:
                    if self.enable_size_logging:
                        self.logger.info(f"🔍 Пропускаем boundary ID: {size}")
                    continue
                    
                # Классифицируем размеры
                if 10_000 <= size <= 200_000_000:  # От 10KB до 200MB
                    valid_sizes.append(size)
                elif size > 200_000_000:
                    suspicious_numbers.append(size)
            
            # Логируем найденные размеры
            if self.enable_size_logging:
                if valid_sizes:
                    self.logger.info(f"📊 Разумные размеры в структуре: {valid_sizes}")
                if suspicious_numbers:
                    self.logger.info(f"🔍 Подозрительные большие числа (игнорируем): {suspicious_numbers[:5]}...")

            # Проверяем на большие компоненты
            for size in valid_sizes:
                if size > 20_000_000:  # 20MB
                    if self.enable_size_logging:
                        self.logger.info(f"⚠️ Обнаружен большой компонент: {size} байт ({size/1024/1024:.1f} МБ)")
                    return True

            if self.enable_size_logging:
                self.logger.info(f"✅ Все компоненты имеют приемлемый размер")
            return False

        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка анализа размеров структуры: {e}")
            return False


    def decode_header_value(self, val: str) -> str:
        """📝 ИСПРАВЛЕННОЕ декодирование MIME-заголовков с правильным извлечением email"""
        from email.header import decode_header, make_header
        import re
        
        try:
            decoded = str(make_header(decode_header(val or '')))
            
            # 🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: правильное извлечение email из угловых скобок
            email_match = re.search(r'<([^>]+)>', decoded)
            if email_match:
                return email_match.group(1).strip()
            else:
                # Если нет скобок, ищем email в строке
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                email_match = re.search(email_pattern, decoded)
                return email_match.group(0).strip() if email_match else decoded.strip()
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка декодирования заголовка '{val}': {e}")
            return val or ''

    def extract_plain_text(self, msg: email.message.Message) -> str:
        """📄 Извлечение текста письма"""
        text_parts = []
        max_len = 500_000
        
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype in ('text/plain', 'text/html'):
                        try:
                            raw = part.get_payload(decode=True)
                            charset = part.get_content_charset() or 'utf-8'
                            chunk = raw.decode(charset, errors='ignore')
                            
                            if ctype == 'text/html':
                                chunk = re.sub(r'<[^>]+>', '', chunk)
                                chunk = re.sub(r'&[a-z]+;', ' ', chunk)
                            
                            text_parts.append(chunk)
                        except Exception as e:
                            self.logger.warning(f"⚠️ Ошибка извлечения текста: {e}")
                            continue
            else:
                try:
                    raw = msg.get_payload(decode=True)
                    if raw:
                        charset = msg.get_content_charset() or 'utf-8'
                        text_parts.append(raw.decode(charset, errors='ignore'))
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка извлечения простого текста: {e}")

            full_text = '\n'.join(text_parts)
            return full_text[:max_len].strip()
        
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка извлечения текста: {e}")
            return ""

    def parse_recipient(self, recipients_str: str) -> List[str]:
        """📧 Парсинг списка получателей"""
        if not recipients_str:
            return []
        
        # Простой парсинг email адресов
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, recipients_str)
        return emails

    def save_attachment_or_inline(self, part: email.message.Message, thread_id: str, date_folder: str, is_inline: bool = False) -> Optional[Dict]:
        """📎 Сохранение вложения с детальной диагностикой размеров"""
        
        try:
            # Для встроенных изображений имя файла может отсутствовать
            filename = part.get_filename()
            content_type = part.get_content_type()
            
            # 🆕 Обработка встроенных изображений без имени файла
            if not filename and is_inline and content_type.startswith('image/'):
                # Создаем имя файла на основе content-type
                extension_map = {
                    'image/jpeg': '.jpg',
                    'image/png': '.png',
                    'image/gif': '.gif',
                    'image/bmp': '.bmp',
                    'image/tiff': '.tiff',
                    'image/webp': '.webp'
                }
                extension = extension_map.get(content_type, '.img')
                
                # Создаем уникальное имя файла
                timestamp = self.get_local_time().strftime('%H%M%S_%f')
                filename = f"inline_image_{timestamp}{extension}"
                self.logger.info(f"🖼️ Встроенное изображение без имени, создаем: {filename}")
            
            if not filename:
                return None
            
            # Декодируем имя файла
            filename = self.decode_header_value(filename)

            # 🆕 ФИЛЬТРАЦИЯ ПО РАЗМЕРУ И ПАРАМЕТРАМ ИЗОБРАЖЕНИЯ
            if is_inline or (filename and Path(filename).suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        # Проверяем размер файла
                        file_size = len(payload)

                        # ✅ Детальное логирование каждого вложения
                        #self.logger.info(f"🔍 Анализ вложения: {filename}")
                        #self.logger.info(f"📏 Реальный размер файла: {file_size} байт ({file_size / 1024:.1f} КБ)")

                        # ✅ УМНЫЙ ФИЛЬТР: разные пороги для разных типов файлов
                        size_thresholds = {
                            'image': 50000,      # 50 КБ для image*
                            'logo': 30000,       # 30 КБ для logo*
                            'signature': 30000,  # 30 КБ для signature*
                            'stamp': 30000,      # 30 КБ для stamp*
                            'icon': 20000,       # 20 КБ - иконки
                        }
                            
                        for pattern, threshold in size_thresholds.items():
                            if filename and filename.lower().startswith(pattern) and file_size < threshold:
                                self.logger.info(f"🚫 ИСКЛЮЧЕН МЕЛКИЙ МУСОРНЫЙ ФАЙЛ: {filename} - {file_size} байт (паттерн: {pattern})")
                                self.stats['excluded_by_size'] += 1
                                return {
                                    "original_filename": filename,
                                    "status": "excluded_by_size",
                                    "file_size": file_size,
                                    "exclusion_reason": f"мелкий мусорный файл {pattern} < {threshold} байт",
                                    "is_inline": is_inline
                                }

                        # ✅ Фильтр по размеру конкретного вложения
                        if file_size > 10_000_000:  # 10MB для отдельного файла
                            self.logger.info(f"🚫 ИСКЛЮЧЕНО: файл слишком большой - {file_size} байт")
                            self.stats['excluded_by_size'] += 1
                            return {
                                "original_filename": filename,
                                "status": "excluded_by_size",
                                "file_size": file_size,
                                "is_inline": is_inline
                            }

                        # Точный размер мусорных файлов
                        if file_size == 83509:
                            self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО РАЗМЕРУ ФАЙЛА: {filename} - {file_size} байт (мусорное изображение)")
                            self.stats['excluded_by_size'] += 1
                            return {
                                "original_filename": filename,
                                "saved_filename": None,
                                "file_path": None,
                                "relative_path": None,
                                "file_size": file_size,
                                "file_type": "excluded_by_size",
                                "exclusion_reason": f"размер файла {file_size} байт - известный мусорный файл",
                                "saved_at": self.get_local_time().isoformat(),
                                "status": "excluded_by_size",
                                "is_inline": is_inline
                            }
                        

                        # 🆕 Проверяем размеры изображения через PIL
                        try:
                            img = Image.open(io.BytesIO(payload))
                            width, height = img.size
                            
                            # Исключаем изображения 416×250 (мусорные)
                            if width == 416 and height == 250:
                                self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО РАЗМЕРАМ ИЗОБРАЖЕНИЯ: {filename} - {width}×{height} пикселей")
                                self.stats['excluded_by_image_dimensions'] += 1
                                return {
                                    "original_filename": filename,
                                    "saved_filename": None,
                                    "file_path": None,
                                    "relative_path": None,
                                    "file_size": file_size,
                                    "file_type": "excluded_by_image_size",
                                    "exclusion_reason": f"размеры изображения {width}×{height} - известный мусорный формат",
                                    "saved_at": self.get_local_time().isoformat(),
                                    "status": "excluded_by_size",
                                    "is_inline": is_inline,
                                    "image_dimensions": f"{width}×{height}"
                                }
                                
                        except Exception as e:
                            # Если не удалось проанализировать как изображение, продолжаем
                            self.logger.warning(f"⚠️ Не удалось проанализировать изображение {filename}: {e}")
                            pass
                            
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка анализа размера файла {filename}: {e}")
            
            # 🚫 ВТОРАЯ ПРОВЕРКА: Исключенные расширения
            file_ext = Path(filename).suffix.lower()
            
            if file_ext in EXCLUDED_EXTENSIONS:
                self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО РАСШИРЕНИЮ: {filename} - расширение {file_ext} в черном списке")
                self.stats['excluded_attachments'] += 1
                return {
                    "original_filename": filename,
                    "saved_filename": None,
                    "file_path": None,
                    "relative_path": None,
                    "file_size": 0,
                    "file_type": "excluded",
                    "exclusion_reason": f"расширение {file_ext} исключено",
                    "saved_at": self.get_local_time().isoformat(),
                    "status": "excluded",
                    "is_inline": is_inline
                }
            
            # 🚫 ТРЕТЬЯ ПРОВЕРКА: Неподдерживаемые расширения
            if file_ext not in SUPPORTED_ATTACHMENTS:
                self.logger.info(f"⚠️ НЕПОДДЕРЖИВАЕМОЕ РАСШИРЕНИЕ: {filename} - {file_ext}")
                self.stats['unsupported_attachments'] += 1
                return {
                    "original_filename": filename,
                    "saved_filename": None,
                    "file_path": None,
                    "relative_path": None,
                    "file_size": 0,
                    "file_type": "unsupported",
                    "exclusion_reason": f"расширение {file_ext} не поддерживается",
                    "saved_at": self.get_local_time().isoformat(),
                    "status": "unsupported",
                    "is_inline": is_inline
                }
            
            # ✅ ФАЙЛ ПРОШЕЛ ВСЕ ПРОВЕРКИ - СКАЧИВАЕМ
            attachment_type = "🖼️ Встроенное изображение" if is_inline else "⬇️ Вложение"
            self.logger.info(f"{attachment_type}: {filename}")
            
            # Создаем папку для вложений по дате ПИСЬМА
            attachments_date_dir = self.attachments_dir / date_folder
            attachments_date_dir.mkdir(exist_ok=True)
            
            # Создаем безопасное имя файла
            safe_filename = re.sub(r'[^\w\s\-\.]', '_', filename)
            timestamp = self.get_local_time().strftime('%H%M%S')
            
            # 🆕 Префикс для встроенных изображений
            prefix = "inline" if is_inline else "attach"
            unique_filename = f"{thread_id}_{timestamp}_{prefix}_{safe_filename}"
            
            # Путь для сохранения
            attachment_path = attachments_date_dir / unique_filename
            
            # Сохраняем файл
            payload = part.get_payload(decode=True)
            if payload:
                with open(attachment_path, 'wb') as f:
                    f.write(payload)
                
                file_size = len(payload)
                self.logger.info(f"✅ Сохранено: {filename} ({file_size} байт)")
                
                # Обновляем статистику в зависимости от типа
                if is_inline:
                    self.stats['saved_inline_images'] += 1
                else:
                    self.stats['saved_attachments'] += 1
                
                return {
                    "original_filename": filename,
                    "saved_filename": unique_filename,
                    "file_path": str(attachment_path),
                    "relative_path": f"attachments/{date_folder}/{unique_filename}",
                    "file_size": file_size,
                    "file_type": SUPPORTED_ATTACHMENTS[file_ext],
                    "content_type": content_type,
                    "saved_at": self.get_local_time().isoformat(),
                    "status": "saved",
                    "is_inline": is_inline
                }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения {'встроенного изображения' if is_inline else 'вложения'} {filename}: {e}")
            return None
        
        return None

    def process_single_email(self, msg_id: bytes, date_str: str, email_num_in_day: int, total_emails_in_day: int) -> Optional[Dict]:
        """📧 ИСПРАВЛЕННАЯ ЛОГИКА: заголовки → фильтры → загрузка"""
        
        # Инициализация ВСЕХ переменных в начале метода
        attachments = []
        attachments_stats = {
            'total': 0, 'saved': 0, 'excluded': 0, 'excluded_filenames': 0,
            'excluded_by_size': 0, 'excluded_by_image_dimensions': 0,
            'unsupported': 0, 'inline_images': 0
        }
        body_text = ""
        msg = None
        thread_id = ""
        date_folder = ""
        from_addr = ""
        to_addr = ""
        cc_addr = ""
        subject = ""
        date = ""
        to_emails = []
        cc_emails = []
        raw_email = b""
        email_date_formatted = "неизвестная дата"

        self.logger.info("_" * 70)
        self.stats['processed'] += 1

        try:
            # ШАГ 1: Загружаем заголовки
            headers_msg = self.get_email_headers_only(msg_id)
            if not headers_msg:
                self.logger.error(f"❌ Не удалось загрузить заголовки")
                self.stats['errors'] += 1
                self.save_skipped_email(msg_id, date_str, "failed_to_load_headers")  # ✅ ДОБАВИТЬ
                return None

            # ШАГ 2: Извлекаем информацию из заголовков
            try:
                date_header = headers_msg.get('Date', '')
                email_date_formatted = self.format_email_date_for_log(date_header)
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка парсинга даты: {e}")
                email_date_formatted = "неизвестная дата"

            try:
                # ✅ НОВЫЙ ПРАВИЛЬНЫЙ КОД
                from email.utils import getaddresses
                
                # Для одиночных полей - используем decode_header_value
                from_addr = self.decode_header_value(headers_msg.get('From', ''))
                subject = self.decode_header_value(headers_msg.get('Subject', ''))
                date = self.decode_header_value(headers_msg.get('Date', date_str))
                
                # Для множественных адресов - используем getaddresses
                raw_to = headers_msg.get('To', '')
                raw_cc = headers_msg.get('Cc', '')
                to_emails = [addr.lower().strip() for name, addr in getaddresses([raw_to]) if addr]
                cc_emails = [addr.lower().strip() for name, addr in getaddresses([raw_cc]) if addr]
                
                # Для обратной совместимости с логами
                to_addr = ', '.join(to_emails[:3]) + ('...' if len(to_emails) > 3 else '')
                cc_addr = ', '.join(cc_emails[:3]) + ('...' if len(cc_emails) > 3 else '')
                
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка парсинга получателей: {e}")
                to_emails = []
                cc_emails = []

            self.logger.info(f"🔍 ОБРАБОТКА ПИСЬМА {email_num_in_day}/{total_emails_in_day}, {email_date_formatted}")
            self.logger.info(f"📧 От: {from_addr}")  # Показываем полный адрес
            self.logger.info(f"   Тема: {subject[:100]}...")

            # ШАГ 3: ФИЛЬТРАЦИЯ ПЕРЕД ЗАГРУЗКОЙ

            # 🚫 ФИЛЬТР 1: Тема письма
            subject_filter = self.filters.is_subject_filtered(subject)
            if subject_filter:
                self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО ТЕМЕ: {subject_filter}")
                self.stats['filtered_subject'] += 1
                return None

            # 🚫 ФИЛЬТР 2: Черный список отправителей
            blacklist_filter = self.filters.is_sender_blacklisted(from_addr)
            if blacklist_filter:
                self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО АДРЕСУ: {blacklist_filter}")
                self.stats['filtered_blacklist'] += 1
                return None

            # 🔧 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Правильная проверка массовой рассылки
            # Убеждаемся что to_emails и cc_emails правильно заполнены
            if not to_emails and to_addr:
                self.logger.warning(f"⚠️ ДИАГНОСТИКА: to_emails пуст, но to_addr = {to_addr}")
            if not cc_emails and cc_addr:
                self.logger.warning(f"⚠️ ДИАГНОСТИКА: cc_emails пуст, но cc_addr = {cc_addr}")

            # 🚫 ФИЛЬТР 3: Массовая рассылка
            mass_mailing_filter = self.filters.is_internal_mass_mailing(from_addr, to_emails, cc_emails)
            if mass_mailing_filter:
                self.logger.info(f"🚫 ИСКЛЮЧЕНО ПО РАССЫЛКЕ: {mass_mailing_filter}")
                self.stats['filtered_mass_mailing'] += 1
                return None

            self.logger.info(f"✅ Письмо прошло все фильтры, загружаем полностью...")

            # 📏 ПРОВЕРКА РАЗМЕРА ПИСЬМА
            email_size = self.check_email_size(msg_id)

            if email_size == -1:
                if self.enable_size_logging:
                    self.logger.warning("⚠️ Размер письма неизвестен, полагаемся на анализ структуры")
                    
            elif email_size > 100_000_000:  # 100MB
                self.logger.warning(f"⚠️ Очень большое письмо ({email_size} байт), пропускаем")
                self.stats['skipped_large_emails'] += 1
                self.save_skipped_email(msg_id, date_str, f"large_email_{email_size}_bytes")
                return None
                
            elif email_size > 20_000_000:  # 20MB
                if self.enable_size_logging:
                    self.logger.info(f"📏 Большое письмо ({email_size} байт), обрабатываем осторожно")
            else:
                if self.enable_size_logging:
                    self.logger.info(f"📊 Нормальный размер письма: {email_size} байт")

            # ШАГ 4: Анализ структуры
            structure_info = self.analyze_bodystructure(msg_id)

            # ✅ УЛУЧШЕННАЯ ЛОГИКА: учитываем реальный размер письма
            if email_size != -1 and email_size < 50_000_000:  # 50MB
                # Для писем нормального размера отключаем проверку больших вложений
                has_large_attachments = False
                if self.enable_size_logging:
                    self.logger.info(f"📊 Нормальный размер письма ({email_size} байт), загружаем все вложения")
            else:
                has_large_attachments = structure_info['has_large_attachments']


            # Создаем нужные переменные
            try:
                thread_id = self.generate_thread_id(from_addr, subject, date)
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка генерации thread_id: {e}")
                thread_id = f"unknown_{self.get_local_time().strftime('%Y%m%d_%H%M%S')}"

            try:
                email_date = self.parse_email_date(date)
                date_folder = email_date.strftime('%Y-%m-%d')
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка парсинга даты письма: {e}")
                date_folder = self.get_local_time().strftime('%Y-%m-%d')

            emails_date_dir = self.emails_dir / date_folder
            emails_date_dir.mkdir(exist_ok=True)

            # ШАГ 5: УМНАЯ ЗАГРУЗКА
            if has_large_attachments:
                self.logger.warning(f"⚠️ Обнаружены большие вложения, загружаем без них...")
                msg = headers_msg
                try:
                    status, text_data = self.mail.fetch(msg_id, '(BODY.PEEK[1])')
                    if status == 'OK' and text_data:
                        raw_text = self.extract_raw_email(text_data)
                        if raw_text:
                            body_text = raw_text.decode('utf-8', errors='ignore')[:10000]
                        else:
                            body_text = "[Текст недоступен - проблема извлечения]"
                    else:
                        body_text = f"[Письмо с большими вложениями - текст из заголовков]"
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Ошибка загрузки текста большого письма: {e}")
                    body_text = "[Ошибка извлечения текста большого письма]"

                self.logger.info(f"📎 Вложения пропущены из-за размера")
                self.stats['skipped_large_emails'] += 1

            else:
                fetch_data = self.safe_fetch(msg_id)
                if not fetch_data:
                    self.logger.error(f"❌ Не удалось загрузить письмо")
                    self.stats['errors'] += 1
                    self.save_skipped_email(msg_id, date_str, "failed_to_fetch")  # ✅ ДОБАВИТЬ
                    return None

                raw_email = self.extract_raw_email(fetch_data)
                if not raw_email:
                    self.logger.error(f"❌ Не удалось извлечь сырой байтовый поток письма")
                    self.stats['errors'] += 1
                    self.save_skipped_email(msg_id, date_str, "failed_to_extract_raw")  # ✅ ДОБАВИТЬ
                    return None

                try:
                    msg = email.message_from_bytes(raw_email)
                except Exception as e:
                    self.logger.error(f"❌ Ошибка парсинга email: {e}")
                    self.stats['errors'] += 1
                    self.save_skipped_email(msg_id, date_str, f"parsing_error_{type(e).__name__}")  # ✅ ДОБАВИТЬ
                    return None

                try:
                    body_text = self.extract_plain_text(msg)
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка извлечения текста: {e}")
                    body_text = "[ОШИБКА ИЗВЛЕЧЕНИЯ ТЕКСТА]"

                # Обрабатываем вложения
                self.logger.info("🔍 Обработка вложений...")
                try:
                    if msg.is_multipart():
                        for part_num, part in enumerate(msg.walk()):
                            try:
                                content_disposition = part.get_content_disposition()
                                content_type = part.get_content_type()

                                is_attachment = False
                                is_inline = False

                                if content_disposition == 'attachment':
                                    is_attachment = True
                                elif (content_disposition == 'inline' and content_type.startswith('image/')) or \
                                     (not content_disposition and content_type.startswith('image/') and part.get_filename()):
                                    is_attachment = True
                                    is_inline = True

                                if is_attachment:
                                    attachments_stats['total'] += 1
                                    attachment_info = self.save_attachment_or_inline(part, thread_id, date_folder, is_inline)

                                    if attachment_info:
                                        attachments.append(attachment_info)
                                        status = attachment_info.get('status', 'unknown')
                                        if status == 'saved':
                                            attachments_stats['saved'] += 1
                                            if is_inline:
                                                attachments_stats['inline_images'] += 1
                                        elif status == 'excluded':
                                            attachments_stats['excluded'] += 1
                                        elif status == 'excluded_filename':
                                            attachments_stats['excluded_filenames'] += 1
                                        elif status == 'excluded_by_size':
                                            attachments_stats['excluded_by_size'] += 1
                                        elif status == 'unsupported':
                                            attachments_stats['unsupported'] += 1

                            except Exception as e:
                                self.logger.warning(f"⚠️ Ошибка обработки части {part_num}: {e}")
                                continue

                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки вложений: {e}")

            # СБОРКА ДАННЫХ ПИСЬМА
            email_data = {
                "thread_id": thread_id,
                "message_id": headers_msg.get('Message-ID', ''),
                "from": from_addr,
                "to": to_addr,
                "cc": cc_addr,
                "to_emails": to_emails,
                "cc_emails": cc_emails,
                "subject": subject,
                "date": date,
                "parsed_date": email_date.isoformat() if 'email_date' in locals() else None,
                "body": body_text,
                "char_count": len(body_text),
                "attachments": attachments,
                "attachments_stats": attachments_stats,
                "processed_at": self.get_local_time().isoformat(),
                "raw_size": len(raw_email) if raw_email else 0,
                "date_folder": date_folder
            }

            # Сохраняем письмо
            try:
                email_filename = f"email_{email_num_in_day:03d}_{date_folder.replace('-', '')}_{thread_id}.json"
                email_path = emails_date_dir / email_filename

                with open(email_path, 'w', encoding='utf-8') as f:
                    json.dump(email_data, f, ensure_ascii=False, indent=2)

                self.logger.info(f"✅ Сохранено: {email_filename}")

            except Exception as e:
                self.logger.error(f"❌ Ошибка сохранения письма: {e}")
                self.stats['errors'] += 1
                self.save_skipped_email(msg_id, date_str, f"save_error_{type(e).__name__}")  # ✅ ДОБАВИТЬ
                return None

            # Статистика вложений
            if attachments_stats['total'] > 0:
                inline_info = f" + {attachments_stats['inline_images']}🖼️" if attachments_stats['inline_images'] > 0 else ""
                filename_excluded = f" + {attachments_stats['excluded_filenames']}📝" if attachments_stats['excluded_filenames'] > 0 else ""
                size_excluded = f" + {attachments_stats['excluded_by_size']}📏" if attachments_stats['excluded_by_size'] > 0 else ""
                self.logger.info(f"📎 Вложений: {attachments_stats['saved']}✅ + {attachments_stats['excluded']}🚫 + {attachments_stats['unsupported']}⚠️{inline_info}{filename_excluded}{size_excluded} из {attachments_stats['total']}")

            self.stats['saved'] += 1
            self.logger.info(f"✅ ПИСЬМО СОХРАНЕНО")
            return email_data

        except Exception as e:
            self.logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА обработки письма {email_num_in_day}: {e}")
            self.logger.error(f" Тип ошибки: {type(e).__name__}")
            import traceback
            self.logger.error(f" Трейс: {traceback.format_exc()}")
            self.stats['errors'] += 1
            
            # ✅ ДОБАВИТЬ: Сохраняем письмо для повторной обработки
            self.save_skipped_email(msg_id, date_str, f"critical_error_{type(e).__name__}")
            
            return None

    def generate_thread_id(self, from_addr: str, subject: str, date: str) -> str:
        """🆔 Генерация уникального ID треда"""
        try:
            clean_subject = re.sub(r'^(Re:|Fwd:|Fw:)\s*', '', subject, flags=re.IGNORECASE).strip()
            sender_match = re.search(r'@([^>\s]+)', from_addr)
            domain = sender_match.group(1) if sender_match else 'unknown'
            hash_base = f"{domain}_{clean_subject}_{date[:10]}"
            hash_obj = hashlib.md5(hash_base.encode('utf-8'))
            email_date = self.parse_email_date(date)
            date_part = email_date.strftime('%Y%m%d')
            short_hash = hash_obj.hexdigest()[:8]
            return f"{date_part}_{domain.replace('.', '_')}_{short_hash}"
        except:
            return f"unknown_{self.get_local_time().strftime('%Y%m%d_%H%M%S')}"

    def fetch_emails_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """📅 Получение писем за период с НОВОЙ ЛОГИКОЙ"""
        
        self.logger.info(f"🎯 ЗАГРУЗКА ПИСЕМ ЗА ПЕРИОД (UTC+7)")
        self.logger.info(f"   📅 C: {start_date.strftime('%Y-%m-%d')}")
        self.logger.info(f"   📅 До: {end_date.strftime('%Y-%m-%d')}")
        self.logger.info(f"   🚫 Фильтры активны: {len(self.filters.subject_filters)} тем, {len(self.filters.blacklist)} адресов")
        self.logger.info(f"   ✅ Поддерживаемых расширений: {len(SUPPORTED_ATTACHMENTS)}")
        self.logger.info(f"   🚫 Исключенных расширений: {len(EXCLUDED_EXTENSIONS)}")
        self.logger.info(f"   📝 Исключений по именам: {len(self.filters.filename_excludes)}")
        self.logger.info(f"   🖼️ Включена обработка встроенных изображений")
        self.logger.info(f"   🚀 НОВАЯ ЛОГИКА: заголовки → фильтры → загрузка")
        self.logger.info("-" * 70)

        if not self.connect():
            self.logger.error(f"❌ Не удалось подключиться к серверу")
            return []

        all_emails = []
        current_date = start_date
        processed_emails_total = 0
        total_saved = 0

        while current_date <= end_date:
            date_imap = current_date.strftime('%d-%b-%Y')
            date_display = current_date.strftime('%Y-%m-%d')

            self.logger.info("=" * 70)
            self.logger.info(f"📬 Обработка {date_display}...")

            criteria = f'(ON "{date_imap}")'
            msg_ids = self.safe_search(criteria)

            if len(msg_ids) > 0:
                self.logger.info(f"   Найдено писем: {len(msg_ids)}")
                saved_today = 0

                for day_email_num, msg_id in enumerate(msg_ids, 1):
                    if processed_emails_total > 0 and processed_emails_total % BATCH_SIZE == 0:
                        self.logger.info(f"🔄 Профилактическое переподключение...")
                        if not self.connect():
                            continue

                    email_data = self.process_single_email(msg_id, date_display, day_email_num, len(msg_ids))

                    if email_data:
                        all_emails.append(email_data)
                        saved_today += 1
                        total_saved += 1

                    processed_emails_total += 1

                self.logger.info(f"📊 Итого сохранено писем за {date_display}: {saved_today}")
            else:
                self.logger.info(f"📭 Писем не найдено")

            current_date += timedelta(days=1)
            time.sleep(0.1)

        self.logger.info("=" * 70)
        self.logger.info(f"🎯 ОБЩИЙ ИТОГ ЗА ВСЕ ДНИ: сохранено {total_saved} писем")
        self.save_processing_stats(start_date, end_date)
        self.print_final_stats()

        # ✅ ДОБАВИТЬ ПОВТОРНУЮ ОБРАБОТКУ
        self.retry_skipped_emails()

        return all_emails

    def save_processing_stats(self, start_date: datetime, end_date: datetime):
        """📊 Сохранение статистики обработки"""
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')

        stats = {
            "period": f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}",
            "processed_at": self.get_local_time().isoformat(),
            "stats": self.stats,
            "filters": {
                "subject_filters": list(self.filters.subject_filters),
                "blacklist": list(self.filters.blacklist),
                "filename_excludes": self.filters.filename_excludes
            },
            "supported_attachments": list(SUPPORTED_ATTACHMENTS.keys()),
            "excluded_extensions": list(EXCLUDED_EXTENSIONS)
        }

        stats_path = self.logs_dir / f"processing_stats_{start_str}_{end_str}.json"

        try:
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            self.logger.info(f"📊 Статистика сохранена: {stats_path}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения статистики: {e}")

    def print_final_stats(self):
        """📊 Вывод итоговой статистики с полной фильтрацией"""
        self.logger.info("="*70)
        self.logger.info("📊 ИТОГОВАЯ СТАТИСТИКА")
        self.logger.info("="*70)
        self.logger.info(f"📧 Обработано писем: {self.stats['processed']}")
        self.logger.info(f"✅ Сохранено писем: {self.stats['saved']}")
        self.logger.info(f"🚫 Исключено по теме: {self.stats['filtered_subject']}")
        self.logger.info(f"🚫 Исключено по черному списку: {self.stats['filtered_blacklist']}")
        self.logger.info(f"🚫 Исключено массовых рассылок: {self.stats['filtered_mass_mailing']}")
        self.logger.info("")
        self.logger.info("📎 СТАТИСТИКА ВЛОЖЕНИЙ:")
        self.logger.info(f"✅ Скачано вложений: {self.stats['saved_attachments']}")
        self.logger.info(f"🖼️ Встроенных изображений: {self.stats['saved_inline_images']}")
        self.logger.info(f"🚫 Исключено по расширению: {self.stats['excluded_attachments']}")
        self.logger.info(f"📝 Исключено по имени файла: {self.stats['excluded_filenames']}")
        self.logger.info(f"📏 Исключено по размеру файла: {self.stats['excluded_by_size']}")
        self.logger.info(f"🖼️ Исключено по размерам изображения: {self.stats['excluded_by_image_dimensions']}")
        self.logger.info(f"⚠️ Неподдерживаемых: {self.stats['unsupported_attachments']}")

        total_attachments = (self.stats['saved_attachments'] + self.stats['saved_inline_images'] +
                           self.stats['excluded_attachments'] + self.stats['excluded_filenames'] +
                           self.stats['excluded_by_size'] + self.stats['excluded_by_image_dimensions'] +
                           self.stats['unsupported_attachments'])

        if total_attachments > 0:
            saved_total = self.stats['saved_attachments'] + self.stats['saved_inline_images']
            efficiency = (saved_total / total_attachments) * 100
            self.logger.info(f"📈 Эффективность скачивания: {efficiency:.1f}%")

        self.logger.info(f"❌ Ошибок обработки: {self.stats['errors']}")
        self.logger.info(f"📏 Пропущено больших писем: {self.stats['skipped_large_emails']}")

        total_filtered = (self.stats['filtered_subject'] + self.stats['filtered_blacklist'] + 
                         self.stats['filtered_mass_mailing'])
        self.logger.info(f"🚫 Всего писем исключено: {total_filtered}")

        if self.stats['processed'] > 0:
            save_rate = (self.stats['saved'] / self.stats['processed']) * 100
            self.logger.info(f"📈 Процент сохранения писем: {save_rate:.1f}%")

        self.logger.info("="*70)

    def close(self):
        """🔐 Закрытие соединения"""
        if self.mail:
            try:
                self.mail.logout()
                self.logger.info("🔐 Соединение закрыто")
            except:
                pass

def main():
    """🚀 Главная функция для тестирования парсера v2.10.1 - ИСПРАВЛЕНИЕ КРИТИЧЕСКИХ БАГОВ"""
    
    # Настройки периода для тестирования
    start_date = datetime(2025, 8, 15)
    end_date = datetime(2025, 8, 17)

    # Настраиваем логирование ПЕРЕД созданием fetcher'а
    logs_dir = Path("data/logs")
    logger = setup_logging(logs_dir, start_date, end_date)

    logger.info("📧 ПРОДВИНУТЫЙ IMAP-ПАРСЕР v2.10.1 - ИСПРАВЛЕНИЕ КРИТИЧЕСКИХ БАГОВ")
    logger.info("="*75)
    logger.info(f"🎯 Тестовый период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
    logger.info(f"✅ Скачиваем только: {', '.join(SUPPORTED_ATTACHMENTS.keys())}")
    logger.info(f"🚫 Исключаем расширения: {', '.join(EXCLUDED_EXTENSIONS)}")
    logger.info(f"🔧 ИСПРАВЛЕНЫ: черный список, decode_header_value, extract_raw_email")

    # Создаем парсер с логгером
    fetcher = AdvancedEmailFetcherV2(logger=logger)
    fetcher.enable_size_logging = False  # ✅ Включить детальные логи - True, ✅ Отключить детальные логи - False

    # ✅ ДОБАВИТЬ: тестирование фильтра
    logger.info("🔍 ТЕСТИРОВАНИЕ ФИЛЬТРА ИМЕН:")
    test_files = ['image001.png', 'logo.gif', 'contract.pdf']
    for test_file in test_files:
        result = fetcher.filters.is_filename_excluded(test_file)
        logger.info(f"  {test_file} → {result or 'НЕ ИСКЛЮЧЕН'}")

    try:
        # Загружаем письма
        emails = fetcher.fetch_emails_by_date_range(start_date, end_date)

        logger.info("🎉 ЗАГРУЗКА ЗАВЕРШЕНА С ПОЛНЫМ ИСПРАВЛЕНИЕМ БАГОВ!")
        logger.info("   📁 Письма сохранены в: data/emails/[дата_письма]/")
        logger.info("   📎 Только нужные вложения в: data/attachments/[дата_письма]/")
        logger.info("   📝 Логи в: data/logs/")

        if emails:
            logger.info("📋 СТРУКТУРА ГОТОВА ДЛЯ LLM АНАЛИЗА:")
            logger.info("   ✅ Каждое письмо = отдельный JSON файл")
            logger.info("   ✅ Исправленная фильтрация ПЕРЕД загрузкой")
            logger.info("   ✅ ИСПРАВЛЕН черный список info@*, news@*")
            logger.info("   ✅ ИСПРАВЛЕН decode_header_value для правильного извлечения email")
            logger.info("   ✅ ИСПРАВЛЕН extract_raw_email для корректной обработки bytes")
            logger.info("   ✅ Убран дублированный код в process_single_email")

    except KeyboardInterrupt:
        logger.warning("⏹️ Загрузка прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        fetcher.close()
        logger.info("🎯 ЗАВЕРШЕНИЕ СЕАНСА ОБРАБОТКИ")

if __name__ == '__main__':
    main()