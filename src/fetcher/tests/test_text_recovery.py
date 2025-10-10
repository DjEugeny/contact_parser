#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 Тесты модуля восстановления полных текстов писем
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from fetcher.recovery.text_recovery_module import TextRecoveryModule, RecoveryResult


class TestTextRecoveryModule(unittest.TestCase):
    """🧪 Тесты модуля восстановления текстов"""
    
    def setUp(self):
        """🔧 Настройка тестового окружения"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.emails_dir = self.test_dir / "emails"
        self.emails_dir.mkdir(parents=True)
        
        # Создаем тестовое письмо с обрезанным текстом
        self.test_email_data = {
            "thread_id": "20250728_test_thread",
            "message_id": "<test-message-id@example.com>",
            "from": "test@example.com",
            "to": "recipient@example.com",
            "subject": "Test Email",
            "date": "Mon, 28 Jul 2025 13:56:18 +0300",
            "body": "Короткий текст\n[ТЕКСТ ОБРЕЗАН ДЛЯ ЭКОНОМИИ ТОКЕНОВ]",
            "char_count": 50,
            "attachments": []
        }
        
        # Создаем тестовый JSON файл
        self.test_json_file = self.emails_dir / "2025-07-28" / "email_001_20250728_test_thread.json"
        self.test_json_file.parent.mkdir(parents=True)
        
        with open(self.test_json_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_email_data, f, ensure_ascii=False, indent=2)
        
        # Инициализация модуля
        self.recovery_module = TextRecoveryModule(self.test_dir)
    
    def tearDown(self):
        """🧹 Очистка тестового окружения"""
        shutil.rmtree(self.test_dir)
    
    def test_scan_truncated_emails(self):
        """🔍 Тест сканирования обрезанных писем"""
        # Создаем еще одно письмо без обрезания
        normal_email_data = {
            "thread_id": "20250728_normal_thread",
            "message_id": "<normal-message-id@example.com>",
            "from": "test@example.com",
            "to": "recipient@example.com",
            "subject": "Normal Email",
            "date": "Mon, 28 Jul 2025 13:56:18 +0300",
            "body": "Полный текст письма без обрезания",
            "char_count": 100,
            "attachments": []
        }
        
        normal_json_file = self.emails_dir / "2025-07-28" / "email_002_20250728_normal_thread.json"
        with open(normal_json_file, 'w', encoding='utf-8') as f:
            json.dump(normal_email_data, f, ensure_ascii=False, indent=2)
        
        # Запуск сканирования
        truncated_emails = self.recovery_module.scan_truncated_emails()
        
        # Проверка результатов
        self.assertEqual(len(truncated_emails), 1)
        self.assertEqual(truncated_emails[0]['message_id'], "<test-message-id@example.com>")
        self.assertEqual(truncated_emails[0]['date_folder'], "2025-07-28")
        
        # Проверка статистики
        self.assertEqual(self.recovery_module.stats['total_scanned'], 2)
        self.assertEqual(self.recovery_module.stats['truncated_found'], 1)
    
    def test_find_json_file(self):
        """🔍 Тест поиска JSON файла"""
        # Существующий файл
        found_file = self.recovery_module._find_json_file(
            "<test-message-id@example.com>", 
            "2025-07-28"
        )
        self.assertIsNotNone(found_file)
        self.assertEqual(found_file.name, "email_001_20250728_test_thread.json")
        
        # Несуществующий файл
        not_found = self.recovery_module._find_json_file(
            "<non-existent@example.com>", 
            "2025-07-28"
        )
        self.assertIsNone(not_found)
    
    def test_count_contacts(self):
        """👥 Тест подсчета контактов"""
        text_with_contacts = """
        Добрый день!
        
        Контактная информация:
        Email: test@example.com, admin@company.ru
        Телефон: +7 (495) 123-45-67, 8-800-555-35-35
        
        С уважением,
        Иван Иванов
        ivan.ivanov@company.com
        +7 916 123 45 67
        """
        
        contacts_count = self.recovery_module._count_contacts(text_with_contacts)
        
        # 3 email + 4 телефона = 7 контактов
        self.assertEqual(contacts_count, 7)
    
    def test_clean_html(self):
        """🧹 Тест очистки HTML"""
        html_text = """
        <html>
            <body>
                <h1>Заголовок</h1>
                <p>Текст с   множественными    пробелами</p>
                <div>Блок текста</div>
            </body>
        </html>
        """
        
        clean_text = self.recovery_module._clean_html(html_text)
        
        # Проверка удаления тегов и нормализации пробелов
        self.assertNotIn('<', clean_text)
        self.assertNotIn('>', clean_text)
        self.assertIn('Заголовок', clean_text)
        self.assertIn('Текст с множественными пробелами', clean_text)
    
    @patch('fetcher.recovery.text_recovery_module.ConnectionManager')
    def test_recover_from_imap_success(self, mock_connection_manager):
        """🔄 Тест успешного восстановления через IMAP"""
        # Настройка мока
        mock_manager = Mock()
        mock_manager.connect.return_value = True
        mock_manager.search.return_value = [b'1']
        mock_manager.fetch_email.return_value = b'Test email content'
        mock_connection_manager.return_value = mock_manager
        
        # Мок для парсинга email
        with patch('fetcher.recovery.text_recovery_module.email.message_from_bytes') as mock_parse:
            mock_msg = Mock()
            mock_msg.is_multipart.return_value = False
            mock_msg.get_content_type.return_value = "text/plain"
            mock_msg.get_payload.return_value.decode.return_value = "Полный восстановленный текст"
            mock_parse.return_value = mock_msg
            
            # Запуск восстановления
            result = self.recovery_module.recover_email_text(
                "<test-message-id@example.com>",
                "2025-07-28"
            )
            
            # Проверка результатов
            self.assertTrue(result.success)
            self.assertEqual(result.recovery_method, "imap")
            self.assertGreater(result.recovered_length, result.original_length)
    
    @patch('fetcher.recovery.text_recovery_module.ConnectionManager')
    def test_recover_from_imap_failure(self, mock_connection_manager):
        """❌ Тест неудачного восстановления через IMAP"""
        # Настройка мока - не удается подключиться
        mock_manager = Mock()
        mock_manager.connect.return_value = False
        mock_connection_manager.return_value = mock_manager
        
        # Запуск восстановления
        result = self.recovery_module.recover_email_text(
            "<test-message-id@example.com>",
            "2025-07-28"
        )
        
        # Проверка результатов
        self.assertFalse(result.success)
        self.assertIn("Не удалось восстановить", result.error_message)
    
    def test_update_email_file_success(self):
        """💾 Тест успешного обновления JSON файла"""
        new_body = "Полный восстановленный текст письма с контактами: test@example.com, +7-495-123-45-67"
        
        result = self.recovery_module._update_email_file(
            self.test_json_file,
            self.test_email_data,
            new_body,
            50,  # original_length
            "test"
        )
        
        # Проверка результатов
        self.assertTrue(result.success)
        self.assertEqual(result.recovery_method, "test")
        self.assertGreater(result.recovered_length, result.original_length)
        self.assertGreater(result.contacts_found, 0)
        
        # Проверка обновления файла
        with open(self.test_json_file, 'r', encoding='utf-8') as f:
            updated_data = json.load(f)
        
        self.assertEqual(updated_data['body'], new_body)
        self.assertEqual(updated_data['char_count'], len(new_body))
        self.assertEqual(updated_data['text_recovery_method'], "test")
        self.assertEqual(updated_data['original_char_count'], 50)
        
        # Проверка создания бэкапа
        backup_file = self.test_json_file.with_suffix('.json.backup')
        self.assertTrue(backup_file.exists())
    
    def test_update_email_file_failure(self):
        """❌ Тест неудачного обновления JSON файла"""
        # Создаем файл с ошибкой прав доступа
        readonly_file = self.test_json_file
        readonly_file.chmod(0o444)  # Только для чтения
        
        new_body = "Полный восстановленный текст"
        
        result = self.recovery_module._update_email_file(
            readonly_file,
            self.test_email_data,
            new_body,
            50,
            "test"
        )
        
        # Проверка результатов
        self.assertFalse(result.success)
        self.assertIn("Ошибка обновления", result.error_message)
        
        # Восстановление прав доступа
        readonly_file.chmod(0o644)
    
    def test_find_eml_file(self):
        """📧 Тест поиска .eml файла"""
        # Создаем тестовую папку с .eml файлами
        eml_dir = self.test_dir / "eml" / "2025-07-28"
        eml_dir.mkdir(parents=True)
        
        # Создаем .eml файл с правильным Message-ID
        eml_content = f"""Message-ID: <test-message-id@example.com>
