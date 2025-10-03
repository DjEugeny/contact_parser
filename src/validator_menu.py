#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🎯 API Pipeline Validator CLI Menu - Updated Version with Dynamic Date Selection"""

from pathlib import Path
from typing import List, Optional, Dict
import sys
import os

# Add project root to sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Data directory path
BASE_DIR = PROJECT_ROOT / "data" / "emails"

def list_dates(base_dir: Path) -> List[Path]:
    """📅 Получить список папок с датами"""
    if not base_dir.exists():
        return []
    return sorted([p for p in base_dir.iterdir() if p.is_dir() and p.name.count('-') == 2])

def list_emails_for_date(date_dir: Path) -> List[Path]:
    """📧 Получить список email файлов для конкретной даты"""
    if not date_dir.exists():
        return []
    emails = [p for p in date_dir.iterdir() if p.is_file() and not p.name.startswith(".") and p.name.endswith('.json')]
    emails.sort(key=lambda p: p.name)  # детерминированный порядок
    return emails

def print_header(title: str):
    """🖨️ Печать заголовка"""
    print("=" * 50)
    print(title)
    print("=" * 50)

def prompt_input(prompt: str) -> str:
    """⌨️ Безопасный ввод с обработкой EOF"""
    try:
        return input(prompt)
    except EOFError:
        return "q"

def select_date(dates: List[Path]) -> Optional[Path]:
    """📅 Выбор даты из списка"""
    while True:
        print_header("ВЫБОР ДАТЫ")
        if not dates:
            print(f"Папка {BASE_DIR} пуста или недоступна.")
            return None
        for idx, d in enumerate(dates, start=1):
            email_count = len(list_emails_for_date(d))
            print(f"{idx}. {d.name} ({email_count} писем)")
        print("q. Выход")
        choice = prompt_input("Выберите дату (номер) или q: ").strip().lower()
        if choice in {"q", "й"}:
            return None
        if choice.isdigit():
            i = int(choice)
            if 1 <= i <= len(dates):
                return dates[i - 1]
        print("❌ Неверный выбор\n")

def build_submenu_options(total: int) -> List[tuple]:
    """🔧 Построить опции подменю в зависимости от количества писем"""
    # Вернет список (key, label, handler_id)
    opts = []
    opts.append(("1", "Выбор конкретного письма(писем)", "pick_specific"))
    n = total
    if n >= 3:
        opts.append(("2", f"Первые 3 письма (3 из {n})", "first3"))
    if n > 10:
        next_key = str(len(opts) + 1)
        opts.append((next_key, f"Первые 10 писем (10 из {n})", "first10"))
    next_key = str(len(opts) + 1)
    opts.append((next_key, f"Все письма за дату ({n})", "all"))
    next_key = str(len(opts) + 1)
    opts.append((next_key, "Назад", "back"))
    return opts

def parse_multi_indices(s: str, max_n: int) -> List[int]:
    """
    🔢 Парсит ввод вроде '1,3,5-7, 10–12,14—16' в уникальные 0-based индексы (ограничивает 1..max_n).
    Поддерживает дефисы '-', '–', '—'. Пробелы игнорируются. Дубликаты устраняются,
    порядок сохраняется в порядке появления во вводе.
    """
    if not s or not s.strip():
        return []
    normalized = s.replace(" ", "")
    parts = [p for p in normalized.split(",") if p != ""]
    idxs: List[int] = []
    def add_idx(one_based: int):
        if 1 <= one_based <= max_n:
            zero_based = one_based - 1
            if zero_based not in idxs:
                idxs.append(zero_based)

    for part in parts:
        # определим тип дефиса, если это диапазон
        for dash in ("-", "–", "—"):
            if dash in part:
                left, right = part.split(dash, 1)
                if left.isdigit() and right.isdigit():
                    a, b = int(left), int(right)
                    if a > b:
                        a, b = b, a
                    for val in range(a, b + 1):
                        add_idx(val)
                break
        else:
            # одиночное число
            if part.isdigit():
                add_idx(int(part))

    return idxs

def process_batch(email_paths: List[Path], validator=None):
    """🔄 Обработка пакета писем через API Pipeline Validator"""
    print(f"▶ Обработка {len(email_paths)} письм(а):")
    for p in email_paths:
        print(f"  - {p}")
    
    if validator:
        # Определяем дату из первого файла
        if email_paths:
            date_from_path = email_paths[0].parent.name
            print(f"📅 Дата обработки: {date_from_path}")
            
            # Создаем список имен файлов для обработки
            email_files = [p.name for p in email_paths]
            
            try:
                # Вызываем обработку через валидатор
                validator.process_specific_emails(date_from_path, email_files)
                print("✅ Обработка завершена успешно")
            except Exception as e:
                print(f"❌ Ошибка при обработке: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("⚠️ Валидатор не передан, выполняется только демонстрация")

def date_submenu(date_dir: Path, validator=None):
    """📂 Подменю для конкретной даты"""
    emails = list_emails_for_date(date_dir)
    n = len(emails)
    while True:
        print_header(f"ДАТА: {date_dir.name} — {n} писем")
        if n == 0:
            print("В этой дате писем нет. Нажмите Enter для возврата.")
            prompt_input("")
            return
        opts = build_submenu_options(n)
        for key, label, _ in opts:
            print(f"{key}. {label}")
        choice = prompt_input("Выберите опцию: ").strip()
        handlers = {key: hid for key, _, hid in opts}
        hid = handlers.get(choice)
        if not hid:
            print("❌ Неверный выбор\n")
            continue
        if hid == "back":
            return
        if hid == "pick_specific":
            print("\nСписок писем:")
            for i, p in enumerate(emails, start=1):
                print(f"{i}. {p.name}")
            print("Подсказка: можно вводить номера и диапазоны, например: 1,3,7-9 или 2–4, 6, 10—12")
            sel = prompt_input("Введите номера/диапазоны через запятую: ")
            idxs = parse_multi_indices(sel, n)
            if not idxs:
                print("⚠ Ничего не выбрано.\n")
                continue
            chosen = [emails[i] for i in idxs]
            process_batch(chosen, validator)
        elif hid == "first3":
            process_batch(emails[:3], validator)
        elif hid == "first10":
            process_batch(emails[:10], validator)
        elif hid == "all":
            process_batch(emails, validator)
        prompt_input("\nНажмите Enter, чтобы вернуться в подменю...")

def main_menu(validator=None):
    """🏠 Главное меню выбора дат"""
    dates = list_dates(BASE_DIR)
    while True:
        date = select_date(dates)
        if date is None:
            print("👋 Выход.")
            return
        date_submenu(date, validator)

def main():
    """🚀 Точка входа для standalone запуска"""
    main_menu()

if __name__ == "__main__":
    main()