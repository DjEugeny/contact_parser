#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка ошибки "'int' object is not iterable" при обогащении email для email_017
"""

import json
import sys
import logging
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.postprocessing.org_email_enricher import OrganizationEmailEnricher

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_with_original_llm_response():
    """Тест с оригинальным ответом LLM из JSON"""
    
    logger.info("🧪 Тестируем с оригинальным ответом LLM")
    
    # Читаем обработанный файл
    processed_file = '/Users/svetlana/contact_parser/data/llm_results/2025-07-29/email_017_20250729_20250729_dna_technology_ru_ee04f823_20251004_174647_174809_processed.json'
    
    with open(processed_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Получаем оригинальный ответ LLM
    original_response = data['processed_result']['original_response']
    
    # Парсим JSON из оригинального ответа
    import re
    json_match = re.search(r'```json\n(.*?)\n```', original_response, re.DOTALL)
    if not json_match:
        logger.error("❌ Не найден JSON в оригинальном ответе")
        return False
    
    llm_data = json.loads(json_match.group(1))
    
    # Преобразуем organizations в нужный формат
    organizations = {}
    for org in llm_data.get('organizations', []):
        org_id = org.get('organization_id')
        if org_id:
            organizations[org_id] = org.copy()
            organizations[org_id]['gid'] = f'test_org_{org_id}'
    
    logger.info("📧 Организации из оригинального ответа LLM:")
    for org_id, org in organizations.items():
        logger.info(f"  - {org['name']}: emails = {org.get('emails', [])}")
    
    # Читаем исходные данные письма
    email_file = '/Users/svetlana/contact_parser/data/emails/2025-07-29/email_017_20250729_20250729_dna-technology_ru_ee04f823.json'
    with open(email_file, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    # Создаем энричер и тестируем
    enricher = OrganizationEmailEnricher()
    
    try:
        result = enricher.enrich_organizations_emails(organizations, email_data)
        
        logger.info("📧 Организации после обогащения:")
        for org_id, org in organizations.items():
            logger.info(f"  - {org['name']}: emails = {org.get('emails', [])}")
        
        # Проверяем МЕД КОНГРЕСС
        medcongress_org = organizations.get(2)
        if medcongress_org:
            emails = [email.lower() for email in medcongress_org.get('emails', [])]
            if 'mail@medcongress.ru' in emails:
                logger.info("✅ mail@medcongress.ru найден в МЕД КОНГРЕСС!")
                return True
            else:
                logger.warning(f"⚠️ mail@medcongress.ru НЕ найден. Есть: {emails}")
                return False
        else:
            logger.error("❌ МЕД КОНГРЕСС не найден")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при обогащении: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_with_corrupted_data():
    """Тест с поврежденными данными (int вместо dict)"""
    
    logger.info("🧪 Тестируем с поврежденными данными")
    
    # Имитируем поврежденную структуру где organizations содержат integers
    corrupted_organizations = {
        1: 123,  # Integer вместо dict!
        2: {
            'organization_id': 2,
            'name': 'МЕД КОНГРЕСС',
            'gid': 'test_org_2',
            'emails': ['mail@medcongress.ru']
        }
    }
    
    email_data = {
        'headers': {
            'from': 'test@example.com'
        },
        'body': 'Test email'
    }
    
    enricher = OrganizationEmailEnricher()
    
    try:
        result = enricher.enrich_organizations_emails(corrupted_organizations, email_data)
        logger.info("✅ Обогащение с поврежденными данными прошло успешно")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка с поврежденными данными: {e}")
        return False

if __name__ == "__main__":
    logger.info("🔍 Отладка ошибки email enrichment для email_017")
    
    # Тест 1: с оригинальным ответом LLM
    success1 = test_with_original_llm_response()
    
    # Тест 2: с поврежденными данными
    success2 = test_with_corrupted_data()
    
    if success1 and success2:
        logger.info("✅ Все тесты прошли успешно")
    else:
        logger.error("❌ Тесты завершились с ошибками")
        sys.exit(1)