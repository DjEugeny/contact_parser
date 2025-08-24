#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Локальный экспортер данных в CSV/Excel формат
"""

import json
import csv
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class LocalDataExporter:
    """📊 Локальный экспортер данных в различные форматы"""
    
    def __init__(self, export_dir: str = "data/exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📊 Локальный экспортер инициализирован")
        print(f"   📁 Папка экспорта: {self.export_dir.absolute()}")
    
    def export_results_by_date(self, date: str, results: Dict) -> bool:
        """📅 Экспорт результатов за конкретную дату"""
        
        try:
            print(f"\n📊 ЛОКАЛЬНЫЙ ЭКСПОРТ ДАННЫХ ЗА {date}")
            print("=" * 60)
            
            # Экспортируем в разные форматы
            csv_success = self._export_to_csv(date, results)
            json_success = self._export_to_json(date, results)
            
            if csv_success or json_success:
                print(f"✅ Экспорт завершен успешно")
                print(f"   📁 Файлы сохранены в: {self.export_dir.absolute()}")
                return True
            else:
                print(f"❌ Не удалось экспортировать данные")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка локального экспорта: {e}")
            return False
            
    def export_multiple_dates(self, start_date: str, end_date: str, results_dict: Dict[str, Dict] = None) -> Dict[str, bool]:
        """📅 Экспорт результатов за диапазон дат в CSV и JSON
        
        Args:
            start_date (str): Начальная дата в формате YYYY-MM-DD
            end_date (str): Конечная дата в формате YYYY-MM-DD
            results_dict (Dict[str, Dict], optional): Словарь с результатами, где ключ - дата.
                Если None, результаты не экспортируются.
                
        Returns:
            Dict[str, bool]: Словарь с результатами экспорта, где ключ - дата, значение - успешность экспорта
        """
        # Парсим даты
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            logging.error(f"Неверный формат даты при локальном экспорте: {start_date} - {end_date}")
            print("❌ Неверный формат даты. Используйте формат YYYY-MM-DD")
            return {}
        
        if start > end:
            logging.error(f"Начальная дата {start_date} больше конечной {end_date}")
            print("❌ Начальная дата должна быть меньше или равна конечной")
            return {}
            
        # Проверяем, что results_dict не None
        if results_dict is None:
            logging.warning("Словарь результатов не передан при локальном экспорте")
            print("⚠️ Словарь результатов не передан, экспорт невозможен")
            return {}
            
        # Создаем директорию для диапазона дат
        range_dir = self.export_dir / f"{start_date.replace('-', '')}_{end_date.replace('-', '')}"
        range_dir.mkdir(exist_ok=True)
            
        # Проходим по всем датам в диапазоне
        current = start
        export_results = {}
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            
            # Получаем результаты для текущей даты
            current_results = results_dict.get(date_str)
            
            if current_results:
                print(f"📅 Локальный экспорт за {date_str}")
                export_results[date_str] = self.export_results_by_date(date_str, current_results)
            else:
                logging.warning(f"Нет данных для локального экспорта за {date_str}")
                print(f"⚠️ Нет данных для экспорта за {date_str}")
                export_results[date_str] = False
            
            # Переходим к следующей дате
            current += timedelta(days=1)
            
        # Создаем сводный JSON файл для всего диапазона
        try:
            summary_path = range_dir / f"summary_{start_date.replace('-', '')}_{end_date.replace('-', '')}.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'start_date': start_date,
                    'end_date': end_date,
                    'export_results': export_results,
                    'success_count': sum(1 for success in export_results.values() if success),
                    'total_count': len(export_results),
                    'export_time': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            print(f"✅ Создан сводный отчет: {summary_path}")
        except Exception as e:
            logging.error(f"Ошибка при создании сводного отчета: {e}")
            print(f"❌ Ошибка при создании сводного отчета: {e}")
            
        return export_results
    
    def _export_to_csv(self, date: str, results: Dict) -> bool:
        """📄 Экспорт в CSV формат"""
        
        try:
            # Экспорт контактов
            contacts_file = self.export_dir / f"contacts_{date.replace('-', '')}.csv"
            contacts_data = self._extract_contacts_data(results)
            
            if contacts_data:
                with open(contacts_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=contacts_data[0].keys())
                    writer.writeheader()
                    writer.writerows(contacts_data)
                print(f"   ✅ Контакты экспортированы в: {contacts_file.name}")
            
            # Экспорт статистики
            stats_file = self.export_dir / f"statistics_{date.replace('-', '')}.csv"
            stats_data = self._extract_statistics_data(results, date)
            
            with open(stats_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=stats_data.keys())
                writer.writeheader()
                writer.writerow(stats_data)
            print(f"   ✅ Статистика экспортирована в: {stats_file.name}")
            
            # Экспорт деталей email
            email_details_file = self.export_dir / f"email_details_{date.replace('-', '')}.csv"
            email_details_data = self._extract_email_details(results)
            
            if email_details_data:
                with open(email_details_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=email_details_data[0].keys())
                    writer.writeheader()
                    writer.writerows(email_details_data)
                print(f"   ✅ Детали email экспортированы в: {email_details_file.name}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Ошибка экспорта в CSV: {e}")
            return False
    
    def _export_to_json(self, date: str, results: Dict) -> bool:
        """📋 Экспорт в JSON формат"""
        
        try:
            json_file = self.export_dir / f"export_{date.replace('-', '')}.json"
            
            # Добавляем метаданные экспорта
            export_data = {
                "export_info": {
                    "exported_at": datetime.now().isoformat(),
                    "export_format": "local_json",
                    "original_date": date
                },
                "data": results
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"   ✅ Данные экспортированы в JSON: {json_file.name}")
            return True
            
        except Exception as e:
            print(f"   ❌ Ошибка экспорта в JSON: {e}")
            return False
    
    def _extract_contacts_data(self, results: Dict) -> List[Dict]:
        """👤 Извлечение данных контактов для экспорта"""
        
        contacts_data = []
        
        for email_result in results.get('emails_results', []):
            email_contacts = email_result.get('contacts', [])
            if email_contacts:
                for contact in email_contacts:
                    contact_row = {
                        "Дата": results.get('processing_date', ''),
                        "Имя": contact.get('name', ''),
                        "Email": contact.get('email', ''),
                        "Телефон": contact.get('phone', ''),
                        "Организация": contact.get('organization', ''),
                        "Должность": contact.get('position', ''),
                        "Город": contact.get('city', ''),
                        "Confidence": contact.get('confidence', 0),
                        "Приоритет": contact.get('priority', {}).get('level', 'низкий'),
                        "Тема письма": email_result.get('original_email', {}).get('subject', ''),
                        "Thread ID": email_result.get('original_email', {}).get('thread_id', ''),
                        "От": email_result.get('original_email', {}).get('from', '')
                    }
                    contacts_data.append(contact_row)
        
        return contacts_data
    
    def _extract_statistics_data(self, results: Dict, date: str) -> Dict:
        """📊 Извлечение статистики для экспорта"""
        
        stats = results.get('statistics', {})
        
        return {
            "Дата": date,
            "Писем обработано": stats.get('emails_processed', 0),
            "Контактов найдено": stats.get('total_contacts_found', 0),
            "Писем с вложениями": stats.get('emails_with_attachments', 0),
            "Вложений обработано": stats.get('attachments_processed', 0),
            "КП найдено": stats.get('commercial_offers_found', 0),
            "Ошибок обработки": stats.get('processing_errors', 0),
            "Время обработки (сек)": stats.get('processing_time_seconds', 0)
        }
    
    def _extract_email_details(self, results: Dict) -> List[Dict]:
        """📧 Извлечение деталей email для экспорта"""
        
        email_details = []
        
        for email_result in results.get('emails_results', []):
            email_row = {
                "Thread ID": email_result.get('original_email', {}).get('thread_id', ''),
                "От": email_result.get('original_email', {}).get('from', ''),
                "Тема": email_result.get('original_email', {}).get('subject', ''),
                "Дата": email_result.get('original_email', {}).get('date', ''),
                "Объем текста": email_result.get('combined_text_length', 0),
                "Вложений": email_result.get('attachments_processed', 0),
                "Контактов найдено": len(email_result.get('contacts', [])),
                "Обработано": email_result.get('processed_at', '')
            }
            email_details.append(email_row)
        
        return email_details


def main():
    """🚀 Тестовая функция"""
    
    print("📊 ТЕСТ ЛОКАЛЬНОГО ЭКСПОРТЕРА")
    print("=" * 40)
    
    # Создаем экспортер
    exporter = LocalDataExporter()
    
    # Тестируем на существующих данных
    test_date = "2025-07-28"
    test_file = Path("data/llm_results") / f"llm_analysis_{test_date.replace('-', '')}.json"
    
    if test_file.exists():
        print(f"📁 Тестирую на файле: {test_file}")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            test_results = json.load(f)
        
        success = exporter.export_results_by_date(test_date, test_results)
        
        if success:
            print(f"\n✅ Тест завершен успешно!")
        else:
            print(f"\n❌ Тест завершился с ошибками")
    else:
        print(f"❌ Тестовый файл не найден: {test_file}")


if __name__ == '__main__':
    main()
