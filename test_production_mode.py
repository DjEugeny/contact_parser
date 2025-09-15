#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест обработки вложений в рабочем режиме (с реальным LLM)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from src.integrated_llm_processor import IntegratedLLMProcessor
from src.email_loader import ProcessedEmailLoader
import json
from datetime import datetime

def test_production_mode():
    """Тестирует обработку письма с вложениями в рабочем режиме"""
    
    print("🧪 ТЕСТ ОБРАБОТКИ ВЛОЖЕНИЙ В РАБОЧЕМ РЕЖИМЕ")
    print("=" * 60)
    
    # Инициализируем процессор в рабочем режиме (test_mode=False)
    processor = IntegratedLLMProcessor(test_mode=False)
    email_loader = ProcessedEmailLoader()
    
    # Получаем доступные даты
    available_dates = email_loader.get_available_date_folders()
    print(f"📅 Доступные даты: {available_dates[:3]}...")  # Показываем первые 3
    
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
        # Берем первое письмо для теста
        email_with_attachments = emails[0]
    
    print(f"\n🎯 ТЕСТИРУЕМ ПИСЬМО:")
    print(f"   От: {email_with_attachments.get('from', 'N/A')}")
    print(f"   Тема: {email_with_attachments.get('subject', 'N/A')[:80]}...")
    print(f"   Вложения: {len(email_with_attachments.get('attachments', []))}")
    
    # Показываем информацию о вложениях
    attachments = email_with_attachments.get('attachments', [])
    if attachments:
        print("\n📎 ИНФОРМАЦИЯ О ВЛОЖЕНИЯХ:")
        for i, attachment in enumerate(attachments, 1):
            print(f"   {i}. {attachment}")
    
    print("\n⚠️ ВНИМАНИЕ: Запускается реальный LLM запрос!")
    print("   Это может занять время и потратить токены.")
    
    # Спрашиваем подтверждение
    response = input("\n❓ Продолжить? (y/N): ").strip().lower()
    if response != 'y':
        print("❌ Тест отменен пользователем")
        return
    
    # Обрабатываем письмо через основной пайплайн
    print("\n🔄 ЗАПУСК ОБРАБОТКИ В РАБОЧЕМ РЕЖИМЕ...")
    print("   ⏳ Это может занять 30-60 секунд...")
    
    try:
        result = processor.process_single_email(email_with_attachments)
        
        if result:
            print("\n✅ РЕЗУЛЬТАТ ОБРАБОТКИ:")
            print(f"   📧 Письмо обработано: Да")
            print(f"   📎 Вложений обработано: {result.get('attachments_processed', 0)}")
            print(f"   🏢 Организаций найдено: {len(result.get('organizations', []))}")
            print(f"   👤 Контактов найдено: {len(result.get('contacts', []))}")
            print(f"   💼 Коммерческих предложений: {len(result.get('commercial_offers', []))}")
            
            # Показываем коммерческие предложения (главная цель теста)
            commercial_offers = result.get('commercial_offers', [])
            if commercial_offers:
                print("\n💼 НАЙДЕННЫЕ КОММЕРЧЕСКИЕ ПРЕДЛОЖЕНИЯ:")
                for i, offer in enumerate(commercial_offers, 1):
                    print(f"   {i}. Тип: {offer.get('offer_type', 'N/A')}")
                    print(f"      Найдено: {offer.get('found', False)}")
                    print(f"      Оборудование: {len(offer.get('equipment_items', []))} позиций")
                    
                    # Показываем детали оборудования
                    equipment = offer.get('equipment_items', [])
                    if equipment:
                        print("      📋 Позиции оборудования:")
                        for j, item in enumerate(equipment[:3], 1):  # Показываем первые 3
                            print(f"         {j}. {item.get('name', 'N/A')}")
                            print(f"            Количество: {item.get('quantity', 'N/A')}")
                            print(f"            Цена: {item.get('price', 'N/A')}")
                        if len(equipment) > 3:
                            print(f"         ... и еще {len(equipment) - 3} позиций")
            else:
                print("\n💼 Коммерческие предложения не найдены")
                print("   ⚠️ Возможные причины:")
                print("   - В письме/вложениях действительно нет КП")
                print("   - Ошибка в промпте или обработке LLM")
                print("   - Формат КП не распознается")
            
            # Сохраняем результат для анализа
            output_file = Path("test_production_result.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Результат сохранен в {output_file}")
            
        else:
            print("❌ Ошибка обработки письма")
            
    except Exception as e:
        print(f"❌ Ошибка при обработке: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🏁 ТЕСТ ЗАВЕРШЕН")

if __name__ == "__main__":
    test_production_mode()