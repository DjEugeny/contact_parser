#!/usr/bin/env python3
"""
Тестовый скрипт для проверки улучшений PreCleaner
"""

import json
import sys
import os
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fetcher.utils.precleaner_core import preclean_email_for_llm
from fetcher.utils.precleaner_adapter import PreCleanerAdapter
import yaml

def load_config():
    """Загрузка улучшенной конфигурации"""
    config_path = Path(__file__).parent.parent / 'config' / 'precleaner_improved.yaml'
    
    # Если улучшенной конфигурации нет, используем стандартную с изменениями
    if not config_path.exists():
        config_path = Path(__file__).parent.parent / 'config' / 'precleaner.yaml'
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Улучшенные параметры для тестирования
    config.update({
        'quote_preview_header_markers': [
            "Кому:", "От:", "Тема:", "Дата:", "Копия:", "Скрытая копия:",
            "From:", "To:", "Subject:", "Date:", "Cc:", "Bcc:"
        ],
        'quote_preview_markers': [
            "пишет", "написал", "писал", "wrote:", "writes:", 
            "forwarded message", "перенаправленное сообщение", "ответ на"
        ],
        'sig_markers': [
            "--", "—", "с уважением", "с наилучшими пожеланиями",
            "best regards", "kind regards", "regards", "с уважением,",
            "с наилучшими пожеланиями,", "уважаем,", "уважаемая,", "уважаемый,"
        ],
        'quote_preview_non_empty_lines': 50,
        'quote_preview_tail_non_empty_lines': 10,
        'quote_preview_max_chars': 1200,
        'max_signature_lines': 8,
        'max_disclaimer_lines': 8,
        'keep_first_signature_per_sender': True,
        'keep_first_disclaimer_per_thread': True,
        'fold_quote_over_chars': 2000
    })
    
    return config

