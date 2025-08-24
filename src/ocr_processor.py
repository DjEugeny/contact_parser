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

from PIL import Image
from google.api_core import exceptions as google_exceptions

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
        self.texts_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.vision_client = vision.ImageAnnotatorClient() if GOOGLE_VISION_AVAILABLE else None
        self._show_capabilities()
        print("\n" + "=" * 70)
        print("🎯 OCR ТЕСТЕР С GOOGLE CLOUD VISION v13 🎯")
        print(f"📁 Исходные файлы: {self.attachments_dir}")
        print(f"🗂️  Результаты в папке: {self.base_results_dir}")
        print("=" * 70)
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
        return text, avg_confidence
    
    def run_google_vision_ocr_with_smart_compression(self, content: bytes, max_size_mb: float = 19.0) -> Tuple[str, float]:
        """
        Отправка в Google Vision с интеллектуальным сжатием
        """
        if not self.vision_client:
            raise RuntimeError("Клиент Google Vision не инициализирован.")

        max_size_bytes = int(max_size_mb * 1024 * 1024)

        # Если размер приемлемый, отправляем как есть
        if len(content) <= max_size_bytes:
            return self.run_google_vision_ocr(content)

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
                    return self.run_google_vision_ocr(compressed_content)
            
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
                        return self.run_google_vision_ocr(compressed_content)
            
            raise RuntimeError("Не удалось сжать изображение до приемлемого размера")

    def extract_text_from_file(self, file_path: Path, date: str = None) -> Dict:
        """🔍 Извлечение текста из файла с автоматическим выбором метода"""
        
        start_time = time.time()
        file_name = file_path.name
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        # Проверяем, есть ли уже обработанные результаты
        if date and self._check_existing_results(file_path, date):
            print(f"   ⏭️ Вложение {file_name} уже обработано. Пропускаю.")
            return self._get_existing_result(file_path, date)
        
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
                text = "\n".join([p.text for p in doc.paragraphs])
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
            print(f"   ❌ Произошла ошибка: {e}")

        # Формируем результат
        result.update({
            "success": not error and bool(text.strip()),
            "text": text.strip(),
            "method": method,
            "confidence": confidence,
            "error": error,
            "processing_time_sec": time.time() - ts,
            "timestamp": datetime.now().isoformat()
        })
        
        # Сохраняем результат, если указана дата
        if date:
            self.save_result(result, date)
        
        return result
    
    def _check_existing_results(self, file_path: Path, date: str) -> bool:
        """🔍 Проверка существования уже обработанных результатов"""
        
        date_texts_dir = self.texts_dir / date
        if not date_texts_dir.exists():
            return False
        
        file_stem = file_path.stem
        # Ищем файлы с результатами для данного файла (любой метод)
        existing_files = list(date_texts_dir.glob(f"{file_stem}___*.txt"))
        return len(existing_files) > 0
    
    def _get_existing_result(self, file_path: Path, date: str) -> Dict:
        """📄 Получение уже существующего результата обработки"""
        
        date_texts_dir = self.texts_dir / date
        file_stem = file_path.stem
        
        # Ищем первый доступный файл с результатами
        existing_files = list(date_texts_dir.glob(f"{file_stem}___*.txt"))
        
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
        
        # Читаем содержимое первого найденного файла
        result_file = existing_files[0]
        method = result_file.stem.split('___')[-1] if '___' in result_file.stem else 'unknown'
        
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Извлекаем текст (пропускаем заголовки)
            lines = content.split('\n')
            text_start_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('# ==='):
                    text_start_idx = i + 2
                    break
            
            text = '\n'.join(lines[text_start_idx:]).strip()
            
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
    def save_result(self, result: Dict, date: str):
        """💾 Сохранение результатов OCR в файлы"""
        date_texts_dir = self.texts_dir / date
        date_texts_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем TXT файл только при успешном распознавании
        if result["success"] and result.get("text", "").strip():
            txt_filename = f"{Path(result['file_name']).stem}___{result['method']}.txt"
            txt_path = date_texts_dir / txt_filename
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"# 📄 Файл: {result['file_name']}\n# ⚙️ Метод: {result['method']}\n")
                f.write(f"# ✨ Уверенность: {result['confidence']:.2%}\n# ⏱️ Время: {result['processing_time_sec']:.2f} сек\n")
                f.write("# " + "=" * 50 + "\n\n" + result['text'])
            result["txt_file_path"] = str(txt_path)
        
        # Всегда сохраняем JSON отчет (даже при ошибках)
        json_report_path = self.reports_dir / f"test_report_{date}.json"
        report_data = []
        if json_report_path.exists():
            with open(json_report_path, "r", encoding="utf-8") as f:
                try: 
                    report_data = json.load(f)
                except json.JSONDecodeError: 
                    pass
        
        report_data.append(result)
        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # Выводим сообщение о сохранении
        print(f"   ✅ Результаты распознавания сохранены")
    def _print_summary(self, date: str, stats: Dict):
        # ... без изменений ...
        print("\n" + "="*25 + f" 📊 ИТОГИ ТЕСТА ЗА {date} " + "="*25)
        total = stats.get('total', 0)
        successful = stats.get('successful', 0)
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0
        print(f"🗂️  Всего обработано файлов: {total}")
        print(f"✅ Успешно: {successful} ({success_rate:.1f}%)")
        print(f"❌ С ошибками: {failed}")
        print("-" * 70)
        print("⚙️ Статистика по методам:")
        methods = stats.get('methods', {})
        for method, count in sorted(methods.items()):
            print(f"   - {method}: {count} раз")
        print("=" * 73)
    def test_files_by_date(self, date: str, files_to_test: List[Path], limit: int = None):
        # ... без изменений ...
        if limit:
            files_to_test = files_to_test[:limit]
            print(f"🎯 Ограничение: тестируем первые {limit} файлов.")
        stats = {"total": 0, "successful": 0, "methods": {}}
        for i, file_path in enumerate(files_to_test, 1):
            print(f"\n--- 🧪 Файл {i}/{len(files_to_test)}: {file_path.name} ---")
            result = self.extract_text_from_file(file_path)
            self.save_result(result, date)
            stats["total"] += 1
            if result["success"]:
                stats["successful"] += 1
            stats["methods"][result["method"]] = stats["methods"].get(result["method"], 0) + 1
        print(f"\n🎉 Тестирование для даты {date} завершено!")
        self._print_summary(date, stats)
def main():
    # ... без изменений ...
    try: tester = OCRProcessor()
    except Exception as e:
        print(f"❌ Критическая ошибка при инициализации: {e}"); return
    if not tester.vision_client:
        print("\n⚠️ Пожалуйста, настройте Google Cloud Vision и перезапустите скрипт."); return
    available_dates = tester.get_available_dates()
    if not available_dates:
        print("🤷 В папке 'data/attachments' не найдено папок с датами (YYYY-MM-DD)."); return
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