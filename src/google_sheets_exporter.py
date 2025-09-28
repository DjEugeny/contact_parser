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

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.paths import CONFIG_DIR, DATA_DIR

# Обеспечиваем правильный импорт модулей (совместимость со старыми скриптами)
sys.path.append(str(CURRENT_DIR))
sys.path.append(str(PROJECT_ROOT))

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
        
        self.data_dir = DATA_DIR
        self.results_dir = self.data_dir / "llm_results"
        self.config_dir = CONFIG_DIR
        
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
        
        # Переименовываем первый лист для организаций
        worksheet = spreadsheet.get_worksheet(0)
        worksheet.update_title("Организации")
        
        # Настраиваем заголовки для организаций
        org_headers = [
            "Дата", "ID организации", "Название", "ИНН", "Сайт", "Город", 
            "Адрес", "Email (основные)", "Телефоны", "Тема письма", "Thread ID"
        ]
        worksheet.update('A1:K1', [org_headers])
        worksheet.format('A1:K1', {'textFormat': {'bold': True}})
        
        # Создаем лист для персональных контактов
        contacts_worksheet = spreadsheet.add_worksheet(title="Контакты", rows=100, cols=15)
        contact_headers = [
            "Дата", "ID контакта", "Имя", "ID организации", "Должность", 
            "Email", "Телефоны (тип: номер)", "Город", "Адрес", "Confidence",
            "Тема письма", "Thread ID"
        ]
        contacts_worksheet.update('A1:L1', [contact_headers])
        contacts_worksheet.format('A1:L1', {'textFormat': {'bold': True}})
        
        # Создаем лист для КП
        co_worksheet = spreadsheet.add_worksheet(title="Коммерческие предложения", rows=100, cols=20)
        co_headers = [
            "Дата", "№ КП", "Дата КП", "Конечный пользователь", "ИНН конечного пользователя",
            "Посредник", "Данные посредника", "Условия оплаты", "Срок поставки",
            "Условия доставки", "Действительно до", "Общая стоимость", "Комментарии",
            "Тема письма", "Thread ID"
        ]
        co_worksheet.update('A1:O1', [co_headers])
        co_worksheet.format('A1:O1', {'textFormat': {'bold': True}})
        
        # Создаем лист для статистики
        stats_worksheet = spreadsheet.add_worksheet(title="Статистика", rows=50, cols=10)
        stats_headers = [
            "Дата", "Писем обработано", "Организаций найдено", "Контактов найдено",
            "Писем с вложениями", "Вложений обработано", "КП найдено"
        ]
        stats_worksheet.update('A1:G1', [stats_headers])
        stats_worksheet.format('A1:G1', {'textFormat': {'bold': True}})
    
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
            
            # Экспортируем организации
            print(f"   🏢 Начинаю экспорт организаций...")
            self._export_organizations(spreadsheet, results, date)
            
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
    
    def _export_organizations(self, spreadsheet, results: Dict, date: str):
        """🏢 Экспорт организаций в таблицу"""
        
        worksheet = spreadsheet.worksheet("Организации")
        
        # Получаем все организации из результатов обработки email
        all_organizations = []
        for email_result in results.get('emails_results', []):
            email_organizations = email_result.get('organizations', [])
            if email_organizations:
                # Добавляем метаданные email к каждой организации
                for org in email_organizations:
                    org_with_metadata = org.copy()
                    org_with_metadata['email_thread_id'] = email_result.get('original_email', {}).get('thread_id', 'неизвестно')
                    org_with_metadata['email_subject'] = email_result.get('original_email', {}).get('subject', 'неизвестно')
                    org_with_metadata['email_from'] = email_result.get('original_email', {}).get('from', 'неизвестно')
                    all_organizations.append(org_with_metadata)
        
        if not all_organizations:
            print("   ℹ️ Организации для экспорта не найдены")
            return
        
        # Подготавливаем данные для вставки
        org_rows = []
        for org in all_organizations:
            # Форматируем телефоны
            phones_formatted = ""
            if org.get('phones'):
                phone_list = []
                for phone in org['phones']:
                    if isinstance(phone, dict):
                        phone_type = phone.get('type', 'unknown')
                        phone_number = phone.get('number', '')
                        phone_list.append(f"{phone_type}: {phone_number}")
                    else:
                        phone_list.append(str(phone))
                phones_formatted = "; ".join(phone_list)
            
            # Форматируем основные email
            main_emails = "; ".join(org.get('main_emails', []))
            
            # Формируем строку для вставки
            row = [
                date,
                org.get('id', ''),
                org.get('name', ''),
                org.get('inn', ''),
                org.get('website', ''),
                org.get('city', ''),
                org.get('address', ''),
                main_emails,
                phones_formatted,
                org.get('email_subject', 'неизвестно'),
                org.get('email_thread_id', 'неизвестно')
            ]
            org_rows.append(row)
        
        # Получаем следующую пустую строку для вставки
        next_row = len(worksheet.get_all_values()) + 1
        
        # Вставляем данные
        if org_rows:
            cell_range = f"A{next_row}:K{next_row + len(org_rows) - 1}"
            worksheet.update(cell_range, org_rows)
            print(f"   ✅ Экспортировано организаций: {len(org_rows)}")
    
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
            # Форматируем телефоны
            phones_formatted = ""
            if contact.get('phones'):
                phone_list = []
                for phone in contact['phones']:
                    if isinstance(phone, dict):
                        phone_type = phone.get('type', 'unknown')
                        phone_number = phone.get('number', '')
                        phone_list.append(f"{phone_type}: {phone_number}")
                    else:
                        phone_list.append(str(phone))
                phones_formatted = "; ".join(phone_list)
            elif contact.get('phone'):
                phones_formatted = contact.get('phone')
            
            # Формируем строку для вставки
            row = [
                date,
                contact.get('id', ''),
                contact.get('name', ''),
                contact.get('organization_id', ''),
                contact.get('position', ''),
                contact.get('email', ''),
                phones_formatted,
                contact.get('city', ''),
                contact.get('address', ''),
                contact.get('confidence', 0),
                contact.get('email_subject', 'неизвестно'),
                contact.get('email_thread_id', 'неизвестно')
            ]
            contact_rows.append(row)
        
        # Получаем следующую пустую строку для вставки
        next_row = len(worksheet.get_all_values()) + 1
        
        # Вставляем данные
        if contact_rows:
            cell_range = f"A{next_row}:L{next_row + len(contact_rows) - 1}"
            worksheet.update(cell_range, contact_rows)
            print(f"   ✅ Экспортировано контактов: {len(contact_rows)}")
    
    def _export_commercial_offers(self, spreadsheet, results: Dict, date: str):
        """💼 Экспорт коммерческих предложений в таблицу"""

        worksheet = spreadsheet.worksheet("Коммерческие предложения")

        # Получаем все КП из результатов обработки email
        all_offers = []
        for email_result in results.get('emails_results', []):
            # Поддержка новой структуры (Фаза 1)
            commercial_offers = email_result.get('commercial_offers', [])
            if commercial_offers and isinstance(commercial_offers, list):
                for offer in commercial_offers:
                    if offer.get('found', False):
                        # Добавляем метаданные email к КП
                        offer_with_metadata = offer.copy()
                        offer_with_metadata['email_thread_id'] = email_result.get('original_email', {}).get('thread_id', 'неизвестно')
                        offer_with_metadata['email_subject'] = email_result.get('original_email', {}).get('subject', 'неизвестно')
                        offer_with_metadata['email_from'] = email_result.get('original_email', {}).get('from', 'неизвестно')
                        all_offers.append(offer_with_metadata)

            # Обратная совместимость со старой структурой
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
            # Новая структура (Фаза 1)
            if 'supplier' in offer_data:
                row = [
                    date,
                    offer_data.get('email_from', 'неизвестно'),
                    offer_data.get('supplier', 'неизвестно'),  # Поставщик
                    ', '.join(offer_data.get('products', [])),  # Продукты
                    offer_data.get('total_amount', ''),  # Сумма
                    offer_data.get('currency', 'RUB'),  # Валюта
                    offer_data.get('valid_until', ''),  # Срок действия
                    offer_data.get('email_thread_id', 'неизвестно')
                ]
            # Старая структура (обратная совместимость)
            else:
                # Форматируем данные посредника
                intermediary_data = ""
                if offer_data.get('intermediary_data'):
                    intermediary_info = offer_data['intermediary_data']
                    if isinstance(intermediary_info, dict):
                        parts = []
                        if intermediary_info.get('name'):
                            parts.append(f"Название: {intermediary_info['name']}")
                        if intermediary_info.get('inn'):
                            parts.append(f"ИНН: {intermediary_info['inn']}")
                        if intermediary_info.get('contact'):
                            parts.append(f"Контакт: {intermediary_info['contact']}")
                        intermediary_data = "; ".join(parts)
                    else:
                        intermediary_data = str(intermediary_info)
                
                row = [
                    date,
                    offer_data.get('offer_number', 'б/н'),
                    offer_data.get('offer_date', ''),
                    offer_data.get('end_user', ''),
                    offer_data.get('end_user_inn', ''),
                    offer_data.get('intermediary', ''),
                    intermediary_data,
                    offer_data.get('payment_terms', ''),
                    offer_data.get('delivery_time', ''),
                    offer_data.get('delivery_conditions', ''),
                    offer_data.get('valid_until', ''),
                    offer_data.get('total_cost', ''),
                    offer_data.get('comments', ''),
                    offer_data.get('email_subject', 'неизвестно'),
                    offer_data.get('email_thread_id', 'неизвестно')
                ]
            offer_rows.append(row)

        # Получаем следующую пустую строку для вставки
        next_row = len(worksheet.get_all_values()) + 1

        # Вставляем данные
        if offer_rows:
            # Для новой структуры меньше колонок
            if 'supplier' in all_offers[0]:
                cell_range = f"A{next_row}:H{next_row + len(offer_rows) - 1}"
            else:
                cell_range = f"A{next_row}:O{next_row + len(offer_rows) - 1}"
            worksheet.update(cell_range, offer_rows)
            print(f"   ✅ Экспортировано КП: {len(offer_rows)}")
    
    def _export_statistics(self, spreadsheet, results: Dict, date: str):
        """📊 Экспорт статистики в таблицу"""
        
        worksheet = spreadsheet.worksheet("Статистика")
        
        # Подсчитываем статистику из результатов
        emails_processed = len(results.get('emails_results', []))
        
        organizations_found = 0
        contacts_found = 0
        commercial_offers_found = 0
        emails_with_attachments = 0
        attachments_processed = 0
        
        for email_result in results.get('emails_results', []):
            # Подсчитываем организации
            organizations_found += len(email_result.get('organizations', []))
            
            # Подсчитываем контакты
            contacts_found += len(email_result.get('contacts', []))
            
            # Подсчитываем КП
            commercial_offers_found += len(email_result.get('commercial_offers', []))
            
            # Подсчитываем вложения
            attachments = email_result.get('attachments', [])
            if attachments:
                emails_with_attachments += 1
                attachments_processed += len(attachments)
        
        # Формируем строку для вставки
        stats_row = [
            date,
            emails_processed,
            organizations_found,
            contacts_found,
            emails_with_attachments,
            attachments_processed,
            commercial_offers_found
        ]
        
        # Получаем следующую пустую строку для вставки
        next_row = len(worksheet.get_all_values()) + 1
        
        # Вставляем данные
        cell_range = f"A{next_row}:G{next_row}"
        worksheet.update(cell_range, [stats_row])
        print(f"   ✅ Экспортирована статистика за {date}: {emails_processed} писем, {organizations_found} организаций, {contacts_found} контактов, {commercial_offers_found} КП")
    
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


