#!/usr/bin/env python3
"""CLI утилита для удаления дубликатов вложений по SHA-256."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ..config.paths import DATA_DIR
from ..db.attachments_repository import AttachmentsRepository

logger = logging.getLogger("attachments_deduplicate")


def deduplicate(db_url: str | None, dry_run: bool) -> None:
    repo = AttachmentsRepository(db_url)
    duplicates = repo.fetch_duplicates()
    if not duplicates:
        logger.info("✅ Дубликаты не найдены")
        return

    attachments_root = DATA_DIR / "attachments"
    removed_files = 0

    for group in duplicates:
        keeper = group[0]
        logger.info(
            "🔁 Группа дубликатов sha256=%s (%d файлов)",
            keeper.sha256,
            len(group),
        )
        for record in group[1:]:
            file_path = attachments_root / record.email_date / record.stored_name
            payload = json.dumps(
                {
                    "kept_attachment_id": keeper.id,
                    "kept_file": keeper.stored_name,
                    "duplicate_file": record.stored_name,
                },
                ensure_ascii=False,
            )
            if dry_run:
                repo.log_event(
                    record.id,
                    "duplicate_detected",
                    payload=payload,
                    process="deduplicate",
                )
                continue

            if file_path.exists():
                try:
                    file_path.unlink()
                    removed_files += 1
                    logger.info("   🗑️ Удалён файл %s", file_path)
                except Exception as exc:  # pragma: no cover
                    logger.error("   ❌ Ошибка удаления %s: %s", file_path, exc)
            repo.update_status(record.id, "duplicate")
            repo.log_event(
                record.id,
                "duplicate_removed",
                payload=payload,
                process="deduplicate",
            )

    logger.info(
        "📊 Итог: обработано групп %d, удалено файлов %d", len(duplicates), removed_files
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Удаление дубликатов вложений")
    parser.add_argument("--db-url", help="Путь или URL SQLite", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только фиксировать события без удаления файлов",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    deduplicate(args.db_url, args.dry_run)


if __name__ == "__main__":
    main()
