#!/usr/bin/env python3
"""CLI для поиска и обработки файлов вложений без записей в БД."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..config.paths import DATA_DIR
from ..db.attachments_repository import AttachmentsRepository

logger = logging.getLogger("attachments_orphans")


def find_orphans(db_url: str | None, move: bool) -> None:
    repo = AttachmentsRepository(db_url)
    known = {
        (stored_name, email_date) for stored_name, email_date in repo.fetch_all_file_mappings()
    }

    attachments_root = DATA_DIR / "attachments"
    orphans: list[Path] = []

    for date_dir in attachments_root.glob("*/"):
        if not date_dir.is_dir():
            continue
        date_folder = date_dir.name
        for file_path in date_dir.iterdir():
            if not file_path.is_file():
                continue
            key = (file_path.name, date_folder)
            if key not in known:
                orphans.append(file_path)

    if not orphans:
        logger.info("✅ Орфанные файлы не найдены")
        return

    logger.info("🔍 Найдено %d орфанных файлов", len(orphans))

    if move:
        orphan_root = attachments_root / "orphans"
        orphan_root.mkdir(exist_ok=True)
        for orphan in orphans:
            target_dir = orphan_root / orphan.parent.name
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / orphan.name
            logger.info("   📦 Перемещаем %s → %s", orphan, target_path)
            orphan.rename(target_path)
    else:
        for orphan in orphans:
            logger.info("   ⚠️ %s", orphan)

    logger.info("📊 Итог: обработано %d файлов", len(orphans))


def main() -> None:
    parser = argparse.ArgumentParser(description="Поиск орфанных файлов вложений")
    parser.add_argument("--db-url", help="Путь или URL SQLite", default=None)
    parser.add_argument(
        "--move",
        action="store_true",
        help="Переместить найденные файлы в папку attachments/orphans",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    find_orphans(args.db_url, args.move)


if __name__ == "__main__":
    main()
