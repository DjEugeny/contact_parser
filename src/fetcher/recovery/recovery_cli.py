#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔄 CLI утилита для восстановления полных текстов писем
Исправляет проблему обрезанных текстов с пометкой "ТЕКСТ ОБРЕЗАН ДЛЯ ЭКОНОМИИ ТОКЕНОВ"
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Добавляем пути для импорта
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fetcher.recovery.text_recovery_module import TextRecoveryModule
from fetcher.config.paths import DATA_DIR


def parse_date_range(date_str: str) -> tuple:
    """Парсинг диапазона дат в формате YYYY-MM-DD,YYYY-MM-DD"""
    try:
        start_str, end_str = date_str.split(',')
        start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d').date()
        return (start_str, end_str)
    except Exception:
        raise ValueError("Неверный формат диапазона дат. Используйте: YYYY-MM-DD,YYYY-MM-DD")


def main():
    """🚀 Главная функция CLI"""
    parser = argparse.ArgumentParser(
        description="Восстановление полных текстов писем",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Сканирование на наличие обрезанных текстов
  python recovery_cli.py --scan
  
  # Восстановление всех обрезанных текстов
  python recovery_cli.py --recover-all
  
  # Восстановление за конкретную дату
  python recovery_cli.py --recover-all --date 2025-07-28
  
  # Восстановление за диапазон дат
  python recovery_cli.py --recover-all --date-range 2025-07-01,2025-07-31
  
  # Восстановление конкретного письма
  python recovery_cli.py --recover-message <message_id> --date 2025-07-28
        """
    )
    
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Только сканирование на наличие обрезанных текстов"
    )
    
    parser.add_argument(
        "--recover-all",
        action="store_true",
        help="Восстановление всех обрезанных текстов"
    )
    
    parser.add_argument(
        "--recover-message",
        type=str,
        help="Восстановление конкретного письма по Message-ID"
    )
    
    parser.add_argument(
        "--date",
        type=str,
        help="Дата обработки в формате YYYY-MM-DD"
    )
    
    parser.add_argument(
        "--date-range",
        type=str,
        help="Диапазон дат в формате YYYY-MM-DD,YYYY-MM-DD"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(DATA_DIR),
        help=f"Папка с данными (по умолчанию: {DATA_DIR})"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Подробное логирование"
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    import logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Загрузка переменных окружения
    load_dotenv(PROJECT_ROOT / ".env")
    
    # Инициализация модуля восстановления
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ Папка с данными не найдена: {data_dir}")
        sys.exit(1)
    
    recovery_module = TextRecoveryModule(data_dir)
    
    try:
        if args.scan:
            # Сканирование на наличие обрезанных текстов
            print("🔍 Сканирование на наличие обрезанных текстов...")
            truncated_emails = recovery_module.scan_truncated_emails()
            
            if truncated_emails:
                print(f"\n📊 Найдено обрезанных писем: {len(truncated_emails)}")
                print("\n📋 Список обрезанных писем:")
                for i, email in enumerate(truncated_emails[:10], 1):
                    print(f"  {i}. {email['date_folder']} - {email['subject'][:50]}...")
                    print(f"     Message-ID: {email['message_id']}")
                    print(f"     От: {email['from']}")
                
                if len(truncated_emails) > 10:
                    print(f"\n   ... и еще {len(truncated_emails) - 10} писем")
                
                print(f"\n🔄 Для восстановления выполните:")
                print(f"   python recovery_cli.py --recover-all")
            else:
                print("✅ Обрезанных текстов не найдено")
        
        elif args.recover_message:
            # Восстановление конкретного письма
            if not args.date:
                print("❌ Для восстановления конкретного письма указите --date")
                sys.exit(1)
            
            print(f"🔄 Восстановление письма: {args.recover_message}")
            result = recovery_module.recover_email_text(args.recover_message, args.date)
            
            if result.success:
                print(f"✅ Письмо восстановлено успешно:")
                print(f"   Файл: {result.file_path}")
                print(f"   Размер: {result.original_length} → {result.recovered_length} байт")
                print(f"   Контакты найдено: {result.contacts_found}")
                print(f"   Метод: {result.recovery_method}")
            else:
                print(f"❌ Не удалось восстановить письмо:")
                print(f"   Ошибка: {result.error_message}")
        
        elif args.recover_all:
            # Восстановление всех обрезанных текстов
            print("🔄 Начало восстановления всех обрезанных текстов...")
            
            date_range = None
            if args.date_range:
                date_range = parse_date_range(args.date_range)
                print(f"   Диапазон дат: {date_range[0]} - {date_range[1]}")
            elif args.date:
                date_range = (args.date, args.date)
                print(f"   Дата: {args.date}")
            
            # Создание резервной копии
            backup_dir = data_dir.parent / f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"💾 Создание резервной копии: {backup_dir}")
            
            import shutil
            shutil.copytree(data_dir, backup_dir)
            
            # Восстановление
            results = recovery_module.batch_recovery(date_range)
            
            # Статистика
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful
            
            print(f"\n📊 Результаты восстановления:")
            print(f"   ✅ Успешно: {successful}")
            print(f"   ❌ Неудачно: {failed}")
            
            if failed > 0:
                print(f"\n❌ Неудачные восстановления:")
                for result in results:
                    if not result.success:
                        print(f"   - {result.message_id}: {result.error_message}")
            
            print(f"\n💾 Резервная копия: {backup_dir}")
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n⏹️ Операция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()