#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт миграции писем на единый формат с полем body.

Обеспечивает обратную совместимость добавляя поле body со значением 
из body_clean в старые письма, которые его не имеют.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def setup_logging() -> logging.Logger:
    """Настройка логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                PROJECT_ROOT / "data" / "logs" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                encoding="utf-8"
            )
        ]
    )
    return logging.getLogger("EmailMigration")

def check_email_format(email_path: Path, logger: logging.Logger) -> Tuple[bool, bool]:
    """
    Проверяет формат письма.
    
    Returns:
        Tuple[has_body, body_equals_clean]: (есть поле body, body == body_clean)
    """
    try:
        with open(email_path, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        has_body = 'body' in email_data
        body_equals_clean = False
        
        if has_body and 'body_clean' in email_data:
            body_equals_clean = email_data['body'] == email_data['body_clean']
        
        return has_body, body_equals_clean
    except Exception as e:
        logger.error(f"❌ Ошибка проверки {email_path}: {e}")
        return False, False

def migrate_email(email_path: Path, logger: logging.Logger) -> bool:
    """
    Мигрирует письмо на новый формат.
    
    Returns:
        True если миграция успешна
    """
    try:
        with open(email_path, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        # Если поле body уже есть - ничего не делаем
        if 'body' in email_data:
            logger.debug(f"⏭️ Пропуск (уже есть body): {email_path.name}")
            return True
        
        # Добавляем поле body со значением из body_clean
        if 'body_clean' in email_data:
            email_data['body'] = email_data['body_clean']
            logger.info(f"🔄 Миграция (body_clean → body): {email_path.name}")
        elif 'body_original' in email_data:
            email_data['body'] = email_data['body_original']
            logger.info(f"🔄 Миграция (body_original → body): {email_path.name}")
        else:
            logger.warning(f"⚠️ Нет исходных полей для миграции: {email_path.name}")
            return False
        
        # Сохраняем обновленное письмо
        with open(email_path, 'w', encoding='utf-8') as f:
            json.dump(email_data, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции {email_path}: {e}")
        return False

def analyze_emails_directory(emails_dir: Path, logger: logging.Logger) -> Dict[str, int]:
    """
    Анализирует директорию с письмами.
    
    Returns:
        Статистика по форматам писем
    """
    stats = {
        'total': 0,
        'with_body': 0,
        'without_body': 0,
        'body_equals_clean': 0,
        'migration_needed': 0
    }
    
    for date_dir in sorted(emails_dir.iterdir()):
        if not date_dir.is_dir():
            continue
            
        logger.info(f"📂 Анализ папки: {date_dir.name}")
        
        for email_file in date_dir.glob("*.json"):
            stats['total'] += 1
            
            has_body, body_equals_clean = check_email_format(email_file, logger)
            
            if has_body:
                stats['with_body'] += 1
                if body_equals_clean:
                    stats['body_equals_clean'] += 1
            else:
                stats['without_body'] += 1
                stats['migration_needed'] += 1
    
    return stats

def migrate_emails_directory(emails_dir: Path, logger: logging.Logger, dry_run: bool = False) -> Dict[str, int]:
    """
    Мигрирует письма в директории.
    
    Returns:
        Статистика миграции
    """
    stats = {
        'total': 0,
        'migrated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    for date_dir in sorted(emails_dir.iterdir()):
        if not date_dir.is_dir():
            continue
            
        logger.info(f"📂 Обработка папки: {date_dir.name}")
        
        for email_file in date_dir.glob("*.json"):
            stats['total'] += 1
            
            has_body, _ = check_email_format(email_file, logger)
            
            if has_body:
                stats['skipped'] += 1
                logger.debug(f"⏭️ Пропуск (уже есть body): {email_file.name}")
                continue
            
            if dry_run:
                logger.info(f"🔍 Нужна миграция: {email_file.name}")
                stats['migrated'] += 1
            else:
                if migrate_email(email_file, logger):
                    stats['migrated'] += 1
                else:
                    stats['errors'] += 1
    
    return stats

def main():
    """Главная функция."""
    logger = setup_logging()
    
    print("=" * 70)
    print("🔄 МИГРАЦИЯ ПИСЕМ НА ЕДИНЫЙ ФОРМАТ (body)")
    print("=" * 70)
    print()
    
    emails_dir = PROJECT_ROOT / "data" / "emails"
    
    if not emails_dir.exists():
        logger.error(f"❌ Директория с письмами не найдена: {emails_dir}")
        return
    
    print("📊 АНАЛИЗ ТЕКУЩЕГО СОСТОЯНИЯ")
    print("=" * 50)
    
    stats = analyze_emails_directory(emails_dir, logger)
    
    print(f"📧 Всего писем: {stats['total']}")
    print(f"✅ С полем body: {stats['with_body']}")
    print(f"❌ Без поля body: {stats['without_body']}")
    print(f"✅ body == body_clean: {stats['body_equals_clean']}")
    print(f"🔄 Нужна миграция: {stats['migration_needed']}")
    print()
    
    if stats['migration_needed'] == 0:
        print("🎉 Все письма уже в новом формате!")
        return
    
    print("🚫 ВАЖНО: Создайте бэкап перед миграцией!")
    print("   cp -r data/emails data/emails_backup_$(date +%Y%m%d_%H%M%S)")
    print()
    
    choice = input("Продолжить миграцию? (д/н): ").strip().lower()
    if choice not in ['д', 'да', 'y', 'yes']:
        print("❌ Миграция отменена")
        return
    
    print()
    print("🔄 ВЫПОЛНЕНИЕ МИГРАЦИИ")
    print("=" * 50)
    
    migration_stats = migrate_emails_directory(emails_dir, logger, dry_run=False)
    
    print()
    print("📊 РЕЗУЛЬТАТЫ МИГРАЦИИ")
    print("=" * 50)
    print(f"📧 Всего обработано: {migration_stats['total']}")
    print(f"✅ Успешно мигрировано: {migration_stats['migrated']}")
    print(f"⏭️ Пропущено: {migration_stats['skipped']}")
    print(f"❌ Ошибок: {migration_stats['errors']}")
    print()
    
    if migration_stats['errors'] == 0:
        print("🎉 Миграция завершена успешно!")
        print("✅ Все письма теперь имеют единое поле body")
    else:
        print("⚠️ Миграция завершена с ошибками")
        print("🔍 Проверьте лог файл для деталей")

if __name__ == "__main__":
    main()