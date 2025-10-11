# Email Fetcher v2.0 - Новая модульная архитектура

## Обзор

Email Fetcher v2.0 представляет собой полную переработку оригинального модуля `advanced_email_fetcher.py` с фокусом на исправление критической проблемы маппинга вложений и улучшение архитектуры.

## Ключевые исправления

### 🎯 Исправление маппинга вложений

**Проблема**: Вложения привязывались к `thread_id` вместо `message_id`, что приводило к некорректному отображению вложений в письмах одного треда.

**Решение**: Внедрен `AttachmentRegistry` с привязкой вложений к `message_id`, что обеспечивает точное соответствие вложений конкретным письмам.

### 🏗️ Модульная архитектура

Монолитный модуль разделен на специализированные компоненты:

```
src/fetcher/
├── core/                 # Основная логика
│   ├── email_fetcher.py      # Главный фасад
│   ├── connection_manager.py # Управление соединениями
│   └── email_processor.py    # Обработка писем
├── filters/              # Фильтрация
│   └── email_filters.py      # Фильтры писем
├── parsers/              # Парсинг
│   └── email_parser.py       # Парсер писем
├── storage/              # Хранение
│   └── email_storage.py      # Хранилище писем
├── attachments/          # Вложения
│   └── attachment_registry.py # Реестр вложений
├── legacy/               # Обратная совместимость
│   └── legacy_email_fetcher.py # Legacy фасад
└── tests/                # Тесты
    └── test_new_architecture.py # Тесты архитектуры
```

## Компоненты

### Core компоненты

#### EmailFetcher
Основной фасад, координирующий работу всех компонентов.

```python
from src.fetcher import EmailFetcher

fetcher = EmailFetcher(
    connection_manager=connection_manager,
    email_storage=email_storage,
    attachment_registry=attachment_registry,
    email_filters=email_filters,
    email_parser=email_parser,
    text_cleaner=text_cleaner,
    logger=logger
)

emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
```

#### ConnectionManager
Управление IMAP соединениями с авто-переподключением и обработкой ошибок.

#### EmailProcessor
Обработка отдельных писем с применением фильтров и сохранением.

### Специализированные компоненты

#### AttachmentRegistry
Реестр вложений с привязкой к `message_id`:

```python
from src.fetcher import AttachmentRegistry

registry = AttachmentRegistry(logger)

# Сохранение вложения с привязкой к message_id
attachment_info = registry.save_attachment(
    part=email_part,
    message_id=message_id,  # Ключевое исправление
    date_folder=date_folder,
    is_inline=is_inline
)

# Поиск вложений конкретного письма
attachments = registry.find_attachments_by_message_id(message_id, date_folder)
```

#### EmailStorage
Хранение email данных с поддержкой обновления информации о вложениях.

#### EmailFilters
Фильтрация писем по темам, отправителям, массовым рассылкам.

#### EmailParser
Парсинг email контента с извлечением текста и метаданных.

## Обратная совместимость

Для существующего кода предоставлен `LegacyEmailFetcherV2`:

```python
from src.fetcher import LegacyEmailFetcherV2

# Полная замена старого класса
fetcher = LegacyEmailFetcherV2(logger)

# Все старые методы работают
emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
email_data = fetcher.process_single_email(msg_id, date_str, 1, 10)
```

## Миграция со старой версии

### 1. Быстрая замена (рекомендуется)

```python
# Было:
from src.advanced_email_fetcher import AdvancedEmailFetcherV2
fetcher = AdvancedEmailFetcherV2(logger)

# Стало:
from src.fetcher import LegacyEmailFetcherV2
fetcher = LegacyEmailFetcherV2(logger)
```

### 2. Полная миграция на новую архитектуру

```python
from src.fetcher import (
    EmailFetcher,
    ConnectionManager,
    EmailStorage,
    AttachmentRegistry,
    EmailFilters,
    EmailParser
)

# Настройка компонентов
connection_manager = ConnectionManager(logger)
email_storage = EmailStorage(logger)
attachment_registry = AttachmentRegistry(logger)
email_filters = EmailFilters(logger)
email_parser = EmailParser(logger)
text_cleaner = EmailTextCleaner(logger)

# Создание фасада
fetcher = EmailFetcher(
    connection_manager=connection_manager,
    email_storage=email_storage,
    attachment_registry=attachment_registry,
    email_filters=email_filters,
    email_parser=email_parser,
    text_cleaner=text_cleaner,
    logger=logger
)
```

## Тестирование

Запуск тестов новой архитектуры:

```bash
cd src/fetcher/tests
python test_new_architecture.py
```

Тесты проверяют:
- Корректность работы реестра вложений
- Функциональность хранилища писем
- Обратную совместимость
- Исправление маппинга вложений

## Преимущества новой архитектуры

1. **Исправлен баг маппинга вложений** - вложения привязаны к конкретным письмам
2. **Модульность** - легкое тестирование и поддержка отдельных компонентов
3. **Расширяемость** - простое добавление новой функциональности
4. **Обратная совместимость** - существующий код работает без изменений
5. **Лучшая диагностика** - детальное логирование и обработка ошибок

