"""SQLite-backed attachment registry with message_id mapping."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import fnmatch

from ...config.paths import CONFIG_DIR, DATA_DIR
from ...db.attachments_repository import AttachmentsRepository, AttachmentRecord
from ..utils.date_utils import get_local_time
from ..utils.email_utils import decode_header_value

SUPPORTED_ATTACHMENTS = {
    # PDF документы
    ".pdf": "application/pdf",
    
    # Microsoft Office документы
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    
    # 🆕 OpenDocument форматы (LibreOffice/OpenOffice) - только избранные
    ".odt": "application/vnd.oasis.opendocument.text",  # Текстовые документы
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",  # Электронные таблицы
    
    # Текстовые файлы
    ".txt": "text/plain",
    
    # Изображения
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".webp": "image/webp",
}

EXCLUDED_EXTENSIONS = {
    # Архивы
    ".zip",
    ".rar",
    ".7z",
    
    # Исполняемые файлы
    ".exe",
    ".msi",
    ".dmg",
    
    # Образы дисков
    ".iso",
    ".img",
    
    # 🆕 Презентации (обычно содержат графику, мало текста)
    ".pptx",
    ".ppt",
    ".ppsx",
    ".pps",
    
    # 🆕 Технические и системные форматы
    ".rt",
    ".trt",
    ".tr",
    ".r96",
    
    # 🆕 Мультимедиа (обычно не содержат текстовую информацию)
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".mkv",
}


class AttachmentRegistry:
    """Registry responsible for persisting attachment metadata."""

    def __init__(
        self,
        logger: logging.Logger,
        repository: Optional[AttachmentsRepository] = None,
        attachments_dir: Optional[Path] = None,
    ) -> None:
        self.logger = logger
        self.repository = repository or AttachmentsRepository()
        self.data_dir = DATA_DIR
        self.attachments_dir = attachments_dir or (self.data_dir / "attachments")
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

        self.filename_exclude_patterns = []
        patterns_path = CONFIG_DIR / "attachment_filename_excludes.txt"
        if patterns_path.exists():
            try:
                with open(patterns_path, "r", encoding="utf-8") as handler:
                    for line in handler:
                        pattern = line.strip()
                        if pattern and not pattern.startswith("#"):
                            self.filename_exclude_patterns.append(pattern)
                if self.filename_exclude_patterns:
                    self.logger.info(
                        "✅ Загружено %d паттернов исключения имен вложений",
                        len(self.filename_exclude_patterns),
                    )
            except Exception as exc:
                self.logger.warning(
                    "⚠️ Не удалось загрузить attachment_filename_excludes.txt: %s",
                    exc,
                )

        # Names of inline/system files to exclude completely
        self.specific_excluded_files = {
            "WRD0004.jpg",
            "WRD000.jpg",
            "WRD00.jpg",
            "WRD0.jpg",
            "~WRD0004.jpg",
            "~WRD000.jpg",
            "~WRD00.jpg",
            "~WRD0.jpg",
            "_.jpg",
            "_.png",
            "_.gif",
            "blocked.gif",
            "image001.png",
            "image002.png",
            "image003.png",
            "image004.png",
            "image005.png",
            "image006.png",
            "image007.png",
        }

        self.logger.info("📎 AttachmentRegistry инициализирован (SQLite)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def save_attachment(
        self,
        part,
        message_id: str,
        thread_id: str,
        date_folder: str,
        is_inline: bool = False,
    ) -> Optional[Dict]:
        """Persist attachment metadata and payload."""
        if not message_id:
            self.logger.error("❌ Не указан message_id для вложения")
            return None

        filename = part.get_filename()
        content_type = part.get_content_type()

        if not filename and is_inline and content_type.startswith("image/"):
            timestamp = get_local_time().strftime("%H%M%S_%f")
            extension = self._extension_from_mime(content_type)
            filename = f"inline_image_{timestamp}{extension}"
            self.logger.debug("🖼️ Генерируем имя для inline изображения: %s", filename)

        if not filename:
            self.logger.warning("⚠️ Вложение без имени пропущено")
            return {
                "status": "excluded",
                "reason": "missing_filename",
                "is_inline": is_inline,
            }

        filename = decode_header_value(filename)
        exclusion_reason = self._check_exclusions(filename, part, is_inline)
        if exclusion_reason:
            self.logger.debug("⏭️ Вложение '%s' исключено: %s", filename, exclusion_reason)
            return {
                "status": "excluded",
                "reason": exclusion_reason,
                "original_filename": filename,
                "is_inline": is_inline,
            }

        payload = part.get_payload(decode=True)
        if not payload:
            self.logger.warning("⚠️ Нет payload для вложения '%s'", filename)
            return {
                "status": "excluded",
                "reason": "empty_payload",
                "original_filename": filename,
                "is_inline": is_inline,
            }

        payload_hash = hashlib.sha256(payload).hexdigest()
        existing = self.repository.find_by_message_and_hash(message_id, payload_hash)
        if existing:
            self.logger.debug(
                "🔁 Найдено существующее вложение для message_id=%s (sha256=%s)",
                message_id,
                payload_hash,
            )
            self.repository.log_event(existing.id, "duplicate_skipped", process="fetcher")
            return self._record_to_dict(existing, status="already_exists")

        stored_name = self._create_safe_filename(filename, message_id, date_folder, is_inline)
        file_path = self._save_attachment_file(payload, stored_name, date_folder)
        file_size = file_path.stat().st_size if file_path.exists() else len(payload)

        record = self.repository.insert_attachment(
            message_id=message_id,
            thread_id=thread_id,
            email_date=date_folder,
            original_name=filename,
            stored_name=stored_name,
            content_type=content_type,
            file_size=file_size,
            sha256=payload_hash,
            is_inline=is_inline,
            status="saved",
        )
        self.repository.log_event(record.id, "created", process="fetcher")

        return self._record_to_dict(record, status="saved")

    def get_attachments_for_message(
        self, message_id: str, date_folder: Optional[str] = None
    ) -> List[Dict]:
        records = self.repository.fetch_by_message(message_id)
        if date_folder:
            records = [rec for rec in records if rec.email_date == date_folder]
        return [self._record_to_dict(rec, status=rec.status) for rec in records]

    def check_email_processing_status(self, message_id: str, date_folder: str) -> Dict:
        status = {
            "json_exists": False,
            "attachments_exist": False,
            "json_file_path": None,
            "attachment_files": [],
        }

        emails_dir = self.data_dir / "emails" / date_folder
        if emails_dir.exists():
            for json_file in emails_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as handler:
                        data = handler.read()
                    if message_id in data:
                        status["json_exists"] = True
                        status["json_file_path"] = str(json_file)
                        break
                except Exception as exc:
                    self.logger.warning(
                        "⚠️ Ошибка чтения %s: %s", json_file.name, exc
                    )

        attachments = self.get_attachments_for_message(message_id, date_folder)
        status["attachments_exist"] = bool(attachments)
        status["attachment_files"] = [att.get("file_path") for att in attachments]
        return status

    def get_attachments_by_message_id(self, message_id: str) -> List[AttachmentRecord]:
        return self.repository.fetch_by_message(message_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extension_from_mime(self, content_type: str) -> str:
        for ext, mime in SUPPORTED_ATTACHMENTS.items():
            if mime == content_type:
                return ext
        if "/" in content_type:
            return f".{content_type.split('/')[-1]}"
        return ".bin"

    def _check_exclusions(self, filename: str, part, is_inline: bool) -> Optional[str]:
        if filename in self.specific_excluded_files:
            return "filename_in_static_exclusions"

        extension = Path(filename).suffix.lower()
        if extension in EXCLUDED_EXTENSIONS:
            return f"extension_excluded:{extension}"

        if extension not in SUPPORTED_ATTACHMENTS:
            self.logger.debug(
                "ℹ️ Расширение %s не в списке SUPPORTED_ATTACHMENTS — сохраняем как есть",
                extension or "<none>",
            )

        fname_lower = filename.lower()
        for pattern in self.filename_exclude_patterns:
            pattern_lower = pattern.lower()
            if fnmatch.fnmatch(fname_lower, pattern_lower):
                return f"filename_matches_pattern:{pattern}"

        if is_inline:
            content_id = part.get("Content-ID", "").strip("<>")
            if content_id:
                return f"inline_content_id:{content_id}"
        return None

    def _create_safe_filename(
        self,
        original_filename: str,
        message_id: str,
        date_folder: str,
        is_inline: bool,
    ) -> str:
        message_hash = hashlib.md5(message_id.encode("utf-8")).hexdigest()[:8]
        safe_filename = re.sub(r"[^\w\s\-.]", "_", original_filename)
        timestamp = get_local_time().strftime("%H%M%S_%f")
        prefix = "inline" if is_inline else "attach"
        return (
            f"{date_folder.replace('-', '')}_{message_hash}_{timestamp}_{prefix}_{safe_filename}"
        )

    def _save_attachment_file(self, payload: bytes, stored_name: str, date_folder: str) -> Path:
        attachments_date_dir = self.attachments_dir / date_folder
        attachments_date_dir.mkdir(parents=True, exist_ok=True)
        file_path = attachments_date_dir / stored_name
        with open(file_path, "wb") as handler:
            handler.write(payload)
        self.logger.debug("💾 Файл сохранён: %s", file_path)
        return file_path

    def _record_to_dict(self, record: AttachmentRecord, status: str) -> Dict:
        relative_path = f"attachments/{record.email_date}/{record.stored_name}"
        absolute_path = str(self.attachments_dir / record.email_date / record.stored_name)
        return {
            "id": record.id,
            "original_filename": record.original_name,
            "saved_filename": record.stored_name,
            "file_path": absolute_path,
            "relative_path": relative_path,
            "file_size": record.file_size,
            "file_type": record.content_type,
            "content_type": record.content_type,
            "saved_at": record.saved_at,
            "status": status,
            "is_inline": record.is_inline,
            "message_id": record.message_id,
            "thread_id": record.thread_id,
            "sha256": record.sha256,
        }
