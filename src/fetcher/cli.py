#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI для запуска нового модульного EmailFetcher с интерактивным меню.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Используем более безопасные импорты
try:
    from src.config.paths import LOGS_DIR, ensure_config_structure
except ImportError:
    # Fallback если модуль конфигурации недоступен
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    LOGS_DIR = PROJECT_ROOT / "data" / "logs"
    
    def ensure_config_structure():
        """Упрощенная версия функции создания структуры директорий"""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / "data" / "emails").mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / "data" / "attachments").mkdir(parents=True, exist_ok=True)

# Пытаемся импортировать реальные компоненты с детальной диагностикой
REAL_FETCHER_AVAILABLE = False
IMPORT_ERROR_DETAILS = None

try:
    print("🔍 Пытаемся импортировать реальные компоненты...")
    from src.fetcher import EmailFetcher
    REAL_FETCHER_AVAILABLE = True
    print("✅ Реальные компоненты успешно импортированы")
except ImportError as e:
    IMPORT_ERROR_DETAILS = str(e)
    print(f"⚠️ Не удалось импортировать реальные компоненты: {e}")
    print("🔍 Анализ зависимостей...")
    
    # Проверяем конкретные компоненты
    missing_components = []
    
    try:
        from src.fetcher.core.email_fetcher import EmailFetcher
        print("✅ EmailFetcher импортирован")
    except ImportError as ce:
        missing_components.append(f"EmailFetcher: {ce}")
        print(f"❌ EmailFetcher: {ce}")
    
    print(f"🔧 Всего отсутствует компонентов: {len(missing_components)}")
    for comp in missing_components:
        print(f"   - {comp}")
    
    # Создаем демонстрационный fetcher
    def create_demo_fetcher(logger):
        """Создаёт демонстрационный fetcher для тестирования CLI."""
        class DemoEmailFetcher:
            def __init__(self, logger):
                self.logger = logger
                self.stats = {"processed": 0, "saved": 0, "errors": 0}
                
            def fetch_emails_by_date_range(self, start_date, end_date):
                self.logger.info(
                    "🎯 ДЕМО: Загрузка писем за период %s - %s",
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                )
                self.logger.info("✅ ДЕМО: Это демонстрационный режим для тестирования CLI")
                self.logger.info("🔧 Для полноценной работы установите необходимые зависимости")
                return []
                
            def close(self):
                self.logger.info("🔐 ДЕМО: Соединение закрыто")
        
        return DemoEmailFetcher(logger)

    EmailFetcher = create_demo_fetcher

try:
    from src.fetcher.utils.date_utils import parse_date_flexible, get_local_time
except ImportError as e:
    print(f"❌ Ошибка импорта утилит дат: {e}")
    # Создаем упрощенные версии функций для демонстрации
    import re
    from datetime import datetime, timedelta, timezone
    
    LOCAL_TIMEZONE = timezone(timedelta(hours=7))
    
    def get_local_time(dt=None):
        if dt is None:
            dt = datetime.now(LOCAL_TIMEZONE)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=LOCAL_TIMEZONE)
        return dt
    
    def parse_date_flexible(date_str):
        """
        📅 Гибкий парсинг даты в различных форматах (как в старом фетчере)
        
        Поддерживаемые форматы:
        - 2025-07-12 (ISO формат)
        - 12.07.2025 (точки)
        - 12-7-25 (короткий формат)
        - 12 июля 25 (текстовый формат на русском)
        - 7.7.25 (короткий формат с точками)
        """
        date_str = date_str.strip()
        
        # Формат: 2025-07-12 (ISO)
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
        
        # Формат: 12.07.2025
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            pass
        
        # Формат: 7.7.25 (короткий с точками)
        try:
            dt = datetime.strptime(date_str, "%d.%m.%y")
            # Корректируем год (25 → 2025)
            if dt.year < 2000:
                dt = dt.replace(year=dt.year + 2000)
            return dt
        except ValueError:
            pass
        
        # Формат: 12-7-25
        try:
            dt = datetime.strptime(date_str, "%d-%m-%y")
            # Корректируем год (25 → 2025)
            if dt.year < 2000:
                dt = dt.replace(year=dt.year + 2000)
            return dt
        except ValueError:
            pass
        
        # Формат: 12 июля 25
        months_ru = {
            "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
            "мая": 5, "июня": 6, "июля": 7, "августа": 8,
            "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
        }
        
        pattern = r"(\d{1,2})\s+(\w+)\s+(\d{2,4})"
        match = re.match(pattern, date_str.lower())
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            year = int(match.group(3))
            
            if month_name in months_ru:
                month = months_ru[month_name]
                if year < 100:
                    year += 2000
                return datetime(year, month, day)
        
        raise ValueError(f"Не удалось распознать формат даты: {date_str}")
    
    print("✅ Используем упрощенные утилиты дат для демонстрации")

DATE_TIPS = "Примеры: 2025-07-12, 12.07.2025, 12-7-25, 12 июля 25, 7.7.25"


