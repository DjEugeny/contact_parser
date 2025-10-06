#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест обогащения email-адресов для письма email_017 (кейс Медконгресс)
"""

import sys
import json
import logging
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Простой тест только нашего модуля
from src.postprocessing.org_email_enricher import OrganizationEmailEnricher

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_email_017_enrichment():
    """Тест обогащения письма email_017"""
    
    # Путь к исходному письму
    email_file = Path('/Users/svetlana/contact_parser/data/emails/2025-07-29/email_017_20250729_20250729_dna-technology_ru_ee04f823.json')
    
    if not email_file.exists():
        logger.error(f"Файл письма не найден: {email_file}")
        return False
    
    # Читаем исходное письмо
    with open(email_file, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    # Имитируем LLM результат как в processed.json
    llm_result = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "inn": None,
                "website": "dna-technology.ru",
                "city": "Москва",
                "address": "Варшавское шоссе, дом 125Ж, корпус 6, этаж 5",
                "emails": [],
                "phones": [
                    {
                        "type": "main",
                        "number": "+7 (495) 640-17-71",
                        "normalized": "+74956401771",
                        "original": "+7 (495) 640-17-71 (доб. 2026)",
                        "extension": "2026"
                    }
                ]
            },
            {
                "organization_id": 2,
                "name": "МЕД КОНГРЕСС",
                "inn": None,
                "website": "medcongress.ru",
                "city": "Новосибирск",
                "address": "ул. Красина 43",
                "emails": ["mail@medcongress.ru"],  # В оригинальном LLM ответе это было!
                "phones": [
                    {
                        "type": "main",
                        "number": "+7 (905) 952-20-20",
                        "normalized": "+79059522020",
                        "original": "+7 (905) 952-20-20",
                        "extension": None
                    },
                    {
                        "type": "main",
                        "number": "+7 (383) 380-21-04",
                        "normalized": "+73833802104",
                        "original": "+7 (383) 380-21-04",
                        "extension": None
                    }
                ]
            }
        ],
        "contacts": [
            {
                "contact_id": 1,
                "name": "Козлова Ольга",
                "organization_id": 1,
                "position": "Ведущий сервис-менеджер",
                "email": "kozlova@dna-technology.ru",
                "phones": [
                    {
                        "type": "mobile",
                        "number": "+7-915-252-22-43",
                        "normalized": "+79152522243",
                        "original": "+7-915-252-22-43",
                        "extension": None
                    }
                ],
                "city": None,
                "address": None,
                "role_in_message": "sender",
                "confidence": 1.0
            }
        ]
    }
    
    logger.info("🧪 Тестируем обогащение письма email_017")
    logger.info(f"📧 Исходные организации:")
    for org in llm_result['organizations']:
        logger.info(f"  - {org['name']}: emails = {org.get('emails', [])}")
    
    # Простое тестирование только нашего модуля
    enricher = OrganizationEmailEnricher()
    
    # Преобразуем организации в формат словаря
    organizations = {}
    for org in llm_result['organizations']:
        org_id = org['organization_id']
        org['gid'] = f'test_org_{org_id}'
        organizations[org_id] = org
    
    # Обрабатываем только нашим модулем
    try:
        logger.info("📧 Организации до обработки:")
        for org_id, org in organizations.items():
            logger.info(f"  - {org['name']}: emails = {org.get('emails', [])}")
        
        # Обогащаем email
        result = enricher.enrich_organizations_emails(organizations, email_data)
        
        logger.info("📧 Организации после обработки:")
        for org_id, org in organizations.items():
            logger.info(f"  - {org['name']}: emails = {org.get('emails', [])}")
        
        # Проверяем что mail@medcongress.ru есть у МЕД КОНГРЕСС
        medcongress_org = organizations.get(2)  # organization_id = 2
        
        if medcongress_org:
            emails = [email.lower() for email in medcongress_org.get('emails', [])]
            if 'mail@medcongress.ru' in emails:
                logger.info("✅ mail@medcongress.ru найден в МЕД КОНГРЕСС!")
                return True
            else:
                logger.error(f"❌ mail@medcongress.ru НЕ найден! Есть: {emails}")
                return False
        else:
            logger.error("❌ Организация МЕД КОНГРЕСС не найдена")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_email_017_enrichment()
    sys.exit(0 if success else 1)