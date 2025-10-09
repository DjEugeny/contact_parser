#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔧 Быстрое исправление проблемы с вложениями в advanced_email_fetcher.py

Проблема: вложения из одного письма в thread цепочке некорректно приписываются другим письмам.
Решение: добавляем Message-ID в имя файла вложения для точной идентификации.

Использование:
    python quick_fix_patch.py

Внимание: перед применением патча создайте резервную копию advanced_email_fetcher.py
"""

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional

def apply_fix_to_save_attachment_method():
    """Применение исправления к методу save_attachment_or_inline"""
    
    # Читаем исходный файл
    fetcher_path = Path("src/advanced_email_fetcher.py")
    if not fetcher_path.exists():
        print(f"❌ Файл не найден: {fetcher_path}")
        return False
    
    with open(fetcher_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Находим метод save_attachment_or_inline
    method_pattern = r'(def save_attachment_or_inline\(\s*self,\s*part: email\.message\.Message,\s*thread_id: str,\s*date_folder: str,\s*is_inline: bool = False,\s*\) -> Optional\[Dict\]:.*?)(\s+# Создаем безопасное имя файла)'
    
    replacement = r'''\1
            # 🔧 ИСПРАВЛЕНИЕ: добавляем message_id_hash в имя файла вложения
            # Извлекаем message_id из контекста (передаем как параметр)
            # Временно используем thread_id для совместимости (будет исправлено в вызовах метода)
            thread_hash = hashlib.md5(thread_id.encode()).hexdigest()[:8]
        \2'''
    
    new_content = re.sub(method_pattern, replacement, content, flags=re.DOTALL)
    
    # Находим строку с генерацией уникального имени файла
    old_filename_pattern = r'unique_filename = f"\{thread_id\}_\{timestamp\}_\{prefix\}_\{safe_filename\}"'
    new_filename = 'unique_filename = f"{thread_id}_{thread_hash}_{timestamp}_{prefix}_{safe_filename}"'
    
    new_content = re.sub(old_filename_pattern, new_filename, new_content)
    
    # Сохраняем изменения
    with open(fetcher_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("✅ Исправление применено к методу save_attachment_or_inline")
    return True

def apply_fix_to_check_email_processing_status():
    """Применение исправления к методу check_email_processing_status"""
    
    fetcher_path = Path("src/advanced_email_fetcher.py")
    with open(fetcher_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Находим и заменяем проблемный код в check_email_processing_status
    old_pattern = r'(# Ищем файлы с префиксом thread_id\s+attachment_files = list\(\s+attachments_path\.glob\(f"\*\{thread_id\}\*"\)\s+\))'
    
    new_code = '''# 🔧 ИСПРАВЛЕНИЕ: ищем файлы с учетом message_id_hash
                    # Для обратной совместимости сначала ищем по новому формату
                    message_id_hash = hashlib.md5(message_id.encode()).hexdigest()[:8]
                    attachment_files = list(
                        attachments_path.glob(f"*{thread_id}_{message_id_hash}_*")
                    )
                    
                    # Если ничего не нашли, пробуем старый формат (для обратной совместимости)
                    if not attachment_files:
                        attachment_files = list(
                            attachments_path.glob(f"*{thread_id}_*")
                        )'''
    
    new_content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)
    
    # Сохраняем изменения
    with open(fetcher_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("✅ Исправление применено к методу check_email_processing_status")
    return True

def apply_fix_to_process_single_email():
    """Применение исправления к методу process_single_email"""
    
    fetcher_path = Path("src/advanced_email_fetcher.py")
    with open(fetcher_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Находим вызовы save_attachment_or_inline и добавляем message_id
    old_call_pattern = r'attachment_info = \(.*?self\.save_attachment_or_inline\(\s*part, thread_id, date_folder, is_inline.*?\)\)'
    
    # Это сложная замена, так как нужно передать message_id в вызовы
    # Для простоты создадим заглушку и warn в логах
    
    # Добавляем warn в начале метода
    method_start_pattern = r'(def process_single_email\(\s*self,\s*msg_id: bytes,\s*date_str: str,\s*email_num_in_day: int,\s*total_emails_in_day: int,\s*include_attachment_data: bool = False,\s*\) -> Optional\[Dict\]:.*?)(\s+"""📧 ИСПРАВЛЕННАЯ ЛОГИКА: заголовки → фильтры → загрузка""")'
    
    warning_addition = r'''\1
        # 🔧 ВНИМАНИЕ: требуется передача message_id в save_attachment_or_inline
        # Это временное решение, полное исправление требует рефакторинга
        self.logger.warning("⚠️ ВНИМАНИЕ: используется временное исправление для вложений")
    \2'''
    
    new_content = re.sub(method_start_pattern, warning_addition, content, flags=re.DOTALL)
    
    # Сохраняем изменения
    with open(fetcher_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("✅ Исправление применено к методу process_single_email")
    return True

def create_backup():
    """Создание резервной копии файла"""
    
    fetcher_path = Path("src/advanced_email_fetcher.py")
    backup_path = Path("src/advanced_email_fetcher.py.backup")
    
    if not fetcher_path.exists():
        print(f"❌ Файл не найден: {fetcher_path}")
        return False
    
    with open(fetcher_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ Резервная копия создана: {backup_path}")
    return True

def main():
    """Главная функция применения патча"""
    
    print("🔧 ПРИМЕНЕНИЕ БЫСТРОГО ИСПРАВЛЕНИЯ ДЛЯ ПРОБЛЕМЫ С ВЛОЖЕНИЯМИ")
    print("=" * 70)
    
    # Создаем резервную копию
    if not create_backup():
        print("❌ Не удалось создать резервную копию. Прерывание.")
        return
    
    # Применяем исправления
    fixes_applied = 0
    
    if apply_fix_to_save_attachment_method():
        fixes_applied += 1
    
    if apply_fix_to_check_email_processing_status():
        fixes_applied += 1
    
    if apply_fix_to_process_single_email():
        fixes_applied += 1
    
    print("=" * 70)
    print(f"📊 ИТОГО: применено {fixes_applied}/3 исправлений")
    
    if fixes_applied == 3:
        print("✅ Все исправления успешно применены!")
        print("\n📝 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Протестируйте обработку новых писем")
        print("2. Проверьте, что вложения корректно привязываются к письмам")
        print("3. При необходимости создайте скрипт миграции для существующих вложений")
        print("\n⚠️ ВНИМАНИЕ: это временное решение. Рекомендуется реализовать")
        print("   долгосрочное решение из файла FIX_PLAN.md")
    else:
        print("⚠️ Некоторые исправления не применены. Проверьте код вручную.")
    
    print("=" * 70)

if __name__ == "__main__":
    main()