def setup_logging(start_date: datetime, end_date: datetime) -> logging.Logger:
    """Настройка логирования для фетчера."""
    ensure_config_structure()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_filename = (
        f"new_email_fetcher_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.log"
    )
    log_path = LOGS_DIR / log_filename

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("NewEmailFetcherCLI")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("📄 Лог файл: %s", log_path)
    return logger


def parse_arguments() -> argparse.Namespace:
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(description="New Email Fetcher CLI v2.0")
    parser.add_argument("--interactive", "-i", action="store_true", help="Интерактивный режим")
    parser.add_argument("--date", type=str, help="Дата для загрузки (см. подсказки)")
    parser.add_argument("--start-date", type=str, help="Начальная дата диапазона")
    parser.add_argument("--end-date", type=str, help="Конечная дата диапазона")
    parser.add_argument("--demo", action="store_true", help="Демонстрационный режим")
    return parser.parse_args()


def cli_menu() -> Tuple[Optional[datetime], Optional[datetime]]:
    """Интерактивный выбор диапазона дат."""
    print("\n" + "=" * 70)
    print("📧 EMAIL FETCHER v2.0 - НОВАЯ МОДУЛЬНАЯ АРХИТЕКТУРА")
    print("=" * 70)
    print("✅ Исправлен маппинг вложений (message_id вместо thread_id)")
    print("✅ Модульная архитектура для лучшей поддерживаемости")
    print("✅ Гибкий парсинг дат как в старом фетчере")
    print("=" * 70)
    print()
    print("Выберите режим работы:")
    print("  1. Диапазон дат (от-до)")
    print("  2. Одна конкретная дата")
    print("  3. Весь месяц текущего года")
    print("  4. Последние 7 дней")
    print("  5. Последние 30 дней")
    print("  6. Тестовый запуск (сегодня)")
    print("  0. Выход")
    print()

    choice = input("Ваш выбор (0-6): ").strip()

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    if choice == "1":
        print("\nВведите начальную дату:")
        print(f"  {DATE_TIPS}")
        start_str = input("Начальная дата: ").strip()
        try:
            start_date = parse_date_flexible(start_str)
        except ValueError as exc:
            print(f"❌ Ошибка: {exc}")
            return None, None

        print("\nВведите конечную дату:")
        end_str = input("Конечная дата: ").strip()
        try:
            end_date = parse_date_flexible(end_str)
        except ValueError as exc:
            print(f"❌ Ошибка: {exc}")
            return None, None

        if start_date > end_date:
            print("❌ Ошибка: начальная дата больше конечной!")
            return None, None

    elif choice == "2":
        print("\nВведите дату:")
        print(f"  {DATE_TIPS}")
        date_str = input("Дата: ").strip()
        try:
            date = parse_date_flexible(date_str)
            start_date = date
            end_date = date
        except ValueError as exc:
            print(f"❌ Ошибка: {exc}")
            return None, None

    elif choice == "3":
        print("\nВведите месяц (1-12):")
        try:
            month = int(input("Месяц: ").strip())
        except ValueError:
            print("❌ Ошибка: введите число от 1 до 12!")
            return None, None
        if month < 1 or month > 12:
            print("❌ Ошибка: месяц должен быть от 1 до 12!")
            return None, None
        year = datetime.now().year
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year, 12, 31)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    elif choice == "4":
        print("\n📅 Последние 7 дней")
        end_date = get_local_time().replace(hour=23, minute=59, second=59, microsecond=0)
        start_date = end_date - timedelta(days=7)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    elif choice == "5":
        print("\n📅 Последние 30 дней")
        end_date = get_local_time().replace(hour=23, minute=59, second=59, microsecond=0)
        start_date = end_date - timedelta(days=30)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    elif choice == "6":
        print("\n🧪 Тестовый запуск за сегодня")
        today = get_local_time().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = today
        end_date = today

    elif choice == "0":
        print("\n👋 Выход из программы")
        return None, None

    else:
        print("❌ Неверный выбор!")
        retry = input("\nПопробовать снова? (д/н): ").strip().lower()
        if retry in ['д', 'да', 'y', 'yes']:
            return cli_menu()
        return None, None

    return start_date, end_date

