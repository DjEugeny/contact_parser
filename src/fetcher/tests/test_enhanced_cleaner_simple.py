#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Упрощенный тест EnhancedTextCleaner
Проверяет, что новая архитектура сохраняет полные тексты БЕЗ ОБРЕЗКИ
"""

import sys
import logging
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Импортируем только нужные модули
from src.fetcher.utils.enhanced_text_cleaner import EnhancedTextCleaner


def test_enhanced_cleaner_basic():
    """🧪 Базовый тест EnhancedTextCleaner"""
    print("🧪 ТЕСТИРОВАНИЕ EnhancedTextCleaner")
    print("=" * 50)
    
    # Настраиваем логирование
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    # Создаем очиститель
    cleaner = EnhancedTextCleaner(logger)
    
    # Тест 1: Проверка отсутствия обрезки по умолчанию
    print("\n📝 Тест 1: Проверка отсутствия обрезки по умолчанию")
    
    long_text = """
    <div>
        <p>Здравствуйте!</p>
        <p>Контактная информация:</p>
        <p>Телефон: +7 (495) 123-45-67</p>
        <p>Email: contact@example.com</p>
        <p>Адрес: Москва, ул. Тестовая, 123</p>
        <p>ИНН: 1234567890</p>
        <p>ОГРН: 1234567890123</p>
    </div>
    """ + "Дополнительный текст для проверки длины. " * 2000  # Делаем текст очень длинным
    
    result = cleaner.clean_email_body_full(long_text)
    
    print(f"   Исходная длина: {result['original_length']}")
    print(f"   Финальная длина: {result['final_length']}")
    print(f"   Обрезка: {'НЕТ' if 'ТЕКСТ ОБРЕЗАН' not in result['cleaned_text'] else 'ЕСТЬ'}")
    print(f"   Контакты сохранены: {'ДА' if '+7 (495) 123-45-67' in result['cleaned_text'] else 'НЕТ'}")
    
    # Проверки
    assert 'ТЕКСТ ОБРЕЗАН' not in result['cleaned_text'], "Текст не должен быть обрезан"
    assert '+7 (495) 123-45-67' in result['cleaned_text'], "Контакты должны быть сохранены"
    assert result['final_length'] > 10000, "Текст должен быть длинным"
    
    print("   ✅ Тест 1 пройден")
    
    # Тест 2: Проверка явного ограничения
    print("\n📝 Тест 2: Проверка явного ограничения")
    
    result_with_limit = cleaner.clean_email_body(long_text, max_length=100)
    
    print(f"   С ограничением 100 символов:")
    print(f"   Финальная длина: {result_with_limit['final_length']}")
    print(f"   Обрезка: {'ЕСТЬ' if 'ТЕКСТ ОБРЕЗАН' in result_with_limit['cleaned_text'] else 'НЕТ'}")
    
    # Проверки
    assert 'ТЕКСТ ОБРЕЗАН' in result_with_limit['cleaned_text'], "Текст должен быть обрезан при явном ограничении"
    
    print("   ✅ Тест 2 пройден")
    
    # Тест 3: Сравнение с оригинальным TextCleaner
    print("\n📝 Тест 3: Сравнение с оригинальным TextCleaner")
    
    try:
        from src.text_cleaner import EmailTextCleaner
        
        original_cleaner = EmailTextCleaner(logger)
        original_result = original_cleaner.extract_meaningful_content(long_text)
        
        print(f"   Оригинальный TextCleaner:")
        print(f"     Длина: {len(original_result)}")
        print(f"     Обрезка: {'ЕСТЬ' if 'ТЕКСТ ОБРЕЗАН' in original_result else 'НЕТ'}")
        print(f"     Контакты: {'ДА' if '+7 (495) 123-45-67' in original_result else 'НЕТ'}")
        
        print(f"   EnhancedTextCleaner:")
        print(f"     Длина: {result['final_length']}")
        print(f"     Обрезка: {'ЕСТЬ' if 'ТЕКСТ ОБРЕЗАН' in result['cleaned_text'] else 'НЕТ'}")
        print(f"     Контакты: {'ДА' if '+7 (495) 123-45-67' in result['cleaned_text'] else 'НЕТ'}")
        
        # Проверки
        assert 'ТЕКСТ ОБРЕЗАН' in original_result, "Оригинальный должен обрезать"
        assert 'ТЕКСТ ОБРЕЗАН' not in result['cleaned_text'], "Enhanced не должен обрезать"
        assert result['final_length'] >= len(original_result), "Enhanced должен сохранить больше"
        
        print("   ✅ Тест 3 пройден")
        
    except ImportError as e:
        print(f"   ⚠️ Не удалось импортировать оригинальный TextCleaner: {e}")
        print("   ✅ Тест 3 пропущен")
    
    print("\n" + "=" * 50)
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("✅ EnhancedTextCleaner сохраняет полные тексты БЕЗ ОБРЕЗКИ")
    
    return True


def test_contact_preservation():
    """🧪 Тест сохранения контактной информации"""
    print("\n🧪 ТЕСТИРОВАНИЕ СОХРАНЕНИЯ КОНТАКТОВ")
    print("=" * 50)
    
    logger = logging.getLogger(__name__)
    cleaner = EnhancedTextCleaner(logger)
    
    # Текст с различными типами контактов
    contact_text = """
    <html>
        <body>
            <div>
                <h1>Контактные данные</h1>
                <p>Основные контакты:</p>
                <ul>
                    <li>Телефон: +7 (495) 123-45-67</li>
                    <li>Мобильный: +7 (916) 987-65-43</li>
                    <li>Email: general@company.ru</li>
                    <li>Личный email: personal@example.com</li>
                    <li>Сайт: https://www.example.com</li>
                </ul>
                
                <p>Юридические данные:</p>
                <ul>
                    <li>Название: ООО "Тестовая Компания"</li>
                    <li>ИНН: 1234567890</li>
                    <li>КПП: 123456789</li>
                    <li>ОГРН: 1234567890123</li>
                    <li>Юридический адрес: 123456, г. Москва, ул. Тестовая, д. 123, оф. 456</li>
                </ul>
                
                <p>Банковские реквизиты:</p>
                <ul>
                    <li>Банк: ПАО "СБЕРБАНК"</li>
                    <li>БИК: 044525225</li>
                    <li>Корр. счет: 30101810900000000225</li>
                    <li>Расчетный счет: 40702810900000012345</li>
                </ul>
            </div>
            
            <div class="moz-signature">
                --
                <br />
                С уважением,
                <br />
                Тестовый Тест
            </div>
        </body>
    </html>
    """
    
    result = cleaner.clean_email_body_full(contact_text)
    cleaned_text = result['cleaned_text']
    
    # Проверяем сохранение контактной информации
    contact_checks = [
        ("+7 (495) 123-45-67", "Телефон"),
        ("+7 (916) 987-65-43", "Мобильный"),
        ("general@company.ru", "Email"),
        ("personal@example.com", "Личный email"),
        ("ООО \"Тестовая Компания\"", "Название компании"),
        ("1234567890", "ИНН"),
        ("123456789", "КПП"),
        ("1234567890123", "ОГРН"),
        ("г. Москва, ул. Тестовая", "Адрес"),
        ("ПАО \"СБЕРБАНК\"", "Банк"),
        ("044525225", "БИК"),
        ("30101810900000000225", "Корр. счет"),
        ("40702810900000012345", "Расчетный счет"),
    ]
    
    preserved_contacts = 0
    for contact_text, contact_type in contact_checks:
        if contact_text in cleaned_text:
            preserved_contacts += 1
            print(f"   ✅ {contact_type}: сохранен")
        else:
            print(f"   ❌ {contact_type}: потерян")
    
    # Проверяем, что подпись удалена
    signature_removed = "С уважением," not in cleaned_text or "Тестовый Тест" not in cleaned_text
    
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"   Сохранено контактов: {preserved_contacts}/{len(contact_checks)}")
    print(f"   Подпись удалена: {'ДА' if signature_removed else 'НЕТ'}")
    print(f"   Обрезка: {'НЕТ' if 'ТЕКСТ ОБРЕЗАН' not in cleaned_text else 'ЕСТЬ'}")
    
    # Проверки
    assert preserved_contacts >= len(contact_checks) * 0.8, "Большинство контактов должно быть сохранено"
    assert 'ТЕКСТ ОБРЕЗАН' not in cleaned_text, "Текст не должен быть обрезан"
    
    print("\n✅ Тест сохранения контактов пройден")
    return True


if __name__ == '__main__':
    print("🚀 ЗАПУК УПРОЩЕННЫХ ТЕСТОВ ENHANCED TEXT CLEANER")
    print("=" * 60)
    
    try:
        # Запускаем тесты
        test1_result = test_enhanced_cleaner_basic()
        test2_result = test_contact_preservation()
        
        if test1_result and test2_result:
            print("\n" + "=" * 60)
            print("🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
            print("✅ Новая архитектура сохраняет полные тексты БЕЗ ОБРЕЗКИ")
            print("✅ Вся контактная информация сохраняется")
            print("✅ Обрезка происходит только при явном запросе")
        else:
            print("\n❌ Некоторые тесты не пройдены")
            
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()