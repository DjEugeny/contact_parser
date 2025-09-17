#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Гибридный OCR тестер v13 (Google Cloud Vision Edition) - "Бронебойная" версия
- Для экстремально больших или нестандартных страниц PDF используется надежный метод
  конвертации через временные файлы на диске.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time
from datetime import datetime
import subprocess
import shutil
import io
import logging
import traceback
from logging.handlers import RotatingFileHandler
import re
import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
from google.api_core import exceptions as google_exceptions
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from file_utils import normalize_filename

Image.MAX_IMAGE_PIXELS = None

# ... (остальные импорты без изменений) ...
try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False
try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
try:
    from docx import Document as DocxDocument
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

class OCRProcessor:
    # ... (init, _show_capabilities, get_available_dates, get_files_for_date, run_google_vision_ocr - без изменений) ...
    def __init__(self):
        self.data_dir = Path("data")
        self.attachments_dir = self.data_dir / "attachments"
        self.base_results_dir = self.data_dir / "final_results"
        self.texts_dir = self.base_results_dir / "texts"
        self.reports_dir = self.base_results_dir / "reports"
        self.logs_dir = self.data_dir / "logs" / "ocr"
        self.texts_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройка логирования
        self._setup_logging()
        
        # Инициализация кэша структурного анализа PDF
        self._pdf_structure_cache = {}
        self._cache_dir = self.data_dir / "cache" / "pdf_analysis"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_pdf_structure_cache()
        
        self.vision_client = vision.ImageAnnotatorClient() if GOOGLE_VISION_AVAILABLE else None
        
        if GOOGLE_VISION_AVAILABLE and self.vision_client:
            self.logger.info("Google Cloud Vision API успешно инициализирован")
        else:
            self.logger.error("Google Cloud Vision API не инициализирован")
        
        self._show_capabilities()
        print("\n" + "=" * 70)
        print("🎯 OCR ТЕСТЕР С GOOGLE CLOUD VISION v13 🎯")
        print(f"📁 Исходные файлы: {self.attachments_dir}")
        print(f"🗂️  Результаты в папке: {self.base_results_dir}")
        print(f"💾 Кэш PDF анализа: {self._cache_dir}")
        print("=" * 70)
    def _setup_logging(self):
        """🔧 Настройка системы логирования с ротацией файлов"""
        
        # Создаем логгер
        self.logger = logging.getLogger('OCRProcessor')
        self.logger.setLevel(logging.INFO)
        
        # Очищаем существующие обработчики
        self.logger.handlers.clear()
        
        # Форматтер для логов
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Файловый обработчик с ротацией (максимум 10MB, 5 файлов)
        log_file = self.logs_dir / 'ocr_processor.log'
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Консольный обработчик для критических ошибок
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(formatter)
        
        # Добавляем обработчики
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("=" * 50)
        self.logger.info("OCR Processor запущен")
        self.logger.info(f"Логи сохраняются в: {log_file}")
    
    def _load_pdf_structure_cache(self):
        """💾 Загрузка кэша структурного анализа PDF"""
        cache_file = self._cache_dir / "pdf_structure_cache.json"
        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self._pdf_structure_cache = json.load(f)
                self.logger.info(f"💾 Загружен кэш PDF анализа: {len(self._pdf_structure_cache)} записей")
            else:
                self._pdf_structure_cache = {}
                self.logger.info("💾 Создан новый кэш PDF анализа")
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки кэша PDF анализа: {e}")
            self._pdf_structure_cache = {}
    
    def _save_pdf_structure_cache(self):
        """💾 Сохранение кэша структурного анализа PDF"""
        cache_file = self._cache_dir / "pdf_structure_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._pdf_structure_cache, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"💾 Кэш PDF анализа сохранен: {len(self._pdf_structure_cache)} записей")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения кэша PDF анализа: {e}")
    
    def _get_pdf_cache_key(self, pdf_path: Path) -> str:
        """🔑 Генерация ключа кэша для PDF файла"""
        try:
            # Используем путь, размер файла и время модификации для уникальности
            stat = pdf_path.stat()
            cache_data = f"{pdf_path.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(cache_data.encode('utf-8')).hexdigest()
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации ключа кэша для {pdf_path}: {e}")
            return hashlib.md5(str(pdf_path).encode('utf-8')).hexdigest()
        
    def _show_capabilities(self):
        antiword_ok = shutil.which('antiword') is not None
        print("📋 ВОЗМОЖНОСТИ СИСТЕМЫ:")
        if GOOGLE_VISION_AVAILABLE and self.vision_client:
            print("   ☁️ Google Cloud Vision: ✅ Готов к работе!")
        else:
            print("   ☁️ Google Cloud Vision: ❌ НЕ НАСТРОЕН!")
        local_status = [f"PDF (текст) {'✅' if PYMUPDF_AVAILABLE else '❌'}", f"DOCX {'✅' if PYTHON_DOCX_AVAILABLE else '❌'}", f"XLSX {'✅' if OPENPYXL_AVAILABLE else '❌'}", f"DOC (antiword) {'✅' if antiword_ok else '❌ (brew install antiword)'}", f"XLS (xlrd) {'✅' if XLRD_AVAILABLE else '❌'}"]
        print(f"   📄 Локальные форматы: {' | '.join(local_status)}")
    def get_available_dates(self) -> List[str]:
        if not self.attachments_dir.exists(): return []
        return sorted([d.name for d in self.attachments_dir.iterdir() if d.is_dir() and d.name.count("-") == 2])
    def get_files_for_date(self, date: str) -> List[Path]:
        """Получение списка файлов для обработки на основе JSON метаданных писем"""
        # Нормализуем формат даты
        normalized_date = self._normalize_date_format(date)
        
        date_dir = self.attachments_dir / normalized_date
        if not date_dir.exists():
            print(f"❌ Папка не существует: {date_dir}")
            return []

        # Получаем список сохраненных файлов из JSON метаданных
        saved_files = self._get_saved_files_from_metadata(normalized_date)
        
        if saved_files:
            print(f"📋 Найдено {len(saved_files)} сохраненных файлов из метаданных писем")
            return saved_files
        
        # Fallback на старый метод если метаданные недоступны
        print(f"⚠️ Метаданные писем недоступны, используем fallback метод")
        return self._get_files_fallback(date_dir)
    
    def _get_saved_files_from_metadata(self, date: str) -> List[Path]:
        """Получение списка сохраненных файлов из JSON метаданных писем"""
        # Нормализуем формат даты
        normalized_date = self._normalize_date_format(date)
        
        emails_dir = Path("data/emails") / normalized_date
        saved_files = []
        
        if not emails_dir.exists():
            self.logger.warning(f"Папка с письмами не найдена: {emails_dir}")
            return []
        
        try:
            # Ищем все JSON файлы писем
            json_files = list(emails_dir.glob("email_*.json"))
            self.logger.info(f"Найдено {len(json_files)} JSON файлов писем для даты {normalized_date}")
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        email_data = json.load(f)
                    
                    # Проверяем вложения
                    attachments = email_data.get('attachments', [])
                    for attachment in attachments:
                        status = attachment.get('status', '')
                        
                        # Обрабатываем только сохраненные файлы или уже существующие
                        if status in ['saved', 'already_exists']:
                            file_path_str = attachment.get('file_path', '')
                            if file_path_str:
                                file_path = Path(file_path_str)
                                if file_path.exists():
                                    saved_files.append(file_path)
                                    self.logger.debug(f"Добавлен файл: {file_path.name} (статус: {status})")
                                else:
                                    self.logger.warning(f"Файл указан в метаданных, но не найден: {file_path}")
                        else:
                            self.logger.debug(f"Пропущен файл со статусом '{status}': {attachment.get('original_filename', 'unknown')}")
                            
                except json.JSONDecodeError as e:
                    self.logger.error(f"Ошибка парсинга JSON файла {json_file}: {e}")
                except Exception as e:
                    self.logger.error(f"Ошибка обработки файла {json_file}: {e}")
            
            # Удаляем дубликаты и сортируем
            saved_files = sorted(list(set(saved_files)))
            self.logger.info(f"Итого найдено {len(saved_files)} уникальных сохраненных файлов")
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении файлов из метаданных: {e}")
            return []
        
        return saved_files
    
    def _get_files_fallback(self, date_dir: Path) -> List[Path]:
        """Fallback метод получения файлов (старая логика)"""
        # Нормализация формата даты в пути
        date_match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', str(date_dir))
        if date_match:
            original_date = date_match.group(1)
            normalized_date = self._normalize_date_format(original_date)
            normalized_path = str(date_dir).replace(original_date, normalized_date)
            date_dir = Path(normalized_path)
        
        # Используем более надежный способ поиска файлов, который правильно обрабатывает кириллицу
        file_types = [".png", ".jpg", ".jpeg", ".tiff", ".pdf", ".docx", ".doc", ".xlsx", ".xls"]
        files = []

        try:
            # Сначала пробуем стандартный glob
            for item in date_dir.iterdir():
                if item.is_file() and item.suffix.lower() in file_types:
                    files.append(item)
        except Exception as e:
            self.logger.warning(f"Ошибка при поиске файлов через iterdir: {e}")
            # Fallback на glob паттерны
            try:
                files = sorted(list(set(f for ext in file_types for f in date_dir.glob(f"*{ext}"))))
            except Exception as e2:
                self.logger.error(f"Ошибка при поиске файлов через glob: {e2}")
                return []

        # Исключаем системные файлы
        files = [f for f in files if not f.name.startswith('.') and f.name != '.DS_Store']

        return sorted(files)
    
    def _normalize_filename(self, filename: str) -> str:
        """🔧 Нормализация имени файла через единую функцию из file_utils"""
        return normalize_filename(filename, remove_extension=True, to_lowercase=True)
    
    def _normalize_date_format(self, date: str) -> str:
        """🗓️ Нормализация формата даты к стандартному YYYY-MM-DD"""
        if not date:
            return None
            
        # Удаляем лишние пробелы
        date = date.strip()
        
        # Если уже в правильном формате YYYY-MM-DD
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            return date
            
        # Попытка парсинга различных форматов
        date_formats = [
            '%Y-%m-%d',    # 2024-12-30
            '%Y.%m.%d',    # 2024.12.30
            '%Y/%m/%d',    # 2024/12/30
            '%d-%m-%Y',    # 30-12-2024
            '%d.%m.%Y',    # 30.12.2024
            '%d/%m/%Y',    # 30/12/2024
            '%Y%m%d',      # 20241230
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date, fmt)
                normalized = parsed_date.strftime('%Y-%m-%d')
                self.logger.info(f"Нормализация даты: {date} -> {normalized}")
                return normalized
            except ValueError:
                continue
                
        # Если не удалось распарсить, возвращаем как есть с предупреждением
        self.logger.warning(f"Не удалось нормализовать формат даты: {date}")
        return date

    def _detect_excel_format(self, file_path: Path) -> str:
        """
        Определяет реальный формат Excel файла по его сигнатуре,
        независимо от расширения файла.
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)

            # XLSX файлы - это ZIP архивы, начинающиеся с PK
            if header.startswith(b'PK\x03\x04'):
                return 'xlsx'

            # XLS файлы начинаются с OLE сигнатуры
            if header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
                return 'xls'

            return 'unknown'

        except Exception as e:
            self.logger.warning(f"Ошибка определения формата Excel файла {file_path}: {e}")
            return 'unknown'

    def _process_excel_file(self, file_path: Path, expected_format: str) -> Tuple[str, str, float]:
        """
        Универсальная обработка Excel файлов с автоматическим определением формата.
        expected_format: 'xls' или 'xlsx' - ожидаемый формат по расширению
        """
        real_format = self._detect_excel_format(file_path)

        if real_format == 'unknown':
            raise RuntimeError(f"Не удалось определить формат Excel файла {file_path}")

        print(f"   📊 Реальный формат файла: {real_format.upper()}, расширение указывает на: {expected_format.upper()}")

        # Пробуем основной метод (xlrd для XLS, openpyxl для XLSX)
        if real_format == 'xls' and XLRD_AVAILABLE:
            try:
                wb = xlrd.open_workbook(file_path, encoding_override="cp1251")
                lines = []
                for sheet in wb.sheets():
                    for row_idx in range(sheet.nrows):
                        row_data = [str(sheet.cell(row_idx, col_idx).value or "") for col_idx in range(sheet.ncols)]
                        lines.append(" | ".join(row_data))
                text = "\n".join(lines)
                text = text.strip()

                if text:
                    method = "local_xls" if expected_format == 'xls' else "local_xls_fallback"
                    return text, method, 1.0
                else:
                    raise RuntimeError("xlrd не смог извлечь текст")

            except Exception as e:
                print(f"   ⚠️ xlrd не справился: {e}")

        elif real_format == 'xlsx' and OPENPYXL_AVAILABLE:
            try:
                wb = openpyxl.load_workbook(file_path, data_only=True)
                lines = [" | ".join([str(cell.value or "") for cell in row])
                        for sheet in wb.worksheets for row in sheet.iter_rows()]
                text = "\n".join(lines)
                text = text.strip()

                if text:
                    method = "local_xlsx" if expected_format == 'xlsx' else "local_xlsx_fallback"
                    return text, method, 1.0
                else:
                    raise RuntimeError("openpyxl не смог извлечь текст")

            except Exception as e:
                print(f"   ⚠️ openpyxl не справился: {e}")

        # Пробуем pandas как универсальный метод
        if PANDAS_AVAILABLE:
            try:
                print("   🔄 Пробуем pandas как универсальный метод...")
                # Используем engine='openpyxl' для XLSX файлов
                if real_format == 'xlsx':
                    df_dict = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
                else:
                    # Для XLS файлов используем engine='xlrd'
                    df_dict = pd.read_excel(file_path, sheet_name=None, engine='xlrd')

                lines = []
                for sheet_name, df in df_dict.items():
                    lines.append(f"=== {sheet_name} ===")
                    # Преобразуем DataFrame в строки
                    for _, row in df.iterrows():
                        row_data = [str(val) if pd.notna(val) else "" for val in row]
                        lines.append(" | ".join(row_data))

                text = "\n".join(lines)
                text = text.strip()

                if text:
                    method = "local_pandas_fallback"
                    print("   ✅ Pandas успешно обработал файл")
                    return text, method, 1.0
                else:
                    raise RuntimeError("Pandas не смог извлечь текст")

            except Exception as e:
                print(f"   ⚠️ Pandas тоже не справился: {e}")

        # Пробуем альтернативный метод
        print("   🔄 Пробуем альтернативный метод...")

        if real_format == 'xls' and OPENPYXL_AVAILABLE:
            # Для XLS файла пробуем openpyxl (редкий случай)
            try:
                wb = openpyxl.load_workbook(file_path, data_only=True)
                lines = [" | ".join([str(cell.value or "") for cell in row])
                        for sheet in wb.worksheets for row in sheet.iter_rows()]
                text = "\n".join(lines)
                text = text.strip()

                if text:
                    method = "local_xlsx_fallback"
                    print("   ✅ Альтернативный метод (XLSX) сработал успешно")
                    return text, method, 1.0
                else:
                    raise RuntimeError("Альтернативный метод не смог извлечь текст")

            except Exception as e:
                print(f"   ❌ Альтернативный метод тоже не сработал: {e}")

        elif real_format == 'xlsx' and XLRD_AVAILABLE:
            # Для XLSX файла пробуем xlrd (редкий случай)
            try:
                wb = xlrd.open_workbook(file_path, encoding_override="cp1251")
                lines = []
                for sheet in wb.sheets():
                    for row_idx in range(sheet.nrows):
                        row_data = [str(sheet.cell(row_idx, col_idx).value or "") for col_idx in range(sheet.ncols)]
                        lines.append(" | ".join(row_data))
                text = "\n".join(lines)
                text = text.strip()

                if text:
                    method = "local_xls_fallback"
                    print("   ✅ Альтернативный метод (XLS) сработал успешно")
                    return text, method, 1.0
                else:
                    raise RuntimeError("Альтернативный метод не смог извлечь текст")

            except Exception as e:
                print(f"   ❌ Альтернативный метод тоже не сработал: {e}")

        # Если ничего не сработало
        raise RuntimeError(f"Все методы обработки {expected_format.upper()} файла неудачны. Реальный формат: {real_format.upper()}")

    def _analyze_pdf_structure(self, pdf_path: Path) -> dict:
        """
        Улучшенный анализ структуры PDF для точного определения качественного текстового слоя.
        Возвращает детальную информацию о структуре документа с расширенными метриками.
        Использует кэширование для оптимизации производительности.
        """
        # Проверяем кэш
        cache_key = self._get_pdf_cache_key(pdf_path)
        if cache_key in self._pdf_structure_cache:
            cached_result = self._pdf_structure_cache[cache_key]
            # Преобразуем set обратно из списка для font_types
            if 'font_types' in cached_result and isinstance(cached_result['font_types'], list):
                cached_result['font_types'] = set(cached_result['font_types'])
            self.logger.debug(f"💾 Использован кэш PDF анализа для {pdf_path.name}")
            return cached_result
        
        start_time = time.time()
        result = {
            'has_text_layer': False,
            'text_to_image_ratio': 0.0,
            'has_embedded_fonts': False,
            'text_objects_count': 0,
            'image_objects_count': 0,
            'total_objects': 0,
            'font_types': set(),
            'text_confidence': 0.0,
            'structure_score': 0.0,
            'page_count': 0,
            'text_density': 0.0,
            'font_diversity': 0.0,
            'has_vector_text': False,
            'text_quality_indicators': {}
        }

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(pdf_path))
            result['page_count'] = len(doc)
            
            total_text_chars = 0
            total_meaningful_text = 0
            total_image_area = 0
            total_page_area = 0
            vector_text_pages = 0
            font_sizes = []
            text_blocks_with_coords = []

            # Анализируем до 5 страниц для более точной оценки
            pages_to_analyze = min(len(doc), 5)
            
            for page_num in range(pages_to_analyze):
                page = doc[page_num]
                page_area = page.rect.width * page.rect.height
                total_page_area += page_area

                # Извлекаем текст с координатами и метаданными
                text_dict = page.get_text("dict")
                page_text = page.get_text()
                total_text_chars += len(page_text)
                
                # Подсчитываем осмысленный текст (исключаем мусор)
                meaningful_chars = len(re.sub(r'[^\w\s\.,;:!?()\[\]{}"\'-]', '', page_text))
                total_meaningful_text += meaningful_chars

                # Анализируем текстовые блоки
                text_blocks = text_dict.get('blocks', [])
                result['text_objects_count'] += len(text_blocks)
                
                # Проверяем наличие векторного текста
                has_vector_on_page = False
                for block in text_blocks:
                    if 'lines' in block:
                        for line in block['lines']:
                            if 'spans' in line:
                                for span in line['spans']:
                                    # Проверяем размер шрифта и флаги
                                    font_size = span.get('size', 0)
                                    if font_size > 0:
                                        font_sizes.append(font_size)
                                        has_vector_on_page = True
                                        
                                    # Собираем координаты для анализа плотности
                                    bbox = span.get('bbox')
                                    if bbox:
                                        text_blocks_with_coords.append(bbox)
                
                if has_vector_on_page:
                    vector_text_pages += 1

                # Анализируем изображения
                images = page.get_images(full=True)
                result['image_objects_count'] += len(images)

                # Вычисляем площадь изображений более точно
                for img in images:
                    try:
                        img_rect = page.get_image_rects(img[7])  # xref
                        if img_rect:
                            for rect in img_rect:
                                img_area = abs((rect[2] - rect[0]) * (rect[3] - rect[1]))
                                total_image_area += img_area
                    except:
                        # Fallback: используем размер изображения из метаданных
                        try:
                            img_width = img[2] if len(img) > 2 else 100
                            img_height = img[3] if len(img) > 3 else 100
                            total_image_area += img_width * img_height * 0.1  # Примерная оценка
                        except:
                            pass

                # Анализируем шрифты более детально
                fonts = page.get_fonts()
                for font in fonts:
                    if font and len(font) > 3:
                        font_name = font[3] if isinstance(font[3], str) else str(font[3])
                        result['font_types'].add(font_name)

            doc.close()

            # Расчет улучшенных метрик
            if total_page_area > 0:
                result['text_to_image_ratio'] = total_image_area / total_page_area
                result['text_density'] = total_meaningful_text / total_page_area * 1000000  # символов на кв.единицу

            # Определяем разнообразие шрифтов
            result['font_diversity'] = len(result['font_types'])
            
            # Проверяем наличие векторного текста
            result['has_vector_text'] = vector_text_pages > 0
            
            # Определяем embedded шрифты более точно
            system_fonts = {'Times', 'Helvetica', 'Courier', 'Symbol', 'ZapfDingbats', 
                          'Arial', 'Times-Roman', 'Times-Bold', 'Times-Italic',
                          'Helvetica-Bold', 'Helvetica-Oblique', 'Courier-Bold'}
            embedded_fonts = [f for f in result['font_types'] 
                            if not any(f.startswith(sf) for sf in system_fonts)]
            result['has_embedded_fonts'] = len(embedded_fonts) > 0

            # Общее количество объектов
            result['total_objects'] = result['text_objects_count'] + result['image_objects_count']

            # Улучшенные критерии определения текстового слоя
            has_significant_text = total_meaningful_text > 300  # Минимум 300 осмысленных символов
            has_reasonable_density = result['text_density'] > 50  # Достаточная плотность текста
            has_low_image_ratio = result['text_to_image_ratio'] < 0.4  # Менее 40% площади - изображения
            has_good_object_ratio = (result['text_objects_count'] > result['image_objects_count'] * 1.5 
                                   if result['image_objects_count'] > 0 else result['text_objects_count'] > 0)
            has_vector_text = result['has_vector_text']
            has_font_diversity = result['font_diversity'] >= 2  # Минимум 2 разных шрифта
            
            # Индикаторы качества текста
            result['text_quality_indicators'] = {
                'significant_text': has_significant_text,
                'reasonable_density': has_reasonable_density,
                'low_image_ratio': has_low_image_ratio,
                'good_object_ratio': has_good_object_ratio,
                'vector_text': has_vector_text,
                'embedded_fonts': result['has_embedded_fonts'],
                'font_diversity': has_font_diversity
            }

            # Улучшенная логика определения текстового слоя
            quality_score = sum([
                has_significant_text * 25,
                has_reasonable_density * 20,
                has_low_image_ratio * 15,
                has_good_object_ratio * 15,
                has_vector_text * 15,
                result['has_embedded_fonts'] * 10
            ])
            
            result['structure_score'] = min(100, quality_score)
            
            # Определяем наличие текстового слоя с более строгими критериями
            result['has_text_layer'] = (
                has_significant_text and 
                has_vector_text and 
                (has_reasonable_density or has_low_image_ratio or result['has_embedded_fonts'])
            )

            # Определяем уверенность с учетом новых метрик
            if result['has_text_layer'] and result['structure_score'] >= 80:
                result['text_confidence'] = 0.95
            elif result['has_text_layer'] and result['structure_score'] >= 65:
                result['text_confidence'] = 0.8
            elif result['has_text_layer'] and result['structure_score'] >= 50:
                result['text_confidence'] = 0.6
            elif has_significant_text and has_vector_text:
                result['text_confidence'] = 0.4
            else:
                result['text_confidence'] = 0.1

            self.logger.debug(f"📊 Анализ PDF {pdf_path.name}: score={result['structure_score']:.1f}, "
                            f"confidence={result['text_confidence']:.2f}, density={result['text_density']:.1f}")

        except Exception as e:
            result['error'] = str(e)
            result['has_text_layer'] = False
            result['text_confidence'] = 0.0
            self.logger.error(f"Ошибка анализа PDF структуры {pdf_path.name}: {e}")

        # Сохраняем результат в кэш
        cache_key = self._get_pdf_cache_key(pdf_path)
        self.pdf_structure_cache[cache_key] = result
        self._save_pdf_structure_cache()
        
        return result

    def _analyze_pdf_with_fallback(self, pdf_path: Path) -> dict:
        """
        Fallback механизм для спорных случаев определения текстового слоя PDF.
        Применяет дополнительные проверки и альтернативные стратегии анализа.
        """
        # Получаем базовый анализ
        base_analysis = self._analyze_pdf_structure(pdf_path)
        
        # Если уверенность высокая, возвращаем базовый результат
        if base_analysis['text_confidence'] >= 0.8:
            return base_analysis
            
        # Для спорных случаев применяем дополнительные проверки
        fallback_result = base_analysis.copy()
        fallback_result['fallback_applied'] = True
        fallback_result['fallback_checks'] = {}
        
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            
            # Дополнительная проверка 1: Анализ первых строк текста
            first_page_text = doc[0].get_text() if len(doc) > 0 else ""
            text_lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
            meaningful_lines = [line for line in text_lines if len(line) > 10 and not re.match(r'^[\d\s\.,;:!?()-]+$', line)]
            
            fallback_result['fallback_checks']['meaningful_lines_count'] = len(meaningful_lines)
            fallback_result['fallback_checks']['has_meaningful_content'] = len(meaningful_lines) >= 3
            
            # Дополнительная проверка 2: Анализ метаданных документа
            metadata = doc.metadata
            has_creation_software = any(key in metadata for key in ['creator', 'producer', 'title'])
            fallback_result['fallback_checks']['has_metadata'] = has_creation_software
            
            # Дополнительная проверка 3: Проверка наличия закладок/оглавления
            toc = doc.get_toc()
            fallback_result['fallback_checks']['has_toc'] = len(toc) > 0
            
            # Дополнительная проверка 4: Анализ структуры страниц
            consistent_structure = True
            if len(doc) > 1:
                first_page_objects = len(doc[0].get_text("dict").get('blocks', []))
                for page_num in range(1, min(len(doc), 4)):
                    page_objects = len(doc[page_num].get_text("dict").get('blocks', []))
                    if abs(page_objects - first_page_objects) > first_page_objects * 0.5:
                        consistent_structure = False
                        break
            
            fallback_result['fallback_checks']['consistent_structure'] = consistent_structure
            
            # Дополнительная проверка 5: Тест извлечения текста с разными методами
            text_methods_results = {}
            try:
                # Метод 1: Стандартное извлечение
                standard_text = doc[0].get_text()
                text_methods_results['standard'] = len(standard_text.strip())
                
                # Метод 2: Извлечение с сохранением разметки
                html_text = doc[0].get_text("html")
                text_methods_results['html'] = len(re.sub(r'<[^>]+>', '', html_text).strip())
                
                # Метод 3: Извлечение блоков
                blocks_text = ""
                for block in doc[0].get_text("dict").get('blocks', []):
                    if 'lines' in block:
                        for line in block['lines']:
                            for span in line.get('spans', []):
                                blocks_text += span.get('text', '') + " "
                text_methods_results['blocks'] = len(blocks_text.strip())
                
            except Exception as e:
                self.logger.debug(f"Ошибка при тестировании методов извлечения: {e}")
            
            fallback_result['fallback_checks']['text_methods'] = text_methods_results
            
            # Дополнительная проверка 6: Анализ соотношения символов
            if first_page_text:
                total_chars = len(first_page_text)
                alpha_chars = len(re.sub(r'[^a-zA-Zа-яА-Я]', '', first_page_text))
                digit_chars = len(re.sub(r'[^0-9]', '', first_page_text))
                space_chars = len(re.sub(r'[^ ]', '', first_page_text))
                
                fallback_result['fallback_checks']['char_analysis'] = {
                    'alpha_ratio': alpha_chars / total_chars if total_chars > 0 else 0,
                    'digit_ratio': digit_chars / total_chars if total_chars > 0 else 0,
                    'space_ratio': space_chars / total_chars if total_chars > 0 else 0
                }
            
            doc.close()
            
            # Пересчитываем уверенность на основе fallback проверок
            fallback_score = 0
            checks = fallback_result['fallback_checks']
            
            # Бонусы за положительные индикаторы
            if checks.get('has_meaningful_content', False):
                fallback_score += 30
            if checks.get('has_metadata', False):
                fallback_score += 15
            if checks.get('has_toc', False):
                fallback_score += 10
            if checks.get('consistent_structure', False):
                fallback_score += 15
            
            # Анализ методов извлечения текста
            text_methods = checks.get('text_methods', {})
            if text_methods:
                max_text_length = max(text_methods.values()) if text_methods.values() else 0
                if max_text_length > 500:
                    fallback_score += 20
                elif max_text_length > 100:
                    fallback_score += 10
            
            # Анализ символов
            char_analysis = checks.get('char_analysis', {})
            if char_analysis:
                alpha_ratio = char_analysis.get('alpha_ratio', 0)
                if alpha_ratio > 0.3:  # Более 30% букв
                    fallback_score += 15
                elif alpha_ratio > 0.15:  # Более 15% букв
                    fallback_score += 8
            
            # Обновляем результат на основе fallback анализа
            original_confidence = base_analysis['text_confidence']
            fallback_confidence = min(0.95, fallback_score / 100)
            
            # Используем максимальную уверенность из двух методов
            final_confidence = max(original_confidence, fallback_confidence)
            fallback_result['text_confidence'] = final_confidence
            
            # Обновляем решение о наличии текстового слоя
            if final_confidence >= 0.6 and fallback_score >= 50:
                fallback_result['has_text_layer'] = True
            elif final_confidence >= 0.4 and fallback_score >= 70:
                fallback_result['has_text_layer'] = True
            
            fallback_result['fallback_score'] = fallback_score
            fallback_result['original_confidence'] = original_confidence
            
            self.logger.debug(f"🔄 Fallback анализ {pdf_path.name}: "
                            f"original={original_confidence:.2f}, "
                            f"fallback={fallback_confidence:.2f}, "
                            f"final={final_confidence:.2f}, "
                            f"score={fallback_score}")
            
        except Exception as e:
            self.logger.error(f"Ошибка fallback анализа {pdf_path.name}: {e}")
            fallback_result['fallback_error'] = str(e)
        
        return fallback_result

    def _choose_pdf_processing_strategy(self, pdf_path: Path) -> str:
        """
        Улучшенный выбор оптимальной стратегии обработки PDF с учетом расширенных метрик.
        Возвращает: 'text_extraction', 'ocr_only', 'hybrid'
        """
        try:
            # Получаем анализ структуры PDF
            structure = self._analyze_pdf_structure(pdf_path)
            
            # Если есть ошибка в анализе - используем OCR
            if 'error' in structure:
                self.logger.warning(f"Ошибка анализа структуры {pdf_path.name}: {structure['error']}")
                return 'ocr_only'
            
            # Извлекаем метрики для принятия решения
            has_text_layer = structure.get('has_text_layer', False)
            text_confidence = structure.get('text_confidence', 0.0)
            structure_score = structure.get('structure_score', 0.0)
            text_to_image_ratio = structure.get('text_to_image_ratio', 0.0)
            text_density = structure.get('text_density', 0.0)
            has_vector_text = structure.get('has_vector_text', False)
            quality_indicators = structure.get('text_quality_indicators', {})
            
            # Проверяем спорные случаи и применяем fallback анализ
            is_borderline = (
                (0.3 <= text_confidence <= 0.6) or  # Средняя уверенность
                (40 <= structure_score <= 70) or    # Средний балл структуры
                (0.2 <= text_to_image_ratio <= 0.6) # Смешанный контент
            )
            
            if is_borderline:
                self.logger.info(f"🔍 Спорный случай для {pdf_path.name}, применяю fallback анализ")
                fallback_result = self._analyze_pdf_with_fallback(pdf_path, structure)
                if fallback_result:
                    # Обновляем метрики на основе fallback анализа
                    text_confidence = fallback_result.get('adjusted_confidence', text_confidence)
                    structure_score = fallback_result.get('adjusted_score', structure_score)
                    has_text_layer = fallback_result.get('has_reliable_text', has_text_layer)
                    self.logger.info(f"📊 Fallback результат: conf={text_confidence:.2f}, score={structure_score:.1f}")
            
            # Улучшенная логика выбора стратегии
            if (has_text_layer and text_confidence >= 0.8 and structure_score >= 75 and 
                has_vector_text and quality_indicators.get('reasonable_density', False)):
                # Отличное качество текстового слоя - чистое извлечение
                strategy = 'text_extraction'
                reason = f"Отличное качество (conf: {text_confidence:.2f}, score: {structure_score:.1f}, density: {text_density:.1f})"
                
            elif (has_text_layer and text_confidence >= 0.6 and structure_score >= 60 and 
                  has_vector_text and text_to_image_ratio < 0.5):
                # Хорошее качество с небольшим количеством изображений - извлечение с проверкой
                strategy = 'text_extraction'
                reason = f"Хорошее качество текста (conf: {text_confidence:.2f}, img_ratio: {text_to_image_ratio:.2f})"
                
            elif (has_text_layer and text_confidence >= 0.4 and 
                  (text_to_image_ratio > 0.3 or not quality_indicators.get('reasonable_density', True))):
                # Смешанный контент или низкая плотность - гибридный подход
                strategy = 'hybrid'
                reason = f"Смешанный контент (conf: {text_confidence:.2f}, img_ratio: {text_to_image_ratio:.2f})"
                
            elif (has_text_layer and text_confidence >= 0.4 and has_vector_text and 
                  structure_score >= 40):
                # Приемлемое качество векторного текста - гибридный подход
                strategy = 'hybrid'
                reason = f"Приемлемый векторный текст (conf: {text_confidence:.2f}, score: {structure_score:.1f})"
                
            elif not has_text_layer or not has_vector_text or text_confidence < 0.3:
                # Нет качественного текстового слоя - только OCR
                strategy = 'ocr_only'
                reason = f"Отсутствие качественного текста (conf: {text_confidence:.2f}, vector: {has_vector_text})"
                
            else:
                # Пограничные случаи - гибридный подход для безопасности
                strategy = 'hybrid'
                reason = f"Пограничное качество (conf: {text_confidence:.2f}, score: {structure_score:.1f})"
            
            self.logger.info(f"📋 Стратегия для {pdf_path.name}: {strategy} - {reason}")
            return strategy
            
        except Exception as e:
            self.logger.error(f"Ошибка выбора стратегии для {pdf_path.name}: {e}")
            return 'ocr_only'  # Безопасный fallback

    def _evaluate_pdf_before_processing(self, pdf_path: Path) -> dict:
        """
        Предварительная оценка PDF для оптимизации процесса обработки.
        Возвращает детальную информацию для принятия решений.
        """
        evaluation = {
            'file_size_mb': 0.0,
            'page_count': 0,
            'estimated_processing_time': 0.0,
            'recommended_strategy': 'ocr_only',
            'complexity_score': 0.0,
            'memory_requirements_mb': 0.0,
            'should_use_batching': False,
            'optimal_batch_size': 1,
            'risk_factors': [],
            'optimization_hints': []
        }
        
        try:
            # Базовая информация о файле
            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            evaluation['file_size_mb'] = file_size_mb
            
            # Анализ структуры PDF
            structure = self._analyze_pdf_structure(pdf_path)
            page_count = structure.get('page_count', 0)
            evaluation['page_count'] = page_count
            
            # Выбор стратегии обработки
            strategy = self._choose_pdf_processing_strategy(pdf_path)
            evaluation['recommended_strategy'] = strategy
            
            # Расчет сложности документа
            complexity_score = self._calculate_document_complexity(structure, file_size_mb)
            evaluation['complexity_score'] = complexity_score
            
            # Оценка времени обработки
            estimated_time = self._estimate_processing_time(strategy, page_count, file_size_mb, complexity_score)
            evaluation['estimated_processing_time'] = estimated_time
            
            # Требования к памяти
            memory_req = self._estimate_memory_requirements(file_size_mb, page_count, strategy)
            evaluation['memory_requirements_mb'] = memory_req
            
            # Определение необходимости батчинга
            should_batch, batch_size = self._should_use_batching(page_count, file_size_mb, memory_req)
            evaluation['should_use_batching'] = should_batch
            evaluation['optimal_batch_size'] = batch_size
            
            # Анализ рисков и оптимизаций
            evaluation['risk_factors'] = self._identify_risk_factors(structure, file_size_mb, page_count)
            evaluation['optimization_hints'] = self._generate_optimization_hints(structure, strategy, file_size_mb)
            
            self.logger.info(f"Оценка PDF {pdf_path.name}: {strategy}, {page_count} стр., {file_size_mb:.1f}MB, сложность: {complexity_score:.1f}")
            
        except Exception as e:
            self.logger.error(f"Ошибка оценки PDF {pdf_path.name}: {e}")
            evaluation['risk_factors'].append(f"Ошибка анализа: {str(e)}")
            
        return evaluation
    
    def _calculate_document_complexity(self, structure: dict, file_size_mb: float) -> float:
        """Расчет сложности документа для оценки времени обработки."""
        complexity = 0.0
        
        # Базовая сложность от размера
        complexity += min(file_size_mb * 0.1, 2.0)
        
        # Сложность от структуры
        if structure.get('text_to_image_ratio', 0) < 0.1:
            complexity += 3.0  # Много изображений
        elif structure.get('text_to_image_ratio', 0) > 0.8:
            complexity += 0.5  # Преимущественно текст
        else:
            complexity += 1.5  # Смешанный контент
            
        # Сложность от качества текстового слоя
        text_confidence = structure.get('text_confidence', 0.0)
        if text_confidence < 0.3:
            complexity += 2.0
        elif text_confidence < 0.7:
            complexity += 1.0
            
        return min(complexity, 10.0)
    
    def _estimate_processing_time(self, strategy: str, page_count: int, file_size_mb: float, complexity: float) -> float:
        """Оценка времени обработки в секундах."""
        base_time_per_page = {
            'text_extraction': 0.1,
            'ocr_only': 2.0,
            'hybrid': 1.2
        }
        
        base_time = base_time_per_page.get(strategy, 2.0) * page_count
        complexity_multiplier = 1.0 + (complexity / 10.0)
        size_factor = 1.0 + (file_size_mb / 50.0)  # Дополнительное время для больших файлов
        
        return base_time * complexity_multiplier * size_factor
    
    def _estimate_memory_requirements(self, file_size_mb: float, page_count: int, strategy: str) -> float:
        """Оценка требований к памяти в MB."""
        base_memory = file_size_mb * 2  # Базовое требование
        
        if strategy == 'ocr_only':
            # OCR требует больше памяти для обработки изображений
            base_memory += page_count * 5  # ~5MB на страницу для OCR
        elif strategy == 'hybrid':
            base_memory += page_count * 3  # Промежуточное значение
        else:
            base_memory += page_count * 0.5  # Минимум для текстового извлечения
            
        return base_memory
    
    def _should_use_batching(self, page_count: int, file_size_mb: float, memory_req_mb: float) -> tuple:
        """Определяет необходимость батчинга и оптимальный размер батча."""
        # Критерии для батчинга
        should_batch = (
            page_count > 50 or  # Много страниц
            file_size_mb > 100 or  # Большой файл
            memory_req_mb > 500  # Высокие требования к памяти
        )
        
        if not should_batch:
            return False, None
            
        # Расчет оптимального размера батча
        base_batch_size = 10
        
        # Корректировка на основе размера файла
        if file_size_mb > 500:
            base_batch_size = 5
        elif file_size_mb > 200:
            base_batch_size = 8
        elif file_size_mb < 50:
            base_batch_size = 15
            
        # Корректировка на основе требований к памяти
        if memory_req_mb > 1000:
            base_batch_size = max(3, base_batch_size - 3)
        elif memory_req_mb > 750:
            base_batch_size = max(5, base_batch_size - 2)
            
        # Корректировка на основе количества страниц
        if page_count > 200:
            base_batch_size = max(5, base_batch_size - 2)
        elif page_count > 100:
            base_batch_size = max(8, base_batch_size - 1)
            
        # Ограничиваем размер батча разумными пределами
        optimal_batch_size = max(3, min(20, base_batch_size))
        
        return True, optimal_batch_size

    def _detect_document_type(self, text: str, pdf_path: Path = None) -> str:
        """
        Определяет тип документа для применения адаптивных критериев качества.
        """
        text_lower = text.lower()
        
        # Проверяем на финансовые документы
        financial_keywords = ['счет', 'invoice', 'payment', 'сумма', 'amount', 'руб', 'rub', '$', '€', 'налог', 'tax']
        if any(keyword in text_lower for keyword in financial_keywords):
            return 'financial'
            
        # Проверяем на технические документы
        technical_keywords = ['спецификация', 'specification', 'техническ', 'technical', 'параметр', 'parameter']
        if any(keyword in text_lower for keyword in technical_keywords):
            return 'technical'
            
        # Проверяем на контракты и юридические документы
        legal_keywords = ['договор', 'contract', 'соглашение', 'agreement', 'статья', 'пункт', 'clause']
        if any(keyword in text_lower for keyword in legal_keywords):
            return 'legal'
            
        # Проверяем на отчеты
        report_keywords = ['отчет', 'report', 'анализ', 'analysis', 'результат', 'result', 'данные', 'data']
        if any(keyword in text_lower for keyword in report_keywords):
            return 'report'
            
        # Проверяем структуру текста для определения типа
        if self._has_table_structure(text):
            return 'tabular'
            
        # По умолчанию - обычный документ
        return 'general'
        
    def _get_confidence_threshold(self, document_type: str, structure_analysis: dict) -> float:
        """
        Возвращает адаптивный порог уверенности для разных типов документов.
        """
        base_thresholds = {
            'financial': 0.6,    # Финансовые документы - более строгие требования
            'legal': 0.65,       # Юридические документы - высокие требования
            'technical': 0.55,   # Технические документы - средние требования
            'report': 0.5,       # Отчеты - более мягкие требования
            'tabular': 0.45,     # Табличные данные - мягкие требования
            'general': 0.7       # Обычные документы - стандартные требования
        }
        
        threshold = base_thresholds.get(document_type, 0.7)
        
        # Корректируем порог на основе структурного анализа
        if structure_analysis.get('structure_score', 0) > 80:
            threshold -= 0.1  # Снижаем требования для хорошо структурированных документов
        elif structure_analysis.get('structure_score', 0) < 30:
            threshold += 0.1  # Повышаем требования для плохо структурированных документов
            
        return max(0.2, min(0.9, threshold))  # Ограничиваем диапазон
        
    def _get_garbage_threshold(self, document_type: str) -> float:
        """
        Возвращает адаптивный порог мусора для разных типов документов.
        """
        thresholds = {
            'financial': 0.03,   # Очень низкий порог для финансовых документов
            'legal': 0.04,       # Низкий порог для юридических документов
            'technical': 0.06,   # Средний порог для технических документов
            'report': 0.08,      # Более высокий порог для отчетов
            'tabular': 0.1,      # Высокий порог для табличных данных
            'general': 0.05      # Стандартный порог
        }
        
        return thresholds.get(document_type, 0.05)
        
    def _has_table_structure(self, text: str) -> bool:
        """
        Проверяет наличие табличной структуры в тексте.
        """
        lines = text.split('\n')
        table_indicators = 0
        
        for line in lines:
            # Проверяем на разделители таблиц
            if '|' in line or '\t' in line:
                table_indicators += 1
            # Проверяем на выравнивание (много пробелов)
            elif '   ' in line:  # 3+ пробелов подряд
                table_indicators += 1
                
        return table_indicators > len(lines) * 0.3  # Более 30% строк имеют табличные признаки
        
    def _analyze_document_quality_adaptive(self, text: str, document_type: str) -> bool:
        """
        Адаптивный анализ качества документа в зависимости от его типа.
        """
        # Разделяем текст на страницы для анализа
        pages = text.split('\n\n')
        if len(pages) == 0:
            return False

        # Получаем адаптивные критерии для типа документа
        quality_criteria = self._get_quality_criteria(document_type)
        
        good_pages = 0
        total_meaningful_text = 0
        total_pages_analyzed = 0

        for page_text in pages:
            if len(page_text.strip()) < quality_criteria['min_page_length']:
                continue
                
            total_pages_analyzed += 1
            page_analysis = self._analyze_page_quality_adaptive(page_text, document_type)
            
            if page_analysis['is_good']:
                good_pages += 1
                total_meaningful_text += page_analysis['meaningful_chars']

        # Адаптивные критерии успеха
        if total_pages_analyzed == 0:
            return False
            
        good_page_ratio = good_pages / total_pages_analyzed
        
        # Проверяем соответствие критериям для данного типа документа
        return (
            good_page_ratio >= quality_criteria['min_good_page_ratio'] or
            total_meaningful_text >= quality_criteria['min_meaningful_chars']
        )
        
    def _get_quality_criteria(self, document_type: str) -> dict:
        """
        Возвращает критерии качества для разных типов документов.
        """
        criteria = {
            'financial': {
                'min_page_length': 30,
                'min_good_page_ratio': 0.8,
                'min_meaningful_chars': 300,
                'min_text_confidence': 0.6,
                'max_garbage_ratio': 0.03
            },
            'legal': {
                'min_page_length': 50,
                'min_good_page_ratio': 0.7,
                'min_meaningful_chars': 500,
                'min_text_confidence': 0.65,
                'max_garbage_ratio': 0.04
            },
            'technical': {
                'min_page_length': 40,
                'min_good_page_ratio': 0.6,
                'min_meaningful_chars': 400,
                'min_text_confidence': 0.55,
                'max_garbage_ratio': 0.06
            },
            'report': {
                'min_page_length': 25,
                'min_good_page_ratio': 0.5,
                'min_meaningful_chars': 300,
                'min_text_confidence': 0.5,
                'max_garbage_ratio': 0.08
            },
            'tabular': {
                'min_page_length': 15,
                'min_good_page_ratio': 0.4,
                'min_meaningful_chars': 200,
                'min_text_confidence': 0.45,
                'max_garbage_ratio': 0.1
            },
            'general': {
                'min_page_length': 20,
                'min_good_page_ratio': 0.6,
                'min_meaningful_chars': 500,
                'min_text_confidence': 0.7,
                'max_garbage_ratio': 0.05
            }
        }
        
        
    def _should_use_batching(self, page_count: int, file_size_mb: float, memory_req_mb: float) -> tuple:
        """
        Определяет необходимость батчевой обработки и оптимальный размер батча.
        """
        # Если файл небольшой, батчинг не нужен
        if page_count <= 50 and file_size_mb <= 50:
            return False, page_count
            
        # Расчет оптимального размера батча
        if memory_req_mb > 1000:
            batch_size = max(5, page_count // 20)
        elif memory_req_mb > 500:
            batch_size = max(10, page_count // 10)
        else:
            batch_size = max(20, page_count // 5)
            
        return True, min(batch_size, page_count)
    
    def _identify_risk_factors(self, structure: dict, file_size_mb: float, page_count: int) -> list:
        """Расширенный анализ рисков с учетом улучшенных метрик."""
        risks = []
        
        # Риски размера файла
        if file_size_mb > 500:
            risks.append(f"⚠️ Критически большой файл ({file_size_mb:.1f}MB) - высокий риск нехватки памяти")
        elif file_size_mb > 200:
            risks.append(f"⚠️ Очень большой файл ({file_size_mb:.1f}MB) - возможны проблемы с памятью")
        elif file_size_mb > 100:
            risks.append(f"⚠️ Большой файл ({file_size_mb:.1f}MB) - увеличенное время обработки")
            
        # Риски количества страниц
        if page_count > 500:
            risks.append(f"⚠️ Критически много страниц ({page_count}) - очень длительная обработка")
        elif page_count > 200:
            risks.append(f"⚠️ Очень много страниц ({page_count}) - длительное время обработки")
        elif page_count > 100:
            risks.append(f"⚠️ Много страниц ({page_count}) - увеличенное время обработки")
            
        # Риски качества текста
        text_confidence = structure.get('text_confidence', 0)
        has_vector_text = structure.get('has_vector_text', False)
        
        if not has_vector_text and text_confidence < 0.1:
            risks.append(f"⚠️ Отсутствие векторного текста (conf: {text_confidence:.2f}) - только OCR")
        elif text_confidence < 0.2:
            risks.append(f"⚠️ Очень низкое качество текста (conf: {text_confidence:.2f}) - сложный OCR")
        elif text_confidence < 0.4:
            risks.append(f"⚠️ Низкое качество текста (conf: {text_confidence:.2f}) - требуется гибридный подход")
            
        # Риски соотношения контента
        text_to_image_ratio = structure.get('text_to_image_ratio', 0)
        if text_to_image_ratio > 0.9:
            risks.append(f"⚠️ Преимущественно изображения ({text_to_image_ratio:.2f}) - высокая нагрузка на OCR")
        elif text_to_image_ratio > 0.7:
            risks.append(f"⚠️ Много изображений ({text_to_image_ratio:.2f}) - увеличенная нагрузка на OCR")
            
        # Риски плотности текста
        text_density = structure.get('text_density', 0)
        if text_density < 0.05 and page_count > 20:
            risks.append(f"⚠️ Очень низкая плотность текста ({text_density:.2f}) - возможен мусорный контент")
            
        # Риски качественных индикаторов
        quality_indicators = structure.get('text_quality_indicators', {})
        if not quality_indicators.get('reasonable_density', True):
            risks.append("⚠️ Нерациональная плотность текста - возможны проблемы с извлечением")
        if not quality_indicators.get('meaningful_content', True):
            risks.append("⚠️ Отсутствие осмысленного контента - низкое качество результата")
            
        # Системные ошибки
        if 'error' in structure:
            risks.append(f"❌ Ошибка анализа структуры: {structure['error']}")
            
        return risks
    
    def _generate_optimization_hints(self, structure: dict, strategy: str, file_size_mb: float) -> list:
        """Расширенные рекомендации по оптимизации с учетом улучшенных метрик."""
        hints = []
        
        # Извлекаем метрики
        page_count = structure.get('page_count', 0)
        text_confidence = structure.get('text_confidence', 0)
        text_density = structure.get('text_density', 0)
        text_to_image_ratio = structure.get('text_to_image_ratio', 0)
        has_vector_text = structure.get('has_vector_text', False)
        quality_indicators = structure.get('text_quality_indicators', {})
        
        # Оптимизации по стратегии
        if strategy == 'text_extraction':
            hints.append("✅ Оптимальная стратегия - быстрое извлечение векторного текста")
            if text_confidence > 0.9:
                hints.append("💡 Отличное качество текста - минимальная постобработка")
        elif strategy == 'hybrid':
            hints.append("⚡ Гибридный подход - комбинирование извлечения и OCR")
            hints.append("💡 Приоритет извлечению текста, OCR для изображений")
        else:  # ocr_only
            hints.append("🔍 Полный OCR - максимальное качество распознавания")
            
        # Оптимизации по размеру файла
        if file_size_mb > 100 and strategy in ['hybrid', 'ocr_only']:
            hints.append("🗜️ Рекомендуется предварительное сжатие изображений")
            hints.append("💾 Использование батчинга для экономии памяти")
        elif file_size_mb > 50 and strategy == 'ocr_only':
            hints.append("🗜️ Сжатие изображений ускорит OCR")
            
        # Оптимизации по количеству страниц
        if page_count > 50:
            hints.append("🚀 Параллельная обработка страниц значительно ускорит процесс")
        elif page_count > 20:
            hints.append("⚡ Рекомендуется многопоточная обработка")
            
        # Оптимизации по качеству текста
        if has_vector_text and text_confidence > 0.8:
            hints.append("✨ Отличный векторный текст - минимальная обработка")
        elif has_vector_text and text_confidence > 0.6:
            hints.append("👍 Хороший векторный текст - быстрое извлечение")
        elif not has_vector_text:
            hints.append("🔍 Отсутствие векторного текста - полагаемся на OCR")
            
        # Оптимизации по соотношению контента
        if text_to_image_ratio < 0.1:
            hints.append("📸 Преимущественно текст - OCR может не понадобиться")
        elif text_to_image_ratio > 0.8:
            hints.append("🖼️ Много изображений - оптимизация OCR критична")
            hints.append("🎯 Адаптивное DPI для разных типов изображений")
        else:
            hints.append("📊 Смешанный контент - гибридный подход оптимален")
            
        # Оптимизации по плотности текста
        if text_density > 0.5:
            hints.append("📝 Высокая плотность текста - эффективное извлечение")
        elif text_density < 0.1:
            hints.append("🧹 Низкая плотность - дополнительная фильтрация текста")
            
        # Оптимизации по качественным индикаторам
        if quality_indicators.get('reasonable_density', True):
            hints.append("✅ Рациональная плотность текста - стандартная обработка")
        else:
            hints.append("🔧 Нерациональная плотность - усиленная постобработка")
            
        if quality_indicators.get('meaningful_content', True):
            hints.append("📖 Осмысленный контент - высокое качество результата")
        else:
            hints.append("⚠️ Возможен мусорный контент - дополнительная валидация")
            
        # Общие оптимизации
        if file_size_mb > 20 or page_count > 30:
            hints.append("⏱️ Рекомендуется мониторинг прогресса обработки")
            
        return hints

    # Кэш скомпилированных регулярных выражений для оптимизации
    _GARBAGE_PATTERNS_CACHE = None
    _WORD_PATTERNS_CACHE = None
    
    def _get_compiled_patterns(self):
        """Получить скомпилированные регулярные выражения с кэшированием."""
        if self._GARBAGE_PATTERNS_CACHE is None:
            self._GARBAGE_PATTERNS_CACHE = {
                'ocr_garbage': re.compile(r'[a-z]{2,}[0-9]{2,}[a-z]*'),
                'letter_substitution': re.compile(r'[a-z]{3,}[A-Z]{1,}[a-z]*'),
                'symbol_mess': re.compile(r'[<>(){}[\]]{2,}'),
                'repeated_chars': re.compile(r'(.)\1{3,}'),
                'mixed_encoding': re.compile(r'[\u0080-\u00FF]{3,}'),
            }
        
        if self._WORD_PATTERNS_CACHE is None:
            self._WORD_PATTERNS_CACHE = {
                'russian_words': re.compile(r'[а-яё]{4,}'),
                'english_words': re.compile(r'[a-z]{4,}'),
                'fake_english': re.compile(r'[a-z]*[o]{2,}[a-z]*'),
            }
        
        return self._GARBAGE_PATTERNS_CACHE, self._WORD_PATTERNS_CACHE

    def _quick_garbage_check(self, text: str) -> dict:
        """
        Оптимизированная быстрая проверка текста на наличие мусорных паттернов.
        Использует кэшированные скомпилированные регулярные выражения.
        Возвращает {'is_good': bool, 'reason': str}
        """
        # Получаем скомпилированные паттерны из кэша
        garbage_patterns, word_patterns = self._get_compiled_patterns()
        
        # Предварительная обработка текста для оптимизации
        text_lower = text.lower()
        text_len = len(text)
        
        # Быстрая проверка на очень короткий текст
        if text_len < 20:
            return {'is_good': False, 'reason': 'text_too_short'}
        
        # Анализ паттернов мусора с оптимизированным поиском
        garbage_score = 0
        pattern_details = {}
        
        for pattern_name, compiled_pattern in garbage_patterns.items():
            matches = compiled_pattern.findall(text)
            count = len(matches)
            garbage_score += count
            pattern_details[pattern_name] = count

        # Поиск реальных слов с использованием скомпилированных паттернов
        russian_words = word_patterns['russian_words'].findall(text_lower)
        english_words = word_patterns['english_words'].findall(text_lower)

        # Оптимизированная проверка на искаженные английские слова
        fake_english_score = 0
        if english_words:
            # Ограничиваем проверку первыми 15 словами для производительности
            words_to_check = english_words[:15]
            fake_pattern = word_patterns['fake_english']
            
            for word in words_to_check:
                if fake_pattern.search(word):
                    fake_english_score += 1
                if re.search(r'[a-z]*[e]{3,}[a-z]*', word):  # 'е' заменяется на 'e'
                    fake_english_score += 1
                if re.search(r'[a-z]*[a]{3,}[a-z]*', word):  # 'а' заменяется на 'a'
                    fake_english_score += 1

        # Расчет процента фейковых английских слов
        fake_ratio = fake_english_score / max(len(english_words), 1)

        # Адаптивные критерии мусора в зависимости от типа документа
        total_words = len(russian_words) + len(english_words)
        text_length = len(text)

        # Для длинных технических документов (более 10000 символов) более мягкие критерии
        if text_length > 10000:
            garbage_threshold = 20  # Увеличиваем порог для длинных документов
        elif text_length > 5000:
            garbage_threshold = 10
        else:
            garbage_threshold = 5   # Оригинальный порог для коротких документов

        # Для документов с большим количеством слов более мягкие критерии
        if total_words > 1000:
            garbage_threshold *= 2
        elif total_words > 500:
            garbage_threshold *= 1.5

        # Учитываем соотношение мусора к общему количеству слов
        garbage_to_words_ratio = garbage_score / max(total_words, 1)

        # Критерии мусора с адаптивными порогами
        is_good = (
            garbage_score < garbage_threshold and  # Адаптивный порог мусора
            garbage_to_words_ratio < 0.05 and  # Менее 5% мусора от общего количества слов
            len(russian_words) > 2 and  # Есть русские слова
            fake_ratio < 0.7  # Менее 70% английских слов являются фейковыми
        )

        return {
            'is_good': is_good,
            'reason': f"garbage_score={garbage_score}/{garbage_threshold}, ratio={garbage_to_words_ratio:.3f}, russian_words={len(russian_words)}, fake_english_ratio={fake_ratio:.2f}",
            'details': {
                'pattern_details': pattern_details,
                'total_words': total_words,
                'text_length': text_len,
                'garbage_threshold': garbage_threshold
            }
        }

    def _is_text_quality_good(self, text: str, pdf_path: Path = None) -> bool:
        """
        Улучшенная оценка качества извлеченного текста из PDF.
        Использует адаптивные критерии для разных типов документов.
        """
        if not text or len(text) < 50:
            return False

        # Определяем тип документа для адаптивных критериев
        document_type = self._detect_document_type(text, pdf_path)
        
        # Если передан путь к PDF, сначала анализируем его структуру
        if pdf_path and pdf_path.exists():
            try:
                structure_analysis = self._analyze_pdf_structure(pdf_path)

                # Адаптивные пороги в зависимости от типа документа
                confidence_threshold = self._get_confidence_threshold(document_type, structure_analysis)
                
                # Если структура показывает наличие качественного текстового слоя
                if structure_analysis['has_text_layer'] and structure_analysis['text_confidence'] > confidence_threshold:
                    # Дополнительная проверка текста на мусор с адаптивными критериями
                    garbage_check = self._quick_garbage_check(text)

                    # Специальная логика для документов с отличной структурой PDF
                    if (structure_analysis['structure_score'] >= 90 and
                        'ratio=' in garbage_check['reason']):
                        # Извлекаем ratio из reason
                        try:
                            ratio_str = garbage_check['reason'].split('ratio=')[1].split(',')[0]
                            garbage_ratio = float(ratio_str)
                            # Адаптивный порог мусора в зависимости от типа документа
                            garbage_threshold = self._get_garbage_threshold(document_type)
                            if garbage_ratio < garbage_threshold:
                                return True
                        except (ValueError, IndexError):
                            pass

                    return garbage_check['is_good']
                elif structure_analysis['text_confidence'] < 0.2:  # Снижен порог для отклонения
                    return False
            except Exception as e:
                # Если анализ структуры не удался, продолжаем с текстовым анализом
                pass

        # Быстрая проверка на мусор перед основной обработкой
        garbage_check = self._quick_garbage_check(text)
        if not garbage_check['is_good']:
            return False

        # Адаптивный анализ страниц в зависимости от типа документа
        return self._analyze_document_quality_adaptive(text, document_type)

    def _analyze_page_quality(self, page_text: str) -> dict:
        """
        Улучшенная анализ качества текста на отдельной странице PDF.
        Проверяет язык, читаемость и исключает технический мусор.
        """
        result = {
            'is_good': False,
            'meaningful_chars': 0,
            'has_structure': False,
            'language_score': 0
        }

        # Очищаем текст от лишних пробелов
        clean_text = page_text.replace('\n', ' ').replace('\t', ' ')
        clean_text = ' '.join(clean_text.split())  # Убираем множественные пробелы

        if len(clean_text) < 50:  # Увеличиваем минимальную длину
            return result

        # Подсчет различных типов символов
        total_chars = len(clean_text.replace(' ', ''))
        if total_chars == 0:
            return result

        # Расширенная проверка на мусор - исключаем файлы с техническими кодами
        # Проверяем на наличие паттернов, характерных для искаженного текста
        garbage_patterns = [
            r'[a-z]{2,}[0-9]{2,}[a-z]*',  # Смешанные буквы и цифры без пробелов
            r'[<>(){}[\]]{3,}',           # Много скобок подряд
            r'[|@#$%^&*]{3,}',            # Специальные символы группами
            r'[A-Z]{5,}',                 # Длинные последовательности заглавных букв
        ]

        for pattern in garbage_patterns:
            if re.search(pattern, clean_text):
                return result  # Это мусор

        # Проверяем кодировку - исключаем файлы с неправильной кодировкой
        weird_chars = sum(1 for c in clean_text if ord(c) > 1000 or (ord(c) < 32 and c not in '\n\t '))
        weird_ratio = weird_chars / total_chars if total_chars > 0 else 0
        if weird_ratio > 0.1:  # Более 10% странных символов
            return result

        # Считаем читаемые символы (буквы и цифры)
        readable_chars = sum(1 for c in clean_text if c.isalnum())
        readable_ratio = readable_chars / total_chars if total_chars > 0 else 0

        # Считаем специальные символы
        special_chars = sum(1 for c in clean_text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / total_chars if total_chars > 0 else 0

        # Проверяем язык - должен быть русский или английский
        cyrillic_chars = sum(1 for c in clean_text if ord(c) >= 1040 and ord(c) <= 1103)  # Основная кириллица
        latin_chars = sum(1 for c in clean_text if c.isalpha() and ord(c) < 128)  # Латиница

        language_chars = cyrillic_chars + latin_chars
        language_ratio = language_chars / readable_chars if readable_chars > 0 else 0

        # Если меньше 60% символов на известных языках - это мусор
        if language_ratio < 0.6:
            return result

        # Проверяем на наличие повторяющихся символов
        char_counts = {}
        for c in clean_text[:1000]:  # Проверяем первые 1000 символов
            if not c.isspace():
                char_counts[c] = char_counts.get(c, 0) + 1

        # Если какой-то символ повторяется более 50 раз - это мусор
        max_repeats = max(char_counts.values()) if char_counts else 0
        if max_repeats > 50:
            return result

        # Проверяем на последовательные повторения
        for char, count in char_counts.items():
            if count > 20 and not char.isalnum():
                return result

        # Анализируем слова
        words = [word for word in clean_text.split() if len(word.strip()) > 0]
        if len(words) < 3:  # Слишком мало слов
            return result

        meaningful_words = 0
        total_word_length = 0
        real_words = 0  # Слова, которые выглядят как настоящие

        for word in words:
            # Очищаем слово от знаков препинания
            clean_word = ''.join(c for c in word if c.isalnum())
            word_len = len(clean_word)

            if word_len >= 2:
                has_letters = any(c.isalpha() for c in clean_word)
                has_digits = any(c.isdigit() for c in clean_word)

                if has_letters:  # Слово содержит буквы
                    meaningful_words += 1
                    total_word_length += word_len

                    # Проверяем, является ли слово "реальным"
                    # Реальные слова не должны быть слишком длинными (>20 символов)
                    # и не должны содержать слишком много цифр
                    if word_len <= 20 and (not has_digits or len(clean_word.replace('0123456789', '')) >= len(clean_word) * 0.3):
                        real_words += 1

        # Рассчитываем метрики
        meaningful_ratio = meaningful_words / len(words) if words else 0
        real_words_ratio = real_words / len(words) if words else 0
        avg_word_length = total_word_length / meaningful_words if meaningful_words > 0 else 0

        # Проверяем наличие структурированного текста
        has_structure = self._has_text_structure(clean_text)

        # Сохраняем языковой скор
        result['language_score'] = language_ratio

        # Улучшенные критерии качественного текста:
        # 1. Достаточное количество читаемых символов (> 40%)
        # 2. Не слишком много специальных символов (< 60%)
        # 3. Достаточное количество осмысленных слов (> 25%)
        # 4. Реальные слова (> 20%)
        # 5. Средняя длина слова разумная (2-18 символов)
        # 6. Хороший языковой скор (> 70%)
        # 7. Наличие структуры ИЛИ достаточное количество реальных слов

        is_good = (
            readable_ratio > 0.4 and
            special_ratio < 0.6 and
            meaningful_ratio > 0.25 and
            real_words_ratio > 0.2 and
            2 <= avg_word_length <= 18 and
            language_ratio > 0.7 and
            (has_structure or real_words > 5)
        )

        result['is_good'] = is_good
        result['meaningful_chars'] = readable_chars
        result['has_structure'] = has_structure

        return result

    def _has_text_structure(self, text: str) -> bool:
        """
        Проверяет наличие структурированного текста (таблицы, списки, заголовки).
        """
        lines = text.split('\n')

        # Проверяем на наличие таблиц (строки с разделителями | или табуляциями)
        table_indicators = ['|', '\t']
        table_lines = 0
        for line in lines:
            if any(indicator in line for indicator in table_indicators):
                table_lines += 1

        if table_lines > 2:  # Более 2 строк с разделителями - вероятно таблица
            return True

        # Проверяем на наличие списков (маркеры: -, •, цифры с точкой)
        list_indicators = [' - ', ' • ', ' 1. ', ' 2. ', ' 3. ']
        list_lines = 0
        for line in lines:
            if any(indicator in line for indicator in list_indicators):
                list_lines += 1

        if list_lines > 3:  # Более 3 строк со списком - вероятно структурированный текст
            return True

        # Проверяем на наличие заголовков (ВСЕ ЗАГЛАВНЫЕ БУКВЫ)
        uppercase_lines = 0
        for line in lines:
            clean_line = ''.join(c for c in line if c.isalpha())
            if len(clean_line) > 3 and clean_line.isupper():
                uppercase_lines += 1

        if uppercase_lines > 1:  # Более 1 заголовка - структурированный текст
            return True

        return False

    def _analyze_page_quality_adaptive(self, page_text: str, document_type: str, structure_analysis: dict = None) -> dict:
        """
        Адаптивный анализ качества страницы с учетом типа документа.
        """
        result = {
            'is_good': False,
            'confidence': 0.0,
            'readable_ratio': 0.0,
            'meaningful_words': 0,
            'has_structure': False,
            'language_score': 0.0,
            'garbage_score': 0.0,
            'document_type': document_type
        }

        if not page_text or len(page_text.strip()) < 10:
            return result

        # Получаем критерии качества для данного типа документа
        criteria = self._get_quality_criteria(document_type)
        
        # Базовый анализ качества
        base_analysis = self._analyze_page_quality(page_text)
        
        # Копируем базовые метрики
        result.update(base_analysis)
        
        # Адаптивная оценка на основе типа документа
        readable_ratio = base_analysis.get('readable_ratio', 0)
        meaningful_words = base_analysis.get('meaningful_words', 0)
        language_score = base_analysis.get('language_score', 0)
        has_structure = base_analysis.get('has_structure', False)
        
        # Специальная логика для разных типов документов
        if document_type == 'table':
            # Для таблиц важнее структура, чем количество слов
            table_structure = self._has_table_structure(page_text)
            structure_bonus = 0.3 if table_structure else 0
            quality_score = (readable_ratio * 0.4 + 
                           (meaningful_words / max(len(page_text.split()), 1)) * 0.3 + 
                           language_score * 0.3 + structure_bonus)
            
        elif document_type == 'form':
            # Для форм важны структурированные данные
            form_indicators = len(re.findall(r'[:\-]\s*[_\s]{2,}', page_text))
            form_bonus = min(form_indicators * 0.1, 0.4)
            quality_score = (readable_ratio * 0.5 + 
                           language_score * 0.3 + 
                           form_bonus + 
                           (0.2 if has_structure else 0))
            
        elif document_type == 'technical':
            # Для технических документов допустимы специальные символы
            tech_patterns = len(re.findall(r'[0-9]+[.,][0-9]+|[A-Z]{2,}|\b[a-z]+\d+\b', page_text))
            tech_bonus = min(tech_patterns * 0.05, 0.3)
            quality_score = (readable_ratio * 0.4 + 
                           language_score * 0.4 + 
                           tech_bonus + 
                           (0.2 if meaningful_words > 5 else 0))
            
        else:  # 'text' и другие
            # Стандартная оценка для текстовых документов
            quality_score = (readable_ratio * 0.4 + 
                           (meaningful_words / max(len(page_text.split()), 1)) * 0.3 + 
                           language_score * 0.3)
        
        # Применяем адаптивные пороги
        confidence_threshold = self._get_confidence_threshold(document_type, structure_analysis or {})
        
        result['confidence'] = quality_score
        result['is_good'] = quality_score >= confidence_threshold
        
        return result

    def _get_adaptive_dpi(self, page, page_idx: int, total_pages: int, pdf_path: Path = None) -> int:
        """
        Выбирает оптимальное DPI для страницы на основе анализа содержимого.
        """
        try:
            # Базовые параметры страницы
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            page_area = page_width * page_height
            
            # Анализ содержимого страницы с низким разрешением
            test_pix = page.get_pixmap(dpi=72)  # Быстрый анализ
            test_img_bytes = test_pix.tobytes("png")
            
            # Конвертируем в PIL Image для анализа
            test_img = Image.open(io.BytesIO(test_img_bytes))
            content_analysis = self._analyze_image_content(test_img)
            
            # Определяем тип документа если возможно
            document_type = 'text'  # По умолчанию
            if pdf_path:
                # Быстрый анализ текста для определения типа
                quick_text = page.get_text()[:500]  # Первые 500 символов
                if quick_text:
                    document_type = self._detect_document_type(quick_text, pdf_path)
            
            # Базовое DPI в зависимости от типа содержимого
            if content_analysis['content_type'] == 'text':
                base_dpi = 200  # Стандартное для текста
            elif content_analysis.get('text_likelihood', 0) > 50:
                base_dpi = 250  # Повышенное для смешанного контента
            else:
                base_dpi = 150  # Пониженное для изображений
            
            # Корректировка на основе размера страницы
            if page_area > 500000:  # Большая страница (A3 и больше)
                size_multiplier = 1.2
            elif page_area < 200000:  # Маленькая страница
                size_multiplier = 0.9
            else:  # Стандартная страница (A4)
                size_multiplier = 1.0
            
            # Корректировка на основе типа документа
            type_multipliers = {
                'table': 1.3,      # Таблицы требуют высокого разрешения
                'form': 1.2,       # Формы тоже
                'technical': 1.4,  # Технические документы с мелким текстом
                'text': 1.0        # Обычный текст
            }
            
            type_multiplier = type_multipliers.get(document_type, 1.0)
            
            # Корректировка на основе качества изображения
            if content_analysis.get('sharpness_score', 0.5) < 0.3:
                quality_multiplier = 1.3  # Размытое изображение - повышаем DPI
            elif content_analysis.get('sharpness_score', 0.5) > 0.8:
                quality_multiplier = 0.9  # Четкое изображение - можно снизить
            else:
                quality_multiplier = 1.0
            
            # Итоговое DPI
            adaptive_dpi = int(base_dpi * size_multiplier * type_multiplier * quality_multiplier)
            
            # Ограничиваем диапазон DPI
            adaptive_dpi = max(100, min(adaptive_dpi, 400))
            
            # Логирование для отладки
            self.logger.debug(f"Адаптивное DPI для страницы {page_idx+1}: {adaptive_dpi} "
                            f"(тип: {document_type}, содержимое: {content_analysis['content_type']}, "
                            f"размер: {page_width:.0f}x{page_height:.0f})")
            
            return adaptive_dpi
            
        except Exception as e:
            self.logger.warning(f"Ошибка расчета адаптивного DPI: {e}")
            return 200  # Fallback к стандартному значению
    
    def _analyze_page_content_quick(self, page) -> dict:
        """
        Быстрый анализ содержимого страницы для выбора параметров обработки.
        """
        try:
            # Получаем текстовый слой
            text_content = page.get_text()
            
            # Анализируем изображения на странице
            image_list = page.get_images()
            
            # Анализируем векторную графику
            drawings = page.get_drawings()
            
            analysis = {
                'has_text': len(text_content.strip()) > 10,
                'text_length': len(text_content),
                'image_count': len(image_list),
                'drawing_count': len(drawings),
                'complexity_score': 0
            }
            
            # Рассчитываем сложность страницы
            complexity = 0
            if analysis['has_text']:
                complexity += min(len(text_content) / 1000, 2)  # Максимум 2 балла за текст
            
            complexity += min(len(image_list) * 0.5, 3)  # Максимум 3 балла за изображения
            complexity += min(len(drawings) * 0.3, 2)     # Максимум 2 балла за векторную графику
            
            analysis['complexity_score'] = complexity
            
            return analysis
            
        except Exception as e:
            self.logger.warning(f"Ошибка анализа содержимого страницы: {e}")
            return {
                'has_text': False,
                'text_length': 0,
                'image_count': 0,
                'drawing_count': 0,
                'complexity_score': 1.0
            }

    def run_google_vision_ocr(self, content: bytes) -> Tuple[str, float]:
        if not self.vision_client: raise RuntimeError("Клиент Google Vision не инициализирован.")
        print("   ☁️ Отправка в Google Cloud Vision... (может занять несколько секунд)")
        ts = time.time()
        image = vision.Image(content=content)
        response = self.vision_client.document_text_detection(image=image)
        if response.error.message:
            raise Exception(f"Google Vision API Error: {response.error.message}")
        text = response.full_text_annotation.text
        confidences = [page.confidence for page in response.full_text_annotation.pages]
        avg_confidence = np.mean(confidences) if confidences else 0.0
        elapsed = time.time() - ts
        print(f"   ✨ Получен ответ от Google за {elapsed:.2f} сек. Уверенность: {avg_confidence:.2%}")
        
        # Логируем время выполнения операции
        self._log_operation_time("google_vision_ocr", ts, 
                               text_length=len(text) if text else 0, 
                               confidence=avg_confidence,
                               content_size_mb=len(content) / (1024 * 1024))
        
        # Логируем метрики качества OCR
        if text:
            self._log_ocr_quality_metrics(text, avg_confidence, method="google_vision")
        
        return text, avg_confidence
    
    def _analyze_image_content(self, img: Image.Image) -> dict:
        """
        Анализ содержимого изображения для выбора оптимальной стратегии сжатия
        """
        # Конвертируем в numpy array для анализа
        img_array = np.array(img.convert('RGB'))
        
        # Анализ цветности
        gray_img = np.array(img.convert('L'))
        color_variance = np.var(img_array)
        gray_variance = np.var(gray_img)
        
        # Определяем тип содержимого
        is_grayscale = color_variance < gray_variance * 1.1
        
        # Анализ контрастности
        contrast = gray_img.std()
        
        # Анализ детализации (высокочастотные компоненты)
        from scipy import ndimage
        try:
            edges = ndimage.sobel(gray_img)
            edge_density = np.mean(np.abs(edges))
        except ImportError:
            # Fallback без scipy
            edge_density = np.mean(np.abs(np.diff(gray_img, axis=0))) + np.mean(np.abs(np.diff(gray_img, axis=1)))
        
        # Анализ текстовых областей (высокий контраст + структурированность)
        text_likelihood = contrast * edge_density / 1000
        
        # Расчет резкости изображения (Laplacian variance)
        sharpness_score = self._calculate_sharpness(gray_img)
        
        return {
            'is_grayscale': is_grayscale,
            'contrast': contrast,
            'edge_density': edge_density,
            'text_likelihood': text_likelihood,
            'sharpness_score': sharpness_score,
            'content_type': 'text' if text_likelihood > 50 else 'image'
        }

    def _get_adaptive_compression_params(self, analysis: dict, target_size_mb: float) -> dict:
        """
        Выбор параметров сжатия на основе анализа содержимого
        """
        if analysis['content_type'] == 'text':
            # Для текстовых документов приоритет качества
            return {
                'format': 'PNG' if analysis['is_grayscale'] else 'JPEG',
                'quality_range': [90, 85, 80, 75] if not analysis['is_grayscale'] else [95],
                'max_dimension': 2400,  # Выше для текста
                'preserve_sharpness': True
            }
        else:
            # Для изображений можно больше сжимать
            return {
                'format': 'JPEG',
                'quality_range': [85, 80, 75, 70, 65],
                'max_dimension': 2048,
                'preserve_sharpness': False
            }
    
    def _preprocess_image_for_ocr(self, img: Image.Image, content_analysis: Dict) -> Image.Image:
        """Предварительная обработка изображения для улучшения качества OCR"""
        processed_img = img.copy()
        
        # Конвертация в RGB если необходимо
        if processed_img.mode not in ('RGB', 'L'):
            processed_img = processed_img.convert('RGB')
        
        # Применяем обработку в зависимости от типа содержимого
        if content_analysis['content_type'] == 'text':
            processed_img = self._enhance_text_image(processed_img)
        elif content_analysis.get('text_likelihood', 0) > 25:  # Смешанный контент с текстом
            processed_img = self._enhance_mixed_content(processed_img)
        
        return processed_img

    def _detect_document_type(self, text_sample: str, pdf_path: Path = None) -> str:
        """
        Определяет тип документа на основе анализа текста и имени файла.
        """
        try:
            text_lower = text_sample.lower()
            
            # Анализ имени файла если доступно
            filename_hints = []
            if pdf_path:
                filename = pdf_path.name.lower()
                if any(word in filename for word in ['table', 'таблица', 'report', 'отчет']):
                    filename_hints.append('table')
                elif any(word in filename for word in ['form', 'форма', 'заявление', 'анкета']):
                    filename_hints.append('form')
                elif any(word in filename for word in ['tech', 'technical', 'spec', 'техн']):
                    filename_hints.append('technical')
            
            # Анализ содержимого текста
            table_indicators = [
                '|', '\t', 'таблица', 'table', 'строка', 'столбец', 'итого', 'сумма',
                'total', 'sum', '№', 'п/п', 'наименование'
            ]
            
            form_indicators = [
                'форма', 'form', 'заявление', 'анкета', 'заполните', 'подпись',
                'дата', 'фио', 'адрес', 'телефон', 'email', 'signature'
            ]
            
            technical_indicators = [
                'спецификация', 'specification', 'техническ', 'technical',
                'параметр', 'parameter', 'гост', 'ту', 'снип', 'размер',
                'диаметр', 'длина', 'ширина', 'высота'
            ]
            
            # Подсчет совпадений
            table_score = sum(1 for indicator in table_indicators if indicator in text_lower)
            form_score = sum(1 for indicator in form_indicators if indicator in text_lower)
            tech_score = sum(1 for indicator in technical_indicators if indicator in text_lower)
            
            # Учитываем подсказки из имени файла
            if 'table' in filename_hints:
                table_score += 2
            elif 'form' in filename_hints:
                form_score += 2
            elif 'technical' in filename_hints:
                tech_score += 2
            
            # Определяем тип документа
            max_score = max(table_score, form_score, tech_score)
            
            if max_score == 0:
                return 'text'  # Обычный текст по умолчанию
            elif table_score == max_score:
                return 'table'
            elif form_score == max_score:
                return 'form'
            elif tech_score == max_score:
                return 'technical'
            else:
                return 'text'
                
        except Exception as e:
            self.logger.warning(f"Ошибка определения типа документа: {e}")
            return 'text'

    def _calculate_sharpness(self, gray_img: np.ndarray) -> float:
        """
        Расчет резкости изображения с использованием Laplacian variance.
        Возвращает значение от 0 до 1, где 1 - максимальная резкость.
        """
        try:
            # Применяем оператор Лапласа для детекции краев
            laplacian = cv2.Laplacian(gray_img, cv2.CV_64F)
            
            # Вычисляем дисперсию - мера резкости
            variance = laplacian.var()
            
            # Нормализуем значение (эмпирически подобранные пороги)
            # Для типичных документов: размытые < 100, четкие > 500
            normalized_sharpness = min(variance / 500.0, 1.0)
            
            return normalized_sharpness
            
        except Exception as e:
            self.logger.warning(f"Ошибка расчета резкости: {e}")
            # Fallback без OpenCV
            try:
                # Простой расчет через градиенты
                grad_x = np.abs(np.diff(gray_img, axis=1))
                grad_y = np.abs(np.diff(gray_img, axis=0))
                sharpness = np.mean(grad_x) + np.mean(grad_y)
                return min(sharpness / 50.0, 1.0)  # Нормализация для градиентов
            except:
                return 0.5  # Средняя резкость по умолчанию
    
    def _process_pdf_sequential(self, doc, pdf_path: Path) -> Tuple[List[str], List[float]]:
        """
        Последовательная обработка всех страниц PDF без батчинга.
        """
        all_pages_text = []
        all_confidences = []
        
        for page_idx, page in enumerate(doc):
            print(f"     -- Обработка страницы {page_idx+1}/{len(doc)} --")
            
            # Используем адаптивное DPI на основе анализа страницы
            adaptive_dpi = self._get_adaptive_dpi(page, page_idx, len(doc), pdf_path)
            
            page_text, page_confidence = self._process_single_pdf_page(page, adaptive_dpi, page_idx+1)
            all_pages_text.append(page_text)
            all_confidences.append(page_confidence)
        
        return all_pages_text, all_confidences
    
    def _process_pdf_with_batching(self, doc, pdf_path: Path, batch_size: int) -> Tuple[List[str], List[float]]:
        """
        Обработка PDF с разбиением на батчи для оптимизации памяти.
        """
        all_pages_text = []
        all_confidences = []
        total_pages = len(doc)
        
        # Обрабатываем страницы батчами
        for batch_start in range(0, total_pages, batch_size):
            batch_end = min(batch_start + batch_size, total_pages)
            batch_pages = list(range(batch_start, batch_end))
            
            print(f"   📦 Батч {batch_start//batch_size + 1}: страницы {batch_start+1}-{batch_end}")
            
            # Обрабатываем текущий батч
            batch_texts, batch_confidences = self._process_pdf_batch(doc, pdf_path, batch_pages)
            
            all_pages_text.extend(batch_texts)
            all_confidences.extend(batch_confidences)
            
            # Принудительная очистка памяти между батчами
            import gc
            gc.collect()
            
            print(f"   ✅ Батч завершен. Обработано {len(batch_texts)} страниц.")
        
        return all_pages_text, all_confidences
    
    def _process_pdf_batch(self, doc, pdf_path: Path, page_indices: List[int]) -> Tuple[List[str], List[float]]:
        """
        Обработка одного батча страниц PDF.
        """
        batch_texts = []
        batch_confidences = []
        
        for page_idx in page_indices:
            page = doc[page_idx]
            print(f"     -- Обработка страницы {page_idx+1}/{len(doc)} --")
            
            # Используем адаптивное DPI
            adaptive_dpi = self._get_adaptive_dpi(page, page_idx, len(doc), pdf_path)
            
            page_text, page_confidence = self._process_single_pdf_page(page, adaptive_dpi, page_idx+1)
            batch_texts.append(page_text)
            batch_confidences.append(page_confidence)
        
        return batch_texts, batch_confidences
    
    def _process_single_pdf_page(self, page, adaptive_dpi: int, page_num: int) -> Tuple[str, float]:
        """
        Обработка одной страницы PDF с обработкой ошибок.
        """
        try:
            pix = page.get_pixmap(dpi=adaptive_dpi)
            img_bytes = pix.tobytes("png")
            
            # Используем новый метод с интеллектуальным сжатием
            page_text, page_confidence = self.run_google_vision_ocr_with_smart_compression(img_bytes)
            return page_text, page_confidence
            
        except google_exceptions.InvalidArgument as e:
            print(f"     ❌ Ошибка Google Vision с DPI {adaptive_dpi}: {str(e)[:100]}...")
            
            # Пробуем с уменьшенным DPI (75% от адаптивного)
            fallback_dpi = max(100, int(adaptive_dpi * 0.75))
            print(f"     🔧 Пробую с уменьшенным разрешением ({fallback_dpi} DPI)...")
            try:
                pix_low = page.get_pixmap(dpi=fallback_dpi)
                img_bytes_low = pix_low.tobytes("png")
                page_text, page_confidence = self.run_google_vision_ocr_with_smart_compression(img_bytes_low)
                return page_text, page_confidence
            except Exception as e2:
                print(f"     ❌ Критическая ошибка: {e2}")
                return f"[ОШИБКА ОБРАБОТКИ СТРАНИЦЫ {page_num}]", 0.0
        
        except Exception as e:
            print(f"     ❌ Неожиданная ошибка на странице {page_num}: {e}")
            return f"[ОШИБКА ОБРАБОТКИ СТРАНИЦЫ {page_num}]", 0.0

    def _enhance_text_image(self, img: Image.Image) -> Image.Image:
        """Улучшение изображения с текстом"""
        try:
            from PIL import ImageEnhance, ImageFilter
            
            # Увеличение контрастности для лучшего распознавания текста
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
            
            # Увеличение резкости
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)
            
            # Легкое шумоподавление
            img = img.filter(ImageFilter.MedianFilter(size=3))
            
            print("   ✨ Применена обработка для текстового содержимого")
            
        except Exception as e:
            print(f"   ⚠️ Ошибка при обработке текстового изображения: {e}")
        
        return img
    
    def _enhance_mixed_content(self, img: Image.Image) -> Image.Image:
        """Улучшение изображения со смешанным содержимым"""
        try:
            from PIL import ImageEnhance
            
            # Умеренное увеличение контрастности
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.1)
            
            # Небольшое увеличение яркости если изображение темное
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.05)
            
            print("   ✨ Применена обработка для смешанного содержимого")
            
        except Exception as e:
            print(f"   ⚠️ Ошибка при обработке смешанного изображения: {e}")
        
        return img

    def run_google_vision_ocr_with_smart_compression(self, content: bytes, max_size_mb: float = 19.0) -> Tuple[str, float]:
        """
        Отправка в Google Vision с адаптивным интеллектуальным сжатием
        """
        start_time = time.time()
        if not self.vision_client:
            raise RuntimeError("Клиент Google Vision не инициализирован.")

        max_size_bytes = int(max_size_mb * 1024 * 1024)

        # Если размер приемлемый, отправляем как есть
        if len(content) <= max_size_bytes:
            result = self.run_google_vision_ocr(content)
            self._log_operation_time("google_vision_smart_compression", start_time, 
                                   compression_applied=False, 
                                   original_size_mb=len(content) / (1024 * 1024))
            return result

        print(f"   ⚠️ Размер изображения {len(content)/1024/1024:.1f}MB превышает лимит {max_size_mb}MB")
        print("   🔧 Применяю адаптивное интеллектуальное сжатие...")

        # Загружаем изображение через Pillow
        with Image.open(io.BytesIO(content)) as img:
            # Конвертируем в RGB если нужно
            if img.mode not in ['RGB', 'L']:
                print(f"   🎨 Конвертирую из {img.mode} в RGB")
                img = img.convert('RGB')
            
            original_size = img.size
            print(f"   📏 Исходный размер: {original_size[0]}x{original_size[1]} пикселей")
            
            # Анализируем содержимое изображения
            print("   🔍 Анализирую содержимое изображения...")
            content_analysis = self._analyze_image_content(img)
            compression_params = self._get_adaptive_compression_params(content_analysis, max_size_mb)
            
            print(f"   📊 Тип содержимого: {content_analysis['content_type']}")
            print(f"   🎯 Стратегия сжатия: {compression_params['format']} (макс. размер: {compression_params['max_dimension']}px)")
            
            # Применяем предварительную обработку для улучшения OCR
            print("   🔧 Применяю предварительную обработку...")
            img = self._preprocess_image_for_ocr(img, content_analysis)
            
            # Используем адаптивное разрешение на основе анализа
            max_dimension = compression_params['max_dimension']
            
            # Вычисляем новый размер с сохранением пропорций
            ratio = min(max_dimension / original_size[0], max_dimension / original_size[1])
            if ratio < 1:
                new_size = (int(original_size[0] * ratio), int(original_size[1] * ratio))
                print(f"   📐 Изменяю размер до: {new_size[0]}x{new_size[1]} пикселей")
                # Используем более качественный ресемплинг для текста
                resample_method = Image.Resampling.LANCZOS if compression_params['preserve_sharpness'] else Image.Resampling.BILINEAR
                img = img.resize(new_size, resample_method)
            
            # Пробуем адаптивные уровни качества
            format_to_use = compression_params['format']
            
            if format_to_use == 'PNG':
                # Для PNG пробуем разные уровни сжатия
                for compress_level in [6, 7, 8, 9]:  # PNG compression levels
                    buffer = io.BytesIO()
                    img_to_save = img.convert('L') if content_analysis['is_grayscale'] else img
                    img_to_save.save(buffer, format='PNG', compress_level=compress_level, optimize=True)
                    compressed_content = buffer.getvalue()
                    
                    size_mb = len(compressed_content) / 1024 / 1024
                    print(f"   🗜️ PNG сжатие уровень {compress_level}: {size_mb:.1f}MB")
                    
                    if len(compressed_content) <= max_size_bytes:
                        print(f"   ✅ Найден подходящий размер: {size_mb:.1f}MB (PNG уровень {compress_level})")
                        result = self.run_google_vision_ocr(compressed_content)
                        self._log_operation_time("google_vision_smart_compression", start_time, 
                                               compression_applied=True, 
                                               original_size_mb=len(content) / (1024 * 1024),
                                               final_size_mb=size_mb,
                                               format_used='PNG',
                                               compression_level=compress_level,
                                               content_type=content_analysis['content_type'])
                        return result
            else:
                # Для JPEG пробуем разные уровни качества
                for quality in compression_params['quality_range']:
                    buffer = io.BytesIO()
                    
                    # Сохраняем в JPEG с текущим качеством
                    img.save(buffer, format='JPEG', quality=quality, optimize=True)
                    compressed_content = buffer.getvalue()
                    
                    size_mb = len(compressed_content) / 1024 / 1024
                    print(f"   🎚️ JPEG качество {quality}%: {size_mb:.1f}MB")
                    
                    if len(compressed_content) <= max_size_bytes:
                        print(f"   ✅ Найден подходящий размер: {size_mb:.1f}MB при качестве {quality}%")
                        result = self.run_google_vision_ocr(compressed_content)
                        self._log_operation_time("google_vision_smart_compression", start_time, 
                                               compression_applied=True, 
                                               original_size_mb=len(content) / (1024 * 1024),
                                               final_size_mb=size_mb,
                                               format_used='JPEG',
                                               quality_used=quality,
                                               content_type=content_analysis['content_type'])
                        return result
            
            # Если стандартное сжатие не помогло, уменьшаем разрешение еще больше
            print("   ⚠️ Требуется дополнительное уменьшение разрешения...")
            
            # Адаптивные размеры в зависимости от типа содержимого
            if content_analysis['content_type'] == 'text':
                fallback_dimensions = [2000, 1600, 1400, 1200]  # Больше для текста
                fallback_quality = 90 if format_to_use == 'JPEG' else 8
            else:
                fallback_dimensions = [1600, 1200, 1024, 800]   # Меньше для изображений
                fallback_quality = 85 if format_to_use == 'JPEG' else 7
            
            for max_dim in fallback_dimensions:
                ratio = min(max_dim / img.size[0], max_dim / img.size[1])
                if ratio < 1:
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    resample_method = Image.Resampling.LANCZOS if compression_params['preserve_sharpness'] else Image.Resampling.BILINEAR
                    resized_img = img.resize(new_size, resample_method)
                    
                    buffer = io.BytesIO()
                    if format_to_use == 'PNG':
                        img_to_save = resized_img.convert('L') if content_analysis['is_grayscale'] else resized_img
                        img_to_save.save(buffer, format='PNG', compress_level=fallback_quality, optimize=True)
                    else:
                        resized_img.save(buffer, format='JPEG', quality=fallback_quality, optimize=True)
                    
                    compressed_content = buffer.getvalue()
                    
                    size_mb = len(compressed_content) / 1024 / 1024
                    print(f"   📏 Размер {new_size[0]}x{new_size[1]} ({format_to_use}): {size_mb:.1f}MB")
                    
                    if len(compressed_content) <= max_size_bytes:
                        print(f"   ✅ Успешное адаптивное сжатие до {size_mb:.1f}MB")
                        result = self.run_google_vision_ocr(compressed_content)
                        
                        # Логируем метрики качества для сжатого изображения
                        if result[0]:  # Если есть текст
                            self._log_ocr_quality_metrics(result[0], result[1], method="google_vision_compressed")
                        
                        self._log_operation_time("google_vision_smart_compression", start_time, 
                                               compression_applied=True, 
                                               original_size_mb=len(content) / (1024 * 1024),
                                               final_size_mb=size_mb,
                                               format_used=format_to_use,
                                               resolution_reduced=True,
                                               final_resolution=new_size,
                                               content_type=content_analysis['content_type'])
                        return result
            
            self._log_operation_time("google_vision_smart_compression", start_time, 
                                   compression_applied=True, 
                                   original_size_mb=len(content) / (1024 * 1024),
                                   content_type=content_analysis['content_type'],
                                   error="Failed to compress to acceptable size")
            raise RuntimeError(f"Не удалось сжать изображение до приемлемого размера (тип: {content_analysis['content_type']})")

    def extract_text_from_file(self, file_path: Path, date: str = None) -> Dict:
        """🔍 Извлечение текста из файла с автоматическим выбором метода"""
        
        start_time = time.time()
        file_name = file_path.name
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        # Нормализуем формат даты к стандартному YYYY-MM-DD
        if date:
            normalized_date = self._normalize_date_format(date)
        else:
            normalized_date = None
        
        # Логируем начало обработки
        self.logger.info(f"Начало обработки файла: {file_name} ({file_size_mb:.2f} MB) для даты {normalized_date}")
        
        # Проверяем, есть ли уже обработанные результаты
        if normalized_date and self._check_existing_results(file_path, normalized_date):
            self.logger.info(f"Файл {file_name} уже обработан, используем кэшированный результат")
            print(f"   ⏭️ Вложение {file_name} уже обработано. Пропускаю.")
            return self._get_existing_result(file_path, normalized_date)
        
        self.logger.info(f"Обработка файла {file_name} методом OCR")
        print(f"   🔄 Обрабатываю вложение {file_name} ({file_size_mb:.1f} MB)")
        
        result = {
            "file_name": file_name,
            "file_path": str(file_path),
            "file_size_mb": round(file_size_mb, 2),
            "success": False,
            "text": "",
            "method": "unknown",
            "confidence": 0.0,
            "processing_time_sec": 0.0,
            "error": None
        }
        
        ext = file_path.suffix.lower()
        text, method, confidence, error = "", "unknown", 0.0, None
        ts = time.time()
        try:
            if ext == ".docx":
                print("   📄 Обработка DOCX локально...")
                doc = DocxDocument(file_path)

                # Извлекаем текст из параграфов
                paragraphs_text = "\n".join([p.text for p in doc.paragraphs])

                # Извлекаем текст из таблиц
                tables_text = []
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            cell_text = cell.text.strip()
                            if cell_text:
                                tables_text.append(cell_text)
                tables_combined = "\n".join(tables_text)

                # Комбинируем текст из параграфов и таблиц
                text = paragraphs_text + "\n" + tables_combined
                text = text.strip()

                method, confidence = "local_docx", 1.0
            elif ext == ".doc":
                print("   📄 Обработка DOC (старый формат) через antiword...")
                if not shutil.which('antiword'):
                    raise FileNotFoundError("Утилита 'antiword' не найдена. Установите ее: brew install antiword")

                # Пытаемся обработать через antiword
                process = subprocess.run(['antiword', str(file_path)], capture_output=True, text=True, encoding='utf-8', errors='ignore')

                if process.returncode == 0 and process.stdout.strip():
                    text = process.stdout
                    method, confidence = "local_doc_antiword", 1.0
                else:
                    print("   ⚠️ Antiword не справился. Пробуем резервный метод (DOCX)...")
                    # Резервный метод: пробуем обработать как DOCX (файл может быть в новом формате)
                    try:
                        if PYTHON_DOCX_AVAILABLE:
                            doc = DocxDocument(file_path)
                            paragraphs_text = "\n".join([p.text for p in doc.paragraphs])
                            tables_text = []
                            for table in doc.tables:
                                for row in table.rows:
                                    for cell in row.cells:
                                        cell_text = cell.text.strip()
                                        if cell_text:
                                            tables_text.append(cell_text)
                            tables_combined = "\n".join(tables_text)
                            text = paragraphs_text + "\n" + tables_combined
                            text = text.strip()

                            if text:  # Проверяем, что извлечен текст
                                method, confidence = "local_docx_fallback", 1.0
                                print("   ✅ Резервный метод (DOCX) сработал успешно")
                            else:
                                raise RuntimeError("Резервный метод не смог извлечь текст")
                        else:
                            raise RuntimeError("Библиотека python-docx не доступна для резервного метода")
                    except Exception as fallback_error:
                        raise RuntimeError(f"Все методы обработки DOC файла неудачны. Antiword: {process.stderr or 'ошибка'}. Резервный: {str(fallback_error)}")
            elif ext == ".xlsx":
                print("   📄 Обработка XLSX локально...")
                text, method, confidence = self._process_excel_file(file_path, 'xlsx')
            elif ext == ".xls":
                print("   📄 Обработка XLS (старый формат) локально...")
                text, method, confidence = self._process_excel_file(file_path, 'xls')

            # <<< ИЗМЕНЕНИЕ: Самая надежная обработка PDF >>>
            elif ext == ".pdf":
                print("   📄 Обработка PDF... Попытка извлечь текстовый слой.")
                doc = fitz.open(file_path)
                texts = [page.get_text() for page in doc]
                full_text_direct = "\n\n".join(texts).strip()

                # Проверяем качество извлеченного текста с учетом структуры PDF
                if len(full_text_direct) > 100 and self._is_text_quality_good(full_text_direct, file_path):
                    print("   ✅ Обнаружен качественный текстовый слой. Извлечено локально.")
                    text, method, confidence = full_text_direct, "local_pdf_text", 1.0
                else:
                    if len(full_text_direct) > 100:
                        print("   ⚠️ Извлеченный текст содержит много мусора. Конвертируем страницы PDF в картинки для Google Vision.")
                    else:
                        print("   🖼️ Текстовый слой пуст. Конвертируем страницы PDF в картинки для Google Vision.")
                    
                    # Интеллектуальное разбиение на батчи для больших PDF
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    page_count = len(doc)
                    
                    # Оценка необходимости батчинга
                    memory_req_mb = self._estimate_memory_requirements(file_size_mb, page_count, "ocr")
                    should_batch, optimal_batch_size = self._should_use_batching(page_count, file_size_mb, memory_req_mb)
                    
                    if should_batch:
                        print(f"   📦 Большой PDF ({page_count} стр., {file_size_mb:.1f}MB). Используем батчинг по {optimal_batch_size} страниц.")
                        all_pages_text, all_confidences = self._process_pdf_with_batching(doc, file_path, optimal_batch_size)
                    else:
                        print(f"   📄 Обычная обработка PDF ({page_count} страниц)")
                        all_pages_text, all_confidences = self._process_pdf_sequential(doc, file_path)
                    
                    text = "\n\n--- PAGE BREAK ---\n\n".join(all_pages_text)
                    confidence = np.mean(all_confidences) if all_confidences else 0.0
                    method = "google_vision_pdf_batched" if should_batch else "google_vision_pdf_optimized"
            
            elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
                print(f"   🖼️ Обработка изображения ({ext}). Отправляем в Google Vision.")
                try:
                    img_bytes = file_path.read_bytes()
                    text, confidence = self.run_google_vision_ocr_with_smart_compression(img_bytes)
                except Exception as e:
                    print(f"     ❌ Ошибка обработки изображения: {e}")
                    text, confidence = f"[ОШИБКА ОБРАБОТКИ ИЗОБРАЖЕНИЯ]", 0.0
                method = "google_vision_image_optimized"

            else:
                method, error = "unsupported", f"Формат {ext} не поддерживается."

        except Exception as e:
            error = str(e)
            method = "error"
            error_details = {
                "file_name": file_name,
                "file_size_mb": file_size_mb,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            self.logger.error(f"Ошибка обработки файла {file_name}: {e}", extra=error_details)
            print(f"   ❌ Произошла ошибка: {e}")

        # Формируем результат
        processing_time = time.time() - ts
        total_time = time.time() - start_time
        
        result.update({
            "success": not error and bool(text.strip()),
            "text": text.strip(),
            "method": method,
            "confidence": confidence,
            "error": error,
            "processing_time_sec": processing_time,
            "total_time_sec": total_time,
            "timestamp": datetime.now().isoformat()
        })
        
        # Логируем результат обработки
        if result["success"]:
            self.logger.info(f"Успешно обработан {file_name}: метод={method}, время={total_time:.2f}с, уверенность={confidence:.2%}")
        else:
            self.logger.warning(f"Неудачная обработка {file_name}: метод={method}, ошибка={error}")
        
        # Сохраняем результат, если указана дата
        if date:
            self.save_result(result, normalized_date)
        
        return result
    
    def _check_existing_results(self, file_path: Path, date: str) -> bool:
        """🔍 Проверка существования уже обработанных результатов"""
        # Нормализуем формат даты для создания пути
        normalized_date = self._normalize_date_format(date)
        date_texts_dir = self.texts_dir / normalized_date
        if not date_texts_dir.exists():
            self.logger.debug(f"Папка для даты {date} не существует: {date_texts_dir}")
            return False

        # Получаем точное имя файла без расширения
        file_stem = file_path.stem

        # 🆕 ИСПРАВЛЕНИЕ: Ищем файлы с учетом возможных временных меток
        # Формат имени: {thread_id}_{timestamp}_{type}_{original_filename}
        # Пример: 20250722_dna-technology_ru_17cb0020_033857_attach_реквизиты ООО

        # Разбираем имя файла для извлечения оригинального имени без временных меток
        parts = file_stem.split('_')
        
        # Ищем позицию 'attach' в частях имени файла
        attach_index = -1
        for i, part in enumerate(parts):
            if part == 'attach':
                attach_index = i
                break
        
        if attach_index != -1 and attach_index < len(parts) - 1:
            # Это файл вложения с правильным форматом
            # Извлекаем оригинальное имя: все после '_attach_'
            original_name = '_'.join(parts[attach_index + 1:])
            self.logger.debug(f"Распознано имя вложения: {original_name}")

            # Ищем все файлы, содержащие оригинальное имя
            all_txt_files = list(date_texts_dir.glob("*.txt"))
            matching_files = []

            for txt_file in all_txt_files:
                txt_stem = txt_file.stem
                # Убираем суффиксы методов и ошибок для сравнения
                clean_txt_stem = txt_stem.replace('___google_vision_pdf_optimized', '').replace('___local_pdf_text', '').replace('_ERROR', '')

                # Проверяем, содержит ли имя файла оригинальное имя вложения
                if original_name in clean_txt_stem:
                    matching_files.append(txt_file)

            if matching_files:
                # Проверяем, есть ли успешные результаты
                error_files = [f for f in matching_files if '_ERROR.txt' in f.name]
                success_files = [f for f in matching_files if '_ERROR.txt' not in f.name]

                if success_files:
                    self.logger.debug(f"Найдены успешные результаты для вложения '{original_name}': {len(success_files)} файлов")
                    return True  # Есть успешные результаты - пропускаем
                elif error_files:
                    self.logger.debug(f"Найдены только файлы-маркеры ошибок для вложения '{original_name}': {len(error_files)} файлов")
                    return False  # Файлы с ошибками нуждаются в повторной обработке
        else:
            # Файл не соответствует ожидаемому формату - используем старую логику
            self.logger.debug(f"Файл {file_path.name} не соответствует формату вложения, используем точное совпадение")

        # Резервная логика: ищем файлы с точным совпадением имени
        exact_match_files = list(date_texts_dir.glob(f"{file_stem}.txt")) + list(date_texts_dir.glob(f"{file_stem}_ERROR.txt"))

        if exact_match_files:
            error_files = [f for f in exact_match_files if '_ERROR.txt' in f.name]
            success_files = [f for f in exact_match_files if '_ERROR.txt' not in f.name]

            if success_files:
                self.logger.debug(f"Найдены успешные результаты для {file_path.name}: {len(success_files)} файлов")
                return True
            elif error_files:
                self.logger.debug(f"Найдены только файлы-маркеры ошибок для {file_path.name}: {len(error_files)} файлов")
                return False

        # Дополнительно проверяем старые файлы с суффиксами методов для совместимости
        old_format_files = list(date_texts_dir.glob(f"{file_stem}___*.txt"))

        if old_format_files:
            error_files = [f for f in old_format_files if '_ERROR.txt' in f.name]
            success_files = [f for f in old_format_files if '_ERROR.txt' not in f.name]

            if success_files:
                self.logger.debug(f"Найдены старые успешные результаты для {file_path.name}: {len(success_files)} файлов")
                return True
            elif error_files:
                self.logger.debug(f"Найдены старые файлы-маркеры ошибок для {file_path.name}: {len(error_files)} файлов")
                return False

        self.logger.debug(f"Результаты для {file_path.name} не найдены")
        return False
    
    def _get_existing_result(self, file_path: Path, date: str) -> Dict:
        """📄 Получение уже существующего результата обработки"""
        # Нормализуем формат даты для создания пути
        normalized_date = self._normalize_date_format(date)
        date_texts_dir = self.texts_dir / normalized_date
        file_stem = file_path.stem

        # 🆕 ИСПРАВЛЕНИЕ: Используем ту же логику, что и в _check_existing_results
        parts = file_stem.split('_')
        existing_files = []

        if len(parts) >= 4 and parts[-2] == 'attach':
            # Это файл вложения с правильным форматом
            original_name = '_'.join(parts[3:])  # parts[3:] содержит оригинальное имя

            # Ищем все файлы, содержащие оригинальное имя
            all_txt_files = list(date_texts_dir.glob("*.txt"))

            for txt_file in all_txt_files:
                txt_stem = txt_file.stem
                # Убираем суффиксы методов и ошибок для сравнения
                clean_txt_stem = txt_stem.replace('___google_vision_pdf_optimized', '').replace('___local_pdf_text', '').replace('_ERROR', '')

                # Проверяем, содержит ли имя файла оригинальное имя вложения
                if original_name in clean_txt_stem:
                    existing_files.append(txt_file)
        else:
            # Файл не соответствует формату - используем старую логику
            exact_match_files = list(date_texts_dir.glob(f"{file_stem}.txt")) + list(date_texts_dir.glob(f"{file_stem}_ERROR.txt"))

            if not exact_match_files:
                old_format_files = list(date_texts_dir.glob(f"{file_stem}___*.txt"))
                existing_files = old_format_files
            else:
                existing_files = exact_match_files
        
        if not existing_files:
            # Если файлов нет, возвращаем пустой результат
            return {
                "file_name": file_path.name,
                "file_path": str(file_path),
                "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                "success": False,
                "text": "",
                "method": "not_found",
                "confidence": 0.0,
                "processing_time_sec": 0.0,
                "error": "Existing result not found"
            }
        
        # Разделяем файлы на успешные и файлы-маркеры ошибок
        error_files = [f for f in existing_files if '_ERROR.txt' in f.name]
        success_files = [f for f in existing_files if '_ERROR.txt' not in f.name]
        
        # Приоритет отдаем успешным файлам
        if success_files:
            result_file = success_files[0]
            is_error = False
        elif error_files:
            result_file = error_files[0]
            is_error = True
        else:
            result_file = existing_files[0]
            is_error = '_ERROR.txt' in result_file.name
        
        # Определяем метод обработки из имени файла или содержимого
        if '___' in result_file.stem:
            # Старый формат с суффиксом метода
            method = result_file.stem.split('___')[-1]
            if method.endswith('_ERROR'):
                method = method[:-6]  # Убираем _ERROR суффикс
        else:
            # Новый формат - метод в содержимом файла
            method = 'unknown'
        
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Если новый формат, извлекаем метод из содержимого
            if method == 'unknown' and '# ⚙️ Метод:' in content:
                for line in content.split('\n'):
                    if line.startswith('# ⚙️ Метод:'):
                        method = line.split(': ')[1].strip()
                        break
                
            # Извлекаем текст (пропускаем заголовки)
            lines = content.split('\n')
            text_start_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('# ==='):
                    text_start_idx = i + 1
                    break
            
            text = '\n'.join(lines[text_start_idx:]).strip()
            
            if is_error:
                # Для файлов-маркеров ошибок возвращаем информацию об ошибке
                return {
                    "file_name": file_path.name,
                    "file_path": str(file_path),
                    "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                    "success": False,
                    "text": "",
                    "method": f"{method}_cached",
                    "confidence": 0.0,
                    "processing_time_sec": 0.0,
                    "error": "Cached error result"
                }
            else:
                return {
                    "file_name": file_path.name,
                    "file_path": str(file_path),
                    "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                    "success": True,
                    "text": text,
                    "method": f"{method}_cached",
                    "confidence": 1.0,  # Предполагаем высокую уверенность для кэшированных результатов
                    "processing_time_sec": 0.0,
                    "error": None
                }
            
        except Exception as e:
            return {
                "file_name": file_path.name,
                "file_path": str(file_path),
                "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                "success": False,
                "text": "",
                "method": "cache_error",
                "confidence": 0.0,
                "processing_time_sec": 0.0,
                "error": f"Error reading cached result: {e}"
            }

    # ... (все остальные функции: save_result, _print_summary, test_files_by_date, main - без изменений) ...
    def _verify_saved_result(self, result: Dict, date: str) -> bool:
        """🔍 Проверка корректности сохраненного результата"""
        try:
            file_name = result['file_name']
            txt_file_path = result.get('txt_file_path')
            
            if not txt_file_path:
                self.logger.error(f"Отсутствует путь к TXT файлу для {file_name}")
                return False
            
            txt_path = Path(txt_file_path)
            
            # Проверяем существование файла
            if not txt_path.exists():
                self.logger.error(f"TXT файл не найден: {txt_path}")
                return False
            
            # Проверяем размер файла (должен быть больше 0)
            if txt_path.stat().st_size == 0:
                self.logger.error(f"TXT файл пустой: {txt_path}")
                return False
            
            # Проверяем возможность чтения файла
            try:
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Проверяем наличие обязательных заголовков
                if not content.startswith('# 📄 Файл:'):
                    self.logger.error(f"Неверный формат TXT файла: {txt_path}")
                    return False
                    
                # Проверяем наличие разделителя
                if '# =' not in content:
                    self.logger.error(f"Отсутствует разделитель в TXT файле: {txt_path}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Ошибка чтения TXT файла {txt_path}: {e}")
                return False
            
            # Проверяем JSON отчет с нормализованной датой
            normalized_date = self._normalize_date_format(date)
            json_report_path = self.reports_dir / f"test_report_{normalized_date}.json"
            if json_report_path.exists():
                try:
                    with open(json_report_path, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                        
                    # Проверяем, что результат есть в JSON отчете
                    found_in_report = False
                    for entry in report_data:
                        if entry.get('file_name') == file_name:
                            found_in_report = True
                            break
                    
                    if not found_in_report:
                        self.logger.warning(f"Результат для {file_name} не найден в JSON отчете")
                        # Не считаем это критической ошибкой
                        
                except Exception as e:
                    self.logger.error(f"Ошибка проверки JSON отчета {json_report_path}: {e}")
                    return False
            
            self.logger.debug(f"Верификация результата для {file_name} прошла успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка верификации результата для {result.get('file_name', 'unknown')}: {e}")
            return False

    def save_result(self, result: Dict, date: str):
        """💾 Сохранение результатов OCR в файлы с проверкой корректности"""
        # Нормализуем формат даты к стандартному YYYY-MM-DD
        normalized_date = self._normalize_date_format(date)
        date_texts_dir = self.texts_dir / normalized_date
        date_texts_dir.mkdir(parents=True, exist_ok=True)
        
        file_name = result['file_name']
        
        try:
            # Сохраняем TXT файл ВСЕГДА при успешной обработке (даже если текст пустой)
            # Это предотвращает повторную обработку файлов с пустым содержимым
            if result["success"]:
                # Используем точное имя файла как в папке @attachments
                original_name = Path(result['file_name']).stem
                txt_filename = f"{original_name}.txt"
                txt_path = date_texts_dir / txt_filename

                # УДАЛЯЕМ СТАРЫЕ ФАЙЛЫ С ОШИБКАМИ перед сохранением нового результата
                error_filename = f"{original_name}_ERROR.txt"
                error_path = date_texts_dir / error_filename
                if error_path.exists():
                    error_path.unlink()
                    self.logger.info(f"Удален старый файл с ошибкой: {error_path}")

                # Также проверяем старый формат файлов для совместимости
                old_error_files = list(date_texts_dir.glob(f"{original_name}___*_ERROR.txt"))
                for old_error_file in old_error_files:
                    old_error_file.unlink()
                    self.logger.info(f"Удален старый файл с ошибкой: {old_error_file}")

                # Определяем содержимое для сохранения
                text_content = result.get("text", "").strip()
                if not text_content:
                    text_content = "[ФАЙЛ ОБРАБОТАН УСПЕШНО, НО ТЕКСТ НЕ ИЗВЛЕЧЕН]"

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"# 📄 Файл: {result['file_name']}\n# ⚙️ Метод: {result['method']}\n")
                    f.write(f"# ✨ Уверенность: {result['confidence']:.2%}\n# ⏱️ Время: {result['processing_time_sec']:.2f} сек\n")
                    if result.get('error'):
                        f.write(f"# ⚠️ Ошибка: {result['error']}\n")
                    f.write("# " + "=" * 50 + "\n\n" + text_content)

                result["txt_file_path"] = str(txt_path)
                self.logger.info(f"Сохранен TXT файл для {file_name}: {txt_path} (текст: {len(text_content)} символов)")
            else:
                # Для неуспешной обработки тоже создаем файл-маркер
                original_name = Path(result['file_name']).stem
                txt_filename = f"{original_name}_ERROR.txt"
                txt_path = date_texts_dir / txt_filename
                
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"# 📄 Файл: {result['file_name']}\n# ⚙️ Метод: {result['method']}\n")
                    f.write(f"# ❌ ОШИБКА ОБРАБОТКИ\n# ⚠️ Ошибка: {result.get('error', 'Неизвестная ошибка')}\n")
                    f.write(f"# ⏱️ Время: {result['processing_time_sec']:.2f} сек\n")
                    f.write("# " + "=" * 50 + "\n\n[ФАЙЛ НЕ УДАЛОСЬ ОБРАБОТАТЬ]")
                
                result["txt_file_path"] = str(txt_path)
                self.logger.warning(f"Сохранен файл-маркер ошибки для {file_name}: {txt_path}")
            
            # Всегда сохраняем JSON отчет (даже при ошибках)
            json_report_path = self.reports_dir / f"test_report_{normalized_date}.json"
            report_data = []
            
            if json_report_path.exists():
                with open(json_report_path, "r", encoding="utf-8") as f:
                    try: 
                        report_data = json.load(f)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Ошибка чтения JSON отчета {json_report_path}: {e}")
                        report_data = []
            
            report_data.append(result)
            
            with open(json_report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Обновлен JSON отчет для даты {date}: {len(report_data)} записей")
            
            # Проверяем корректность сохраненных результатов
            if self._verify_saved_result(result, date):
                print(f"   ✅ Результаты распознавания сохранены и проверены")
            else:
                print(f"   ⚠️ Результаты сохранены, но обнаружены проблемы при проверке")
                self.logger.warning(f"Проблемы при верификации результата для {file_name}")
            
        except Exception as e:
            error_msg = f"Ошибка сохранения результатов для {file_name}: {e}"
            self.logger.error(error_msg, exc_info=True)
            print(f"   ❌ {error_msg}")
    def _print_summary(self, date: str, stats: Dict):
        """📊 Вывод итоговой статистики обработки файлов с детализацией"""
        print("\n" + "="*25 + f" 📊 ИТОГИ ТЕСТА ЗА {date} " + "="*25)
        
        total = stats.get('total', 0)
        successful = stats.get('successful', 0)
        skipped = stats.get('skipped', 0)
        processed = stats.get('processed', 0)
        failed = processed - successful
        
        success_rate = (successful / processed * 100) if processed > 0 else 0
        
        verification_passed = stats.get('verification_passed', 0)
        verification_failed = stats.get('verification_failed', 0)
        verification_rate = (verification_passed / successful * 100) if successful > 0 else 0
        
        # Основная статистика
        print(f"🗂️  Всего файлов проверено: {total}")
        print(f"⏭️  Пропущено (уже обработаны): {skipped}")
        print(f"🔄 Обработано заново: {processed}")
        print(f"✅ Успешно обработано: {successful} ({success_rate:.1f}%)")
        print(f"❌ С ошибками: {failed}")
        print(f"🔍 Верификация результатов:")
        print(f"   ✅ Прошли проверку: {verification_passed} ({verification_rate:.1f}%)")
        print(f"   ⚠️  Проблемы при проверке: {verification_failed}")
        
        # Детализированная статистика по методам
        print("-" * 70)
        print("⚙️ Детальная статистика по методам обработки:")
        methods = stats.get('methods', {})
        method_categories = {
            'OCR методы': ['google_vision', 'tesseract', 'easyocr'],
            'Текстовые методы': ['pypdf_text', 'docx_text', 'xlsx_text'],
            'Системные': ['skipped_existing', 'error', 'unsupported']
        }
        
        for category, method_list in method_categories.items():
            category_total = sum(methods.get(method, 0) for method in method_list)
            if category_total > 0:
                print(f"\n   📂 {category}: {category_total} файлов")
                for method in method_list:
                    count = methods.get(method, 0)
                    if count > 0:
                        percentage = (count / category_total * 100) if category_total > 0 else 0
                        print(f"      • {method}: {count} ({percentage:.1f}%)")
        
        # Статистика по типам файлов
        file_types = stats.get('file_types', {})
        if file_types:
            print(f"\n📁 Статистика по типам файлов:")
            for file_type, type_stats in sorted(file_types.items()):
                type_total = type_stats.get('total', 0)
                type_success = type_stats.get('successful', 0)
                type_rate = (type_success / type_total * 100) if type_total > 0 else 0
                print(f"   • {file_type.upper()}: {type_total} файлов, успешно: {type_success} ({type_rate:.1f}%)")
        
        # Статистика производительности
        timing_stats = stats.get('timing', {})
        if timing_stats:
            avg_time = timing_stats.get('average_time', 0)
            total_time = timing_stats.get('total_time', 0)
            fastest = timing_stats.get('fastest', 0)
            slowest = timing_stats.get('slowest', 0)
            print(f"\n⏱️  Производительность:")
            print(f"   • Общее время: {total_time:.1f}с")
            print(f"   • Среднее время на файл: {avg_time:.2f}с")
            print(f"   • Самый быстрый: {fastest:.2f}с")
            print(f"   • Самый медленный: {slowest:.2f}с")
        
        # Статистика качества OCR
        quality_stats = stats.get('quality', {})
        if quality_stats:
            avg_confidence = quality_stats.get('average_confidence', 0)
            high_confidence = quality_stats.get('high_confidence_count', 0)
            low_confidence = quality_stats.get('low_confidence_count', 0)
            print(f"\n🎯 Качество OCR:")
            print(f"   • Средняя уверенность: {avg_confidence:.1f}%")
            print(f"   • Высокая уверенность (>80%): {high_confidence} файлов")
            print(f"   • Низкая уверенность (<50%): {low_confidence} файлов")
        
        print("=" * 73)
        
        # Логируем статистику производительности
        self._log_performance_stats(date, stats)
    
    def _log_performance_stats(self, date: str, stats: Dict):
        """📈 Логирование расширенной статистики производительности"""
        try:
            total = stats.get('total', 0)
            successful = stats.get('successful', 0)
            skipped = stats.get('skipped', 0)
            processed = stats.get('processed', 0)
            failed = processed - successful
            
            verification_passed = stats.get('verification_passed', 0)
            verification_failed = stats.get('verification_failed', 0)
            verification_rate = round((verification_passed / successful * 100) if successful > 0 else 0, 2)
            
            # Базовая статистика
            performance_data = {
                 "timestamp": datetime.now().isoformat(),
                 "date": date,
                 "total_files": total,
                 "processed_files": processed,
                 "successful_files": successful,
                 "skipped_files": skipped,
                 "error_files": failed,
                 "verification_passed": verification_passed,
                 "verification_failed": verification_failed,
                 "success_rate": round((successful / processed * 100) if processed > 0 else 0, 2),
                 "error_rate": round((failed / total * 100) if total > 0 else 0, 2),
                 "verification_rate": verification_rate,
                 "methods_used": stats.get('methods', {})
             }
            
            # Добавляем статистику по типам файлов
            file_types_stats = stats.get('file_types', {})
            if file_types_stats:
                performance_data["file_types_breakdown"] = file_types_stats
            
            # Добавляем статистику производительности
            timing_stats = stats.get('timing', {})
            if timing_stats and 'total_time' in timing_stats:
                performance_data["timing_stats"] = {
                    "total_time_sec": round(timing_stats.get('total_time', 0), 2),
                    "average_time_sec": round(timing_stats.get('average_time', 0), 3),
                    "fastest_time_sec": round(timing_stats.get('fastest', 0), 3),
                    "slowest_time_sec": round(timing_stats.get('slowest', 0), 3),
                    "files_per_minute": round((processed / (timing_stats.get('total_time', 1) / 60)) if timing_stats.get('total_time', 0) > 0 else 0, 1)
                }
            
            # Добавляем статистику качества OCR
            quality_stats = stats.get('quality', {})
            if quality_stats and 'average_confidence' in quality_stats:
                performance_data["quality_stats"] = {
                    "average_confidence": round(quality_stats.get('average_confidence', 0), 1),
                    "high_confidence_count": quality_stats.get('high_confidence_count', 0),
                    "low_confidence_count": quality_stats.get('low_confidence_count', 0),
                    "confidence_distribution": {
                        "high_confidence_rate": round((quality_stats.get('high_confidence_count', 0) / successful * 100) if successful > 0 else 0, 1),
                        "low_confidence_rate": round((quality_stats.get('low_confidence_count', 0) / successful * 100) if successful > 0 else 0, 1)
                    }
                }
            
            self.logger.info("Расширенная статистика обработки завершена", extra={
                "performance_data": performance_data,
                "event_type": "enhanced_processing_summary"
            })
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования расширенной статистики производительности: {e}", exc_info=True)
    
    def _log_operation_time(self, operation_name: str, start_time: float, file_name: str = None, **kwargs):
        """⏱️ Логирование времени выполнения операций с расширенными метриками"""
        try:
            execution_time = time.time() - start_time
            
            log_data = {
                "operation": operation_name,
                "execution_time_sec": round(execution_time, 3),
                "timestamp": datetime.now().isoformat(),
                "event_type": "operation_timing",
                "performance_category": self._categorize_performance(execution_time, operation_name)
            }
            
            if file_name:
                log_data["file_name"] = file_name
                log_data["file_size_mb"] = self._get_file_size_mb(file_name)
            
            # Добавляем дополнительные параметры
            log_data.update(kwargs)
            
            # Логируем с разным уровнем в зависимости от производительности
            if execution_time > 30:  # Медленные операции
                self.logger.warning(f"Медленная операция '{operation_name}' выполнена за {execution_time:.3f} сек", extra=log_data)
            elif execution_time > 10:  # Умеренно медленные
                self.logger.info(f"Операция '{operation_name}' выполнена за {execution_time:.3f} сек", extra=log_data)
            else:  # Быстрые операции
                self.logger.debug(f"Операция '{operation_name}' выполнена за {execution_time:.3f} сек", extra=log_data)
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования времени операции {operation_name}: {e}")
    
    def _categorize_performance(self, execution_time: float, operation_name: str) -> str:
        """📊 Категоризация производительности операций"""
        # Пороги зависят от типа операции
        if "ocr" in operation_name.lower():
            if execution_time < 2: return "fast"
            elif execution_time < 10: return "normal"
            elif execution_time < 30: return "slow"
            else: return "very_slow"
        elif "compression" in operation_name.lower():
            if execution_time < 1: return "fast"
            elif execution_time < 5: return "normal"
            elif execution_time < 15: return "slow"
            else: return "very_slow"
        else:
            if execution_time < 0.5: return "fast"
            elif execution_time < 2: return "normal"
            elif execution_time < 10: return "slow"
            else: return "very_slow"
    
    def _get_file_size_mb(self, file_name: str) -> float:
        """📏 Получение размера файла в МБ"""
        try:
            if isinstance(file_name, (str, Path)):
                file_path = Path(file_name)
                if file_path.exists():
                    return round(file_path.stat().st_size / (1024 * 1024), 2)
        except Exception:
            pass
        return 0.0
    
    def _log_ocr_quality_metrics(self, text: str, confidence: float, file_name: str = None, method: str = None):
        """🎯 Логирование метрик качества OCR"""
        try:
            # Анализ качества текста
            text_length = len(text.strip())
            word_count = len(text.split())
            line_count = len(text.splitlines())
            
            # Проверка на наличие специальных символов и структуры
            special_chars = len([c for c in text if not c.isalnum() and not c.isspace()])
            digit_ratio = len([c for c in text if c.isdigit()]) / max(text_length, 1)
            
            # Оценка качества на основе различных факторов
            quality_score = self._calculate_text_quality_score(text, confidence)
            
            quality_data = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "ocr_quality_metrics",
                "confidence": round(confidence, 2),
                "quality_score": round(quality_score, 2),
                "text_metrics": {
                    "character_count": text_length,
                    "word_count": word_count,
                    "line_count": line_count,
                    "special_chars_count": special_chars,
                    "digit_ratio": round(digit_ratio, 3)
                },
                "quality_indicators": {
                    "has_structure": line_count > 1,
                    "reasonable_length": 10 < text_length < 50000,
                    "good_confidence": confidence > 0.7,
                    "balanced_content": 0.1 < digit_ratio < 0.8
                }
            }
            
            if file_name:
                quality_data["file_name"] = file_name
                quality_data["file_size_mb"] = self._get_file_size_mb(file_name)
            
            if method:
                quality_data["ocr_method"] = method
            
            # Логируем с соответствующим уровнем
            if quality_score > 0.8:
                self.logger.info(f"Высокое качество OCR: {quality_score:.2f}", extra=quality_data)
            elif quality_score > 0.5:
                self.logger.debug(f"Среднее качество OCR: {quality_score:.2f}", extra=quality_data)
            else:
                self.logger.warning(f"Низкое качество OCR: {quality_score:.2f}", extra=quality_data)
                
        except Exception as e:
            self.logger.error(f"Ошибка логирования метрик качества OCR: {e}")
    
    def _calculate_text_quality_score(self, text: str, confidence: float) -> float:
        """🧮 Расчет общего балла качества текста"""
        try:
            if not text or not text.strip():
                return 0.0
            
            score = 0.0
            
            # Базовый балл от confidence (40% веса)
            score += confidence * 0.4
            
            # Длина текста (20% веса)
            text_length = len(text.strip())
            if 50 <= text_length <= 10000:
                score += 0.2
            elif 10 <= text_length < 50 or 10000 < text_length <= 50000:
                score += 0.1
            
            # Структурированность (20% веса)
            lines = text.splitlines()
            if len(lines) > 1:
                score += 0.1
                # Бонус за разнообразие длин строк
                line_lengths = [len(line.strip()) for line in lines if line.strip()]
                if line_lengths and max(line_lengths) - min(line_lengths) > 10:
                    score += 0.1
            
            # Соотношение символов (20% веса)
            words = text.split()
            if words:
                avg_word_length = sum(len(word) for word in words) / len(words)
                if 3 <= avg_word_length <= 12:
                    score += 0.2
                elif 2 <= avg_word_length < 3 or 12 < avg_word_length <= 20:
                    score += 0.1
            
            return min(score, 1.0)
            
        except Exception:
            return confidence * 0.5  # Fallback к половине confidence
    
    def _create_progress_bar(self, current: int, total: int, width: int = 30) -> str:
        """📊 Создание визуального прогресс-бара"""
        try:
            progress = current / total
            filled = int(width * progress)
            bar = "█" * filled + "░" * (width - filled)
            return f"[{bar}]"
        except Exception:
            return "[" + "?" * width + "]"
    
    def _print_current_stats(self, stats: Dict):
        """📈 Отображение текущей статистики обработки"""
        try:
            total = stats.get('total', 0)
            successful = stats.get('successful', 0)
            skipped = stats.get('skipped', 0)
            processed = stats.get('processed', 0)
            verification_passed = stats.get('verification_passed', 0)
            verification_failed = stats.get('verification_failed', 0)
            
            success_rate = round((successful / processed * 100) if processed > 0 else 0, 1)
            verification_rate = round((verification_passed / successful * 100) if successful > 0 else 0, 1)
            
            print(f"   📊 Текущая статистика: Всего: {total} | Обработано: {processed} | Успешно: {successful} ({success_rate}%) | Пропущено: {skipped} | Верификация: {verification_passed}/{successful} ({verification_rate}%)")
        except Exception as e:
            print(f"   ⚠️ Ошибка отображения статистики: {e}")

    def _auto_retry_error_files(self, date: str):
        """🔄 Автоматическая повторная обработка файлов с ошибками для указанной даты"""
        # Нормализуем формат даты
        normalized_date = self._normalize_date_format(date)
        
        date_texts_dir = self.texts_dir / normalized_date
        if not date_texts_dir.exists():
            return

        # Ищем файлы с ошибками
        error_files = list(date_texts_dir.glob("*_ERROR.txt"))

        if not error_files:
            return

        print(f"\n🔄 Найдено {len(error_files)} файлов с ошибками. Запускаю автоматическую повторную обработку...")

        retry_stats = {"successful": 0, "failed": 0}

        for error_file in error_files:
            # Извлекаем оригинальное имя файла из имени файла с ошибкой
            error_filename = error_file.stem  # Убираем .txt
            if error_filename.endswith('_ERROR'):
                original_filename = error_filename[:-6]  # Убираем _ERROR
            else:
                continue

            # Ищем соответствующий файл во вложениях
            attachments_dir = self.attachments_dir / normalized_date
            matching_files = list(attachments_dir.glob(f"{original_filename}.*"))

            if not matching_files:
                print(f"   ⚠️ Не найден файл вложения для {original_filename}")
                continue

            file_path = matching_files[0]
            print(f"   🔄 Переобработка: {file_path.name}")

            try:
                # Повторная обработка файла
                result = self.extract_text_from_file(file_path, date)

                if result["success"]:
                    retry_stats["successful"] += 1
                    print(f"   ✅ Успешно переобработан: {original_filename}")

                    # Удаляем старый файл с ошибкой
                    error_file.unlink()
                    self.logger.info(f"Удален файл с ошибкой после успешной переобработки: {error_file}")
                else:
                    retry_stats["failed"] += 1
                    print(f"   ❌ Переобработка неудачна: {original_filename}")

            except Exception as e:
                retry_stats["failed"] += 1
                print(f"   ❌ Ошибка при переобработке {original_filename}: {e}")
                self.logger.error(f"Ошибка автоматической переобработки файла {original_filename}: {e}")

        if retry_stats["successful"] > 0:
            print(f"   🎉 Автоматическая переобработка завершена: {retry_stats['successful']} успешно, {retry_stats['failed']} неудачно")

    async def test_files_by_date_async(self, date: str, files_to_test: List[Path], limit: int = None, max_workers: int = 4):
        """🧪 Асинхронное тестирование файлов за конкретную дату с параллельной обработкой"""
        # Нормализуем формат даты
        normalized_date = self._normalize_date_format(date)
        
        if limit:
            files_to_test = files_to_test[:limit]
            print(f"🎯 Ограничение: тестируем первые {limit} файлов.")

        # Автоматическая повторная обработка файлов с ошибками
        await self._auto_retry_error_files_async(normalized_date)

        stats = {
            "total": 0, "successful": 0, "skipped": 0, "processed": 0,
            "verification_passed": 0, "verification_failed": 0,
            "methods": {}, "file_types": {}, "timing": {"times": []}, "quality": {"confidences": []}
        }
        total_files = len(files_to_test)

        print(f"\n🔍 Проверяю существующие результаты для {total_files} файлов...")
        print(f"📊 Прогресс обработки для даты {normalized_date} (параллельно, {max_workers} потоков):")
        print("=" * 80)
        
        # Разделяем файлы на батчи для параллельной обработки
        semaphore = asyncio.Semaphore(max_workers)
        tasks = []
        
        for i, file_path in enumerate(files_to_test, 1):
            task = self._process_file_async(file_path, normalized_date, i, total_files, stats, semaphore)
            tasks.append(task)
        
        # Выполняем все задачи параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Ошибка обработки файла {files_to_test[i].name}: {result}")
                stats["total"] += 1
            else:
                # Результат уже учтен в _process_file_async
                pass
        
        # Вычисляем агрегированные статистики
        times = stats["timing"]["times"]
        if times:
            stats["timing"]["total_time"] = sum(times)
            stats["timing"]["average_time"] = sum(times) / len(times)
            stats["timing"]["fastest"] = min(times)
            stats["timing"]["slowest"] = max(times)
        
        confidences = stats["quality"]["confidences"]
        if confidences:
            stats["quality"]["average_confidence"] = sum(confidences) / len(confidences) * 100
            stats["quality"]["high_confidence_count"] = sum(1 for c in confidences if c > 0.8)
            stats["quality"]["low_confidence_count"] = sum(1 for c in confidences if c < 0.5)
        
        print("\n" + "=" * 80)
        print(f"🎉 Асинхронное тестирование для даты {date} завершено!")
        self._print_summary(date, stats)

    async def _process_file_async(self, file_path: Path, date: str, file_index: int, total_files: int, stats: Dict, semaphore: asyncio.Semaphore):
        """Асинхронная обработка одного файла"""
        async with semaphore:
            # Отображение прогресса
            progress_percent = (file_index / total_files) * 100
            progress_bar = self._create_progress_bar(file_index, total_files)
            
            print(f"\n{progress_bar} [{file_index:3d}/{total_files}] ({progress_percent:5.1f}%)")
            print(f"📄 Файл: {file_path.name}")
            
            # Проверяем существующие результаты в отдельном потоке
            loop = asyncio.get_event_loop()
            existing_check = await loop.run_in_executor(None, self._check_existing_results, file_path, date)
            
            if existing_check:
                # Проверяем файлы с ошибками
                error_files = await loop.run_in_executor(None, self._get_error_files_for_path, file_path, date)
                
                if error_files:
                    print(f"   🔄 Статус: ОБНАРУЖЕНЫ СТАРЫЕ ОШИБКИ - повторная обработка")
                else:
                    print(f"   ⏭️  Статус: УСПЕШНО ОБРАБОТАН РАНЕЕ - пропускаем")
                    stats["total"] += 1
                    stats["skipped"] += 1
                    stats["methods"]["skipped_existing"] = stats["methods"].get("skipped_existing", 0) + 1
                    return
            
            # Обрабатываем файл в отдельном потоке
            print(f"   🔄 Статус: ОБРАБАТЫВАЕТСЯ...")
            start_time = time.time()
            
            result = await loop.run_in_executor(None, self.extract_text_from_file, file_path, date)
            processing_time = time.time() - start_time
            
            # Обновляем статистику (thread-safe операции)
            file_ext = file_path.suffix.lower().lstrip('.')
            if file_ext not in stats["file_types"]:
                stats["file_types"][file_ext] = {"total": 0, "successful": 0}
            stats["file_types"][file_ext]["total"] += 1
            
            stats["timing"]["times"].append(processing_time)
            stats["total"] += 1
            stats["processed"] += 1
            
            if result["success"]:
                stats["successful"] += 1
                stats["file_types"][file_ext]["successful"] += 1
                print(f"   ✅ Статус: УСПЕШНО ({result['method']}) за {processing_time:.2f}с")
                
                confidence = result.get('confidence', 0)
                if confidence > 0:
                    stats["quality"]["confidences"].append(confidence)
                
                # Проверяем корректность в отдельном потоке
                verification_result = await loop.run_in_executor(None, self._verify_saved_result, result, date)
                if verification_result:
                    stats["verification_passed"] += 1
                    print(f"   🔍 Верификация: ПРОЙДЕНА")
                else:
                    stats["verification_failed"] += 1
                    print(f"   ⚠️  Верификация: ПРОБЛЕМЫ")
            else:
                print(f"   ❌ Статус: ОШИБКА ({result.get('error', 'Неизвестная ошибка')})")
            
            stats["methods"][result["method"]] = stats["methods"].get(result["method"], 0) + 1
            return result

    def _get_error_files_for_path(self, file_path: Path, date: str) -> List[Path]:
        """Получение списка файлов с ошибками для конкретного пути"""
        # Нормализуем формат даты
        normalized_date = self._normalize_date_format(date)
        
        file_stem = file_path.stem
        parts = file_stem.split('_')
        error_files = []

        if len(parts) >= 4 and parts[-2] == 'attach':
            # Для файлов вложений ищем по оригинальному имени
            original_name = '_'.join(parts[3:])
            date_texts_dir = self.texts_dir / normalized_date
            all_txt_files = list(date_texts_dir.glob("*.txt"))

            for txt_file in all_txt_files:
                txt_stem = txt_file.stem
                clean_txt_stem = txt_stem.replace('___google_vision_pdf_optimized', '').replace('___local_pdf_text', '').replace('_ERROR', '')

                if original_name in clean_txt_stem and '_ERROR.txt' in txt_file.name:
                    error_files.append(txt_file)
        else:
            # Для файлов не-вложений используем старую логику
            date_texts_dir = self.texts_dir / normalized_date
            error_files = list(date_texts_dir.glob(f"{file_stem}_ERROR.txt")) + list(date_texts_dir.glob(f"{file_stem}___*_ERROR.txt"))

        return error_files

    async def _auto_retry_error_files_async(self, date: str):
        """Асинхронная автоматическая повторная обработка файлов с ошибками"""
        # Нормализуем формат даты
        normalized_date = self._normalize_date_format(date)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._auto_retry_error_files, normalized_date)

    async def extract_text_from_files_async(self, file_paths: List[Path], date: str = None, max_workers: int = 4) -> List[Dict]:
        """Асинхронное извлечение текста из множества файлов с параллельной обработкой"""
        # Нормализуем формат даты если она передана
        normalized_date = self._normalize_date_format(date) if date else None
        
        semaphore = asyncio.Semaphore(max_workers)
        tasks = []
        
        for file_path in file_paths:
            task = self._extract_text_single_async(file_path, normalized_date, semaphore)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем исключения
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = {
                    "file_name": file_paths[i].name,
                    "file_path": str(file_paths[i]),
                    "success": False,
                    "error": str(result),
                    "method": "async_error"
                }
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results

    async def _extract_text_single_async(self, file_path: Path, date: str, semaphore: asyncio.Semaphore) -> Dict:
        """Асинхронное извлечение текста из одного файла"""
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.extract_text_from_file, file_path, date)

    def test_files_by_date(self, date: str, files_to_test: List[Path], limit: int = None):
        """🧪 Тестирование файлов за конкретную дату с оптимизацией повторной обработки (синхронная версия)"""
        # Нормализуем формат даты
        normalized_date = self._normalize_date_format(date)
        
        if limit:
            files_to_test = files_to_test[:limit]
            print(f"🎯 Ограничение: тестируем первые {limit} файлов.")

        # Автоматическая повторная обработка файлов с ошибками
        self._auto_retry_error_files(normalized_date)

        stats = {
            "total": 0, "successful": 0, "skipped": 0, "processed": 0,
            "verification_passed": 0, "verification_failed": 0,
            "methods": {}, "file_types": {}, "timing": {"times": []}, "quality": {"confidences": []}
        }
        total_files = len(files_to_test)

        print(f"\n🔍 Проверяю существующие результаты для {total_files} файлов...")
        print(f"📊 Прогресс обработки для даты {normalized_date}:")
        print("=" * 80)
        
        for i, file_path in enumerate(files_to_test, 1):
            # Отображение прогресса
            progress_percent = (i / total_files) * 100
            progress_bar = self._create_progress_bar(i, total_files)
            
            print(f"\n{progress_bar} [{i:3d}/{total_files}] ({progress_percent:5.1f}%)")
            print(f"📄 Файл: {file_path.name}")
            
            # Проверяем, есть ли уже обработанные результаты
            if self._check_existing_results(file_path, normalized_date):
                # 🆕 ИСПРАВЛЕНИЕ: Проверяем, есть ли файлы с ошибками, которые нужно переобработать
                # Используем ту же логику, что и в _check_existing_results
                file_stem = file_path.stem
                parts = file_stem.split('_')
                error_files = []

                if len(parts) >= 4 and parts[-2] == 'attach':
                    # Для файлов вложений ищем по оригинальному имени
                    original_name = '_'.join(parts[3:])
                    date_texts_dir = self.texts_dir / normalized_date
                    all_txt_files = list(date_texts_dir.glob("*.txt"))

                    for txt_file in all_txt_files:
                        txt_stem = txt_file.stem
                        clean_txt_stem = txt_stem.replace('___google_vision_pdf_optimized', '').replace('___local_pdf_text', '').replace('_ERROR', '')

                        if original_name in clean_txt_stem and '_ERROR.txt' in txt_file.name:
                            error_files.append(txt_file)
                else:
                    # Для файлов не-вложений используем старую логику
                    date_texts_dir = self.texts_dir / normalized_date
                    error_files = list(date_texts_dir.glob(f"{file_stem}_ERROR.txt")) + list(date_texts_dir.glob(f"{file_stem}___*_ERROR.txt"))

                if error_files:
                    print(f"   🔄 Статус: ОБНАРУЖЕНЫ СТАРЫЕ ОШИБКИ - повторная обработка")
                    # Не пропускаем, обрабатываем повторно
                else:
                    print(f"   ⏭️  Статус: УСПЕШНО ОБРАБОТАН РАНЕЕ - пропускаем")
                    stats["total"] += 1
                    stats["skipped"] += 1
                    stats["methods"]["skipped_existing"] = stats["methods"].get("skipped_existing", 0) + 1
                    self._print_current_stats(stats)
                    continue
            
            # Обрабатываем файл
            print(f"   🔄 Статус: ОБРАБАТЫВАЕТСЯ...")
            start_time = time.time()
            result = self.extract_text_from_file(file_path, normalized_date)
            processing_time = time.time() - start_time
            
            # Собираем статистику по типам файлов
            file_ext = file_path.suffix.lower().lstrip('.')
            if file_ext not in stats["file_types"]:
                stats["file_types"][file_ext] = {"total": 0, "successful": 0}
            stats["file_types"][file_ext]["total"] += 1
            
            # Собираем статистику времени
            stats["timing"]["times"].append(processing_time)
            
            stats["total"] += 1
            stats["processed"] += 1
            
            if result["success"]:
                stats["successful"] += 1
                stats["file_types"][file_ext]["successful"] += 1
                print(f"   ✅ Статус: УСПЕШНО ({result['method']}) за {processing_time:.2f}с")
                
                # Собираем статистику качества OCR
                confidence = result.get('confidence', 0)
                if confidence > 0:
                    stats["quality"]["confidences"].append(confidence)
                
                # Проверяем корректность сохраненных результатов
                if self._verify_saved_result(result, normalized_date):
                    stats["verification_passed"] += 1
                    print(f"   🔍 Верификация: ПРОЙДЕНА")
                else:
                    stats["verification_failed"] += 1
                    print(f"   ⚠️  Верификация: ПРОБЛЕМЫ")
            else:
                print(f"   ❌ Статус: ОШИБКА ({result.get('error', 'Неизвестная ошибка')})")
            
            stats["methods"][result["method"]] = stats["methods"].get(result["method"], 0) + 1
            self._print_current_stats(stats)
        
        # Вычисляем агрегированные статистики
        times = stats["timing"]["times"]
        if times:
            stats["timing"]["total_time"] = sum(times)
            stats["timing"]["average_time"] = sum(times) / len(times)
            stats["timing"]["fastest"] = min(times)
            stats["timing"]["slowest"] = max(times)
        
        confidences = stats["quality"]["confidences"]
        if confidences:
            stats["quality"]["average_confidence"] = sum(confidences) / len(confidences) * 100  # Convert to percentage
            stats["quality"]["high_confidence_count"] = sum(1 for c in confidences if c > 0.8)  # 80% as decimal
            stats["quality"]["low_confidence_count"] = sum(1 for c in confidences if c < 0.5)   # 50% as decimal
        
        print("\n" + "=" * 80)
        print(f"🎉 Тестирование для даты {normalized_date} завершено!")
        self._print_summary(normalized_date, stats)
def main():
    import argparse
    
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='OCR Processor')
    parser.add_argument('--auto', action='store_true', help='Автоматический режим без интерактивного меню')
    parser.add_argument('--date', type=str, help='Дата для обработки в формате YYYY-MM-DD')
    args = parser.parse_args()
    
    try: 
        tester = OCRProcessor()
    except Exception as e:
        print(f"❌ Критическая ошибка при инициализации: {e}")
        return
        
    if not tester.vision_client:
        print("\n⚠️ Пожалуйста, настройте Google Cloud Vision и перезапустите скрипт.")
        return
        
    available_dates = tester.get_available_dates()
    if not available_dates:
        print("🤷 В папке 'data/attachments' не найдено папок с датами (YYYY-MM-DD).")
        return
    
    # Автоматический режим
    if args.auto:
        if args.date:
            # Обработка конкретной даты
            if args.date not in available_dates:
                print(f"❌ Дата '{args.date}' не найдена в доступных датах: {', '.join(available_dates)}")
                return
            
            print(f"🚀 Автоматическая обработка файлов за {args.date}")
            files_found = tester.get_files_for_date(args.date)
            if not files_found:
                print(f"🤷 В папке за {args.date} не найдено поддерживаемых файлов.")
                return
            
            print(f"✅ Найдено файлов для обработки: {len(files_found)}")
            tester.test_files_by_date(args.date, files_found)
        else:
            # Обработка всех дат
            print("🚀 Автоматическая обработка всех файлов")
            for date in available_dates:
                print(f"\n\n--- 🚀 Обработка даты: {date} ---")
                files_found = tester.get_files_for_date(date)
                if files_found:
                    tester.test_files_by_date(date, files_found)
                else:
                    print(f"🤷 В папке за {date} не найдено поддерживаемых файлов.")
        return
    
    # Интерактивный режим
    while True:
        print("\n\n" + "="*25 + " 🎯 МЕНЮ ТЕСТИРОВЩИКА 🎯 " + "="*25)
        print(f"📅 Доступные даты для теста: {', '.join(available_dates)}")
        print("1. 🧪 Протестировать файлы за конкретную дату")
        print("2. 🚀 Протестировать ВСЕ файлы из ВСЕХ дат")
        print("3. 🚪 Выйти")
        choice = input("👉 Ваш выбор (1-3): ").strip()
        if choice == "1":
            date = input("   Введите дату (YYYY-MM-DD): ").strip()
            if date not in available_dates:
                print(f"   ❌ Дата '{date}' не найдена!"); continue
            files_found = tester.get_files_for_date(date)
            if not files_found:
                print(f"🤷 В папке за {date} не найдено поддерживаемых файлов.")
                continue
            print(f"✅ Найдено файлов для обработки: {len(files_found)}")
            limit_input = input(f"   Сколько файлов тестировать? (Enter = все {len(files_found)}): ").strip()
            limit = int(limit_input) if limit_input.isdigit() else None
            tester.test_files_by_date(date, files_found, limit)
        elif choice == "2":
            if input("   Вы уверены, что хотите протестировать все файлы? (y/n): ").lower() == 'y':
                for date in available_dates:
                    print(f"\n\n--- 🚀 Обработка даты: {date} ---")
                    files_found = tester.get_files_for_date(date)
                    if files_found:
                        tester.test_files_by_date(date, files_found)
                    else:
                        print(f"🤷 В папке за {date} не найдено поддерживаемых файлов.")
            else:
                print("   Отменено.")
        elif choice == "3":
            print("👋 До свидания!"); break
        else:
            print("   ❌ Неверный выбор. Пожалуйста, введите число от 1 до 3.")

if __name__ == "__main__":
    main()