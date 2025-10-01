#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""📊 Модуль формирования отчётов для API Pipeline Validator."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import logger as global_logger


class ReportGenerator:
    """📄 Генератор Markdown/JSON отчётов и агрегированных сводок."""

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

        self.summary_path = self.run_dir / f"_summary_{self.run_id}.json"
        self.summary_md_path = self.run_dir / f"_summary_{self.run_id}.md"
        self.index_path = self.run_dir / "index.md"
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

        raw_path = self.run_dir / f"{slug}_{self.run_id}_{timestamp_suffix}_raw.json"
        processed_path = self.run_dir / f"{slug}_{self.run_id}_{timestamp_suffix}_processed.json"
        markdown_path = self.run_dir / f"{slug}_{self.run_id}_{timestamp_suffix}.md"

        self.logger.debug(
            "report_generator_prepare_email",
            message="🔍 Формирование артефактов письма",
            filename=filename,
            slug=slug,
        )

        self._write_json_file(raw_path, {"source_file": filename, "llm_response": llm_raw})
        self._write_json_file(processed_path, {"source_file": filename, "processed_result": processed})

        markdown_content = self._build_markdown_report(
            filename=filename,
            email_metadata=email_metadata,
            processed=processed,
            llm_raw=llm_raw,
            processing_time_seconds=processing_time_seconds,
            errors=errors,
        )
        self._write_text_file(markdown_path, markdown_content)

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
            "raw_json": raw_path.name,
            "processed_json": processed_path.name,
            "markdown": markdown_path.name,
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
        patterns = [
            f"{slug}_{self.run_id}_*_raw.json",
            f"{slug}_{self.run_id}_*_processed.json",
            f"{slug}_{self.run_id}_*.md",
        ]
        for pattern in patterns:
            for path in self.run_dir.glob(pattern):
                try:
                    path.unlink()
                except Exception as cleanup_error:  # pylint: disable=broad-except
                    self.logger.warning(
                        "report_generator_cleanup_failed",
                        message="⚠️ Не удалось удалить старый артефакт",
                        path=str(path),
                        error=str(cleanup_error),
                    )

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
        summary_md = self._build_summary_markdown(summary_payload)
        self._write_text_file(self.summary_md_path, summary_md)
        self._refresh_index(summary_payload)

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

    def _refresh_index(self, summary_payload: Dict[str, Any]) -> None:
        """🗂️ Обновляет индекс Markdown с перечнем отчётов."""
        new_section = [
            f"## Запуск {summary_payload['run_id']} ({summary_payload['completed_at']})",
            "",
            f"- Всего писем: {summary_payload['totals']['emails']}",
            f"- Успешно: {summary_payload['totals']['success']}",
            f"- Ошибки: {summary_payload['totals']['failed']}",
            "",
            "| Файл | Статус | Организации | Контакты | КП | Взаимодействия | Markdown |",
            "|------|--------|-------------|----------|----|----------------|----------|",
        ]
        for entry in summary_payload["entries"]:
            status_icon = "✅" if entry.get("success") else "❌"
            new_section.append(
                "| {filename} | {status} | {orgs} | {contacts} | {offers} | {interactions} | [{md}](./{md}) |".format(
                    filename=entry["filename"],
                    status=status_icon,
                    orgs=entry["organizations"],
                    contacts=entry["contacts"],
                    offers=entry["commercial_offers"],
                    interactions=entry["interactions"],
                    md=entry["markdown"],
                )
            )
        new_section.append("")
        new_section.append(f"🔄 Автообновление: {summary_payload['completed_at']}")
        new_section.append("\n---\n")

        existing_content = ""
        if self.index_path.exists():
            try:
                existing_content = self.index_path.read_text(encoding="utf-8")
            except Exception as read_error:
                self.logger.error(
                    "report_generator_index_read_failed",
                    message="❌ Не удалось прочитать index.md",
                    error=str(read_error),
                    index_path=str(self.index_path),
                )

        new_content = "\n".join(new_section)
        if existing_content:
            new_content = f"{new_content}\n{existing_content.strip()}\n"

        self._write_text_file(self.index_path, new_content)

    def _write_json_file(self, path: Path, payload: Dict[str, Any]) -> None:
        """💾 Сохраняет JSON с системой резервного копирования."""
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
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

    def _write_text_file(self, path: Path, content: str) -> None:
        """📝 Сохраняет Markdown/текст с fallback."""
        try:
            with path.open("w", encoding="utf-8") as handle:
                handle.write(content)
        except Exception as error:
            self.logger.error(
                "report_generator_text_write_failed",
                message="❌ Ошибка записи текста",
                target_path=str(path),
                error=str(error),
            )
            self._write_text_fallback(path.name, content)

    def _write_text_fallback(self, filename: str, content: str) -> None:
        """🛟 Резервная запись текста в fallback-директорию."""
        try:
            self.fallback_dir.mkdir(parents=True, exist_ok=True)
            fallback_path = self.fallback_dir / filename
            with fallback_path.open("w", encoding="utf-8") as handle:
                handle.write(content)
            self.logger.warning(
                "report_generator_text_fallback_saved",
                message="⚠️ Текст сохранён в fallback",
                fallback_path=str(fallback_path),
            )
        except Exception as fallback_error:
            self.logger.critical(
                "report_generator_text_fallback_failed",
                message="🚨 Полный отказ записи текста",
                filename=filename,
                error=str(fallback_error),
            )

    def _build_markdown_report(
        self,
        filename: str,
        email_metadata: Dict[str, Any],
        processed: Dict[str, Any],
        llm_raw: Dict[str, Any],
        processing_time_seconds: Optional[float],
        errors: List[str],
    ) -> str:
        """🧱 Генерирует Markdown-отчёт по одному письму."""
        subject = email_metadata.get("subject") or processed.get("summary", {}).get("topic") or filename
        header = f"# Отчёт по письму — {subject}"

        metadata_lines = [
            "## Метаданные",
            f"- **Файл:** `{filename}`",
            f"- **От:** {email_metadata.get('from', '—')}",
            f"- **Кому:** {email_metadata.get('to', '—')}",
            f"- **Дата:** {email_metadata.get('date', '—')}",
            f"- **Вложения:** {email_metadata.get('attachments_count', 0)}",
            f"- **Размер текста:** {email_metadata.get('char_count', 0)} символов",
            f"- **Время обработки:** {processing_time_seconds or '—'} сек",
        ]

        business_context = processed.get("business_context") or "—"
        summary = processed.get("summary", {})
        key_points = processed.get("key_points", [])

        summary_lines = [
            "## Резюме",
            f"- **Бизнес-контекст:** {business_context}",
            f"- **Тема:** {summary.get('topic', '—')}",
            f"- **Интерес продукта:** {summary.get('product_interest', '—')}",
            f"- **Стадия коммуникации:** {summary.get('communication_stage', '—')}",
            f"- **Тип запроса:** {summary.get('request_type', '—')}",
            "",
            "### Ключевые моменты",
        ]
        if key_points:
            summary_lines.extend([f"- {point}" for point in key_points])
        else:
            summary_lines.append("- —")

        org_lines = self._build_organizations_section(processed.get("organizations", []))
        contact_lines = self._build_contacts_section(processed.get("contacts", []))
        interactions_lines = self._build_interactions_section(processed.get("interactions", []))
        offers_lines = self._build_offers_section(processed.get("commercial_offers", []))

        diagnostics = [
            "## Диагностика",
            f"- **Статус:** {'✅ Успех' if processed.get('success', True) else '❌ Ошибка'}",
        ]
        if errors:
            diagnostics.append("- **Ошибки:**")
            diagnostics.extend([f"  - {err}" for err in errors])
        
        original_error = processed.get('original_error')
        if original_error:
            diagnostics.append(f"- **Исходная ошибка (fallback):** {original_error}")
        
        provider = llm_raw.get("provider") or llm_raw.get("provider_used") or processed.get("provider_used")
        if provider:
            diagnostics.append(f"- **Провайдер:** {provider}")

        return "\n\n".join(
            [
                header,
                "\n".join(metadata_lines),
                "\n".join(summary_lines),
                "\n".join(org_lines),
                "\n".join(contact_lines),
                "\n".join(interactions_lines),
                "\n".join(offers_lines),
                "\n".join(diagnostics),
            ]
        )

    def _build_organizations_section(self, organizations: List[Dict[str, Any]]) -> List[str]:
        """🏢 Формирует Markdown-блок для организаций."""
        lines = ["## Организации"]
        if not organizations:
            lines.append("- —")
            return lines
        lines.append("| ID | Название | ИНН | Город | Адрес | Сайт | Emails | Телефоны |")
        lines.append("|----|----------|-----|-------|-------|------|--------|----------|")
        for org in organizations:
            phone_values: List[str] = []
            for phone in org.get("phones", []):
                if isinstance(phone, dict):
                    number = phone.get("number") or phone.get("formatted") or phone.get("original") or "—"
                    phone_type = phone.get("type") or "main"
                    phone_values.append(f"{phone_type}: {number}")
                else:
                    phone_values.append(str(phone))
            phones_display = ", ".join(phone_values) if phone_values else "—"
            lines.append(
                "| {oid} | {name} | {inn} | {city} | {address} | {website} | {emails} | {phones} |".format(
                    oid=org.get("organization_id", "—"),
                    name=org.get("name", "—"),
                    inn=org.get("inn", "—"),
                    city=org.get("city", "—"),
                    address=org.get("address", "—"),
                    website=org.get("website", "—"),
                    emails=", ".join(org.get("emails", [])) if org.get("emails") else "—",
                    phones=phones_display,
                )
            )
        return lines

    def _build_contacts_section(self, contacts: List[Dict[str, Any]]) -> List[str]:
        """👥 Формирует Markdown-блок для контактов."""
        lines = ["## Контакты"]
        if not contacts:
            lines.append("- —")
            return lines
        lines.append(
            "| ID | Имя | Org ID | Должность | Email | Телефоны | Роль | Город | ⚖️ |"
        )
        lines.append("|----|-----|--------|----------|-------|----------|------|-------|----|")
        for contact in contacts:
            phone_values = []
            for phone in contact.get("phones", []):
                if isinstance(phone, dict):
                    number = phone.get("number", "—")
                    phone_values.append(f"{phone.get('type', '—')}: {number}")
                else:
                    phone_values.append(str(phone))
            phone_display = ", ".join(phone_values) if phone_values else "—"
            lines.append(
                "| {cid} | {name} | {org_id} | {position} | {email} | {phones} | {role} | {city} | {confidence} |".format(
                    cid=contact.get("contact_id", "—"),
                    name=contact.get("name", "—"),
                    org_id=contact.get("organization_id", "—"),
                    position=contact.get("position", "—"),
                    email=contact.get("email", "—"),
                    phones=phone_display,
                    role=contact.get("role_in_message", "—"),
                    city=contact.get("city", "—"),
                    confidence=self._format_confidence(contact.get("confidence")),
                )
            )
        return lines

    def _build_interactions_section(self, interactions: List[Dict[str, Any]]) -> List[str]:
        """🔄 Формирует Markdown-блок для взаимодействий."""
        lines = ["## Взаимодействия"]
        if not interactions:
            lines.append("- —")
            return lines
        lines.append(
            "| Local ID | Contact ID | Org ID | Тип | Роль | Дата | Confidence |"
        )
        lines.append("|----------|-----------|-------|-----|------|------|------------|")
        for interaction in interactions:
            lines.append(
                "| {lid} | {cid} | {oid} | {itype} | {role} | {date} | {confidence} |".format(
                    lid=interaction.get("interaction_local_id", "—"),
                    cid=interaction.get("contact_id", "—"),
                    oid=interaction.get("organization_id", "—"),
                    itype=interaction.get("interaction_type", "—"),
                    role=interaction.get("role_in_message", "—"),
                    date=interaction.get("message_date", "—"),
                    confidence=self._format_confidence(interaction.get("confidence")),
                )
            )
        return lines

    def _build_offers_section(self, offers: List[Dict[str, Any]]) -> List[str]:
        """💼 Формирует Markdown-блок для коммерческих предложений."""
        lines = ["## Коммерческие предложения"]
        if not offers:
            lines.append("- —")
            return lines
        for index, offer in enumerate(offers, start=1):
            status_icon = "✅" if offer.get("found") else "❌"
            lines.append(f"### КП #{index} {status_icon}")
            lines.append(f"- **Тип:** {offer.get('offer_type', '—')}")
            lines.append(f"- **Номер:** {offer.get('offer_number', '—')}")
            lines.append(f"- **Дата:** {offer.get('offer_date', '—')}")
            lines.append(f"- **Конечный заказчик:** {offer.get('end_user', '—')}")
            lines.append(f"- **ИНН заказчика:** {offer.get('end_user_inn', '—')}")
            lines.append(f"- **Посредник:** {offer.get('intermediary', '—')}")
            lines.append(f"- **Контакт посредника:** {offer.get('intermediary_date', '—')}")
            lines.append(f"- **Условия оплаты:** {offer.get('payment_terms', '—')}")
            lines.append(f"- **Срок поставки:** {offer.get('delivery_time', '—')}")
            lines.append(f"- **Условия доставки:** {offer.get('delivery_terms', '—')}")
            lines.append(f"- **Срок действия:** {offer.get('valid_until', '—')}")
            lines.append(f"- **Итого:** {offer.get('total_cost', '—')}")
            if offer.get("comments"):
                lines.append(f"- **Комментарии:** {offer['comments']}")
            equipment = offer.get("equipment_items", [])
            if equipment:
                lines.append("\n| # | Наименование | Модель | Артикул | Кол-во | Цена | Итого | НДС |")
                lines.append("|---|-------------|-------|--------|--------|------|------|-----|")
                for idx, item in enumerate(equipment, start=1):
                    lines.append(
                        "| {idx} | {name} | {model} | {article} | {quantity} | {unit_price} | {total_price} | {vat} |".format(
                            idx=idx,
                            name=item.get("name", "—"),
                            model=item.get("model", "—"),
                            article=item.get("article", "—"),
                            quantity=item.get("quantity", "—"),
                            unit_price=item.get("unit_price", "—"),
                            total_price=item.get("total_price", "—"),
                            vat=item.get("vat", "—"),
                        )
                    )
            lines.append("")
        return lines

    def _build_summary_markdown(self, summary_payload: Dict[str, Any]) -> str:
        """📚 Формирует Markdown для сводного отчёта запуска."""
        header = f"# Сводка запуска {summary_payload['run_id']} ({summary_payload['date']})"
        totals = summary_payload["totals"]
        lines = [
            header,
            "",
            f"- Запущен: {summary_payload['started_at']}",
            f"- Завершён: {summary_payload['completed_at']}",
            f"- Временная зона: {summary_payload['timezone']}",
            "",
            "## Итоги",
            f"- Писем обработано: {totals['emails']}",
            f"- Успешно: {totals['success']}",
            f"- Ошибки: {totals['failed']}",
            f"- Всего организаций: {totals['organizations']}",
            f"- Всего контактов: {totals['contacts']}",
            f"- Найдено КП: {totals['commercial_offers']}",
            f"- Зафиксировано взаимодействий: {totals['interactions']}",
            "",
            "## Письма",
            "| Файл | Статус | Markdown |",
            "|------|--------|----------|",
        ]
        for entry in summary_payload["entries"]:
            status_icon = "✅" if entry.get("success") else "❌"
            strategy_info = ""
            if entry.get("processing_strategy", "standard") != "standard":
                strategy_info = f" ({entry.get('processing_strategy', 'unknown')})"
            lines.append(
                f"| {entry['filename']} | {status_icon}{strategy_info} | [{entry['markdown']}](./{entry['markdown']}) |"
            )
        
        # Добавляем секцию о проблемных письмах
        problematic_emails = [entry for entry in summary_payload["entries"] if entry.get("was_retried", False)]
        if problematic_emails:
            lines.extend([
                "",
                "## 🔄 Проблемные письма (потребовали повторной обработки)",
                ""
            ])
            
            for entry in problematic_emails:
                strategy = entry.get("processing_strategy", "unknown")
                fallback_reason = entry.get("fallback_reason", "Неизвестная причина")
                errors = entry.get("errors", [])
                
                lines.append(f"### {entry['filename']}")
                lines.append(f"- **Стратегия обработки**: {strategy}")
                
                if strategy == "fallback":
                    lines.append(f"- **Причина fallback**: {fallback_reason}")
                
                if errors:
                    lines.append("- **Исходные ошибки**:")
                    for error in errors:
                        lines.append(f"  - {error}")
                
                lines.append(f"- **Результат**: {entry.get('organizations', 0)} орг., {entry.get('contacts', 0)} контактов")
                lines.append("")
        
        lines.append("")
        if summary_payload.get("run_stats"):
            lines.append("## Дополнительная статистика")
            for key, value in summary_payload["run_stats"].items():
                lines.append(f"- **{key}**: {value}")
        lines.append("\n---\n")
        lines.append(f"Автоматически сгенерировано {summary_payload['completed_at']}")
        return "\n".join(lines)

    def _build_slug(self, filename: str) -> str:
        """🔤 Формирует безопасный slug из имени файла."""
        stem = Path(filename).stem
        safe = [ch if ch.isalnum() else "_" for ch in stem]
        return "".join(safe).strip("_") or "email"

    def _format_confidence(self, value: Optional[Any]) -> str:
        """🎯 Преобразует confidence в строку."""
        if value is None:
            return "—"
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)
