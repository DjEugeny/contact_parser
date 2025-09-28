#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест обработки вложений через основной пайплайн
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from src.integrated_llm_processor import IntegratedLLMProcessor
from src.email_loader import ProcessedEmailLoader
import json
from datetime import datetime

def test_attachment_processing():
    """Тестирует обработку письма с вложениями через основной пайплайн"""
    
    print("🧪 ТЕСТ ОБРАБОТКИ ВЛОЖЕНИЙ ЧЕРЕЗ ОСНОВНОЙ ПАЙПЛАЙН")
    print("=" * 60)
    
    # Инициализируем процессор в тестовом режиме
    processor = IntegratedLLMProcessor(test_mode=True)
    email_loader = ProcessedEmailLoader()
    
    # Получаем доступные даты
    available_dates = email_loader.get_available_date_folders()
    print(f"📅 Доступные даты: {available_dates[:5]}...")  # Показываем первые 5
    
    if not available_dates:
        print("❌ Нет доступных дат для тестирования")
        return
    
    # Берем первую доступную дату
    test_date = available_dates[0]
    print(f"🎯 Тестируем дату: {test_date}")
    
    # Загружаем письма за эту дату
    emails = email_loader.load_emails_by_date(test_date)
    print(f"📧 Загружено писем: {len(emails)}")
    
    if not emails:
        print("❌ Нет писем для тестирования")
        return
    
    # Ищем письмо с вложениями
    email_with_attachments = None
    for email in emails:
        if email.get('attachments') and len(email['attachments']) > 0:
            email_with_attachments = email
            break
    
    if not email_with_attachments:
        print("❌ Не найдено писем с вложениями")
        # Показываем информацию о первом письме
        if emails:
            first_email = emails[0]
            print(f"\n📧 Информация о первом письме:")
            print(f"   От: {first_email.get('from', 'N/A')}")
            print(f"   Тема: {first_email.get('subject', 'N/A')}")
            print(f"   Вложения: {len(first_email.get('attachments', []))}")
            
            # Тестируем на первом письме даже без вложений
            email_with_attachments = first_email
    
    print(f"\n🎯 ТЕСТИРУЕМ ПИСЬМО:")
    print(f"   От: {email_with_attachments.get('from', 'N/A')}")
    print(f"   Тема: {email_with_attachments.get('subject', 'N/A')}")
    print(f"   Вложения: {len(email_with_attachments.get('attachments', []))}")
    
    # Обрабатываем письмо через основной пайплайн
    print("\n🔄 ЗАПУСК ОБРАБОТКИ ЧЕРЕЗ ОСНОВНОЙ ПАЙПЛАЙН...")
    result = processor.process_single_email(email_with_attachments)
    
    if result:
        print("\n✅ РЕЗУЛЬТАТ ОБРАБОТКИ:")
        print(f"   📧 Письмо обработано: Да")
        print(f"   📎 Вложений обработано: {result.get('attachments_processed', 0)}")
        print(f"   🏢 Организаций найдено: {len(result.get('organizations', []))}")
        print(f"   👤 Контактов найдено: {len(result.get('contacts', []))}")
        print(f"   💼 Коммерческих предложений: {len(result.get('commercial_offers', []))}")
        
        # Показываем детали организаций
        organizations = result.get('organizations', [])
        if organizations:
            print("\n🏢 НАЙДЕННЫЕ ОРГАНИЗАЦИИ:")
            for i, org in enumerate(organizations, 1):
                print(f"   {i}. {org.get('name', 'N/A')}")
                print(f"      ИНН: {org.get('inn', 'N/A')}")
                print(f"      Город: {org.get('city', 'N/A')}")
                print(f"      Телефоны: {org.get('phones', [])}")
                print(f"      Email: {org.get('emails', [])}")
        
        # Показываем детали контактов
        contacts = result.get('contacts', [])
        if contacts:
            print("\n👤 НАЙДЕННЫЕ КОНТАКТЫ:")
            for i, contact in enumerate(contacts, 1):
                print(f"   {i}. {contact.get('name', 'N/A')}")
                print(f"      Должность: {contact.get('position', 'N/A')}")
                print(f"      Телефон: {contact.get('phones', [])}")
                print(f"      Email: {contact.get('email', 'N/A')}")
                print(f"      Уверенность: {contact.get('confidence', 0):.2%}")
        
        # Показываем коммерческие предложения
        commercial_offers = result.get('commercial_offers', [])
        if commercial_offers:
            print("\n💼 КОММЕРЧЕСКИЕ ПРЕДЛОЖЕНИЯ:")
            for i, offer in enumerate(commercial_offers, 1):
                print(f"   {i}. Тип: {offer.get('offer_type', 'N/A')}")
                print(f"      Найдено: {offer.get('found', False)}")
                print(f"      Оборудование: {len(offer.get('equipment_items', []))} позиций")
        else:
            print("\n💼 Коммерческие предложения не найдены")
            print("   ⚠️ Возможные причины:")
            print("   - Тестовый режим (commercial_offers всегда пустой)")
            print("   - В письме/вложениях нет КП")
            print("   - Ошибка в промпте или обработке LLM")
        
        # Сохраняем результат для анализа
        output_file = Path("test_attachment_result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Результат сохранен в {output_file}")
        
    else:
        print("❌ Ошибка обработки письма")
    
    print("\n🏁 ТЕСТ ЗАВЕРШЕН")

if __name__ == "__main__":
    test_attachment_processing()