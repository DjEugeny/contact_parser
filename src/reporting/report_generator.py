#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""📊 Модуль формирования отчётов для API Pipeline Validator."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import logger as global_logger


class ReportGenerator:
    """📄 Генератор JSON артефактов и агрегированных сводок (без Markdown отчётов)."""

    def __init__(
        self,
        base_dir: Path,
        date: str,
        run_id: Optional[str] = None,
        timezone: Optional[str] = None,
        log: Optional[Any] = None,
    ) -> None:
        """🚀 Инициализация генератора отчётов."""
        self.logger = log or global_logger.get_logger("report_generator")
        self.base_dir = Path(base_dir)
        self.date = date
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.timezone = timezone or "UTC"
        self.run_started_at = datetime.now().astimezone().isoformat()

        self.run_dir = self.base_dir / date
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.raw_dir = self.run_dir / "raw"
        self.raw_dir.mkdir(exist_ok=True)
        # Markdown отчёты отключены - оставляем только raw и processed JSON

        self.summary_path = self.run_dir / f"_summary_{self.run_id}.json"
        # Markdown отчёты отключены
        self.fallback_dir = self.base_dir / "_failed_reports"

        self.entries: List[Dict[str, Any]] = []
        self.logger.info(
            "report_generator_initialized",
            message="🔧 Инициализирован генератор отчётов",
            date=self.date,
            run_id=self.run_id,
            base_dir=str(self.base_dir),
        )

    def register_email_result(
        self,
        filename: str,
        email_metadata: Dict[str, Any],
        llm_raw: Dict[str, Any],
        processed: Dict[str, Any],
        processing_time_seconds: Optional[float],
        errors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """🧾 Формирует артефакты для одного письма."""
        errors = errors or []
        slug = self._build_slug(filename)
        timestamp_suffix = datetime.now().strftime("%H%M%S")

        self._cleanup_previous_artifacts(slug)

        raw_path = self.raw_dir / f"{slug}_{self.run_id}_{timestamp_suffix}_raw.json"
        processed_path = self.run_dir / f"{slug}_{self.run_id}_{timestamp_suffix}_processed.json"

        self.logger.debug(
            "report_generator_prepare_email",
            message="🔍 Формирование артефактов письма",
            filename=filename,
            slug=slug,
        )

        self._write_json_file(raw_path, {"source_file": filename, "llm_response": llm_raw})
        self._write_json_file(processed_path, {"source_file": filename, "processed_result": processed})

        # Markdown отчёты отключены - генерируем только JSON артефакты

        # Извлекаем информацию о стратегии обработки
        processing_strategy = processed.get("processing_strategy", "standard")
        fallback_reason = processed.get("fallback_reason", None)
        
        entry = {
            "filename": filename,
            "success": processed.get("success", True),
            "organizations": len(processed.get("organizations", [])),
            "contacts": len(processed.get("contacts", [])),
            "commercial_offers": len(processed.get("commercial_offers", [])),
            "interactions": len(processed.get("interactions", [])),
            "processing_time_seconds": processing_time_seconds,
            "raw_json": str(Path("raw") / raw_path.name),
            "processed_json": processed_path.name,
            "errors": errors,
            "processing_strategy": processing_strategy,
            "fallback_reason": fallback_reason,
            "was_retried": processing_strategy != "standard",
        }
        self.entries.append(entry)
        self.logger.info(
            "report_generator_email_ready",
            message="✅ Отчёты сформированы",
            filename=filename,
            organizations=entry["organizations"],
            contacts=entry["contacts"],
            commercial_offers=entry["commercial_offers"],
            interactions=entry["interactions"],
        )

        return entry

    def _cleanup_previous_artifacts(self, slug: str) -> None:
        """🧹 Удаляет артефакты повтора для одного письма в рамках запуска."""
        raw_pattern = f"{slug}_{self.run_id}_*_raw.json"
        processed_pattern = f"{slug}_{self.run_id}_*_processed.json"

        for path in self.raw_dir.glob(raw_pattern):
            self._safe_unlink(path)
        for path in self.run_dir.glob(processed_pattern):
            self._safe_unlink(path)
        # Markdown отчёты отключены

    def finalize(self, run_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """🏁 Завершает формирование отчётов и выпускает сводки."""
        totals = self._calculate_totals()
        summary_payload = {
            "date": self.date,
            "run_id": self.run_id,
            "timezone": self.timezone,
            "started_at": self.run_started_at,
            "completed_at": datetime.now().astimezone().isoformat(),
            "totals": totals,
            "entries": self.entries,
            "run_stats": run_stats or {},
        }

        self._write_json_file(self.summary_path, summary_payload)
        # Markdown отчёты отключены - генерируем только JSON сводку

        self.logger.info(
            "report_generator_summary_ready",
            message="📊 Сводный отчёт сохранён",
            summary_path=str(self.summary_path),
            total_emails=totals["emails"],
            success=totals["success"],
        )
        return summary_payload

    def _calculate_totals(self) -> Dict[str, Any]:
        """📈 Рассчитывает агрегированные показатели по письмам."""
        total_emails = len(self.entries)
        success_count = sum(1 for entry in self.entries if entry.get("success"))
        totals = {
            "emails": total_emails,
            "success": success_count,
            "failed": total_emails - success_count,
            "organizations": sum(entry["organizations"] for entry in self.entries),
            "contacts": sum(entry["contacts"] for entry in self.entries),
            "commercial_offers": sum(entry["commercial_offers"] for entry in self.entries),
            "interactions": sum(entry["interactions"] for entry in self.entries),
        }
        return totals


    def _write_json_file(self, path: Path, payload: Dict[str, Any]) -> None:
        """💾 Сохраняет JSON с системой резервного копирования."""
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                self._flush_and_sync(handle)
            self._sync_directory(path.parent)
        except Exception as error:
            self.logger.error(
                "report_generator_json_write_failed",
                message="❌ Ошибка записи JSON",
                target_path=str(path),
                error=str(error),
            )
            self._write_json_fallback(path.name, payload)

    def _write_json_fallback(self, filename: str, payload: Dict[str, Any]) -> None:
        """🛟 Резервная запись JSON в fallback-директорию."""
        try:
            self.fallback_dir.mkdir(parents=True, exist_ok=True)
            fallback_path = self.fallback_dir / filename
            with fallback_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                self._flush_and_sync(handle)
            self._sync_directory(fallback_path.parent)
            self.logger.warning(
                "report_generator_json_fallback_saved",
                message="⚠️ JSON сохранён в fallback",
                fallback_path=str(fallback_path),
            )
        except Exception as fallback_error:
            self.logger.critical(
                "report_generator_json_fallback_failed",
                message="🚨 Полный отказ записи JSON",
                filename=filename,
                error=str(fallback_error),
            )


    def _safe_unlink(self, path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except Exception as cleanup_error:  # pylint: disable=broad-except
            self.logger.warning(
                "report_generator_cleanup_failed",
                message="⚠️ Не удалось удалить старый артефакт",
                path=str(path),
                error=str(cleanup_error),
            )

    @staticmethod
    def _flush_and_sync(handle: Any) -> None:
        handle.flush()
        os.fsync(handle.fileno())

    def _sync_directory(self, directory: Path) -> None:
        try:
            fd = os.open(directory, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(fd)
        except OSError:
            pass
        finally:
            os.close(fd)


    def _build_slug(self, filename: str) -> str:
        """🔤 Формирует безопасный slug из имени файла."""
        stem = Path(filename).stem
        safe = [ch if ch.isalnum() else "_" for ch in stem]
        return "".join(safe).strip("_") or "email"

