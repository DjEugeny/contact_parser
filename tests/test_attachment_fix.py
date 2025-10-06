#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🧪 Тест исправления проблемы с вложениями"""

import json
import sys
from pathlib import Path
from argparse import Namespace

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api_pipeline_validator import APIPipelineValidator


def test_single_email_with_attachments():
    """🧪 Тестирует обработку письма с вложениями"""
    
    # Тестируем конкретное письмо email_010 с коммерческими предложениями
    email_file = PROJECT_ROOT / "data" / "emails" / "2025-07-09" / "email_010_20250709_20250709_dna-technology_ru_0ec75872.json"
    
    if not email_file.exists():
        print(f"❌ Файл письма не найден: {email_file}")
        return
    
    print(f"🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ ПРОБЛЕМЫ С ВЛОЖЕНИЯМИ")
    print(f"=" * 60)
    print(f"📧 Тестируемое письмо: {email_file.name}")
    
    # Создаем экземпляр валидатора
    dummy_args = Namespace(
        mode="test",
        date=None,
        count=None,
        start_date=None,
        end_date=None,
        dry_run=True
    )
    
    try:
        validator = APIPipelineValidator(dummy_args)
        
        # Читаем данные письма
        with email_file.open("r", encoding="utf-8") as f:
            email_data = json.load(f)
        
        print(f"\n📎 Вложения в письме:")
        attachments = email_data.get('attachments', [])
        for i, attachment in enumerate(attachments, 1):
            print(f"   {i}. {attachment.get('filename', 'unknown')}")
            print(f"      Путь: {attachment.get('path', 'НЕ УКАЗАН')}")
            print(f"      Статус: {attachment.get('status', 'unknown')}")
        
        # Тестируем метод объединения текста
        date = "2025-07-09"
        print(f"\n🔍 ТЕСТИРОВАНИЕ _compose_combined_text")
        print(f"-" * 40)
        
        combined_text = validator._compose_combined_text(email_data, date)
        
        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        print(f"   Общая длина объединенного текста: {len(combined_text)} символов")
        
        # Проверяем наличие секций
        has_email_section = "=== ТЕКСТ ПИСЬМА ===" in combined_text
        has_attachment_sections = combined_text.count("=== ВЛОЖЕНИЕ") 
        
        print(f"   Содержит секцию письма: {'✅' if has_email_section else '❌'}")
        print(f"   Количество секций вложений: {has_attachment_sections}")
        
        if has_attachment_sections > 0:
            print(f"   ✅ ИСПРАВЛЕНИЕ РАБОТАЕТ! Текст вложений извлекается!")
        else:
            print(f"   ❌ Проблема НЕ исправлена. Текст вложений не извлекается.")
        
        # Показываем превью объединенного текста
        print(f"\n📄 ПРЕВЬЮ ОБЪЕДИНЕННОГО ТЕКСТА (первые 1000 символов):")
        print(f"   {'-'*50}")
        preview = combined_text[:1000]
        print(f"   {preview}")
        if len(combined_text) > 1000:
            print(f"   ... (еще {len(combined_text) - 1000} символов)")
        print(f"   {'-'*50}")
        
        # Проверяем, есть ли упоминания коммерческого предложения
        commercial_mentions = []
        keywords = ["коммерческое предложение", "КП", "прайс", "цена", "стоимость", "скидка"]
        for keyword in keywords:
            if keyword.lower() in combined_text.lower():
                commercial_mentions.append(keyword)
        
        if commercial_mentions:
            print(f"\n💼 Найдены упоминания коммерческих терминов: {', '.join(commercial_mentions)}")
        else:
            print(f"\n⚠️ Коммерческие термины не найдены в объединенном тексте")
            
        return combined_text
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_single_email_with_attachments()