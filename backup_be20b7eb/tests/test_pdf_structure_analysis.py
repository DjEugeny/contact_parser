#!/usr/bin/env python3
"""
Тест нового метода анализа структуры PDF для определения текстового слоя
"""

import sys
import os
from pathlib import Path

# Имитируем необходимые компоненты
class MockOCRProcessor:
    def __init__(self):
        pass

    def _analyze_pdf_structure(self, pdf_path: Path) -> dict:
        """
        Глубокий анализ структуры PDF для определения наличия качественного текстового слоя.
        """
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
            import fitz  # PyMuPDF

            doc = fitz.open(str(pdf_path))
            total_text_chars = 0
            total_image_area = 0
            total_page_area = 0

            print(f"📄 Анализ PDF: {len(doc)} страниц(ы)")

            for page_num in range(min(len(doc), 3)):  # Анализируем первые 3 страницы
                page = doc[page_num]
                page_area = page.rect.width * page.rect.height
                total_page_area += page_area

                # Извлекаем текст
                text = page.get_text()
                total_text_chars += len(text)
                print(f"  Страница {page_num + 1}: {len(text)} символов текста")

                # Анализируем объекты страницы
                text_blocks = page.get_text("dict")
                page_text_objects = len(text_blocks.get('blocks', []))
                result['text_objects_count'] += page_text_objects
                print(f"  Страница {page_num + 1}: {page_text_objects} текстовых объектов")

                # Анализируем изображения
                images = page.get_images(full=True)
                page_images = len(images)
                result['image_objects_count'] += page_images
                print(f"  Страница {page_num + 1}: {page_images} изображений")

                # Анализируем шрифты
                fonts = page.get_fonts()
                print(f"  Страница {page_num + 1}: найдено {len(fonts)} шрифтов")
                for font in fonts:
                    if font and len(font) > 3:
                        font_name = font[3] if isinstance(font[3], str) else str(font[3])
                        result['font_types'].add(font_name)
                        print(f"    Шрифт: {font_name}")

            doc.close()

            # Вычисляем соотношения
            if total_page_area > 0:
                result['text_to_image_ratio'] = total_image_area / total_page_area

            # Определяем наличие embedded шрифтов
            embedded_fonts = [f for f in result['font_types'] if not f.startswith(('Times', 'Helvetica', 'Courier', 'Symbol', 'ZapfDingbats'))]
            result['has_embedded_fonts'] = len(embedded_fonts) > 0

            # Общее количество объектов
            result['total_objects'] = result['text_objects_count'] + result['image_objects_count']

            print("\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
            print(f"  Всего символов текста: {total_text_chars}")
            print(f"  Общая площадь страниц: {total_page_area:.0f}")
            print(f"  Соотношение изображений: {result['text_to_image_ratio']:.3f}")
            print(f"  Текстовых объектов: {result['text_objects_count']}")
            print(f"  Изображений: {result['image_objects_count']}")
            print(f"  Embedded шрифты: {result['has_embedded_fonts']}")
            print(f"  Типы шрифтов: {list(result['font_types'])}")

            # Определяем наличие качественного текстового слоя
            has_significant_text = total_text_chars > 500  # Минимум 500 символов текста
            has_low_image_ratio = result['text_to_image_ratio'] < 0.3  # Менее 30% площади занимают изображения
            has_good_object_ratio = result['text_objects_count'] > result['image_objects_count']  # Больше текстовых объектов чем изображений
            has_embedded_fonts = result['has_embedded_fonts']

            result['has_text_layer'] = has_significant_text and (has_low_image_ratio or has_embedded_fonts or has_good_object_ratio)

            print("\n🔍 КРИТЕРИИ:")
            print(f"  Значительный текст (>500 символов): {has_significant_text}")
            print(f"  Низкое соотношение изображений (<30%): {has_low_image_ratio}")
            print(f"  Преобладание текстовых объектов: {has_good_object_ratio}")
            print(f"  Embedded шрифты: {has_embedded_fonts}")

            # Вычисляем общий structural score (0-100)
            score = 0
            if has_significant_text: score += 40
            if has_low_image_ratio: score += 30
            if has_good_object_ratio: score += 20
            if has_embedded_fonts: score += 10

            result['structure_score'] = min(100, score)

            # Определяем уверенность в наличии текстового слоя
            if result['has_text_layer'] and result['structure_score'] > 70:
                result['text_confidence'] = 0.9
            elif result['has_text_layer'] and result['structure_score'] > 50:
                result['text_confidence'] = 0.7
            elif result['has_text_layer']:
                result['text_confidence'] = 0.5
            else:
                result['text_confidence'] = 0.1

            print("\n✅ ВЫВОД:")
            print(f"  Наличие текстового слоя: {result['has_text_layer']}")
            print(f"  Structural score: {result['structure_score']}/100")
            print(f"  Уверенность: {result['text_confidence']:.1f}")

        except Exception as e:
            result['error'] = str(e)
            result['has_text_layer'] = False
            result['text_confidence'] = 0.0
            print(f"❌ Ошибка анализа: {e}")

        return result

def analyze_pdf_file(pdf_path: str):
    """Анализ конкретного PDF файла"""
    if not os.path.exists(pdf_path):
        print(f"❌ Файл не найден: {pdf_path}")
        return

    processor = MockOCRProcessor()
    print(f"🔍 Анализ файла: {pdf_path}")
    print("=" * 60)

    try:
        result = processor._analyze_pdf_structure(Path(pdf_path))
        print("=" * 60)
        return result
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

if __name__ == "__main__":
    # Анализируем проблемные файлы за 2 июля
    files_to_analyze = [
        "data/attachments/2025-07-02/20250702_dna-technology_ru_60c0538b_075414_attach_7684.pdf",
        "data/attachments/2025-07-02/20250702_dna-technology_ru_c96fcd46_075358_attach_КП 7649 от 02.07.2025.pdf"
    ]

    for pdf_file in files_to_analyze:
        analyze_pdf_file(pdf_file)
        print("\n" + "=" * 80 + "\n")
