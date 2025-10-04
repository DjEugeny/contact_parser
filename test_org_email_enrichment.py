#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест обогащения организаций email-адресами (TASK-007B)
Проверяет кейс с Медконгресс и другие сценарии
"""

import sys
import json
import logging
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.postprocessing.org_email_enricher import OrganizationEmailEnricher

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_medcongress_case():
    """Тест кейса с Медконгресс - mail@medcongress.ru должен попасть в organizations[].emails"""
    
    logger.info("🧪 Тестируем кейс с Медконгресс")
    
    # Имитируем данные организации Медконгресс (как после assign_global_ids)
    organizations = {
        1: {
            'organization_id': 1,
            'gid': 'org_medcongress_001',
            'name': 'Медконгресс',
            'website': 'medcongress.ru',
            'emails': [],  # Пустой список - email не извлечен LLM
            'city': 'Москва'
        }
    }
    
    # Имитируем данные письма с mail@medcongress.ru в заголовках
    email_data = {
        'headers': {
            'from': 'Иван Петров <ivan.petrov@medcongress.ru>',
            'to': 'partner@dna-technology.ru',
            'reply-to': 'mail@medcongress.ru',  # Тот самый адрес!
            'cc': 'info@medcongress.ru'
        },
        'body': '''
        Добрый день!
        
        Направляем предложение по конференции.
        
        С уважением,
        Иван Петров
        Менеджер по работе с партнерами
        ООО "Медконгресс"
        E-mail: ivan.petrov@medcongress.ru
        Общие вопросы: mail@medcongress.ru
        Тел: +7 (495) 123-45-67
        ''',
        'attachments': []
    }
    
    # Создаем энричер и тестируем
    enricher = OrganizationEmailEnricher()
    result = enricher.enrich_organizations_emails(organizations, email_data)
    
    # Проверяем результат
    medcongress_org = organizations[1]
    emails_after = medcongress_org.get('emails', [])
    
    logger.info(f"📧 Emails после обогащения: {emails_after}")
    logger.info(f"📊 Метаданные: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # Проверки
    assert 'mail@medcongress.ru' in [email.lower() for email in emails_after], \
        f"mail@medcongress.ru должен быть в {emails_after}"
    
    assert 'info@medcongress.ru' in [email.lower() for email in emails_after], \
        f"info@medcongress.ru должен быть в {emails_after}"
    
    # Персональный адрес НЕ должен попасть
    assert 'ivan.petrov@medcongress.ru' not in [email.lower() for email in emails_after], \
        f"ivan.petrov@medcongress.ru НЕ должен быть в {emails_after}"
    
    logger.info("✅ Тест кейса с Медконгресс пройден!")
    return result

def test_classification_logic():
    """Тест логики классификации email-адресов"""
    
    logger.info("🧪 Тестируем классификацию email-адресов")
    
    organizations = {
        1: {
            'organization_id': 1,
            'gid': 'org_test_001',
            'name': 'Тестовая Компания',
            'website': 'test-company.ru',
            'emails': []
        }
    }
    
    email_data = {
        'headers': {
            'from': 'sales@test-company.ru',          # Роль - должен попасть
            'to': 'ivan.petrov@test-company.ru',      # Персональный - НЕ должен
            'cc': 'info@test-company.ru',             # Роль - должен попасть
            'reply-to': 'john.doe@gmail.com'          # Внешний домен - НЕ должен
        },
        'body': '''
        Контакты:
        - Отдел продаж: sales@test-company.ru  
        - Поддержка: support@test-company.ru
        - Личный email директора: ceo.smith@test-company.ru
        - Внешний консультант: expert@external.com
        ''',
        'attachments': []
    }
    
    enricher = OrganizationEmailEnricher()
    result = enricher.enrich_organizations_emails(organizations, email_data)
    
    emails_after = organizations[1].get('emails', [])
    emails_lower = [email.lower() for email in emails_after]
    
    logger.info(f"📧 Emails после обогащения: {emails_after}")
    
    # Роль/общие адреса должны попасть
    assert 'sales@test-company.ru' in emails_lower, "sales@ должен попасть"
    assert 'info@test-company.ru' in emails_lower, "info@ должен попасть"  
    assert 'support@test-company.ru' in emails_lower, "support@ должен попасть"
    
    # Персональные адреса НЕ должны попасть
    assert 'ivan.petrov@test-company.ru' not in emails_lower, "ivan.petrov@ НЕ должен попасть"
    assert 'ceo.smith@test-company.ru' not in emails_lower, "ceo.smith@ НЕ должен попасть"
    
    # Внешние домены НЕ должны попасть
    assert 'john.doe@gmail.com' not in emails_lower, "gmail НЕ должен попасть"
    assert 'expert@external.com' not in emails_lower, "external.com НЕ должен попасть"
    
    logger.info("✅ Тест классификации пройден!")
    return result

def test_our_domain_protection():
    """Тест защиты от добавления наших доменов в сторонние организации"""
    
    logger.info("🧪 Тестируем защиту от наших доменов")
    
    organizations = {
        1: {
            'organization_id': 1,
            'gid': 'org_external_001',
            'name': 'Внешняя Компания',
            'website': 'external-corp.ru',
            'emails': []
        }
    }
    
    # В письме есть наши адреса - они НЕ должны попасть в сторонние организации
    email_data = {
        'headers': {
            'from': 'info@external-corp.ru',
            'to': 'sales@dna-technology.ru',         # НАШ домен - НЕ должен попасть!
            'cc': 'support@dna-technology.ru',       # НАШ домен - НЕ должен попасть!
            'reply-to': 'contact@external-corp.ru'
        },
        'body': 'Письмо от внешней компании к нам',
        'attachments': []
    }
    
    enricher = OrganizationEmailEnricher()
    result = enricher.enrich_organizations_emails(organizations, email_data)
    
    emails_after = organizations[1].get('emails', [])
    emails_lower = [email.lower() for email in emails_after]
    
    logger.info(f"📧 Emails после обогащения: {emails_after}")
    
    # Наши адреса НЕ должны попасть в стороннюю организацию
    assert 'sales@dna-technology.ru' not in emails_lower, "Наш sales@ НЕ должен попасть"
    assert 'support@dna-technology.ru' not in emails_lower, "Наш support@ НЕ должен попасть"
    
    # Адреса внешней компании должны попасть
    assert 'info@external-corp.ru' in emails_lower, "info@ внешней компании должен попасть"
    assert 'contact@external-corp.ru' in emails_lower, "contact@ внешней компании должен попасть"
    
    logger.info("✅ Тест защиты от наших доменов пройден!")
    return result

def test_attachment_processing():
    """Тест извлечения email из OCR-текста вложений"""
    
    logger.info("🧪 Тестируем извлечение из вложений")
    
    organizations = {
        1: {
            'organization_id': 1,
            'gid': 'org_supplier_001',
            'name': 'Поставщик Материалов',
            'website': 'supplier.ru',
            'emails': []
        }
    }
    
    # В OCR-тексте вложения есть контакты
    email_data = {
        'headers': {
            'from': 'manager@supplier.ru'
        },
        'body': 'Реквизиты в приложении',
        'attachments': [
            {
                'filename': 'реквизиты.pdf',
                'ocr_text': '''
                ООО "Поставщик Материалов"
                ИНН: 7701234567
                Адрес: г. Москва, ул. Промышленная, д. 10
                
                Контакты:
                - Общий отдел: office@supplier.ru
                - Отдел продаж: sales@supplier.ru  
                - Бухгалтерия: buh@supplier.ru
                - Директор Иванов И.И.: ivanov@supplier.ru
                
                Банковские реквизиты:
                Р/с: 40702810000000000001
                '''
            }
        ]
    }
    
    enricher = OrganizationEmailEnricher()
    result = enricher.enrich_organizations_emails(organizations, email_data)
    
    emails_after = organizations[1].get('emails', [])
    emails_lower = [email.lower() for email in emails_after]
    
    logger.info(f"📧 Emails после обогащения: {emails_after}")
    
    # Роль/общие адреса из OCR должны попасть
    assert 'office@supplier.ru' in emails_lower, "office@ из OCR должен попасть"
    assert 'sales@supplier.ru' in emails_lower, "sales@ из OCR должен попасть"
    assert 'buh@supplier.ru' in emails_lower, "buh@ из OCR должен попасть"
    
    # Персональный адрес НЕ должен попасть
    assert 'ivanov@supplier.ru' not in emails_lower, "ivanov@ НЕ должен попасть"
    
    logger.info("✅ Тест извлечения из вложений пройден!")
    return result

def main():
    """Запуск всех тестов"""
    
    logger.info("🚀 Запуск тестов TASK-007B: Organization Emails Backfill")
    
    try:
        # Тест основного кейса Медконгресс
        medcongress_result = test_medcongress_case()
        
        # Тест логики классификации
        classification_result = test_classification_logic()
        
        # Тест защиты от наших доменов  
        protection_result = test_our_domain_protection()
        
        # Тест обработки вложений
        attachment_result = test_attachment_processing()
        
        logger.info("🎉 Все тесты пройдены успешно!")
        
        # Суммарная статистика
        total_stats = {
            'medcongress': medcongress_result,
            'classification': classification_result,
            'protection': protection_result,
            'attachment': attachment_result
        }
        
        logger.info(f"📊 Сводная статистика: {json.dumps(total_stats, indent=2, ensure_ascii=False)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)