def get_available_dates():
    """📅 Получение списка доступных дат из папки data/emails"""
    from pathlib import Path
    import os
    
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    emails_dir = DATA_DIR / "emails"
    
    if not emails_dir.exists():
        print(f"❌ Папка с данными не найдена: {emails_dir}")
        return []
    
    dates = []
    for item in os.listdir(emails_dir):
        item_path = emails_dir / item
        if item_path.is_dir() and item.startswith('2025-'):
            dates.append(item)
    
    return sorted(dates)

def show_date_menu():
    """📋 Показать меню выбора дат"""
    dates = get_available_dates()
    
    if not dates:
        print("❌ Доступные даты не найдены")
        return None
    
    print("\n📅 Доступные даты:")
    for i, date in enumerate(dates, 1):
        print(f"   {i:2d}. {date}")
    
    print(f"   {len(dates)+1:2d}. Диапазон дат")
    print(f"   {len(dates)+2:2d}. Все даты")
    print("    0. Назад")
    
    while True:
        try:
            choice = input("\n🎯 Выберите опцию (номер или дату YYYY-MM-DD): ").strip()
            
            if choice == '0':
                return None
            
            # Проверяем, не ввел ли пользователь дату напрямую
            if len(choice) == 10 and choice.count('-') == 2:
                # Возможно, это дата в формате YYYY-MM-DD
                try:
                    from datetime import datetime
                    datetime.strptime(choice, '%Y-%m-%d')
                    # Проверяем, есть ли такая дата в списке
                    if choice in dates:
                        print(f"✅ Выбрана дата: {choice}")
                        return [choice]
                    else:
                        print(f"❌ Дата {choice} не найдена в доступных датах")
                        print("   Используйте номер из списка выше")
                        continue
                except ValueError:
                    # Не является корректной датой, обрабатываем как номер
                    pass
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(dates):
                return [dates[choice_num - 1]]
            elif choice_num == len(dates) + 1:
                # Диапазон дат
                print("\n📊 Выбор диапазона дат:")
                start_idx = int(input(f"Начальная дата (1-{len(dates)}): ")) - 1
                end_idx = int(input(f"Конечная дата (1-{len(dates)}): ")) - 1
                
                if 0 <= start_idx <= end_idx < len(dates):
                    return dates[start_idx:end_idx + 1]
                else:
                    print("❌ Неверный диапазон дат")
                    continue
            elif choice_num == len(dates) + 2:
                return dates
            else:
                print("❌ Неверный выбор")
                continue
                
        except (ValueError, IndexError) as e:
            print(f"❌ Введите корректный номер или дату в формате YYYY-MM-DD (ошибка: {e})")
            continue
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            continue

