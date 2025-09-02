#!/usr/bin/env python3
"""
Отладка обработки PDF файла
"""

import sys
import os
from pathlib import Path

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

def is_text_quality_good(text):
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

def main():
    print("🔍 Отладка обработки PDF файла\n")

    try:
        import fitz
    except ImportError:
        print("❌ PyMuPDF не установлен")
        return

    file_path = "data/attachments/2025-07-11/20250711_dna-technology_ru_73424a0e_161536_attach_D043-02_ПРОБА-МЧ-РАПИД-II_2025-03-07.pdf"

    if not os.path.exists(file_path):
        print(f"⚠️ Файл не найден: {file_path}")
        return

    print(f"📄 Анализируем файл: {os.path.basename(file_path)}")

    # Извлекаем текст
    doc = fitz.open(file_path)
    texts = [page.get_text() for page in doc]
    full_text_direct = "\n\n".join(texts).strip()

    print(f"📝 Извлечено текста: {len(full_text_direct)} символов")
    print(f"📄 Количество страниц: {len(doc)}")

    # Проверяем условия
    print(f"\n🔍 Проверяем условия:")
    print(f"  len(full_text_direct) > 100: {len(full_text_direct)} > 100 = {len(full_text_direct) > 100}")

    quality_good = is_text_quality_good(full_text_direct)
    print(f"  is_text_quality_good(): {quality_good}")

    final_condition = len(full_text_direct) > 100 and quality_good
    print(f"  Финальное условие: {final_condition}")

    if final_condition:
        print("✅ Файл должен обрабатываться ЛОКАЛЬНО")
    else:
        print("❌ Файл будет отправлен в Google Vision")

    # Детальный анализ страниц
    print("\n📄 Детальный анализ страниц:")
    good_pages_count = 0
    for i, page_text in enumerate(texts):
        if len(page_text.strip()) > 0:
            analysis = analyze_page_quality(page_text)
            status = "✅ ХОРОШАЯ" if analysis['is_good'] else "❌ ПЛОХАЯ"
            structure = " (структурирована)" if analysis['has_structure'] else ""
            print(f"  Страница {i+1}: {len(page_text)} символов - {status}{structure}")
            if analysis['is_good']:
                good_pages_count += 1

    print(f"\n📊 Резюме: {good_pages_count} хороших страниц из {len(doc)}")

    doc.close()

if __name__ == "__main__":
    main()
