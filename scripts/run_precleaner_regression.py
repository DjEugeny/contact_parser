#!/usr/bin/env python3
"""
Регрессионная проверка PreCleaner на эталонных письмах.

Скрипт прогоняет конвейер EmailParser → EnhancedTextCleanerWithPreCleaner
для сохранённых `.eml` и проверяет ключевые инварианты:
    • контакты и подписи не теряются;
    • цитаты схлопываются, но первая с контактами остаётся;
    • итоговый текст не пустой и заметно короче исходного HTML.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Iterable, Sequence

# Добавляем src в PYTHONPATH
# Добавляем корень репозитория в PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.fetcher.parsers.email_parser import EmailParser
from src.fetcher.utils.enhanced_text_cleaner_with_precleaner import (
    EnhancedTextCleanerWithPreCleaner,
)


logging.basicConfig(level=logging.WARNING)


@dataclass
class RegressionCase:
    """Описание тестового кейса."""

    name: str
    eml_path: Path
    must_contain: Sequence[str]
    optional_contains: Sequence[str] = ()
    must_not_strip: Sequence[str] = ()
    min_length: int = 500
    max_length: int | None = None


CASES: Iterable[RegressionCase] = [
    RegressionCase(
        name="HimLabService long thread",
        eml_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "Re_ счет 4186.eml",
        must_contain=[
            "Сунцова Татьяна",
            "ООО \"ХимЛабСервис\"",
            "8 (3822) 42-45-35",
            "https://himlabservice.ru",
        ],
        optional_contains=["[quoted message elided"],
        min_length=4000,
        max_length=15000,
    ),
    RegressionCase(
        name="Mail.ru short mail",
        eml_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "001_письмо.eml",
        must_contain=[
            "mail.ru",
        ],
        min_length=50,
        max_length=1000,
    ),
    RegressionCase(
        name="Irkmed request",
        eml_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "002_запрос КП Термит.eml",
        must_contain=[
            "Термит",
            "КП",
        ],
        min_length=200,
        max_length=2000,
    ),
    RegressionCase(
        name="Invitro software update",
        eml_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "010_RE_ обновление ПО Менеджер Протоколов до версии 1.8.eml",
        must_contain=[
            "От нас что нужно?",
            "Форат Оксана Николаевна",
            "+7 (383) 344-97-27",
            "Дубровских Даниил Сергеевич",
        ],
        optional_contains=["[quoted message elided"],
        min_length=1500,
        max_length=8000,
    ),
    RegressionCase(
        name="Invitro follow-up",
        eml_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "018_RE_ обновление ПО Менеджер Протоколов до версии 1.8.eml",
        must_contain=[
            "Интересно Вы, конечно, поставили вопрос.",
            "Форат Оксана Николаевна",
        ],
        min_length=1500,
        max_length=9000,
    ),
    RegressionCase(
        name="DNA Technology follow-up (17)",
        eml_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "017_Re_ обновление ПО Менеджер Протоколов до версии 1.8.eml",
        must_contain=[
            "Коллеги, добрый день!",
            "Дубровских Даниил Сергеевич",
        ],
        min_length=2000,
        max_length=7000,
    ),
    RegressionCase(
        name="DNA Technology follow-up (19)",
        eml_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "019_Re_ обновление ПО Менеджер Протоколов до версии 1.8.eml",
        must_contain=[
            "Добрый день",
            "Роман Куропаткин",
        ],
        min_length=2000,
        max_length=7000,
    ),
    RegressionCase(
        name="DNA Technology follow-up (21)",
        eml_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "021_Re_ обновление ПО Менеджер Протоколов до версии 1.8.emл",
        must_contain=[
            "Если перечислите примеры специальных отчетов",
            "Форат Оксана Николаевна",
        ],
        min_length=2000,
        max_length=7000,
    ),
]


def load_clean_text(eml_path: Path, parser: EmailParser, cleaner: EnhancedTextCleanerWithPreCleaner) -> str:
    """Возвращает очищенный текст письма через рабочий конвейер."""
    with eml_path.open("rb") as fp:
        msg = BytesParser(policy=policy.default).parse(fp)
    raw_text = parser.extract_plain_text(msg)
    result = cleaner.clean_email_body_full(
        raw_text,
        thread_id="regression",
        sender_email=msg.get("From", "unknown"),
    )
    return result["cleaned_text"]


def run_case(case: RegressionCase, parser: EmailParser, cleaner: EnhancedTextCleanerWithPreCleaner) -> list[str]:
    """Проверяет инварианты для одного письма. Возвращает список замечаний."""
    issues: list[str] = []
    if not case.eml_path.exists():
        return [f"❌ Файл не найден: {case.eml_path}"]

    cleaned_text = load_clean_text(case.eml_path, parser, cleaner)
    length = len(cleaned_text)

    if length < case.min_length:
        issues.append(f"❌ {case.name}: длина {length} < минимальной {case.min_length}")
    if case.max_length and length > case.max_length:
        issues.append(f"❌ {case.name}: длина {length} > ожидаемой {case.max_length}")

    for snippet in case.must_contain:
        if snippet not in cleaned_text:
            issues.append(f"❌ {case.name}: отсутствует обязательный фрагмент «{snippet}»")

    for snippet in case.must_not_strip:
        if snippet.strip() and snippet not in cleaned_text:
            issues.append(f"❌ {case.name}: важная строка удалена «{snippet}»")

    for snippet in case.optional_contains:
        if snippet not in cleaned_text:
            issues.append(f"⚠️ {case.name}: нет ожидаемого индикатора «{snippet}»")

    return issues


def main() -> int:
    parser = EmailParser(logging.getLogger("email-parser"))
    cleaner = EnhancedTextCleanerWithPreCleaner(logging.getLogger("precleaner"))

    total_issues: list[str] = []
    for case in CASES:
        issues = run_case(case, parser, cleaner)
        if issues:
            total_issues.extend(issues)
            for issue in issues:
                print(issue)
        else:
            print(f"✅ {case.name}: все проверки пройдены ({case.eml_path.name})")

    if total_issues:
        print(f"\nИТОГ: {len(total_issues)} проблем(ы) обнаружено")
        return 1

    print("\nИТОГ: Все регрессионные проверки пройдены успешно")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
