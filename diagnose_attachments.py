#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔍 Диагностика проблемы с вложениями в API Pipeline Validator"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api_pipeline_validator import APIPipelineValidator
from argparse import Namespace


def diagnose_email_attachments(email_file: Path) -> Dict[str, Any]:
    """🔍 Диагностирует проблему с вложениями для конкретного письма"""
    print(f"\n{'='*60}")
    print(f"🔍 ДИАГНОСТИКА ПИСЬМА: {email_file.name}")
    print(f"{'='*60}")
    
    if not email_file.exists():
        print(f"❌ Файл письма не найден: {email_file}")
        return {"error": "Файл не найден"}
    
    # Читаем данные письма
    try:
        with email_file.open("r", encoding="utf-8") as f:
            email_data = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения файла письма: {e}")
        return {"error": f"Ошибка чтения: {e}"}
    
    # Анализируем структуру письма
    print(f"📧 Основная информация:")
    print(f"   От: {email_data.get('from', 'Не указано')}")
    print(f"   Тема: {email_data.get('subject', 'Без темы')}")
    print(f"   Дата: {email_data.get('date', 'Не указана')}")
    print(f"   Thread ID: {email_data.get('thread_id', 'Не указан')}")
    
    # Проверяем текст письма
    body = email_data.get('body', '')
    print(f"\n📝 Текст письма:")
    print(f"   Длина: {len(body)} символов")
    if body:
        preview = body[:200].replace('\n', ' ')
        print(f"   Превью: {preview}...")
    else:
        print(f"   ⚠️ Текст письма отсутствует!")
    
    # Анализируем вложения
    attachments = email_data.get('attachments', [])
    print(f"\n📎 Анализ вложений:")
    print(f"   Количество: {len(attachments)}")
    
    if not attachments:
        print(f"   ⚠️ Вложения отсутствуют!")
        return {
            "email_file": str(email_file),
            "body_length": len(body),
            "attachments_count": 0,
            "issues": ["Нет вложений"]
        }
    
    issues = []
    attachment_analysis = []
    
    for i, attachment in enumerate(attachments, 1):
        print(f"\n   📎 Вложение {i}:")
        att_info = {
            "index": i,
            "original_filename": attachment.get('original_filename', 'Неизвестно'),
            "status": attachment.get('status', 'Неизвестно')
        }
        
        print(f"      Файл: {att_info['original_filename']}")
        print(f"      Статус: {att_info['status']}")
        
        # Проверяем пути к файлам
        file_path = attachment.get('file_path') or attachment.get('relative_path')
        att_info['file_path'] = file_path
        
        if file_path:
            print(f"      Путь: {file_path}")
            
            # Проверяем существование файла
            attachment_path = Path(file_path)
            if not attachment_path.is_absolute():
                attachment_path = PROJECT_ROOT / file_path
                
            if attachment_path.exists():
                print(f"      ✅ Файл существует")
                print(f"      Размер: {attachment_path.stat().st_size} байт")
                att_info['file_exists'] = True
                att_info['file_size'] = attachment_path.stat().st_size
            else:
                print(f"      ❌ Файл НЕ существует: {attachment_path}")
                att_info['file_exists'] = False
                issues.append(f"Файл вложения {i} не найден: {attachment_path}")
        else:
            print(f"      ❌ Путь к файлу НЕ указан")
            att_info['file_exists'] = False
            issues.append(f"У вложения {i} отсутствует путь к файлу")
        
        # Проверяем готовый текст
        content = attachment.get('content')
        if content and isinstance(content, str) and content.strip():
            print(f"      ✅ Есть извлеченный текст: {len(content)} символов")
            preview = content[:100].replace('\n', ' ')
            print(f"      Превью: {preview}...")
            att_info['has_content'] = True
            att_info['content_length'] = len(content)
        else:
            print(f"      ❌ Извлеченный текст отсутствует")
            att_info['has_content'] = False
            if att_info['file_exists']:
                issues.append(f"У вложения {i} нет извлеченного текста, хотя файл существует")
        
        attachment_analysis.append(att_info)
    
    return {
        "email_file": str(email_file),
        "body_length": len(body),
        "attachments_count": len(attachments),
        "attachments": attachment_analysis,
        "issues": issues
    }


