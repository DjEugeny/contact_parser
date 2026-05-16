#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Проверка, что organizations.emails не содержат персональных адресов.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from src.postprocessing.email_classifier import MailboxType, classify_mailbox

PERSONAL_TYPES = {MailboxType.PERSONAL_INTERNAL, MailboxType.PERSONAL_EXTERNAL}


def load_org_profile(profile_path: Path) -> Tuple[set[str], Dict[str, Any]]:
    """📚 Загружает конфигурацию доменов и префиксов."""
    with open(profile_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    corp_domains = {d.lower() for d in data.get("internal_domains", [])}
    return corp_domains, data


def find_latest_processed_file(input_dir: Path, email_id: int) -> Path:
    """🗂️ Находит последний processed JSON по email_id."""
    pattern = f"email_{email_id:03d}_*_processed.json"
    candidates = sorted(input_dir.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"Не найден processed JSON для email_{email_id:03d}")
    return candidates[-1]


def normalize_emails(value: Any) -> List[str]:
    """📨 Гарантирует список email адресов."""
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    if isinstance(value, str):
        return [value]
    return []


def analyze_email_file(
    file_path: Path,
    corp_domains: set[str],
    classifier_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """🧪 Анализирует один processed JSON на предмет персональных email."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    organizations = data.get("organizations", []) or []
    org_reports: List[Dict[str, Any]] = []
    personal_hits: List[Dict[str, Any]] = []
    total_emails = 0

    for idx, org in enumerate(organizations):
        if not isinstance(org, dict):
            continue
        org_name = org.get("name")
        email_entries: List[Dict[str, Any]] = []
        for address in normalize_emails(org.get("emails")):
            total_emails += 1
            mailbox_type = classify_mailbox(address, org_name, corp_domains, classifier_cfg)
            entry = {
                "address": address,
                "mailbox_type": mailbox_type.value,
                "is_personal": mailbox_type in PERSONAL_TYPES,
            }
            email_entries.append(entry)
            if entry["is_personal"]:
                personal_hits.append({
                    "organization_index": idx,
                    "organization_name": org_name,
                    "address": address,
                    "mailbox_type": mailbox_type.value,
                })
        org_reports.append({
            "index": idx,
            "name": org_name,
            "emails": email_entries,
        })

    return {
        "file": str(file_path),
        "organizations": org_reports,
        "personal_hits": personal_hits,
        "total_org_emails": total_emails,
    }


def run_validation(args: argparse.Namespace) -> Dict[str, Any]:
    """🚀 Запускает проверку для указанного набора писем."""
    corp_domains, classifier_cfg = load_org_profile(args.org_profile)
    summary: Dict[str, Any] = {
        "checked_emails": [],
        "total_org_emails": 0,
        "personal_hits": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "input_dir": str(args.input_dir),
    }

    for email_id in args.emails:
        try:
            file_path = find_latest_processed_file(args.input_dir, email_id)
        except FileNotFoundError as exc:
            print(f"❌ {exc}")
            continue

        report = analyze_email_file(file_path, corp_domains, classifier_cfg)
        summary["checked_emails"].append({
            "email_id": f"{email_id:03d}",
            "file": report["file"],
            "total_org_emails": report["total_org_emails"],
            "personal_hits": len(report["personal_hits"]),
        })
        summary["total_org_emails"] += report["total_org_emails"]
        summary["personal_hits"].extend(
            {
                "email_id": f"{email_id:03d}",
                **hit,
            }
            for hit in report["personal_hits"]
        )

        if report["personal_hits"]:
            print(f"❌ email_{email_id:03d}: обнаружены персональные адреса")
        else:
            print(f"✅ email_{email_id:03d}: персональные адреса не найдены")

    summary["status"] = "pass" if not summary["personal_hits"] else "fail"
    return summary


def save_report(summary: Dict[str, Any], output_path: Path) -> None:
    """💾 Сохраняет JSON отчёт."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"💾 Отчёт сохранён: {output_path}")


def parse_args() -> argparse.Namespace:
    """🧭 Парсинг CLI аргументов."""
    parser = argparse.ArgumentParser(description="Валидация фильтра персональных email в organizations")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/llm_results/2025-07-29"),
        help="Директория с processed JSON",
    )
    parser.add_argument(
        "--emails",
        type=int,
        nargs="+",
        required=True,
        help="Номера писем для проверки (например: 24 25 26)",
    )
    parser.add_argument(
        "--org-profile",
        type=Path,
        default=Path("config/org_profile.yml"),
        help="Файл с настройками классификатора email",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path(f"data/reports/org_email_filter_validation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"),
        help="Путь для сохранения отчёта",
    )
    return parser.parse_args()


def main() -> int:
    """🎯 Точка входа."""
    args = parse_args()
    summary = run_validation(args)
    save_report(summary, args.output_json)

    if summary["status"] == "pass":
        print("🎉 Все проверки пройдены, персональных email не найдено.")
        return 0

    print("⚠️ Обнаружены персональные адреса:")
    for hit in summary["personal_hits"]:
        print(
            f"   email_{hit['email_id']} | org #{hit['organization_index']} ({hit['organization_name']}): "
            f"{hit['address']} [{hit['mailbox_type']}]"
        )
    return 2


if __name__ == "__main__":
    sys.exit(main())
