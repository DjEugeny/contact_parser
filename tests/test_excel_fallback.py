#!/usr/bin/env python3
"""
Тест fallback механизма для Excel файлов (.xls и .xlsx)
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, 'src')

# Проверяем доступность библиотек
try:
    import xlrd
    XLRD_AVAILABLE = True
    print("✅ xlrd доступен")
except ImportError:
    XLRD_AVAILABLE = False
    print("❌ xlrd недоступен")

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
    print("✅ openpyxl доступен")
except ImportError:
    OPENPYXL_AVAILABLE = False
    print("❌ openpyxl недоступен")

def test_xls_file(file_path):
    """Тест обработки XLS файла с fallback механизмом"""
    print(f"\n🔍 Тестируем XLS файл: {os.path.basename(file_path)}")

    if not XLRD_AVAILABLE:
        print("❌ xlrd не доступен")
        return

    # Пытаемся обработать через xlrd
    try:
        wb = xlrd.open_workbook(file_path, encoding_override="cp1251")
        lines = []
        for sheet in wb.sheets():
            for row_idx in range(sheet.nrows):
                lines.append(" | ".join([str(sheet.cell(row_idx, col_idx).value or "") for col_idx in range(sheet.ncols)]))
        text = "\n".join(lines)
        text = text.strip()

        if text:
            print("✅ xlrd сработал успешно")
            print(f"📝 Извлечено символов: {len(text)}")
            print(f"📄 Первые 200 символов: {text[:200]}...")
            return True
        else:
            print("⚠️ xlrd не смог извлечь текст")
    except Exception as xlrd_error:
        print(f"⚠️ xlrd не справился: {str(xlrd_error)}")

    # Резервный метод: пробуем обработать как XLSX
    if OPENPYXL_AVAILABLE:
        print("🔄 Пробуем резервный метод (XLSX)...")
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            lines = [" | ".join([str(cell.value or "") for cell in row]) for sheet in wb.worksheets for row in sheet.iter_rows()]
            text = "\n".join(lines)
            text = text.strip()

            if text:
                print("✅ Резервный метод (XLSX) сработал успешно")
                print(f"📝 Извлечено символов: {len(text)}")
                print(f"📄 Первые 200 символов: {text[:200]}...")
                return True
            else:
                print("❌ Резервный метод не смог извлечь текст")
        except Exception as fallback_error:
            print(f"❌ Резервный метод неудачен: {str(fallback_error)}")
    else:
        print("❌ openpyxl недоступен для резервного метода")

    return False

def test_xlsx_file(file_path):
    """Тест обработки XLSX файла с fallback механизмом"""
    print(f"\n🔍 Тестируем XLSX файл: {os.path.basename(file_path)}")

    if not OPENPYXL_AVAILABLE:
        print("❌ openpyxl не доступен")
        return

    # Пытаемся обработать через openpyxl
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        lines = [" | ".join([str(cell.value or "") for cell in row]) for sheet in wb.worksheets for row in sheet.iter_rows()]
        text = "\n".join(lines)
        text = text.strip()

        if text:
            print("✅ openpyxl сработал успешно")
            print(f"📝 Извлечено символов: {len(text)}")
            print(f"📄 Первые 200 символов: {text[:200]}...")
            return True
        else:
            print("⚠️ openpyxl не смог извлечь текст")
    except Exception as openpyxl_error:
        print(f"⚠️ openpyxl не справился: {str(openpyxl_error)}")

    # Резервный метод: пробуем обработать как XLS
    if XLRD_AVAILABLE:
        print("🔄 Пробуем резервный метод (XLS)...")
        try:
            wb = xlrd.open_workbook(file_path, encoding_override="cp1251")
            lines = []
            for sheet in wb.sheets():
                for row_idx in range(sheet.nrows):
                    lines.append(" | ".join([str(sheet.cell(row_idx, col_idx).value or "") for col_idx in range(sheet.ncols)]))
            text = "\n".join(lines)
            text = text.strip()

            if text:
                print("✅ Резервный метод (XLS) сработал успешно")
                print(f"📝 Извлечено символов: {len(text)}")
                print(f"📄 Первые 200 символов: {text[:200]}...")
                return True
            else:
                print("❌ Резервный метод не смог извлечь текст")
        except Exception as fallback_error:
            print(f"❌ Резервный метод неудачен: {str(fallback_error)}")
    else:
        print("❌ xlrd недоступен для резервного метода")

    return False

def main():
    print("🚀 Тест fallback механизма для Excel файлов\n")

    test_files = [
        'test_documents/20250730_mail_ru_b74bcc7b_084908_attach_Заявка на инсталляцию_АлтГУ.xls',
        'test_documents/20250808_dna-technology_ru_752b78d6_165301_attach_ТЗ по КП 8852 по КТРУ.xlsx',
        'test_documents/test_xlsx_as_xls.xlsx',  # XLSX файл с расширением .xlsx (правильное)
        'test_documents/test_xls_as_xlsx.xls'    # XLS файл с расширением .xls (правильное)
    ]

    for file_path in test_files:
        if os.path.exists(file_path):
            ext = Path(file_path).suffix.lower()
            if ext == '.xls':
                test_xls_file(file_path)
            elif ext == '.xlsx':
                test_xlsx_file(file_path)
            else:
                print(f"⚠️ Неподдерживаемое расширение: {ext}")
        else:
            print(f"⚠️ Файл не найден: {file_path}")

if __name__ == "__main__":
    main()
