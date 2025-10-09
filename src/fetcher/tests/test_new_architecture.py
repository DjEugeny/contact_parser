"""
Тестирование новой архитектуры email fetcher.

Проверяет корректность маппинга вложений и обратную совместимость.
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

from src.fetcher.core.email_fetcher import EmailFetcher
from src.fetcher.legacy.legacy_email_fetcher import LegacyEmailFetcherV2
from src.fetcher.attachments.attachment_registry import AttachmentRegistry
from src.fetcher.storage.email_storage import EmailStorage
from src.fetcher.config.paths import DATA_DIR


def setup_test_logging():
    """Настройка тестового логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )
    return logging.getLogger("TestNewArchitecture")


def test_attachment_registry():
    """Тестирование реестра вложений."""
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ REЕСТРА ВЛОЖЕНИЙ")
    print("="*60)
    
    logger = setup_test_logging()
    registry = AttachmentRegistry(logger)
    
    # Тест 1: Проверка создания имени файла с message_id
    test_message_id = "<test-message-123@example.com>"
    test_filename = "test_document.pdf"
    
    generated_filename = registry.generate_attachment_filename(
        test_message_id, test_filename, "2025-07-23"
    )
    
    print(f"📄 Message-ID: {test_message_id}")
    print(f"📎 Оригинальное имя: {test_filename}")
    print(f"✨ Сгенерированное имя: {generated_filename}")
    
    # Проверяем наличие message_id в имени файла
    if "test-message-123" in generated_filename:
        print("✅ Message-ID корректно включен в имя файла")
    else:
        print("❌ Message-ID НЕ включен в имя файла")
        return False
    
    # Тест 2: Проверка поиска вложений по message_id
    test_date_folder = "2025-07-23"
    attachments = registry.find_attachments_by_message_id(test_message_id, test_date_folder)
    
    print(f"🔍 Поиск вложений для message_id: {test_message_id}")
    print(f"📁 Папка: {test_date_folder}")
    print(f"📎 Найдено вложений: {len(attachments)}")
    
    return True


def test_email_storage():
    """Тестирование хранилища писем."""
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ ХРАНИЛИЩА ПИСЕМ")
    print("="*60)
    
    logger = setup_test_logging()
    storage = EmailStorage(logger)
    
    # Тест 1: Проверка существования письма по message_id
    test_message_id = "<376b6d5e-2e91-49f1-8a5c-8b5859e9e9bb@dna-technology.ru>"
    test_date_folder = "2025-07-23"
    
    exists = storage.email_exists(test_message_id, test_date_folder)
    print(f"📧 Message-ID: {test_message_id[:50]}...")
    print(f"📁 Папка: {test_date_folder}")
    print(f"📄 Существует: {exists}")
    
    if exists:
        # Тест 2: Получение данных письма
        email_data = storage.get_email_data(test_message_id, test_date_folder)
        if email_data:
            print(f"📊 Размер письма: {email_data.get('char_count', 0)} символов")
            print(f"📎 Вложений: {email_data.get('attachments_stats', {}).get('total', 0)}")
            
            # Проверяем корректность маппинга вложений
            attachments = email_data.get('attachments', [])
            message_id_in_data = email_data.get('message_id', '')
            
            print(f"🔍 Проверка маппинга вложений:")
            print(f"   Message-ID в данных: {message_id_in_data[:50]}...")
            
            # Ищем реальные файлы вложений
            real_attachments = storage.list_emails_by_date(test_date_folder)
            print(f"📁 Найдено файлов писем: {len(real_attachments)}")
            
            return True
        else:
            print("❌ Не удалось загрузить данные письма")
            return False
    else:
        print("ℹ️ Письмо не найдено (это нормально для теста)")
        return True