def test_compose_combined_text(email_file: Path) -> str:
    """🧪 Тестирует метод _compose_combined_text"""
    print(f"\n{'='*60}")
    print(f"🧪 ТЕСТИРОВАНИЕ _compose_combined_text")
    print(f"{'='*60}")
    
    # Создаем экземпляр валидатора
    dummy_args = Namespace(
        mode="test",
        date=None,
        count=None,
        start_date=None,
        end_date=None,
        dry_run=True
    )
    
    validator = APIPipelineValidator(dummy_args)
    
    # Читаем данные письма
    with email_file.open("r", encoding="utf-8") as f:
        email_data = json.load(f)
    
    # Извлекаем дату из имени файла
    date = validator._extract_date_from_filename(email_file.name)
    print(f"📅 Извлеченная дата: {date}")
    
    # Тестируем объединение текста
    combined_text = validator._compose_combined_text(email_data, date)
    
    print(f"📝 Результат объединения:")
    print(f"   Общая длина: {len(combined_text)} символов")
    
    # Анализируем содержимое
    has_email_section = "=== ТЕКСТ ПИСЬМА ===" in combined_text
    has_attachment_section = "=== ВЛОЖЕНИЕ" in combined_text
    
    print(f"   Содержит секцию письма: {'✅' if has_email_section else '❌'}")
    print(f"   Содержит секции вложений: {'✅' if has_attachment_section else '❌'}")
    
    # Показываем превью
    if combined_text:
        print(f"\n📄 Первые 500 символов объединенного текста:")
        print(f"   {'-'*50}")
        preview = combined_text[:500]
        print(f"   {preview}")
        if len(combined_text) > 500:
            print(f"   ... (еще {len(combined_text) - 500} символов)")
        print(f"   {'-'*50}")
    
    return combined_text


def main():
    """🎯 Главная функция диагностики"""
    print("🔍 ДИАГНОСТИКА ПРОБЛЕМЫ С ВЛОЖЕНИЯМИ")
    print("=" * 60)
    
    # Ищем файлы писем за 2025-07-09
    emails_dir = PROJECT_ROOT / "data" / "emails" / "2025-07-09"
    
    if not emails_dir.exists():
        print(f"❌ Директория с письмами не найдена: {emails_dir}")
        return
    
    email_files = list(emails_dir.glob("email_*.json"))
    if not email_files:
        print(f"❌ Файлы писем не найдены в: {emails_dir}")
        return
    
    print(f"📧 Найдено {len(email_files)} файлов писем")
    
    # Диагностируем каждое письмо
    all_issues = []
    
    for email_file in sorted(email_files)[:3]:  # Ограничиваемся первыми 3 для тестирования
        diagnosis = diagnose_email_attachments(email_file)
        all_issues.extend(diagnosis.get('issues', []))
        
        # Тестируем объединение текста
        combined_text = test_compose_combined_text(email_file)
        
        if len(combined_text) < 1000:
            all_issues.append(f"Объединенный текст очень короткий ({len(combined_text)} символов) для {email_file.name}")
    
    # Общий анализ проблем
    print(f"\n{'='*60}")
    print(f"📊 ОБЩИЙ АНАЛИЗ ПРОБЛЕМ")
    print(f"{'='*60}")
    
    if all_issues:
        print(f"❌ Обнаружено {len(all_issues)} проблем:")
        for i, issue in enumerate(all_issues, 1):
            print(f"   {i}. {issue}")
    else:
        print(f"✅ Проблем не обнаружено!")
    
    # Рекомендации по исправлению
    print(f"\n🔧 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
    print(f"1. Проверить, правильно ли извлекается текст из PDF-файлов")
    print(f"2. Убедиться, что OCR manager работает корректно")
    print(f"3. Проверить пути к файлам вложений")
    print(f"4. Добавить отладочную печать в _get_attachment_text")


if __name__ == "__main__":
    main()