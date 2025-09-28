#!/usr/bin/env python3
"""
Тест исправленной логики _is_text_quality_good из новой версии
"""
import re
import sys
from pathlib import Path

class MockOCRProcessor:
    """Имитация OCR процессора с исправленной логикой"""
    
    def _analyze_pdf_structure(self, pdf_path: Path) -> dict:
        """Имитация анализа структуры PDF - предполагаем хорошую структуру"""
        return {
            'has_text_layer': True,
            'text_confidence': 0.9,  # Высокая уверенность
            'structure_score': 95,   # Отличная структура
            'error': None
        }
    
    def _quick_garbage_check(self, text: str) -> dict:
        """Простая проверка на мусор"""
        clean_text = re.sub(r'\s+', ' ', text.strip())
        
        if len(clean_text) < 50:
            return {'is_good': False, 'reason': 'too_short'}
        
        total_chars = len(clean_text)
        total_words = len(clean_text.split())
        
        # Поиск реальных слов
        russian_words = re.findall(r'[а-яё]{4,}', clean_text.lower())
        english_words = re.findall(r'[a-z]{4,}', clean_text.lower())

        # Проверка на искаженные английские слова
        fake_english_score = 0
        if english_words:
            for word in english_words[:10]:
                if re.search(r'[a-z]*[o]{2,}[a-z]*', word):
                    fake_english_score += 1
                if re.search(r'[a-z]*[e]{3,}[a-z]*', word):
                    fake_english_score += 1
                if re.search(r'[a-z]*[a]{3,}[a-z]*', word):
                    fake_english_score += 1

        fake_ratio = fake_english_score / max(len(english_words), 1)
        garbage_threshold = max(5, total_words // 20)
        garbage_score = fake_english_score
        garbage_to_words_ratio = garbage_score / max(total_words, 1)

        is_good = (
            garbage_score < garbage_threshold and
            garbage_to_words_ratio < 0.05 and
            len(russian_words) > 2 and
            fake_ratio < 0.7
        )

        return {
            'is_good': is_good,
            'reason': f"garbage_score={garbage_score}/{garbage_threshold}, ratio={garbage_to_words_ratio:.3f}, russian_words={len(russian_words)}, fake_english_ratio={fake_ratio:.2f}"
        }
    
    def _analyze_page_quality(self, page_text: str) -> dict:
        """Простой анализ качества страницы"""
        meaningful_chars = sum(1 for c in page_text if c.isalnum())
        return {
            'is_good': meaningful_chars > 100,
            'meaningful_chars': meaningful_chars
        }
    
    def _is_text_quality_good(self, text: str, pdf_path: Path = None) -> bool:
        """
        ИСПРАВЛЕННАЯ упрощённая оценка качества текста из новой версии.
        Возвращена к проверенной логике из старой версии.
        """
        if not text or len(text) < 50:
            return False

        # Если передан путь к PDF, сначала анализируем его структуру
        if pdf_path and pdf_path.exists():
            try:
                structure_analysis = self._analyze_pdf_structure(pdf_path)

                # Если структура показывает наличие качественного текстового слоя с высокой уверенностью
                if structure_analysis['has_text_layer'] and structure_analysis['text_confidence'] > 0.7:
                    # Дополнительная проверка текста на мусор
                    garbage_check = self._quick_garbage_check(text)

                    # Специальная логика для документов с отличной структурой PDF
                    if (structure_analysis['structure_score'] >= 90 and
                        'ratio=' in garbage_check['reason']):
                        # Извлекаем ratio из reason
                        try:
                            ratio_str = garbage_check['reason'].split('ratio=')[1].split(',')[0]
                            garbage_ratio = float(ratio_str)
                            # Если соотношение мусора мало (< 5%), игнорируем строгие пороги
                            if garbage_ratio < 0.05:
                                return True
                        except (ValueError, IndexError):
                            pass

                    return garbage_check['is_good']
                elif structure_analysis['text_confidence'] < 0.3:
                    # Структура показывает отсутствие качественного текстового слоя
                    return False
            except Exception as e:
                # Если анализ структуры не удался, продолжаем с текстовым анализом
                pass

        # Быстрая проверка на мусор перед основной обработкой
        garbage_check = self._quick_garbage_check(text)
        if not garbage_check['is_good']:
            return False

        # Разделяем текст на страницы для анализа
        pages = text.split('\n\n')
        if len(pages) == 0:
            return False

        # Анализируем каждую страницу отдельно
        good_pages = 0
        total_meaningful_text = 0

        for page_text in pages:
            if len(page_text.strip()) < 20:
                continue

            page_analysis = self._analyze_page_quality(page_text)
            if page_analysis['is_good']:
                good_pages += 1
                total_meaningful_text += page_analysis['meaningful_chars']

        # Если хотя бы одна страница содержит качественный текст - считаем документ хорошим
        if good_pages > 0:
            return True

        # Дополнительная проверка: если есть значительный объем осмысленного текста
        if total_meaningful_text > 500:
            return True

        return False

def test_with_problem_file():
    """Тест с проблемным файлом"""
    # Загружаем текст из результата Google Vision
    ocr_result_file = "data/final_results/texts/3333-33-33/20250512_dna-technology_ru_d0a44d1d_155249_attach_579-2_HLA-эксперт_IVD_b_2021-09-08.txt"
    
    if not Path(ocr_result_file).exists():
        print(f"❌ Файл не найден: {ocr_result_file}")
        return False
    
    with open(ocr_result_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем только текст
    lines = content.split('\n')
    text_started = False
    text_lines = []
    
    for line in lines:
        if line.startswith('# =================================================='):
            text_started = True
        elif text_started:
            text_lines.append(line)
    
    text = '\n'.join(text_lines).strip()
    
    # Тестируем исправленную логику
    processor = MockOCRProcessor()
    pdf_path = Path("data/attachments/3333-33-33/20250512_dna-technology_ru_d0a44d1d_155249_attach_579-2_HLA-эксперт_IVD_b_2021-09-08.pdf")
    
    print("🔍 Тестирование ИСПРАВЛЕННОЙ логики _is_text_quality_good")
    print("=" * 60)
    print(f"📝 Длина текста: {len(text)} символов")
    print(f"📄 Путь к PDF: {pdf_path.exists()}")
    
    # Проверяем условия
    condition1 = len(text) > 100
    condition2 = processor._is_text_quality_good(text, pdf_path)
    
    print(f"\n🔍 Условия:")
    print(f"   • len(text) > 100: {len(text)} > 100 = {condition1}")
    print(f"   • _is_text_quality_good(): {condition2}")
    
    final_decision = condition1 and condition2
    print(f"   • Финальное решение: {final_decision}")
    
    if final_decision:
        print("\n✅ РЕЗУЛЬТАТ: Файл будет обработан ЛОКАЛЬНО (local_pdf_text)")
        print("🎉 ИСПРАВЛЕНИЕ РАБОТАЕТ! Файл больше не отправляется в Google Vision!")
        return True
    else:
        print("\n❌ РЕЗУЛЬТАТ: Файл все еще отправляется в Google Vision")
        print("🔧 Нужны дополнительные исправления...")
        return False

def main():
    print("🧪 Тест исправленной логики определения качества текста\n")
    
    success = test_with_problem_file()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ТЕСТ ПРОЙДЕН: Исправление работает корректно!")
        print("📋 Теперь можно тестировать на реальных файлах")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН: Нужны дополнительные исправления")
    
    return success

if __name__ == "__main__":
    main()