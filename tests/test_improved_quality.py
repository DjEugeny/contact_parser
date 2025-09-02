#!/usr/bin/env python3
"""
Тест улучшенной функции анализа качества текста
"""

import sys
import os

# Имитируем необходимые компоненты
class MockOCRProcessor:
    def _has_text_structure(self, text):
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

    def _analyze_page_quality(self, page_text):
        """Улучшенная анализ качества текста на странице"""
        result = {
            'is_good': False,
            'meaningful_chars': 0,
            'has_structure': False,
            'language_score': 0
        }

        clean_text = page_text.replace('\n', ' ').replace('\t', ' ')
        clean_text = ' '.join(clean_text.split())

        if len(clean_text) < 50:
            return result

        total_chars = len(clean_text.replace(' ', ''))
        if total_chars == 0:
            return result

        # Расширенная проверка на мусор
        garbage_patterns = [
            r'[a-z]{2,}[0-9]{2,}[a-z]*',
            r'[<>(){}[\]]{3,}',
            r'[|@#$%^&*]{3,}',
            r'[A-Z]{5,}',
        ]

        import re
        for pattern in garbage_patterns:
            if re.search(pattern, clean_text):
                return result

        # Проверяем кодировку
        weird_chars = sum(1 for c in clean_text if ord(c) > 1000 or (ord(c) < 32 and c not in '\n\t '))
        weird_ratio = weird_chars / total_chars if total_chars > 0 else 0
        if weird_ratio > 0.1:
            return result

        readable_chars = sum(1 for c in clean_text if c.isalnum())
        readable_ratio = readable_chars / total_chars if total_chars > 0 else 0

        special_chars = sum(1 for c in clean_text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / total_chars if total_chars > 0 else 0

        # Проверяем язык
        cyrillic_chars = sum(1 for c in clean_text if ord(c) >= 1040 and ord(c) <= 1103)
        latin_chars = sum(1 for c in clean_text if c.isalpha() and ord(c) < 128)

        language_chars = cyrillic_chars + latin_chars
        language_ratio = language_chars / readable_chars if readable_chars > 0 else 0

        if language_ratio < 0.6:
            return result

        # Проверяем повторения
        char_counts = {}
        for c in clean_text[:1000]:
            if not c.isspace():
                char_counts[c] = char_counts.get(c, 0) + 1

        max_repeats = max(char_counts.values()) if char_counts else 0
        if max_repeats > 50:
            return result

        for char, count in char_counts.items():
            if count > 20 and not char.isalnum():
                return result

        # Анализируем слова
        words = [word for word in clean_text.split() if len(word.strip()) > 0]
        if len(words) < 3:
            return result

        meaningful_words = 0
        total_word_length = 0
        real_words = 0

        for word in words:
            clean_word = ''.join(c for c in word if c.isalnum())
            word_len = len(clean_word)

            if word_len >= 2:
                has_letters = any(c.isalpha() for c in clean_word)
                has_digits = any(c.isdigit() for c in clean_word)

                if has_letters:
                    meaningful_words += 1
                    total_word_length += word_len

                    if word_len <= 20 and (not has_digits or len(clean_word.replace('0123456789', '')) >= len(clean_word) * 0.3):
                        real_words += 1

        meaningful_ratio = meaningful_words / len(words) if words else 0
        real_words_ratio = real_words / len(words) if words else 0
        avg_word_length = total_word_length / meaningful_words if meaningful_words > 0 else 0

        has_structure = self._has_text_structure(clean_text)

        result['language_score'] = language_ratio

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

    def _is_text_quality_good(self, text):
        """Главная функция проверки качества"""
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

            page_analysis = self._analyze_page_quality(page_text)
            if page_analysis['is_good']:
                good_pages += 1
                total_meaningful_text += page_analysis['meaningful_chars']

        if good_pages > 0:
            return True

        if total_meaningful_text > 500:
            return True

        return False

def main():
    print("🧪 Тест улучшенной функции анализа качества текста\n")

    processor = MockOCRProcessor()

    # Тестируем на проблемном файле
    file_path = "data/attachments/2025-07-04/20250704_dna-technology_ru_cad5b1db_075548_attach_Письмо.PDF"

    if not os.path.exists(file_path):
        print(f"⚠️ Файл не найден: {file_path}")
        return

    try:
        import fitz
        doc = fitz.open(file_path)
        texts = [page.get_text() for page in doc]
        full_text = "\n\n".join(texts).strip()

        print(f"📄 Файл: {os.path.basename(file_path)}")
        print(f"📝 Извлечено текста: {len(full_text)} символов")
        print(f"📄 Страниц: {len(doc)}")

        # Проверяем качество
        quality_good = processor._is_text_quality_good(full_text)
        print(f"\n📊 Качество текста: {'ХОРОШЕЕ' if quality_good else 'ПЛОХОЕ'}")

        if not quality_good:
            print("✅ Файл будет правильно отправлен в Google Vision")
        else:
            print("❌ Файл все еще считается хорошим (нужно доработать)")

        # Детальный анализ первой страницы
        if texts:
            analysis = processor._analyze_page_quality(texts[0])
            print("\n📋 Анализ первой страницы:")
            print(f"  Качество: {'ХОРОШЕЕ' if analysis['is_good'] else 'ПЛОХОЕ'}")
            print(f"  Читаемые символы: {analysis['meaningful_chars']}")
            print(f"  Структура: {'Есть' if analysis['has_structure'] else 'Нет'}")
            print(f"  Языковой скор: {analysis.get('language_score', 0):.2%}")

        doc.close()

    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
