#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔄 Мост между LLM процессором и Google Sheets экспортером
"""

import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Добавляем путь к текущей директории для импортов
sys.path.append(str(Path(__file__).parent))

# Импортируем наши модули
from integrated_llm_processor import IntegratedLLMProcessor
from google_sheets_exporter import GoogleSheetsExporter
from local_exporter import LocalDataExporter


class LLM_Sheets_Bridge:
    """🔄 Мост для интеграции OCR + LLM + Sheets"""
    
    def __init__(self):
        # Инициализируем процессор с отключенным тестовым режимом
        self.processor = IntegratedLLMProcessor(test_mode=False)
        
        # GoogleSheetsExporter теперь сам правильно определяет пути
        self.exporter = GoogleSheetsExporter()
        
        # Локальный экспортер как fallback
        self.local_exporter = LocalDataExporter()
        
        print("🔄 Инициализация моста OCR + LLM + Google Sheets")
        
        # Проверяем доступность Google Sheets API
        if self.exporter.client:
            print(f"   ✅ Google Sheets API инициализирован")
        else:
            print(f"   ❌ Google Sheets API не инициализирован")
            print(f"   🔑 Путь к service_account.json: {self.exporter.credentials_path}")
        
        print(f"   📊 Локальный экспортер: ✅ Готов к работе")
        
    def _auto_fetch_emails(self, date: str) -> bool:
        """📧 Автоматическая загрузка писем с сервера при их отсутствии
        
        Args:
            date: Дата в формате YYYY-MM-DD
            
        Returns:
            bool: True если загрузка прошла успешно, False в противном случае
        """
        try:
            print(f"📧 Запуск автоматической загрузки писем за {date}...")
            
            # Путь к advanced_email_fetcher.py
            fetcher_path = Path(__file__).parent / "advanced_email_fetcher.py"
            
            if not fetcher_path.exists():
                print(f"❌ Файл {fetcher_path} не найден")
                return False
            
            # Запускаем advanced_email_fetcher.py с указанной датой
            cmd = [sys.executable, str(fetcher_path), "--date", date]
            print(f"   🔧 Команда: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 минут таймаут
            )
            
            if result.returncode == 0:
                print(f"   ✅ Письма успешно загружены за {date}")
                if result.stdout:
                    print(f"   📝 Вывод: {result.stdout.strip()}")
                return True
            else:
                print(f"   ❌ Ошибка загрузки писем: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ Таймаут при загрузке писем за {date}")
            return False
        except Exception as e:
            print(f"   ❌ Исключение при загрузке писем: {e}")
            return False
    
    def process_and_export(self, date: str, create_new_sheet: bool = False, max_emails: int = None) -> bool:
        """📅 Обработка и экспорт данных за одну дату
        
        Args:
            date (str): Дата в формате YYYY-MM-DD
            create_new_sheet (bool): Создать новую таблицу
            max_emails (int, optional): Максимальное количество писем для обработки
            
        Returns:
            bool: True если обработка и экспорт прошли успешно, False в противном случае
        """
        
        import logging
        logging.info(f"Начало обработки и экспорта данных за {date}")
        
        print(f"\n{'='*60}")
        print(f"🔄 ПОЛНЫЙ ЦИКЛ ОБРАБОТКИ ЗА {date}")
        print(f"{'='*60}")
        
        # Шаг 1: Обработка данных через LLM
        print("\n📄 ШАГ 1: Анализ писем и вложений с помощью LLM")
        
        # Обрабатываем реальные данные из почты
        try:
            llm_results = self.processor.process_emails_by_date(date, max_emails=max_emails)
            
            # Проверяем, есть ли письма для обработки
            emails_processed = llm_results.get('statistics', {}).get('emails_processed', 0)
            
            if emails_processed == 0:
                print(f"📭 Письма за {date} не найдены. Запускаем автоматическую загрузку...")
                
                # Пытаемся загрузить письма с сервера
                if self._auto_fetch_emails(date):
                    print(f"🔄 Повторная обработка после загрузки писем...")
                    # Повторно обрабатываем после загрузки
                    llm_results = self.processor.process_emails_by_date(date, max_emails=max_emails)
                    emails_processed = llm_results.get('statistics', {}).get('emails_processed', 0)
                    
                    if emails_processed == 0:
                        print(f"📭 После загрузки письма за {date} всё ещё не найдены")
                        return False
                else:
                    print(f"❌ Не удалось загрузить письма за {date}")
                    return False
            
            if not llm_results or 'emails_processed' not in llm_results.get('statistics', {}):
                logging.error(f"Не удалось обработать данные за {date}")
                print(f"❌ Не удалось обработать данные за {date}")
                return False
                
            # Сохраняем результаты в атрибуте statistics для использования в _print_stats
            self.processor.statistics = llm_results.get('statistics', {})
            self.processor.contacts = llm_results.get('all_contacts', [])
                
            # Проверяем, были ли найдены контакты
            if llm_results.get('summary', {}).get('total_contacts', 0) == 0:
                logging.warning(f"За {date} не найдено контактов")
                print(f"⚠️ За {date} не найдено контактов")
                print(f"   Проверьте, есть ли письма за эту дату")
                
            # Выводим статистику обработки
            self._print_stats()
        except Exception as e:
            logging.error(f"Ошибка при обработке данных за {date}: {e}")
            print(f"❌ Ошибка при обработке данных: {e}")
            return False
        
        # Шаг 2: Экспорт результатов в Google Sheets
        print("\n📊 ШАГ 2: Экспорт результатов в Google Sheets")
        
        # Проверяем доступность Google Sheets API
        if not self.exporter.client:
            logging.warning("Google Sheets API не инициализирован, переключение на локальный экспорт")
            print("❌ Google Sheets API не инициализирован")
            print("  Проверьте файл config/service_account.json и настройки API")
            print("  Переключаюсь на локальный экспорт...")
            return self._fallback_to_local_export(date, llm_results)
        
        try:
            # Если нужно создать новую таблицу
            if create_new_sheet:
                title = f"Контакты из деловой переписки ({date})"
                try:
                    sheet_id = self.exporter.create_new_spreadsheet(title)
                    if sheet_id:
                        self.exporter.spreadsheet_id = sheet_id
                        logging.info(f"Создана новая таблица: {title} с ID: {sheet_id}")
                        print(f"✅ Создана новая таблица: {title}")
                        print(f"   ID: {sheet_id}")
                    else:
                        logging.error("Не удалось создать новую таблицу Google Sheets")
                        print("❌ Не удалось создать новую таблицу")
                        print("  Возможные причины:")
                        print("  1. Недостаточно прав в service_account.json")
                        print("  2. Google Drive API не включен в консоли Google")
                        print("  3. Проверьте подключение к интернету")
                        print("  4. Превышена квота хранилища Google Drive")
                        print("  Переключаюсь на локальный экспорт...")
                        return self._fallback_to_local_export(date, llm_results)
                except Exception as e:
                    logging.error(f"Ошибка создания таблицы: {e}")
                    print(f"❌ Ошибка создания таблицы: {e}")
                    print("  Для активации Google Drive API перейдите по ссылке:")
                    print("  https://console.developers.google.com/apis/api/drive.googleapis.com")
                    print("  Переключаюсь на локальный экспорт...")
                    return self._fallback_to_local_export(date, llm_results)
            
            # Пытаемся экспортировать в Google Sheets
            try:
                # Передаем результаты анализа в метод экспорта
                export_result = self.exporter.export_results_by_date(date, llm_results)
                
                if export_result:
                    logging.info(f"Данные за {date} успешно экспортированы в Google Sheets")
                    print(f"✅ Данные за {date} успешно экспортированы в Google Sheets")
                    return True
                else:
                    logging.warning(f"Экспорт в Google Sheets не удался за {date}, переключение на локальный экспорт")
                    print(f"⚠️ Экспорт в Google Sheets не удался, используем локальный экспорт")
                    # Гарантированно пытаемся сохранить локально
                    local_export_result = self._fallback_to_local_export(date, llm_results)
                    return local_export_result
            except Exception as e:
                logging.error(f"Ошибка при экспорте в Google Sheets за {date}: {e}")
                print(f"⚠️ Ошибка при экспорте в Google Sheets: {e}")
                print(f"🔄 Переключаюсь на локальный экспорт...")
                # Гарантированно пытаемся сохранить локально
                local_export_result = self._fallback_to_local_export(date, llm_results)
                return local_export_result
                
        except Exception as e:
            logging.error(f"Неожиданная ошибка при обработке {date}: {e}")
            print(f"❌ Неожиданная ошибка: {e}")
            print("  Переключаюсь на локальный экспорт...")
            # Гарантированно пытаемся сохранить локально
            local_export_result = self._fallback_to_local_export(date, llm_results)
            return local_export_result
    
    def _fallback_to_local_export(self, date: str, llm_results=None) -> bool:
        """📊 Fallback на локальный экспорт при недоступности Google Sheets
        
        Args:
            date (str): Дата в формате YYYY-MM-DD
            llm_results (Dict, optional): Результаты анализа. Если None, загружаются из файла.
            
        Returns:
            bool: True если экспорт прошел успешно, False в противном случае
        """
        
        import logging
        logging.info(f"Запуск резервного локального экспорта для даты {date}")
        
        try:
            print(f"\n📊 ЛОКАЛЬНЫЙ ЭКСПОРТ (FALLBACK) ЗА {date}")
            print("=" * 50)
            
            results = llm_results
            
            # Если результаты не переданы, пытаемся загрузить их из файла
            if not results:
                results_path = self.processor.results_dir / f"llm_analysis_{date.replace('-', '')}.json"
                logging.info(f"Попытка загрузки результатов из файла: {results_path}")
                
                if not results_path.exists():
                    logging.error(f"Результаты анализа за {date} не найдены: {results_path}")
                    print(f"❌ Результаты анализа за {date} не найдены")
                    print(f"   Путь: {results_path}")
                    return False
                
                try:
                    with open(results_path, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                        logging.info(f"Результаты успешно загружены из файла: {len(str(results))} символов")
                except Exception as e:
                    logging.error(f"Ошибка загрузки результатов из файла: {e}")
                    print(f"❌ Ошибка загрузки результатов из файла: {e}")
                    import traceback
                    error_traceback = traceback.format_exc()
                    logging.error(f"Трассировка ошибки загрузки: {error_traceback}")
                    return False
            
            # Проверяем, что результаты не пустые
            if not results:
                logging.error("Результаты анализа пусты")
                print("❌ Результаты анализа пусты")
                return False
            
            # Экспортируем локально
            logging.info(f"Начало локального экспорта данных за {date}")
            success = self.local_exporter.export_results_by_date(date, results)
            
            if success:
                export_path = self.local_exporter.export_dir.absolute()
                logging.info(f"Локальный экспорт завершен успешно. Файлы сохранены в: {export_path}")
                print(f"✅ Локальный экспорт завершен успешно")
                print(f"   📁 Файлы сохранены в: {export_path}")
                return True
            else:
                logging.error(f"Локальный экспорт не удался за {date}")
                print(f"❌ Локальный экспорт также не удался")
                return False
                
        except Exception as e:
            logging.error(f"Ошибка локального экспорта за {date}: {e}")
            print(f"❌ Ошибка локального экспорта: {e}")
            import traceback
            error_traceback = traceback.format_exc()
            logging.error(f"Трассировка ошибки: {error_traceback}")
            return False
            
    def _fallback_to_local_export_multiple_dates(self, start_date: str, end_date: str, results_dict: Dict[str, Dict]) -> bool:
        """📊 Fallback на локальный экспорт для диапазона дат при недоступности Google Sheets
        
        Args:
            start_date (str): Начальная дата в формате YYYY-MM-DD
            end_date (str): Конечная дата в формате YYYY-MM-DD
            results_dict (Dict[str, Dict]): Словарь с результатами, где ключ - дата
            
        Returns:
            bool: True если хотя бы одна дата экспортирована успешно
        """
        
        import logging
        logging.info(f"Запуск резервного локального экспорта для диапазона дат {start_date} - {end_date}")
        
        print(f"\n📊 ЛОКАЛЬНЫЙ ЭКСПОРТ (FALLBACK) ЗА ПЕРИОД {start_date} - {end_date}")
        print("=" * 60)
        
        try:
            # Используем новый метод для экспорта всего диапазона дат сразу
            export_results = self.local_exporter.export_multiple_dates(start_date, end_date, results_dict)
            
            if not export_results:
                logging.error(f"Ошибка при локальном экспорте диапазона дат {start_date} - {end_date}")
                print("\n❌ Ошибка при локальном экспорте диапазона дат")
                return False
                
            success_count = sum(1 for success in export_results.values() if success)
            total_dates = len(export_results)
            
            if success_count > 0:
                export_path = self.local_exporter.export_dir.absolute()
                logging.info(f"Локальный экспорт завершен. Успешно: {success_count}/{total_dates}. Файлы сохранены в: {export_path}")
                print(f"\n✅ Успешно экспортировано {success_count} из {total_dates} дат")
                print(f"   📁 Файлы сохранены в: {export_path}")
                return True
            else:
                logging.error(f"Не удалось экспортировать ни одной даты из диапазона {start_date} - {end_date}")
                print("\n❌ Не удалось экспортировать ни одной даты")
                return False
                
        except Exception as e:
            # В случае ошибки в новом методе, используем старый подход (по одной дате)
            logging.error(f"Ошибка при использовании export_multiple_dates: {e}. Переключение на экспорт по одной дате.")
            print(f"⚠️ Ошибка при экспорте диапазона: {e}")
            print("⚠️ Переключение на экспорт по одной дате...")
            
            success_count = 0
            total_dates = len(results_dict)
            
            for date_str, results in results_dict.items():
                try:
                    # Экспортируем локально по одной дате
                    success = self.local_exporter.export_results_by_date(date_str, results)
                    
                    if success:
                        success_count += 1
                        logging.info(f"Данные за {date_str} успешно экспортированы локально")
                        print(f"✅ Данные за {date_str} успешно экспортированы локально")
                    else:
                        logging.error(f"Локальный экспорт не удался за {date_str}")
                        print(f"❌ Локальный экспорт не удался за {date_str}")
                except Exception as e:
                    logging.error(f"Ошибка локального экспорта за {date_str}: {e}")
                    print(f"❌ Ошибка локального экспорта за {date_str}: {e}")
            
            if success_count > 0:
                export_path = self.local_exporter.export_dir.absolute()
                logging.info(f"Локальный экспорт завершен. Успешно: {success_count}/{total_dates}. Файлы сохранены в: {export_path}")
                print(f"\n✅ Успешно экспортировано {success_count} из {total_dates} дат")
                print(f"   📁 Файлы сохранены в: {export_path}")
                return True
            else:
                logging.error(f"Не удалось экспортировать ни одной даты из диапазона {start_date} - {end_date}")
                print("\n❌ Не удалось экспортировать ни одной даты")
                return False
    
    def _print_stats(self):
        """📊 Вывести статистику обработки"""
        import logging
        
        # Проверяем наличие атрибута statistics
        if not hasattr(self.processor, 'statistics') or not self.processor.statistics:
            logging.warning("Статистика обработки недоступна")
            print("\n⚠️ Статистика обработки недоступна")
            return
        
        # Проверяем наличие атрибута contacts
        if not hasattr(self.processor, 'contacts'):
            self.processor.contacts = []
            
        stats = self.processor.statistics
        emails_processed = stats.get('emails_processed', 0)
        attachments_processed = stats.get('attachments_processed', 0)
        contacts_found = len(self.processor.contacts)
        processing_time = stats.get('processing_time', 0)
        
        # Логируем основную статистику
        logging.info(f"Статистика обработки: {emails_processed} писем, {attachments_processed} вложений, {contacts_found} контактов, {processing_time:.2f} сек")
            
        print("\n📊 СТАТИСТИКА ОБРАБОТКИ")
        print(f"📧 Обработано писем: {emails_processed}")
        print(f"📎 Обработано вложений: {attachments_processed}")
        print(f"👤 Найдено контактов: {contacts_found}")
        print(f"⏱️ Время обработки: {processing_time:.2f} сек")
        
        # Если есть статистика по LLM
        if 'llm_stats' in stats:
            llm_stats = stats['llm_stats']
            total_requests = llm_stats.get('total_requests', 0)
            total_tokens = llm_stats.get('total_tokens', 0)
            
            logging.info(f"LLM статистика: {total_requests} запросов, {total_tokens} токенов")
            print(f"🤖 LLM запросы: {total_requests}")
            print(f"💰 Токенов использовано: {total_tokens}")
            
            # Если есть информация о стоимости
            if 'cost' in llm_stats:
                cost = llm_stats['cost']
                logging.info(f"Примерная стоимость LLM запросов: ${cost:.4f}")
                print(f"💲 Примерная стоимость: ${cost:.4f}")
                
        # Если есть информация о провайдере
        if 'provider' in stats:
            provider = stats['provider']
            logging.info(f"Использован провайдер: {provider}")
            print(f"🔌 Использован провайдер: {provider}")
            
        # Если есть информация о тестовом режиме
        if 'test_mode' in stats:
            test_mode = stats['test_mode']
            if test_mode:
                logging.warning("Использован тестовый режим (без реальных LLM запросов)")
                print("⚠️ ВНИМАНИЕ: Использован тестовый режим (без реальных LLM запросов)")
            else:
                logging.info("Использован рабочий режим (с реальными LLM запросами)")
                print("✅ Использован рабочий режим (с реальными LLM запросами)")
                
        # Если есть информация о модели
        if 'model' in stats:
            model = stats['model']
            logging.info(f"Использована модель: {model}")
            print(f"🧠 Использована модель: {model}")
            
        # Если есть информация о времени ожидания
        if 'wait_time' in stats:
            wait_time = stats['wait_time']
            logging.info(f"Время ожидания LLM: {wait_time:.2f} сек")
            print(f"⏳ Время ожидания LLM: {wait_time:.2f} сек")

    def process_date_range(self, start_date: str, end_date: str, max_emails: int = None) -> bool:
        """📅 Обработка и экспорт данных за диапазон дат
        
        Args:
            start_date (str): Начальная дата в формате YYYY-MM-DD
            end_date (str): Конечная дата в формате YYYY-MM-DD
            max_emails (int, optional): Максимальное количество писем для обработки за каждую дату
            
        Returns:
            bool: True если хотя бы одна дата обработана успешно
        """
        
        from datetime import datetime, timedelta
        import logging
        
        logging.info(f"Начало обработки диапазона дат: {start_date} - {end_date}")
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            logging.error(f"Неверный формат даты: {start_date} или {end_date}")
            print("❌ Неверный формат даты. Используйте формат YYYY-MM-DD")
            return False
        
        if start > end:
            logging.error(f"Начальная дата {start_date} больше конечной {end_date}")
            print("❌ Начальная дата должна быть меньше или равна конечной")
            return False
        
        print(f"\n{'='*60}")
        print(f"🔄 ПОЛНЫЙ ЦИКЛ ОБРАБОТКИ ЗА ПЕРИОД {start_date} - {end_date}")
        print(f"{'='*60}")
        
        # Создаем одну таблицу для всего диапазона
        title = f"Контакты из деловой переписки ({start_date} - {end_date})"
        try:
            sheet_id = self.exporter.create_new_spreadsheet(title)
            if sheet_id:
                self.exporter.spreadsheet_id = sheet_id
                logging.info(f"Создана новая таблица: {title} с ID: {sheet_id}")
                print(f"✅ Создана новая таблица: {title}")
                print(f"   ID: {sheet_id}")
            else:
                logging.warning("Не удалось создать новую таблицу Google Sheets")
                print("❌ Не удалось создать новую таблицу")
                print("  Возможные причины:")
                print("  1. Недостаточно прав в service_account.json")
                print("  2. Google Drive API не включен в консоли Google")
                print("  3. Проверьте подключение к интернету")
                print("  4. Превышена квота хранилища Google Drive")
                print("  Будет использован локальный экспорт для каждой даты")
        except Exception as e:
            logging.error(f"Ошибка создания таблицы: {e}")
            print(f"❌ Ошибка создания таблицы: {e}")
            print("  Для активации Google Drive API перейдите по ссылке:")
            print("  https://console.developers.google.com/apis/api/drive.googleapis.com")
            print("  Будет использован локальный экспорт для каждой даты")
        
        # Проходим по каждой дате в диапазоне
        current = start
        success_count = 0
        total_days = (end - start).days + 1
        logging.info(f"Всего дней для обработки: {total_days}")
        
        # Словарь для хранения результатов по датам
        all_results = {}
        
        # Сначала собираем все результаты
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            logging.info(f"Начало обработки даты: {date_str}")
            
            print(f"\n{'*'*60}")
            print(f"📅 ОБРАБОТКА ДАТЫ: {date_str}")
            print(f"{'*'*60}")
            
            # Шаг 1: LLM анализ
            print("\n📄 ШАГ 1: Анализ писем и вложений с помощью LLM")
            
            try:
                # Обрабатываем реальные данные из почты
                llm_results = self.processor.process_emails_by_date(date_str, max_emails=max_emails)
                
                # Сохраняем результаты в атрибутах процессора для доступа из _print_stats
                self.processor.statistics = llm_results.get('statistics', {})
                self.processor.contacts = llm_results.get('all_contacts', [])
                
                # Если анализ прошел успешно
                if llm_results and 'emails_processed' in llm_results.get('statistics', {}):
                    # Сохраняем результаты в словарь
                    all_results[date_str] = llm_results
                    
                    # Проверяем, были ли найдены контакты
                    if llm_results.get('summary', {}).get('total_contacts', 0) == 0:
                        logging.warning(f"За {date_str} не найдено контактов")
                        print(f"⚠️ За {date_str} не найдено контактов")
                        print(f"   Проверьте, есть ли письма за эту дату")
                else:
                    logging.error(f"Не удалось обработать данные за {date_str}")
                    print(f"❌ Не удалось обработать данные за {date_str}")
            except Exception as e:
                logging.error(f"Ошибка при обработке данных за {date_str}: {e}")
                print(f"❌ Ошибка при обработке данных: {e}")
            
            # Переходим к следующей дате
            current += timedelta(days=1)
        
        # Если есть результаты, экспортируем их
        if all_results:
            print("\n📊 ШАГ 2: Экспорт результатов в Google Sheets")
            try:
                # Пытаемся экспортировать все результаты сразу в Google Sheets
                logging.info(f"Попытка экспорта данных за период {start_date} - {end_date} в Google Sheets")
                export_result = self.exporter.export_multiple_dates(start_date, end_date, all_results)
                
                if export_result:
                    success_count = len(all_results)
                    logging.info(f"Данные за период {start_date} - {end_date} успешно экспортированы в Google Sheets")
                    print(f"✅ Данные за период {start_date} - {end_date} успешно экспортированы в Google Sheets")
                else:
                    logging.warning(f"Экспорт в Google Sheets не удался (вернул False), используем локальный экспорт")
                    print(f"⚠️ Экспорт в Google Sheets не удался, используем локальный экспорт")
                    
                    # Используем метод для локального экспорта нескольких дат
                    if self._fallback_to_local_export_multiple_dates(start_date, end_date, all_results):
                        success_count = len(all_results)
                        logging.info(f"Данные за период {start_date} - {end_date} успешно экспортированы локально")
                    else:
                        logging.error(f"Не удалось экспортировать данные ни в Google Sheets, ни локально")
                        print(f"❌ Не удалось экспортировать данные ни в Google Sheets, ни локально")
            except Exception as e:
                logging.error(f"Ошибка при экспорте в Google Sheets: {e}")
                print(f"⚠️ Ошибка при экспорте в Google Sheets: {e}")
                print(f"🔄 Переключаюсь на локальный экспорт...")
                
                # Используем метод для локального экспорта нескольких дат
                try:
                    if self._fallback_to_local_export_multiple_dates(start_date, end_date, all_results):
                        success_count = len(all_results)
                        logging.info(f"Данные за период {start_date} - {end_date} успешно экспортированы локально после ошибки Google Sheets")
                        print(f"✅ Данные за период {start_date} - {end_date} успешно экспортированы локально")
                    else:
                        logging.error(f"Локальный экспорт не удался после ошибки Google Sheets")
                        print(f"❌ Локальный экспорт не удался после ошибки Google Sheets")
                except Exception as local_error:
                    logging.error(f"Критическая ошибка при локальном экспорте: {local_error}")
                    print(f"❌ Критическая ошибка при локальном экспорте: {local_error}")
                    success_count = 0
        
        print(f"\n{'='*60}")
        print(f"📊 ИТОГИ ОБРАБОТКИ ПЕРИОДА {start_date} - {end_date}")
        print(f"✅ Успешно обработано дат: {success_count} из {total_days}")
        if self.exporter.spreadsheet_id:
            print(f"🔗 URL таблицы: https://docs.google.com/spreadsheets/d/{self.exporter.spreadsheet_id}")
        print(f"{'='*60}")
        
        # Выводим итоговую статистику обработки
        self._print_stats()
        
        logging.info(f"Завершена обработка диапазона {start_date} - {end_date}. Успешно: {success_count}/{total_days}")
        return success_count > 0


def main():
    """🚀 Основная функция"""
    
    import logging
    from datetime import datetime
    
    # Настройка логирования
    log_file = f"bridge_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logging.info("="*60)
    logging.info("🔄 ИНТЕГРАЦИЯ OCR + LLM + GOOGLE SHEETS")
    logging.info("="*60)
    
    print("\n" + "="*60)
    print("🔄 ИНТЕГРАЦИЯ OCR + LLM + GOOGLE SHEETS")
    print("="*60)
    print(f"📝 Логи сохраняются в: {log_file}")
    
    try:
        # Создаем мост
        bridge = LLM_Sheets_Bridge()
        
        # Проверяем доступность Google Sheets API
        if not bridge.exporter.client:
            logging.warning("Google Sheets API не настроен")
            print("\n❌ Google Sheets API не настроен")
            print("   Убедитесь, что файл config/service_account.json существует")
            print("   Вы можете продолжить без экспорта в Google Sheets")
            # Даем пользователю возможность продолжить без экспорта
            response = input("\nПродолжить только с LLM обработкой? (y/n): ")
            if response.lower() != 'y':
                return
        
        print("\nВыберите режим работы:")
        print("1. Обработать и экспортировать одну дату")
        print("2. Обработать и экспортировать диапазон дат")
        print("3. Обработать произвольный диапазон дат")
        print("4. Выйти")
        
        choice = input("\nВаш выбор (1-4): ")
        logging.info(f"Выбран режим работы: {choice}")
    except Exception as e:
        logging.error(f"Ошибка при инициализации: {e}")
        print(f"❌ Ошибка при инициализации: {e}")
        return
    
    try:
        if choice == '1':
            # Обработка одной даты
            date = input("Введите дату (YYYY-MM-DD): ")
            logging.info(f"Выбрана дата для обработки: {date}")
            create_new = input("Создать новую таблицу? (y/n): ").lower() == 'y'
            
            # Запрос количества писем для обработки
            print("\nСколько писем за выбранный день вы хотите обработать?")
            print("1. Все письма")
            print("2. Указать количество")
            emails_choice = input("Ваш выбор (1-2): ")
            max_emails = None
            
            if emails_choice == '2':
                try:
                    max_emails = int(input("Введите количество писем: "))
                    logging.info(f"Выбрано количество писем для обработки: {max_emails}")
                except ValueError:
                    print("❌ Введено некорректное значение. Будут обработаны все письма.")
                    max_emails = None
            else:
                logging.info("Выбрана обработка всех писем")
            
            result = bridge.process_and_export(date, create_new, max_emails)
            if result:
                logging.info(f"Успешно обработана дата: {date}")
                # Дополнительно выводим статистику
                bridge._print_stats()
            else:
                logging.warning(f"Не удалось обработать дату: {date}")
            
        elif choice == '2':
            # Обработка диапазона дат
            start_date = input("Введите начальную дату (YYYY-MM-DD): ")
            end_date = input("Введите конечную дату (YYYY-MM-DD): ")
            logging.info(f"Выбран диапазон дат: {start_date} - {end_date}")
            
            # Запрос количества писем для обработки
            print("\nСколько писем за каждый день вы хотите обработать?")
            print("1. Все письма")
            print("2. Указать количество")
            emails_choice = input("Ваш выбор (1-2): ")
            max_emails = None
            
            if emails_choice == '2':
                try:
                    max_emails = int(input("Введите количество писем: "))
                    logging.info(f"Выбрано количество писем для обработки: {max_emails}")
                except ValueError:
                    print("❌ Введено некорректное значение. Будут обработаны все письма.")
                    max_emails = None
            else:
                logging.info("Выбрана обработка всех писем")
            
            result = bridge.process_date_range(start_date, end_date, max_emails)
            if result:
                logging.info(f"Успешно обработан диапазон: {start_date} - {end_date}")
                # Статистика уже выводится в методе process_date_range
            else:
                logging.warning(f"Не удалось обработать диапазон: {start_date} - {end_date}")
            
        elif choice == '3':
            # Произвольный диапазон дат
            print("\n📅 Выберите диапазон дат для обработки")
            start_date = input("Введите начальную дату (YYYY-MM-DD): ")
            end_date = input("Введите конечную дату (YYYY-MM-DD): ")
            logging.info(f"Выбран произвольный диапазон дат: {start_date} - {end_date}")
            
            # Запрос количества писем для обработки
            print("\nСколько писем за каждый день вы хотите обработать?")
            print("1. Все письма")
            print("2. Указать количество")
            emails_choice = input("Ваш выбор (1-2): ")
            max_emails = None
            
            if emails_choice == '2':
                try:
                    max_emails = int(input("Введите количество писем: "))
                    logging.info(f"Выбрано количество писем для обработки: {max_emails}")
                except ValueError:
                    print("❌ Введено некорректное значение. Будут обработаны все письма.")
                    max_emails = None
            else:
                logging.info("Выбрана обработка всех писем")
            
            result = bridge.process_date_range(start_date, end_date, max_emails)
            if result:
                logging.info(f"Успешно обработан диапазон: {start_date} - {end_date}")
                # Статистика уже выводится в методе process_date_range
            else:
                logging.warning(f"Не удалось обработать диапазон: {start_date} - {end_date}")
            
        elif choice == '4':
            logging.info("Завершение работы")
            print("\n👋 До свидания!")
            return
            
        else:
            logging.warning(f"Неверный выбор: {choice}")
            print("\n❌ Неверный выбор")
            return
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        print(f"❌ Произошла ошибка: {e}")
        return


if __name__ == '__main__':
    main()
