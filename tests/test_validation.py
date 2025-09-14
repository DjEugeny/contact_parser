#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.core.extractor_factory import ExtractorFactory

def test_validation():
    """Тест валидации с автокоррекцией старого формата"""
    extractor = ExtractorFactory.create_test_extractor()
    
    test_text = "ООО Тестовая компания, тел: +7 (495) 123-45-67, email: test@company.ru"
    
    print("🧪 Тестирование валидации...")
    result = extractor.extract_contacts(test_text)
    
    print("✅ Тест API успешен")
    print(f"📊 Найдено контактов: {len(result.get('contacts', []))}")
    print(f"📊 Найдено организаций: {len(result.get('organizations', []))}")
    
    if result.get('contacts'):
        print(f"📞 Первый контакт: {result['contacts'][0]}")
    
    if result.get('organizations'):
        print(f"🏢 Первая организация: {result['organizations'][0]}")
    
    # Проверяем статистику
    stats = result.get('statistics', {})
    print(f"📈 Статистика: {stats}")
    
    return result

if __name__ == "__main__":
    test_validation()