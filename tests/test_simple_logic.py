#!/usr/bin/env python3
"""
Тест простой логики выбора метода для проблемного PDF файла
"""
import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.append(str(Path(__file__).parent / "src"))

# Проверяем доступность PyMuPDF
try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    print("❌ PyMuPDF не доступен")
    PYMUPDF_AVAILABLE = False
    exit(1)

# Имитируем часть класса OCRProcessor для тестирования логики
class TestOCRProcessor:
    def __init__(self):
        pass
    
    def _analyze_pdf_structure(self, pdf_path: Path) -> dict:
        """Простой анализ структуры PDF"""
        result = {
            'has_text_layer': False,
            'text_to_image_ratio': 0.0,
            'has_embedded_fonts': False,
            'text_objects_count': 0,
            'image_objects_count': 0,
            'total_objects': 0,
            'font_types': set(),
            'text_confidence': 0.0,
            'structure_score': 0.0
        }

        try:
            doc = fitz.open(str(pdf_path))
            total_text_chars = 0
            total_image_area = 0
            total_page_area = 0

            for page_num in range(min(len(doc), 3)):  # Анализируем первые 3 страницы
                page = doc[page_num]
                page_area = page.rect.width * page.rect.height
                total_page_area += page_area

                # Извлекаем текст
                text = page.get_text()
                total_text_chars += len(text)

                # Подсчитываем изображения
                image_list = page.get_images()
                for img in image_list:
                    total_image_area += 1000  # Примерная площадь

                # Анализируем объекты на странице
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    if "lines" in block:
                        result['text_objects_count'] += len(block["lines"])

            # Вычисляем метрики
            result['text_to_image_ratio'] = total_image_area / max(total_page_area, 1)
            result['has_text_layer'] = total_text_chars > 50
            
            # Простое определение качества
            if total_text_chars > 1000:
                result['structure_score'] = 90
                result['text_confidence'] = 0.9
            elif total_text_chars > 200:
                result['structure_score'] = 70
                result['text_confidence'] = 0.7
            else:
                result['structure_score'] = 30
                result['text_confidence'] = 0.3

            doc.close()

        except Exception as e:
            result['error'] = str(e)
            result['has_text_layer'] = False
            result['text_confidence'] = 0.0

        return result
    
    def _quick_garbage_check(self, text: str) -> dict:
        """Простая проверка на мусор"""
        import re
        
        total_chars = len(text)
        if total_chars < 50:
            return {'is_good': False, 'reason': 'too_short'}
        
        # Считаем читаемые символы
        readable_chars = sum(1 for c in text if c.isalnum())
        readable_ratio = readable_chars / total_chars
        
        # Простые критерии
        is_good = readable_ratio > 0.3
        
        return {
            'is_good': is_good,
            'reason': f'readable_ratio={readable_ratio:.3f}'
        }
    
    def _analyze_page_quality(self, page_text: str) -> dict:
        """Простой анализ качества страницы"""
        meaningful_chars = sum(1 for c in page_text if c.isalnum())
        return {
            'is_good': meaningful_chars > 100,
            'meaningful_chars': meaningful_chars
        }
    
    def _is_text_quality_good(self, text: str, pdf_path: Path = None) -> bool:
        """Упрощённая оценка качества текста из старой версии"""
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

def test_pdf_file(file_path: str):
    """Тестирование конкретного PDF файла"""
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return

    processor = TestOCRProcessor()
    print(f"🔍 Анализ файла: {os.path.basename(file_path)}")
    print("=" * 60)

    # Извлекаем текст
    doc = fitz.open(file_path)
    texts = [page.get_text() for page in doc]
    full_text_direct = "\n\n".join(texts).strip()
    doc.close()

    print(f"📝 Извлечено текста: {len(full_text_direct)} символов")
    print(f"📄 Первые 200 символов:\n{full_text_direct[:200]}...")

    # Анализируем структуру
    structure = processor._analyze_pdf_structure(Path(file_path))
    print(f"\n📊 Структурный анализ:")
    print(f"   • has_text_layer: {structure['has_text_layer']}")
    print(f"   • text_confidence: {structure['text_confidence']:.2f}")
    print(f"   • structure_score: {structure['structure_score']}")

    # Проверяем качество
    is_quality_good = len(full_text_direct) > 100 and processor._is_text_quality_good(full_text_direct, Path(file_path))
    
    print(f"\n🔍 Условия:")
    print(f"   • len(text) > 100: {len(full_text_direct) > 100}")
    print(f"   • _is_text_quality_good(): {processor._is_text_quality_good(full_text_direct, Path(file_path))}")
    print(f"   • Финальное решение: {is_quality_good}")

    if is_quality_good:
        print("\n✅ Файл будет обработан ЛОКАЛЬНО (local_pdf_text)")
    else:
        print("\n❌ Файл будет отправлен в GOOGLE VISION (google_vision_pdf_optimized)")

def main():
    print("🧪 Тест упрощённой логики выбора метода OCR\n")

    # Проблемный файл
    problem_file = "data/attachments/3333-33-33/20250512_dna-technology_ru_d0a44d1d_155249_attach_579-2_HLA-эксперт_IVD_b_2021-09-08.pdf"
    
    if os.path.exists(problem_file):
        test_pdf_file(problem_file)
    else:
        print(f"❌ Проблемный файл не найден: {problem_file}")

if __name__ == "__main__":
    main()