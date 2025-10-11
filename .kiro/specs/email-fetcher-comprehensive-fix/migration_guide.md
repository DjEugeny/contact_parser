# Руководство по миграции на новую архитектуру Email Fetcher

## Обзор

Данное руководство описывает процесс миграции с монолитного модуля `advanced_email_fetcher.py` на новую модульную архитектуру, которая исправляет критические баги с маппингом вложений и обрезкой текстов.

## Подготовка к миграции

### 1. Резервное копирование данных

Перед началом миграции создайте резервные копии:

```bash
# Копируем папки с данными
cp -r data/emails data/emails_backup_$(date +%Y%m%d)
cp -r data/attachments data/attachments_backup_$(date +%Y%m%d)

# Копируем оригинальный модуль
cp src/advanced_email_fetcher.py src/advanced_email_fetcher.py.backup_$(date +%Y%m%d)
```

### 2. Проверка окружения

Убедитесь, что все необходимые зависимости установлены:

```bash
pip install -r requirements.txt
```

## Шаг 1: Развертывание новой архитектуры

### 1.1. Создание структуры папок

Новая архитектура уже развернута в следующих папках:
- `src/fetcher/` - основная архитектура
- `src/fetcher/core/` - основные компоненты
- `src/fetcher/attachments/` - управление вложениями
- `src/fetcher/utils/` - утилиты
- `src/fetcher/adapters/` - адаптеры совместимости

### 1.2. Установка модулей

Новые модули уже интегрированы в структуру проекта. Дополнительная установка не требуется.

## Шаг 2: Миграция вложений (критически важно)

### 2.1. Запуск мигратора вложений

```python
from src.fetcher.migration.attachment_migration import AttachmentMigrator

# Создаем мигратор
migrator = AttachmentMigrator(
    data_dir="data",
    backup_dir="data/migration_backup"
)

# Выполняем миграцию
result = migrator.migrate_all_attachments()

print(f"Миграция завершена:")
print(f"- Обработано писем: {result['processed_emails']}")
print(f"- Мигрировано вложений: {result['migrated_attachments']}")
print(f"- Ошибок: {result['errors']}")
```

### 2.2. Проверка результатов миграции

После миграции проверьте корректность:

```python
# Проверка маппинга вложений
from src.fetcher.attachments.attachment_registry import AttachmentRegistry

registry = AttachmentRegistry("data")

# Проверяем конкретное письмо
email_attachments = registry.get_attachments_for_message(
    message_id="<376b6d5e-2e91-49f1-8a5c-8b5859e9e9bb@dna-technology.ru>",
    date_folder="2025-07-23"
)

print(f"Найдено вложений: {len(email_attachments)}")
for att in email_attachments:
    print(f"- {att['original_filename']} ({att['file_size']} байт)")
```

## Шаг 3: Восстановление полных текстов

### 3.1. Анализ обрезанных текстов

```python
from src.fetcher.recovery.text_recovery_module import TextRecoveryModule

recovery = TextRecoveryModule("data")

# Находим письма с обрезанными текстами
truncated_emails = recovery.find_truncated_emails(threshold=10000)

print(f"Найдено писем с обрезанными текстами: {len(truncated_emails)}")
```

### 3.2. Восстановление текстов

```python
# Восстанавливаем тексты
recovery_results = recovery.recover_all_texts()

print(f"Восстановлено текстов: {recovery_results['recovered_count']}")
print(f"Ошибок: {recovery_results['error_count']}")
```

## Шаг 4: Интеграция с существующим кодом

### 4.1. Использование Legacy Adapter

Для максимальной обратной совместимости используйте адаптер:

```python
from src.fetcher.adapters.legacy_adapter import LegacyEmailFetcherV2
from src.config.paths import ensure_config_structure
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmailFetcher")

# Создаем экземпляр (совместим со старым API)
fetcher = LegacyEmailFetcherV2(logger=logger)

# Используем как раньше
emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
```

### 4.2. Прямое использование новой архитектуры

Для новых разработок используйте новый API:

```python
from src.fetcher.core.email_fetcher import EmailFetcher
from src.fetcher.utils.enhanced_text_cleaner import EnhancedTextCleaner

# Создаем компоненты
fetcher = EmailFetcher()
text_cleaner = EnhancedTextCleaner()

# Используем новые возможности
emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
```

## Шаг 5: Валидация миграции

### 5.1. Проверка маппинга вложений

```python
def validate_attachment_mapping():
    """Проверяет корректность маппинга вложений"""
    test_cases = [
        {
            "message_id": "<376b6d5e-2e91-49f1-8a5c-8b5859e9e9bb@dna-technology.ru>",
            "date_folder": "2025-07-23",
            "expected_attachments": 2
        },
        {
            "message_id": "<e15c68a3-b9b3-4f78-8860-dfc2bbe25748@dna-technology.ru>",
            "date_folder": "2025-07-23",
            "expected_attachments": 3
        }
    ]
    
    registry = AttachmentRegistry("data")
    
    for case in test_cases:
        attachments = registry.get_attachments_for_message(
            case["message_id"], 
            case["date_folder"]
        )
        
        assert len(attachments) == case["expected_attachments"], \
            f"Ожидается {case['expected_attachments']} вложений, найдено {len(attachments)}"
    
    print("✅ Валидация маппинга вложений пройдена")

validate_attachment_mapping()
```

### 5.2. Проверка полноты текстов

```python
def validate_text_completeness():
    """Проверяет полноту текстов писем"""
    import json
    from pathlib import Path
    
    emails_dir = Path("data/emails/2025-07-23")
    min_length = 10000  # Минимальная длина текста
    
    for email_file in emails_dir.glob("*.json"):
        with open(email_file, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        text_length = len(email_data.get('body', ''))
        
        if text_length < min_length:
            print(f"⚠️ Короткий текст в {email_file.name}: {text_length} символов")
        else:
            print(f"✅ Полный текст в {email_file.name}: {text_length} символов")

validate_text_completeness()
```

## Шаг 6: Production развертывание

### 6.1. План развертывания

1. **Подготовительный этап**
   - Создание резервных копий
   - Тестирование на небольшом объеме данных

2. **Основной этап**
   - Остановка production процессов
   - Выполнение миграции
   - Валидация результатов

3. **Завершающий этап**
   - Запуск production процессов
   - Мониторинг работы

### 6.2. Откат изменений

В случае проблем используйте резервные копии:

```bash
# Откат данных
rm -rf data/emails
mv data/emails_backup_YYYYMMDD data/emails

rm -rf data/attachments
mv data/attachments_backup_YYYYMMDD data/attachments

# Откат кода
mv src/advanced_email_fetcher.py.backup_YYYYMMDD src/advanced_email_fetcher.py
```

## Часто задаваемые вопросы

### Q: Что произойдет с существующими данными?
A: Данные не будут удалены. Миграция только обновляет метаданные и структуру маппинга.

### Q: Сохранится ли обратная совместимость?
A: Да, через `LegacyEmailFetcherV2` API полностью совместим со старым кодом.

### Q: Как долго занимает миграция?
A: Зависит от объема данных. Для 10,000 писем примерно 30-60 минут.

### Q: Что делать при ошибках миграции?
A: Проверьте логи в `data/logs/`, исправьте проблемы и запустите миграцию повторно.

## Поддержка

При возникновении проблем:
1. Проверьте логи в `data/logs/`
2. Ознакомьтесь с документацией в `src/fetcher/README.md`
3. Используйте утилиты валидации из раздела 5

---

**Важно**: Перед производственным развертыванием обязательно протестируйте процесс на копии данных!