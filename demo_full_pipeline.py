#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Демонстрация полной цепочки обработки: загрузка писем → OCR → LLM → экспорт в таблицы

Этот скрипт демонстрирует работу всей системы:
1. Автоматическая загрузка писем с сервера (если их нет локально)
2. OCR обработка вложений
3. LLM анализ для извлечения контактов
4. Адаптивное управление rate limit
5. Экспорт результатов в Google Sheets или локально
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent / "src"))

from google_sheets_bridge import LLM_Sheets_Bridge


def demo_single_date(date: str, max_emails: int = None):
    """🎯 Демонстрация обработки одной даты
    
    Args:
        date: Дата в формате YYYY-MM-DD
        max_emails: Максимальное количество писем для обработки
    """
    print(f"\n🚀 ДЕМОНСТРАЦИЯ ПОЛНОЙ ЦЕПОЧКИ ОБРАБОТКИ")
    print(f"📅 Дата: {date}")
    if max_emails:
        print(f"📧 Лимит писем: {max_emails}")
    print("=" * 60)
    
    # Инициализируем мост
    bridge = LLM_Sheets_Bridge()
    
    print("\n🔧 КОМПОНЕНТЫ СИСТЕМЫ:")
    print(f"   📧 Email Fetcher: ✅ Готов к автозагрузке")
    print(f"   🔍 OCR Processor: ✅ Готов к обработке вложений")
    print(f"   🤖 LLM Processor: ✅ Готов к анализу (rate limit: адаптивный)")
    
    if bridge.exporter.client:
        print(f"   📊 Google Sheets: ✅ API подключен")
    else:
        print(f"   📊 Google Sheets: ❌ API не подключен (будет локальный экспорт)")
    
    print(f"   💾 Local Exporter: ✅ Готов как fallback")
    
    # Запускаем полную цепочку
    print(f"\n🔄 ЗАПУСК ПОЛНОЙ ЦЕПОЧКИ...")
    
    try:
        success = bridge.process_and_export(date, max_emails=max_emails)
        
        if success:
            print(f"\n🎉 УСПЕШНО ЗАВЕРШЕНО!")
            print(f"   ✅ Данные за {date} обработаны и экспортированы")
            
            # Показываем статистику, если доступна
            if hasattr(bridge.processor, 'statistics') and bridge.processor.statistics:
                stats = bridge.processor.statistics
                print(f"\n📈 СТАТИСТИКА ОБРАБОТКИ:")
                print(f"   📧 Писем обработано: {stats.get('emails_processed', 0)}")
                print(f"   🔍 OCR операций: {stats.get('ocr_operations', 0)}")
                print(f"   🤖 LLM запросов: {stats.get('total_requests', 0)}")
                print(f"   ✅ Успешных запросов: {stats.get('successful_requests', 0)}")
                print(f"   ❌ Неудачных запросов: {stats.get('failed_requests', 0)}")
                
                if hasattr(bridge.processor, 'contacts') and bridge.processor.contacts:
                    print(f"   👥 Найдено контактов: {len(bridge.processor.contacts)}")
                    
                    # Показываем топ-3 контакта по приоритету
                    top_contacts = sorted(bridge.processor.contacts, 
                                         key=lambda x: x.get('priority', 0), 
                                         reverse=True)[:3]
                    
                    print(f"\n🏆 ТОП-3 КОНТАКТА ПО ПРИОРИТЕТУ:")
                    for i, contact in enumerate(top_contacts, 1):
                        print(f"   {i}. {contact.get('name', 'Неизвестно')} ")
                        print(f"      📧 {contact.get('email', 'Нет email')}")
                        print(f"      📞 {contact.get('phone', 'Нет телефона')}")
                        print(f"      🏢 {contact.get('company', 'Нет компании')}")
                        print(f"      ⭐ Приоритет: {contact.get('priority', 0)}/10")
                        print()
        else:
            print(f"\n❌ ОБРАБОТКА НЕ УДАЛАСЬ")
            print(f"   Проверьте логи для получения подробной информации")
            
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print(f"   Проверьте конфигурацию системы")
        return False
        
    return success


