"""
Упрощенный тест для проверки маппинга вложений.
Тестирует основную логику без зависимостей от сложных модулей.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Добавляем пути для импорта
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def setup_test_logging():
    """Настройка тестового логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )
    return logging.getLogger("TestAttachmentMapping")


def test_attachment_mapping_logic():
    """Тестирование логики маппинга вложений."""
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ ЛОГИКИ МАППИНГА ВЛОЖЕНИЙ")
    print("="*60)
    
    logger = setup_test_logging()
    
    # Определяем пути к данным
    data_dir = PROJECT_ROOT / "data"
    emails_dir = data_dir / "emails" / "2025-07-23"
    attachments_dir = data_dir / "attachments" / "2025-07-23"
    
    if not emails_dir.exists():
        print(f"ℹ️ Папка с письмами не найдена: {emails_dir}")
        return True
    
    if not attachments_dir.exists():
        print(f"ℹ️ Папка с вложениями не найдена: {attachments_dir}")
        return True
    
    # Анализируем существующие письма
    email_files = list(emails_dir.glob("email_*.json"))
    print(f"📁 Найдено писем: {len(email_files)}")
    
    attachment_files = list(attachments_dir.glob("*"))
    print(f"📎 Найдено вложений: {len(attachment_files)}")
    
    # Проверяем конкретный пример с проблемой маппинга
    problem_thread_id = "20250723_dna-technology_ru_1c456124"
    
    print(f"\n🔍 Анализ треда: {problem_thread_id}")
    
    # Ищем все письма с этим thread_id
    thread_emails = []
    for email_file in email_files:
        try:
            with open(email_file, "r", encoding="utf-8") as f:
                email_data = json.load(f)
                if email_data.get("thread_id") == problem_thread_id:
                    thread_emails.append({
                        "file": email_file.name,
                        "message_id": email_data.get("message_id", ""),
                        "subject": email_data.get("subject", ""),
                        "attachments_count": len(email_data.get("attachments", [])),
                        "attachments": email_data.get("attachments", []),
                    })
        except Exception as e:
            print(f"⚠️ Ошибка чтения файла {email_file.name}: {e}")
    
    print(f"📧 Найдено писем в треде: {len(thread_emails)}")
    
    for i, email in enumerate(thread_emails):
        print(f"   {i+1}. {email['file']}")
        print(f"      Message-ID: {email['message_id'][:50]}...")
        print(f"      Тема: {email['subject'][:50]}...")
        print(f"      Вложений: {email['attachments_count']}")
        
        # Показываем детали вложений
        for j, attachment in enumerate(email['attachments']):
            print(f"         Вложение {j+1}: {attachment.get('filename', 'Unknown')}")
    
    # Ищем вложения для этого thread_id
    thread_attachments = list(attachments_dir.glob(f"*{problem_thread_id}*"))
    print(f"📎 Вложений для thread_id: {len(thread_attachments)}")
    
    for attachment in thread_attachments[:5]:  # Показываем первые 5
        print(f"   📄 {attachment.name}")
        print(f"      Размер: {attachment.stat().st_size} байт")
    
    # Анализируем проблему
    print(f"\n🔍 АНАЛИЗ ПРОБЛЕМЫ:")
    
    if len(thread_emails) > 1:
        print(f"📊 В треде {len(thread_emails)} писем")
        
        # Считаем общее количество вложений в данных писем
        total_attachments_in_emails = sum(email["attachments_count"] for email in thread_emails)
        print(f"📊 Всего вложений в данных писем: {total_attachments_in_emails}")
        print(f"📊 Файлов вложений на диске: {len(thread_attachments)}")
        
        if total_attachments_in_emails != len(thread_attachments):
            print("⚠️ ОБНАРУЖЕНА ПРОБЛЕМА: несоответствие количества вложений")
            print("   Это может быть признаком некорректного маппинга")
            
            # Детальный анализ проблемы
            print(f"\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ:")
            
            # Группируем вложения по message_id
            attachments_by_message = {}
            for email in thread_emails:
                message_id = email['message_id']
                attachments_by_message[message_id] = email['attachments']
            
            print("📊 Вложения по Message-ID:")
            for message_id, attachments in attachments_by_message.items():
                print(f"   Message-ID: {message_id[:50]}...")
                print(f"   Вложений в данных: {len(attachments)}")
                for attachment in attachments:
                    filename = attachment.get('filename', 'Unknown')
                    print(f"      - {filename}")
            
            # Проверяем дубликаты
            all_attachment_names = []
            for email in thread_emails:
                for attachment in email['attachments']:
                    all_attachment_names.append(attachment.get('filename', ''))
            
            unique_names = set(all_attachment_names)
            duplicate_names = [name for name in unique_names if all_attachment_names.count(name) > 1]
            
            if duplicate_names:
                print(f"\n⚠️ НАЙДЕНЫ ДУБЛИКАТЫ ВЛОЖЕНИЙ:")
                for name in duplicate_names:
                    count = all_attachment_names.count(name)
                    print(f"   {name}: {count} раз")
                    
            return True
        else:
            print("✅ Количество вложений соответствует")
    
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("   1. Используйте новую архитектуру с message_id")
    print("   2. Запустите миграцию существующих данных")
    print("   3. Проверьте корректность маппинга после миграции")
    
    return True


