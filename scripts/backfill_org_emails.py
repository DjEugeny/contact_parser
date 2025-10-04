#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для массового обогащения организаций email-адресами (TASK-007B)
Обрабатывает архив JSON файлов и добавляет недостающие email в organizations[].emails

Author: Contact Parser Team
Created: 2025-10-04
"""

import json
import logging
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime
import glob
import traceback

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.postprocessing.org_email_enricher import OrganizationEmailEnricher

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backfill_org_emails.log')
    ]
)
logger = logging.getLogger(__name__)


class OrganizationEmailBackfiller:
    """Утилита для массового обогащения email-адресов организаций"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.enricher = OrganizationEmailEnricher()
        self.stats = {
            'files_processed': 0,
            'files_updated': 0,
            'files_skipped': 0,
            'files_error': 0,
            'organizations_processed': 0,
            'organizations_enriched': 0,
            'emails_added_total': 0,
            'emails_skipped_total': 0
        }
        
    def backfill_directory(self, directory_path: str, pattern: str = "*.json") -> Dict[str, Any]:
        """
        Обрабатывает все JSON файлы в директории
        
        Args:
            directory_path: Путь к директории с JSON файлами
            pattern: Паттерн для поиска файлов (по умолчанию *.json)
            
        Returns:
            Dict: Отчет о обработке
        """
        directory = Path(directory_path)
        if not directory.exists():
            raise ValueError(f"Директория не найдена: {directory_path}")
            
        files = list(directory.glob(pattern))
        if not files:
            logger.warning(f"Файлы по паттерну {pattern} не найдены в {directory_path}")
            return {'files': [], 'stats': self.stats}
            
        logger.info(f"🔍 Найдено {len(files)} файлов для обработки")
        
        processed_files = []
        
        for file_path in files:
            try:
                result = self._process_file(file_path)
                processed_files.append(result)
                self.stats['files_processed'] += 1
                
                if result['updated']:
                    self.stats['files_updated'] += 1
                else:
                    self.stats['files_skipped'] += 1
                    
            except Exception as e:
                logger.error(f"❌ Ошибка обработки файла {file_path}: {e}")
                self.stats['files_error'] += 1
                processed_files.append({
                    'file': str(file_path),
                    'updated': False,
                    'error': str(e),
                    'organizations': []
                })
        
        return {
            'files': processed_files,
            'stats': self.stats,
            'summary': self._generate_summary()
        }
    
    def _process_file(self, file_path: Path) -> Dict[str, Any]:
        """Обрабатывает один JSON файл"""
        logger.info(f"📁 Обрабатываем файл: {file_path.name}")
        
        # Читаем файл
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем структуру
        if not self._validate_file_structure(data):
            logger.warning(f"⚠️ Файл {file_path.name} не содержит нужной структуры, пропускаем")
            return {
                'file': str(file_path),
                'updated': False,
                'reason': 'invalid_structure',
                'organizations': []
            }
        
        # Готовим данные для обогащения
        organizations = self._prepare_organizations(data.get('organizations', []))
        
        if not organizations:
            logger.info(f"📄 Файл {file_path.name}: нет организаций для обработки")
            return {
                'file': str(file_path),
                'updated': False,
                'reason': 'no_organizations',
                'organizations': []
            }
        
        # Обогащаем email-адреса
        email_data = self._extract_email_data(data)
        original_emails = self._count_existing_emails(organizations)
        
        enrichment_metadata = self.enricher.enrich_organizations_emails(organizations, email_data)
        
        new_emails = self._count_existing_emails(organizations)
        emails_added = new_emails - original_emails
        
        # Обновляем статистику
        self.stats['organizations_processed'] += len(organizations)
        if enrichment_metadata:
            enriched_orgs = len([meta for meta in enrichment_metadata.values() if meta.get('added')])
            self.stats['organizations_enriched'] += enriched_orgs
        
        for meta in enrichment_metadata.values():
            self.stats['emails_added_total'] += len(meta.get('added', []))
            self.stats['emails_skipped_total'] += len(meta.get('skipped', []))
        
        # Записываем обратно в файл (если не dry run)
        updated = emails_added > 0
        if updated and not self.dry_run:
            self._update_file(file_path, data, organizations, enrichment_metadata)
            
        logger.info(f"✅ Файл {file_path.name}: добавлено {emails_added} email в {len(organizations)} организаций")
        
        return {
            'file': str(file_path),
            'updated': updated,
            'emails_added': emails_added,
            'organizations_processed': len(organizations),
            'organizations_enriched': len([meta for meta in enrichment_metadata.values() if meta.get('added')]),
            'organizations': self._format_org_results(organizations, enrichment_metadata),
            'metadata': enrichment_metadata
        }
    
    def _validate_file_structure(self, data: Dict[str, Any]) -> bool:
        """Проверяет структуру JSON файла"""
        return (
            isinstance(data, dict) and
            'organizations' in data and
            isinstance(data['organizations'], list)
        )
        
    def _prepare_organizations(self, org_list: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """Преобразует список организаций в словарь с добавлением gid"""
        organizations = {}
        
        for i, org in enumerate(org_list):
            if not isinstance(org, dict):
                continue
                
            org_id = org.get('organization_id', i + 1)
            
            # Добавляем gid если его нет (для совместимости)
            if 'gid' not in org:
                org['gid'] = f"backfill_org_{org_id}_{i}"
            
            # Обеспечиваем наличие emails массива
            if 'emails' not in org:
                org['emails'] = []
            elif not isinstance(org['emails'], list):
                org['emails'] = []
                
            organizations[org_id] = org
            
        return organizations
        
    def _extract_email_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Извлекает email данные из файла"""
        email_data = {}
        
        # Ищем заголовки письма
        if 'headers' in data:
            email_data['headers'] = data['headers']
        elif 'email_headers' in data:
            email_data['headers'] = data['email_headers']
        
        # Ищем тело письма
        if 'body' in data:
            email_data['body'] = data['body']
        elif 'email_body' in data:
            email_data['body'] = data['email_body']
        elif 'plain_text' in data:
            email_data['body'] = data['plain_text']
            
        # Ищем вложения
        if 'attachments' in data:
            email_data['attachments'] = data['attachments']
        elif 'email_attachments' in data:
            email_data['attachments'] = data['email_attachments']
        else:
            email_data['attachments'] = []
            
        return email_data
        
    def _count_existing_emails(self, organizations: Dict[int, Dict[str, Any]]) -> int:
        """Подсчитывает общее количество email в организациях"""
        total = 0
        for org in organizations.values():
            emails = org.get('emails', [])
            if isinstance(emails, list):
                total += len(emails)
        return total
        
    def _update_file(
        self, 
        file_path: Path, 
        data: Dict[str, Any], 
        organizations: Dict[int, Dict[str, Any]],
        enrichment_metadata: Dict[str, Dict[str, Any]]
    ) -> None:
        """Обновляет файл с новыми данными"""
        
        # Обновляем список организаций в data
        org_list = []
        for org_id in sorted(organizations.keys()):
            org_list.append(organizations[org_id])
        data['organizations'] = org_list
        
        # Добавляем метаданные обогащения
        if 'postprocessing_metadata' not in data:
            data['postprocessing_metadata'] = {}
        
        if 'enrichment' not in data['postprocessing_metadata']:
            data['postprocessing_metadata']['enrichment'] = {}
            
        data['postprocessing_metadata']['enrichment']['org_email_enrichment'] = enrichment_metadata
        data['postprocessing_metadata']['backfill_org_emails'] = {
            'processed_at': datetime.now().isoformat(),
            'version': '1.0.0',
            'script': 'backfill_org_emails.py'
        }
        
        # Записываем файл
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"💾 Файл {file_path.name} обновлен")
        
    def _format_org_results(
        self, 
        organizations: Dict[int, Dict[str, Any]], 
        enrichment_metadata: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Форматирует результаты по организациям для отчета"""
        results = []
        
        for org_id, org in organizations.items():
            gid = org.get('gid', '')
            meta = enrichment_metadata.get(str(gid), {}) if gid else {}
            
            results.append({
                'organization_id': org_id,
                'name': org.get('name'),
                'gid': gid,
                'emails_before': len(org.get('emails', [])) - len(meta.get('added', [])),
                'emails_after': len(org.get('emails', [])),
                'emails_added': meta.get('added', []),
                'emails_skipped': meta.get('skipped', [])
            })
            
        return results
        
    def _generate_summary(self) -> Dict[str, Any]:
        """Генерирует итоговый отчет"""
        return {
            'files': {
                'total': self.stats['files_processed'],
                'updated': self.stats['files_updated'],
                'skipped': self.stats['files_skipped'],
                'errors': self.stats['files_error']
            },
            'organizations': {
                'processed': self.stats['organizations_processed'],
                'enriched': self.stats['organizations_enriched'],
                'enrichment_rate': (
                    self.stats['organizations_enriched'] / self.stats['organizations_processed'] 
                    if self.stats['organizations_processed'] > 0 else 0
                )
            },
            'emails': {
                'added': self.stats['emails_added_total'],
                'skipped': self.stats['emails_skipped_total'],
                'total_processed': self.stats['emails_added_total'] + self.stats['emails_skipped_total']
            }
        }


def main():
    """Основная функция CLI"""
    parser = argparse.ArgumentParser(
        description='Массовое обогащение организаций email-адресами',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Обработать все JSON файлы в текущей директории
  python scripts/backfill_org_emails.py

  # Обработать файлы в конкретной директории
  python scripts/backfill_org_emails.py -d /path/to/json/files

  # Сухой прогон (без изменения файлов)
  python scripts/backfill_org_emails.py --dry-run

  # Обработать файлы по конкретному паттерну
  python scripts/backfill_org_emails.py -p "*_processed.json"

  # Сохранить отчет в файл
  python scripts/backfill_org_emails.py -o report.json
        """
    )
    
    parser.add_argument(
        '-d', '--directory',
        default='.',
        help='Директория с JSON файлами (по умолчанию: текущая директория)'
    )
    
    parser.add_argument(
        '-p', '--pattern',
        default='*.json',
        help='Паттерн для поиска файлов (по умолчанию: *.json)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим просмотра без изменения файлов'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Файл для сохранения отчета (JSON)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Подробный вывод'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.dry_run:
        logger.info("🔍 Режим сухого прогона - файлы не будут изменены")
    
    try:
        # Создаем backfiller
        backfiller = OrganizationEmailBackfiller(dry_run=args.dry_run)
        
        # Обрабатываем файлы
        logger.info(f"🚀 Запуск обогащения email организаций")
        logger.info(f"📁 Директория: {args.directory}")
        logger.info(f"🔍 Паттерн: {args.pattern}")
        
        result = backfiller.backfill_directory(args.directory, args.pattern)
        
        # Выводим отчет
        summary = result['summary']
        logger.info("=" * 60)
        logger.info("📊 ИТОГОВЫЙ ОТЧЕТ")
        logger.info("=" * 60)
        logger.info(f"📁 Файлы:")
        logger.info(f"  • Обработано: {summary['files']['total']}")
        logger.info(f"  • Обновлено: {summary['files']['updated']}")
        logger.info(f"  • Пропущено: {summary['files']['skipped']}")
        logger.info(f"  • Ошибки: {summary['files']['errors']}")
        
        logger.info(f"🏢 Организации:")
        logger.info(f"  • Обработано: {summary['organizations']['processed']}")
        logger.info(f"  • Обогащено: {summary['organizations']['enriched']}")
        logger.info(f"  • Процент обогащения: {summary['organizations']['enrichment_rate']:.1%}")
        
        logger.info(f"📧 Email адреса:")
        logger.info(f"  • Добавлено: {summary['emails']['added']}")
        logger.info(f"  • Пропущено: {summary['emails']['skipped']}")
        logger.info(f"  • Всего обработано: {summary['emails']['total_processed']}")
        
        # Сохраняем отчет
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Отчет сохранен в {args.output}")
        
        logger.info("✅ Обогащение завершено успешно!")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        logger.error(f"📚 Traceback:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()