def run_interactive_mode():
    """🎮 Интерактивный режим работы с Google Sheets"""
    print("\n" + "="*60)
    print("📊 GOOGLE SHEETS ЭКСПОРТЕР - ИНТЕРАКТИВНЫЙ РЕЖИМ")
    print("="*60)
    
    exporter = GoogleSheetsExporter()
    
    if not exporter.client:
        print("\n❌ Невозможно продолжить без настроенного Google Sheets API")
        print("   Убедитесь, что файл service_account.json находится в папке config/")
        return
    
    while True:
        print("\n📋 Главное меню:")
        print("   1. Экспорт данных за выбранные даты")
        print("   2. Создать новую таблицу")
        print("   3. Проверить подключение к Google Sheets")
        print("   4. Показать информацию о текущей таблице")
        print("   0. Выход")
        
        choice = input("\n🎯 Выберите действие (номер): ").strip()
        
        if choice == '0':
            print("👋 До свидания!")
            break
        elif choice == '1':
            # Экспорт данных
            selected_dates = show_date_menu()
            if selected_dates:
                export_selected_dates(exporter, selected_dates)
        elif choice == '2':
            # Создание новой таблицы
            create_new_spreadsheet_interactive(exporter)
        elif choice == '3':
            # Проверка подключения
            test_connection(exporter)
        elif choice == '4':
            # Информация о таблице
            show_spreadsheet_info(exporter)
        else:
            print("❌ Неверный выбор")

