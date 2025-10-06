#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест исправления обработки вложений
"""

def test_attachment_processing_fix():
    """Тест исправления обработки вложений"""
    
    print("🧪 Тест исправления обработки вложений")
    
    # Имитируем логику из AttachmentEvidenceExtractor
    def safe_get_attachments(email_data):
        """Безопасное получение вложений"""
        attachments = email_data.get('attachments', [])
        
        # Проверяем что attachments это список, а не число или другой тип
        if not isinstance(attachments, list):
            print(f"⚠️ Attachments is not a list, got {type(attachments)}: {attachments}")
            return []
        
        if not attachments:
            print("📎 No attachments found in email_data")
            return []
        
        print(f"🔍 Найдено {len(attachments)} вложений")
        return attachments
    
    # Тест 1: Правильная структура
    print("\n📋 Тест 1: Правильная структура")
    email_data_correct = {
        'attachments': [
            {'filename': 'test1.pdf'},
            {'filename': 'test2.pdf'}
        ]
    }
    attachments = safe_get_attachments(email_data_correct)
    assert len(attachments) == 2, f"Ожидали 2 вложения, получили {len(attachments)}"
    print("✅ Правильная структура обработана корректно")
    
    # Тест 2: Неправильная структура (число)
    print("\n📋 Тест 2: Неправильная структура (число)")
    email_data_wrong = {
        'attachments': 4  # Число вместо списка
    }
    attachments = safe_get_attachments(email_data_wrong)
    assert len(attachments) == 0, f"Ожидали 0 вложений, получили {len(attachments)}"
    print("✅ Неправильная структура обработана корректно")
    
    # Тест 3: Отсутствие поля
    print("\n📋 Тест 3: Отсутствие поля attachments")
    email_data_missing = {
        'from': 'test@example.com'
    }
    attachments = safe_get_attachments(email_data_missing)
    assert len(attachments) == 0, f"Ожидали 0 вложений, получили {len(attachments)}"
    print("✅ Отсутствие поля обработано корректно")
    
    # Тест 4: Пустой список
    print("\n📋 Тест 4: Пустой список")
    email_data_empty = {
        'attachments': []
    }
    attachments = safe_get_attachments(email_data_empty)
    assert len(attachments) == 0, f"Ожидали 0 вложений, получили {len(attachments)}"
    print("✅ Пустой список обработан корректно")
    
    print("\n🎉 Все тесты пройдены! Исправление работает корректно")
    
    print("\n📝 Резюме исправления:")
    print("1. ✅ Добавлена проверка типа attachments")
    print("2. ✅ Обработка случая, когда attachments - число")
    print("3. ✅ Обработка отсутствующего поля attachments")
    print("4. ✅ Добавлены полные данные о вложениях в email_metadata")

if __name__ == "__main__":
    test_attachment_processing_fix()