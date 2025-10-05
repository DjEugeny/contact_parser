#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🎯 API Pipeline Validator — тонкий слой для сквозного прогонa Mini-CRM."""

from __future__ import annotations

import argparse
import atexit
import copy
import io
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from dotenv import load_dotenv


class TeeStream(io.TextIOBase):
    """🪢 Дублирует поток в файл и консоль."""

    def __init__(self, original: io.TextIOBase, mirror: io.TextIOBase) -> None:
        self.original = original
        self.mirror = mirror

    @property
    def encoding(self) -> str:  # type: ignore[override]
        return getattr(self.original, "encoding", "utf-8")

    def write(self, data: str) -> int:  # type: ignore[override]
        text = str(data)
        self.original.write(text)
        self.mirror.write(text)
        self.mirror.flush()
        return len(text)

    def flush(self) -> None:  # type: ignore[override]
        self.original.flush()
        self.mirror.flush()

    def fileno(self) -> int:  # type: ignore[override]
        return self.original.fileno()

    def isatty(self) -> bool:  # type: ignore[override]
        return self.original.isatty()

    def readable(self) -> bool:  # type: ignore[override]
        return False

    def writable(self) -> bool:  # type: ignore[override]
        return True


# Добавляем корень проекта в PYTHONPATH до локальных импортов
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.extractor_factory import ExtractorFactory
from src.core.ocr_manager import get_ocr_manager
from src.email_loader import ProcessedEmailLoader
from src.reporting import ReportGenerator
from src.utils.logger import log_pipeline_event, log_system_event, log_error_event
from src.postprocessing.resilient_processor import ResilientEmailProcessor
from src.utils.portable_paths import get_portable_paths

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
        self.mode = args.mode if args.mode != "interactive" else None
        self.date = args.date
        self.count = args.count
        self.start_date = args.start_date
        self.end_date = args.end_date
        self.dry_run = args.dry_run

        # 🔧 ПОРТИРУЕМЫЕ ПУТИ: Используем централизованную систему путей
        self.portable_paths = get_portable_paths()
        self.project_root = self.portable_paths.get_project_root()
        self.data_dir = self.portable_paths.get_data_dir()
        self.emails_dir = self.portable_paths.get_emails_dir()
        self.llm_results_dir = self.portable_paths.get_results_dir()
        self.llm_results_dir.mkdir(parents=True, exist_ok=True)

        self.run_started_at = datetime.now()
        self.run_id = self.run_started_at.strftime("%Y%m%d_%H%M%S")
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._run_log_handle: Optional[io.TextIOWrapper] = None
        self._logging_teardown_done = False
        self._setup_run_logging()

        self.loader = ProcessedEmailLoader()
        self.ocr_manager = get_ocr_manager()
        self.extractor = ExtractorFactory.create_extractor(test_mode=False)
        
        # Создаем устойчивый процессор с автоматическим повтором
        self.resilient_processor = ResilientEmailProcessor(self, max_retries=2)
        
        # Логирование статуса провайдеров
        self._log_provider_status()

        self.run_summaries: List[Dict[str, Any]] = []

        log_system_event(
            "api_validator_initialized",
            mode=self.mode,
            dry_run=self.dry_run,
        )

    def _setup_run_logging(self) -> None:
        """🪵 Настраивает файл лога с дублированием консоли."""
        try:
            log_dir = self.data_dir / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)

            mode_suffix = self.mode or "unknown"
            log_name = f"api_pipeline_validator_{self.run_id}_{mode_suffix}.log"
            self.run_log_path = log_dir / log_name

            handle = self.run_log_path.open("a", encoding="utf-8")
            self._run_log_handle = handle

            sys.stdout = TeeStream(self._original_stdout, handle)
            sys.stderr = TeeStream(self._original_stderr, handle)

            atexit.register(self._teardown_run_logging)
            print(f"🪵 Лог запуска: {self.run_log_path}")
        except Exception as exc:  # pylint: disable=broad-except
            sys.stdout = self._original_stdout
            sys.stderr = self._original_stderr
            self._run_log_handle = None
            print(f"⚠️ Не удалось инициализировать файл лога запуска: {exc}")

    def _teardown_run_logging(self) -> None:
        """🧹 Восстанавливает стандартные потоки вывода."""
        if getattr(self, "_logging_teardown_done", False):
            return

        self._logging_teardown_done = True

        if hasattr(self, "_run_log_handle") and self._run_log_handle:
            try:
                self._run_log_handle.flush()
            except Exception:  # pylint: disable=broad-except
                pass

        try:
            sys.stdout = self._original_stdout
            sys.stderr = self._original_stderr
        finally:
            if hasattr(self, "_run_log_handle") and self._run_log_handle:
                try:
                    self._run_log_handle.close()
                except Exception:  # pylint: disable=broad-except
                    pass
    def _log_provider_status(self) -> None:
        """📊 Логирует статус всех LLM провайдеров"""
        try:
            provider_manager = self.extractor.config.provider_manager
            providers = provider_manager.get_llm_providers()
            
            print(f"\n🤖 СТАТУС LLM ПРОВАЙДЕРОВ:")
            print("=" * 40)
            
            for i, provider in enumerate(providers, 1):
                # Проверяем доступность провайдера через объект провайдера
                is_available = True
                if hasattr(provider_manager, 'providers') and provider.name in provider_manager.providers:
                    provider_obj = provider_manager.providers[provider.name]
                    if hasattr(provider_obj, 'is_available'):
                        is_available = provider_obj.is_available()
                
                status_icon = "✅" if is_available else "❌"
                
                print(f"{status_icon} {i}. {provider.name} ({provider.model})")
                
                if hasattr(provider_manager, 'providers') and provider.name in provider_manager.providers:
                    provider_obj = provider_manager.providers[provider.name]
                    if hasattr(provider_obj, 'get_stats'):
                        stats = provider_obj.get_stats()
                        success_rate = stats.get('success_rate', 0)
                        circuit_break = stats.get('in_circuit_break', False)
                        failure_count = stats.get('failure_count', 0)
                        
                        print(f"   📊 Успешность: {success_rate:.1%}")
                        print(f"   🔄 Circuit Break: {'Да' if circuit_break else 'Нет'}")
                        if failure_count > 0:
                            print(f"   ❌ Ошибки подряд: {failure_count}")
                
                if not is_available:
                    print(f"   ⚠️ Провайдер недоступен")
            
            # Подсчитываем доступные провайдеры
            available_count = 0
            for provider in providers:
                if hasattr(provider_manager, 'providers') and provider.name in provider_manager.providers:
                    provider_obj = provider_manager.providers[provider.name]
                    if hasattr(provider_obj, 'is_available') and provider_obj.is_available():
                        available_count += 1
            print(f"\n📈 Доступно провайдеров: {available_count}/{len(providers)}")
            
        except Exception as e:
            print(f"⚠️ Ошибка получения статуса провайдеров: {e}")

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
        """🧪 Обрабатывает тестовую выборку из 10 писем с поддержкой параметров count и start."""
        self.process_test_dataset(self.count, self.start_date)

    def _run_batch_mode(self) -> None:
        """📦 Обрабатывает первые N писем за указанную дату."""
        if not self.date:
            raise ValueError("Для режима batch требуется параметр --date")
        self.process_date(self.date, self.count)

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
        """📅 Обрабатывает все письма за конкретную дату с устойчивым процессором."""
        if not email_paths:
            print(f"⚠️  Нет писем для обработки за {date}")
            return

        print(f"\n🎯 Запуск устойчивой обработки за {date} — найдено {len(email_paths)} писем")
        report_generator = ReportGenerator(base_dir=self.llm_results_dir, date=date)
        stats = PipelineStats()
        processed_sources: set[str] = set()

        def handle_result(result: Dict[str, Any]) -> None:
            """📡 Регистрирует артефакты сразу после обработки письма."""
            try:
                self._register_result_artifacts(
                    date=date,
                    result=result,
                    report_generator=report_generator,
                    stats=stats,
                    processed_sources=processed_sources,
                )
            except Exception as callback_exc:  # pylint: disable=broad-except
                print(f"⚠️ Ошибка постобработки результата {result.get('source_file')}: {callback_exc}")

        # Подготавливаем список файлов для устойчивого процессора
        email_files = []
        for path in email_paths:
            if not path.exists():
                stats.register_failure(path.name, "Файл отсутствует", 0.0)
                continue
            email_files.append(str(path))

        if not email_files:
            print(f"⚠️  Нет доступных файлов для обработки за {date}")
            return

        # Используем устойчивый процессор с автоматическим повтором
        print(f"🔄 Запуск ResilientEmailProcessor для {len(email_files)} писем")
        resilient_result = self.resilient_processor.process_emails_with_retry(
            email_files,
            result_callback=handle_result,
        )
        
        # Объединяем результаты по письмам, чтобы не плодить артефакты при повторах
        consolidated_results: Dict[str, Dict[str, Any]] = {}
        for result in resilient_result.get('results', []):
            if not isinstance(result, dict):
                continue
            source_file = result.get('source_file')
            if not source_file:
                continue
            consolidated_results[source_file] = result

        for source_file, result in consolidated_results.items():
            try:
                self._register_result_artifacts(
                    date=date,
                    result=result,
                    report_generator=report_generator,
                    stats=stats,
                    processed_sources=processed_sources,
                )
            except Exception as e:
                print(f"⚠️ Ошибка при регистрации результата для {Path(source_file).name}: {e}")

        # Логируем статистику устойчивого процессора
        resilient_stats = resilient_result.get('statistics', {})
        print(f"\n📊 Статистика устойчивой обработки:")
        print(f"   📧 Всего писем: {resilient_stats.get('total_emails', 0)}")
        print(f"   ✅ Успешно: {resilient_stats.get('successful_emails', 0)}")
        print(f"   🎯 Успешно с первой попытки: {resilient_stats.get('successful_first_attempt', 0)}")
        print(f"   🔄 Успешно после повтора: {resilient_stats.get('successful_after_retry', 0)}")
        print(f"   🚫 Окончательно не удалось: {resilient_stats.get('permanently_failed', 0)}")
        
        strategies_used = resilient_stats.get('strategies_used', {})
        if strategies_used:
            print(f"   🔧 Использованные стратегии:")
            for strategy, count in strategies_used.items():
                if count > 0:
                    print(f"      • {strategy}: {count} писем")

        summary_payload = report_generator.finalize(stats.as_dict())
        
        # Добавляем статистику устойчивого процессора в summary
        summary_payload['resilient_processing'] = resilient_stats
        
        self._update_memory_bank_index(report_generator.summary_path, summary_payload)
        self.run_summaries.append(summary_payload)
        print(f"✅ Устойчивая обработка за {date} завершена (успешно: {stats.emails_successful}, ошибки: {stats.emails_failed})")

    def _register_result_artifacts(
        self,
        date: str,
        result: Dict[str, Any],
        report_generator: ReportGenerator,
        stats: PipelineStats,
        processed_sources: set[str],
    ) -> None:
        """📦 Создаёт артефакты и обновляет статистику по письму."""
        source_file = result.get('source_file')
        if not source_file:
            print("⚠️ Результат без указания исходного файла, пропуск")
            return
        if source_file in processed_sources:
            return

        email_path = Path(source_file)
        if not email_path.exists():
            potential_path = self.project_root / source_file
            if potential_path.exists():
                email_path = potential_path
            else:
                resolved = self._resolve_email_path(date, Path(source_file).name)
                if resolved:
                    email_path = resolved

        if not email_path.exists():
            print(f"⚠️ Не удалось найти файл письма для артефактов: {source_file}")
            return

        with email_path.open("r", encoding="utf-8") as handle:
            email_data = json.load(handle)
        metadata = self._build_email_metadata(email_data, email_path)

        processed_copy = copy.deepcopy(result)
        raw_payload = processed_copy.pop("raw_llm_result", {})
        if raw_payload is None:
            raw_payload = {}
        elif isinstance(raw_payload, list):
            raw_payload = {"responses": raw_payload}
        elif not isinstance(raw_payload, dict):
            raw_payload = {"value": raw_payload}

        processing_time_raw = (
            processed_copy.get("processing_time_seconds")
            or result.get("processing_time")
            or 0.0
        )
        try:
            processing_time = float(processing_time_raw)
        except (TypeError, ValueError):
            processing_time = 0.0

        processed_copy.setdefault("processing_strategy", result.get("processing_strategy", "standard"))
        processed_copy["success"] = bool(processed_copy.get("success", False))
        processed_copy.setdefault("source_file", source_file)

        for section in ("organizations", "contacts", "commercial_offers", "interactions"):
            value = processed_copy.get(section)
            if value is None:
                processed_copy[section] = []

        errors = self._collect_result_errors(result)
        processing_time_value = round(processing_time, 3)
        entry = report_generator.register_email_result(
            filename=email_path.name,
            email_metadata=metadata,
            llm_raw=raw_payload,
            processed=processed_copy,
            processing_time_seconds=processing_time_value,
            errors=errors,
        )
        stats.register_email(entry)
        processed_sources.add(source_file)

    def _collect_result_errors(self, result: Dict[str, Any]) -> List[str]:
        """🧹 Сводит ошибки результата в уникальный список."""
        errors: List[str] = []
        raw_errors = result.get("errors")
        if isinstance(raw_errors, list):
            errors.extend(str(err) for err in raw_errors if err)
        elif isinstance(raw_errors, str):
            errors.append(raw_errors)

        for key in ("error", "fallback_reason", "original_error"):
            value = result.get(key)
            if value:
                errors.append(str(value))

        unique_errors: List[str] = []
        seen: set[str] = set()
        for err in errors:
            normalized = err.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_errors.append(normalized)
        return unique_errors

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
            
            # Дополнительная информация о письме
            print(f"   📧 От: {metadata.get('from', 'Неизвестно')}")
            print(f"   📝 Тема: {metadata.get('subject', 'Без темы')[:60]}...")
            print(f"   📎 Вложений: {metadata.get('attachments_count', 0)}")
            print(f"   📏 Размер текста: {len(combined_text)} символов")

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

            # Извлекаем информацию о провайдере для логирования
            provider_used = processed_result.get("provider_used", "Unknown")
            response_time = processed_result.get("processing_time", 0)
            
            print(f"🤖 Использован провайдер: {provider_used}")
            print(f"⏱️ Время ответа LLM: {response_time:.2f}с")
            print(f"📊 Общее время обработки: {duration:.2f}с")

            raw_llm = processed_result.get("raw_llm_result", {})
            processed_copy = copy.deepcopy(processed_result)
            raw_payload = processed_copy.pop("raw_llm_result", raw_llm if isinstance(raw_llm, dict) else {})

            success = self._determine_success(processed_copy)
            processed_copy["success"] = success
            errors = self._collect_errors(processed_copy)
            
            # Детальное логирование результатов
            contacts_count = len(processed_copy.get('contacts', []))
            organizations_count = len(processed_copy.get('organizations', []))
            commercial_offers_count = len(processed_copy.get('commercial_offers', []))
            
            print(f"📊 Результаты извлечения:")
            print(f"   👥 Контакты: {contacts_count}")
            print(f"   🏢 Организации: {organizations_count}")
            print(f"   💼 Коммерческие предложения: {commercial_offers_count}")
            print(f"   {'✅ Успешно' if success else '❌ Ошибки'}: {len(errors)} ошибок")

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
            error_type = type(exc).__name__
            
            # Детальное логирование ошибки
            print(f"❌ Ошибка обработки {email_path.name}")
            print(f"   🔍 Тип ошибки: {error_type}")
            print(f"   📝 Сообщение: {error_message}")
            print(f"   ⏱️ Время до ошибки: {elapsed:.2f}с")
            
            # Дополнительная диагностика для специфических ошибок
            if "OpenRouter" in error_message:
                print(f"   🤖 Проблема с OpenRouter провайдером")
            elif "Replicate" in error_message:
                print(f"   🤖 Проблема с Replicate провайдером")
            elif "Circuit" in error_message or "недоступен" in error_message:
                print(f"   🔄 Возможная проблема с Circuit Breaker")
            elif "JSON" in error_message or "валидация" in error_message:
                print(f"   📋 Проблема с валидацией JSON ответа")
            
            # Логирование стека ошибки для отладки
            import traceback
            print(f"   📚 Стек ошибки:")
            for line in traceback.format_exc().split('\n')[-5:]:
                if line.strip():
                    print(f"      {line}")
            
            stats.register_failure(email_path.name, error_message, elapsed)
            log_error_event(
                error_type="api_validator_email_failed",
                error_message=f"{error_type}: {error_message}",
                filename=email_path.name,
                date=date,
            )

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

        # ИСПРАВЛЕНО: ищем правильное поле для пути к файлу
        file_path = attachment.get("path") or attachment.get("file_path") or attachment.get("relative_path")
        if not file_path:
            print(f"⚠️ У вложения '{attachment.get('filename', 'unknown')}' отсутствует путь к файлу")
            return None

        # 🔧 ПОРТИРУЕМЫЕ ПУТИ: Используем нормализацию путей вложений
        attachment_path = self.portable_paths.normalize_attachment_path(attachment)
        if not attachment_path:
            print(f"⚠️ У вложения '{attachment.get('filename', 'unknown')}' отсутствует путь к файлу")
            return None
        
        if not attachment_path.exists():
            # Пробуем восстановить путь через ProcessedEmailLoader
            recovered_path = self.loader.get_attachment_file_path(email, attachment)
            attachment_path = recovered_path if recovered_path else attachment_path

        print(f"📎 Попытка извлечения текста из вложения: {attachment.get('filename', 'unknown')}")
        print(f"   Путь к файлу: {attachment_path}")
        print(f"   Файл существует: {attachment_path.exists()}")
        
        if attachment_path.exists() and self.ocr_manager:
            try:
                print(f"   🔍 Запуск OCR для файла: {attachment_path.name}")
                ocr_result = self.ocr_manager.extract_text_from_file(str(attachment_path), date)
                if ocr_result.get("success") and ocr_result.get("text"):
                    extracted_text = ocr_result["text"]
                    print(f"   ✅ OCR успешно: извлечено {len(extracted_text)} символов")
                    # Показываем превью извлеченного текста
                    preview = extracted_text[:200].replace('\n', ' ')
                    print(f"   📄 Превью: {preview}...")
                    return extracted_text
                else:
                    print(f"   ❌ OCR не удалось: {ocr_result}")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"⚠️  OCR не удалось для {attachment_path.name}: {exc}")
        else:
            if not attachment_path.exists():
                print(f"   ❌ Файл не найден: {attachment_path}")
            if not self.ocr_manager:
                print(f"   ❌ OCR manager не инициализирован")
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
            "attachments": email_data.get("attachments", []),  # ИСПРАВЛЕНО: передаем список вложений, а не число
            "attachments_count": metadata.get("attachments_count"),
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
        if processed.get("validation_error"):
            return False
        if processed.get("processing_strategy") == "fallback":
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
        """🗂️ Добавляет ссылку на сводку в memory-bank/reports/index.md с портируемыми путями."""
        try:
            # 🔧 ПОРТИРУЕМЫЕ ПУТИ: Используем относительные пути для переносимости
            reports_dir = self.portable_paths.to_absolute("memory-bank/reports")
            index_path = reports_dir / "index.md"
            
            # Создаем относительный путь от корня проекта
            relative_path = self.portable_paths.to_relative(summary_path)
            
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
    
    def process_test_dataset(self, count: Optional[int] = None, start_filename: Optional[str] = None) -> None:
        """🧪 Обрабатывает тестовую выборку из датасета с опциями."""
        filenames = self._load_test_dataset()
        
        if start_filename:
            try:
                start_index = filenames.index(start_filename)
                filenames = filenames[start_index:]
                print(f"🎯 Начинаем с файла: {start_filename} (индекс {start_index})")
            except ValueError:
                print(f"⚠️ Файл {start_filename} не найден в тестовом датасете, обрабатываем все")
        
        if count is not None:
            filenames = filenames[:count]
            print(f"🎯 Ограничиваем обработку до {count} писем")
        
        print(f"📧 К обработке: {len(filenames)} писем")
        
        grouped = self._group_filenames_by_date(filenames)
    
        for date, date_filenames in grouped.items():
            email_paths = [self._resolve_email_path(date, name) for name in date_filenames]
            self._process_date(date, [path for path in email_paths if path is not None])
    
    
    def process_date(self, date: str, count: Optional[int] = None, exclude_test: bool = False) -> None:
        """📦 Обрабатывает письма за конкретную дату с опциями count и exclude_test."""
        date_dir = self.emails_dir / date
        if not date_dir.exists():
            raise FileNotFoundError(f"Директория с письмами за {date} не найдена: {date_dir}")
        
        all_paths = sorted(date_dir.glob("email_*.json"))
        
        if exclude_test:
            test_filenames = set(self._load_test_dataset())
            all_paths = [p for p in all_paths if p.name not in test_filenames]
            print(f"📧 После исключения тестовых файлов: {len(all_paths)} писем")
        
        if count is not None:
            all_paths = all_paths[:count]
        
        self._process_date(date, all_paths)

    def process_specific_emails(self, date: str, email_files: List[str]) -> None:
        """📧 Обрабатывает конкретные письма за указанную дату по именам файлов."""
        date_dir = self.emails_dir / date
        if not date_dir.exists():
            raise FileNotFoundError(f"Директория с письмами за {date} не найдена: {date_dir}")
        
        email_paths = []
        for filename in email_files:
            email_path = date_dir / filename
            if email_path.exists():
                email_paths.append(email_path)
            else:
                print(f"⚠️ Файл не найден: {filename}")
        
        if not email_paths:
            print(f"❌ Не найдено ни одного файла для обработки")
            return
        
        print(f"📧 К обработке: {len(email_paths)} из {len(email_files)} запрошенных файлов")
        self._process_date(date, email_paths)
    
    
    def process_single_email(self, email_file: str, simplified: bool = False) -> Dict[str, Any]:
        """
        🤖 Обработка одного письма для ResilientEmailProcessor
        
        Args:
            email_file: Путь к файлу письма
            simplified: Флаг упрощенной обработки
            
        Returns:
            Dict с результатом обработки
        """
        try:
            # Определяем путь к файлу
            email_path = Path(email_file)
            if not email_path.exists():
                # Пытаемся найти файл в стандартных директориях
                possible_paths = [
                    EMAILS_DIR / "2025-07-29" / email_path.name,
                    EMAILS_DIR / email_path.name,
                ]
                
                for path in possible_paths:
                    if path.exists():
                        email_path = path
                        break
                    
                if not email_path.exists():
                    return {
                        'success': False,
                        'error': f'Файл не найден: {email_file}',
                        'source_file': email_file
                    }
            
            # Читаем данные письма
            with email_path.open("r", encoding="utf-8") as handle:
                email_data = json.load(handle)
            
            # Определяем дату из имени файла
            date = self._extract_date_from_filename(email_path.name)
            
            # Подготавливаем данные для обработки
            metadata = self._build_email_metadata(email_data, email_path)
            combined_text = self._compose_combined_text(email_data, date)
            llm_metadata = self._build_llm_metadata(email_data, metadata, combined_text)
            
            # Обрабатываем через экстрактор
            if simplified:
                # Упрощенная обработка - используем более простые параметры
                llm_metadata['simplified'] = True
                
            processed_result = self.extractor.extract_all_data(combined_text, llm_metadata)
            
            # Определяем успешность
            success = self._determine_success(processed_result)
            processed_result['success'] = success
            processed_result['source_file'] = email_file
            
            return processed_result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'source_file': email_file,
                'validation_error': True
            }
        
    def _extract_date_from_filename(self, filename: str) -> str:
        """Извлечение даты из имени файла"""
        # Пытаемся извлечь дату из имени файла типа email_001_20250729_...
        import re
        match = re.search(r'(\d{8})', filename)
        if match:
            date_str = match.group(1)
            # Преобразуем YYYYMMDD в YYYY-MM-DD
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return "2025-07-29"  # Дата по умолчанию


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """🧭 Разбирает аргументы командной строки."""
    parser = argparse.ArgumentParser(description="API Pipeline Validator")
    parser.add_argument("--mode", choices=["first10", "batch", "range"], default="first10")
    parser.add_argument("--date", help="Дата обработки для режима batch", default=None)
    parser.add_argument("--count", type=int, help="Количество писем (для режимов first10 и batch)", default=10)
    parser.add_argument("--start", dest="start_date", help="Начальная дата для режима range или имя файла для режима first10", default=None)
    parser.add_argument("--end", dest="end_date", help="Конечная дата для режима range", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Не выполнять запись в БД")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    """🏃 Точка входа CLI."""
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) == 0:
        run_interactive_menu()
    else:
        args = parse_args(argv)
        validator = APIPipelineValidator(args)
        validator.run()

def run_interactive_menu() -> None:
    """🖥️ Интерактивное меню для API Pipeline Validator - обновленная версия"""
    from argparse import Namespace
    import sys
    from pathlib import Path
    
    # Добавляем корневую директорию проекта в sys.path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from src.validator_menu import main_menu
    
    dummy_args = Namespace(
        mode="interactive",
        date=None,
        count=None,
        start_date=None,
        end_date=None,
        dry_run=False
    )
    validator = APIPipelineValidator(dummy_args)
    
    # Запускаем новое меню с динамическим выбором дат
    main_menu(validator)


if __name__ == "__main__":
    main()
