#!/usr/bin/env python3
"""
Тест новой системы анализа качества текста PDF
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, 'src')

# Импортируем необходимые модули
try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

def test_pdf_quality(file_path):
    """Тест качества текста PDF файла"""
    print(f"\n🔍 Тестируем PDF файл: {os.path.basename(file_path)}")

    if not PYMUPDF_AVAILABLE:
        print("❌ PyMuPDF не доступен")
        return

    try:
        # Извлекаем текст из PDF
        doc = fitz.open(file_path)
        texts = [page.get_text() for page in doc]
        full_text = "\n\n".join(texts).strip()

        print(f"📝 Извлечено текста: {len(full_text)} символов")
        print(f"📄 Количество страниц: {len(doc)}")

        if len(full_text) < 50:
            print("⚠️ Слишком мало текста для анализа")
            return

        # Проверяем качество текста по старой логике
        old_quality = check_old_quality(full_text)
        print(f"📊 Качество по СТАРОЙ логике: {'ХОРОШЕЕ' if old_quality else 'ПЛОХОЕ'}")

        # Проверяем качество текста по новой логике
        new_quality = check_new_quality(full_text)
        print(f"📊 Качество по НОВОЙ логике: {'ХОРОШЕЕ' if new_quality else 'ПЛОХОЕ'}")

        # Показываем первые 500 символов для анализа
        print(f"\n📋 Первые 500 символов текста:")
        print("-" * 50)
        print(full_text)
        print("-" * 50)

        # Показываем анализ страниц
        print(f"\n📄 Анализ страниц:")
        for i, page_text in enumerate(texts[:3]):  # Показываем первые 3 страницы
            if len(page_text.strip()) > 0:
                page_analysis = analyze_page_quality(page_text)
                print(f"  Страница {i+1}: {page_analysis['meaningful_chars']} символов, качество: {'ХОРОШЕЕ' if page_analysis['is_good'] else 'ПЛОХОЕ'}")
                if page_analysis['has_structure']:
                    print("    📋 Имеет структуру (таблицы/списки)")

        doc.close()

    except Exception as e:
        print(f"❌ Ошибка обработки файла: {e}")

def check_old_quality(text):
    """Старая логика проверки качества текста"""
    if not text or len(text) < 50:
        return False

    clean_text = text.replace(' ', '').replace('\n', '').replace('\t', '')
    total_chars = len(clean_text)
    if total_chars == 0:
        return False

    normal_chars = sum(1 for c in clean_text if c.isalnum() or c in '.,!?;:()[]{}"\'- ')
    normal_ratio = normal_chars / total_chars

    special_counts = {}
    for c in clean_text[:300]:
        safe_chars = ' \n\tabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?;:()[]{}"\'-/_'
        if ord(c) >= 1024 and ord(c) <= 1328:  # Кириллица
            continue
        if c not in safe_chars:
            special_counts[c] = special_counts.get(c, 0) + 1

    max_special_repeats = max(special_counts.values()) if special_counts else 0
    if max_special_repeats > 15:
        return False

    if normal_ratio < 0.2:
        return False

    special_chars_ratio = 1 - normal_ratio
    if special_chars_ratio > 0.6:
        return False

    words = text.split()
    if len(words) < 5:
        return False

    meaningful_words = 0
    for word in words[:30]:
        word_clean = ''.join(c for c in word if c.isalnum())
        if len(word_clean) >= 2 and any(c.isalpha() for c in word_clean):
            meaningful_words += 1

    meaningful_ratio = meaningful_words / len(words)
    if meaningful_ratio > 0.2:
        return True

    if len(text) > 500 and normal_ratio > 0.7:
        return True

    return False

def check_new_quality(text):
    """Новая логика проверки качества текста"""
    if not text or len(text) < 50:
        return False

    pages = text.split('\n\n')
    if len(pages) == 0:
        return False

    good_pages = 0
    total_meaningful_text = 0

    for page_text in pages:
        if len(page_text.strip()) < 20:
            continue

        page_analysis = analyze_page_quality(page_text)
        if page_analysis['is_good']:
            good_pages += 1
            total_meaningful_text += page_analysis['meaningful_chars']

    if good_pages > 0:
        return True

    if total_meaningful_text > 500:
        return True

    return False

def analyze_page_quality(page_text):
    """Анализ качества текста на странице"""
    result = {
        'is_good': False,
        'meaningful_chars': 0,
        'has_structure': False
    }

    clean_text = page_text.replace('\n', ' ').replace('\t', ' ')
    clean_text = ' '.join(clean_text.split())

    if len(clean_text) < 20:
        return result

    total_chars = len(clean_text.replace(' ', ''))
    if total_chars == 0:
        return result

    readable_chars = sum(1 for c in clean_text if c.isalnum())
    readable_ratio = readable_chars / total_chars if total_chars > 0 else 0

    special_chars = sum(1 for c in clean_text if not c.isalnum() and not c.isspace())
    special_ratio = special_chars / total_chars if total_chars > 0 else 0

    char_counts = {}
    for c in clean_text[:500]:
        if not c.isspace():
            char_counts[c] = char_counts.get(c, 0) + 1

    max_repeats = max(char_counts.values()) if char_counts else 0
    if max_repeats > 50:
        return result

    for char, count in char_counts.items():
        if count > 30 and not char.isalnum():
            return result

    words = [word for word in clean_text.split() if len(word.strip()) > 0]
    meaningful_words = 0
    total_word_length = 0

    for word in words:
        clean_word = ''.join(c for c in word if c.isalnum())
        if len(clean_word) >= 2:
            if any(c.isalpha() for c in clean_word):
                meaningful_words += 1
                total_word_length += len(clean_word)

    meaningful_ratio = meaningful_words / len(words) if words else 0
    avg_word_length = total_word_length / meaningful_words if meaningful_words > 0 else 0

    has_structure = has_text_structure(clean_text)

    is_good = (
        readable_ratio > 0.3 and
        special_ratio < 0.7 and
        meaningful_ratio > 0.15 and
        2 <= avg_word_length <= 15 and
        (has_structure or meaningful_words > 10)
    )

    result['is_good'] = is_good
    result['meaningful_chars'] = readable_chars
    result['has_structure'] = has_structure

    return result

def has_text_structure(text):
    """Проверка наличия структурированного текста"""
    lines = text.split('\n')

    table_indicators = ['|', '\t']
    table_lines = 0
    for line in lines:
        if any(indicator in line for indicator in table_indicators):
            table_lines += 1

    if table_lines > 2:
        return True

    list_indicators = [' - ', ' • ', ' 1. ', ' 2. ', ' 3. ']
    list_lines = 0
    for line in lines:
        if any(indicator in line for indicator in list_indicators):
            list_lines += 1

    if list_lines > 3:
        return True

    uppercase_lines = 0
    for line in lines:
        clean_line = ''.join(c for c in line if c.isalpha())
        if len(clean_line) > 3 and clean_line.isupper():
            uppercase_lines += 1

    if uppercase_lines > 1:
        return True

    return False

def main():
    print("🚀 Тест новой системы анализа качества текста PDF\n")

    # Тестируем на проблемном файле
    test_file = "data/attachments/2025-07-11/20250711_dna-technology_ru_73424a0e_161536_attach_D043-02_ПРОБА-МЧ-РАПИД-II_2025-03-07.pdf"

    if os.path.exists(test_file):
        test_pdf_quality(test_file)
    else:
        print(f"⚠️ Файл не найден: {test_file}")

if __name__ == "__main__":
    main()
