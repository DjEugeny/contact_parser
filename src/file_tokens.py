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
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import tiktoken

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
        self.base_path = Path("data")
        self.emails_path = self.base_path / "emails"
        self.attachments_path = self.base_path / "attachments"
        self.final_results_path = self.base_path / "final_results" / "texts"
        self.output_path = self.base_path / "file_tokens"
        self.cache_file = self.base_path / ".processed_file_tokens.json"
        
        self.output_path.mkdir(exist_ok=True)
        self.processed_files = self._load_cache()
        
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
            if isinstance(cached_info, dict) and cached_info.get('hash') == current_hash:
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
                'hash': current_hash,
                'symbols': symbols,
                'tokens': tokens
            }

    def get_available_dates(self) -> List[str]:
        """Получает отсортированный список доступных дат из папок emails и final_results/texts."""
        dates = set()
        
        # Добавляем даты из папки emails
        if self.emails_path.exists():
            for date_folder in self.emails_path.iterdir():
                if date_folder.is_dir() and not date_folder.name.startswith('.'):
                    dates.add(date_folder.name)
        
        # Добавляем даты из папки final_results/texts (для случаев, когда есть только OCR-файлы)
        if self.final_results_path.exists():
            for date_folder in self.final_results_path.iterdir():
                if date_folder.is_dir() and not date_folder.name.startswith('.'):
                    dates.add(date_folder.name)
        
        return sorted(list(dates), reverse=True)

    def choose_date_menu(self) -> Optional[str]:
        """Отображает интерактивное меню для выбора даты обработки."""
        dates = self.get_available_dates()
        if not dates:
            logger.error("В директории 'data/emails' не найдено папок с датами для обработки.")
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

    def count_symbols_tokens(self, text: str) -> Tuple[int, int]:
        """Подсчитывает количество символов и токенов в тексте."""
        if not text or not isinstance(text, str):
            return 0, 0
        
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
        
        # Этап 3: Частичное совпадение (базовое имя содержится в OCR файле)
        for ocr_file in all_ocr_files:
            if attachment_base in ocr_file.name:
                logger.debug(f"Найдено частичное совпадение: {attachment_base} содержится в {ocr_file.name}")
                return ocr_file
        
        # Этап 4: Обратное частичное совпадение (OCR имя содержится в attachment)
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
                body_text = email_data.get('body', '')
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
                attachments = email_data.get('attachments', [])
                for attachment in attachments:
                    saved_filename = attachment.get('saved_filename')
                    if not saved_filename:
                        continue

                    ocr_file = self._find_ocr_file(date, saved_filename)
                    att_result = {"file": saved_filename, "status": "unprocessed", "symbols": 0, "tokens": 0}

                    if ocr_file:
                        processed_ocr_files.add(ocr_file.name)
                        cached_ocr = self._get_cached_data(ocr_file)
                        if cached_ocr:
                            att_result["symbols"], att_result["tokens"] = cached_ocr
                        else:
                            try:
                                ocr_text = ocr_file.read_text(encoding='utf-8')
                                att_result["symbols"], att_result["tokens"] = self.count_symbols_tokens(ocr_text)
                                self._update_cache(ocr_file, att_result["symbols"], att_result["tokens"])
                            except IOError as e:
                                logger.error(f"Ошибка чтения OCR файла {ocr_file.name}: {e}")
                                att_result["status"] = "error"
                        
                        if att_result["status"] != "error":
                            att_result["status"] = "processed"
                    else:
                        logger.warning(f"Для вложения '{saved_filename}' не найден OCR файл.")

                    email_result["attachments"].append(att_result)
                
                date_results.append(email_result)
        else:
            logger.info(f"Папка с письмами для даты {date} не найдена: {emails_dir}")

        # Обработка OCR-файлов без соответствующих писем
        if ocr_dir.exists():
            unprocessed_ocr_files = []
            for ocr_file in ocr_dir.glob("*.txt"):
                if ocr_file.name not in processed_ocr_files:
                    unprocessed_ocr_files.append(ocr_file)
            
            if unprocessed_ocr_files:
                logger.info(f"Найдено {len(unprocessed_ocr_files)} OCR-файлов без соответствующих писем за {date}")
                
                # Создаем виртуальное письмо для несопоставленных OCR-файлов
                orphan_email_result = {
                    "file": f"orphaned_ocr_files_{date}",
                    "symbols": 0,
                    "tokens": 0,
                    "attachments": []
                }
                
                for ocr_file in sorted(unprocessed_ocr_files, key=lambda x: x.name):
                    cached_ocr = self._get_cached_data(ocr_file)
                    if cached_ocr:
                        symbols, tokens = cached_ocr
                    else:
                        try:
                            ocr_text = ocr_file.read_text(encoding='utf-8')
                            symbols, tokens = self.count_symbols_tokens(ocr_text)
                            self._update_cache(ocr_file, symbols, tokens)
                        except IOError as e:
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
            # Подсчет файлов в attachments
            attachments_dir = self.attachments_path / date
            attachments_count = len(list(attachments_dir.glob("*"))) if attachments_dir.exists() else 0
            
            # Подсчет файлов в final_results
            ocr_dir = self.final_results_path / date
            ocr_count = len(list(ocr_dir.glob("*.txt"))) if ocr_dir.exists() else 0
            
            # Подсчет писем
            emails_dir = self.emails_path / date
            emails_count = len(list(emails_dir.glob("*.json"))) if emails_dir.exists() else 0
            
            status_class = ""
            if attachments_count == 0 and ocr_count == 0:
                status_class = "status-empty"
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
                <td class="status-cell">{self._get_status_text(attachments_count, ocr_count)}</td>
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
    
    def _get_status_text(self, attachments_count: int, ocr_count: int) -> str:
        """Возвращает текст статуса для диагностики."""
        if attachments_count == 0 and ocr_count == 0:
            return "Нет файлов"
        elif attachments_count == ocr_count:
            return "✅ Соответствие"
        elif attachments_count > ocr_count:
            return f"⚠️ Не обработано: {attachments_count - ocr_count}"
        else:
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
                
                # Строка с письмом
                email_rows_html += f"""
                <tr class="email-row">
                    <td class="file-name">{email['file']}</td>
                    <td class="symbols">{email['symbols']:,}</td>
                    <td class="tokens">{email['tokens']:,}</td>
                </tr>
                """
                
                # Строки с вложениями
                if email['attachments']:
                    for att in email['attachments']:
                        email_total_symbols += att['symbols']
                        email_total_tokens += att['tokens']
                        
                        status_text = ""
                        if att['status'] == 'unprocessed':
                            status_text = " (не обработано)"
                        elif att['status'] == 'error':
                            status_text = " (ошибка чтения)"

                        email_rows_html += f"""
                <tr class="attachment-row">
                    <td class="file-name attachment-indent">{att['file']}{status_text}</td>
                    <td class="symbols">{att['symbols']:,}</td>
                    <td class="tokens">{att['tokens']:,}</td>
                </tr>
                        """
                
                # Строка итого по письму
                email_rows_html += f"""
                <tr class="email-total-row">
                    <td class="file-name total-label">ИТОГО:</td>
                    <td class="symbols total-value">{email_total_symbols:,}</td>
                    <td class="tokens total-value">{email_total_tokens:,}</td>
                </tr>
                """

                date_total_symbols += email_total_symbols
                date_total_tokens += email_total_tokens

            grand_total_symbols += date_total_symbols
            grand_total_tokens += date_total_tokens

            # Секция для даты
            date_sections_html += f"""
            <details class="date-section">
                <summary class="date-header">{date}</summary>
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
                            <td class="symbols total-value">{date_total_symbols:,}</td>
                            <td class="tokens total-value">{date_total_tokens:,}</td>
                        </tr>
                    </tbody>
                </table>
            </details>
            """

        # Финальный HTML с общим итогом
        final_total_html = f"""
        <div class="grand-total">
            <table class="data-table">
                <tbody>
                    <tr class="grand-total-row">
                        <td class="file-name total-label">ОБЩИЙ ИТОГ:</td>
                        <td class="symbols total-value">{grand_total_symbols:,}</td>
                        <td class="tokens total-value">{grand_total_tokens:,}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        
        # Финальный HTML
        return f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчёт по файлам и токенам</title>
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
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            position: sticky;
            top: 0;
            background: #ffffff;
            z-index: 100;
            padding: 15px 0;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 20px;
        }}
        .header h1 {{
            text-align: center;
            font-size: 24px;
            font-weight: 600;
            color: #333;
        }}
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
        }}
        .data-table th.symbols-column,
        .data-table th.tokens-column {{
            text-align: center;
            width: 120px;
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
             font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
             width: 120px;
         }}
        .date-section {{
             margin-bottom: 30px;
             border: 1px solid #dee2e6;
             border-radius: 8px;
             overflow: hidden;
         }}
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
        .grand-total-row td {{
             font-weight: 700;
             font-size: 18px;
             padding: 20px 15px;
         }}
        .date-header {{
              background: #f5f5f5;
              padding: 12px 20px;
              font-size: 16px;
              font-weight: normal;
              color: #666;
              cursor: pointer;
              display: flex;
              justify-content: space-between;
              align-items: center;
          }}
        .date-header:hover {{
            background: #e8eaed;
        }}
        .date-content {{
            background: #ffffff;
        }}
        .no-attachments {{
            color: #999;
            font-style: italic;
            padding: 8px 15px 8px 35px;
            background: #fafbfc;
            font-size: 13px;
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
        .arrow {{
            transition: transform 0.3s ease;
            font-size: 20px;
        }}
        .date-section.collapsed .arrow {{
            transform: rotate(-90deg);
        }}
        .date-section.collapsed .date-content {{
            display: none;
        }}
        
        /* Диагностика */
        .diagnostics-section {{
            margin-bottom: 20px;
            border: 2px solid #007bff;
            border-radius: 8px;
            background: #f8f9fa;
        }}
        .diagnostics-header {{
            background: #007bff;
            color: white;
            padding: 12px 15px;
            margin: 0;
            cursor: pointer;
            font-weight: bold;
            border-radius: 6px 6px 0 0;
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
        .status-ok {{ background-color: #d4edda; }}
        .status-mismatch {{ background-color: #fff3cd; }}
        .status-empty {{ background-color: #f8d7da; }}
        .status-cell {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Отчёт по файлам и токенам</h1>
        </div>
        
        {diagnostics_html}
        
        {date_sections_html}
        
        {final_total_html}
    </div>
    
    <script>
        function toggleDate(header) {{
            const section = header.parentElement;
            section.classList.toggle('collapsed');
        }}
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