## Пример использования

### CLI интерфейс (рекомендуется)

```bash
# Интерактивный режим с полным меню
python src/fetcher/cli.py --interactive

# Прямой запуск с различными форматами дат
python src/fetcher/cli.py --date 2025-07-12
python src/fetcher/cli.py --date "12 июля 25"
python src/fetcher/cli.py --date "7.7.25"

# Диапазон дат
python src/fetcher/cli.py --start-date 2025-07-01 --end-date 2025-07-31

# Legacy режим
python src/fetcher/cli.py --legacy --date "12 июля 2025"

# Быстрый запуск из корня проекта
python run_new_fetcher.py
```

### Базовое использование (legacy)

```python
import logging
from src.fetcher import LegacyEmailFetcherV2
from datetime import datetime

logger = logging.getLogger(__name__)
fetcher = LegacyEmailFetcherV2(logger)

if fetcher.connect():
    emails = fetcher.fetch_emails_by_date_range(
        datetime(2025, 7, 23),
        datetime(2025, 7, 23)
    )
    print(f"Загружено {len(emails)} писем")
    fetcher.close()
```

### Продвинутое использование (новая архитектура)

```python
import logging
from src.fetcher import EmailFetcher, AttachmentRegistry
from datetime import datetime

logger = logging.getLogger(__name__)

# Создаем реестр вложений
attachment_registry = AttachmentRegistry(logger)

# Проверяем вложения конкретного письма
message_id = "<test@example.com>"
attachments = attachment_registry.find_attachments_by_message_id(
    message_id, "2025-07-23"
)

print(f"Письмо {message_id} имеет {len(attachments)} вложений")
for att in attachments:
    print(f"  - {att['original_filename']} ({att['file_size']} байт)")
```

### 🎛️ Интерактивное меню

CLI интерфейс предоставляет удобное меню с выбором:

1. **Диапазон дат (от-до)** - выбор периода
2. **Одна конкретная дата** - обработка за день
3. **Весь месяц текущего года** - целый месяц
4. **Последние 7 дней** - автоматический период
5. **Последние 30 дней** - автоматический период
6. **Тестовый запуск (сегодня)** - быстрая проверка

### 📅 Гибкие форматы дат

CLI поддерживает все форматы из старого фетчера:
- `2025-07-12` (ISO)
- `12.07.2025` (точки)
- `12-7-25` (короткий)
- `12 июля 25` (русский)
- `7.7.25` (короткий с точками)

## Важные замечания

1. **Message-ID** является уникальным идентификатором письма
2. **Thread-ID** используется для группировки писем в диалоги
3. **Вложения** теперь корректно привязаны к конкретным письмам
4. **Миграция** существующих данных может потребоваться для корректной работы

## 🚀 Быстрый старт

### Для быстрого запуска используйте:

```bash
# 1. Интерактивный режим (рекомендуется)
python src/fetcher/cli.py --interactive

# 2. Быстрый тест
python src/fetcher/cli.py --demo

# 3. Прямой запуск
python run_new_fetcher.py
```

### Подробная документация

- 📖 **CLI руководство**: [`CLI_USAGE.md`](CLI_USAGE.md)
- 🏗️ **План рефакторинга**: [`fetcher_refactoring_plan.md`](fetcher_refactoring_plan.md)

## Следующие шаги

1. Протестировать новую архитектуру на реальных данных
2. Выполнить миграцию существующих писем
3. Обновить связанные модули (OCR Processor, File Tokens)
4. Внедрить в production после тестирования

## 🚀 CLI Интерфейс

Новый CLI интерфейс обеспечивает удобный запуск фетчера с интерактивным меню:

### Запуск CLI

```bash
# Интерактивный режим (рекомендуется)
python src/fetcher/cli.py --interactive

# Прямой запуск с параметрами
python src/fetcher/cli.py --date 2025-07-12
python src/fetcher/cli.py --start-date 2025-07-01 --end-date 2025-07-31

# Legacy режим
python src/fetcher/cli.py --interactive --legacy
```

### Возможности CLI

- 📅 **Гибкий выбор дат**: поддержка различных форматов дат
- 🔄 **Выбор архитектуры**: новая v2.0 или legacy режим
- 📊 **Детальное логирование**: сохранение логов в файлы
- 🧪 **Тестовый режим**: быстрый тест на текущей дате
- ⚡ **Прямой запуск**: без интерактивного меню

### Форматы дат

CLI поддерживает множество форматов дат:
- `2025-07-12` (ISO)
- `12.07.2025` (точки)
- `12-7-25` (короткий)
- `12 июля 25` (текстовый на русском)

### Преимущества нового CLI

1. **Удобство**: Интерактивное меню с подсказками
2. **Гибкость**: Выбор между новой и legacy архитектурой
3. **Информативность**: Подробная информация о процессе обработки
4. **Совместимость**: Полная обратная совместимость со старым кодом

---

**Версия**: 2.0.0
**Дата**: 2025-10-11
**Автор**: Kilo Code Assistant