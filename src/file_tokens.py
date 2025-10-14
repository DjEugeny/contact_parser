#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@file: file_tokens.py
@description: Скрипт для подсчёта символов и токенов в письмах и их вложениях.
@dependencies: tiktoken
@created: 2025-01-26
@updated: 2025-08-27
"""

import json
import os
import logging
import hashlib
import re
from pathlib import Path
# from file_utils import normalize_filename  # Комментируем импорт
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import tiktoken

if __name__ == "__main__" or __package__ is None:
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent
    if str(project_root.parent) not in sys.path:
        sys.path.insert(0, str(project_root.parent))

try:
    from fetcher.attachments.attachment_registry import AttachmentRegistry
except ImportError:
    # Fallback для прямого запуска
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.fetcher.attachments.attachment_registry import AttachmentRegistry

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('file_tokens.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class FileTokenCounter:
    """
    Класс для подсчета символов и токенов в файлах писем и их вложениях,
    с генерацией интерактивного HTML-отчета.
    """
    def __init__(self):
        # Импортируем централизованные пути
        try:
            from config.paths import DataPaths
        except ImportError:
            # Fallback для прямого запуска
            import sys
            from pathlib import Path
            project_root = Path(__file__).resolve().parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            try:
                from src.config.paths import DataPaths
            except ImportError:
                # Дополнительный fallback для импорта из src/config
                from src.config.paths import CONFIG_DIR, DATA_DIR, LOGS_DIR
                class DataPaths:
                    OCR_TEXTS_DIR = DATA_DIR / "ocr" / "texts"
                    @staticmethod
                    def migrate_if_needed():
                        pass
        
        # Выполняем автомиграцию если необходимо
        DataPaths.migrate_if_needed()
        
        self.base_path = Path("data")
        self.emails_path = self.base_path / "emails"
        self.attachments_path = self.base_path / "attachments"
        self.final_results_path = DataPaths.OCR_TEXTS_DIR
        self.output_path = self.base_path / "file_tokens"
        self.cache_file = self.base_path / ".processed_file_tokens.json"
        self.cache_version = "2025-10-14_v2"
        
        self.output_path.mkdir(exist_ok=True)
        self.processed_files = self._load_cache()
        self.attachment_registry = AttachmentRegistry(logger=logging.getLogger("file_tokens.attachment_registry"))
        
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.error(f"Ошибка инициализации tiktoken: {e}. Подсчёт токенов будет отключен.")
            self.encoder = None

    def _load_cache(self) -> Dict:
        """Загружает кэш обработанных файлов из JSON."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Ошибка загрузки кэша {self.cache_file}: {e}. Кэш будет создан заново.")
        return {}

    def _save_cache(self):
        """Сохраняет кэш обработанных файлов в JSON."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения кэша в {self.cache_file}: {e}")

    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """Вычисляет MD5 хэш файла для отслеживания изменений."""
        try:
            if file_path.is_file():
                return hashlib.md5(file_path.read_bytes()).hexdigest()
        except IOError as e:
            logger.warning(f"Ошибка вычисления хэша для {file_path}: {e}")
        return None

    def _get_cached_data(self, file_path: Path) -> Optional[Tuple[int, int]]:
        """
        Проверяет кэш. Если хэш файла совпадает, возвращает кэшированные данные.
        Возвращает (symbols, tokens) или None, если файл нужно пересчитать.
        """
        file_id = str(file_path)
        current_hash = self._get_file_hash(file_path)

        if not current_hash:
            return None

        if file_id in self.processed_files:
            cached_info = self.processed_files[file_id]
            if isinstance(cached_info, dict):
                if cached_info.get("version") != self.cache_version:
                    return None
                if cached_info.get('hash') == current_hash:
                    logger.info(f"Файл '{file_path.name}' не изменился, используем данные из кэша.")
                    return cached_info.get('symbols', 0), cached_info.get('tokens', 0)
        
        logger.info(f"Файл '{file_path.name}' новый или был изменен, будет обработан.")
        return None

    def _update_cache(self, file_path: Path, symbols: int, tokens: int):
        """Обновляет кэш для указанного файла."""
        file_id = str(file_path)
        current_hash = self._get_file_hash(file_path)
        if current_hash:
            self.processed_files[file_id] = {
                'version': self.cache_version,
                'hash': current_hash,
                'symbols': symbols,
                'tokens': tokens
            }

    def get_available_dates(self) -> List[str]:
        """📅 Возвращает доступные даты, основываясь на реальных папках с вложениями."""
        if not self.attachments_path.exists():
            logger.warning("📂 Папка с вложениями не найдена, список дат будет пустым.")
            return []

        dates: List[str] = []
        for date_folder in self.attachments_path.iterdir():
            if date_folder.is_dir() and not date_folder.name.startswith('.'):
                dates.append(date_folder.name)

        return sorted(dates, reverse=True)

    def choose_date_menu(self) -> Optional[str]:
        """Отображает интерактивное меню для выбора даты обработки."""
        dates = self.get_available_dates()
        if not dates:
            logger.error("В директории 'data/attachments' не найдено папок с датами для обработки.")
            return None

        print("\n" + "="*50 + "\nДОСТУПНЫЕ ДАТЫ ДЛЯ ОБРАБОТКИ:\n" + "="*50)
        for i, date in enumerate(dates, 1):
            print(f"{i:2d}. {date}")
        print("-" * 50)
        print(f"{len(dates) + 1:2d}. Все даты")
        print(f"{len(dates) + 2:2d}. Выход")
        print("="*50)

        while True:
            try:
                choice = input("\nВыберите номер (или 'q' для выхода): ").strip().lower()
                if choice == 'q': return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(dates):
                    return dates[choice_num - 1]
                if choice_num == len(dates) + 1:
                    return "all"
                if choice_num == len(dates) + 2:
                    return None
                print("Неверный номер. Попробуйте снова.")
            except ValueError:
                print("Некорректный ввод. Введите число или 'q'.")

    def _extract_email_body(self, email_data: Dict[str, Any]) -> str:
        """📝 Извлекает тело письма с учётом возможных вариантов полей."""
        body_candidates = [
            email_data.get("body"),
            email_data.get("body_clean"),
            email_data.get("body_plain"),
            email_data.get("body_text"),
            email_data.get("text"),
            email_data.get("body_raw"),
        ]

        for candidate in body_candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate

        return ""

    def count_symbols_tokens(self, text: str) -> Tuple[int, int]:
        """Подсчитывает количество символов и токенов в тексте с нормализацией."""
        if not text or not isinstance(text, str):
            return 0, 0

        # Нормализуем текст для консистентности расчетов
        # Удаляем BOM если присутствует
        if text.startswith('\ufeff'):
            text = text[1:]

        # Удаляем лишние пробелы в начале и конце
        text = text.strip()

        symbols = len(text)
        tokens = 0
        if self.encoder:
            try:
                tokens = len(self.encoder.encode(text))
            except Exception as e:
                logger.warning(f"Ошибка подсчёта токенов: {e}")

        return symbols, tokens

    def _extract_email_number(self, filename: str) -> int:
        """Извлекает номер письма из имени файла для корректной сортировки."""
        match = re.search(r"email_(\d+)", filename)
        return int(match.group(1)) if match else 0
    
    def _normalize_filename(self, filename: str) -> str:
        """Нормализует имя файла для лучшего сопоставления."""
        # Простая нормализация без использования file_utils
        return filename.lower().replace(' ', '_')
    
    def _make_index_key(self, value: Optional[str]) -> Optional[str]:
        """Формирует ключ индекса для сопоставления вложений."""
        if not value:
            return None
        return str(value).strip().lower()

    def _merge_attachment_records(
        self,
        original: Optional[Dict[str, Any]],
        registry_record: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Объединяет данные вложения из JSON и реестра."""
        merged = dict(original) if isinstance(original, dict) else {}
        merged.setdefault("original_filename", registry_record.get("original_filename"))
        merged["saved_filename"] = registry_record.get("saved_filename")
        merged["status"] = registry_record.get("status")
        merged["file_path"] = registry_record.get("file_path")
        merged["relative_path"] = registry_record.get("relative_path")
        merged["file_exists"] = registry_record.get("file_exists")
        merged["reason"] = registry_record.get("reason")
        merged["message_id"] = registry_record.get("message_id")
        merged["thread_id"] = registry_record.get("thread_id")
        merged["sha256"] = registry_record.get("sha256")
        return merged

    def _get_reconciled_attachments(
        self,
        email_data: Dict[str, Any],
        date: str,
    ) -> List[Dict[str, Any]]:
        """Возвращает список вложений после reconciliation с AttachmentRegistry."""
        attachments = email_data.get("attachments") or []
        message_id = email_data.get("message_id")

        if not message_id:
            return attachments

        reconciled_records = self.attachment_registry.reconcile_attachments_for_message(message_id, date)
        if not reconciled_records:
            return attachments

        index: Dict[str, Dict[str, Any]] = {}
        for attachment in attachments:
            candidates = [
                attachment.get("saved_filename"),
                Path(attachment.get("file_path", "")).name if attachment.get("file_path") else None,
                Path(attachment.get("relative_path", "")).name if attachment.get("relative_path") else None,
                attachment.get("original_filename"),
            ]
            for candidate in candidates:
                key = self._make_index_key(candidate)
                if key and key not in index:
                    index[key] = attachment

        merged_attachments: List[Dict[str, Any]] = []
        for record in reconciled_records:
            candidates = [
                record.get("saved_filename"),
                Path(record.get("file_path", "")).name if record.get("file_path") else None,
                record.get("original_filename"),
            ]
            source = None
            for candidate in candidates:
                key = self._make_index_key(candidate)
                if key and key in index:
                    source = index[key]
                    break

            merged_attachments.append(self._merge_attachment_records(source, record))

        return merged_attachments
    
    def _extract_attachment_core_name(self, attachment_name: str) -> str:
        """Извлекает ключевую часть имени вложения, которая остаётся после обработки OCR."""
        # Простая нормализация без использования file_utils
        return attachment_name.lower().replace(' ', '_')
    
    def _extract_ocr_core_name(self, ocr_filename: str) -> str:
        """Извлекает ключевую часть имени OCR файла."""
        # Простая нормализация без использования file_utils
        return ocr_filename.lower().replace(' ', '_')

    def _resolve_saved_filename(self, attachment: Dict[str, Any]) -> Optional[str]:
        """Определяет актуальное имя файла вложения на основе доступных полей."""
        if attachment.get("saved_filename"):
            return attachment["saved_filename"]
        if attachment.get("file_path"):
            try:
                return Path(attachment["file_path"]).name
            except Exception:
                pass
        if attachment.get("relative_path"):
            try:
                return Path(attachment["relative_path"]).name
            except Exception:
                pass
        if attachment.get("original_filename"):
            return attachment["original_filename"]
        return None

    def _resolve_attachment_disk_path(self, date: str, attachment: Dict[str, Any]) -> Optional[Path]:
        """🗂️ Возвращает фактический путь к вложению на диске, если он существует."""
        saved_filename = self._resolve_saved_filename(attachment)
        if not saved_filename:
            return None

        candidates: List[Path] = []
        attachments_dir = self.attachments_path / date
        candidates.append(attachments_dir / saved_filename)

        for field in ("file_path", "relative_path"):
            candidate_value = attachment.get(field)
            if not candidate_value:
                continue
            try:
                candidate_path = Path(candidate_value)
                if not candidate_path.is_absolute():
                    candidate_path = self.base_path / candidate_path
                candidates.append(candidate_path)
            except Exception:
                continue

        for candidate in candidates:
            try:
                if candidate.exists():
                    return candidate
            except Exception:
                continue

        return None

    def _locate_ocr_for_attachment(self, date: str, attachment: Dict[str, Any]) -> Optional[Path]:
        """Подбирает OCR-файл для конкретного вложения, перебирая возможные имена."""
        candidates: List[str] = []
        saved_filename = self._resolve_saved_filename(attachment)
        if saved_filename:
            candidates.append(saved_filename)
        original_filename = attachment.get("original_filename")
        if original_filename and original_filename not in candidates:
            candidates.append(original_filename)

        file_path = attachment.get("file_path")
        if file_path:
            try:
                base_name = Path(file_path).name
                if base_name not in candidates:
                    candidates.append(base_name)
            except Exception:
                pass

        relative_path = attachment.get("relative_path")
        if relative_path:
            try:
                base_name = Path(relative_path).name
                if base_name not in candidates:
                    candidates.append(base_name)
            except Exception:
                pass

        for candidate in candidates:
            ocr_file = self._find_ocr_file(date, candidate)
            if ocr_file:
                return ocr_file

        return None
    
    def _extract_email_prefix(self, filename: str) -> Optional[str]:
        """Извлекает префикс email_X_ из имени файла OCR."""
        match = re.search(r'^(email_\d+)_', filename)
        return match.group(1) if match else None

    def _read_file_content(self, file_path: Path) -> str:
        """Унифицированное чтение файла с поддержкой различных кодировок."""
        encodings_to_try = ['utf-8', 'utf-8-sig', 'cp1251', 'windows-1251', 'iso-8859-1']

        for encoding in encodings_to_try:
            try:
                content = file_path.read_text(encoding=encoding)

                # Удаляем BOM если присутствует
                if content.startswith('\ufeff'):
                    content = content[1:]

                # Проверяем, что файл не пустой и содержит текст
                if content.strip():
                    logger.debug(f"Файл {file_path.name} успешно прочитан с кодировкой {encoding}")
                    return content
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.warning(f"Ошибка при чтении файла {file_path.name} с кодировкой {encoding}: {e}")
                continue

        # Если ни одна кодировка не сработала, пробуем прочитать как бинарный файл
        try:
            content = file_path.read_bytes().decode('utf-8', errors='replace')
            if content.strip():
                logger.debug(f"Файл {file_path.name} прочитан как бинарный с заменой ошибок")
                return content
        except Exception as e:
            logger.error(f"Критическая ошибка чтения файла {file_path.name}: {e}")

        return ""

    def _normalize_for_comparison(self, text: str) -> str:
        """Нормализует текст для сравнения, устраняя различия в кодировке."""
        if not text:
            return text

        # Приводим к нижнему регистру
        text = text.lower()

        # Заменяем похожие символы (кириллица vs латиница, диакритические знаки)
        replacements = {
            'й': 'и',  # й -> и
            'ё': 'е',  # ё -> е
            'ъ': '',   # удаляем твердый знак
            'ь': '',   # удаляем мягкий знак
            # Заменяем похожие буквы
            'a': 'а', 'b': 'в', 'c': 'с', 'e': 'е', 'h': 'н',
            'k': 'к', 'm': 'м', 'o': 'о', 'p': 'р', 't': 'т',
            'u': 'и', 'x': 'х', 'y': 'у',
            # Удаляем диакритические знаки и специальные символы
            '\u0301': '',  # ударение
            '\u0300': '',  # гравис
            '\u0306': '',  # breve
        }

        for old_char, new_char in replacements.items():
            text = text.replace(old_char, new_char)

        # Удаляем множественные пробелы и приводим к единому формату
        import re
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _find_ocr_file(self, date: str, attachment_name: str) -> Optional[Path]:
        """Выполняет гибкий поиск OCR-файла для указанного вложения с диагностикой."""
        ocr_dir = self.final_results_path / date
        if not ocr_dir.exists():
            logger.debug(f"OCR папка для даты {date} не существует: {ocr_dir}")
            return None

        # Получаем список всех OCR файлов для диагностики
        all_ocr_files = list(ocr_dir.glob("*.txt"))
        logger.debug(f"Поиск OCR для '{attachment_name}' среди {len(all_ocr_files)} файлов в {date}")

        attachment_base = attachment_name.rsplit('.', 1)[0] if '.' in attachment_name else attachment_name

        # Этап 1: Точное совпадение по полному имени
        for ocr_file in all_ocr_files:
            ocr_file_name_no_ext = ocr_file.stem
            if attachment_name == ocr_file_name_no_ext:
                logger.debug(f"Найдено точное совпадение: {attachment_name} -> {ocr_file.name}")
                return ocr_file

        # Этап 2: Совпадение по базовому имени без расширения
        for ocr_file in all_ocr_files:
            ocr_file_name_no_ext = ocr_file.stem
            if attachment_base == ocr_file_name_no_ext:
                logger.debug(f"Найдено совпадение по базовому имени: {attachment_base} -> {ocr_file.name}")
                return ocr_file

        # Этап 3: Нормализованное сравнение (учитывает кодировочные различия)
        attachment_normalized = self._normalize_for_comparison(attachment_base)
        logger.debug(f"Нормализованное имя вложения: '{attachment_normalized}'")

        for ocr_file in all_ocr_files:
            ocr_file_name_no_ext = ocr_file.stem
            ocr_normalized = self._normalize_for_comparison(ocr_file_name_no_ext)

            # Проверяем схожесть после нормализации
            if attachment_normalized == ocr_normalized:
                logger.debug(f"Найдено совпадение после нормализации: '{attachment_base}' -> '{ocr_file_name_no_ext}'")
                return ocr_file

            # Более мягкое сравнение - проверяем, содержит ли одно имя другое после нормализации
            if (len(attachment_normalized) > 10 and attachment_normalized in ocr_normalized) or \
               (len(ocr_normalized) > 10 and ocr_normalized in attachment_normalized):
                logger.debug(f"Найдено частичное совпадение после нормализации: '{attachment_base}' ~ '{ocr_file_name_no_ext}'")
                return ocr_file

        # Этап 4: Частичное совпадение (базовое имя содержится в OCR файле)
        for ocr_file in all_ocr_files:
            if attachment_base in ocr_file.name:
                logger.debug(f"Найдено частичное совпадение: {attachment_base} содержится в {ocr_file.name}")
                return ocr_file

        # Этап 5: Обратное частичное совпадение (OCR имя содержится в attachment)
        for ocr_file in all_ocr_files:
            ocr_base = ocr_file.stem
            if len(ocr_base) > 5 and ocr_base in attachment_name:  # Минимальная длина для избежания ложных совпадений
                logger.debug(f"Найдено обратное частичное совпадение: {ocr_base} содержится в {attachment_name}")
                return ocr_file

        logger.warning(f"OCR файл для вложения '{attachment_name}' не найден среди {len(all_ocr_files)} файлов")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Доступные OCR файлы: {[f.name for f in all_ocr_files[:10]]}{'...' if len(all_ocr_files) > 10 else ''}")
        return None

    def process_date(self, date: str) -> List[Dict]:
        """
        Обрабатывает все письма и их вложения за указанную дату.
        Также обрабатывает OCR-файлы, для которых нет соответствующих писем.
        Возвращает иерархический список словарей с данными для отчета.
        """
        emails_dir = self.emails_path / date
        ocr_dir = self.final_results_path / date
        date_results = []
        processed_ocr_files = set()

        # Обработка писем (если папка с письмами существует)
        if emails_dir.is_dir():
            email_files = sorted(list(emails_dir.glob("*.json")), key=lambda p: self._extract_email_number(p.name))
            logger.info(f"Начинаем обработку {len(email_files)} писем за {date}...")

            for email_file in email_files:
                try:
                    with open(email_file, 'r', encoding='utf-8') as f:
                        email_data = json.load(f)
                except (IOError, json.JSONDecodeError) as e:
                    logger.error(f"Ошибка чтения или парсинга файла письма {email_file.name}: {e}")
                    continue

                # Обработка тела письма
                body_text = self._extract_email_body(email_data)
                cached_body = self._get_cached_data(email_file)
                if cached_body:
                    body_symbols, body_tokens = cached_body
                else:
                    body_symbols, body_tokens = self.count_symbols_tokens(body_text)
                    self._update_cache(email_file, body_symbols, body_tokens)

                email_result = {
                    "file": email_file.name,
                    "symbols": body_symbols,
                    "tokens": body_tokens,
                    "attachments": []
                }

                # Обработка вложений
                reconciled_attachments = self._get_reconciled_attachments(email_data, date)
                allowed_statuses = {"saved", "already_exists"}
                for attachment in reconciled_attachments:
                    att_status = (attachment.get("status") or "unknown").lower()
                    if att_status not in allowed_statuses:
                        continue

                    saved_filename = self._resolve_saved_filename(attachment)
                    if not saved_filename:
                        logger.warning(
                            f"❌ Вложение без имени в письме {email_file.name}: {attachment}"
                        )
                        continue

                    disk_path = self._resolve_attachment_disk_path(date, attachment)
                    if not disk_path:
                        original_name = attachment.get("original_filename")
                        logger.warning(
                            f"❌ Файл вложения {saved_filename} "
                            f"(оригинал: {original_name}) из письма {email_file.name} не найден на диске."
                        )
                        continue

                    att_result = {
                        "file": saved_filename,
                        "status": "saved",
                        "symbols": 0,
                        "tokens": 0,
                        "reason": attachment.get("reason"),
                        "disk_path": str(disk_path),
                    }

                    ocr_file = self._locate_ocr_for_attachment(date, attachment)
                    if ocr_file:
                        processed_ocr_files.add(ocr_file.name)
                        cached_ocr = self._get_cached_data(ocr_file)
                        if cached_ocr:
                            att_result["symbols"], att_result["tokens"] = cached_ocr
                        else:
                            try:
                                ocr_text = self._read_file_content(ocr_file)
                                if ocr_text:
                                    att_result["symbols"], att_result["tokens"] = self.count_symbols_tokens(ocr_text)
                                    self._update_cache(ocr_file, att_result["symbols"], att_result["tokens"])
                                else:
                                    logger.error(f"Не удалось прочитать OCR файл {ocr_file.name}")
                                    att_result["status"] = "error"
                            except Exception as e:
                                logger.error(f"Ошибка чтения OCR файла {ocr_file.name}: {e}")
                                att_result["status"] = "error"

                        if att_result["status"] != "error":
                            att_result["status"] = "processed"
                    else:
                        att_result["status"] = "saved_no_ocr"
                        logger.info(
                            f"⚠️ Для вложения '{att_result['file']}' в письме {email_file.name} не найден OCR файл"
                        )

                    email_result["attachments"].append(att_result)
                
                date_results.append(email_result)
        else:
            logger.info(f"Папка с письмами для даты {date} не найдена: {emails_dir}")

        # Улучшенная обработка несопоставленных OCR-файлов
        if ocr_dir.exists():
            unprocessed_ocr_files = []
            for ocr_file in ocr_dir.glob("*.txt"):
                if ocr_file.name not in processed_ocr_files:
                    unprocessed_ocr_files.append(ocr_file)
            
            if unprocessed_ocr_files:
                logger.info(f"🔍 Найдено {len(unprocessed_ocr_files)} несопоставленных OCR-файлов за {date}")
                
                # Пытаемся повторно связать OCR файлы с существующими письмами с более гибким алгоритмом
                still_orphaned = []
                
                for ocr_file in unprocessed_ocr_files:
                    matched = False
                    
                    # Пытаемся найти письмо по префиксу email_X_
                    email_prefix = self._extract_email_prefix(ocr_file.name)
                    if email_prefix:
                        email_number = int(email_prefix.split('_')[1])
                        
                        # Ищем соответствующее письмо
                        for email_result in date_results:
                            if self._extract_email_number(email_result["file"]) == email_number:
                                # Добавляем OCR файл как вложение к найденному письму
                                cached_ocr = self._get_cached_data(ocr_file)
                                if cached_ocr:
                                    symbols, tokens = cached_ocr
                                else:
                                    try:
                                        ocr_text = self._read_file_content(ocr_file)
                                        if ocr_text:
                                            symbols, tokens = self.count_symbols_tokens(ocr_text)
                                            self._update_cache(ocr_file, symbols, tokens)
                                        else:
                                            logger.error(f"Не удалось прочитать OCR файл {ocr_file.name}")
                                            symbols, tokens = 0, 0
                                    except Exception as e:
                                        logger.error(f"Ошибка чтения OCR файла {ocr_file.name}: {e}")
                                        symbols, tokens = 0, 0
                                
                                att_result = {
                                    "file": ocr_file.name + " (восстановлено)",
                                    "status": "processed" if symbols > 0 else "error",
                                    "symbols": symbols,
                                    "tokens": tokens
                                }
                                email_result["attachments"].append(att_result)
                                processed_ocr_files.add(ocr_file.name)
                                matched = True
                                logger.info(f"✅ Восстановлена связь: {ocr_file.name} -> {email_result['file']}")
                                break
                    
                    if not matched:
                        still_orphaned.append(ocr_file)
                
                # Только действительно несопоставленные файлы показываем отдельно
                if still_orphaned:
                    logger.warning(f"❓ Остается {len(still_orphaned)} действительно несопоставленных OCR-файлов")
                    
                    orphan_email_result = {
                        "file": f"🔍 Несопоставленные OCR файлы ({len(still_orphaned)} шт.)",
                        "symbols": 0,
                        "tokens": 0,
                        "attachments": []
                    }
                    
                    for ocr_file in sorted(still_orphaned, key=lambda x: x.name):
                        cached_ocr = self._get_cached_data(ocr_file)
                        if cached_ocr:
                            symbols, tokens = cached_ocr
                        else:
                            try:
                                ocr_text = self._read_file_content(ocr_file)
                                if ocr_text:
                                    symbols, tokens = self.count_symbols_tokens(ocr_text)
                                    self._update_cache(ocr_file, symbols, tokens)
                                else:
                                    logger.error(f"Не удалось прочитать OCR файл {ocr_file.name}")
                                    symbols, tokens = 0, 0
                            except Exception as e:
                                logger.error(f"Ошибка чтения OCR файла {ocr_file.name}: {e}")
                                symbols, tokens = 0, 0
                        
                        att_result = {
                            "file": ocr_file.name,
                            "status": "processed" if symbols > 0 else "error",
                            "symbols": symbols,
                            "tokens": tokens
                        }
                        orphan_email_result["attachments"].append(att_result)
                    
                    if orphan_email_result["attachments"]:
                        date_results.append(orphan_email_result)
        
        return date_results

    def _build_diagnostics_section(self, dates: List[str]) -> str:
        """Строит секцию с диагностической информацией."""
        diagnostics_rows = ""

        for date in dates:
            # Подсчет файлов в attachments (исключаем скрытые файлы)
            attachments_dir = self.attachments_path / date
            if attachments_dir.exists():
                attachments_count = len([f for f in attachments_dir.iterdir()
                                       if f.is_file() and not f.name.startswith('.')])
            else:
                attachments_count = 0

            # Подсчет файлов в data/ocr (только .txt файлы)
            ocr_dir = self.final_results_path / date
            ocr_count = len(list(ocr_dir.glob("*.txt"))) if ocr_dir.exists() else 0

            # Подсчет писем
            emails_dir = self.emails_path / date
            emails_count = len(list(emails_dir.glob("*.json"))) if emails_dir.exists() else 0

            # Подсчет вложений на основе данных из JSON файлов писем
            saved_attachments = 0
            missing_attachments = 0
            excluded_attachments = 0
            allowed_statuses = {"saved", "already_exists"}
            if emails_dir.exists():
                for email_file in emails_dir.glob("*.json"):
                    try:
                        with open(email_file, 'r', encoding='utf-8') as f:
                            email_data = json.load(f)
                        email_attachments = self._get_reconciled_attachments(email_data, date)
                        for attachment in email_attachments:
                            status = (attachment.get('status') or '').lower()
                            if status in allowed_statuses:
                                saved_attachments += 1
                                saved_filename = self._resolve_saved_filename(attachment)
                                disk_path = (
                                    self._resolve_attachment_disk_path(date, attachment)
                                    if saved_filename else None
                                )
                                if (not saved_filename) or (disk_path is None):
                                    missing_attachments += 1
                            elif status in {
                                'excluded',
                                'excluded_filename',
                                'excluded_by_filter',
                                'excluded_by_size',
                                'excluded_inline_image',
                                'unsupported',
                            }:
                                excluded_attachments += 1
                    except (IOError, json.JSONDecodeError) as e:
                        logger.warning(f"Ошибка чтения файла письма {email_file.name}: {e}")

            # Определяем статус с улучшенной логикой
            status_class = ""
            if saved_attachments == 0:
                status_class = "status-ok"
            elif missing_attachments > 0:
                status_class = "status-missing"
            elif attachments_count != ocr_count:
                status_class = "status-mismatch"
            else:
                status_class = "status-ok"

            diagnostics_rows += f"""
            <tr class="{status_class}">
                <td>{date}</td>
                <td class="number">{emails_count}</td>
                <td class="number">{attachments_count}</td>
                <td class="number">{ocr_count}</td>
                <td class="status-cell">{self._get_status_text(saved_attachments, attachments_count, ocr_count, missing_attachments)}</td>
            </tr>
            """
        
        return f"""
        <details class="diagnostics-section" open>
            <summary class="diagnostics-header">📊 Диагностика файлов</summary>
            <div class="diagnostics-content">
                <table class="diagnostics-table">
                    <thead>
                        <tr>
                            <th>Дата</th>
                            <th>Письма</th>
                            <th>Вложения</th>
                            <th>OCR файлы</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        {diagnostics_rows}
                    </tbody>
                </table>
            </div>
        </details>
        """
        
        return f"""
        <details class="diagnostics-section" open>
            <summary class="diagnostics-header">📊 Диагностика файлов</summary>
            <div class="diagnostics-content">
                <table class="diagnostics-table">
                    <thead>
                        <tr>
                            <th>Дата</th>
                            <th>Письма</th>
                            <th>Вложения</th>
                            <th>OCR файлы</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        {diagnostics_rows}
                    </tbody>
                </table>
            </div>
        </details>
        """

    def _build_top_attachments_section(self, all_results: Dict[str, List[Dict]]) -> str:
        """Строит секцию с ТОП-30 вложений по количеству символов."""
        # Собираем все вложения из всех дат
        all_attachments = []

        for date, emails in all_results.items():
            for email in emails:
                for attachment in email.get('attachments', []):
                    if attachment['symbols'] > 0:  # Только вложения с содержимым
                        all_attachments.append({
                            'file': attachment['file'],
                            'symbols': attachment['symbols'],
                            'tokens': attachment['tokens'],
                            'date': date,
                            'email': email['file'],
                            'disk_path': attachment.get('disk_path')
                        })

        # Сортируем по количеству символов (по убыванию) и берем топ-30
        top_attachments = sorted(all_attachments, key=lambda x: x['symbols'], reverse=True)[:30]

        if not top_attachments:
            return ""

        # Строим HTML таблицу
        top_rows = ""
        for i, att in enumerate(top_attachments, 1):
            # Создаем кликабельную ссылку с JavaScript для открытия файла
            if att.get('disk_path'):
                file_path = str(Path(att['disk_path']).resolve())
            else:
                file_path = str((self.attachments_path / att['date'] / att['file']).resolve())
            top_rows += f"""
            <tr class="top-attachment-row">
                <td class="number">{i}</td>
                <td class="file-name">
                    <button onclick="openFile('{file_path}')" class="file-link" title="Открыть файл: {att['file']}">
                        {att['file']}
                    </button>
                    <br><small class="file-info">{att['date']} • {att['email']}</small>
                </td>
                <td class="symbols">{self.format_number(att['symbols'])}</td>
                <td class="tokens">{self.format_number(att['tokens'])}</td>
            </tr>
            """

        return f"""
        <details class="top-attachments-section" open>
            <summary class="top-attachments-header">📊 ТОП-30 вложений по символам</summary>
            <div class="top-attachments-content">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th class="rank-column">#</th>
                            <th class="file-column">Файл</th>
                            <th class="symbols-column">Символы</th>
                            <th class="tokens-column">Токены</th>
                        </tr>
                    </thead>
                    <tbody>
                        {top_rows}
                    </tbody>
                </table>
            </div>
        </details>
        """

    def format_number(self, number: int) -> str:
        """Форматирование числа с разделителем разрядов (пробел справа налево через 3 знака)."""
        if number == 0:
            return "0"
        # Преобразуем число в строку и разбиваем на группы по 3 символа справа налево
        num_str = str(number)
        # Разбиваем на группы по 3 символа, начиная с конца
        groups = []
        while len(num_str) > 3:
            groups.insert(0, num_str[-3:])
            num_str = num_str[:-3]
        groups.insert(0, num_str)  # Оставшаяся часть
        return ' '.join(groups)
    
    def _get_status_text(
        self,
        saved_attachments: int,
        attachments_count: int,
        ocr_count: int,
        missing_attachments: int,
    ) -> str:
        """Возвращает текст статуса для диагностики."""
        if saved_attachments == 0:
            return "📭 Без вложений"
        if missing_attachments > 0:
            return f"❌ Отсутствуют файлы: {missing_attachments}"
        if attachments_count == ocr_count:
            return "✅ Соответствие"
        if attachments_count > ocr_count:
            return f"⚠️ Не обработано OCR: {attachments_count - ocr_count}"
        return f"❓ Дубли OCR: +{ocr_count - attachments_count}"

    def build_html_report(self, all_results: Dict[str, List[Dict]]) -> str:
        """Строит и возвращает HTML-отчет на основе обработанных данных."""
        if not all_results:
            return "<h1>Нет данных для отображения.</h1>"

        # Сортировка дат от самой новой к старой
        sorted_dates = sorted(all_results.keys(), reverse=True)
        
        grand_total_symbols = 0
        grand_total_tokens = 0

        # Сбор диагностической информации
        diagnostics_html = self._build_diagnostics_section(sorted_dates)

        # Сбор информации о ТОП вложениях
        top_attachments_html = self._build_top_attachments_section(all_results)

        date_sections_html = ""
        for date in sorted_dates:
            date_emails = all_results[date]
            date_total_symbols = 0
            date_total_tokens = 0
            
            # Сортировка писем по номеру
            sorted_emails = sorted(date_emails, key=lambda x: x['file'])
            
            email_rows_html = ""
            for email in sorted_emails:
                email_total_symbols = email['symbols']
                email_total_tokens = email['tokens']
                
                # Проверяем, есть ли вложения
                has_attachments = bool(email['attachments'])
                
                # Строка с письмом
                if has_attachments:
                    # Если есть вложения, показываем символы и токены письма
                    email_rows_html += f"""
                <tr class="email-row">
                    <td class="file-name">{email['file']}</td>
                    <td class="symbols">{self.format_number(email['symbols'])}</td>
                    <td class="tokens">{self.format_number(email['tokens'])}</td>
                </tr>
                """
                else:
                    # Если нет вложений, показываем только имя файла
                    email_rows_html += f"""
                <tr class="email-row">
                    <td class="file-name">{email['file']}</td>
                    <td class="symbols"></td>
                    <td class="tokens"></td>
                </tr>
                """
                
                # Строки с вложениями
                if has_attachments:
                    for att in email['attachments']:
                        email_total_symbols += att['symbols']
                        email_total_tokens += att['tokens']
                        
                        status_text = ""
                        if att['status'] == 'saved_no_ocr':
                            status_text = " (нет OCR)"
                        elif att['status'] == 'saved':
                            status_text = " (ожидает OCR)"
                        elif att['status'] == 'error':
                            status_text = " (ошибка чтения)"

                        email_rows_html += f"""
                <tr class="attachment-row">
                    <td class="file-name attachment-indent">{att['file']}{status_text}</td>
                    <td class="symbols attachment-number">{self.format_number(att['symbols'])}</td>
                    <td class="tokens attachment-number">{self.format_number(att['tokens'])}</td>
                </tr>
                        """
                
                # Строка итого по письму (ИТОГО в первой колонке справа, цифры без префикса)
                email_rows_html += f"""
                <tr class="email-total-row">
                    <td class="file-name total-label total-right">ИТОГО:</td>
                    <td class="symbols total-value email-total">{self.format_number(email_total_symbols)}</td>
                    <td class="tokens total-value email-total">{self.format_number(email_total_tokens)}</td>
                </tr>
                """

                date_total_symbols += email_total_symbols
                date_total_tokens += email_total_tokens

            grand_total_symbols += date_total_symbols
            grand_total_tokens += date_total_tokens

            # Секция для даты
            date_sections_html += f"""
            <div class="date-section" data-date="{date}">
                <div class="date-header" onclick="toggleDateSection(this)">
                    <span>{date}</span>
                    <span class="arrow">▼</span>
                </div>
                <div class="date-content">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th class="file-column">Файл</th>
                                <th class="symbols-column">Символы</th>
                                <th class="tokens-column">Токены</th>
                            </tr>
                        </thead>
                        <tbody>
                            {email_rows_html}
                            <tr class="date-total-row">
                                <td class="file-name total-label">ИТОГО за {date}:</td>
                                <td class="symbols total-value">{self.format_number(date_total_symbols)}</td>
                                <td class="tokens total-value">{self.format_number(date_total_tokens)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            """

        # Финальный HTML с общим итогом
        final_total_html = f"""
        <div class="grand-total">
            <table class="data-table">
                <tbody>
                    <tr class="grand-total-row">
                        <td class="file-name total-label">ОБЩИЙ ИТОГ:</td>
                        <td class="symbols total-value">{self.format_number(grand_total_symbols)}</td>
                        <td class="tokens total-value">{self.format_number(grand_total_tokens)}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        
        # Финальный HTML с правильной структурой липких заголовков
        return f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчёт по файлам и токенам</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #ffffff;
            color: #333;
            line-height: 1.4;
            padding-top: 0;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* Основной заголовок - всегда на верху */
        .header {{
            position: sticky;
            top: 0;
            background: #ffffff;
            z-index: 1000;
            padding: 15px 0;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            text-align: center;
            font-size: 24px;
            font-weight: 600;
            color: #333;
        }}
        
        /* Диагностика - обычная секция */
        .diagnostics-section {{
            margin-bottom: 20px;
            border: 2px solid #007bff;
            border-radius: 8px;
            background: #f8f9fa;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        /* Только заголовок диагностики липкий */
        .diagnostics-header {{
            position: sticky;
            top: 70px;
            z-index: 900;
            background: #007bff;
            color: white;
            padding: 12px 15px;
            margin: 0;
            cursor: pointer;
            font-weight: bold;
            border-radius: 6px 6px 0 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .diagnostics-content {{
            padding: 15px;
        }}
        
        .diagnostics-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0;
        }}
        
        .diagnostics-table th,
        .diagnostics-table td {{
            padding: 8px 12px;
            text-align: left;
            border: 1px solid #dee2e6;
        }}
        
        .diagnostics-table th {{
            background: #e9ecef;
            font-weight: bold;
        }}
        
        .diagnostics-table .number {{ text-align: center; }}
        
        /* Статусы диагностики */
        .status-ok {{ background-color: #d4edda; }}
        .status-mismatch {{ background-color: #fff3cd; }}
        .status-empty {{ background-color: #f8d7da; }}
        .status-missing {{ background-color: #f5c6cb; color: #721c24 !important; }}
        .status-cell {{ font-weight: bold; }}

        /* Раздел ТОП вложений */
        .top-attachments-section {{
            margin-bottom: 30px;
            border: 2px solid #17a2b8;
            border-radius: 8px;
            background: #f8f9fa;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .top-attachments-header {{
            position: sticky;
            top: 70px;
            z-index: 900;
            background: #17a2b8;
            color: white;
            padding: 12px 15px;
            margin: 0;
            cursor: pointer;
            font-weight: bold;
            border-radius: 6px 6px 0 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .top-attachments-content {{
            padding: 15px;
        }}

        .top-attachment-row {{
            background: #ffffff;
            border-bottom: 1px solid #f0f0f0;
        }}

        .top-attachment-row:hover {{
            background: #f8f9fa;
        }}

        .top-attachment-row td {{
            padding: 12px 15px;
            vertical-align: middle;
        }}

        .top-attachment-row .file-name {{
            font-weight: 600;
            color: #333;
        }}

        .file-link {{
            background: none;
            border: none;
            color: #007bff;
            text-decoration: underline;
            cursor: pointer;
            font-family: inherit;
            font-size: inherit;
            font-weight: 600;
            padding: 0;
            text-align: left;
        }}

        .file-link:hover {{
            color: #0056b3;
            text-decoration: none;
        }}

        .file-info {{
            color: #666;
            font-weight: normal;
            font-size: 11px;
        }}

        .rank-column {{
            width: 40px;
            text-align: center;
            font-weight: bold;
            color: #17a2b8;
        }}

        /* Секция даты */
        .date-section {{
            margin-bottom: 30px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            overflow: visible;
            background: #ffffff;
        }}
        
        /* Заголовок даты - становится липким */
        .date-header {{
            background: #f5f5f5;
            padding: 12px 20px;
            font-size: 16px;
            font-weight: 600;
            color: #333;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #dee2e6;
            transition: all 0.2s ease;
        }}
        
        .date-header:hover {{
            background: #e9ecef;
        }}
        
        .date-header.is-sticky {{
            position: sticky;
            top: 114px;
            z-index: 800;
            background: #e9ecef;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            font-weight: 700;
        }}
        
        .arrow {{
            transition: transform 0.3s ease;
            font-size: 18px;
            font-weight: bold;
        }}
        
        .date-section.collapsed .arrow {{
            transform: rotate(-90deg);
        }}
        
        .date-section.collapsed .date-content {{
            display: none;
        }}
        
        /* Контент даты */
        .date-content {{
            background: #ffffff;
        }}
        
        /* Таблица данных */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 0;
        }}
        
        .data-table th {{
            background: #f8f9fa;
            padding: 12px 15px;
            border: 1px solid #dee2e6;
            font-weight: 600;
            font-size: 14px;
            color: #495057;
            text-align: left;
            position: sticky;
            z-index: 700;
        }}
        
        .data-table th.symbols-column,
        .data-table th.tokens-column {{
            text-align: center;
            width: 120px;
        }}
        
        .sticky-table-header {{
            top: 162px !important;
        }}
        
        .data-table td {{
            padding: 8px 15px;
            border: 1px solid #f0f0f0;
            vertical-align: middle;
            min-height: 40px;
        }}
        
        .data-table td.symbols,
        .data-table td.tokens {{
            text-align: right;
            font-family: 'Manrope', 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-weight: 600;
            width: 120px;
        }}
        
        /* Стили строк */
        .email-row {{
            background: #ffffff;
        }}
        
        .email-row td {{
            font-weight: 600;
            color: #333;
            min-height: 40px;
        }}
        
        .attachment-row {{
            background: #fafbfc;
        }}
        
        .attachment-row td.file-name {{
            padding-left: 35px;
            color: #666;
            font-size: 13px;
            font-weight: normal;
        }}
        
        .attachment-row .attachment-number {{
            color: #666;
            font-size: 13px;
            font-weight: normal;
            font-family: 'Manrope', 'SF Mono', Monaco, 'Cascadia Code', monospace;
        }}
        
        .email-total-row {{
            background: #f8f9fa;
        }}
        
        .email-total-row td {{
            font-weight: 600;
            border-top: 1px solid #dee2e6;
        }}
        
        .date-total-row {{
            background: #e9ecef;
        }}
        
        .date-total-row td {{
            font-weight: 700;
            font-size: 16px;
            border-top: 2px solid #dee2e6;
            padding: 15px;
        }}
        
        /* Итоги */
        .email-total {{
            text-align: right !important;
        }}
        
        .total-value {{
            text-align: right;
        }}
        
        .total-right {{
            text-align: right;
        }}
        
        .grand-total {{
            margin-top: 30px;
            padding: 20px;
            background: #e3f2fd;
            border: 2px solid #2196f3;
            border-radius: 8px;
            text-align: center;
            font-size: 18px;
            font-weight: 700;
        }}
        
        .grand-total-row td {{
            font-weight: 700;
            font-size: 18px;
            padding: 20px 15px;
        }}
        
        /* Скрытое содержимое */
        .no-attachments {{
            color: #999;
            font-style: italic;
            padding: 8px 15px 8px 35px;
            background: #fafbfc;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Отчёт по файлам и токенам</h1>
        </div>
        
        {diagnostics_html}

        {top_attachments_html}

        {date_sections_html}

        {final_total_html}
    </div>
    
    <script>
                // Функция для показа пути к файлу
        function openFile(filePath) {{
            // Показываем полный путь к файлу для ручного открытия
            const message = '📁 Путь к файлу:\\n' + filePath + '\\n\\n' +
                           '💡 Инструкция:\\n' +
                           '1. Скопируйте путь выше\\n' +
                           '2. Откройте Finder\\n' +
                           '3. Нажмите Cmd+Shift+G\\n' +
                           '4. Вставьте путь и нажмите Enter';

            // Пытаемся скопировать в буфер обмена
            if (navigator.clipboard && window.isSecureContext) {{
                navigator.clipboard.writeText(filePath).then(function() {{
                    alert(message + '\\n\\n✅ Путь скопирован в буфер обмена!');
                }}).catch(function() {{
                    alert(message + '\\n\\n❌ Не удалось скопировать в буфер');
                }});
            }} else {{
                // Fallback для браузеров без clipboard API
                alert(message + '\\n\\nСкопируйте путь вручную.');
            }}
        }}

        // Переключение развертывания секции
        function toggleDateSection(header) {{
            const section = header.parentElement;
            const content = section.querySelector('.date-content');
            const arrow = header.querySelector('.arrow');
            
            section.classList.toggle('collapsed');
            
            if (section.classList.contains('collapsed')) {{
                // Закрыть секцию
                if (content) {{
                    content.style.display = 'none';
                }}
                if (arrow) {{
                    arrow.textContent = '▶';
                }}
            }} else {{
                // Открыть секцию
                if (content) {{
                    content.style.display = 'block';
                }}
                if (arrow) {{
                    arrow.textContent = '▼';
                }}
            }}
            
            // Обновить липкие заголовки после изменения
            setTimeout(updateStickyHeaders, 100);
        }}
        
        // Система липких заголовков
        function updateStickyHeaders() {{
            const dateHeaders = document.querySelectorAll('.date-header');
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            // Сбросить все липкие состояния
            dateHeaders.forEach(header => {{
                header.classList.remove('is-sticky');
                const tableHeaders = header.parentElement.querySelectorAll('.data-table th');
                tableHeaders.forEach(th => {{
                    th.classList.remove('sticky-table-header');
                }});
            }});
            
            // Найти активную секцию и применить липкие стили
            for (let i = 0; i < dateHeaders.length; i++) {{
                const header = dateHeaders[i];
                const section = header.parentElement;
                const sectionRect = section.getBoundingClientRect();
                const headerRect = header.getBoundingClientRect();
                
                // Если секция пересекается с позицией 114px (под диагностикой)
                if (sectionRect.top <= 114 && sectionRect.bottom > 114) {{
                    header.classList.add('is-sticky');
                    
                    // Сделать заголовки таблицы липкими тоже
                    const tableHeaders = section.querySelectorAll('.data-table th');
                    tableHeaders.forEach(th => {{
                        th.classList.add('sticky-table-header');
                    }});
                    
                    break;
                }}
            }}
        }}
        
        // Инициализация
        window.addEventListener('DOMContentLoaded', function() {{
            // Закрыть ВСЕ секции по умолчанию (включая первую)
            const allSections = document.querySelectorAll('.date-section');
            allSections.forEach((section, index) => {{
                // Все секции закрыты по умолчанию
                section.classList.add('collapsed');
                const content = section.querySelector('.date-content');
                if (content) {{
                    content.style.display = 'none';
                }}
                const arrow = section.querySelector('.arrow');
                if (arrow) {{
                    arrow.textContent = '▶';
                }}
            }});
            
            // Первичная установка липких заголовков
            updateStickyHeaders();
        }});
        
        // Обновление при скролле и изменении размера
        window.addEventListener('scroll', updateStickyHeaders);
        window.addEventListener('resize', updateStickyHeaders);
    </script>
</body>
</html>
"""

    def run(self):
        """Основной метод запуска обработки."""
        selected_date = self.choose_date_menu()
        if not selected_date:
            logger.info("Обработка отменена пользователем.")
            return

        all_results = {}
        
        if selected_date == "all":
            dates = self.get_available_dates()
            logger.info(f"Обработка всех дат: {', '.join(dates)}")
            for date in dates:
                results = self.process_date(date)
                if results:
                    all_results[date] = results
        else:
            logger.info(f"Обработка даты: {selected_date}")
            results = self.process_date(selected_date)
            if results:
                all_results[selected_date] = results

        if all_results:
            html_content = self.build_html_report(all_results)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.output_path / f"report_file_tokens_{timestamp}.html"
            
            try:
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print("\n" + "="*60)
                print("✅ ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО!")
                print("="*60)
                print(f"📊 Отчёт сохранён: {report_file}")
                print(f"🔗 Откройте файл в браузере для просмотра")
                print("="*60)
                logger.info(f"HTML-отчёт сохранён: {report_file}")
            except IOError as e:
                logger.error(f"Ошибка сохранения отчёта: {e}")
        else:
            logger.warning("Нет данных для создания отчёта.")
        
        self._save_cache()

if __name__ == '__main__':
    counter = FileTokenCounter()
    counter.run()
