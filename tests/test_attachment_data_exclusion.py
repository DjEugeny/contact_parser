#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки исключения base64 данных вложений из поля body
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем src в путь
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from advanced_email_fetcher import AdvancedEmailFetcherV2
from email_loader import ProcessedEmailLoader

def test_attachment_data_exclusion():
    """🧪 Тест исключения base64 данных из поля body"""
    
    print("\n" + "="*60)
    print("🧪 ТЕСТ: Исключение base64 данных из поля body")
    print("="*60)
    
    # Инициализация
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Создаем фетчер
    from advanced_email_fetcher import setup_logging
    logger = setup_logging(logs_dir, datetime.now(), datetime.now())
    fetcher = AdvancedEmailFetcherV2(logger)
    
    # Загружаем письма за последние 3 дня для тестирования
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    
    print(f"📅 Загружаем письма с {start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}")
    
    try:
        emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
        
        if not emails:
            print("⚠️ Нет писем для тестирования")
            return
            
        print(f"📧 Найдено {len(emails)} писем")
        
        # Анализируем письма с вложениями
        emails_with_attachments = []
        for email in emails:
            if email.get('attachments') and len(email['attachments']) > 0:
                emails_with_attachments.append(email)
        
        print(f"📎 Писем с вложениями: {len(emails_with_attachments)}")
        
        if not emails_with_attachments:
            print("⚠️ Нет писем с вложениями для тестирования")
            return
            
        # Проверяем первые 3 письма с вложениями
        test_emails = emails_with_attachments[:3]
        
        for i, email in enumerate(test_emails, 1):
            print(f"\n📧 Письмо {i}:")
            print(f"   От: {email.get('from', 'N/A')[:50]}...")
            print(f"   Тема: {email.get('subject', 'N/A')[:60]}...")
            print(f"   Вложений: {len(email.get('attachments', []))}")
            
            body = email.get('body', '')
            body_length = len(body)
            
            print(f"   Размер body: {body_length:,} символов")
            
            # Проверяем наличие base64 данных в body
            base64_indicators = [
                'base64',
                'Content-Transfer-Encoding: base64',
                'iVBORw0KGgo',  # PNG signature
                '/9j/',  # JPEG signature
                'JVBERi0',  # PDF signature
                'UEsDBBQ'  # ZIP/DOCX signature
            ]
            
            found_base64 = []
            for indicator in base64_indicators:
                if indicator in body:
                    found_base64.append(indicator)
            
            if found_base64:
                print(f"   ❌ ОШИБКА: Найдены base64 данные в body: {found_base64}")
            else:
                print(f"   ✅ OK: base64 данные исключены из body")
            
            # Проверяем, что метаданные вложений сохранены
            attachments = email.get('attachments', [])
            for j, att in enumerate(attachments):
                print(f"     Вложение {j+1}: {att.get('filename', 'N/A')} ({att.get('size', 'N/A')} байт)")
                
                # Проверяем, что путь к файлу указан
                if att.get('saved_path'):
                    print(f"       ✅ Путь сохранения: {att['saved_path']}")
                else:
                    print(f"       ⚠️ Путь сохранения не указан")
        
        print(f"\n✅ Тест завершен. Проверено {len(test_emails)} писем с вложениями")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        fetcher.close()

def test_body_size_comparison():
    """🧪 Сравнение размеров body с включенными и исключенными вложениями"""
    
    print("\n" + "="*60)
    print("🧪 ТЕСТ: Сравнение размеров body")
    print("="*60)
    
    # Этот тест требует модификации кода для тестирования обеих опций
    print("⚠️ Для полного тестирования нужно временно изменить include_attachment_data=True")
    print("   и сравнить размеры body с текущей версией")

if __name__ == "__main__":
    test_attachment_data_exclusion()
    test_body_size_comparison()