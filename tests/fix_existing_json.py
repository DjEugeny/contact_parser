#!/usr/bin/env python3
"""
🔧 Скрипт для исправления существующих JSON файлов писем
Добавляет информацию о вложениях, которые были скачаны, но не записаны в JSON
"""

import json
from pathlib import Path

def fix_json_attachments():
    """Исправляем существующие JSON файлы, добавляя информацию о вложениях"""

    print("🔧 ИСПРАВЛЕНИЕ СУЩЕСТВУЮЩИХ JSON ФАЙЛОВ")
    print("=" * 60)

    # Папки для обработки
    emails_base = Path('data/emails')
    attachments_base = Path('data/attachments')

    if not emails_base.exists():
        print("❌ Папка с письмами не найдена")
        return

    fixed_count = 0
    total_processed = 0

    # Обрабатываем все подпапки с датами
    for date_folder in sorted(emails_base.iterdir()):
        if not date_folder.is_dir():
            continue

        date_str = date_folder.name
        print(f"\n📅 Обработка даты: {date_str}")

        attachments_dir = attachments_base / date_str
        if not attachments_dir.exists():
            print(f"   📭 Папка вложений {date_str} не найдена, пропускаем")
            continue

        # Получаем все JSON файлы за эту дату
        json_files = list(date_folder.glob("*.json"))
        print(f"   📧 Найдено JSON файлов: {len(json_files)}")

        for json_file in json_files:
            total_processed += 1
            try:
                # Читаем JSON файл
                with open(json_file, 'r', encoding='utf-8') as f:
                    email_data = json.load(f)

                thread_id = email_data.get('thread_id', '')
                message_id = email_data.get('message_id', '')

                if not thread_id:
                    print(f"   ⚠️ Пропускаем {json_file.name} - нет thread_id")
                    continue

                # Ищем файлы вложений по thread_id
                attachment_pattern = f"*{thread_id}*"
                attachment_files = list(attachments_dir.glob(attachment_pattern))

                if not attachment_files:
                    # Проверяем, есть ли вообще файлы в папке даты
                    all_files_in_date = list(attachments_dir.glob("*"))
                    if all_files_in_date:
                        print(f"   📎 Для {json_file.name} вложений не найдено (всего файлов в папке: {len(all_files_in_date)})")
                    continue

                # Проверяем, есть ли уже информация о вложениях в JSON
                existing_attachments = email_data.get('attachments', [])
                existing_count = len(existing_attachments)

                if existing_count >= len(attachment_files):
                    print(f"   ✅ {json_file.name} уже содержит информацию о {existing_count} вложениях")
                    continue

                print(f"   🔧 Исправляем {json_file.name}: найдено {len(attachment_files)} файлов, в JSON {existing_count}")

                # Собираем информацию о вложениях
                attachments = []
                attachments_stats = {
                    'total': 0,
                    'saved': 0,
                    'excluded': 0,
                    'excluded_filenames': 0,
                    'excluded_by_size': 0,
                    'excluded_by_image_dimensions': 0,
                    'unsupported': 0,
                    'inline_images': 0
                }

                for attachment_file in attachment_files:
                    filename = attachment_file.name
                    file_size = attachment_file.stat().st_size

                    # Парсим имя файла для извлечения оригинального имени
                    # Формат: {thread_id}_{timestamp}_{type}_{original_filename}
                    parts = filename.split('_', 3)
                    if len(parts) >= 4:
                        original_filename = parts[3]
                        attachment_type = parts[2]
                    else:
                        original_filename = filename
                        attachment_type = 'unknown'

                    # Определяем, является ли это inline изображением
                    is_inline = 'inline' in attachment_type

                    attachment_info = {
                        'original_filename': original_filename,
                        'saved_filename': filename,
                        'file_path': str(attachment_file),
                        'relative_path': f"attachments/{date_str}/{filename}",
                        'file_size': file_size,
                        'file_type': attachment_file.suffix.lower().lstrip('.'),
                        'status': 'saved',
                        'is_inline': is_inline,
                        'saved_at': email_data.get('processed_at', 'unknown')
                    }

                    attachments.append(attachment_info)

                    if is_inline:
                        attachments_stats['inline_images'] += 1
                    attachments_stats['saved'] += 1

                attachments_stats['total'] = len(attachments)

                # Обновляем JSON файл
                email_data['attachments'] = attachments
                email_data['attachments_stats'] = attachments_stats

                # Сохраняем исправленный JSON
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(email_data, f, ensure_ascii=False, indent=2)

                print(f"   ✅ Исправлено: добавлено {len(attachments)} вложений")
                fixed_count += 1

            except Exception as e:
                print(f"   ❌ Ошибка обработки {json_file.name}: {e}")

    print("\n" + "=" * 60)
    print(f"📊 ИТОГИ ИСПРАВЛЕНИЯ:")
    print(f"   📧 Обработано файлов: {total_processed}")
    print(f"   ✅ Исправлено файлов: {fixed_count}")
    print(f"   📈 Процент исправленных: {fixed_count/total_processed*100:.1f}%" if total_processed > 0 else "0%")

if __name__ == '__main__':
    fix_json_attachments()