def export_selected_dates(exporter, dates):
    """📊 Экспорт данных за выбранные даты"""
    print(f"\n🚀 Начинаю экспорт данных за {len(dates)} дат(ы)")
    
    # Проверяем, есть ли активная таблица
    if not exporter.spreadsheet_id:
        print("⚠️ Активная таблица не найдена. Создаем новую...")
        title = f"Экспорт контактов ({dates[0]} - {dates[-1]})"
        spreadsheet_id = exporter.create_new_spreadsheet(title)
        if spreadsheet_id:
            exporter.spreadsheet_id = spreadsheet_id
            print(f"✅ Создана новая таблица: {title}")
        else:
            print("❌ Не удалось создать таблицу")
            return
    
    success_count = 0
    
    for date in dates:
        print(f"\n📅 Экспорт данных за {date}...")
        
        try:
            success = exporter.export_results_by_date(date)
            if success:
                print(f"   ✅ Данные за {date} экспортированы")
                success_count += 1
            else:
                print(f"   ❌ Ошибка экспорта за {date}")
        except Exception as e:
            print(f"   ❌ Ошибка экспорта за {date}: {e}")
    
    print(f"\n🎉 Экспорт завершен! Успешно обработано дат: {success_count}/{len(dates)}")
    
    if exporter.spreadsheet_id:
        print(f"🔗 URL таблицы: https://docs.google.com/spreadsheets/d/{exporter.spreadsheet_id}")

