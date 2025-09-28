#!/usr/bin/env python3
"""
Диагностика проблемы с файлом 20250512_dna-technology_ru_d0a44d1d_155249_attach_579-2_HLA-эксперт_IVD_b_2021-09-08.pdf
"""
import re
from pathlib import Path

def simple_garbage_check(text: str) -> dict:
    """Упрощенная проверка на мусор из старой версии"""
    # Очищаем текст от лишних символов для анализа
    clean_text = re.sub(r'\s+', ' ', text.strip())
    
    if len(clean_text) < 50:
        return {'is_good': False, 'reason': 'too_short'}
    
    total_chars = len(clean_text)
    total_words = len(clean_text.split())
    
    # Поиск реальных слов (улучшенная версия)
    russian_words = re.findall(r'[а-яё]{4,}', clean_text.lower())  # Минимум 4 буквы
    english_words = re.findall(r'[a-z]{4,}', clean_text.lower())  # Минимум 4 буквы

    # Проверка на искаженные английские слова (замена русских букв)
    fake_english_score = 0
    if english_words:
        for word in english_words[:10]:  # Проверяем первые 10 слов
            # Проверяем на наличие паттернов замены русских букв
            if re.search(r'[a-z]*[o]{2,}[a-z]*', word):  # 'о' заменяется на 'o'
                fake_english_score += 1
            if re.search(r'[a-z]*[e]{3,}[a-z]*', word):  # 'е' заменяется на 'e'
                fake_english_score += 1
            if re.search(r'[a-z]*[a]{3,}[a-z]*', word):  # 'а' заменяется на 'a'
                fake_english_score += 1

    # Расчет процента фейковых английских слов
    fake_ratio = fake_english_score / max(len(english_words), 1)

    # Расчет адаптивного порога мусора
    garbage_threshold = max(5, total_words // 20)
    
    # Учитываем соотношение мусора к общему количеству слов
    garbage_score = fake_english_score
    garbage_to_words_ratio = garbage_score / max(total_words, 1)

    # Критерии мусора с адаптивными порогами
    is_good = (
        garbage_score < garbage_threshold and  # Адаптивный порог мусора
        garbage_to_words_ratio < 0.05 and  # Менее 5% мусора от общего количества слов
        len(russian_words) > 2 and  # Есть русские слова
        fake_ratio < 0.7  # Менее 70% английских слов являются фейковыми
    )

    return {
        'is_good': is_good,
        'reason': f"garbage_score={garbage_score}/{garbage_threshold}, ratio={garbage_to_words_ratio:.3f}, russian_words={len(russian_words)}, fake_english_ratio={fake_ratio:.2f}",
        'details': {
            'total_chars': total_chars,
            'total_words': total_words,
            'russian_words': len(russian_words),
            'english_words': len(english_words),
            'fake_english_score': fake_english_score,
            'fake_ratio': fake_ratio,
            'garbage_threshold': garbage_threshold,
            'garbage_to_words_ratio': garbage_to_words_ratio
        }
    }

def analyze_text_from_file(file_path: str):
    """Анализ текста из результирующего файла"""
    if not Path(file_path).exists():
        print(f"❌ Файл не найден: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем метод и текст
    lines = content.split('\n')
    method = None
    text_started = False
    text_lines = []
    
    for line in lines:
        if line.startswith('# ⚙️ Метод:'):
            method = line.split(':', 1)[1].strip()
        elif line.startswith('# =================================================='):
            text_started = True
        elif text_started:
            text_lines.append(line)
    
    text = '\n'.join(text_lines).strip()
    
    print(f"📁 Файл: {Path(file_path).name}")
    print(f"🔧 Метод обработки: {method}")
    print(f"📝 Длина текста: {len(text)} символов")
    print(f"📄 Первые 200 символов:")
    print(f"   {text[:200]}...")
    
    # Анализируем качество текста
    garbage_check = simple_garbage_check(text)
    
    print(f"\n🔍 Анализ качества текста:")
    print(f"   • Результат: {'✅ ХОРОШО' if garbage_check['is_good'] else '❌ ПЛОХО'}")
    print(f"   • Причина: {garbage_check['reason']}")
    
    details = garbage_check['details']
    print(f"\n📊 Детали анализа:")
    print(f"   • Общее количество символов: {details['total_chars']}")
    print(f"   • Общее количество слов: {details['total_words']}")
    print(f"   • Русские слова (≥4 букв): {details['russian_words']}")
    print(f"   • Английские слова (≥4 букв): {details['english_words']}")
    print(f"   • Фейковые английские слова: {details['fake_english_score']}")
    print(f"   • Доля фейковых английских: {details['fake_ratio']:.2%}")
    print(f"   • Порог мусора: {details['garbage_threshold']}")
    print(f"   • Отношение мусора к словам: {details['garbage_to_words_ratio']:.3f}")
    
    # Показываем критерии
    print(f"\n📏 Критерии качества:")
    print(f"   • garbage_score < garbage_threshold: {details['fake_english_score']} < {details['garbage_threshold']} = {details['fake_english_score'] < details['garbage_threshold']}")
    print(f"   • garbage_to_words_ratio < 0.05: {details['garbage_to_words_ratio']:.3f} < 0.05 = {details['garbage_to_words_ratio'] < 0.05}")
    print(f"   • russian_words > 2: {details['russian_words']} > 2 = {details['russian_words'] > 2}")
    print(f"   • fake_ratio < 0.7: {details['fake_ratio']:.2f} < 0.7 = {details['fake_ratio'] < 0.7}")
    
    return garbage_check

def main():
    print("🔍 Диагностика проблемного файла\n")
    
    # Проблемный файл
    problem_file = "data/final_results/texts/3333-33-33/20250512_dna-technology_ru_d0a44d1d_155249_attach_579-2_HLA-эксперт_IVD_b_2021-09-08.txt"
    
    print("=" * 60)
    result = analyze_text_from_file(problem_file)
    print("=" * 60)
    
    # Хороший файл для сравнения
    good_file = "data/final_results/texts/3333-33-33/20250714_dna-technology_ru_a82f46c2_081406_attach_Счет на оплату _ 8069 от 14.07.2025.txt"
    
    print("\n📋 Для сравнения - хорошо обработанный файл:")
    print("=" * 60)
    result2 = analyze_text_from_file(good_file)
    print("=" * 60)

if __name__ == "__main__":
    main()