#!/usr/bin/env python3
"""
🧪 Тестовый скрипт для проверки исправлений логики вложений
"""

import json
from pathlib import Path

def test_attachment_json_sync():
    """Проверяем синхронизацию информации о вложениях между JSON и файловой системой"""

    print("🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ ЛОГИКИ ВЛОЖЕНИЙ")
    print("=" * 60)

    # Проверяем конкретные файлы из примера пользователя
    test_cases = [
        {
            'json_path': 'data/emails/2025-06-02/email_006_20250602_20250602_dna-technology_ru_8e904fa9.json',
            'thread_id': '20250602_dna-technology_ru_8e904fa9',
            'expected_attachments': 1
        },
        {
            'json_path': 'data/emails/2025-06-02/email_007_20250602_20250602_dna-technology_ru_7cba8f23.json',
            'thread_id': '20250602_dna-technology_ru_7cba8f23',
            'expected_attachments': 1
        }
    ]

    for test_case in test_cases:
        json_path = Path(test_case['json_path'])
        thread_id = test_case['thread_id']
        expected_count = test_case['expected_attachments']

        print(f"\n📧 Проверка: {json_path.name}")
        print(f"   Thread-ID: {thread_id}")

        # Проверяем JSON файл
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                attachments = data.get('attachments', [])
                attachments_stats = data.get('attachments_stats', {})

                print(f"   📎 В JSON: {len(attachments)} вложений")
                print(f"   📊 Статистика: {attachments_stats}")

                if len(attachments) == 0:
                    print("   ❌ ПРОБЛЕМА: В JSON нет информации о вложениях!")
                else:
                    print("   ✅ JSON содержит информацию о вложениях")

            except Exception as e:
                print(f"   ❌ Ошибка чтения JSON: {e}")
        else:
            print("   ❌ JSON файл не найден")

        # Проверяем файлы вложений
        attachments_dir = Path('data/attachments/2025-06-02')
        if attachments_dir.exists():
            attachment_files = list(attachments_dir.glob(f"*{thread_id}*"))
            print(f"   📁 В файловой системе: {len(attachment_files)} файлов")

            for attachment_file in attachment_files:
                print(f"      - {attachment_file.name}")
        else:
            print("   ❌ Папка вложений не найдена")

if __name__ == '__main__':
    test_attachment_json_sync()
