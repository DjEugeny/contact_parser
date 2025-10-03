# Обновление CLI «API PIPELINE VALIDATOR»: выбор диапазонов и улучшенное меню

---

## Что изменилось
1. Убраны пункты про «Стартовый датасет 2025-07-29» и все режимы `first10/batch` из главного меню. И вся логика в коде по выбору стартового датасета писем из test_dataset_10_emails.md и режима `batch`
2. Первый экран теперь **сразу** показывает «Выбор даты» (список папок `data/emails/YYYY-MM-DD`).
3. Подменю даты **динамическое** и зависит от количества писем в папке:
   - `Выбор конкретного письма(писем)` — всегда. Поддерживает ввод **номеров и диапазонов**: `1,3,7-9`.
   - `Первые 3 письма (3 из N)` — если писем ≥ 3.
   - `Первые 10 писем (10 из N)` — если писем > 10.
   - `Все письма за дату (N)` — всегда.
   - `Назад` — возврат к выбору даты.
4. Парсер выбора поддерживает:
   - одиночные номера (`3`),  
   - диапазоны (`1-5`), в том числе с длинным тире (`1–5`, `1—5`),  
   - смешанные списки (`1,4-6, 10,12–14`).  
   Дубликаты удаляются, порядок — как в вводе. Вне-диапазонные номера игнорируются.

---

## Полный скрипт (drop-in)
Сохраните как `validator_menu.py` или замените текущий entrypoint. При необходимости поправьте `BASE_DIR`.

```python
from pathlib import Path
from typing import List

BASE_DIR = Path("data/emails")

def list_dates(base_dir: Path) -> List[Path]:
    if not base_dir.exists():
        return []
    return sorted([p for p in base_dir.iterdir() if p.is_dir()])

def list_emails_for_date(date_dir: Path) -> List[Path]:
    if not date_dir.exists():
        return []
    emails = [p for p in date_dir.iterdir() if p.is_file() and not p.name.startswith(".")]
    emails.sort(key=lambda p: p.name)  # детерминированный порядок
    return emails

def print_header(title: str):
    print("=" * 50)
    print(title)
    print("=" * 50)

def prompt_input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return "q"

def select_date(dates: List[Path]) -> Path | None:
    while True:
        print_header("ВЫБОР ДАТЫ")
        if not dates:
            print(f"Папка {BASE_DIR} пуста или недоступна.")
            return None
        for idx, d in enumerate(dates, start=1):
            print(f"{idx}. {d.name}")
        print("q. Выход")
        choice = prompt_input("Выберите дату (номер) или q: ").strip().lower()
        if choice in {"q", "й"}:
            return None
        if choice.isdigit():
            i = int(choice)
            if 1 <= i <= len(dates):
                return dates[i - 1]
        print("❌ Неверный выбор
")

def build_submenu_options(total: int) -> List[tuple]:
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
    Парсит ввод вроде '1,3,5-7, 10–12,14—16' в уникальные 0-based индексы (ограничивает 1..max_n).
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

# TODO: Заменить на твой реальный раннер пайплайна
def process_batch(email_paths: List[Path]):
    print(f"▶ Обработка {len(email_paths)} письм(а):")
    for p in email_paths:
        print(f"  - {p}")

def date_submenu(date_dir: Path):
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
            print("❌ Неверный выбор
")
            continue
        if hid == "back":
            return
        if hid == "pick_specific":
            print("
Список писем:")
            for i, p in enumerate(emails, start=1):
                print(f"{i}. {p.name}")
            print("Подсказка: можно вводить номера и диапазоны, например: 1,3,7-9 или 2–4, 6, 10—12")
            sel = prompt_input("Введите номера/диапазоны через запятую: ")
            idxs = parse_multi_indices(sel, n)
            if not idxs:
                print("⚠ Ничего не выбрано.
")
                continue
            chosen = [emails[i] for i in idxs]
            process_batch(chosen)
        elif hid == "first3":
            process_batch(emails[:3])
        elif hid == "first10":
            process_batch(emails[:10])
        elif hid == "all":
            process_batch(emails)
        prompt_input("
Нажмите Enter, чтобы вернуться в подменю...")

def main():
    dates = list_dates(BASE_DIR)
    while True:
        date = select_date(dates)
        if date is None:
            print("👋 Выход.")
            return
        date_submenu(date)

if __name__ == "__main__":
    main()
```

---

## Примеры ввода
- `1,3,7-9` → письма № 1, 3, 7, 8, 9  
- `2–4, 6, 10—12` → письма № 2, 3, 4, 6, 10, 11, 12  
- `5-3` → автоматически нормализуется в `3-5`  
- `0, 999` → игнор (вне диапазона)

---

## Точки интеграции
Вместо `process_batch()` вызовите ваш пайплайн, например:
```python
from pipeline import run_on_emails
def process_batch(email_paths):
    run_on_emails(email_paths)
```
