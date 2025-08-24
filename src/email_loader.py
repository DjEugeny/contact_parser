#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📧 Загрузчик обработанных писем v1.1 с исправлением ошибок
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ProcessedEmailLoader:
    """📧 Загрузчик обработанных писем"""
    
    def __init__(self):
        # Используем абсолютные пути относительно корня проекта
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        self.data_dir = project_root / "data"
        self.emails_dir = self.data_dir / "emails"
        self.attachments_dir = self.data_dir / "attachments"
        
        print("📁 Инициализация загрузчика:")
        print(f"   📧 Письма: {self.emails_dir}")
        print(f"   📎 Вложения: {self.attachments_dir}")

    def get_available_date_folders(self) -> List[str]:
        """📅 Получение списка доступных дат"""
        
        if not self.emails_dir.exists():
            return []
        
        date_folders = []
        for folder in self.emails_dir.iterdir():
            if folder.is_dir() and folder.name.count('-') == 2:  # Формат YYYY-MM-DD
                date_folders.append(folder.name)
        
        return sorted(date_folders)

    def load_emails_by_date(self, date: str) -> List[Dict]:
        """📧 Загрузка писем за конкретную дату"""
        
        date_folder = self.emails_dir / date
        
        if not date_folder.exists():
            print(f"❌ Папка {date} не найдена")
            return []
        
        emails = []
        json_files = list(date_folder.glob("email_*.json"))
        
        print(f"📧 Загрузка писем за {date}: найдено {len(json_files)} файлов")
        
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    email_data = json.load(f)
                    emails.append(email_data)
            except Exception as e:
                print(f"❌ Ошибка загрузки {json_file}: {e}")
        
        print(f"✅ Успешно загружено: {len(emails)} писем")
        return emails

    def load_all_emails(self) -> Dict[str, List[Dict]]:
        """📧 Загрузка ВСЕХ писем по всем датам"""
        
        available_dates = self.get_available_date_folders()
        all_emails = {}
        
        print(f"📅 Загрузка писем за все доступные даты: {len(available_dates)}")
        
        for date in available_dates:
            emails = self.load_emails_by_date(date)
            if emails:
                all_emails[date] = emails
                
        total_emails = sum(len(emails) for emails in all_emails.values())
        print(f"✅ Загружено {total_emails} писем за {len(all_emails)} дат")
        
        return all_emails

    def get_emails_with_attachments(self, emails: List[Dict]) -> List[Dict]:
        """📎 Фильтрация писем только с вложениями"""
        
        emails_with_attachments = []
        
        for email in emails:
            attachments = email.get('attachments', [])
            # 🆕 ИСПРАВЛЕНИЕ: Проверяем только успешно скачанные вложения
            downloaded_attachments = [
                att for att in attachments 
                if att.get('status') == 'saved' and att.get('file_path')
            ]
            
            if downloaded_attachments:
                emails_with_attachments.append(email)
        
        return emails_with_attachments

    def get_attachment_file_path(self, email: Dict, attachment: Dict) -> Optional[Path]:
        """📎 Получение полного пути к файлу вложения с исправлением ошибок"""
        
        # 🆕 ИСПРАВЛЕНИЕ: Проверяем что file_path не None
        file_path_str = attachment.get('file_path')
        if file_path_str:
            attachment_path = Path(file_path_str)
            if attachment_path.exists():
                return attachment_path
        
        # 🆕 Попробуем найти по relative_path
        relative_path = attachment.get('relative_path')
        if relative_path:
            full_path = self.data_dir / relative_path
            if full_path.exists():
                return full_path
        
        # 🆕 Последняя попытка через date_folder из письма
        date_folder = email.get('date_folder', '')
        saved_filename = attachment.get('saved_filename')
        
        if date_folder and saved_filename:
            constructed_path = self.attachments_dir / date_folder / saved_filename
            if constructed_path.exists():
                return constructed_path
        
        print(f"⚠️ Файл вложения не найден: {attachment.get('original_filename', 'неизвестно')}")
        return None

    def print_summary(self, emails: List[Dict]):
        """📊 Печать сводной информации"""
        
        print(f"\n📊 СВОДКА ПО ЗАГРУЖЕННЫМ ПИСЬМАМ:")
        print(f"{'='*50}")
        print(f"📧 Всего писем: {len(emails)}")
        
        emails_with_attachments = self.get_emails_with_attachments(emails)
        print(f"📎 Писем с вложениями: {len(emails_with_attachments)}")
        
        total_attachments = sum(len([att for att in email.get('attachments', []) if att.get('status') == 'saved']) for email in emails)
        print(f"📎 Всего вложений: {total_attachments}")
        
        # Анализ доменов отправителей
        domains = {}
        for email in emails:
            from_addr = email.get('from', '')
            if '@' in from_addr:
                domain = from_addr.split('@')[-1].split('>')[0]
                domains[domain] = domains.get(domain, 0) + 1
        
        print(f"📨 Уникальных доменов отправителей: {len(domains)}")
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {domain}>: {count} писем")
        
        total_chars = sum(email.get('char_count', 0) for email in emails)
        print(f"📝 Общий объем текста: {total_chars:,} символов")
        print(f"🎯 Примерные токены: {total_chars // 3:,}")


def main():
    """🧪 Тестирование загрузчика с одной датой"""
    
    print("📧 ТЕСТИРОВАНИЕ ЗАГРУЗЧИКА ОБРАБОТАННЫХ ПИСЕМ")
    print("="*60)
    
    loader = ProcessedEmailLoader()
    
    available_dates = loader.get_available_date_folders()
    print(f"📅 Доступные даты: {available_dates}")
    
    if available_dates:
        # Тестируем на последней дате
        target_date = available_dates[-1]
        print(f"\n🎯 Тестируем загрузку за {target_date}...")
        
        emails = loader.load_emails_by_date(target_date)
        loader.print_summary(emails)


if __name__ == '__main__':
    main()