def test_email(email_path, config):
    """Тестирование обработки письма"""
    print(f"\n{'='*80}")
    print(f"ТЕСТИРОВАНИЕ: {email_path}")
    print(f"{'='*80}")
    
    # Загрузка письма
    with open(email_path, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    original_text = email_data.get('body', '')
    original_length = len(original_text)
    
    print(f"Исходная длина: {original_length:,} символов")
    print(f"Отправитель: {email_data.get('from', '未知')}")
    print(f"Тема: {email_data.get('subject', '未知')}")
    print(f"Дата: {email_data.get('date', '未知')}")
    
    # Создание кэшей
    caches = {
        'thread': {},
        'sender': {}
    }
    
    # Обработка с PreCleaner
    try:
        result = preclean_email_for_llm(
            original_text,
            thread_id=email_data.get('thread_id', 'unknown'),
            sender_email=email_data.get('from', 'unknown'),
            config=config,
            caches=caches
        )
        
        cleaned_length = len(result.body_clean_llm)
        reduction = (1 - cleaned_length / original_length) * 100 if original_length > 0 else 0
        
        print(f"\nРЕЗУЛЬТАТЫ:")
        print(f"Обработанная длина: {cleaned_length:,} символов")
        print(f"Сокращение: {reduction:.1f}%")
        print(f"Экономия символов: {original_length - cleaned_length:,}")
        
        print(f"\nПРЕВЬЮ ОБРАБОТАННОГО ТЕКСТА:")
        print("-" * 60)
        preview = result.body_clean_llm[:500]
        print(preview)
        if len(result.body_clean_llm) > 500:
            print("...\n[текст обрезан для previews]")
        print("-" * 60)
        
        # Анализ содержимого
        print(f"\nАНАЛИЗ СОДЕРЖИМОГО:")
        print(f"Содержит '[quote': {'Да' if '[quote' in result.body_clean_llm else 'Нет'}")
        print(f"Содержит '[signature': {'Да' if '[signature' in result.body_clean_llm else 'Нет'}")
        print(f"Содержит '[disclaimer': {'Да' if '[disclaimer' in result.body_clean_llm else 'Нет'}")
        print(f"Содержит 'Контактная информация': {'Да' if 'Контактная информация' in result.body_clean_llm else 'Нет'}")
        print(f"Содержит 'Важная информация': {'Да' if 'Важная информация' in result.body_clean_llm else 'Нет'}")
        
        # Проверка сохранения важной информации
        important_info = {
            'Телефон': bool(re.search(r'(?:телефон|тел\.|phone):?\s*[+\d\s\-\(\)]+', result.body_clean_llm, re.I)),
            'Email': bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', result.body_clean_llm)),
            'Адрес': bool(re.search(r'(?:адрес|address):?\s*[^,\n]+', result.body_clean_llm, re.I)),
            'Версия': bool(re.search(r'(?:версия|version):\s*[^\s\n]+', result.body_clean_llm, re.I))
        }
        
        print(f"\nСОХРАНЕНИЕ ВАЖНОЙ ИНФОРМАЦИИ:")
        for info_type, preserved in important_info.items():
            print(f"{info_type}: {'✅ Сохранено' if preserved else '❌ Утеряно'}")
        
        return {
            'original_length': original_length,
            'cleaned_length': cleaned_length,
            'reduction': reduction,
            'important_info_preserved': sum(important_info.values()),
            'result': result
        }
        
    except Exception as e:
        print(f"\n❌ ОШИБКА ОБРАБОТКИ: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ УЛУЧШЕННОГО PRECLEANER")
    print("=" * 80)
    
    # Загрузка конфигурации
    config = load_config()
    print("✅ Конфигурация загружена")
    
    # Пути к тестовым письмам
    email_paths = [
        Path(__file__).parent.parent / 'data' / 'emails' / '2025-04-01' / 'email_016_20250401_20250401_himlabservice_ru_06d4360a.json',
        Path(__file__).parent.parent / 'data' / 'emails' / '2025-04-02' / 'email_023_20250402_20250402_invitro_ru_b972f810.json'
    ]
    
    results = []
    
    for email_path in email_paths:
        if email_path.exists():
            result = test_email(email_path, config)
            if result:
                results.append({
                    'email': email_path.name,
                    'result': result
                })
        else:
            print(f"\n❌ Файл не найден: {email_path}")
    
    # Сводные результаты
    print(f"\n{'='*80}")
    print("СВОДНЫЕ РЕЗУЛЬТАТЫ")
    print(f"{'='*80}")
    
    if results:
        total_original = sum(r['result']['original_length'] for r in results)
        total_cleaned = sum(r['result']['cleaned_length'] for r in results)
        total_reduction = (1 - total_cleaned / total_original) * 100 if total_original > 0 else 0
        
        print(f"Всего писем обработано: {len(results)}")
        print(f"Общий исходный размер: {total_original:,} символов")
        print(f"Общий обработанный размер: {total_cleaned:,} символов")
        print(f"Общее сокращение: {total_reduction:.1f}%")
        print(f"Общая экономия: {total_original - total_cleaned:,} символов")
        
        print(f"\nРЕЗУЛЬТАТЫ ПО ПИСЬМАМ:")
        for r in results:
            print(f"{r['email']}: {r['result']['reduction']:.1f}% сокращения, "
                  f"{r['result']['important_info_preserved']}/4 важной информации сохранено")
        
        # Оценка качества
        avg_reduction = sum(r['result']['reduction'] for r in results) / len(results)
        avg_preserved = sum(r['result']['important_info_preserved'] for r in results) / len(results)
        
        print(f"\nОЦЕНКА КАЧЕСТВА:")
        print(f"Среднее сокращение: {avg_reduction:.1f}%")
        print(f"Среднее сохранение важной информации: {avg_preserved:.1f}/4")
        
        if avg_reduction > 30 and avg_preserved > 2:
            print("✅ РЕЗУЛЬТАТ ХОРОШИЙ: эффективное сокращение с сохранением важной информации")
        elif avg_reduction > 30:
            print("⚠️ РЕЗУЛЬТАТ УДОВЛЕТВОРИТЕЛЬНЫЙ: хорошее сокращение, но теряется важная информация")
        elif avg_preserved > 2:
            print("⚠️ РЕЗУЛЬТАТ УДОВЛЕТВОРИТЕЛЬНЫЙ: важная информация сохранена, но сокращение недостаточно")
        else:
            print("❌ РЕЗУЛЬТАТ ПЛОХОЙ: требуется доработка алгоритма")
    else:
        print("❌ Ни одно письмо не было обработано")

if __name__ == "__main__":
    import re
    main()