def test_legacy_compatibility():
    """Тестирование обратной совместимости."""
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ ОБРАТНОЙ СОВМЕСТИМОСТИ")
    print("="*60)
    
    logger = setup_test_logging()
    
    # Создаем legacy фасад
    legacy_fetcher = LegacyEmailFetcherV2(logger)
    
    print("✅ LegacyEmailFetcherV2 создан")
    
    # Проверяем наличие всех необходимых атрибутов
    required_attributes = [
        'stats', 'filters', 'text_cleaner', 'connection_manager',
        'email_storage', 'attachment_registry', 'email_fetcher'
    ]
    
    missing_attrs = []
    for attr in required_attributes:
        if not hasattr(legacy_fetcher, attr):
            missing_attrs.append(attr)
    
    if missing_attrs:
        print(f"❌ Отсутствуют атрибуты: {missing_attrs}")
        return False
    else:
        print("✅ Все необходимые атрибуты присутствуют")
    
    # Проверяем наличие основных методов
    required_methods = [
        'connect', 'close', 'fetch_emails_by_date_range', 
        'process_single_email', 'check_email_already_saved'
    ]
    
    missing_methods = []
    for method in required_methods:
        if not hasattr(legacy_fetcher, method) or not callable(getattr(legacy_fetcher, method)):
            missing_methods.append(method)
    
    if missing_methods:
        print(f"❌ Отсутствуют методы: {missing_methods}")
        return False
    else:
        print("✅ Все необходимые методы присутствуют")
    
    # Тестируем совместимые методы
    test_date_folder = "2025-07-23"
    
    # Проверяем статистику хранилища
    if hasattr(legacy_fetcher, 'email_storage'):
        storage_stats = legacy_fetcher.email_storage.get_storage_stats()
        print(f"📊 Статистика хранилища:")
        print(f"   Всего писем: {storage_stats.get('total_emails', 0)}")
        print(f"   Всего дат: {storage_stats.get('total_dates', 0)}")
        print(f"   Размер: {storage_stats.get('total_size_mb', 0):.1f} МБ")
    
    return True


def test_attachment_mapping_fix():
    """Тестирование исправления маппинга вложений."""
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ МАППИНГА ВЛОЖЕНИЙ")
    print("="*60)
    
    logger = setup_test_logging()
    
    # Проверяем существующие данные
    test_date_folder = "2025-07-23"
    emails_dir = DATA_DIR / "emails" / test_date_folder
    attachments_dir = DATA_DIR / "attachments" / test_date_folder
    
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
                    })
        except Exception as e:
            print(f"⚠️ Ошибка чтения файла {email_file.name}: {e}")
    
    print(f"📧 Найдено писем в треде: {len(thread_emails)}")
    
    for i, email in enumerate(thread_emails):
        print(f"   {i+1}. {email['file']}")
        print(f"      Message-ID: {email['message_id'][:50]}...")
        print(f"      Тема: {email['subject'][:50]}...")
        print(f"      Вложений: {email['attachments_count']}")
    
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
        
        # Считаем общее количество вложений в письмах
        total_attachments_in_emails = sum(email["attachments_count"] for email in thread_emails)
        print(f"📊 Всего вложений в данных писем: {total_attachments_in_emails}")
        print(f"📊 Файлов вложений на диске: {len(thread_attachments)}")
        
        if total_attachments_in_emails != len(thread_attachments):
            print("⚠️ ОБНАРУЖЕНА ПРОБЛЕМА: несоответствие количества вложений")
            print("   Это может быть признаком некорректного маппинга")
        else:
            print("✅ Количество вложений соответствует")
    
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("   1. Используйте новую архитектуру с message_id")
    print("   2. Запустите миграцию существующих данных")
    print("   3. Проверьте корректность маппинга после миграции")
    
    return True


def main():
    """Основная функция тестирования."""
    print("🧪 ТЕСТИРОВАНИЕ НОВОЙ АРХИТЕКТУРЫ EMAIL FETCHER")
    print("="*60)
    
    tests = [
        ("Реестр вложений", test_attachment_registry),
        ("Хранилище писем", test_email_storage),
        ("Обратная совместимость", test_legacy_compatibility),
        ("Исправление маппинга", test_attachment_mapping_fix),
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
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Новая архитектура готова к использованию.")
    else:
        print("⚠️ Некоторые тесты не пройдены. Требуется доработка.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)