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
from typing import Dict, List, Tuple
import time
from datetime import datetime
import subprocess
import shutil
import io
import logging
import traceback
from logging.handlers import RotatingFileHandler

from PIL import Image
from google.api_core import exceptions as google_exceptions
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
        file_types = ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.pdf", "*.docx", "*.doc", "*.xlsx", "*.xls"]
        files = sorted(list(set(f for pat in file_types for f in date_dir.rglob(pat))))
        return files
    
    def _normalize_filename(self, filename: str) -> str:
        """🔧 Нормализация имени файла через единую функцию из file_utils"""
        return normalize_filename(filename, remove_extension=True, to_lowercase=True)
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
                process = subprocess.run(['antiword', str(file_path)], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                if process.returncode == 0:
                    text = process.stdout
                else:
                    raise RuntimeError(f"Antiword вернул ошибку: {process.stderr}")
                method, confidence = "local_doc_antiword", 1.0
            elif ext == ".xlsx":
                print("   📄 Обработка XLSX локально...")
                wb = openpyxl.load_workbook(file_path, data_only=True)
                lines = [" | ".join([str(cell.value or "") for cell in row]) for sheet in wb.worksheets for row in sheet.iter_rows()]
                text = "\n".join(lines)
                method, confidence = "local_xlsx", 1.0
            elif ext == ".xls":
                print("   📄 Обработка XLS (старый формат) локально...")
                if not XLRD_AVAILABLE: raise ImportError("Библиотека xlrd не найдена. Установите: pip install xlrd")
                wb = xlrd.open_workbook(file_path, encoding_override="cp1251")
                lines = []
                for sheet in wb.sheets():
                    for row_idx in range(sheet.nrows):
                        lines.append(" | ".join([str(sheet.cell(row_idx, col_idx).value or "") for col_idx in range(sheet.ncols)]))
                text = "\n".join(lines)
                method, confidence = "local_xls", 1.0

            # <<< ИЗМЕНЕНИЕ: Самая надежная обработка PDF >>>
            elif ext == ".pdf":
                print("   📄 Обработка PDF... Попытка извлечь текстовый слой.")
                doc = fitz.open(file_path)
                texts = [page.get_text() for page in doc]
                full_text_direct = "\n\n".join(texts).strip()
                
                if len(full_text_direct) > 100:
                    print("   ✅ Обнаружен текстовый слой. Извлечено локально.")
                    text, method, confidence = full_text_direct, "local_pdf_text", 1.0
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
        
        # Ищем файлы с точным совпадением имени (без суффиксов метода)
        exact_match_files = list(date_texts_dir.glob(f"{file_stem}.txt")) + list(date_texts_dir.glob(f"{file_stem}_ERROR.txt"))
        
        # Если найдены файлы с точным совпадением
        if exact_match_files:
            # Проверяем, есть ли среди найденных файлов файлы-маркеры ошибок
            error_files = [f for f in exact_match_files if '_ERROR.txt' in f.name]
            success_files = [f for f in exact_match_files if '_ERROR.txt' not in f.name]

            if success_files:
                self.logger.debug(f"Найдены успешные результаты для {file_path.name}: {len(success_files)} файлов")
                return True  # Есть успешные результаты - пропускаем
            elif error_files:
                self.logger.debug(f"Найдены только файлы-маркеры ошибок для {file_path.name}: {len(error_files)} файлов")
                # Файлы с ошибками нуждаются в повторной обработке
                return False  # НЕ пропускаем, а обрабатываем повторно
        
        # Дополнительно проверяем старые файлы с суффиксами методов для совместимости
        old_format_files = list(date_texts_dir.glob(f"{file_stem}___*.txt"))
        
        if old_format_files:
            # Аналогично проверяем старые файлы
            error_files = [f for f in old_format_files if '_ERROR.txt' in f.name]
            success_files = [f for f in old_format_files if '_ERROR.txt' not in f.name]

            if success_files:
                self.logger.debug(f"Найдены старые успешные результаты для {file_path.name}: {len(success_files)} файлов")
                return True  # Есть успешные результаты - пропускаем
            elif error_files:
                self.logger.debug(f"Найдены старые файлы-маркеры ошибок для {file_path.name}: {len(error_files)} файлов")
                return False  # Файлы с ошибками нуждаются в повторной обработке
        
        self.logger.debug(f"Результаты для {file_path.name} не найдены")
        return False
    
    def _get_existing_result(self, file_path: Path, date: str) -> Dict:
        """📄 Получение уже существующего результата обработки"""
        
        date_texts_dir = self.texts_dir / date
        file_stem = file_path.stem
        
        # Сначала ищем файлы с точным совпадением имени (новый формат)
        exact_match_files = list(date_texts_dir.glob(f"{file_stem}.txt")) + list(date_texts_dir.glob(f"{file_stem}_ERROR.txt"))
        
        # Если не найдено, ищем по старому формату с суффиксами методов
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
    def test_files_by_date(self, date: str, files_to_test: List[Path], limit: int = None):
        """🧪 Тестирование файлов за конкретную дату с оптимизацией повторной обработки"""
        if limit:
            files_to_test = files_to_test[:limit]
            print(f"🎯 Ограничение: тестируем первые {limit} файлов.")
        
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
                # Дополнительная проверка: есть ли файлы с ошибками, которые нужно переобработать
                date_texts_dir = self.texts_dir / date
                file_stem = file_path.stem
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