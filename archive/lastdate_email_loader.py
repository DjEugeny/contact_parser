#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📧 Загрузчик обработанных писем для LLM анализа
"""

import json
import os
import re  # 🔧 ДОБАВЛЕНО
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, date


class ProcessedEmailLoader:
    """📬 Загрузчик писем из JSON файлов для LLM обработки"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data")
        self.emails_dir = self.data_dir / "emails"
        self.attachments_dir = self.data_dir / "attachments"
        
        print(f"📁 Инициализация загрузчика:")
        print(f"   📧 Письма: {self.emails_dir}")
        print(f"   📎 Вложения: {self.attachments_dir}")

    def get_available_date_folders(self) -> List[str]:
        """📅 Получение списка доступных папок с датами"""
        
        if not self.emails_dir.exists():
            return []
        
        date_folders = []
        for folder in self.emails_dir.iterdir():
            # 🔧 ИСПРАВЛЕНО: используем re.match() вместо folder.name.match()
            if folder.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', folder.name):
                date_folders.append(folder.name)
        
        return sorted(date_folders)

    def load_emails_by_date(self, target_date: str) -> List[Dict]:
        """📧 Загрузка всех писем за конкретную дату"""
        
        date_folder = self.emails_dir / target_date
        if not date_folder.exists():
            print(f"❌ Папка с датой не найдена: {target_date}")
            return []
        
        emails = []
        json_files = list(date_folder.glob("email_*.json"))
        
        print(f"📧 Загрузка писем за {target_date}: найдено {len(json_files)} файлов")
        
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    email_data = json.load(f)
                    email_data['json_file_path'] = str(json_file)
                    emails.append(email_data)
            except Exception as e:
                print(f"❌ Ошибка загрузки {json_file.name}: {e}")
                continue
        
        print(f"✅ Успешно загружено: {len(emails)} писем")
        return emails

    def load_emails_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """📅 Загрузка писем за диапазон дат"""
        
        all_emails = []
        available_dates = self.get_available_date_folders()
        
        # Фильтруем даты по диапазону
        target_dates = [d for d in available_dates if start_date <= d <= end_date]
        
        if not target_dates:
            print(f"❌ Нет писем в диапазоне {start_date} - {end_date}")
            return []
        
        print(f"📅 Загрузка писем за период {start_date} - {end_date}")
        print(f"   Найдены даты: {target_dates}")
        
        for target_date in target_dates:
            date_emails = self.load_emails_by_date(target_date)
            all_emails.extend(date_emails)
        
        print(f"📊 ИТОГО загружено писем: {len(all_emails)}")
        return all_emails

    def get_emails_with_attachments(self, emails: List[Dict]) -> List[Dict]:
        """📎 Фильтрация писем с вложениями"""
        
        emails_with_attachments = []
        
        for email in emails:
            if email.get('attachments') and len(email['attachments']) > 0:
                emails_with_attachments.append(email)
        
        print(f"📎 Писем с вложениями: {len(emails_with_attachments)} из {len(emails)}")
        return emails_with_attachments

    def get_attachment_file_path(self, email: Dict, attachment: Dict) -> Path:
        """📎 Получение полного пути к файлу вложения"""
        
        attachment_path = Path(attachment.get('file_path', ''))
        
        if attachment_path.exists():
            return attachment_path
        
        # Попробуем построить путь из relative_path
        if attachment.get('relative_path'):
            full_path = self.data_dir / attachment['relative_path']
            if full_path.exists():
                return full_path
        
        # Последняя попытка через saved_filename и дату
        date_folder = email.get('date_folder', '')
        if date_folder and attachment.get('saved_filename'):
            constructed_path = self.attachments_dir / date_folder / attachment['saved_filename']
            if constructed_path.exists():
                return constructed_path
        
        return None

    def print_email_summary(self, emails: List[Dict]):
        """📊 Краткая сводка по загруженным письмам"""
        
        if not emails:
            print("📭 Нет писем для анализа")
            return
        
        print(f"\n📊 СВОДКА ПО ЗАГРУЖЕННЫМ ПИСЬМАМ:")
        print(f"{'='*50}")
        print(f"📧 Всего писем: {len(emails)}")
        
        # Статистика по вложениям
        total_attachments = sum(len(email.get('attachments', [])) for email in emails)
        emails_with_attachments = len([e for e in emails if e.get('attachments')])
        
        print(f"📎 Писем с вложениями: {emails_with_attachments}")
        print(f"📎 Всего вложений: {total_attachments}")
        
        # Статистика по отправителям
        senders = {}
        for email in emails:
            sender_domain = email.get('from', '').split('@')[-1] if '@' in email.get('from', '') else 'unknown'
            senders[sender_domain] = senders.get(sender_domain, 0) + 1
        
        print(f"📨 Уникальных доменов отправителей: {len(senders)}")
        
        # ТОП-3 домена
        top_domains = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:3]
        for domain, count in top_domains:
            print(f"   • {domain}: {count} писем")
        
        # Общий объем текста
        total_chars = sum(email.get('char_count', 0) for email in emails)
        estimated_tokens = total_chars // 3  # Приблизительно для русского
        
        print(f"📝 Общий объем текста: {total_chars:,} символов")
        print(f"🎯 Примерные токены: {estimated_tokens:,}")
        
        print(f"{'='*50}")


def main():
    """🧪 Тестирование загрузчика писем"""
    
    print("📧 ТЕСТИРОВАНИЕ ЗАГРУЗЧИКА ОБРАБОТАННЫХ ПИСЕМ")
    print("="*60)
    
    loader = ProcessedEmailLoader()
    
    # Показываем доступные даты
    available_dates = loader.get_available_date_folders()
    print(f"📅 Доступные даты: {available_dates}")
    
    if not available_dates:
        print("❌ Нет обработанных писем для тестирования")
        print("   Сначала запустите advanced_email_fetcher_v2_fixed.py")
        return
    
    # Загружаем письма за последнюю доступную дату
    latest_date = available_dates[-1]
    print(f"\n🎯 Тестируем загрузку за {latest_date}...")
    
    emails = loader.load_emails_by_date(latest_date)
    
    if emails:
        loader.print_email_summary(emails)
        
        # Показываем примеры писем
        print(f"\n📋 ПРИМЕРЫ ЗАГРУЖЕННЫХ ПИСЕМ:")
        for i, email in enumerate(emails[:3], 1):
            print(f"   {i}. От: {email.get('from', 'N/A')[:50]}...")
            print(f"      Тема: {email.get('subject', 'N/A')[:60]}...")
            print(f"      Символов: {email.get('char_count', 0)}")
            
            attachments = email.get('attachments', [])
            if attachments:
                print(f"      Вложения ({len(attachments)}):")
                for att in attachments:
                    file_path = loader.get_attachment_file_path(email, att)
                    status = "✅" if file_path and file_path.exists() else "❌"
                    print(f"        {status} {att.get('original_filename', 'N/A')}")
    
    else:
        print("❌ Не удалось загрузить письма")


if __name__ == '__main__':
    main()
