#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест полной цепочки обработки: загрузка писем → OCR → LLM → экспорт в таблицы
"""

import sys
import os
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from google_sheets_bridge import LLM_Sheets_Bridge
from integrated_llm_processor import IntegratedLLMProcessor
from google_sheets_exporter import GoogleSheetsExporter
from local_exporter import LocalDataExporter


class TestFullPipeline(unittest.TestCase):
    """🧪 Тесты полной цепочки обработки"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.test_date = "2025-01-15"
        self.bridge = LLM_Sheets_Bridge()
        
    def test_bridge_initialization(self):
        """🔧 Тест инициализации моста"""
        print("\n🔧 Тестирование инициализации LLM_Sheets_Bridge...")
        
        # Проверяем, что все компоненты инициализированы
        self.assertIsInstance(self.bridge.processor, IntegratedLLMProcessor)
        self.assertIsInstance(self.bridge.exporter, GoogleSheetsExporter)
        self.assertIsInstance(self.bridge.local_exporter, LocalDataExporter)
        
        # Проверяем, что процессор не в тестовом режиме
        self.assertFalse(self.bridge.processor.test_mode)
        
        print("   ✅ Все компоненты инициализированы корректно")
        
    @patch('subprocess.run')
    def test_auto_fetch_emails_success(self, mock_subprocess):
        """📧 Тест успешной автоматической загрузки писем"""
        print("\n📧 Тестирование автоматической загрузки писем...")
        
        # Мокаем успешный результат subprocess
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Загружено 5 писем за 2025-01-15"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Тестируем автозагрузку
        result = self.bridge._auto_fetch_emails(self.test_date)
        
        # Проверяем результат
        self.assertTrue(result)
        
        # Проверяем, что subprocess был вызван с правильными параметрами
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        self.assertIn("advanced_email_fetcher.py", str(call_args))
        self.assertIn("--date", call_args)
        self.assertIn(self.test_date, call_args)
        
        print("   ✅ Автоматическая загрузка писем работает корректно")
        
    @patch('subprocess.run')
    def test_auto_fetch_emails_failure(self, mock_subprocess):
        """📧 Тест неудачной автоматической загрузки писем"""
        print("\n📧 Тестирование обработки ошибок при загрузке писем...")
        
        # Мокаем неудачный результат subprocess
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Ошибка подключения к серверу"
        mock_subprocess.return_value = mock_result
        
        # Тестируем автозагрузку
        result = self.bridge._auto_fetch_emails(self.test_date)
        
        # Проверяем результат
        self.assertFalse(result)
        
        print("   ✅ Обработка ошибок загрузки работает корректно")
        
    @patch.object(LLM_Sheets_Bridge, '_auto_fetch_emails')
    @patch.object(IntegratedLLMProcessor, 'process_emails_by_date')
    def test_process_and_export_with_auto_fetch(self, mock_process, mock_fetch):
        """🔄 Тест полной цепочки с автоматической загрузкой"""
        print("\n🔄 Тестирование полной цепочки с автозагрузкой...")
        
        # Первый вызов process_emails_by_date возвращает пустой результат
        # Второй вызов (после автозагрузки) возвращает данные
        mock_process.side_effect = [
            # Первый вызов - нет писем
            {
                'statistics': {'emails_processed': 0},
                'summary': {'total_contacts': 0},
                'all_contacts': []
            },
            # Второй вызов - есть письма после автозагрузки
            {
                'statistics': {
                    'emails_processed': 3,
                    'total_requests': 3,
                    'successful_requests': 3,
                    'failed_requests': 0
                },
                'summary': {'total_contacts': 2},
                'all_contacts': [
                    {
                        'name': 'Иван Петров',
                        'email': 'ivan@example.com',
                        'phone': '+7-123-456-7890',
                        'company': 'ООО Тест',
                        'priority': 8
                    },
                    {
                        'name': 'Мария Сидорова',
                        'email': 'maria@test.ru',
                        'phone': '+7-987-654-3210',
                        'company': 'ИП Сидорова',
                        'priority': 7
                    }
                ]
            }
        ]
        
        # Мокаем успешную автозагрузку
        mock_fetch.return_value = True
        
        # Мокаем экспорт в Google Sheets (недоступен)
        with patch.object(self.bridge.exporter, 'client', None):
            with patch.object(self.bridge, '_fallback_to_local_export', return_value=True) as mock_local:
                # Тестируем полную цепочку
                result = self.bridge.process_and_export(self.test_date)
                
                # Проверяем результат
                self.assertTrue(result)
                
                # Проверяем, что автозагрузка была вызвана
                mock_fetch.assert_called_once_with(self.test_date)
                
                # Проверяем, что process_emails_by_date был вызван дважды
                self.assertEqual(mock_process.call_count, 2)
                
                # Проверяем, что был вызван локальный экспорт
                mock_local.assert_called_once()
                
        print("   ✅ Полная цепочка с автозагрузкой работает корректно")
        
    @patch.object(IntegratedLLMProcessor, 'process_emails_by_date')
    def test_process_and_export_no_emails_no_fetch(self, mock_process):
        """📭 Тест обработки случая, когда нет писем и автозагрузка не помогла"""
        print("\n📭 Тестирование случая отсутствия писем...")
        
        # Мокаем отсутствие писем
        mock_process.return_value = {
            'statistics': {'emails_processed': 0},
            'summary': {'total_contacts': 0},
            'all_contacts': []
        }
        
        # Мокаем неудачную автозагрузку
        with patch.object(self.bridge, '_auto_fetch_emails', return_value=False):
            # Тестируем обработку
            result = self.bridge.process_and_export(self.test_date)
            
            # Проверяем результат
            self.assertFalse(result)
            
        print("   ✅ Обработка отсутствия писем работает корректно")
        
    @patch.object(IntegratedLLMProcessor, 'process_emails_by_date')
    def test_process_and_export_with_google_sheets(self, mock_process):
        """📊 Тест экспорта в Google Sheets"""
        print("\n📊 Тестирование экспорта в Google Sheets...")
        
        # Мокаем успешную обработку писем
        mock_process.return_value = {
            'statistics': {
                'emails_processed': 2,
                'total_requests': 2,
                'successful_requests': 2,
                'failed_requests': 0
            },
            'summary': {'total_contacts': 1},
            'all_contacts': [
                {
                    'name': 'Тест Контакт',
                    'email': 'test@example.com',
                    'phone': '+7-111-222-3333',
                    'company': 'Тест Компания',
                    'priority': 9
                }
            ]
        }
        
        # Мокаем доступный Google Sheets API
        with patch.object(self.bridge.exporter, 'client', MagicMock()):
            with patch.object(self.bridge.exporter, 'export_results_by_date', return_value=True) as mock_export:
                # Тестируем экспорт
                result = self.bridge.process_and_export(self.test_date)
                
                # Проверяем результат
                self.assertTrue(result)
                
                # Проверяем, что экспорт был вызван
                mock_export.assert_called_once_with(self.test_date, mock_process.return_value)
                
        print("   ✅ Экспорт в Google Sheets работает корректно")
        
    def test_pipeline_components_integration(self):
        """🔗 Тест интеграции компонентов пайплайна"""
        print("\n🔗 Тестирование интеграции компонентов...")
        
        # Проверяем, что RateLimitManager интегрирован в процессор
        self.assertIsNotNone(self.bridge.processor.rate_limit_manager)
        
        # Проверяем, что процессор не в тестовом режиме (для реальной обработки)
        self.assertFalse(self.bridge.processor.test_mode)
        
        # Проверяем наличие необходимых методов
        self.assertTrue(hasattr(self.bridge, 'process_and_export'))
        self.assertTrue(hasattr(self.bridge, '_auto_fetch_emails'))
        self.assertTrue(hasattr(self.bridge, '_fallback_to_local_export'))
        
        print("   ✅ Интеграция компонентов корректна")
        
    def test_error_handling_in_pipeline(self):
        """⚠️ Тест обработки ошибок в пайплайне"""
        print("\n⚠️ Тестирование обработки ошибок...")
        
        # Мокаем ошибку в процессоре
        with patch.object(self.bridge.processor, 'process_emails_by_date', side_effect=Exception("Тестовая ошибка")):
            # Тестируем обработку ошибки
            result = self.bridge.process_and_export(self.test_date)
            
            # Проверяем, что ошибка обработана корректно
            self.assertFalse(result)
            
        print("   ✅ Обработка ошибок работает корректно")


if __name__ == '__main__':
    print("🧪 Запуск тестов полной цепочки обработки")
    print("=" * 50)
    
    # Запускаем тесты с подробным выводом
    unittest.main(verbosity=2, buffer=True)