#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI для запуска LegacyEmailFetcherV2 с выбором интервала дат."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.paths import LOGS_DIR, ensure_config_structure
from src.fetcher import LegacyEmailFetcherV2
from src.fetcher.utils.date_utils import parse_date_flexible

DATE_TIPS = "Примеры: 2025-07-12, 12.07.2025, 12-7-25, 12 июля 25"


def setup_logging(start_date: datetime, end_date: datetime) -> logging.Logger:
    ensure_config_structure()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_filename = (
        f"email_fetcher_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.log"
    )
    log_path = LOGS_DIR / log_filename

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("EmailFetcherCLI")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("📄 Лог файл: %s", log_path)
    return logger


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Legacy Email Fetcher CLI")
    parser.add_argument("--interactive", "-i", action="store_true", help="Интерактивный режим")
    parser.add_argument("--date", type=str, help="Дата для загрузки (см. подсказки)")
    parser.add_argument("--start-date", type=str, help="Начальная дата диапазона")
    parser.add_argument("--end-date", type=str, help="Конечная дата диапазона")
    return parser.parse_args()


def cli_menu() -> Tuple[Optional[datetime], Optional[datetime]]:
    print("\n=" * 35)
    print("🎛️  РЕЖИМ ВЫБОРА ДАТ")
    print("=" * 35)
    print("1. Диапазон дат")
    print("2. Одна дата")
    print("3. Текущий месяц")
    print("0. Выход")

    choice = input("Ваш выбор (0-3): ").strip()

    if choice == "1":
        print("\nВведите начальную дату")
        print(f"  {DATE_TIPS}")
        start_str = input("Начальная дата: ").strip()
        try:
            start_date = parse_date_flexible(start_str)
        except ValueError as exc:
            print(f"❌ Ошибка: {exc}")
            return None, None

        print("\nВведите конечную дату")
        end_str = input("Конечная дата: ").strip()
        try:
            end_date = parse_date_flexible(end_str)
        except ValueError as exc:
            print(f"❌ Ошибка: {exc}")
            return None, None

        if start_date > end_date:
            print("❌ Ошибка: начальная дата больше конечной")
            return None, None
        return start_date, end_date

    if choice == "2":
        print("\nВведите дату")
        print(f"  {DATE_TIPS}")
        date_str = input("Дата: ").strip()
        try:
            date = parse_date_flexible(date_str)
            return date, date
        except ValueError as exc:
            print(f"❌ Ошибка: {exc}")
            return None, None

    if choice == "3":
        print("\nВведите месяц (1-12)")
        try:
            month = int(input("Месяц: ").strip())
        except ValueError:
            print("❌ Ошибка: введите число от 1 до 12")
            return None, None

        if not 1 <= month <= 12:
            print("❌ Ошибка: месяц должен быть от 1 до 12")
            return None, None

        year = datetime.now().year
        start_date = datetime(year, month, 1)
        end_date = (datetime(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1))
        return start_date, end_date

    if choice == "0":
        print("👋 Выход")
        return None, None

    print("❌ Неверный выбор")
    return None, None


def resolve_period(args: argparse.Namespace) -> Tuple[Optional[datetime], Optional[datetime]]:
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


def main() -> None:
    args = parse_arguments()
    start_date, end_date = resolve_period(args)
    if not start_date or not end_date:
        return

    logger = setup_logging(start_date, end_date)
    logger.info(
        "🎯 Запуск загрузки писем: %s → %s",
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )

    fetcher = LegacyEmailFetcherV2(logger)
    try:
        emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
        logger.info("✅ Загрузка завершена. Получено писем: %d", len(emails))
    except KeyboardInterrupt:
        logger.warning("⏹️ Прервано пользователем")
    except Exception as exc:  # pragma: no cover
        logger.exception("❌ Ошибка загрузки писем: %s", exc)
    finally:
        fetcher.close()
        logger.info("🔚 Завершено")


if __name__ == "__main__":
    main()
