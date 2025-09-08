#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Сравнение Варианта 1 и Варианта 2 промптов для Фазы 2
Тестируем оба подхода к промптам на одинаковых данных
"""

import sys
import os
import json
import time
sys.path.append('src')

from llm_extractor import ContactExtractor

def test_prompt_variants():
    """Сравнение двух вариантов промптов"""
    print("🧪 Сравнение вариантов промптов для Фазы 2...")

    # Создаем экстрактор
    extractor = ContactExtractor(test_mode=False)

    # Тестовый текст с коммерческим предложением
    test_text = """
    Уважаемый Иван Петрович!

    Меня зовут Анна Сергеевна, я менеджер по продажам ООО "МедТехника".
    Телефон: +7 (495) 123-45-67 доб. 123
    Email: a.sergeeva@medteh.ru

    Пишу по поводу вашего запроса на поставку лабораторного оборудования.

    Мы можем предложить:
    - Амплификатор DNA Pro, 2 шт. по 150 000 руб.
    - Реагенты для ПЦР, 500 000 руб.
    Итого: 800 000 руб. (без НДС)

    Срок поставки - 30 дней.
    Условия оплаты: 50% предоплата, 50% после поставки.

    С уважением,
    Анна Сергеевна
    ООО "МедТехника"
    г. Москва
    """

    results = {}

    print("\n📋 ТЕСТИРУЕМ ВАРИАНТ 1: Разделители")
    print("=" * 50)

    # Меняем промпт на Вариант 1
    original_load = extractor._load_prompt
    extractor._load_prompt = lambda filename: original_load("unified_contact_extraction.txt") if filename == "unified_contact_extraction.txt" else original_load(filename)

    try:
        start_time = time.time()
        result1 = extractor.extract_all_data(test_text)
        time1 = time.time() - start_time

        print(".2f")
        print(f"📊 Контактов: {len(result1.get('contacts', []))}")
        print(f"💼 КП: {len(result1.get('commercial_offers', []))}")
        print(f"📝 Бизнес-контекст: {result1.get('business_context', '')[:100]}...")

        results['variant1'] = {
            'result': result1,
            'time': time1,
            'success': True
        }

    except Exception as e:
        print(f"❌ Ошибка Варианта 1: {e}")
        results['variant1'] = {'success': False, 'error': str(e)}

    print("\n🏗️ ТЕСТИРУЕМ ВАРИАНТ 2: Структурированный")
    print("=" * 50)

    # Меняем промпт на Вариант 2
    extractor._load_prompt = lambda filename: original_load("unified_contact_extraction_structured.txt") if filename == "unified_contact_extraction.txt" else original_load(filename)

    try:
        start_time = time.time()
        result2 = extractor.extract_all_data(test_text)
        time2 = time.time() - start_time

        print(".2f")
        print(f"📊 Контактов: {len(result2.get('contacts', []))}")
        print(f"💼 КП: {len(result2.get('commercial_offers', []))}")
        print(f"📝 Бизнес-контекст: {result2.get('business_context', '')[:100]}...")

        results['variant2'] = {
            'result': result2,
            'time': time2,
            'success': True
        }

    except Exception as e:
        print(f"❌ Ошибка Варианта 2: {e}")
        results['variant2'] = {'success': False, 'error': str(e)}

    # Сравнение результатов
    print("\n📈 АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("=" * 60)

    if results.get('variant1', {}).get('success') and results.get('variant2', {}).get('success'):
        time1 = results['variant1']['time']
        time2 = results['variant2']['time']

        print("⏱️ СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ:")
        print(".2f")
        print(".2f")
        print(".3f")

        # Сравнение качества
        contacts1 = len(results['variant1']['result'].get('contacts', []))
        contacts2 = len(results['variant2']['result'].get('contacts', []))
        offers1 = len(results['variant1']['result'].get('commercial_offers', []))
        offers2 = len(results['variant2']['result'].get('commercial_offers', []))

        print("\n📊 СРАВНЕНИЕ КАЧЕСТВА:")
        print(f"Контакты: В1={contacts1}, В2={contacts2}")
        print(f"КП: В1={offers1}, В2={offers2}")

        # Определяем победителя
        if abs(time1 - time2) < 1.0 and contacts1 == contacts2 and offers1 == offers2:
            print("\n🤝 ВАРИАНТЫ РАВНОЦЕННЫ!")
        elif time1 < time2 and contacts1 >= contacts2 and offers1 >= offers2:
            print("\n🏆 ВАРИАНТ 1 ЛУЧШЕ!")
        elif time2 < time1 and contacts2 >= contacts1 and offers2 >= offers1:
            print("\n🏆 ВАРИАНТ 2 ЛУЧШЕ!")
        else:
            print("\n🤔 НУЖЕН РУЧНОЙ АНАЛИЗ РЕЗУЛЬТАТОВ")
    else:
        print("⚠️ Один из вариантов не прошел тестирование")

    # Сохранение результатов для детального анализа
    with open('prompt_comparison_phase2.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n💾 Результаты сохранены в prompt_comparison_phase2.json")
    return results

if __name__ == "__main__":
    results = test_prompt_variants()
