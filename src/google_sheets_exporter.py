#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Экспортер результатов LLM анализа в Google Sheets
"""

import os
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

# Обеспечиваем правильный импорт модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread
# Замена oauth2client на google.oauth2
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class GoogleSheetsExporter:
    """📊 Экспорт результатов LLM анализа в Google Sheets"""
    
    def __init__(self):
        # Папки для данных - используем абсолютные пути от корня проекта
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        
        self.data_dir = project_root / "data"
        self.results_dir = self.data_dir / "llm_results"
        self.config_dir = project_root / "config"
        
        # Настройки Google Sheets API
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        self.credentials_path = self.config_dir / "service_account.json"
        
        print(f"   📁 Путь к конфигурации: {self.credentials_path}")
        
        if not self.credentials_path.exists():
            print(f"❌ Файл с учетными данными не найден: {self.credentials_path}")
            print("   Для работы с Google Sheets нужен файл service_account.json")
            self.client = None
            return
            
        try:
            creds = Credentials.from_service_account_file(
                str(self.credentials_path), scopes=scope)
            self.client = gspread.authorize(creds)
            print("🔑 Авторизация в Google Sheets API успешна")
        except Exception as e:
            print(f"❌ Ошибка авторизации в Google Sheets API: {e}")
            self.client = None
        
        # ID тестовой таблицы (при отсутствии берем из .env)
        self.spreadsheet_id = os.getenv('GOOGLE_SHEET_ID', '')
        
        print(f"📊 Инициализация экспортера Google Sheets")
        if self.spreadsheet_id:
            print(f"   🔗 ID таблицы: {self.spreadsheet_id}")
        else:
            print(f"   ⚠️ ID таблицы не указан в .env (GOOGLE_SHEET_ID)")
    
    def create_new_spreadsheet(self, title: str) -> Optional[str]:
        """📝 Создание новой таблицы Google Sheets"""
        
        if not self.client:
            print("❌ Клиент Google Sheets не инициализирован")
            return None
        
        try:
            spreadsheet = self.client.create(title)
            
            # Предоставляем доступ по email (если указан)
            share_email = os.getenv('GOOGLE_SHARE_EMAIL')
            if share_email:
                spreadsheet.share(share_email, perm_type='user', role='writer')
                print(f"✅ Доступ предоставлен: {share_email}")
            
            print(f"✅ Создана новая таблица: {title}")
            print(f"   URL: {spreadsheet.url}")
            
            # Создаем базовую структуру листов
            self._setup_spreadsheet_structure(spreadsheet)
            
            return spreadsheet.id
            
        except Exception as e:
            print(f"❌ Ошибка создания таблицы: {e}")
            return None
    
    def _setup_spreadsheet_structure(self, spreadsheet):
        """📋 Настройка структуры листов в таблице"""
        
        # Переименовываем первый лист
        worksheet = spreadsheet.get_worksheet(0)
        worksheet.update_title("Контакты")
        
        # Настраиваем заголовки для контактов
        headers = [
            "Дата", "Имя", "Email", "Телефон", "Организация", 
            "Должность", "Город", "Confidence", "Приоритет",
            "Тема письма", "Thread ID"
        ]
        worksheet.update('A1:K1', [headers])
        worksheet.format('A1:K1', {'textFormat': {'bold': True}})
        
        # Создаем лист для КП
        co_worksheet = spreadsheet.add_worksheet(title="Коммерческие предложения", rows=100, cols=20)
        co_headers = [
            "Дата", "От", "№ КП", "Дата КП", "Конечный пользователь",
            "Город", "Посредник", "Условия оплаты", "Срок поставки",
            "Доставка", "Действительно до", "Кто выставил", "Общая стоимость",
            "Валюта", "Thread ID"
        ]
        co_worksheet.update('A1:O1', [co_headers])
        co_worksheet.format('A1:O1', {'textFormat': {'bold': True}})
        
        # Создаем лист для статистики
        stats_worksheet = spreadsheet.add_worksheet(title="Статистика", rows=50, cols=10)
        stats_headers = [
            "Дата", "Писем обработано", "Контактов найдено", 
            "Писем с вложениями", "Вложений обработано", "КП найдено"
        ]
        stats_worksheet.update('A1:F1', [stats_headers])
        stats_worksheet.format('A1:F1', {'textFormat': {'bold': True}})
    
    def export_results_by_date(self, date: str, results: Dict = None) -> bool:
        """📊 Экспорт результатов за конкретную дату
        
        Args:
            date (str): Дата в формате YYYY-MM-DD
            results (Dict, optional): Результаты анализа. Если None, загружаются из файла.
            
        Returns:
            bool: True если экспорт прошел успешно, False в противном случае
        """
        
        if not self.client:
            print("❌ Клиент Google Sheets не инициализирован")
            return False
        
        # Если результаты не переданы, загружаем их из файла
        if results is None:
            # Загружаем результаты
            results_path = self.results_dir / f"llm_analysis_{date.replace('-', '')}.json"
            
            if not results_path.exists():
                print(f"❌ Результаты анализа за {date} не найдены")
                return False
            
            try:
                with open(results_path, 'r', encoding='utf-8') as f:
                    results = json.load(f)
            except Exception as e:
                print(f"❌ Ошибка загрузки результатов: {e}")
                return False
        
        # Если ID таблицы не указан, создаем новую
        if not self.spreadsheet_id:
            title = f"Контакты из деловой переписки ({date})"
            self.spreadsheet_id = self.create_new_spreadsheet(title)
            if not self.spreadsheet_id:
                return False
        
        try:
            # Открываем таблицу
            print(f"   🔗 Открываю таблицу: {self.spreadsheet_id}")
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            print(f"   ✅ Таблица открыта успешно")
            
            # Экспортируем контакты
            print(f"   👤 Начинаю экспорт контактов...")
            self._export_contacts(spreadsheet, results, date)
            
            # Экспортируем КП
            print(f"   💼 Начинаю экспорт КП...")
            self._export_commercial_offers(spreadsheet, results, date)
            
            # Экспортируем статистику
            print(f"   📊 Начинаю экспорт статистики...")
            self._export_statistics(spreadsheet, results, date)
            
            print(f"✅ Данные за {date} успешно экспортированы")
            print(f"   URL таблицы: https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка экспорта в Google Sheets: {e}")
            import traceback
            print(f"   🔍 Детали ошибки:")
            traceback.print_exc()
            return False
    
    def _export_contacts(self, spreadsheet, results: Dict, date: str):
        """👤 Экспорт контактов в таблицу"""
        
        worksheet = spreadsheet.worksheet("Контакты")
        
        # Получаем все контакты из результатов обработки email
        all_contacts = []
        for email_result in results.get('emails_results', []):
            email_contacts = email_result.get('contacts', [])
            if email_contacts:
                # Добавляем метаданные email к каждому контакту
                for contact in email_contacts:
                    contact_with_metadata = contact.copy()
                    contact_with_metadata['email_thread_id'] = email_result.get('original_email', {}).get('thread_id', 'неизвестно')
                    contact_with_metadata['email_subject'] = email_result.get('original_email', {}).get('subject', 'неизвестно')
                    contact_with_metadata['email_from'] = email_result.get('original_email', {}).get('from', 'неизвестно')
                    all_contacts.append(contact_with_metadata)
        
        if not all_contacts:
            print("   ℹ️ Контакты для экспорта не найдены")
            return
        
        # Подготавливаем данные для вставки
        contact_rows = []
        for contact in all_contacts:
            # Формируем строку для вставки
            row = [
                date,
                contact.get('name', ''),
                contact.get('email', ''),
                contact.get('phone', ''),
                contact.get('organization', ''),
                contact.get('position', ''),
                contact.get('city', ''),
                contact.get('confidence', 0),
                contact.get('priority', {}).get('level', 'низкий'),
                contact.get('email_subject', 'неизвестно'),
                contact.get('email_thread_id', 'неизвестно')
            ]
            contact_rows.append(row)
        
        # Получаем следующую пустую строку для вставки
        next_row = len(worksheet.get_all_values()) + 1
        
        # Вставляем данные
        if contact_rows:
            cell_range = f"A{next_row}:K{next_row + len(contact_rows) - 1}"
            worksheet.update(cell_range, contact_rows)
            print(f"   ✅ Экспортировано контактов: {len(contact_rows)}")
    
    def _export_commercial_offers(self, spreadsheet, results: Dict, date: str):
        """💼 Экспорт коммерческих предложений в таблицу"""
        
        worksheet = spreadsheet.worksheet("Коммерческие предложения")
        
        # Получаем все КП из результатов обработки email
        all_offers = []
        for email_result in results.get('emails_results', []):
            commercial_analysis = email_result.get('commercial_analysis', {})
            if commercial_analysis and commercial_analysis.get('commercial_offer_found'):
                # Добавляем метаданные email к КП
                offer_with_metadata = commercial_analysis.copy()
                offer_with_metadata['email_thread_id'] = email_result.get('original_email', {}).get('thread_id', 'неизвестно')
                offer_with_metadata['email_subject'] = email_result.get('original_email', {}).get('subject', 'неизвестно')
                offer_with_metadata['email_from'] = email_result.get('original_email', {}).get('from', 'неизвестно')
                all_offers.append(offer_with_metadata)
        
        if not all_offers:
            print("   ℹ️ Коммерческие предложения для экспорта не найдены")
            return
        
        # Подготавливаем данные для вставки
        offer_rows = []
        for offer_data in all_offers:
            # Формируем строку для вставки
            row = [
                date,
                offer_data.get('email_from', 'неизвестно'),
                offer_data.get('offer_number', 'б/н'),
                offer_data.get('offer_date', ''),
                offer_data.get('end_user', ''),
                offer_data.get('end_user_city', ''),
                offer_data.get('intermediary', ''),
                offer_data.get('payment_terms', ''),
                offer_data.get('delivery_time', ''),
                offer_data.get('delivery_terms', ''),
                offer_data.get('valid_until', ''),
                offer_data.get('issued_by', ''),
                offer_data.get('total_cost', ''),
                offer_data.get('currency', 'RUB'),
                offer_data.get('email_thread_id', 'неизвестно')
            ]
            offer_rows.append(row)
        
        # Получаем следующую пустую строку для вставки
        next_row = len(worksheet.get_all_values()) + 1
        
        # Вставляем данные
        if offer_rows:
            cell_range = f"A{next_row}:O{next_row + len(offer_rows) - 1}"
            worksheet.update(cell_range, offer_rows)
            print(f"   ✅ Экспортировано КП: {len(offer_rows)}")
    
    def _export_statistics(self, spreadsheet, results: Dict, date: str):
        """📊 Экспорт статистики в таблицу"""
        
        worksheet = spreadsheet.worksheet("Статистика")
        
        # Получаем статистику
        stats = results.get('statistics', {})
        
        # Формируем строку для вставки
        stats_row = [
            date,
            stats.get('emails_processed', 0),
            stats.get('total_contacts_found', 0),
            stats.get('emails_with_attachments', 0),
            stats.get('attachments_processed', 0),
            stats.get('commercial_offers_found', 0)
        ]
        
        # Получаем следующую пустую строку для вставки
        next_row = len(worksheet.get_all_values()) + 1
        
        # Вставляем данные
        cell_range = f"A{next_row}:F{next_row}"
        worksheet.update(cell_range, [stats_row])
        print(f"   ✅ Экспортирована статистика за {date}")
    
    def export_multiple_dates(self, start_date: str, end_date: str, results_dict: Dict[str, Dict] = None) -> bool:
        """📅 Экспорт результатов за диапазон дат
        
        Args:
            start_date (str): Начальная дата в формате YYYY-MM-DD
            end_date (str): Конечная дата в формате YYYY-MM-DD
            results_dict (Dict[str, Dict], optional): Словарь с результатами, где ключ - дата.
                Если None, результаты загружаются из файлов.
                
        Returns:
            bool: True если хотя бы одна дата обработана успешно
        """
        
        from datetime import datetime, timedelta
        import logging
        
        # Парсим даты
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            logging.error(f"Неверный формат даты при экспорте: {start_date} - {end_date}")
            print("❌ Неверный формат даты. Используйте формат YYYY-MM-DD")
            return False
        
        if start > end:
            logging.error(f"Начальная дата {start_date} больше конечной {end_date}")
            print("❌ Начальная дата должна быть меньше или равна конечной")
            return False
        
        # Проходим по всем датам в диапазоне
        current = start
        success_count = 0
        
        # Создаем одну таблицу для всего диапазона
        if not self.spreadsheet_id:
            title = f"Контакты из деловой переписки ({start_date} - {end_date})"
            self.spreadsheet_id = self.create_new_spreadsheet(title)
            if not self.spreadsheet_id:
                logging.error("Не удалось создать таблицу для экспорта диапазона дат")
                print("❌ Не удалось создать таблицу для экспорта")
                return False
        
        # Проверяем, что results_dict не None перед использованием
        if results_dict is None:
            results_dict = {}
            logging.warning("Словарь результатов не передан, будет выполнена загрузка из файлов")
            print("⚠️ Словарь результатов не передан, загружаю из файлов...")
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            print(f"\n📅 Обработка даты: {date_str}")
            
            # Получаем результаты для текущей даты, если они переданы
            current_results = results_dict.get(date_str)
            
            # Если результаты не переданы, проверяем наличие файла
            if current_results is None:
                results_path = self.results_dir / f"llm_analysis_{date_str.replace('-', '')}.json"
                
                if results_path.exists():
                     # Загружаем результаты из файла
                     try:
                         with open(results_path, 'r', encoding='utf-8') as f:
                             file_results = json.load(f)
                         if self.export_results_by_date(date_str, file_results):
                             success_count += 1
                     except Exception as e:
                         logging.error(f"Ошибка загрузки результатов из файла {results_path}: {e}")
                         print(f"❌ Ошибка загрузки результатов из файла: {e}")
                         continue
                else:
                    logging.warning(f"Результаты анализа за {date_str} не найдены")
                    print(f"   ⚠️ Результаты анализа за {date_str} не найдены")
            else:
                # Используем переданные результаты
                if self.export_results_by_date(date_str, current_results):
                    success_count += 1
            
            # Переходим к следующей дате
            current += timedelta(days=1)
        
        print(f"\n✅ Экспорт завершен. Успешно обработано дат: {success_count}")
        if self.spreadsheet_id:
            print(f"   🔗 URL таблицы: https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}")
        
        return success_count > 0


def main():
    """🚀 Основная функция для тестирования экспортера"""
    
    print("\n" + "="*60)
    print("📊 ТЕСТИРОВАНИЕ ЭКСПОРТА В GOOGLE SHEETS")
    print("="*60)
    
    exporter = GoogleSheetsExporter()
    
    if not exporter.client:
        print("\n❌ Невозможно продолжить без настроенного Google Sheets API")
        return
    
    # Тестовый диапазон дат
    test_start_date = "2025-07-28"
    test_end_date = "2025-07-31"
    
    print(f"\n📅 Тестирование на диапазоне дат: {test_start_date} - {test_end_date}")
    
    # Создаем новую таблицу, если ID не указан
    if not exporter.spreadsheet_id:
        title = f"Тестовый экспорт контактов ({test_start_date} - {test_end_date})"
        spreadsheet_id = exporter.create_new_spreadsheet(title)
        if spreadsheet_id:
            exporter.spreadsheet_id = spreadsheet_id
        else:
            print("❌ Не удалось создать таблицу")
            return
    
    # Экспортируем данные
    result = exporter.export_multiple_dates(test_start_date, test_end_date)
    
    if result:
        print("\n✅ Тестирование завершено успешно!")
    else:
        print("\n❌ При тестировании возникли ошибки")


if __name__ == '__main__':
    main()
