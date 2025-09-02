#!/usr/bin/env python3
"""
Тест для обнаружения мусорного текста в PDF файлах
"""

import re
import sys
import os

# Имитируем необходимые компоненты
class MockOCRProcessor:
    def __init__(self):
        pass

    def _analyze_text_patterns(self, text: str) -> dict:
        """Анализ паттернов в тексте для выявления мусора"""
        patterns = {
            'ocr_garbage': r'[a-z]{2,}[0-9]{2,}[a-z]*',  # типичные OCR ошибки
            'letter_substitution': r'[a-z]{3,}[A-Z]{1,}[a-z]*',  # замена букв
            'symbol_mess': r'[<>(){}[\]]{2,}',  # скобки и символы
            'repeated_chars': r'(.)\1{3,}',  # повторяющиеся символы
            'mixed_encoding': r'[\u0080-\u00FF]{3,}',  # смешанная кодировка
        }

        results = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, text)
            results[name] = len(matches)

        return results

    def _calculate_text_entropy(self, text: str) -> float:
        """Расчет энтропии текста (мусор имеет высокую энтропию)"""
        if not text:
            return 0

        # Убираем пробелы и считаем частоты символов
        clean_text = ''.join(c for c in text if c.isalnum())
        if not clean_text:
            return 0

        char_counts = {}
        for c in clean_text:
            char_counts[c] = char_counts.get(c, 0) + 1

        total_chars = len(clean_text)
        entropy = 0
        for count in char_counts.values():
            p = count / total_chars
            if p > 0:
                entropy -= p * (p ** 0.5)  # упрощенная энтропия

        return entropy

    def _detect_real_words(self, text: str) -> dict:
        """Поиск реальных слов в тексте"""
        # Русские слова (минимум 3 буквы)
        russian_words = re.findall(r'[а-яё]{3,}', text.lower())
        # Английские слова (минимум 3 буквы)
        english_words = re.findall(r'[a-z]{3,}', text.lower())

        return {
            'russian_words': len(russian_words),
            'english_words': len(english_words),
            'total_words': len(russian_words) + len(english_words)
        }

    def _is_text_quality_good_improved(self, text: str) -> tuple:
        """Улучшенная функция определения качества текста"""
        if not text or len(text) < 50:
            return False, "Текст слишком короткий"

        # Анализ паттернов мусора
        patterns = self._analyze_text_patterns(text)
        garbage_score = sum(patterns.values())

        # Расчет энтропии
        entropy = self._calculate_text_entropy(text)

        # Поиск реальных слов
        words = self._detect_real_words(text)

        # Дополнительные проверки
        clean_text = re.sub(r'\s+', ' ', text)
        total_chars = len(clean_text.replace(' ', ''))

        # Проверка на процент читаемых символов
        readable_chars = sum(1 for c in clean_text if c.isalnum() or c in ' .,;:!?()[]{}"\'-')
        readable_ratio = readable_chars / max(len(clean_text), 1)

        # Проверка на повторяющиеся паттерны
        lines = text.split('\n')
        similar_lines = 0
        for i in range(len(lines) - 1):
            for j in range(i + 1, len(lines)):
                if len(lines[i]) > 10 and len(lines[j]) > 10:
                    # Простая проверка на схожесть
                    common_chars = sum(1 for a, b in zip(lines[i], lines[j]) if a == b)
                    if common_chars / max(len(lines[i]), len(lines[j])) > 0.8:
                        similar_lines += 1

        # Критерии качества
        is_good = (
            garbage_score < 5 and  # мало мусорных паттернов
            entropy < 0.8 and      # низкая энтропия (структурированный текст)
            words['total_words'] > 5 and  # достаточно реальных слов
            readable_ratio > 0.6 and     # большинство символов читаемые
            similar_lines < len(lines) * 0.3  # не слишком много похожих строк
        )

        reason = f"garbage_score={garbage_score}, entropy={entropy:.2f}, words={words['total_words']}, readable={readable_ratio:.2f}, similar_lines={similar_lines}"

        return is_good, reason

def test_file_quality(file_path: str):
    """Тестирование качества файла"""
    processor = MockOCRProcessor()

    print(f"🔍 Анализ файла: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Пропускаем заголовок
        lines = content.split('\n')
        text_start = 0
        for i, line in enumerate(lines):
            if line.startswith('# =================================================='):
                text_start = i + 1
                break

        actual_text = '\n'.join(lines[text_start:])

        print("📊 Анализ паттернов мусора:")
        patterns = processor._analyze_text_patterns(actual_text)
        for name, count in patterns.items():
            print(f"  {name}: {count}")

        entropy = processor._calculate_text_entropy(actual_text)
        print(f"📈 Энтропия текста: {entropy:.3f}")

        words = processor._detect_real_words(actual_text)
        print(f"📝 Реальные слова: {words}")

        is_good, reason = processor._is_text_quality_good_improved(actual_text)
        print(f"✅ Качество: {'ХОРОШЕЕ' if is_good else 'ПЛОХОЕ'}")
        print(f"📋 Причина: {reason}")

        return is_good

    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return False

if __name__ == "__main__":
    # Тестируем проблемные файлы
    files_to_test = [
        "data/final_results/texts/2025-07-03/20250703_dna-technology_ru_ac60a6b9_075514_attach_Письмо.txt",
        "data/final_results/texts/2025-07-04/20250704_dna-technology_ru_cad5b1db_075548_attach_Письмо.txt"
    ]

    for file_path in files_to_test:
        if os.path.exists(file_path):
            test_file_quality(file_path)
            print("-" * 50)
        else:
            print(f"❌ Файл не найден: {file_path}")
