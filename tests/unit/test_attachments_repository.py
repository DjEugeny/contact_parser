import tempfile
from pathlib import Path

from src.db.attachments_repository import AttachmentsRepository
from src.fetcher.attachments.attachment_registry import AttachmentRegistry


class FakePart:
    def __init__(self, payload: bytes, filename: str, content_type: str = "application/pdf"):
        self._payload = payload
        self._filename = filename
        self._content_type = content_type

    def get_payload(self, decode: bool = False):
        return self._payload

    def get_content_type(self) -> str:
        return self._content_type

    def get_filename(self) -> str:
        return self._filename

    def get(self, key: str, default: str = "") -> str:
        return ""  # Content-ID по умолчанию отсутствует


def test_repository_insert_and_fetch(tmp_path):
    db_path = tmp_path / "attachments.db"
    repo = AttachmentsRepository(f"sqlite:///{db_path}")

    record = repo.insert_attachment(
        message_id="msg-1",
        thread_id="thread-1",
        email_date="2025-05-05",
        original_name="invoice.pdf",
        stored_name="20250505_abcd1234_120000_attach_invoice.pdf",
        content_type="application/pdf",
        file_size=128,
        sha256="hash-1",
        is_inline=False,
    )

    fetched = repo.fetch_by_message("msg-1")
    assert len(fetched) == 1
    assert fetched[0].sha256 == record.sha256

    repo.log_event(record.id, "created")
    events = repo.fetch_events_for_attachment(record.id)
    assert events[0].event_type == "created"


def test_registry_skips_duplicates(tmp_path):
    db_path = tmp_path / "attachments.db"
    repo = AttachmentsRepository(f"sqlite:///{db_path}")
    attachments_dir = tmp_path / "attachments"

    registry = AttachmentRegistry(
        logger=_test_logger(),
        repository=repo,
        attachments_dir=attachments_dir,
    )

    part = FakePart(b"payload", "invoice.pdf")
    result_first = registry.save_attachment(
        part,
        message_id="msg-duplicate",
        thread_id="thread-duplicate",
        date_folder="2025-05-05",
        is_inline=False,
    )
    assert result_first["status"] == "saved"
    assert Path(result_first["file_path"]).exists()

    result_second = registry.save_attachment(
        part,
        message_id="msg-duplicate",
        thread_id="thread-duplicate",
        date_folder="2025-05-05",
        is_inline=False,
    )
    assert result_second["status"] == "already_exists"
    assert result_second["id"] == result_first["id"]


def _test_logger():
    import logging

    logger = logging.getLogger("test_attachment_registry")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