def demo_date_range(start_date: str, end_date: str, max_emails: int = None):
    """📅 Демонстрация обработки диапазона дат
    
    Args:
        start_date: Начальная дата в формате YYYY-MM-DD
        end_date: Конечная дата в формате YYYY-MM-DD
        max_emails: Максимальное количество писем для обработки за день
    """
    print(f"\n🚀 ДЕМОНСТРАЦИЯ ОБРАБОТКИ ДИАПАЗОНА ДАТ")
    print(f"📅 Период: {start_date} - {end_date}")
    if max_emails:
        print(f"📧 Лимит писем в день: {max_emails}")
    print("=" * 60)
    
    # Инициализируем мост
    bridge = LLM_Sheets_Bridge()
    
    try:
        success = bridge.process_date_range(start_date, end_date, max_emails=max_emails)
        
        if success:
            print(f"\n🎉 ДИАПАЗОН УСПЕШНО ОБРАБОТАН!")
        else:
            print(f"\n❌ ОБРАБОТКА ДИАПАЗОНА НЕ УДАЛАСЬ")
            
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return False
        
    return success


def main():
    """🎯 Главная функция демонстрации"""
    parser = argparse.ArgumentParser(
        description="🚀 Демонстрация полной цепочки обработки писем",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python demo_full_pipeline.py --date 2025-01-15
  python demo_full_pipeline.py --date 2025-01-15 --max-emails 5
  python demo_full_pipeline.py --start-date 2025-01-10 --end-date 2025-01-15
  python demo_full_pipeline.py --start-date 2025-01-10 --end-date 2025-01-15 --max-emails 3

Система автоматически:
1. Загрузит письма с сервера, если их нет локально
2. Обработает вложения через OCR
3. Проанализирует содержимое через LLM
4. Экспортирует результаты в Google Sheets или локально
        """
    )
    
    # Группа для одной даты
    single_group = parser.add_argument_group('Обработка одной даты')
    single_group.add_argument(
        '--date', 
        type=str, 
        help='Дата для обработки в формате YYYY-MM-DD'
    )
    
    # Группа для диапазона дат
    range_group = parser.add_argument_group('Обработка диапазона дат')
    range_group.add_argument(
        '--start-date', 
        type=str, 
        help='Начальная дата диапазона в формате YYYY-MM-DD'
    )
    range_group.add_argument(
        '--end-date', 
        type=str, 
        help='Конечная дата диапазона в формате YYYY-MM-DD'
    )
    
    # Общие параметры
    parser.add_argument(
        '--max-emails', 
        type=int, 
        help='Максимальное количество писем для обработки (за день)'
    )
    
    args = parser.parse_args()
    
    # Проверяем аргументы
    if args.date and (args.start_date or args.end_date):
        print("❌ Ошибка: Нельзя одновременно указывать --date и --start-date/--end-date")
        return False
        
    if (args.start_date and not args.end_date) or (args.end_date and not args.start_date):
        print("❌ Ошибка: Для диапазона дат нужно указать и --start-date, и --end-date")
        return False
        
    if not args.date and not args.start_date:
        # Если не указаны даты, используем вчерашний день
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"ℹ️ Даты не указаны, используем вчерашний день: {yesterday}")
        args.date = yesterday
    
    # Валидация формата дат
    def validate_date(date_str):
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    if args.date and not validate_date(args.date):
        print(f"❌ Ошибка: Неверный формат даты '{args.date}'. Используйте YYYY-MM-DD")
        return False
        
    if args.start_date and not validate_date(args.start_date):
        print(f"❌ Ошибка: Неверный формат начальной даты '{args.start_date}'. Используйте YYYY-MM-DD")
        return False
        
    if args.end_date and not validate_date(args.end_date):
        print(f"❌ Ошибка: Неверный формат конечной даты '{args.end_date}'. Используйте YYYY-MM-DD")
        return False
    
    # Запускаем демонстрацию
    if args.date:
        success = demo_single_date(args.date, args.max_emails)
    else:
        success = demo_date_range(args.start_date, args.end_date, args.max_emails)
    
    if success:
        print(f"\n🎯 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print(f"   Проверьте результаты в Google Sheets или локальных файлах")
        return True
    else:
        print(f"\n❌ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА С ОШИБКАМИ")
        print(f"   Проверьте логи и конфигурацию системы")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)