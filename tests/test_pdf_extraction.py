#!/usr/bin/env python3
"""
Тест прямого извлечения текста из проблемного PDF файла
"""
import sys
from pathlib import Path

def test_pdf_text_extraction():
    """Тестируем прямое извлечение текста из PDF"""
    
    pdf_file = "data/attachments/3333-33-33/20250512_dna-technology_ru_d0a44d1d_155249_attach_579-2_HLA-эксперт_IVD_b_2021-09-08.pdf"
    
    if not Path(pdf_file).exists():
        print(f"❌ PDF файл не найден: {pdf_file}")
        return
    
    # Симулируем прямое извлечение как в коде OCR
    print("🔍 Имитация логики извлечения текста из PDF...")
    print("📄 Обработка PDF... Попытка извлечь текстовый слой.")
    
    # Вместо реального PyMuPDF будем читать уже извлеченный текст
    # из результата Google Vision для сравнения
    ocr_result_file = "data/final_results/texts/3333-33-33/20250512_dna-technology_ru_d0a44d1d_155249_attach_579-2_HLA-эксперт_IVD_b_2021-09-08.txt"
    
    with open(ocr_result_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем только текст после разделителя
    lines = content.split('\n')
    text_started = False
    text_lines = []
    
    for line in lines:
        if line.startswith('# =================================================='):
            text_started = True
        elif text_started:
            text_lines.append(line)
    
    extracted_text = '\n'.join(text_lines).strip()
    
    print(f"📝 Извлечено текста: {len(extracted_text)} символов")
    print(f"📄 Первые 500 символов:")
    print(f"{extracted_text[:500]}...")
    
    # Имитируем проверку условий
    condition1 = len(extracted_text) > 100
    print(f"\n🔍 Проверка условий:")
    print(f"   • len(extracted_text) > 100: {len(extracted_text)} > 100 = {condition1}")
    
    if condition1:
        print("✅ Условие длины выполнено - нужна проверка качества")
        print("🔧 Следующий шаг: проверка _is_text_quality_good(text, pdf_path)")
        
        # Простая проверка качества
        words = extracted_text.split()
        russian_words = len([w for w in words if any(c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for c in w.lower())])
        
        print(f"   • Общее количество слов: {len(words)}")
        print(f"   • Русские слова: {russian_words}")
        print(f"   • Процент русских слов: {russian_words/len(words)*100:.1f}%")
        
        if russian_words > 100:
            print("\n✅ ВЫВОД: Файл должен обрабатываться ЛОКАЛЬНО (local_pdf_text)")
            print("🤔 Но в реальности был отправлен в Google Vision...")
            print("🔍 Возможные причины:")
            print("   1. Прямое извлечение текста из PDF дало другой/худший результат")
            print("   2. Алгоритм _is_text_quality_good() был слишком строгим")
            print("   3. Проблема в алгоритме _analyze_pdf_structure()")
        else:
            print("\n❌ ВЫВОД: Файл правильно отправлен в Google Vision")
    else:
        print("❌ Условие длины НЕ выполнено - файл отправляется в Google Vision")
    
    return extracted_text

def main():
    print("🧪 Тест прямого извлечения текста из проблемного PDF\n")
    print("=" * 70)
    
    extracted_text = test_pdf_text_extraction()
    
    print("=" * 70)
    print("\n📋 ЗАКЛЮЧЕНИЕ:")
    print("Если текст качественный и его много, но файл все равно отправляется")
    print("в Google Vision, то проблема в одном из следующих мест:")
    print("1. 🔍 Алгоритм анализа структуры PDF (_analyze_pdf_structure)")
    print("2. 🔧 Алгоритм определения качества (_is_text_quality_good)")
    print("3. 📄 Прямое извлечение текста из PDF дает худший результат")

if __name__ == "__main__":
    main()