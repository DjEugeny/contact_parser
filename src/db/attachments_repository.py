import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

DEFAULT_DB_URL = os.getenv("DB_URL", "sqlite:///./crm.db")


def _resolve_db_path(db_url: Optional[str]) -> Path:
    if not db_url:
        db_url = DEFAULT_DB_URL

    if db_url.startswith("sqlite:///"):
        raw_path = db_url[len("sqlite:///") :]
        if raw_path == ":memory:":
            return Path(raw_path)
        return Path(raw_path).expanduser().resolve()
    if db_url.startswith("sqlite://"):
        raw_path = db_url[len("sqlite://") :]
        if raw_path == ":memory:":
            return Path(raw_path)
        return Path(raw_path).expanduser().resolve()
    return Path(db_url).expanduser().resolve()


@dataclass
class AttachmentRecord:
    id: int
    message_id: str
    thread_id: Optional[str]
    email_date: str
    original_name: str
    stored_name: str
    content_type: Optional[str]
    file_size: Optional[int]
    sha256: str
    is_inline: bool
    status: str
    saved_at: str


@dataclass
class AttachmentEvent:
    id: int
    attachment_id: int
    event_type: str
    payload: Optional[str]
    process: Optional[str]
    occurred_at: str


class AttachmentsRepository:
    """SQLite-backed repository for attachment metadata."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_path = _resolve_db_path(db_url)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Connectivity helpers
    # ------------------------------------------------------------------
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _ensure_schema(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    thread_id TEXT,
                    email_date TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    stored_name TEXT NOT NULL UNIQUE,
                    content_type TEXT,
                    file_size INTEGER,
                    sha256 TEXT NOT NULL,
                    is_inline INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'saved',
                    saved_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_attachments_message_original
                    ON attachments(message_id, original_name);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_attachments_message_sha
                    ON attachments(message_id, sha256);
                CREATE INDEX IF NOT EXISTS idx_attachments_sha256
                    ON attachments(sha256);
                CREATE INDEX IF NOT EXISTS idx_attachments_message_date
                    ON attachments(message_id, email_date);

                CREATE TABLE IF NOT EXISTS attachment_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attachment_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT,
                    process TEXT,
                    occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (attachment_id) REFERENCES attachments(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_attachment_events_attachment
                    ON attachment_events(attachment_id);
                """
            )

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------
    def insert_attachment(
        self,
        *,
        message_id: str,
        thread_id: Optional[str],
        email_date: str,
        original_name: str,
        stored_name: str,
        content_type: Optional[str],
        file_size: Optional[int],
        sha256: str,
        is_inline: bool,
        status: str = "saved",
    ) -> AttachmentRecord:
        payload = (
            message_id,
            thread_id,
            email_date,
            original_name,
            stored_name,
            content_type,
            file_size,
            sha256,
            1 if is_inline else 0,
            status,
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO attachments (
                    message_id, thread_id, email_date, original_name, stored_name,
                    content_type, file_size, sha256, is_inline, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            row = conn.execute(
                "SELECT * FROM attachments WHERE id = last_insert_rowid()"
            ).fetchone()
        return self._row_to_attachment(row)

    def upsert_attachment(
        self,
        *,
        message_id: str,
        thread_id: Optional[str],
        email_date: str,
        original_name: str,
        stored_name: str,
        content_type: Optional[str],
        file_size: Optional[int],
        sha256: str,
        is_inline: bool,
        status: str = "saved",
    ) -> AttachmentRecord:
        payload = (
            message_id,
            thread_id,
            email_date,
            original_name,
            stored_name,
            content_type,
            file_size,
            sha256,
            1 if is_inline else 0,
            status,
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO attachments (
                    message_id, thread_id, email_date, original_name, stored_name,
                    content_type, file_size, sha256, is_inline, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id, original_name) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    email_date = excluded.email_date,
                    stored_name = excluded.stored_name,
                    content_type = excluded.content_type,
                    file_size = excluded.file_size,
                    sha256 = excluded.sha256,
                    is_inline = excluded.is_inline,
                    status = excluded.status,
                    saved_at = datetime('now')
                """,
                payload,
            )
            row = conn.execute(
                "SELECT * FROM attachments WHERE message_id = ? AND original_name = ?",
                (message_id, original_name),
            ).fetchone()
        return self._row_to_attachment(row)

    def update_status(self, attachment_id: int, status: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE attachments SET status = ?, saved_at = saved_at WHERE id = ?",
                (status, attachment_id),
            )

    def find_by_message_and_hash(
        self, message_id: str, sha256: str
    ) -> Optional[AttachmentRecord]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM attachments WHERE message_id = ? AND sha256 = ?",
                (message_id, sha256),
            ).fetchone()
        return self._row_to_attachment(row) if row else None

    def find_by_id(self, attachment_id: int) -> Optional[AttachmentRecord]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM attachments WHERE id = ?",
                (attachment_id,),
            ).fetchone()
        return self._row_to_attachment(row) if row else None

    def fetch_by_message(self, message_id: str) -> List[AttachmentRecord]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM attachments WHERE message_id = ? ORDER BY saved_at ASC",
                (message_id,),
            ).fetchall()
        return [self._row_to_attachment(row) for row in rows]

    def fetch_duplicates(self) -> List[Sequence[AttachmentRecord]]:
        duplicates: List[Sequence[AttachmentRecord]] = []
        with self._get_connection() as conn:
            sha_rows = conn.execute(
                "SELECT sha256 FROM attachments GROUP BY sha256 HAVING COUNT(*) > 1"
            ).fetchall()
            for sha_row in sha_rows:
                sha256 = sha_row["sha256"]
                rows = conn.execute(
                    "SELECT * FROM attachments WHERE sha256 = ? ORDER BY saved_at ASC",
                    (sha256,),
                ).fetchall()
                duplicates.append(
                    tuple(self._row_to_attachment(row) for row in rows)
                )
        return duplicates

    def fetch_all_file_mappings(self) -> List[tuple]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT stored_name, email_date FROM attachments"
            ).fetchall()
        return [(row["stored_name"], row["email_date"]) for row in rows]

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def log_event(
        self,
        attachment_id: int,
        event_type: str,
        payload: Optional[str] = None,
        process: Optional[str] = None,
    ) -> AttachmentEvent:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO attachment_events (attachment_id, event_type, payload, process)
                VALUES (?, ?, ?, ?)
                """,
                (attachment_id, event_type, payload, process),
            )
            row = conn.execute(
                "SELECT * FROM attachment_events WHERE id = last_insert_rowid()"
            ).fetchone()
        return self._row_to_event(row)

    def fetch_events_for_attachment(self, attachment_id: int) -> List[AttachmentEvent]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM attachment_events WHERE attachment_id = ? ORDER BY occurred_at ASC",
                (attachment_id,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def fetch_events_for_message(self, message_id: str) -> List[AttachmentEvent]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT e.*
                FROM attachment_events e
                JOIN attachments a ON a.id = e.attachment_id
                WHERE a.message_id = ?
                ORDER BY e.occurred_at ASC
                """,
                (message_id,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _row_to_attachment(self, row: sqlite3.Row) -> AttachmentRecord:
        return AttachmentRecord(
            id=row["id"],
            message_id=row["message_id"],
            thread_id=row["thread_id"],
            email_date=row["email_date"],
            original_name=row["original_name"],
            stored_name=row["stored_name"],
            content_type=row["content_type"],
            file_size=row["file_size"],
            sha256=row["sha256"],
            is_inline=bool(row["is_inline"]),
            status=row["status"],
            saved_at=row["saved_at"],
        )

    def _row_to_event(self, row: sqlite3.Row) -> AttachmentEvent:
        return AttachmentEvent(
            id=row["id"],
            attachment_id=row["attachment_id"],
            event_type=row["event_type"],
            payload=row["payload"],
            process=row["process"],
            occurred_at=row["occurred_at"],
        )

    # ------------------------------------------------------------------
    # Maintenance helpers
    # ------------------------------------------------------------------
    def delete_attachment(self, attachment_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))

    def iter_all(self) -> Iterable[AttachmentRecord]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM attachments ORDER BY id ASC").fetchall()
        for row in rows:
            yield self._row_to_attachment(row)

