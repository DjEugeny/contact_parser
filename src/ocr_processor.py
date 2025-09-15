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
        date_dir = self.attachments_dir / date
        if not date_dir.exists():
            print(f"❌ Папка не существует: {date_dir}")
            return []

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
        Глубокий анализ структуры PDF для определения наличия качественного текстового слоя.
        Возвращает детальную информацию о структуре документа.
        """
        result = {
            'has_text_layer': False,
            'text_to_image_ratio': 0.0,
            'has_embedded_fonts': False,
            'text_objects_count': 0,
            'image_objects_count': 0,
            'total_objects': 0,
            'font_types': set(),
            'text_confidence': 0.0,
            'structure_score': 0.0
        }

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(pdf_path))
            total_text_chars = 0
            total_image_area = 0
            total_page_area = 0

            for page_num in range(min(len(doc), 3)):  # Анализируем первые 3 страницы
                page = doc[page_num]
                page_area = page.rect.width * page.rect.height
                total_page_area += page_area

                # Извлекаем текст
                text = page.get_text()
                total_text_chars += len(text)

                # Анализируем объекты страницы
                text_blocks = page.get_text("dict")
                result['text_objects_count'] += len(text_blocks.get('blocks', []))

                # Анализируем изображения
                images = page.get_images(full=True)
                result['image_objects_count'] += len(images)

                # Вычисляем площадь изображений
                for img in images:
                    try:
                        img_rect = page.get_image_rects(img[7])  # xref
                        if img_rect:
                            for rect in img_rect:
                                img_area = (rect[2] - rect[0]) * (rect[3] - rect[1])
                                total_image_area += img_area
                    except:
                        pass

                # Анализируем шрифты
                fonts = page.get_fonts()
                for font in fonts:
                    if font and len(font) > 3:
                        font_name = font[3] if isinstance(font[3], str) else str(font[3])
                        result['font_types'].add(font_name)

            doc.close()

            # Вычисляем соотношения
            if total_page_area > 0:
                result['text_to_image_ratio'] = total_image_area / total_page_area

            # Определяем наличие embedded шрифтов
            embedded_fonts = [f for f in result['font_types'] if not f.startswith(('Times', 'Helvetica', 'Courier', 'Symbol', 'ZapfDingbats'))]
            result['has_embedded_fonts'] = len(embedded_fonts) > 0

            # Общее количество объектов
            result['total_objects'] = result['text_objects_count'] + result['image_objects_count']

            # Определяем наличие качественного текстового слоя
            has_significant_text = total_text_chars > 500  # Минимум 500 символов текста
            has_low_image_ratio = result['text_to_image_ratio'] < 0.3  # Менее 30% площади занимают изображения
            has_good_object_ratio = result['text_objects_count'] > result['image_objects_count']  # Больше текстовых объектов чем изображений
            has_embedded_fonts = result['has_embedded_fonts']

            result['has_text_layer'] = has_significant_text and (has_low_image_ratio or has_embedded_fonts or has_good_object_ratio)

            # Вычисляем общий structural score (0-100)
            score = 0
            if has_significant_text: score += 40
            if has_low_image_ratio: score += 30
            if has_good_object_ratio: score += 20
            if has_embedded_fonts: score += 10

            result['structure_score'] = min(100, score)

            # Определяем уверенность в наличии текстового слоя
            if result['has_text_layer'] and result['structure_score'] > 70:
                result['text_confidence'] = 0.9
            elif result['has_text_layer'] and result['structure_score'] > 50:
                result['text_confidence'] = 0.7
            elif result['has_text_layer']:
                result['text_confidence'] = 0.5
            else:
                result['text_confidence'] = 0.1

        except Exception as e:
            result['error'] = str(e)
            result['has_text_layer'] = False
            result['text_confidence'] = 0.0

        return result

    def _quick_garbage_check(self, text: str) -> dict:
        """
        Быстрая проверка текста на наличие мусорных паттернов.
        Возвращает {'is_good': bool, 'reason': str}
        """
        # Анализ паттернов мусора
        patterns = {
            'ocr_garbage': r'[a-z]{2,}[0-9]{2,}[a-z]*',
            'letter_substitution': r'[a-z]{3,}[A-Z]{1,}[a-z]*',
            'symbol_mess': r'[<>(){}[\]]{2,}',
            'repeated_chars': r'(.)\1{3,}',
            'mixed_encoding': r'[\u0080-\u00FF]{3,}',
        }

        garbage_score = 0
        pattern_details = {}
        for pattern_name, pattern in patterns.items():
            matches = re.findall(pattern, text)
            count = len(matches)
            garbage_score += count
            pattern_details[pattern_name] = count

        # Поиск реальных слов (улучшенная версия)
        russian_words = re.findall(r'[а-яё]{4,}', text.lower())  # Минимум 4 буквы
        english_words = re.findall(r'[a-z]{4,}', text.lower())  # Минимум 4 буквы

        # Проверка на искаженные английские слова (замена русских букв)
        fake_english_score = 0
        if english_words:
            for word in english_words[:10]:  # Проверяем первые 10 слов
                # Проверяем на наличие паттернов замены русских букв
                if re.search(r'[a-z]*[o]{2,}[a-z]*', word):  # 'о' заменяется на 'o'
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
            'reason': f"garbage_score={garbage_score}/{garbage_threshold}, ratio={garbage_to_words_ratio:.3f}, russian_words={len(russian_words)}, fake_english_ratio={fake_ratio:.2f}"
        }

    def _is_text_quality_good(self, text: str, pdf_path: Path = None) -> bool:
        """
        Улучшенная оценка качества извлеченного текста из PDF.
        Использует комбинацию анализа текста и структуры PDF.
        """
        if not text or len(text) < 50:
            return False

        # Если передан путь к PDF, сначала анализируем его структуру
        if pdf_path and pdf_path.exists():
            try:
                structure_analysis = self._analyze_pdf_structure(pdf_path)

                # Если структура показывает наличие качественного текстового слоя с высокой уверенностью
                if structure_analysis['has_text_layer'] and structure_analysis['text_confidence'] > 0.7:
                    # Дополнительная проверка текста на мусор
                    garbage_check = self._quick_garbage_check(text)

                    # Специальная логика для документов с отличной структурой PDF
                    if (structure_analysis['structure_score'] >= 90 and
                        'ratio=' in garbage_check['reason']):
                        # Извлекаем ratio из reason
                        try:
                            ratio_str = garbage_check['reason'].split('ratio=')[1].split(',')[0]
                            garbage_ratio = float(ratio_str)
                            # Если соотношение мусора мало (< 5%), игнорируем строгие пороги
                            if garbage_ratio < 0.05:
                                return True
                        except (ValueError, IndexError):
                            pass

                    return garbage_check['is_good']
                elif structure_analysis['text_confidence'] < 0.3:
                    # Структура показывает отсутствие качественного текстового слоя
                    return False
            except Exception as e:
                # Если анализ структуры не удался, продолжаем с текстовым анализом
                pass

        # Быстрая проверка на мусор перед основной обработкой
        garbage_check = self._quick_garbage_check(text)
        if not garbage_check['is_good']:
            return False

        # Разделяем текст на страницы для анализа
        pages = text.split('\n\n')
        if len(pages) == 0:
            return False

        # Анализируем каждую страницу отдельно
        good_pages = 0
        total_meaningful_text = 0

        for page_text in pages:
            if len(page_text.strip()) < 20:  # Пропускаем пустые или слишком короткие страницы
                continue

            page_analysis = self._analyze_page_quality(page_text)
            if page_analysis['is_good']:
                good_pages += 1
                total_meaningful_text += page_analysis['meaningful_chars']

        # Если хотя бы одна страница содержит качественный текст - считаем документ хорошим
        if good_pages > 0:
            return True

        # Дополнительная проверка: если есть значительный объем осмысленного текста
        if total_meaningful_text > 500:  # Минимум 500 символов осмысленного текста
            return True

        return False

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
        
        return text, avg_confidence
    
    def run_google_vision_ocr_with_smart_compression(self, content: bytes, max_size_mb: float = 19.0) -> Tuple[str, float]:
        """
        Отправка в Google Vision с интеллектуальным сжатием
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
        print("   🔧 Применяю интеллектуальное сжатие...")

        # Загружаем изображение через Pillow
        with Image.open(io.BytesIO(content)) as img:
            # Конвертируем в RGB если нужно
            if img.mode not in ['RGB', 'L']:
                print(f"   🎨 Конвертирую из {img.mode} в RGB")
                img = img.convert('RGB')
            
            original_size = img.size
            print(f"   📏 Исходный размер: {original_size[0]}x{original_size[1]} пикселей")
            
            # Для OCR оптимальное разрешение
            max_dimension = 2048  # Максимальная сторона
            
            # Вычисляем новый размер с сохранением пропорций
            ratio = min(max_dimension / original_size[0], max_dimension / original_size[1])
            if ratio < 1:
                new_size = (int(original_size[0] * ratio), int(original_size[1] * ratio))
                print(f"   📐 Изменяю размер до: {new_size[0]}x{new_size[1]} пикселей")
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Пробуем разные уровни качества JPEG
            for quality in [95, 90, 85, 80, 75, 70]:
                buffer = io.BytesIO()
                
                # Сохраняем в JPEG с текущим качеством
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                compressed_content = buffer.getvalue()
                
                size_mb = len(compressed_content) / 1024 / 1024
                print(f"   🎚️ Качество {quality}%: {size_mb:.1f}MB")
                
                if len(compressed_content) <= max_size_bytes:
                        print(f"   ✅ Найден подходящий размер: {size_mb:.1f}MB при качестве {quality}%")
                        result = self.run_google_vision_ocr(compressed_content)
                        self._log_operation_time("google_vision_smart_compression", start_time, 
                                               compression_applied=True, 
                                               original_size_mb=len(content) / (1024 * 1024),
                                               final_size_mb=size_mb,
                                               quality_used=quality)
                        return result
            
            # Если даже при 70% качества размер большой, уменьшаем разрешение еще больше
            print("   ⚠️ Требуется дополнительное уменьшение разрешения...")
            
            for max_dim in [1600, 1200, 1024, 800]:
                ratio = min(max_dim / img.size[0], max_dim / img.size[1])
                if ratio < 1:
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    buffer = io.BytesIO()
                    resized_img.save(buffer, format='JPEG', quality=85, optimize=True)
                    compressed_content = buffer.getvalue()
                    
                    size_mb = len(compressed_content) / 1024 / 1024
                    print(f"   📏 Размер {new_size[0]}x{new_size[1]}: {size_mb:.1f}MB")
                    
                    if len(compressed_content) <= max_size_bytes:
                        print(f"   ✅ Успешное сжатие до {size_mb:.1f}MB")
                        result = self.run_google_vision_ocr(compressed_content)
                        self._log_operation_time("google_vision_smart_compression", start_time, 
                                               compression_applied=True, 
                                               original_size_mb=len(content) / (1024 * 1024),
                                               final_size_mb=size_mb,
                                               resolution_reduced=True,
                                               final_resolution=new_size)
                        return result
            
            self._log_operation_time("google_vision_smart_compression", start_time, 
                                   compression_applied=True, 
                                   original_size_mb=len(content) / (1024 * 1024),
                                   error="Failed to compress to acceptable size")
            raise RuntimeError("Не удалось сжать изображение до приемлемого размера")

    def extract_text_from_file(self, file_path: Path, date: str = None) -> Dict:
        """🔍 Извлечение текста из файла с автоматическим выбором метода"""
        
        start_time = time.time()
        file_name = file_path.name
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        # Логируем начало обработки
        self.logger.info(f"Начало обработки файла: {file_name} ({file_size_mb:.2f} MB) для даты {date}")
        
        # Проверяем, есть ли уже обработанные результаты
        if date and self._check_existing_results(file_path, date):
            self.logger.info(f"Файл {file_name} уже обработан, используем кэшированный результат")
            print(f"   ⏭️ Вложение {file_name} уже обработано. Пропускаю.")
            return self._get_existing_result(file_path, date)
        
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
                    all_pages_text = []
                    all_confidences = []
                    
                    for page_idx, page in enumerate(doc):
                        print(f"     -- Обработка страницы {page_idx+1}/{len(doc)} --")
                        
                        # Используем оптимальное DPI для OCR
                        dpi = 200  # Достаточно для качественного OCR
                        
                        try:
                            pix = page.get_pixmap(dpi=dpi)
                            img_bytes = pix.tobytes("png")
                            
                            # Используем новый метод с интеллектуальным сжатием
                            page_text, page_confidence = self.run_google_vision_ocr_with_smart_compression(img_bytes)
                            
                        except google_exceptions.InvalidArgument as e:
                            print(f"     ❌ Ошибка Google Vision: {str(e)[:100]}...")
                            
                            # Пробуем с еще меньшим DPI
                            print("     🔧 Пробую с уменьшенным разрешением (150 DPI)...")
                            try:
                                pix_low = page.get_pixmap(dpi=150)
                                img_bytes_low = pix_low.tobytes("png")
                                page_text, page_confidence = self.run_google_vision_ocr_with_smart_compression(img_bytes_low)
                            except Exception as e2:
                                print(f"     ❌ Критическая ошибка: {e2}")
                                page_text, page_confidence = f"[ОШИБКА ОБРАБОТКИ СТРАНИЦЫ]", 0.0
                        
                        all_pages_text.append(page_text)
                        all_confidences.append(page_confidence)
                    
                    text = "\n\n--- PAGE BREAK ---\n\n".join(all_pages_text)
                    confidence = np.mean(all_confidences) if all_confidences else 0.0
                    method = "google_vision_pdf_optimized"
            
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
            self.save_result(result, date)
        
        return result
    
    def _check_existing_results(self, file_path: Path, date: str) -> bool:
        """🔍 Проверка существования уже обработанных результатов"""

        date_texts_dir = self.texts_dir / date
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

        date_texts_dir = self.texts_dir / date
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
                    text_start_idx = i + 2
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
            
            # Проверяем JSON отчет
            json_report_path = self.reports_dir / f"test_report_{date}.json"
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
        date_texts_dir = self.texts_dir / date
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
            json_report_path = self.reports_dir / f"test_report_{date}.json"
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
        """⏱️ Логирование времени выполнения операций"""
        try:
            execution_time = time.time() - start_time
            
            log_data = {
                "operation": operation_name,
                "execution_time_sec": round(execution_time, 3),
                "timestamp": datetime.now().isoformat(),
                "event_type": "operation_timing"
            }
            
            if file_name:
                log_data["file_name"] = file_name
            
            # Добавляем дополнительные параметры
            log_data.update(kwargs)
            
            self.logger.debug(f"Операция '{operation_name}' выполнена за {execution_time:.3f} сек", extra=log_data)
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования времени операции {operation_name}: {e}")
    
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
        date_texts_dir = self.texts_dir / date
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
            attachments_dir = self.attachments_dir / date
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

    def test_files_by_date(self, date: str, files_to_test: List[Path], limit: int = None):
        """🧪 Тестирование файлов за конкретную дату с оптимизацией повторной обработки"""
        if limit:
            files_to_test = files_to_test[:limit]
            print(f"🎯 Ограничение: тестируем первые {limit} файлов.")

        # Автоматическая повторная обработка файлов с ошибками
        self._auto_retry_error_files(date)

        stats = {
            "total": 0, "successful": 0, "skipped": 0, "processed": 0,
            "verification_passed": 0, "verification_failed": 0,
            "methods": {}, "file_types": {}, "timing": {"times": []}, "quality": {"confidences": []}
        }
        total_files = len(files_to_test)

        print(f"\n🔍 Проверяю существующие результаты для {total_files} файлов...")
        print(f"📊 Прогресс обработки для даты {date}:")
        print("=" * 80)
        
        for i, file_path in enumerate(files_to_test, 1):
            # Отображение прогресса
            progress_percent = (i / total_files) * 100
            progress_bar = self._create_progress_bar(i, total_files)
            
            print(f"\n{progress_bar} [{i:3d}/{total_files}] ({progress_percent:5.1f}%)")
            print(f"📄 Файл: {file_path.name}")
            
            # Проверяем, есть ли уже обработанные результаты
            if self._check_existing_results(file_path, date):
                # 🆕 ИСПРАВЛЕНИЕ: Проверяем, есть ли файлы с ошибками, которые нужно переобработать
                # Используем ту же логику, что и в _check_existing_results
                file_stem = file_path.stem
                parts = file_stem.split('_')
                error_files = []

                if len(parts) >= 4 and parts[-2] == 'attach':
                    # Для файлов вложений ищем по оригинальному имени
                    original_name = '_'.join(parts[3:])
                    date_texts_dir = self.texts_dir / date
                    all_txt_files = list(date_texts_dir.glob("*.txt"))

                    for txt_file in all_txt_files:
                        txt_stem = txt_file.stem
                        clean_txt_stem = txt_stem.replace('___google_vision_pdf_optimized', '').replace('___local_pdf_text', '').replace('_ERROR', '')

                        if original_name in clean_txt_stem and '_ERROR.txt' in txt_file.name:
                            error_files.append(txt_file)
                else:
                    # Для файлов не-вложений используем старую логику
                    date_texts_dir = self.texts_dir / date
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
            result = self.extract_text_from_file(file_path, date)
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
                if self._verify_saved_result(result, date):
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
        print(f"🎉 Тестирование для даты {date} завершено!")
        self._print_summary(date, stats)
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