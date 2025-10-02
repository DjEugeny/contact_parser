#!/usr/bin/env python3
"""
🧪 Тест одного проблемного письма после исправлений
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from integrated_llm_processor import IntegratedLLMProcessor
import json

def test_single_email():
    """Тестирование одного письма с вложением"""
    print("🧪 Тест письма email_004 после исправлений")
    print("=" * 60)
    
    # Инициализируем процессор
    processor = IntegratedLLMProcessor(test_mode=False)
    
    # Тестируем проблемное письмо с КП
    email_file = Path("data/emails/2025-07-29/email_004_20250729_20250729_dna-technology_ru_6e851453.json")
    
    if not email_file.exists():
        print(f"❌ Файл {email_file} не найден")
        return
    
    print(f"📧 Обработка: {email_file.name}")
    print("-" * 50)
    
    try:
        # Загружаем письмо
        with open(email_file, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        # Обрабатываем письмо
        result = processor.process_single_email(email_data)
        
        if result:
            print(f"✅ Письмо обработано успешно")
            print(f"   📊 Контактов: {len(result.get('contacts', []))}")
            print(f"   🏢 Организаций: {len(result.get('organizations', []))}")
            print(f"   💼 КП: {len(result.get('commercial_offers', []))}")
            print(f"   🔗 Взаимодействий: {len(result.get('interactions', []))}")
            
            # Проверяем наличие вложений
            attachments = result.get('attachments_details', [])
            if attachments:
                print(f"   📎 Вложений обработано: {len(attachments)}")
                for att in attachments:
                    if att and att.get('text'):
                        print(f"     - {att['file_name']}: {len(att['text'])} символов ✅")
                    else:
                        print(f"     - {att.get('file_name', 'Unknown')}: ❌ не обработано")
            else:
                print(f"   📎 Вложений: нет")
            
            # Проверяем организации
            organizations = result.get('organizations', [])
            print(f"\\n🏢 Найденные организации:")
            for i, org in enumerate(organizations, 1):
                print(f"   {i}. {org.get('name', 'Unknown')} (ID: {org.get('organization_id')})")
            
            # Проверяем КП
            commercial_offers = result.get('commercial_offers', [])
            if commercial_offers:
                print(f"\\n💼 Коммерческие предложения:")
                for i, offer in enumerate(commercial_offers, 1):
                    print(f"   {i}. {offer.get('title', 'Unknown')}")
            else:
                print(f"\\n💼 Коммерческие предложения: не найдены ❌")
                
        else:
            print(f"❌ Ошибка обработки письма")
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_email()