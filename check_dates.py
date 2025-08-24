#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка количества писем по датам
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.append('src')

from email_loader import ProcessedEmailLoader

def main():
    loader = ProcessedEmailLoader()
    dates = loader.get_available_date_folders()
    
    print("📅 Проверка количества писем по датам:")
    print("=" * 50)
    
    for date in dates[-10:]:  # Последние 10 дат
        emails = loader.load_emails_by_date(date)
        print(f"{date}: {len(emails)} писем")
    
    # Найдем дату с наибольшим количеством писем
    max_emails = 0
    best_date = None
    
    for date in dates:
        emails = loader.load_emails_by_date(date)
        if len(emails) > max_emails:
            max_emails = len(emails)
            best_date = date
    
    print(f"\n🏆 Лучшая дата для тестирования: {best_date} ({max_emails} писем)")

if __name__ == '__main__':
    main()