def create_new_spreadsheet_interactive(exporter):
    """📝 Интерактивное создание новой таблицы"""
    print("\n📝 Создание новой Google Sheets таблицы")
    
    title = input("Введите название таблицы: ").strip()
    if not title:
        title = f"Контакты LLM анализ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        print(f"Используется название по умолчанию: {title}")
    
    print(f"\n🚀 Создаю таблицу '{title}'...")
    
    try:
        spreadsheet_id = exporter.create_new_spreadsheet(title)
        if spreadsheet_id:
            exporter.spreadsheet_id = spreadsheet_id
            print(f"✅ Таблица создана успешно!")
            print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        else:
            print("❌ Не удалось создать таблицу")
    except Exception as e:
        print(f"❌ Ошибка создания таблицы: {e}")

def test_connection(exporter):
    """🔧 Проверка подключения к Google Sheets"""
    print("\n🔧 Проверка подключения к Google Sheets...")
    
    try:
        if exporter.client:
            # Пытаемся получить список таблиц
            spreadsheets = exporter.client.openall()
            print(f"✅ Подключение успешно! Доступно таблиц: {len(spreadsheets)}")
            
            if spreadsheets:
                print("\n📋 Последние 5 таблиц:")
                for i, sheet in enumerate(spreadsheets[:5], 1):
                    print(f"   {i}. {sheet.title}")
        else:
            print("❌ Клиент Google Sheets не инициализирован")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

def show_spreadsheet_info(exporter):
    """📊 Показать информацию о текущей таблице"""
    print("\n📊 Информация о текущей таблице:")
    
    if not exporter.spreadsheet_id:
        print("❌ Активная таблица не выбрана")
        return
    
    try:
        spreadsheet = exporter.client.open_by_key(exporter.spreadsheet_id)
        print(f"📝 Название: {spreadsheet.title}")
        print(f"🔗 ID: {exporter.spreadsheet_id}")
        print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{exporter.spreadsheet_id}")
        
        worksheets = spreadsheet.worksheets()
        print(f"📄 Листов: {len(worksheets)}")
        
        for i, worksheet in enumerate(worksheets, 1):
            print(f"   {i}. {worksheet.title} ({worksheet.row_count} строк, {worksheet.col_count} столбцов)")
            
    except Exception as e:
        print(f"❌ Ошибка получения информации о таблице: {e}")

def main():
    """🚀 Основная функция"""
    import sys
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Тестовый режим
        print("🧪 Запуск в тестовом режиме...")
        
        print("\n" + "="*60)
        print("📊 ТЕСТИРОВАНИЕ ЭКСПОРТА В GOOGLE SHEETS")
        print("="*60)
        
        exporter = GoogleSheetsExporter()
        
        if not exporter.client:
            print("\n❌ Невозможно продолжить без настроенного Google Sheets API")
            return
        
        # Диапазон дат для обработки
        test_start_date = "2025-07-04"
        test_end_date = "2025-07-04"
        
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
    else:
        # Интерактивный режим
        run_interactive_mode()


if __name__ == '__main__':
    main()