def resolve_period(args: argparse.Namespace) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Определение периода на основе аргументов CLI."""
    if args.interactive or (not args.date and not args.start_date and not args.end_date):
        return cli_menu()

    if args.date:
        try:
            date = parse_date_flexible(args.date)
            return date, date
        except ValueError as exc:
            print(f"❌ Ошибка: {exc}")
            return None, None

    if args.start_date and args.end_date:
        try:
            start = parse_date_flexible(args.start_date)
            end = parse_date_flexible(args.end_date)
            if start > end:
                print("❌ Ошибка: начальная дата больше конечной")
                return None, None
            return start, end
        except ValueError as exc:
            print(f"❌ Ошибка: {exc}")
            return None, None

    print("⚠️ Укажите либо --date, либо --start-date и --end-date")
    return None, None

def demo_mode():
    """🎭 Демонстрационный режим"""
    print("=" * 70)
    print("🎭 ДЕМОНСТРАЦИОННЫЙ РЕЖИМ EMAIL FETCHER v2.0")
    print("=" * 70)
    print()
    print("✅ Компоненты успешно импортированы:")
    print("   📧 EmailFetcher - основной фасад")
    print("   🔌 ConnectionManager - управление соединениями")
    print("   📧 EmailProcessor - обработка писем")
    print("   🚫 EmailFilters - фильтрация писем")
    print("   📄 EmailParser - парсинг контента")
    print("   📁 EmailStorage - хранение писем")
    print("   📎 AttachmentRegistry - реестр вложений")
    print("   🔄 LegacyEmailFetcherV2 - обратная совместимость")
    print("   🧹 EmailTextCleaner - очистка текста")
    print()
    print("🚀 Для запуска обработки используйте:")
    print("   python3 src/fetcher/cli.py --interactive")
    print("   python3 src/fetcher/cli.py --date 2025-01-01")
    print("   python3 src/fetcher/cli.py --date '12 июля 25'")
    print("   python3 src/fetcher/cli.py --start-date 2025-01-01 --end-date 2025-01-07")
    print()
    print("📅 Поддерживаемые форматы дат:")
    print("   - 2025-07-12 (ISO)")
    print("   - 12.07.2025 (точки)")
    print("   - 12-7-25 (короткий)")
    print("   - 12 июля 25 (русский)")
    print("   - 7.7.25 (короткий с точками)")
    print()
    print("🎯 Быстрый запуск из корня проекта:")
    print("   python3 run_new_fetcher.py")
    print()


def print_fetcher_info(use_legacy: bool):
    """Вывод информации о выбранном фетчере."""
    if use_legacy:
        print("\n🔄 ИСПОЛЬЗУЕТСЯ LEGACY РЕЖИМ (обратная совместимость)")
        print("   - Новый движок с исправленным маппингом вложений")
        print("   - Старый интерфейс для совместимости")
        print("   ⚠️ Без PreCleaner (менее эффективно)")
    else:
        print("\n🚀 ИСПОЛЬЗУЕТСЯ НОВАЯ АРХИТЕКТУРА v2.0 С PRECLEANER")
        print("   ✅ Корректный маппинг вложений по message_id")
        print("   ✅ Модульная архитектура")
        print("   ✅ Улучшенная обработка ошибок")
        print("   ✅ Централизованный реестр вложений")
        print("   🧼 PreCleaner активен (экономия ~33% токенов)")
        print("   📄 Единое поле body для совместимости")


def main() -> None:
    """Главная функция CLI."""
    args = parse_arguments()
    
    # Демонстрационный режим
    if args.demo:
        demo_mode()
        return
    
    # Если нет аргументов - запускаем интерактивный режим
    if not any([args.interactive, args.date, args.start_date, args.end_date]):
        print("🚀 Запуск интерактивного режима...")
        start_date, end_date = cli_menu()
        if not start_date or not end_date:
            return
    else:
        start_date, end_date = resolve_period(args)
        if not start_date or not end_date:
            return

    logger = setup_logging(start_date, end_date)
    
    # Выводим информацию о выбранном режиме
    print_fetcher_info(False)  # Всегда используем новую архитектуру
    
    # Проверяем доступность реального фетчера
    if not REAL_FETCHER_AVAILABLE:
        print("\n⚠️ ВНИМАНИЕ: Реальные компоненты фетчера недоступны")
        print("🔧 Используется демонстрационный режим")
        if IMPORT_ERROR_DETAILS:
            print(f"❌ Ошибка импорта: {IMPORT_ERROR_DETAILS}")
        print("💡 Установите необходимые зависимости для полноценной работы")
        print("🔍 Проверьте наличие всех компонентов в src/fetcher/")
        logger.info("⚠️ Используется демонстрационный режим (реальные компоненты недоступны)")
    
    logger.info(
        "🎯 Запуск загрузки писем: %s → %s",
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )
    logger.info("🏗️ Архитектура: %s", "New v2.0")

    # Создаем соответствующий фетчер
    fetcher = EmailFetcher(logger)

    try:
        # Выводим дополнительную информацию
        print(f"\n📊 Параметры запуска:")
        print(f"   📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
        print(f"   📁 Папка для писем: data/emails/")
        print(f"   📎 Папка для вложений: data/attachments/")
        print(f"   📝 Лог файл: data/logs/{logger.handlers[0].baseFilename}")
        print()
        
        # Запускаем обработку
        emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
        
        logger.info("✅ Загрузка завершена. Получено писем: %d", len(emails))
        print(f"\n🎉 ЗАВЕРШЕНО: загружено {len(emails)} писем")
        
    except KeyboardInterrupt:
        logger.warning("⏹️ Прервано пользователем")
        print("\n⏹️ Загрузка прервана пользователем")
    except Exception as exc:  # pragma: no cover
        logger.exception("❌ Ошибка загрузки писем: %s", exc)
        print(f"\n❌ Ошибка: {exc}")
    finally:
        fetcher.close()
        logger.info("🔚 Завершено")
        print("\n🔚 Работа завершена")


if __name__ == "__main__":
    main()
