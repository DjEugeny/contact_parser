#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🎯 API Pipeline Validator — тонкий слой для сквозного прогонa Mini-CRM."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from dotenv import load_dotenv

# Добавляем корень проекта в PYTHONPATH до локальных импортов
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.extractor_factory import ExtractorFactory
from src.core.ocr_manager import get_ocr_manager
from src.email_loader import ProcessedEmailLoader
from src.reporting import ReportGenerator
from src.utils.logger import log_pipeline_event, log_system_event, log_error_event

load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
EMAILS_DIR = DATA_DIR / "emails"
LLM_RESULTS_DIR = DATA_DIR / "llm_results"
REPORTS_DIR = PROJECT_ROOT / "memory-bank" / "reports"
TEST_DATASET_PATH = PROJECT_ROOT / "memory-bank" / "test_dataset_10_emails.md"


@dataclass
class PipelineStats:
    """📊 Аккумулятор статистики по прогону."""

    emails_total: int = 0
    emails_successful: int = 0
    emails_failed: int = 0
    total_processing_time: float = 0.0
    organizations: int = 0
    contacts: int = 0
    commercial_offers: int = 0
    interactions: int = 0
    failures: List[Dict[str, Any]] = field(default_factory=list)

    def register_email(self, entry: Dict[str, Any]) -> None:
        """✅ Учитывает результат обработки письма."""
        self.emails_total += 1
        processing_time = entry.get("processing_time_seconds") or 0.0
        self.total_processing_time += processing_time

        if entry.get("success"):
            self.emails_successful += 1
        else:
            self.emails_failed += 1
            if entry.get("errors"):
                self.failures.append({
                    "filename": entry.get("filename"),
                    "errors": entry.get("errors"),
                    "processing_time_seconds": processing_time,
                })

        self.organizations += entry.get("organizations", 0)
        self.contacts += entry.get("contacts", 0)
        self.commercial_offers += entry.get("commercial_offers", 0)
        self.interactions += entry.get("interactions", 0)

    def register_failure(self, filename: str, error_message: str, processing_time: float) -> None:
        """❌ Регистрирует фатальную ошибку обработки."""
        entry = {
            "filename": filename,
            "success": False,
            "organizations": 0,
            "contacts": 0,
            "commercial_offers": 0,
            "interactions": 0,
            "processing_time_seconds": round(processing_time, 3),
            "errors": [error_message],
        }
        self.register_email(entry)

    def as_dict(self) -> Dict[str, Any]:
        """📚 Возвращает статистику в виде словаря."""
        average_time = 0.0
        if self.emails_total:
            average_time = self.total_processing_time / self.emails_total

        return {
            "emails_total": self.emails_total,
            "emails_successful": self.emails_successful,
            "emails_failed": self.emails_failed,
            "total_processing_time": round(self.total_processing_time, 3),
            "average_processing_time": round(average_time, 3),
            "organizations": self.organizations,
            "contacts": self.contacts,
            "commercial_offers": self.commercial_offers,
            "interactions": self.interactions,
            "failures": self.failures,
        }


