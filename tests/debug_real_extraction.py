#!/usr/bin/env python3
"""
Диагностика реального извлечения текста из проблемного PDF файла
"""
import sys
import os
from pathlib import Path

def debug_real_pdf_extraction():
    """Тестируем реальное извлечение текста из PDF как в коде"""
    
    # Путь к проблемному файлу в тестовой папке
    pdf_file = "data/attachments/2222-22-22/20250512_dna-technology_ru_d0a44d1d_155249_attach_579-2_HLA-эксперт_IVD_b_2021-09-08.pdf"
    
    if not Path(pdf_file).exists():
        print(f"❌ PDF файл не найден: {pdf_file}")
        return
    
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("❌ PyMuPDF не доступен")
        return
    
    print("🔍 ДИАГНОСТИКА РЕАЛЬНОГО ИЗВЛЕЧЕНИЯ ТЕКСТА")
    print("=" * 60)
    print(f"📄 Файл: {pdf_file}")
    
    # Имитируем код из src/ocr_processor.py строки 2577-2582
    print("\n📄 Обработка PDF... Попытка извлечь текстовый слой.")
    doc = fitz.open(pdf_file)
    texts = [page.get_text() for page in doc]
    full_text_direct = "\n\n".join(texts).strip()
    
    print(f"📝 Извлечено текста: {len(full_text_direct)} символов")
    print(f"📄 Количество страниц: {len(doc)}")
    
    # Показываем первые 500 символов
    print(f"\n📄 Первые 500 символов:")
    print("-" * 40)
    print(full_text_direct[:500])
    print("-" * 40)
    
    # Показываем последние 500 символов
    print(f"\n📄 Последние 500 символов:")
    print("-" * 40)
    print(full_text_direct[-500:])
    print("-" * 40)
    
    # Проверяем основное условие
    condition1 = len(full_text_direct) > 100
    print(f"\n🔍 УСЛОВИЕ 1: len(full_text_direct) > 100")
    print(f"   Результат: {len(full_text_direct)} > 100 = {condition1}")
    
    if condition1:
        print("✅ Условие длины выполнено!")
        print("🔧 Следующий шаг: _is_text_quality_good(full_text_direct, file_path)")
        
        # Создаем простую проверку качества как в нашем исправленном методе
        print("\n🧪 ПРОСТАЯ ПРОВЕРКА КАЧЕСТВА:")
        
        # Подсчет русских слов
        import re
        words = full_text_direct.split()
        russian_chars = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
        russian_words = [w for w in words if any(c in russian_chars for c in w.lower())]
        
        print(f"   • Общее количество слов: {len(words)}")
        print(f"   • Русские слова: {len(russian_words)}")
        print(f"   • Процент русских слов: {len(russian_words)/len(words)*100:.1f}%")
        
        # Простая проверка на мусор
        special_chars = sum(1 for c in full_text_direct if not c.isalnum() and not c.isspace())
        total_chars = len(full_text_direct.replace(' ', ''))
        special_ratio = special_chars / total_chars if total_chars > 0 else 0
        
        print(f"   • Специальные символы: {special_chars}")
        print(f"   • Доля спец. символов: {special_ratio:.2%}")
        
        # Проверка на странные паттерны
        weird_patterns = len(re.findall(r'[a-z]{2,}[0-9]{2,}[a-z]*', full_text_direct.lower()))
        print(f"   • Странные паттерны (буквы+цифры): {weird_patterns}")
        
        # Итоговая оценка
        is_likely_good = (
            len(russian_words) > 50 and  # Много русских слов
            special_ratio < 0.5 and     # Не слишком много спец. символов
            weird_patterns < 10         # Мало странных паттернов
        )
        
        print(f"\n📊 ИТОГОВАЯ ОЦЕНКА:")
        print(f"   • Русские слова > 50: {len(russian_words)} > 50 = {len(russian_words) > 50}")
        print(f"   • Спец. символы < 50%: {special_ratio:.2%} < 50% = {special_ratio < 0.5}")
        print(f"   • Странные паттерны < 10: {weird_patterns} < 10 = {weird_patterns < 10}")
        print(f"   • Файл должен быть ХОРОШИМ: {is_likely_good}")
        
        if is_likely_good:
            print("\n✅ ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: local_pdf_text")
            print("❌ ФАКТИЧЕСКИЙ РЕЗУЛЬТАТ: google_vision_pdf_batched")
            print("🚨 ПРОБЛЕМА: _is_text_quality_good() возвращает False!")
        else:
            print("\n❌ ФАЙЛ ДЕЙСТВИТЕЛЬНО ПЛОХОЙ")
            print("✅ Google Vision - правильный выбор")
    else:
        print("❌ Условие длины НЕ выполнено")
        print("✅ Правильно отправляется в Google Vision")
    
    doc.close()

def main():
    print("🧪 Диагностика реального извлечения текста из PDF\n")
    debug_real_pdf_extraction()

if __name__ == "__main__":
    main()