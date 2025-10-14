"""
EmailFilters - Фильтрация email писем.

Перенесенная логика фильтрации из оригинального модуля с адаптацией
для новой архитектуры.
"""

import fnmatch
import logging
import re
from pathlib import Path
from typing import List, Optional, Set

# Импорты конфигурации
import os
from dotenv import load_dotenv

load_dotenv()

COMPANY_DOMAIN = os.getenv("COMPANY_DOMAIN", "dna-technology.ru")


class EmailFilters:
    """
    Класс для управления фильтрами исключений.
    
    Перенесенная логика из оригинального AdvancedEmailFetcherV2
    с адаптацией для модульной архитектуры.
    """
    
    def __init__(self, logger: logging.Logger, config_dir: Optional[Path] = None):
        """
        Инициализация фильтров.
        
        Args:
            logger: Экземпляр логгера
            config_dir: Директория с конфигурацией
        """
        self.logger = logger
        
        # Используем стандартную директорию конфигурации
        if config_dir is None:
            try:
                from ...config.paths import CONFIG_DIR
                config_dir = CONFIG_DIR
            except ImportError:
                # Fallback для прямого запуска
                import sys
                from pathlib import Path
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                from src.config.paths import CONFIG_DIR
                config_dir = CONFIG_DIR
        
        self.config_dir = config_dir
        
        # Инициализация фильтров
        self.subject_filters: Set[str] = set()
        self.blacklist: Set[str] = set()
        self.filename_excludes: List[str] = []
        
        # Паттерны для исключения inline изображений
        self.inline_exclusion_patterns = {
            r"mailrusigimg_.*",  # Подписи Mail.ru
            r"signature.*",  # Подписи
            r"logo.*",  # Логотипы
            r"banner.*",  # Баннеры
            r"footer.*",  # Футеры
            r"header.*",  # Хедеры
            r"image00[1-9]\.",  # image001, image002 и т.д.
            r"image0[1-9]\.",  # image01, image02 и т.д.
            r"blocked\.",  # blocked.gif и т.д.
            r".*WRD00.*",  # WRD000.jpg, WRD001.jpg и т.д.
            r".*WRD0.*",  # WRD0.jpg и т.д.
            r"_\..*",  # _.jpg, _.png и т.д.
            r"^_+$",  # ___, ____ и т.д.
        }
        
        # Загружаем фильтры
        self.load_filters()
        
        self.logger.info("🚫 EmailFilters инициализированы")
    
    def load_filters(self):
        """Загрузка фильтров из файлов."""
        # Загружаем фильтры тем
        filters_file = self.config_dir / "filters.txt"
        if filters_file.exists():
            try:
                with open(filters_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            self.subject_filters.add(line.lower())
                self.logger.info(
                    f"✅ Загружено {len(self.subject_filters)} фильтров тем"
                )
            except Exception as e:
                self.logger.error(f"❌ Ошибка загрузки фильтров: {e}")
        
        # Загружаем черный список
        blacklist_file = self.config_dir / "blacklist.txt"
        if blacklist_file.exists():
            try:
                with open(blacklist_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            self.blacklist.add(line.lower())
                self.logger.info(
                    f"✅ Загружено {len(self.blacklist)} адресов в черном списке"
                )
                self.logger.info(f"   Примеры: {list(self.blacklist)[:3]}")
            except Exception as e:
                self.logger.error(f"❌ Ошибка загрузки черного списка: {e}")
        
        # Загружаем исключения по именам файлов
        filename_excludes_file = self.config_dir / "attachment_filename_excludes.txt"
        if filename_excludes_file.exists():
            try:
                with open(filename_excludes_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if line == "****":
                                self.logger.warning(
                                    f"⚠️ Пропускаем проблемный паттерн: {line}"
                                )
                                continue
                            self.filename_excludes.append(line)
                self.logger.info(
                    f"✅ Загружено {len(self.filename_excludes)} исключений по именам файлов"
                )
            except Exception as e:
                self.logger.error(f"❌ Ошибка загрузки исключений имён файлов: {e}")
    
    def is_subject_filtered(self, subject: str) -> Optional[str]:
        """
        Проверка темы письма на исключение.
        
        Args:
            subject: Тема письма
            
        Returns:
            Причина исключения или None
        """
        if not subject:
            return None
        
        subject_lower = subject.lower()
        for filter_word in self.subject_filters:
            if filter_word in subject_lower:
                return f"тема содержит '{filter_word}'"
        return None
    
    def is_sender_blacklisted(self, from_addr: str) -> Optional[str]:
        """
        Проверка отправителя в черном списке.
        
        Args:
            from_addr: Email отправителя
            
        Returns:
            Причина исключения или None
        """
        if not from_addr:
            return None
        
        from_addr_lower = from_addr.lower().strip()
        
        self.logger.debug(
            f"Проверяем адрес '{from_addr_lower}' против {len(self.blacklist)} правил"
        )
        
        for blacklisted in self.blacklist:
            blacklisted = blacklisted.strip().lower()
            
            if blacklisted.endswith("*"):
                # Маски типа info@*, newsletter@*, marketing@*
                prefix = blacklisted[:-1]  # убираем звездочку
                if from_addr_lower.startswith(prefix):
                    return f"адрес начинается с '{prefix}' (в черном списке)"
            
            elif blacklisted.startswith("*@"):
                # Маски типа *@domain.com
                domain = blacklisted[2:]  # убираем *@
                if from_addr_lower.endswith(f"@{domain}"):
                    return f"домен в черном списке ({domain})"
            
            else:
                # Точные совпадения
                if from_addr_lower == blacklisted:
                    return f"адрес в черном списке"
        
        return None
    
    def is_inline_image_excluded(
        self, filename: str, content_type: str, content_id: str = None
    ) -> Optional[str]:
        """
        Проверка inline изображения на исключение.
        
        Args:
            filename: Имя файла
            content_type: Content-Type
            content_id: Content-ID
            
        Returns:
            Причина исключения или None
        """
        if not filename:
            return None
        
        filename_lower = filename.lower()
        
        # Проверяем Content-ID (характерно для встроенных изображений)
        if content_id:
            return f"изображение с Content-ID: {content_id}"
        
        # Проверяем на очень короткие имена файлов
        if len(filename) <= 3:
            return f"слишком короткое имя файла: {filename}"
        
        # Извлекаем имя файла без расширения для анализа
        name_without_ext = filename
        if "." in filename:
            name_without_ext = filename.rsplit(".", 1)[0]
        
        # Проверяем на случайные имена (только буквы и цифры, без пробелов и точек)
        if re.match(r"^[a-zA-Z0-9]+$", name_without_ext):
            # Для коротких имен - проверяем длину
            if len(name_without_ext) <= 6:
                # Короткие имена могут быть нормальными, проверяем на специальные случаи
                if name_without_ext in ["img", "pic", "photo", "image"]:
                    return None  # Эти короткие имена могут быть нормальными
                else:
                    return f"слишком короткое имя файла: {filename}"
            
            # Для длинных имен - проверяем entropy
            unique_chars = len(set(name_without_ext.lower()))
            total_chars = len(name_without_ext)
            
            # Вычисляем коэффициент разнообразия
            diversity_ratio = unique_chars / total_chars
            
            # Если много повторяющихся символов - вероятно паттерн, а не случайное имя
            if diversity_ratio < 0.6:  # Менее 60% уникальных символов
                return f"низкая энтропия символов, вероятно паттерн: {filename}"
            
            # Если высокая энтропия и длина > 8 - вероятно случайное имя
            if len(name_without_ext) > 8 and diversity_ratio > 0.7:
                return f"высокая энтропия символов, вероятно случайное имя: {filename}"
            
            # Средний случай - исключаем имена длиннее 12 символов
            if len(name_without_ext) > 12:
                return f"слишком длинное имя файла: {filename}"
        
        # Проверяем паттерны мусорных inline изображений
        for pattern in self.inline_exclusion_patterns:
            if re.match(pattern, filename_lower, re.IGNORECASE):
                return f"соответствует паттерну исключения: {pattern}"
        
        return None
    
    def is_filename_excluded(self, filename: str) -> Optional[str]:
        """
        Проверка имени файла на исключение.
        
        Args:
            filename: Имя файла
            
        Returns:
            Причина исключения или None
        """
        if not filename or not self.filename_excludes:
            return None
        
        self.logger.debug(
            f"🔍 Проверка файла '{filename}' против {len(self.filename_excludes)} паттернов"
        )
        
        # Проверка на одиночные символы и короткие имена
        if filename in [
            "_",
            "__",
            "___",
            "____",
            "_____",
            "-",
            "--",
            "---",
            "----",
            "....",
        ]:
            self.logger.info(f"🚫 ФАЙЛ ИСКЛЮЧЕН ПО КОРОТКОМУ ИМЕНИ: {filename}")
            return f"имя файла точно соответствует короткому исключению '{filename}'"
        
        # Получаем базовое имя файла (без любых префиксов типа ~ или .)
        base_filename = filename
        if base_filename.startswith("~") or base_filename.startswith("."):
            base_filename = base_filename[1:]
        
        # Проверка паттернов
        for exclude_pattern in self.filename_excludes:
            if "*" in exclude_pattern:
                # Wildcard паттерн
                if fnmatch.fnmatch(
                    filename.lower(), exclude_pattern.lower()
                ) or fnmatch.fnmatch(base_filename.lower(), exclude_pattern.lower()):
                    self.logger.info(
                        f"🚫 ФАЙЛ ИСКЛЮЧЕН ПО ПАТТЕРНУ: {filename} → {exclude_pattern}"
                    )
                    return f"имя файла соответствует паттерну '{exclude_pattern}'"
            else:
                # Точное совпадение
                if (
                    filename.lower() == exclude_pattern.lower()
                ):  # Игнорируем регистр для точного совпадения
                    self.logger.info(f"🚫 ФАЙЛ ИСКЛЮЧЕН ПО ТОЧНОМУ ИМЕНИ: {filename}")
                    return f"имя файла точно соответствует '{exclude_pattern}'"
        
        self.logger.debug(f"✅ Файл '{filename}' прошел все фильтры имен")
        return None
    
    def is_internal_mass_mailing(
        self, from_addr: str, to_addrs: List[str], cc_addrs: List[str] = None
    ) -> Optional[str]:
        """
        Проверка на внутреннюю массовую рассылку.
        
        Args:
            from_addr: Email отправителя
            to_addrs: Список получателей (To)
            cc_addrs: Список получателей (CC)
            
        Returns:
            Причина исключения или None
        """
        # Импортируем настройки
        try:
            try:
                from config.settings import EMAIL_FILTERS_CONFIG
                config = EMAIL_FILTERS_CONFIG["mass_mailing"]
            except (ImportError, KeyError):
                # Fallback для прямого запуска
                import sys
                from pathlib import Path
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                from src.config.settings import EMAIL_FILTERS_CONFIG
                config = EMAIL_FILTERS_CONFIG["mass_mailing"]
        except (ImportError, KeyError):
            # Fallback на старые значения если настройки недоступны
            config = {
                "enabled": True,
                "max_internal_recipients": 10,
                "apply_to_external_senders": False,
            }
        
        # Проверяем включен ли фильтр
        if not config.get("enabled", True):
            return None
        
        # Получаем настройки
        max_recipients = config.get("max_internal_recipients", 10)
        apply_to_external = config.get("apply_to_external_senders", False)
        
        # Проверяем домен отправителя
        is_internal_sender = from_addr and f"@{COMPANY_DOMAIN}" in from_addr.lower()
        
        # Если отправитель внешний и фильтр не применяется к внешним - пропускаем
        if not is_internal_sender and not apply_to_external:
            self.logger.debug(
                f"Внешний отправитель {from_addr}, фильтр массовой рассылки не применяется"
            )
            return None
        
        # Считаем внутренних получателей
        all_recipients = []
        all_recipients.extend(to_addrs or [])
        all_recipients.extend(cc_addrs or [])
        
        internal_recipients = 0
        for recipient in all_recipients:
            if f"@{COMPANY_DOMAIN}" in recipient.lower():
                internal_recipients += 1
        
        # Проверяем порог
        if internal_recipients >= max_recipients:
            sender_type = "внутренняя" if is_internal_sender else "внешняя"
            return f"массовая {sender_type} рассылка ({internal_recipients} получателей, порог: {max_recipients})"
        
        return None