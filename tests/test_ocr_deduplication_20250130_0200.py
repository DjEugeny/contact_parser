#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест устранения дублирования OCR обработки
Дата создания: 2025-01-30 02:00 (UTC+07)

Проверяет:
1. Корректность работы _check_existing_results
2. Правильность загрузки кэшированных результатов через _get_existing_result
3. Работу дедупликации в синхронном и асинхронном режиме
4. Обработку различных форматов имен файлов результатов
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import asyncio
from unittest.mock import patch, MagicMock

# Добавляем путь к src для импорта
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from ocr_processor import OCRProcessor

def test_check_existing_results():
    """Тест проверки существующих результатов"""
    print("\n=== Тест проверки существующих результатов ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Создаем тестовую структуру
        processor = OCRProcessor()
        # Переопределяем базовые пути для тестирования
        processor.base_results_dir = temp_path
        processor.texts_dir = temp_path / "texts"
        processor.reports_dir = temp_path / "reports"
        processor.texts_dir.mkdir(exist_ok=True)
        processor.reports_dir.mkdir(exist_ok=True)
        
        # Создаем папку для даты
        date_dir = processor.texts_dir / "2025-01-30"
        date_dir.mkdir(exist_ok=True)
        
        # Создаем тестовый файл результата
        test_file_path = temp_path / "20250130_1200_attach_test_document.pdf"
        test_file_path.touch()
        
        # Создаем файл результата в правильной структуре папок
        result_file = date_dir / "20250130_1200_attach_test_document___google_vision_pdf_optimized.txt"
        result_file.write_text("# Результат OCR\n# ⚙️ Метод: google_vision_pdf_optimized\n# ===\nТестовый текст")
        
        # Тест 1: Проверка существующего результата
        exists = processor._check_existing_results(test_file_path, "2025-01-30")
        print(f"✓ Существующий результат найден: {exists}")
        assert exists, "Должен найти существующий результат"
        
        # Тест 2: Проверка несуществующего результата
        non_existing_file = temp_path / "non_existing_file.pdf"
        non_existing_file.touch()
        exists = processor._check_existing_results(non_existing_file, "2025-01-30")
        print(f"✓ Несуществующий результат не найден: {not exists}")
        assert not exists, "Не должен найти несуществующий результат"
        
        print("✅ Тест проверки существующих результатов пройден")

def test_get_existing_result():
    """Тест получения существующего результата"""
    print("\n=== Тест получения существующего результата ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        processor = OCRProcessor()
        # Переопределяем базовые пути для тестирования
        processor.base_results_dir = temp_path
        processor.texts_dir = temp_path / "texts"
        processor.reports_dir = temp_path / "reports"
        processor.texts_dir.mkdir(exist_ok=True)
        processor.reports_dir.mkdir(exist_ok=True)
        
        date_dir = processor.texts_dir / "2025-01-30"
        date_dir.mkdir(exist_ok=True)
        
        test_file_path = temp_path / "20250130_1200_attach_test_document.pdf"
        test_file_path.write_bytes(b"test pdf content")
        
        # Создаем успешный результат
        result_content = """# Результат OCR обработки
# 📄 Файл: test_document.pdf
# ⚙️ Метод: google_vision_pdf_optimized
# 📊 Уверенность: 0.95
# ⏱️ Время обработки: 2.5 сек
# 📅 Дата: 2025-01-30 12:00 (UTC+07)
# ===========================
Тестовый извлеченный текст из документа"""
        
        result_file = date_dir / "20250130_1200_attach_test_document___google_vision_pdf_optimized.txt"
        result_file.write_text(result_content, encoding='utf-8')
        
        # Проверим, что файл создался
        print(f"✓ Тестовый файл создан: {result_file}")
        print(f"✓ Файл существует: {os.path.exists(result_file)}")
        if os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✓ Содержимое файла: '{content}'")
        
        # Отладочная информация перед вызовом
        search_dir = processor.texts_dir / "2025-01-30"
        print(f"✓ Путь поиска: {search_dir}")
        print(f"✓ Папка существует: {search_dir.exists()}")
        if search_dir.exists():
            files_in_dir = list(search_dir.glob("*.txt"))
            print(f"✓ Файлы в папке: {[f.name for f in files_in_dir]}")
        
        # Получаем результат
        result = processor._get_existing_result(test_file_path, "2025-01-30")
        
        print(f"✓ Результат получен: {result['success']}")
        print(f"✓ Метод: {result.get('method', 'None')}")
        print(f"✓ Текст (первые 50 символов): {result['text'][:50] if result['text'] else 'Пустой'}...")
        print(f"✓ Полный текст: '{result['text']}'")
        
        assert result['success'], f"Результат должен быть успешным, но получен: {result}"
        assert result['method'] == 'google_vision_pdf_optimized_cached', f"Метод должен содержать _cached, но получен: {result['method']}"
        assert "Тестовый извлеченный текст" in result['text'], f"Текст должен содержать ожидаемое содержимое, но получен: '{result['text']}'"
        
        print("✅ Тест получения существующего результата пройден")

def test_deduplication_in_extract_text_from_file():
    """Тест дедупликации в основном методе извлечения текста"""
    print("\n=== Тест дедупликации в extract_text_from_file ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        processor = OCRProcessor()
        processor.texts_dir = temp_path / "texts"
        processor.texts_dir.mkdir(exist_ok=True)
        
        date_dir = processor.texts_dir / "2025-01-30"
        date_dir.mkdir(exist_ok=True)
        
        # Создаем тестовый PDF файл
        test_file_path = temp_path / "20250130_1200_attach_test_document.pdf"
        test_file_path.write_bytes(b"test pdf content")
        
        # Создаем кэшированный результат
        result_content = """# Результат OCR обработки
# 📄 Файл: test_document.pdf
# ⚙️ Метод: google_vision_pdf_optimized
# ===========================
Кэшированный текст документа"""
        
        result_file = date_dir / "20250130_1200_attach_test_document___google_vision_pdf_optimized.txt"
        result_file.write_text(result_content, encoding='utf-8')
        
        # Мокаем методы OCR, чтобы убедиться, что они не вызываются
        with patch.object(processor, 'run_google_vision_ocr') as mock_ocr:
            mock_ocr.return_value = ("Новый текст", 0.9)
            
            # Вызываем извлечение текста
            result = processor.extract_text_from_file(test_file_path, "2025-01-30")
            
            print(f"✓ Использован кэш: {result['method'].endswith('_cached')}")
            print(f"✓ Текст из кэша: {'Кэшированный текст' in result['text']}")
            print(f"✓ OCR не вызывался: {not mock_ocr.called}")
            
            assert result['method'].endswith('_cached'), "Должен использоваться кэшированный результат"
            assert "Кэшированный текст" in result['text'], "Должен возвращать кэшированный текст"
            assert not mock_ocr.called, "OCR не должен вызываться для кэшированного файла"
        
        print("✅ Тест дедупликации в extract_text_from_file пройден")

def test_async_deduplication():
    """Тест дедупликации в асинхронном режиме"""
    print("\n=== Тест асинхронной дедупликации ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        processor = OCRProcessor()
        processor.texts_dir = temp_path / "texts"
        processor.texts_dir.mkdir(exist_ok=True)
        
        date_dir = processor.texts_dir / "2025-01-30"
        date_dir.mkdir(exist_ok=True)
        
        # Создаем несколько тестовых файлов
        test_files = []
        for i in range(3):
            test_file = temp_path / f"20250130_120{i}_attach_test_document_{i}.pdf"
            test_file.write_bytes(f"test pdf content {i}".encode())
            test_files.append(test_file)
            
            # Создаем кэшированный результат для каждого файла
            result_content = f"""# Результат OCR обработки
# 📄 Файл: test_document_{i}.pdf
# ⚙️ Метод: google_vision_pdf_optimized
# ===========================
Кэшированный текст документа {i}"""
            
            result_file = date_dir / f"20250130_120{i}_attach_test_document_{i}___google_vision_pdf_optimized.txt"
            result_file.write_text(result_content, encoding='utf-8')
        
        # Тестируем асинхронную обработку
        results = asyncio.run(processor.extract_text_from_files_async(test_files, "2025-01-30", max_workers=2))
        
        print(f"✓ Обработано файлов: {len(results)}")
        
        cached_count = sum(1 for r in results if r['method'].endswith('_cached'))
        print(f"✓ Использован кэш для файлов: {cached_count}/{len(results)}")
        
        assert len(results) == 3, "Должны быть обработаны все 3 файла"
        assert cached_count == 3, "Все файлы должны использовать кэш"
        
        for i, result in enumerate(results):
            assert f"Кэшированный текст документа {i}" in result['text'], f"Файл {i} должен содержать кэшированный текст"
        
        print("✅ Тест асинхронной дедупликации пройден")

def test_error_file_handling():
    """Тест обработки файлов-маркеров ошибок"""
    print("\n=== Тест обработки файлов-маркеров ошибок ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        processor = OCRProcessor()
        processor.texts_dir = temp_path / "texts"
        processor.texts_dir.mkdir(exist_ok=True)
        
        date_dir = processor.texts_dir / "2025-01-30"
        date_dir.mkdir(exist_ok=True)
        
        # Создаем тестовый PDF файл с правильным форматом имени
        test_file_path = temp_path / "20250130_1200_attach_error_document.pdf"
        test_file_path.write_bytes(b"test pdf content")
        
        # Создаем файл-маркер ошибки с правильным форматом
        error_content = """# Результат OCR обработки
# 📄 Файл: error_document.pdf
# ⚙️ Метод: google_vision_pdf_optimized
# ===========================
Error: Failed to process document"""
        error_file = date_dir / "20250130_1200_attach_error_document___google_vision_pdf_optimized_ERROR.txt"
        error_file.write_text(error_content, encoding='utf-8')
        
        # Проверяем, что ошибка обнаруживается
        print(f"Проверяем файл: {test_file_path}")
        print(f"Файлы в папке: {list(date_dir.glob('*'))}")
        exists = processor._check_existing_results(test_file_path, "2025-01-30")
        print(f"Результат проверки существующих результатов: {exists}")
        # Для файлов с ошибками метод должен возвращать False, чтобы они были повторно обработаны
        assert not exists, "Файлы с ошибками должны быть помечены для повторной обработки"
        
        # Проверяем, что метод _get_existing_result может извлечь информацию об ошибке
        result = processor._get_existing_result(test_file_path, "2025-01-30")
        print(f"Результат извлечения: {result}")
        assert not result['success'], "Результат должен показывать неуспешную обработку"
        assert result['error'] == "Cached error result", "Должна быть информация о кэшированной ошибке"
        
        # Получаем результат ошибки
        result = processor._get_existing_result(test_file_path, "2025-01-30")
        print(f"✓ Результат содержит ошибку: {not result['success']}")
        print(f"✓ Ошибка: {result['error']}")
        
        assert not result['success'], "Результат должен быть неуспешным"
        assert result['error'] == "Cached error result", "Должна быть указана кэшированная ошибка"
        
        print("✅ Тест обработки файлов-маркеров ошибок пройден")

def run_all_tests():
    """Запуск всех тестов"""
    print("🧪 Запуск тестов устранения дублирования OCR обработки")
    print(f"📅 Дата: 2025-01-30 02:00 (UTC+07)")
    print("=" * 60)
    
    try:
        test_check_existing_results()
        test_get_existing_result()
        test_deduplication_in_extract_text_from_file()
        
        # Запуск асинхронного теста
        test_async_deduplication()
        
        test_error_file_handling()
        
        print("\n" + "=" * 60)
        print("🎉 ВСЕ ТЕСТЫ УСТРАНЕНИЯ ДУБЛИРОВАНИЯ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Дедупликация OCR обработки работает корректно")
        print("✅ Кэширование результатов функционирует правильно")
        print("✅ Асинхронная обработка поддерживает дедупликацию")
        print("✅ Обработка ошибок работает корректно")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)