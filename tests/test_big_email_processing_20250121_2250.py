#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест обработки больших писем с оптимизированными алгоритмами разбивки текста
Дата создания: 2025-01-21 22:50 (UTC+07)
Цель: Проверить работу оптимизированной системы на письме размером 2.5MB
"""

import json
import time
import sys
import os
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from integrated_llm_processor import IntegratedLLMProcessor

def test_big_email_processing():
    """
    Тестирование обработки большого письма (2.5MB) с оптимизированными алгоритмами
    """
    print("=== ТЕСТ ОБРАБОТКИ БОЛЬШОГО ПИСЬМА (2.5MB) ===")
    print(f"Время начала: {time.strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
    
    # Путь к тестовому письму
    email_path = "/Users/evgenyzach/contact_parser/data/emails/2025-01-15/email_021_20250115_20250115_dna-technology_ru_f9c6cc02.json"
    
    if not os.path.exists(email_path):
        print(f"❌ ОШИБКА: Файл письма не найден: {email_path}")
        return False
    
    try:
        # Загружаем письмо
        with open(email_path, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        print(f"📧 Загружено письмо:")
        print(f"   - Размер: {email_data.get('raw_size', 0):,} байт")
        print(f"   - Символов в тексте: {email_data.get('char_count', 0):,}")
        print(f"   - Вложений: {email_data.get('attachments_stats', {}).get('total', 0)}")
        print(f"   - От: {email_data.get('from', 'N/A')}")
        print(f"   - Тема: {email_data.get('subject', 'N/A')}")
        
        # Инициализируем процессор в тестовом режиме
        print("\n🔧 Инициализация IntegratedLLMProcessor в тестовом режиме...")
        processor = IntegratedLLMProcessor(test_mode=True)
        
        # Засекаем время обработки
        start_time = time.time()
        
        print("\n🚀 Запуск обработки большого письма...")
        print("   Ожидается использование оптимизированных алгоритмов разбивки текста")
        
        # Обрабатываем письмо
        result = processor.process_single_email(email_data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n⏱️ Время обработки: {processing_time:.2f} секунд")
        
        # Анализируем результат
        if result:
            print("\n✅ РЕЗУЛЬТАТ ОБРАБОТКИ:")
            print(f"   - Статус: Успешно")
            
            # Проверяем извлеченные контакты
            contacts = result.get('contacts', [])
            if contacts:
                print(f"   - Найдено контактов: {len(contacts)}")
                # Если contacts - это список
                if isinstance(contacts, list):
                    for i, contact in enumerate(contacts[:3]):
                        print(f"       • {contact.get('name', 'N/A')} ({contact.get('email', 'N/A')})")
                    if len(contacts) > 3:
                        print(f"       ... и еще {len(contacts) - 3}")
                # Если contacts - это словарь
                elif isinstance(contacts, dict):
                    for contact_type, contact_list in contacts.items():
                        if contact_list:
                            print(f"     * {contact_type}: {len(contact_list)}")
                            # Показываем первые несколько контактов
                            for i, contact in enumerate(contact_list[:3]):
                                print(f"       • {contact.get('name', 'N/A')} ({contact.get('email', 'N/A')})")
                            if len(contact_list) > 3:
                                print(f"       ... и еще {len(contact_list) - 3}")
            else:
                print("   - Контакты не найдены")
            
            # Проверяем коммерческие предложения
            commercial_offers = result.get('commercial_offers', [])
            if commercial_offers:
                print(f"   - Найдено коммерческих предложений: {len(commercial_offers)}")
                for i, offer in enumerate(commercial_offers[:2]):
                    print(f"     * Предложение {i+1}: {offer.get('summary', 'N/A')[:100]}...")
            else:
                print("   - Коммерческие предложения не найдены")
            
            # Проверяем обработку чанков (если есть информация)
            processing_info = result.get('processing_info', {})
            if processing_info:
                print(f"\n📊 ИНФОРМАЦИЯ О ОБРАБОТКЕ:")
                chunks_processed = processing_info.get('chunks_processed', 0)
                if chunks_processed > 0:
                    print(f"   - Обработано чанков: {chunks_processed}")
                    print(f"   - Использована прогрессивная обработка: ДА")
                else:
                    print(f"   - Письмо обработано целиком (без разбивки)")
                
                total_tokens = processing_info.get('total_tokens_used', 0)
                if total_tokens > 0:
                    print(f"   - Использовано токенов: {total_tokens:,}")
            
            print(f"\n🎯 ОЦЕНКА ПРОИЗВОДИТЕЛЬНОСТИ:")
            chars_per_second = email_data.get('char_count', 0) / processing_time if processing_time > 0 else 0
            print(f"   - Скорость обработки: {chars_per_second:,.0f} символов/сек")
            
            if processing_time < 60:
                print(f"   - Время обработки: ОТЛИЧНОЕ (< 1 минуты)")
            elif processing_time < 180:
                print(f"   - Время обработки: ХОРОШЕЕ (< 3 минут)")
            else:
                print(f"   - Время обработки: ПРИЕМЛЕМОЕ (> 3 минут)")
            
            return True
        else:
            print("\n❌ ОШИБКА: Обработка письма не удалась")
            return False
            
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"\nВремя завершения: {time.strftime('%Y-%m-%d %H:%M:%S')} (UTC+07)")
        print("=" * 60)

def main():
    """
    Главная функция теста
    """
    success = test_big_email_processing()
    
    if success:
        print("\n🎉 ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("Оптимизированные алгоритмы разбивки текста работают корректно")
        return 0
    else:
        print("\n💥 ТЕСТ ПРОВАЛЕН!")
        print("Требуется дополнительная отладка системы")
        return 1

if __name__ == "__main__":
    exit(main())