class APIPipelineValidator:
    """🚀 Управляет запуском сквозного пайплайна LLM-валидации."""

    def __init__(self, args: argparse.Namespace) -> None:
        """🔧 Подготавливает окружение и зависимости."""
        self.mode = args.mode
        self.date = args.date
        self.count = args.count
        self.start_date = args.start_date
        self.end_date = args.end_date
        self.dry_run = args.dry_run

        self.project_root = PROJECT_ROOT
        self.data_dir = DATA_DIR
        self.emails_dir = EMAILS_DIR
        self.llm_results_dir = LLM_RESULTS_DIR
        self.llm_results_dir.mkdir(parents=True, exist_ok=True)

        self.loader = ProcessedEmailLoader()
        self.ocr_manager = get_ocr_manager()
        self.extractor = ExtractorFactory.create_extractor(test_mode=False)

        self.run_summaries: List[Dict[str, Any]] = []

        log_system_event(
            "api_validator_initialized",
            mode=self.mode,
            dry_run=self.dry_run,
        )

    def run(self) -> None:
        """🏁 Запускает обработку в выбранном режиме."""
        log_pipeline_event(event_type="api_validator_run", mode=self.mode, dry_run=self.dry_run)

        if self.mode == "first10":
            self._run_first10()
        elif self.mode == "batch":
            self._run_batch_mode()
        elif self.mode == "range":
            self._run_range_mode()
        else:
            raise ValueError(f"Неизвестный режим: {self.mode}")

    def _run_first10(self) -> None:
        """🧪 Обрабатывает тестовую выборку из 10 писем."""
        filenames = self._load_test_dataset()
        grouped = self._group_filenames_by_date(filenames)

        for date, date_filenames in grouped.items():
            email_paths = [self._resolve_email_path(date, name) for name in date_filenames]
            self._process_date(date, [path for path in email_paths if path is not None])

    def _run_batch_mode(self) -> None:
        """📦 Обрабатывает первые N писем за указанную дату."""
        if not self.date:
            raise ValueError("Для режима batch требуется параметр --date")
        if not self.count or self.count <= 0:
            raise ValueError("Для режима batch требуется положительное значение --count")

        date_dir = self.emails_dir / self.date
        if not date_dir.exists():
            raise FileNotFoundError(f"Директория с письмами за {self.date} не найдена: {date_dir}")

        email_paths = sorted(date_dir.glob("email_*.json"))[: self.count]
        self._process_date(self.date, email_paths)

    def _run_range_mode(self) -> None:
        """📆 Обрабатывает письма в диапазоне дат."""
        if not self.start_date or not self.end_date:
            raise ValueError("Для режима range требуются параметры --start и --end")

        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        if start > end:
            raise ValueError("Начальная дата должна быть меньше или равна конечной")

        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            date_dir = self.emails_dir / date_str
            if date_dir.exists():
                email_paths = sorted(date_dir.glob("email_*.json"))
                self._process_date(date_str, email_paths)
            else:
                print(f"⚠️  Письма за {date_str} не найдены, пропуск")
            current += timedelta(days=1)

    def _process_date(self, date: str, email_paths: Sequence[Path]) -> None:
        """📅 Обрабатывает все письма за конкретную дату."""
        if not email_paths:
            print(f"⚠️  Нет писем для обработки за {date}")
            return

        print(f"\n🎯 Запуск обработки за {date} — найдено {len(email_paths)} писем")
        report_generator = ReportGenerator(base_dir=self.llm_results_dir, date=date)
        stats = PipelineStats()

        for path in email_paths:
            if not path.exists():
                stats.register_failure(path.name, "Файл отсутствует", 0.0)
                continue
            self._process_single_email(date, path, report_generator, stats)

        summary_payload = report_generator.finalize(stats.as_dict())
        self._update_memory_bank_index(report_generator.summary_path, summary_payload)
        self.run_summaries.append(summary_payload)
        print(f"✅ Обработка за {date} завершена (успешно: {stats.emails_successful}, ошибки: {stats.emails_failed})")

    def _process_single_email(
        self,
        date: str,
        email_path: Path,
        report_generator: ReportGenerator,
        stats: PipelineStats,
    ) -> None:
        """🤖 Обрабатывает конкретный JSON-файл письма."""
        print(f"\n🔍 Обработка письма {email_path.name}")
        start_time = time.perf_counter()
        try:
            with email_path.open("r", encoding="utf-8") as handle:
                email_data = json.load(handle)

            metadata = self._build_email_metadata(email_data, email_path)
            combined_text = self._compose_combined_text(email_data, date)
            llm_metadata = self._build_llm_metadata(email_data, metadata, combined_text)

            log_pipeline_event(
                event_type="api_validator_email_start",
                filename=email_path.name,
                date=date,
                attachments=metadata.get("attachments_count"),
                dry_run=self.dry_run,
            )

            extraction_start = time.perf_counter()
            processed_result = self.extractor.extract_all_data(combined_text, llm_metadata)
            duration = time.perf_counter() - extraction_start

            raw_llm = processed_result.get("raw_llm_result", {})
            processed_copy = copy.deepcopy(processed_result)
            raw_payload = processed_copy.pop("raw_llm_result", raw_llm if isinstance(raw_llm, dict) else {})

            success = self._determine_success(processed_copy)
            processed_copy["success"] = success
            errors = self._collect_errors(processed_copy)

            entry = report_generator.register_email_result(
                filename=email_path.name,
                email_metadata=metadata,
                llm_raw=raw_payload or {},
                processed=processed_copy,
                processing_time_seconds=round(duration, 3),
                errors=errors,
            )
            stats.register_email(entry)

            if not self.dry_run:
                self._persist_to_database(processed_copy, metadata)

            log_pipeline_event(
                event_type="api_validator_email_done",
                filename=email_path.name,
                date=date,
                success=success,
                processing_time_seconds=round(time.perf_counter() - start_time, 3),
            )
        except Exception as exc:  # pylint: disable=broad-except
            elapsed = time.perf_counter() - start_time
            error_message = str(exc)
            stats.register_failure(email_path.name, error_message, elapsed)
            log_error_event(
                error_type="api_validator_email_failed",
                error_message=error_message,
                filename=email_path.name,
                date=date,
            )
            print(f"❌ Ошибка обработки {email_path.name}: {error_message}")

    def _compose_combined_text(self, email_data: Dict[str, Any], date: str) -> str:
        """📝 Собирает текст письма и извлечённые файлы вложений."""
        parts: List[str] = []
        body = email_data.get("body")
        if body:
            parts.append(f"=== ТЕКСТ ПИСЬМА ===\n{body}")

        attachments = email_data.get("attachments", [])
        if not attachments:
            return "\n\n".join(parts)

        for index, attachment in enumerate(attachments, start=1):
            status = attachment.get("status", "unknown")
            if status in {"excluded_by_filter", "excluded_by_size", "unsupported"}:
                continue

            attachment_text = self._get_attachment_text(email_data, attachment, date)
            if attachment_text:
                name = attachment.get("original_filename") or attachment.get("saved_filename") or f"attachment_{index}"
                parts.append(f"\n=== ВЛОЖЕНИЕ {index}: {name} ===\n{attachment_text}")

        return "\n\n".join(parts)

    def _get_attachment_text(self, email: Dict[str, Any], attachment: Dict[str, Any], date: str) -> Optional[str]:
        """📎 Извлекает текст вложения, используя готовый OCR или fallback."""
        existing_text = attachment.get("content")
        if existing_text and isinstance(existing_text, str) and existing_text.strip():
            return existing_text

        file_path = attachment.get("file_path") or attachment.get("relative_path")
        if not file_path:
            return None

        attachment_path = Path(file_path)
        if not attachment_path.is_absolute():
            attachment_path = self.project_root / file_path
        if not attachment_path.exists():
            # Пробуем восстановить путь через ProcessedEmailLoader
            recovered_path = self.loader.get_attachment_file_path(email, attachment)
            attachment_path = recovered_path if recovered_path else attachment_path

        if attachment_path.exists() and self.ocr_manager:
            try:
                ocr_result = self.ocr_manager.extract_text_from_file(str(attachment_path), date)
                if ocr_result.get("success") and ocr_result.get("text"):
                    return ocr_result["text"]
            except Exception as exc:  # pylint: disable=broad-except
                print(f"⚠️  OCR не удалось для {attachment_path.name}: {exc}")
        return None

    def _build_email_metadata(self, email_data: Dict[str, Any], email_path: Path) -> Dict[str, Any]:
        """📬 Формирует метаданные для отчёта по письму."""
        return {
            "from": email_data.get("from", ""),
            "to": ", ".join(email_data.get("to_emails", [])) or email_data.get("to", ""),
            "cc": ", ".join(email_data.get("cc_emails", [])) or email_data.get("cc", ""),
            "subject": email_data.get("subject", ""),
            "date": email_data.get("parsed_date") or email_data.get("date"),
            "attachments_count": len(email_data.get("attachments", [])),
            "char_count": email_data.get("char_count", 0),
            "message_id": email_data.get("message_id"),
            "thread_id": email_data.get("thread_id"),
            "file_path": str(email_path),
        }

    def _build_llm_metadata(
        self,
        email_data: Dict[str, Any],
        metadata: Dict[str, Any],
        combined_text: str,
    ) -> Dict[str, Any]:
        """🧠 Собирает метаданные для передачи в LLM."""
        return {
            "from": metadata.get("from"),
            "to": metadata.get("to"),
            "cc": metadata.get("cc"),
            "subject": metadata.get("subject"),
            "date": metadata.get("date"),
            "thread_id": metadata.get("thread_id"),
            "message_id": metadata.get("message_id"),
            "attachments": metadata.get("attachments_count"),
            "text_length": len(combined_text),
            "char_count_original": metadata.get("char_count", 0),
            "email_headers": email_data.get("headers"),
        }

    def _collect_errors(self, processed: Dict[str, Any]) -> List[str]:
        """🚨 Собирает ошибки из ответа LLM и постобработки."""
        errors: List[str] = []
        if processed.get("error"):
            errors.append(str(processed["error"]))
        validation_errors = processed.get("validation_errors")
        if validation_errors:
            if isinstance(validation_errors, list):
                errors.extend(str(item) for item in validation_errors)
            else:
                errors.append(str(validation_errors))
        return errors

    def _determine_success(self, processed: Dict[str, Any]) -> bool:
        """✅ Определяет успешность обработки письма."""
        if processed.get("success") is False:
            return False
        if processed.get("error"):
            return False
        has_entities = bool(
            processed.get("organizations")
            or processed.get("contacts")
            or processed.get("commercial_offers")
        )
        return has_entities

    def _persist_to_database(self, processed: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        """📥 Записывает данные в SQLite (заглушка с логированием)."""
        # TODO: Реализовать сохранение в crm.db согласно спецификации
        log_pipeline_event(
            event_type="api_validator_persist_stub",
            message="📥 Сохранение в БД пока не реализовано",
            subject=metadata.get("subject"),
        )

    def _load_test_dataset(self) -> List[str]:
        """📖 Загружает список файлов из тестовой выборки."""
        if not TEST_DATASET_PATH.exists():
            raise FileNotFoundError(f"Файл тестового датасета не найден: {TEST_DATASET_PATH}")

        filenames: List[str] = []
        content = TEST_DATASET_PATH.read_text(encoding="utf-8")
        for line in content.splitlines():
            if "**Файл:**" in line and "`" in line:
                candidate = line.split("`")
                if len(candidate) >= 2:
                    filename = candidate[1].strip()
                    if filename:
                        filenames.append(filename)
        return filenames

    def _group_filenames_by_date(self, filenames: Iterable[str]) -> Dict[str, List[str]]:
        """📆 Группирует имена файлов по датам."""
        grouped: Dict[str, List[str]] = {}
        for filename in filenames:
            date = self._infer_date_from_filename(filename)
            grouped.setdefault(date, []).append(filename)
        return grouped

    def _infer_date_from_filename(self, filename: str) -> str:
        """🗓️ Извлекает дату из имени файла email."""
        parts = filename.split("_")
        for part in parts:
            if len(part) == 8 and part.isdigit():
                return f"{part[:4]}-{part[4:6]}-{part[6:8]}"
        raise ValueError(f"Не удалось определить дату из имени файла: {filename}")

    def _resolve_email_path(self, date: str, filename: str) -> Optional[Path]:
        """📁 Строит путь до JSON-файла письма."""
        path = self.emails_dir / date / filename
        if not path.exists():
            print(f"⚠️  Файл {filename} не найден в {path.parent}")
            return None
        return path

    def _update_memory_bank_index(self, summary_path: Path, summary_payload: Dict[str, Any]) -> None:
        """🗂️ Добавляет ссылку на сводку в memory-bank/reports/index.md."""
        try:
            index_path = REPORTS_DIR / "index.md"
            relative_path = Path(summary_path).relative_to(self.project_root)
            entry = (
                f"- {datetime.now().isoformat(timespec='seconds')} · API Validator "
                f"{summary_payload['date']} ({summary_payload['run_id']}) — "
                f"{summary_payload['totals']['emails']} писем — [{relative_path}](../../{relative_path})"
            )
            with index_path.open("a", encoding="utf-8") as handle:
                handle.write(entry + "\n")
        except Exception as exc:  # pylint: disable=broad-except
            log_error_event(
                error_type="api_validator_index_update_failed",
                error_message=str(exc),
                summary_path=str(summary_path),
            )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """🧭 Разбирает аргументы командной строки."""
    parser = argparse.ArgumentParser(description="API Pipeline Validator")
    parser.add_argument("--mode", choices=["first10", "batch", "range"], default="first10")
    parser.add_argument("--date", help="Дата обработки для режима batch", default=None)
    parser.add_argument("--count", type=int, help="Количество писем для режима batch", default=10)
    parser.add_argument("--start", dest="start_date", help="Начальная дата для режима range", default=None)
    parser.add_argument("--end", dest="end_date", help="Конечная дата для режима range", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Не выполнять запись в БД")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    """🏃 Точка входа CLI."""
    args = parse_args(argv)
    validator = APIPipelineValidator(args)
    validator.run()


if __name__ == "__main__":
    main()
