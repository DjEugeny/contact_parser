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

import json
import logging
import re
import sys
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Iterable, Sequence, Tuple

# Добавляем src в PYTHONPATH
# Добавляем корень репозитория в PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.fetcher.parsers.email_parser import EmailParser
from src.fetcher.attachments.attachment_registry import AttachmentRegistry
from src.fetcher.utils.enhanced_text_cleaner_with_precleaner import (
    EnhancedTextCleanerWithPreCleaner,
)


logging.basicConfig(level=logging.WARNING)
ATTACHMENT_REGISTRY = AttachmentRegistry(logging.getLogger("attachments-regression"))


@dataclass
class RegressionCase:
    """Описание тестового кейса."""

    name: str
    eml_path: Path | None
    must_contain: Sequence[str]
    optional_contains: Sequence[str] = ()
    must_not_strip: Sequence[str] = ()
    min_length: int = 500
    max_length: int | None = None
    json_path: Path | None = None
    min_attachments: int | None = None


def _resolve_eml_path(case: RegressionCase) -> Path:
    """📁 Определяет путь к файлу .eml."""
    if case.eml_path and case.eml_path.exists():
        return case.eml_path

    if case.json_path and case.json_path.exists():
        try:
            email_data = json.loads(case.json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FileNotFoundError(f"❌ Не удалось прочитать JSON {case.json_path}: {exc}") from exc

        data_dir = case.json_path.parents[2]  # .../data
        eml_relative = email_data.get("eml_path")
        if eml_relative:
            candidate = data_dir / eml_relative
            if candidate.exists():
                return candidate

        date_folder = email_data.get("date_folder")
        message_id = email_data.get("message_id", "")
        sanitized_id = re.sub(r"[^\w\-.]+", "_", message_id.strip("<>")) if message_id else ""
        if date_folder and sanitized_id:
            folder = data_dir / "eml" / date_folder
            if folder.exists():
                matches = sorted(folder.glob(f"{sanitized_id}_*.eml"))
                if matches:
                    return matches[0]

        missing_desc = (
            eml_relative
            if eml_relative
            else f"eml/{date_folder}/{sanitized_id or 'message'}*.eml"
        )
        raise FileNotFoundError(f"❌ Файл не найден: {data_dir / missing_desc}")

    raise FileNotFoundError(f"❌ Для кейса {case.name} не указан путь к .eml")


CASES: Iterable[RegressionCase] = [
    RegressionCase(
        name="HimLabService long thread",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "email_016_20250401_20250401_himlabservice_ru_06d4360a.json",
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
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "email_001_20250401_20250401_mail_ru_cd41b9aa.json",
        must_contain=[
            "mail.ru",
        ],
        min_length=50,
        max_length=1000,
    ),
    RegressionCase(
        name="Irkmed request",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "email_002_20250401_20250401_irkmed_ru_be1a753d.json",
        must_contain=[
            "Термит",
            "КП",
        ],
        min_length=200,
        max_length=2000,
    ),
    RegressionCase(
        name="Invitro software update",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "email_010_20250401_20250401_invitro_ru_b972f810.json",
        must_contain=[
            "От нас что для этого необходимо?",
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
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "email_018_20250401_20250401_invitro_ru_b972f810.json",
        must_contain=[
            "В каких числах ваш выход из отпуска?",
            "пользуетесь ли вы вкладкой \"Отчеты\"",
            "Форат Оксана Николаевна",
        ],
        min_length=1500,
        max_length=9000,
    ),
    RegressionCase(
        name="DNA Technology follow-up (17)",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "email_017_20250401_20250401_dna-technology_ru_5cee51dd.json",
        must_contain=[
            "Добрый день, уважаемые коллеги!",
            "Дубровских Даниил Сергеевич",
        ],
        min_length=2000,
        max_length=10000,
    ),
    RegressionCase(
        name="DNA Technology follow-up (19)",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "email_019_20250401_20250401_dna-technology_ru_5cee51dd.json",
        must_contain=[
            "Добрый день",
            "Роман Куропаткин",
        ],
        min_length=2000,
        max_length=10000,
    ),
    RegressionCase(
        name="DNA Technology follow-up (21)",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-01"
        / "email_021_20250401_20250401_dna-technology_ru_5cee51dd.json",
        must_contain=[
            "Именно их я и имел в виду.",
            "Форат Оксана Николаевна",
        ],
        min_length=2000,
        max_length=10000,
    ),
    RegressionCase(
        name="SibLabService request",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-02"
        / "email_002_20250402_20250402_siblabservice_ru_4a146063.json",
        must_contain=[
            "Менеджер ООО СибЛабСервис",
            "Клебанова Ирина",
            "Г. Иркутск",
        ],
        min_length=200,
        max_length=2000,
    ),
    RegressionCase(
        name="Forwarded request with emails",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-02"
        / "email_004_20250402_20250402_dna-technology_ru_8ec7fb4e.json",
        must_contain=[
            "s.voronova@dna-technology.ru",
            "bortsova@dna-technology.ru",
            "tkachenko@dna-technology.ru",
        ],
        min_length=500,
        max_length=4000,
        min_attachments=1,
    ),
    RegressionCase(
        name="Med3843 thread",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-02"
        / "email_006_20250402_20250402_med3843_ru_fd77b42b.json",
        must_contain=[
            "corp@med3843.ru",
            "m9@med3843.ru",
            "m.gogoleva@dna-technology.ru",
        ],
        min_length=1500,
        max_length=7000,
    ),
    RegressionCase(
        name="DNA forward Mironenko",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-02"
        / "email_009_20250402_20250402_dna-technology_ru_224cb438.json",
        must_contain=[
            "olgmironenko@mail.ru",
            "mail@dna-technology.ru",
        ],
        min_length=1000,
        max_length=6000,
    ),
    RegressionCase(
        name="SFO guests list",
        eml_path=None,
        json_path=REPO_ROOT
        / "data"
        / "emails"
        / "2025-04-02"
        / "email_025_20250402_20250402_dna-technology_ru_c5036846.json",
        must_contain=[
            "ООО Лабора г. Иркутск Ветрова Екатерина Владиславовна",
            "8-964-359-83-97",
            "Дата рождения: 09.07.02",
        ],
        min_length=2000,
        max_length=9000,
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


def run_case(case: RegressionCase, parser: EmailParser, cleaner: EnhancedTextCleanerWithPreCleaner) -> Tuple[list[str], Path | None]:
    """Проверяет инварианты для одного письма. Возвращает список замечаний и путь к .eml."""
    issues: list[str] = []
    try:
        eml_path = _resolve_eml_path(case)
    except FileNotFoundError as exc:
        return [str(exc)], None

    cleaned_text = load_clean_text(eml_path, parser, cleaner)
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

    if case.min_attachments is not None and case.json_path and case.json_path.exists():
        try:
            email_payload = json.loads(case.json_path.read_text(encoding="utf-8"))
            attachments = email_payload.get("attachments") or []
            attachments_count = len(attachments)
            if attachments_count < case.min_attachments:
                registry_records = ATTACHMENT_REGISTRY.get_attachments_for_message(
                    email_payload.get("message_id", ""),
                    email_payload.get("date_folder", ""),
                )
                attachments_count = len(registry_records)
            if attachments_count < case.min_attachments:
                issues.append(
                    f"❌ {case.name}: вложений {attachments_count} < ожидаемых {case.min_attachments}"
                )
        except json.JSONDecodeError as exc:
            issues.append(f"❌ {case.name}: ошибка чтения JSON для проверки вложений ({exc})")

    return issues, eml_path


def main() -> int:
    parser = EmailParser(logging.getLogger("email-parser"))
    cleaner = EnhancedTextCleanerWithPreCleaner(logging.getLogger("precleaner"))

    total_issues: list[str] = []
    for case in CASES:
        issues, eml_path = run_case(case, parser, cleaner)
        if issues:
            total_issues.extend(issues)
            for issue in issues:
                print(issue)
        else:
            eml_name = eml_path.name if eml_path else "unknown.eml"
            print(f"✅ {case.name}: все проверки пройдены ({eml_name})")

    if total_issues:
        print(f"\nИТОГ: {len(total_issues)} проблем(ы) обнаружено")
        return 1

    print("\nИТОГ: Все регрессионные проверки пройдены успешно")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
