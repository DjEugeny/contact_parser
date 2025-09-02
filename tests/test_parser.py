#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def test_parser():
    """Тестируем парсер имен файлов"""

    test_files = [
        "20250721_mail_ru_3e6a56b8_033842_attach_IMG-20250721-WA0003.txt",
        "20250721_mail_ru_3e6a56b8_083944_attach_IMG-20250721-WA0003.txt",
        "20250721_mail_ru_fd4716d7_033848_attach_BRAF 9_Вкладыш S_v.2_ПРОЕКТ.txt",
        "20250721_mail_ru_fd4716d7_084003_attach_BRAF 9_Вкладыш S_v.2_ПРОЕКТ.txt"
    ]

    # Исправленный паттерн: date_domain_threadid_timestamp_attach_filename.txt
    # Пример: 20250721_mail_ru_3e6a56b8_033842_attach_IMG-20250721-WA0003.txt
    pattern = r'(\d{8})_(.+?)_([^_]+)_([^_]+)_attach_(.+)\.txt$'

    print(f"Паттерн: {pattern}")

    for filename in test_files:
        print(f"\n🔍 Тестируем: {filename}")
        match = re.match(pattern, filename)

        if match:
            date, domain, thread_id, timestamp, original_name = match.groups()
            print(f"  ✅ Распарсено:")
            print(f"    Дата: {date}")
            print(f"    Домен: {domain}")
            print(f"    Thread ID: {thread_id}")
            print(f"    Timestamp: {timestamp}")
            print(f"    Оригинальное имя: {original_name}")
            print(f"    Ключ: {date}_{domain}_{original_name}")
        else:
            print(f"  ❌ Не распарсено")

if __name__ == '__main__':
    test_parser()
