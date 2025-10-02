#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔄 Скрипт для перезапуска обработки проблемных писем

Использование:
    python scripts/reprocess_problematic_emails.py --date 2025-07-29 --emails email_024 email_025 email_026
    python scripts/reprocess_problematic_emails.py --date 2025-07-29 --all-dna-tech
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api_pipeline_validator import APIPipelineValidator
from argparse import Namespace


def find_dna_tech_emails(date: str, emails_dir: Path) -> List[str]:
    """
    🔍 Находит все письма с персональными адресами ДНК-Технология в organizations.emails
    
    Args:
        date: Дата для поиска
        emails_dir: Директория с результатами
        
    Returns:
        Список имён файлов с проблемой
    """
    results_dir = PROJECT_ROOT / "data" / "llm_results" / date
    if not results_dir.exists():
        print(f"❌ Директория с результатами не найдена: {results_dir}")
        return []
    
    problematic_files: List[str] = []
    personal_patterns = [
        "m.gogoleva@dna-technology.ru",
        "prisyazhnyuk@dna-technology.ru",
        "s.voronova@dna-technology.ru",
        "o.isaev@dna-technology.ru",
        "savicheva@dna-technology.ru",
        "kalashnikov@dna-technology.ru",
        "kozlova@dna-technology.ru",
        "bilalov@dna-technology.ru",
        "tishkova@dna-technology.ru",
        "litvinenko@dna-technology.ru",
        "korneeva@dna-technology.ru",
    ]
    
    for processed_file in results_dir.glob("email_*_processed.json"):
        try:
            with processed_file.open('r', encoding='utf-8') as f:
                data = json.load(f)
            
            processed_result = data.get('processed_result', {})
            organizations = processed_result.get('organizations', [])
            
            has_personal = False
            for org in organizations:
                org_name = org.get('name', '')
                if 'ДНК-Технология' not in org_name and 'DNA' not in org_name:
                    continue
                    
                org_emails = org.get('emails', [])
                for email in org_emails:
                    if any(pattern in email for pattern in personal_patterns):
                        has_personal = True
                        print(f"🔍 Найден проблемный файл: {processed_file.name}")
                        print(f"   📧 Персональный email в org: {email}")
                        break
                
                if has_personal:
                    break
            
            if has_personal:
                # Извлекаем базовое имя исходного файла
                base_name = processed_file.name.replace('_processed.json', '.json')
                problematic_files.append(base_name)
                
        except Exception as e:
            print(f"⚠️ Ошибка чтения {processed_file.name}: {e}")
    
    return problematic_files


def reprocess_emails(date: str, email_names: List[str], dry_run: bool = False) -> None:
    """
    🔄 Перезапускает обработку указанных писем
    
    Args:
        date: Дата писем
        email_names: Список базовых имён файлов (без пути)
        dry_run: Режим тестирования без записи в БД
    """
    emails_dir = PROJECT_ROOT / "data" / "emails" / date
    if not emails_dir.exists():
        print(f"❌ Директория с письмами не найдена: {emails_dir}")
        return
    
    # Находим полные пути к файлам
    email_paths: List[Path] = []
    for name in email_names:
        # Ищем файл по базовому имени или префиксу
        if not name.endswith('.json'):
            # Ищем по префиксу (например, email_024)
            matches = list(emails_dir.glob(f"{name}*.json"))
            if matches:
                email_paths.append(matches[0])
            else:
                print(f"⚠️ Не найден файл для: {name}")
        else:
            path = emails_dir / name
            if path.exists():
                email_paths.append(path)
            else:
                print(f"⚠️ Файл не найден: {path}")
    
    if not email_paths:
        print("❌ Нет файлов для обработки")
        return
    
    print(f"\n{'🧪 ТЕСТ-РЕЖИМ: ' if dry_run else ''}🚀 Перезапуск обработки {len(email_paths)} писем за {date}")
    print("=" * 60)
    for i, path in enumerate(email_paths, 1):
        print(f"{i}. {path.name}")
    print("=" * 60)
    
    # Создаем валидатор и запускаем обработку
    args = Namespace(
        mode="batch",
        date=date,
        count=None,
        start_date=None,
        end_date=None,
        dry_run=dry_run
    )
    
    validator = APIPipelineValidator(args)
    validator._process_date(date, email_paths)
    
    print(f"\n✅ Перезапуск завершён. Проверьте результаты в data/llm_results/{date}/")


def main():
    """🏃 Точка входа"""
    parser = argparse.ArgumentParser(
        description="Перезапуск обработки проблемных писем с персональными email в organizations"
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Дата писем (формат: YYYY-MM-DD)"
    )
    parser.add_argument(
        "--emails",
        nargs="+",
        help="Список базовых имён файлов или префиксов (например: email_024 email_025)"
    )
    parser.add_argument(
        "--all-dna-tech",
        action="store_true",
        help="Автоматически найти все письма с персональными адресами ДНК-Технология"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Тестовый режим без записи в БД"
    )
    
    args = parser.parse_args()
    
    emails_dir = PROJECT_ROOT / "data" / "emails"
    
    if args.all_dna_tech:
        print(f"🔍 Автопоиск проблемных писем за {args.date}...")
        email_names = find_dna_tech_emails(args.date, emails_dir)
        if not email_names:
            print("✅ Проблемных писем не найдено!")
            return
        print(f"📋 Найдено {len(email_names)} проблемных писем")
    elif args.emails:
        email_names = args.emails
    else:
        print("❌ Укажите --emails или --all-dna-tech")
        parser.print_help()
        return
    
    reprocess_emails(args.date, email_names, args.dry_run)


if __name__ == "__main__":
    main()