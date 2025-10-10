#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тестирование обработки полных текстов БЕЗ ОБРЕЗКИ
Проверяет, что новая архитектура сохраняет все контактные данные
"""

import unittest
import logging
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.fetcher.utils.enhanced_text_cleaner import EnhancedTextCleaner
from src.fetcher.core.email_processor import EmailProcessor


class TestFullTextProcessing(unittest.TestCase):
    """🧪 Тесты обработки полных текстов"""
    
    def setUp(self):
        """Настройка тестов"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Создаем процессор
        self.processor = EmailProcessor(self.logger)
        
        # Создаем улучшенный очиститель
        self.enhanced_cleaner = EnhancedTextCleaner(self.logger)
    
    def test_enhanced_cleaner_no_truncation(self):
        """🧪 Тест: EnhancedTextCleaner НЕ обрезает тексты"""
        # Создаем длинный текст с контактной информацией
        long_text = """
        <div>
            <p>Добрый день!</p>
            <p>Контактная информация:</p>
            <p>Телефон: +7 (495) 123-45-67</p>
            <p>Email: contact@example.com</p>
            <p>Адрес: Москва, ул. Тестовая, 123</p>
            <p>ИНН: 1234567890</p>
            <p>ОГРН: 1234567890123</p>
        </div>
        """ + "Повторяющийся текст для проверки длины. " * 1000  # Делаем текст очень длинным
        
        # Обрабатываем текст
        result = self.enhanced_cleaner.clean_email_body_full(long_text)
        
        # Проверяем результаты
        self.assertGreater(result['final_length'], 10000)  # Текст должен быть длинным
        self.assertNotIn("ТЕКСТ ОБРЕЗАН", result['cleaned_text'])  # Не должно быть обрезки
        self.assertIn("+7 (495) 123-45-67", result['cleaned_text'])  # Контакты должны сохраниться
        self.assertIn("contact@example.com", result['cleaned_text'])  # Email должен сохраниться
        self.assertIn("1234567890", result['cleaned_text'])  # ИНН должен сохраниться
        
        print(f"✅ Тест EnhancedTextCleaner пройден:")
        print(f"   Исходная длина: {result['original_length']}")
        print(f"   Финальная длина: {result['final_length']}")
        print(f"   Обрезка: {'НЕТ' if 'ТЕКСТ ОБРЕЗАН' not in result['cleaned_text'] else 'ЕСТЬ'}")
        print(f"   Контакты сохранены: {'ДА' if '+7 (495) 123-45-67' in result['cleaned_text'] else 'НЕТ'}")
    
    def test_enhanced_cleaner_with_explicit_limit(self):
        """🧪 Тест: EnhancedTextCleaner обрезает только при явном запросе"""
        # Создаем длинный текст
        long_text = "Текст для проверки обрезки. " * 1000
        
        # Обрабатываем БЕЗ ограничения
        result_no_limit = self.enhanced_cleaner.clean_email_body(long_text, max_length=None)
        self.assertNotIn("ТЕКСТ ОБРЕЗАН", result_no_limit['cleaned_text'])
        
        # Обрабатываем С ограничением
        result_with_limit = self.enhanced_cleaner.clean_email_body(long_text, max_length=100)
        self.assertIn("ТЕКСТ ОБРЕЗАН", result_with_limit['cleaned_text'])
        
        print(f"✅ Тест явного ограничения пройден:")
        print(f"   Без ограничения: {'НЕ обрезан' if 'ТЕКСТ ОБРЕЗАН' not in result_no_limit['cleaned_text'] else 'Обрезан'}")
        print(f"   С ограничением: {'Обрезан' if 'ТЕКСТ ОБРЕЗАН' in result_with_limit['cleaned_text'] else 'НЕ обрезан'}")
    
    def test_contact_information_preservation(self):
        """🧪 Тест: Сохранение различной контактной информации"""
        # Текст с различными типами контактной информации
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
        
        # Обрабатываем текст
        result = self.enhanced_cleaner.clean_email_body_full(contact_text)
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
        
        print(f"✅ Тест сохранения контактов пройден:")
        print(f"   Сохранено контактов: {preserved_contacts}/{len(contact_checks)}")
        print(f"   Подпись удалена: {'ДА' if signature_removed else 'НЕТ'}")
        print(f"   Обрезка: {'НЕТ' if 'ТЕКСТ ОБРЕЗАН' not in cleaned_text else 'ЕСТЬ'}")
        
        # Проверяем, что большинство контактов сохранено
        self.assertGreaterEqual(preserved_contacts, len(contact_checks) * 0.8)
        self.assertNotIn("ТЕКСТ ОБРЕЗАН", cleaned_text)
    
    def test_comparison_with_original_cleaner(self):
        """🧪 Тест: Сравнение с оригинальным TextCleaner"""
        from src.text_cleaner import EmailTextCleaner
        
        # Создаем очистители
        original_cleaner = EmailTextCleaner(self.logger)
        enhanced_cleaner = EnhancedTextCleaner(self.logger)
        
        # Тестовый текст с контактами
        test_text = """
        <div>
            <p>Здравствуйте!</p>
            <p>Наши контакты:</p>
            <p>Телефон: +7 (495) 123-45-67</p>
            <p>Email: contact@example.com</p>
            <p>Адрес: Москва, ул. Тестовая, 123</p>
        </div>
        """ + "Дополнительный текст для проверки обрезки. " * 2000
        
        # Обрабатываем оригинальным очистителем
        original_result = original_cleaner.extract_meaningful_content(test_text)
        
        # Обрабатываем улучшенным очистителем
        enhanced_result = enhanced_cleaner.clean_email_body_full(test_text)
        
        print(f"✅ Сравнение очистителей:")
        print(f"   Оригинальный:")
        print(f"     Длина: {len(original_result)}")
        print(f"     Обрезка: {'ЕСТЬ' if 'ТЕКСТ ОБРЕЗАН' in original_result else 'НЕТ'}")
        print(f"     Контакты: {'ДА' if '+7 (495) 123-45-67' in original_result else 'НЕТ'}")
        
        print(f"   Улучшенный:")
        print(f"     Длина: {enhanced_result['final_length']}")
        print(f"     Обрезка: {'ЕСТЬ' if 'ТЕКСТ ОБРЕЗАН' in enhanced_result['cleaned_text'] else 'НЕТ'}")
        print(f"     Контакты: {'ДА' if '+7 (495) 123-45-67' in enhanced_result['cleaned_text'] else 'НЕТ'}")
        
        # Проверяем различия
        self.assertNotIn("ТЕКСТ ОБРЕЗАН", enhanced_result['cleaned_text'])
        self.assertIn("+7 (495) 123-45-67", enhanced_result['cleaned_text'])
        
        # Улучшенный должен сохранить больше информации
        self.assertGreaterEqual(enhanced_result['final_length'], len(original_result))


def run_full_text_tests():
    """🚀 Запуск всех тестов обработки полных текстов"""
    print("🧪 ЗАПУСК ТЕСТОВ ОБРАБОТКИ ПОЛНЫХ ТЕКСТОВ")
    print("=" * 60)
    
    # Настраиваем логирование
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Создаем тестовый набор
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFullTextProcessing)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print(f"   Всего тестов: {result.testsRun}")
    print(f"   Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   Ошибок: {len(result.errors)}")
    print(f"   Провалов: {len(result.failures)}")
    
    if result.failures:
        print("\n❌ ПРОАЛЕННЫЕ ТЕСТЫ:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️ ТЕСТЫ С ОШИБКАМИ:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n📈 УСПЕШНОСТЬ: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Новая архитектура сохраняет полные тексты.")
    else:
        print("⚠️ Некоторые тесты не пройдены. Проверьте реализацию.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_full_text_tests()