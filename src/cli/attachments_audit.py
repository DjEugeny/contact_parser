#!/usr/bin/env python3
"""CLI для просмотра истории событий по вложениям."""

from __future__ import annotations

import argparse
import logging

from ..db.attachments_repository import AttachmentsRepository

logger = logging.getLogger("attachments_audit")


def audit(db_url: str | None, message_id: str | None, attachment_id: int | None) -> None:
    repo = AttachmentsRepository(db_url)

    if attachment_id is not None:
        record = repo.find_by_id(attachment_id)
        if not record:
            logger.warning("❌ Вложение с id=%s не найдено", attachment_id)
            return
        events = repo.fetch_events_for_attachment(attachment_id)
        _print_attachment(record)
        _print_events(events)
        return

    if message_id:
        records = repo.fetch_by_message(message_id)
        if not records:
            logger.warning("⚠️ Для message_id=%s вложений не найдено", message_id)
            return
        for record in records:
            events = repo.fetch_events_for_attachment(record.id)
            _print_attachment(record)
            _print_events(events)
            print("-" * 60)
        return

    logger.info("Укажите хотя бы message_id или attachment_id")


def _print_attachment(record) -> None:
    logger.info(
        "📎 Attachment id=%s message=%s file=%s status=%s",
        record.id,
        record.message_id,
        record.stored_name,
        record.status,
    )


def _print_events(events) -> None:
    if not events:
        logger.info("   (события отсутствуют)")
        return
    for event in events:
        logger.info(
            "   • [%s] %s payload=%s (process=%s)",
            event.occurred_at,
            event.event_type,
            event.payload or "-",
            event.process or "-",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Аудит событий вложений")
    parser.add_argument("--db-url", help="Путь или URL SQLite", default=None)
    parser.add_argument("--message-id", help="Message-ID письма", default=None)
    parser.add_argument(
        "--attachment-id", help="ID вложения", type=int, default=None
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    audit(args.db_url, args.message_id, args.attachment_id)


if __name__ == "__main__":
    main()
