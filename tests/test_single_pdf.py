#!/usr/bin/env python3
"""
Тест обработки одиночного PDF файла
"""

import sys
import os

# Добавляем src в путь
sys.path.insert(0, 'src')

# Имитируем необходимые константы
OPENPYXL_AVAILABLE = True
XLRD_AVAILABLE = True
PYTHON_DOCX_AVAILABLE = True

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

class MockOCRProcessor:
    """Мок класс для тестирования"""

    def _is_text_quality_good(self, text):
        """
        Улучшенная оценка качества извлеченного текста из PDF.
        Различает качественный текст от мусора, игнорирует картинки и диаграммы.
        """
        if not text or len(text) < 50:
            return False

        # Разделяем текст на страницы для анализа
        pages = text.split('\n\n')
        if len(pages) == 0:
            return False

        # Анализируем каждую страницу отдельно
        good_pages = 0
        total_meaningful_text = 0

        for page_text in pages:
            if len(page_text.strip()) < 20:  # Пропускаем пустые или слишком короткие страницы
                continue

            page_analysis = self._analyze_page_quality(page_text)
            if page_analysis['is_good']:
                good_pages += 1
                total_meaningful_text += page_analysis['meaningful_chars']

        # Если хотя бы одна страница содержит качественный текст - считаем документ хорошим
        if good_pages > 0:
            return True

        # Дополнительная проверка: если есть значительный объем осмысленного текста
        if total_meaningful_text > 500:  # Минимум 500 символов осмысленного текста
            return True

        return False

    def _analyze_page_quality(self, page_text):
        """
        Анализирует качество текста на отдельной странице PDF.
        """
        result = {
            'is_good': False,
            'meaningful_chars': 0,
            'has_structure': False
        }

        # Очищаем текст от лишних пробелов
        clean_text = page_text.replace('\n', ' ').replace('\t', ' ')
        clean_text = ' '.join(clean_text.split())  # Убираем множественные пробелы

        if len(clean_text) < 20:
            return result

        # Подсчет различных типов символов
        total_chars = len(clean_text.replace(' ', ''))
        if total_chars == 0:
            return result

        # Считаем читаемые символы (буквы и цифры)
        readable_chars = sum(1 for c in clean_text if c.isalnum())
        readable_ratio = readable_chars / total_chars if total_chars > 0 else 0

        # Считаем специальные символы (знаки препинания и другие)
        special_chars = sum(1 for c in clean_text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / total_chars if total_chars > 0 else 0

        # Проверяем на наличие повторяющихся символов (характерно для мусора)
        char_counts = {}
        for c in clean_text[:500]:  # Проверяем первые 500 символов
            if not c.isspace():
                char_counts[c] = char_counts.get(c, 0) + 1

        # Если какой-то символ повторяется более 30 раз подряд или > 50 раз всего - это мусор
        max_repeats = max(char_counts.values()) if char_counts else 0
        if max_repeats > 50:
            return result

        # Проверяем на последовательные повторения одного символа
        for char, count in char_counts.items():
            if count > 30 and not char.isalnum():  # Не буквенно-цифровые символы
                return result

        # Проверяем наличие осмысленных слов
        words = [word for word in clean_text.split() if len(word.strip()) > 0]
        meaningful_words = 0
        total_word_length = 0

        for word in words:
            # Очищаем слово от знаков препинания
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) >= 2:  # Слово должно быть не короче 2 символов
                # Проверяем, что слово содержит хотя бы одну букву
                if any(c.isalpha() for c in clean_word):
                    meaningful_words += 1
                    total_word_length += len(clean_word)

        # Рассчитываем соотношения
        meaningful_ratio = meaningful_words / len(words) if words else 0
        avg_word_length = total_word_length / meaningful_words if meaningful_words > 0 else 0

        # Проверяем наличие структурированного текста (таблицы, списки)
        has_structure = self._has_text_structure(clean_text)

        # Критерии качественного текста:
        # 1. Достаточное количество читаемых символов (> 30%)
        # 2. Не слишком много специальных символов (< 70%)
        # 3. Достаточное количество осмысленных слов (> 15%)
        # 4. Средняя длина слова разумная (2-15 символов)
        # 5. Наличие структуры (таблицы, списки)

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

    def _has_text_structure(self, text):
        """
        Проверяет наличие структурированного текста (таблицы, списки, заголовки).
        """
        lines = text.split('\n')

        # Проверяем на наличие таблиц (строки с разделителями | или табуляциями)
        table_indicators = ['|', '\t']
        table_lines = 0
        for line in lines:
            if any(indicator in line for indicator in table_indicators):
                table_lines += 1

        if table_lines > 2:  # Более 2 строк с разделителями - вероятно таблица
            return True

        # Проверяем на наличие списков (маркеры: -, •, цифры с точкой)
        list_indicators = [' - ', ' • ', ' 1. ', ' 2. ', ' 3. ']
        list_lines = 0
        for line in lines:
            if any(indicator in line for indicator in list_indicators):
                list_lines += 1

        if list_lines > 3:  # Более 3 строк со списком - вероятно структурированный текст
            return True

        # Проверяем на наличие заголовков (ВСЕ ЗАГЛАВНЫЕ БУКВЫ)
        uppercase_lines = 0
        for line in lines:
            clean_line = ''.join(c for c in line if c.isalpha())
            if len(clean_line) > 3 and clean_line.isupper():
                uppercase_lines += 1

        if uppercase_lines > 1:  # Более 1 заголовка - структурированный текст
            return True

        return False

def main():
    print("🧪 Тест обработки одиночного PDF файла\n")

    if not PYMUPDF_AVAILABLE:
        print("❌ PyMuPDF не доступен")
        return

    processor = MockOCRProcessor()

    file_path = "data/attachments/2025-07-11/20250711_dna-technology_ru_73424a0e_161536_attach_D043-02_ПРОБА-МЧ-РАПИД-II_2025-03-07.pdf"

    if not os.path.exists(file_path):
        print(f"⚠️ Файл не найден: {file_path}")
        return

    print(f"📄 Обрабатываем файл: {os.path.basename(file_path)}")

    # Имитируем логику из ocr_processor.py
    doc = fitz.open(file_path)
    texts = [page.get_text() for page in doc]
    full_text_direct = "\n\n".join(texts).strip()

    print(f"📝 Извлечено текста: {len(full_text_direct)} символов")
    print(f"📄 Страниц: {len(doc)}")

    # Проверяем качество текста
    quality_check = len(full_text_direct) > 100 and processor._is_text_quality_good(full_text_direct)
    print(f"\n🔍 Отладка: len(text)={len(full_text_direct)} > 100 = {len(full_text_direct) > 100}")
    print(f"🔍 Отладка: _is_text_quality_good() = {processor._is_text_quality_good(full_text_direct)}")
    print(f"🔍 Отладка: финальное условие = {quality_check}")

    if quality_check:
        print("✅ Файл будет обработан ЛОКАЛЬНО")
    else:
        print("❌ Файл будет отправлен в Google Vision")

    doc.close()

if __name__ == "__main__":
    main()
