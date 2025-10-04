#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправления классификации mail@ адресов
"""

import json
import sys
import logging
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.postprocessing.email_classifier import classify_mailbox, MailboxType
from src.postprocessing.postprocessor import PostProcessor

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mail_classification():
    """Тест классификации mail@ адресов"""
    
    logger.info("🧪 Тестируем классификацию mail@ адресов")
    
    # Создаем PostProcessor для загрузки конфигурации
    processor = PostProcessor()
    cfg, corp_domains = processor._get_email_classifier_assets()
    
    logger.info(f"📋 Shared prefixes: {cfg.get('shared_mailboxes_prefixes', [])}")
    
    # Тестируем различные адреса
    test_cases = [
        ('mail@medcongress.ru', MailboxType.SHARED_ORG),
        ('info@medcongress.ru', MailboxType.SHARED_ORG),
        ('sales@medcongress.ru', MailboxType.SHARED_ORG),
        ('support@medcongress.ru', MailboxType.SHARED_ORG),
        ('ivan.petrov@medcongress.ru', MailboxType.PERSONAL_EXTERNAL),  # Персональный, внешний домен
        ('noreply@medcongress.ru', MailboxType.TECHNICAL),
    ]
    
    success = True
    for email, expected_type in test_cases:
        result = classify_mailbox(email, None, corp_domains, cfg)
        if result == expected_type:
            logger.info(f"✅ {email} -> {result.value}")
        else:
            logger.error(f"❌ {email} -> {result.value} (ожидалось {expected_type.value})")
            success = False
    
    return success

def test_email_cleanup_preservation():
    """Тест сохранения mail@ адресов в email cleanup"""
    
    logger.info("🧪 Тестируем сохранение mail@ адресов в cleanup")
    
    # Имитируем данные организации с mail@ адресом
    organizations = {
        1: {
            'organization_id': 1,
            'name': 'МЕД КОНГРЕСС',
            'emails': ['mail@medcongress.ru', 'ivan.petrov@medcongress.ru', 'info@medcongress.ru']
        }
    }
    
    contacts = []
    
    # Создаем PostProcessor и тестируем cleanup
    processor = PostProcessor()
    
    # Применяем cleanup
    cleanup_log = processor._cleanup_organization_emails(organizations, contacts)
    
    # Проверяем результат  
    org_emails = organizations[1].get('emails', [])
    logger.info(f"📧 Emails после cleanup: {org_emails}")
    logger.info(f"📊 Cleanup log: {json.dumps(cleanup_log, indent=2, ensure_ascii=False)}")
    
    # mail@ и info@ должны остаться, ivan.petrov@ должен быть удален
    success = True
    if 'mail@medcongress.ru' not in org_emails:
        logger.error("❌ mail@medcongress.ru был удален!")
        success = False
    else:
        logger.info("✅ mail@medcongress.ru сохранен")
    
    if 'info@medcongress.ru' not in org_emails:
        logger.error("❌ info@medcongress.ru был удален!")
        success = False
    else:
        logger.info("✅ info@medcongress.ru сохранен")
    
    if 'ivan.petrov@medcongress.ru' in org_emails:
        logger.error("❌ ivan.petrov@medcongress.ru НЕ был удален!")
        success = False
    else:
        logger.info("✅ ivan.petrov@medcongress.ru правильно удален")
    
    return success

if __name__ == "__main__":
    logger.info("🔍 Тестирование исправления классификации mail@ адресов")
    
    # Тест 1: Классификация
    success1 = test_mail_classification()
    
    # Тест 2: Email cleanup
    success2 = test_email_cleanup_preservation()
    
    if success1 and success2:
        logger.info("✅ Все тесты прошли! mail@ адреса теперь правильно классифицируются")
    else:
        logger.error("❌ Тесты не прошли")
        sys.exit(1)