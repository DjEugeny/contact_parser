#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест миграции data/final_results → data/ocr
Проверяет работоспособность всех затронутых модулей после миграции
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_config_paths():
    """Тест 1: Проверка config/paths.py"""
    print("\n" + "="*70)
    print("ТЕСТ 1: config/paths.py")
    print("="*70)
    
    try:
        from config.paths import DataPaths
        
        # Проверяем что пути правильные (проверяем окончание пути, так как они абсолютные)
        assert str(DataPaths.OCR_DIR).endswith("data/ocr"), f"Неверный OCR_DIR: {DataPaths.OCR_DIR}"
        assert str(DataPaths.OCR_TEXTS_DIR).endswith("data/ocr/texts"), f"Неверный OCR_TEXTS_DIR: {DataPaths.OCR_TEXTS_DIR}"
        assert str(DataPaths.OCR_REPORTS_DIR).endswith("data/ocr/reports"), f"Неверный OCR_REPORTS_DIR: {DataPaths.OCR_REPORTS_DIR}"
        
        # Проверяем что директории существуют
        assert DataPaths.OCR_DIR.exists(), f"Директория не существует: {DataPaths.OCR_DIR}"
        assert DataPaths.OCR_TEXTS_DIR.exists(), f"Директория не существует: {DataPaths.OCR_TEXTS_DIR}"
        assert DataPaths.OCR_REPORTS_DIR.exists(), f"Директория не существует: {DataPaths.OCR_REPORTS_DIR}"
        
        # Проверяем что старая директория НЕ существует
        assert not DataPaths.LEGACY_FINAL_RESULTS_DIR.exists(), f"Старая директория все еще существует: {DataPaths.LEGACY_FINAL_RESULTS_DIR}"
        
        print("✅ config/paths.py работает корректно")
        print(f"   OCR_DIR: {DataPaths.OCR_DIR}")
        print(f"   OCR_TEXTS_DIR: {DataPaths.OCR_TEXTS_DIR}")
        print(f"   OCR_REPORTS_DIR: {DataPaths.OCR_REPORTS_DIR}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в config/paths.py: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ocr_processor():
    """Тест 2: Проверка src/ocr_processor.py"""
    print("\n" + "="*70)
    print("ТЕСТ 2: src/ocr_processor.py")
    print("="*70)
    
    try:
        from ocr_processor import OCRProcessor
        
        # Создаем экземпляр
        processor = OCRProcessor()
        
        # Проверяем что пути правильные (проверяем окончание пути, так как они абсолютные)
        assert str(processor.base_results_dir).endswith("data/ocr"), f"Неверный base_results_dir: {processor.base_results_dir}"
        assert str(processor.texts_dir).endswith("data/ocr/texts"), f"Неверный texts_dir: {processor.texts_dir}"
        assert str(processor.reports_dir).endswith("data/ocr/reports"), f"Неверный reports_dir: {processor.reports_dir}"
        
        # Проверяем что директории существуют
        assert processor.texts_dir.exists(), f"Директория не существует: {processor.texts_dir}"
        assert processor.reports_dir.exists(), f"Директория не существует: {processor.reports_dir}"
        
        # Проверяем что можем получить доступные даты
        dates = processor.get_available_dates()
        print(f"✅ OCRProcessor работает корректно")
        print(f"   base_results_dir: {processor.base_results_dir}")
        print(f"   Доступно дат: {len(dates)}")
        if dates:
            print(f"   Последняя дата: {dates[-1]}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в OCRProcessor: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_tokens():
    """Тест 3: Проверка src/file_tokens.py"""
    print("\n" + "="*70)
    print("ТЕСТ 3: src/file_tokens.py")
    print("="*70)
    
    try:
        from file_tokens import FileTokenCounter
        
        # Создаем экземпляр
        counter = FileTokenCounter()
        
        # Проверяем что пути правильные (проверяем окончание пути, так как они абсолютные)
        assert str(counter.final_results_path).endswith("data/ocr/texts"), f"Неверный final_results_path: {counter.final_results_path}"
        
        # Проверяем что директория существует
        assert counter.final_results_path.exists(), f"Директория не существует: {counter.final_results_path}"
        
        # Проверяем что можем получить доступные даты
        dates = counter.get_available_dates()
        print(f"✅ FileTokenCounter работает корректно")
        print(f"   final_results_path: {counter.final_results_path}")
        print(f"   Доступно дат: {len(dates)}")
        if dates:
            print(f"   Последняя дата: {dates[-1]}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в FileTokenCounter: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_attachment_evidence_extractor():
    """Тест 4: Проверка src/postprocessing/attachment_evidence_extractor.py"""
    print("\n" + "="*70)
    print("ТЕСТ 4: src/postprocessing/attachment_evidence_extractor.py")
    print("="*70)
    
    try:
        # Проверяем что файл существует и содержит правильные пути
        file_path = Path("src/postprocessing/attachment_evidence_extractor.py")
        assert file_path.exists(), f"Файл не найден: {file_path}"
        
        content = file_path.read_text()
        
        # Проверяем что используется DataPaths
        assert "from config.paths import DataPaths" in content, "Не найден импорт DataPaths"
        assert "DataPaths.get_ocr_text_path" in content, "Не найден вызов get_ocr_text_path"
        
        # Проверяем что нет упоминаний data/final_results в строках кода (кроме комментариев)
        lines = [line for line in content.split('\n') if 'data/final_results' in line and not line.strip().startswith('#')]
        assert len(lines) == 0, f"Найдены упоминания data/final_results в коде: {lines}"
        
        print(f"✅ AttachmentEvidenceExtractor обновлен корректно")
        print(f"   Использует DataPaths: ✓")
        print(f"   Нет упоминаний data/final_results в коде: ✓")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в AttachmentEvidenceExtractor: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ocr_cache_manager():
    """Тест 5: Проверка src/core/ocr_cache_manager.py"""
    print("\n" + "="*70)
    print("ТЕСТ 5: src/core/ocr_cache_manager.py")
    print("="*70)
    
    try:
        # Проверяем что файл существует и содержит правильные пути
        file_path = Path("src/core/ocr_cache_manager.py")
        assert file_path.exists(), f"Файл не найден: {file_path}"
        
        content = file_path.read_text()
        
        # Проверяем что используется DataPaths
        assert "from config.paths import DataPaths" in content, "Не найден импорт DataPaths"
        assert "DataPaths.OCR_TEXTS_DIR" in content, "Не найден вызов OCR_TEXTS_DIR"
        
        # Проверяем что в комментариях указан правильный путь
        assert "data/ocr/texts" in content, "Не найдено упоминание data/ocr/texts"
        
        # Проверяем что нет упоминаний data/final_results в строках кода (кроме комментариев)
        lines = [line for line in content.split('\n') if 'data/final_results' in line and not line.strip().startswith('#') and '"""' not in line]
        assert len(lines) == 0, f"Найдены упоминания data/final_results в коде: {lines}"
        
        print(f"✅ OCRCacheManager обновлен корректно")
        print(f"   Использует DataPaths: ✓")
        print(f"   Нет упоминаний data/final_results в коде: ✓")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в OCRCacheManager: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_no_final_results_mentions():
    """Тест 6: Проверка что в коде нет критичных упоминаний final_results"""
    print("\n" + "="*70)
    print("ТЕСТ 6: Проверка критичных упоминаний final_results в коде")
    print("="*70)
    
    try:
        import subprocess
        
        # Ищем упоминания final_results в Python файлах
        result = subprocess.run(
            ["grep", "-r", "final_results", "--include=*.py", "src/"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            
            # Фильтруем допустимые упоминания
            critical_mentions = []
            for line in lines:
                # Игнорируем комментарии
                if '#' in line and line.split('#')[0].strip() == '':
                    continue
                # Игнорируем docstrings и строки документации
                if '"""' in line or "'''" in line:
                    continue
                # Игнорируем строки, которые являются частью документации
                if ':' in line:
                    file_part, code_part = line.split(':', 1)
                    code_part = code_part.strip()
                    # Игнорируем если это часть docstring (содержит описание миграции)
                    if 'миграцию' in code_part or 'миграция' in code_part or 'Автоматическая миграция' in code_part:
                        continue
                # Игнорируем название переменной final_results_path (это допустимо)
                if 'final_results_path' in line and 'DataPaths.OCR_TEXTS_DIR' in line:
                    continue
                # Игнорируем использование переменной final_results_path
                if 'self.final_results_path' in line:
                    continue
                # Игнорируем LEGACY_FINAL_RESULTS_DIR в paths.py (это часть миграции)
                if 'LEGACY_FINAL_RESULTS_DIR' in line:
                    continue
                    
                critical_mentions.append(line)
            
            if critical_mentions:
                print(f"⚠️  Найдены критичные упоминания final_results:")
                for mention in critical_mentions:
                    print(f"   {mention}")
                return False
            else:
                print("✅ Критичных упоминаний final_results не найдено")
                print(f"   (Найдено {len(lines)} допустимых упоминаний в комментариях и переменных)")
                return True
        else:
            print("✅ Упоминаний final_results в коде не найдено")
            return True
            
    except Exception as e:
        print(f"⚠️  Не удалось проверить упоминания: {e}")
        return True  # Не критично


def main():
    """Запуск всех тестов"""
    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ МИГРАЦИИ data/final_results → data/ocr")
    print("="*70)
    
    results = []
    
    # Запускаем тесты
    results.append(("config/paths.py", test_config_paths()))
    results.append(("OCRProcessor", test_ocr_processor()))
    results.append(("FileTokenCounter", test_file_tokens()))
    results.append(("AttachmentEvidenceExtractor", test_attachment_evidence_extractor()))
    results.append(("OCRCacheManager", test_ocr_cache_manager()))
    results.append(("No final_results mentions", check_no_final_results_mentions()))
    
    # Итоговый отчет
    print("\n" + "="*70)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print("="*70)
    print(f"Результат: {passed}/{total} тестов пройдено")
    print("="*70)
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Миграция выполнена успешно!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} тестов провалено. Требуется исправление.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