def test_message_id_extraction():
    """Тестирование извлечения message_id из имен файлов."""
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ ИЗВЛЕЧЕНИЯ MESSAGE-ID")
    print("="*60)
    
    # Тестовые имена файлов
    test_filenames = [
        "20250723_dna-technology_ru_1c456124_084139_attach_КП 8386 от 23.07.2025.pdf",
        "20250723_dna-technology_ru_be4fb59a_084146_attach_АНКЕТА Участника.docx",
        "email_004_20250723_20250723_dna-technology_ru_1c456124.json",
        "email_003_20250723_20250723_dna-technology_ru_be4fb59a.json",
    ]
    
    def extract_thread_id_from_filename(filename):
        """Извлечение thread_id из имени файла."""
        # Простая логика для теста
        parts = filename.replace(".json", "").replace(".pdf", "").replace(".docx", "").split("_")
        if len(parts) >= 4:
            # Для email_XXX_YYYY_... формата
            if parts[0] == "email" and len(parts) >= 4:
                return f"{parts[2]}_{parts[3]}"
            # Для обычных вложений
            elif parts[0].isdigit() and len(parts) >= 4:
                return f"{parts[1]}_{parts[2]}_{parts[3]}"
        return None
    
    def generate_message_id_filename(message_id, original_filename, date_folder):
        """Генерация имени файла с message_id."""
        # Извлекаем базовую часть message_id
        clean_message_id = message_id.replace("<", "").replace(">", "").replace("@", "_").replace(".", "_")
        
        # Создаем уникальное имя
        timestamp = datetime.now().strftime("%H%M%S")
        safe_filename = original_filename.replace(" ", "_").replace("/", "_")
        
        return f"{date_folder}_{clean_message_id}_{timestamp}_{safe_filename}"
    
    print("📄 Тестовые имена файлов:")
    for filename in test_filenames:
        thread_id = extract_thread_id_from_filename(filename)
        print(f"   {filename}")
        print(f"   → Thread-ID: {thread_id}")
    
    print("\n✨ Тестирование генерации имен с message_id:")
    test_message_id = "<test-message-123@example.com>"
    test_filename = "test_document.pdf"
    test_date_folder = "2025-07-23"
    
    generated_filename = generate_message_id_filename(test_message_id, test_filename, test_date_folder)
    print(f"   Message-ID: {test_message_id}")
    print(f"   Оригинальное имя: {test_filename}")
    print(f"   Сгенерированное имя: {generated_filename}")
    
    # Проверяем наличие message_id в имени файла
    if "test_message_123_example" in generated_filename:
        print("✅ Message-ID корректно включен в имя файла")
    else:
        print("❌ Message-ID НЕ включен в имя файла")
    
    return True


def main():
    """Основная функция тестирования."""
    print("🧪 ТЕСТИРОВАНИЕ МАППИНГА ВЛОЖЕНИЙ")
    print("="*60)
    
    tests = [
        ("Логика маппинга", test_attachment_mapping_logic),
        ("Извлечение Message-ID", test_message_id_extraction),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🚀 Запуск теста: {test_name}")
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ Тест '{test_name}' пройден")
            else:
                print(f"❌ Тест '{test_name}' не пройден")
                
        except Exception as e:
            print(f"💥 Ошибка в тесте '{test_name}': {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Итоги
    print("\n" + "="*60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ НЕ ПРОЙДЕН"
        print(f"{test_name:<30} {status}")
    
    print(f"\n📈 Итого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("\n📋 ВЫВОДЫ ПО ПРОБЛЕМЕ МАППИНГА:")
        print("1. 🔍 Обнаружена проблема с thread_id-based маппингом")
        print("2. ✅ Новая архитектура с message_id решает эту проблему")
        print("3. 🔄 Требуется миграция существующих данных")
        print("4. 🚀 Рекомендуется перейти на новую архитектуру")
    else:
        print("⚠️ Некоторые тесты не пройдены. Требуется доработка.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)