From: test@example.com
To: recipient@example.com
Subject: Test

Test email content
"""
        
        eml_file = eml_dir / "test.eml"
        with open(eml_file, 'w', encoding='utf-8') as f:
            f.write(eml_content)
        
        # Поиск файла
        found_file = self.recovery_module._find_eml_file(
            "<test-message-id@example.com>",
            "2025-07-28"
        )
        
        self.assertIsNotNone(found_file)
        self.assertEqual(found_file.name, "test.eml")
        
        # Поиск несуществующего файла
        not_found = self.recovery_module._find_eml_file(
            "<non-existent@example.com>",
            "2025-07-28"
        )
        
        self.assertIsNone(not_found)
    
    def test_batch_recovery(self):
        """🔄 Тест пакетного восстановления"""
        # Создаем еще одно обрезанное письмо
        test_email_data_2 = {
            "thread_id": "20250728_test_thread_2",
            "message_id": "<test-message-id-2@example.com>",
            "from": "test2@example.com",
            "to": "recipient2@example.com",
            "subject": "Test Email 2",
            "date": "Mon, 28 Jul 2025 13:56:18 +0300",
            "body": "Еще один короткий текст\n[ТЕКСТ ОБРЕЗАН ДЛЯ ЭКОНОМИИ ТОКЕНОВ]",
            "char_count": 45,
            "attachments": []
        }
        
        test_json_file_2 = self.emails_dir / "2025-07-28" / "email_002_20250728_test_thread_2.json"
        with open(test_json_file_2, 'w', encoding='utf-8') as f:
            json.dump(test_email_data_2, f, ensure_ascii=False, indent=2)
        
        # Мок для восстановления (имитируем успешное восстановление)
        with patch.object(self.recovery_module, 'recover_email_text') as mock_recover:
            mock_recover.side_effect = [
                RecoveryResult(
                    success=True,
                    message_id="<test-message-id@example.com>",
                    file_path=str(self.test_json_file),
                    original_length=50,
                    recovered_length=200,
                    contacts_found=3,
                    recovery_method="test"
                ),
                RecoveryResult(
                    success=True,
                    message_id="<test-message-id-2@example.com>",
                    file_path=str(test_json_file_2),
                    original_length=45,
                    recovered_length=180,
                    contacts_found=2,
                    recovery_method="test"
                )
            ]
            
            # Запуск пакетного восстановления
            results = self.recovery_module.batch_recovery()
            
            # Проверка результатов
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.success for r in results))
            
            # Проверка статистики
            self.assertEqual(self.recovery_module.stats['recovery_success'], 2)
            self.assertEqual(self.recovery_module.stats['contacts_recovered'], 5)
            
            # Проверка реестра
            self.assertIn("<test-message-id@example.com>", self.recovery_module.recovery_registry)
            self.assertIn("<test-message-id-2@example.com>", self.recovery_module.recovery_registry)


class TestRecoveryResult(unittest.TestCase):
    """🧪 Тесты класса RecoveryResult"""
    
    def test_recovery_result_creation(self):
        """📊 Тест создания результата восстановления"""
        result = RecoveryResult(
            success=True,
            message_id="<test@example.com>",
            file_path="/test/path.json",
            original_length=100,
            recovered_length=500,
            contacts_found=3,
            recovery_method="imap"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.message_id, "<test@example.com>")
        self.assertEqual(result.file_path, "/test/path.json")
        self.assertEqual(result.original_length, 100)
        self.assertEqual(result.recovered_length, 500)
        self.assertEqual(result.contacts_found, 3)
        self.assertEqual(result.recovery_method, "imap")
        self.assertIsNone(result.error_message)
    
    def test_recovery_result_with_error(self):
        """❌ Тест создания результата с ошибкой"""
        result = RecoveryResult(
            success=False,
            message_id="<test@example.com>",
            file_path="/test/path.json",
            original_length=100,
            recovered_length=0,
            contacts_found=0,
            error_message="Connection failed",
            recovery_method="failed"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Connection failed")
        self.assertEqual(result.recovery_method, "failed")


if __name__ == '__main__':
    unittest.main()