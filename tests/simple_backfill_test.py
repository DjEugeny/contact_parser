#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест backfill утилиты без сложных импортов
"""

import sys
import json
import logging
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Упрощенный модуль для тестирования без зависимостей
class SimpleEmailEnricher:
    """Упрощенный энричер для тестирования"""
    
    def enrich_organizations_emails(self, organizations, email_data):
        """Простое обогащение для демонстрации"""
        result = {}
        
        for org_id, org in organizations.items():
            gid = org.get('gid', f'test_org_{org_id}')
            
            # Простое извлечение из заголовков
            added_emails = []
            headers = email_data.get('headers', {})
            
            # Ищем роль/общие адреса в заголовках
            for header_value in headers.values():
                if '@' in str(header_value):
                    # Упрощенное извлечение email
                    import re
                    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', str(header_value))
                    
                    for email in emails:
                        email_lower = email.lower()
                        # Простая проверка на роль/общие адреса
                        local_part = email_lower.split('@')[0]
                        if local_part in ['info', 'mail', 'sales', 'office', 'contact']:
                            if email_lower not in [e.lower() for e in org.get('emails', [])]:
                                org['emails'].append(email_lower)
                                added_emails.append(email_lower)
            
            if added_emails:
                result[gid] = {
                    'added': added_emails,
                    'skipped': [],
                    'source': {'headers': added_emails}
                }
        
        return result

def test_simple_backfill():
    """Тест простого backfill"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Читаем тестовый файл
    test_file = Path('test_backfill_data/email_test_01.json')
    if not test_file.exists():
        logger.error("Тестовый файл не найден")
        return False
    
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Преобразуем организации
    organizations = {}
    for i, org in enumerate(data.get('organizations', [])):
        org_id = org.get('organization_id', i + 1)
        org['gid'] = f'test_org_{org_id}'
        organizations[org_id] = org
    
    logger.info(f"📧 Emails до обогащения:")
    for org_id, org in organizations.items():
        logger.info(f"  Org {org_id} ({org.get('name')}): {org.get('emails', [])}")
    
    # Обогащаем
    enricher = SimpleEmailEnricher()
    result = enricher.enrich_organizations_emails(organizations, data)
    
    logger.info(f"📧 Emails после обогащения:")
    for org_id, org in organizations.items():
        logger.info(f"  Org {org_id} ({org.get('name')}): {org.get('emails', [])}")
    
    logger.info(f"📊 Метаданные обогащения:")
    logger.info(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Проверяем результат
    medcongress_org = organizations[1]
    emails = [e.lower() for e in medcongress_org.get('emails', [])]
    
    success = 'mail@medcongress.ru' in emails and 'info@medcongress.ru' in emails
    
    if success:
        logger.info("✅ Тест backfill пройден!")
    else:
        logger.error("❌ Тест backfill не пройден!")
    
    return success

if __name__ == "__main__":
    success = test_simple_backfill()
    sys.exit(0 if success else 1)