# Интеграция PreCleaner с Email Fetcher - Руководство по использованию

## 📋 Обзор

PreCleaner - это интеллектуальный модуль пред-очистки текстов писем, который интегрируется в Email Fetcher для сокращения размера текстов и экономии токенов LLM.

### 🎯 Основные возможности

1. **Умная сегментация** - разделяет текст на осмысленные блоки
2. **Кэширование паттернов** - запоминает подписи, цитаты и дисклеймеры
3. **Удаление мусора** - удаляет повторяющиеся элементы и системные надписи
4. **Статистика эффективности** - отслеживает экономию токенов и производительность

### 📊 Ожидаемые результаты

- **Экономия токенов**: 30-50% сокращение размера текстов
- **Сохранение контента**: 95%+ важной информации сохранено
- **Улучшение качества LLM**: более точное извлечение сущностей
- **Снижение стоимости**: экономия на API вызовах LLM

## 🚀 Быстрый старт

### 1. Поиск обрезанных писем

```bash
# Запуск поиска обрезанных писем
python src/fetcher/utils/find_truncated_emails.py --verbose

# Результаты будут сохранены в data/reports/
```

### 2. Миграция обрезанных писем

```bash
# Запуск CLI утилиты миграции
python src/fetcher/utils/migrate_truncated_emails.py

# Интерактивное меню:
# 1. Найти обрезанные письма
# 2. Создать бэкап
# 3. Удалить обрезанные письма
```

### 3. Анализ паттернов перед внедрением PreCleaner

```bash
# Анализ паттернов в существующих письмах
python .kiro/specs/precleaner/discover_patterns.py --infile data/emails/2025-07-23/emails.ndjson --out ./patterns

# Результаты:
# - CSV файлы с топовыми паттернами подписей, цитат, дисклеймеров
# - Markdown отчет с анализом
# - Рекомендации по настройке PreCleaner
```

### 4. Использование с Email Fetcher

```python
# Вариант 1: Через Legacy адаптер (рекомендуется для начала)
from src.fetcher import LegacyEmailFetcherV2
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LegacyEmailFetcherV2 уже включает PreCleaner
fetcher = LegacyEmailFetcherV2(logger)
if fetcher.connect():
    emails = fetcher.fetch_emails_by_date_range(
        datetime(2025, 10, 10), datetime(2025, 10, 10)
    )
    print(f'Загружено {len(emails)} писем с PreCleaner')
    fetcher.close()

# Вариант 2: Прямое использование новой архитектуры
from src.fetcher import EmailFetcher, ConnectionManager, EmailStorage
from src.fetcher.utils.enhanced_text_cleaner_with_precleaner import create_text_cleaner

# Создаем компоненты
connection_manager = ConnectionManager(logger)
email_storage = EmailStorage(logger)
text_cleaner = create_text_cleaner(logger, enable_precleaner=True)

# Создаем Email Fetcher с PreCleaner
fetcher = EmailFetcher(
    connection_manager=connection_manager,
    email_storage=email_storage,
    text_cleaner=text_cleaner,
    logger=logger
)

# Используем как обычно
emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
```

## 📁 Структура файлов

```
src/fetcher/utils/
├── find_truncated_emails.py           # Поиск обрезанных писем
├── migrate_truncated_emails.py        # CLI утилита миграции
├── precleaner_adapter.py              # Адаптер PreCleaner
├── enhanced_text_cleaner_with_precleaner.py  # Интегрированный очиститель
└── precleaner_statistics.py           # Система статистики

.kiro/specs/precleaner/
├── ANALYSIS_AND_INTEGRATION_PLAN.md   # План интеграции
├── README_INTEGRATION.md              # Этот файл
├── precleaner/
│   ├── core.py                        # Ядро PreCleaner
│   ├── cli.py                         # CLI PreCleaner
│   └── config.yaml                    # Конфигурация
└── discover_patterns.py               # Анализ паттернов
```

## 🔧 Конфигурация

### Базовая конфигурация PreCleaner

```yaml
# config.yaml
precleaner:
  max_signature_lines: 5              # Максимальное строк в подписи
  fold_quote_over_chars: 1200         # Сворачивать цитаты длиннее N символов
  fold_on_repeat: true                 # Сворачивать повторяющиеся блоки
  keep_first_signature_per_sender: true # Сохранять первую подпись отправителя
  keep_first_disclaimer_per_thread: true # Сохранять первый дисклеймер в треде
  languages: [ru, en]                  # Поддерживаемые языки
  sig_markers:                         # Маркеры подписей
    - "--"
    - "—"
    - "с уважением"
    - "best regards"
    - "kind regards"
  disclaimer_markers:                  # Маркеры дисклеймеров
    - "confidentiality notice"
    - "настоящее сообщение"
    - "this message may contain confidential"
    - "unsubscribe"
    - "privacy policy"
```

### Интеграция в Email Fetcher

```python
# В src/fetcher/core/email_processor.py

class EmailProcessor:
    def __init__(self, logger):
        # ...
        # Используем новый очиститель с PreCleaner
        self.text_cleaner = create_text_cleaner(
            logger, 
            enable_precleaner=True,
            config_path="config/precleaner.yaml"
        )
    
    def process_email_content(self, raw_text, thread_id, sender_email):
        # Базовая очистка через EnhancedTextCleaner
        base_cleaned = self.text_cleaner.clean_html_aggressively(raw_text)
        
        # Интеллектуальная пред-очистка через PreCleaner
        result = self.text_cleaner.clean_email_body_full(
            base_cleaned, thread_id, sender_email
        )
        
        return result['cleaned_text']
```

## 📊 Анализ эффективности

### Сбор статистики

```bash
# Анализ накопленной статистики
python src/fetcher/utils/precleaner_statistics.py --verbose

# Результаты:
# - Markdown отчет в data/reports/precleaner/
# - JSON данные для дальнейшего анализа
```

### Пример отчета

```markdown
# Отчет по эффективности PreCleaner

**Дата создания**: 2025-10-10 15:30:00
**Всего сессий**: 15
**Обработано писем**: 1,250
**Сэкономлено токенов**: 45,000

## 📊 Сводная статистика

| Метрика | Значение |
|---------|----------|
| Среднее сокращение | 36.2% |
| Среднее время обработки | 45.1 мс |
| Удалено подписей | 890 |
| Удалено цитат | 320 |
| Удалено дисклеймеров | 180 |

## 💡 Рекомендации

✅ **Хорошее сокращение текста** (36.2%). Отличная экономия токенов!

⚠️ **Мало цитат удаляется**. Возможно:
- Цитаты имеют нестандартный формат
- Нужно добавить новые паттерны для цитат
```

## 🔄 Процесс миграции

### Шаг 1: Подготовка

```bash
# 1. Создаем бэкап
cp -r data/emails data/emails_backup_$(date +%Y%m%d)

# 2. Ищем обрезанные письма
python src/fetcher/utils/find_truncated_emails.py

# 3. Анализируем результаты
cat data/reports/truncated_emails_*.md
```

### Шаг 2: Миграция

```bash
# Запускаем CLI утилиту
python src/fetcher/utils/migrate_truncated_emails.py

# В меню:
# 1. Найти обрезанные письма
# 2. Создать бэкап (автоматически)
# 3. Удалить обрезанные письма
```

### Шаг 3: Анализ паттернов перед PreCleaner

```bash
# Сначала анализируем паттерны в существующих письмах
python .kiro/specs/precleaner/discover_patterns.py --infile data/emails/2025-07-23/emails.ndjson --out ./patterns

# Это поможет определить реальные паттерны в вашей базе писем
# и настроить PreCleaner для максимальной эффективности
```

### Шаг 4: Перезагрузка с новым Email Fetcher и PreCleaner

```bash
# Используем новый модульный Email Fetcher (НЕ старый monolithic)
python -c "
from src.fetcher import LegacyEmailFetcherV2
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fetcher = LegacyEmailFetcherV2(logger)
if fetcher.connect():
    emails = fetcher.fetch_emails_by_date_range(
        datetime(2025, 10, 10), datetime(2025, 10, 10)
    )
    print(f'Загружено {len(emails)} писем с PreCleaner')
    fetcher.close()
"

# Проверяем результаты
python src/fetcher/utils/precleaner_statistics.py
```

### Шаг 5: Полная миграция на новую архитектуру (опционально)

```bash
# После успешного тестирования можно перейти на новую архитектуру
python -c "
from src.fetcher import EmailFetcher, ConnectionManager, EmailStorage
from src.fetcher.utils.enhanced_text_cleaner_with_precleaner import create_text_cleaner
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем компоненты новой архитектуры
connection_manager = ConnectionManager(logger)
email_storage = EmailStorage(logger)
text_cleaner = create_text_cleaner(logger, enable_precleaner=True)

# Создаем новый Email Fetcher
fetcher = EmailFetcher(
    connection_manager=connection_manager,
    email_storage=email_storage,
    text_cleaner=text_cleaner,
    logger=logger
)

if fetcher.connect():
    emails = fetcher.fetch_emails_by_date_range(
        datetime(2025, 10, 10), datetime(2025, 10, 10)
    )
    print(f'Загружено {len(emails)} писем с новой архитектурой')
    fetcher.close()
"
```

## 🧪 Тестирование

### Unit тесты

```python
# Тестирование адаптера
from src.fetcher.utils.precleaner_adapter import PreCleanerAdapter

adapter = PreCleanerAdapter()
result = adapter.preclean_text(
    "Тестовое письмо\n--\nПодпись", 
    "thread_123", 
    "test@example.com"
)

assert "Подпись" not in result.body_clean_llm
assert "[signature" in result.body_clean_llm
```

### Интеграционные тесты

```python
# Тестирование интеграции с Email Fetcher
from src.fetcher.utils.enhanced_text_cleaner_with_precleaner import create_text_cleaner

cleaner = create_text_cleaner(enable_precleaner=True)
result = cleaner.clean_email_body_full(
    html_content, 
    thread_id="test", 
    sender_email="test@example.com"
)

# Проверяем статистику
stats = cleaner.get_precleaner_stats()
assert stats['total_processed'] > 0
```

## 🔍 Поиск проблем

### Логирование

```python
# Включение детального логирования
import logging
logging.basicConfig(level=logging.DEBUG)

cleaner = create_text_cleaner(logger, enable_precleaner=True)
```

### Диагностика

```bash
# Проверка статистики
python src/fetcher/utils/precleaner_statistics.py --verbose

# Анализ паттернов (рекомендуется перед внедрением)
python .kiro/specs/precleaner/discover_patterns.py --infile data/emails/2025-07-23/emails.ndjson --out ./patterns
```

## 🔍 Анализ паттернов с discover_patterns.py

### Назначение

Модуль `discover_patterns.py` анализирует существующие письма для выявления реальных паттернов подписей, цитат и дисклеймеров. Это позволяет настроить PreCleaner для максимальной эффективности.

### Когда запускать

**Запускайте ДО активации PreCleaner:**
1. После миграции на новый Email Fetcher
2. Перед загрузкой новых писем с PreCleaner
3. При появлении новых типов писем в базе

### Подготовка данных

```bash
# Конвертируем JSON письма в NDJSON формат для анализа
python -c "
import json
import glob
from pathlib import Path

emails_dir = Path('data/emails/2025-07-23')
output_file = Path('data/emails/2025-07-23/emails.ndjson')

with open(output_file, 'w', encoding='utf-8') as outfile:
    for json_file in emails_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as infile:
                email_data = json.load(infile)
                # Конвертируем в нужный формат
                email_ndjson = {
                    'message_id': email_data.get('message_id', ''),
                    'thread_id': email_data.get('thread_id', ''),
                    'from': email_data.get('from', ''),
                    'date': email_data.get('date', ''),
                    'body_text': email_data.get('body', '')
                }
                outfile.write(json.dumps(email_ndjson, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f'Ошибка обработки {json_file}: {e}')

print(f'Создан {output_file} с письмами для анализа')
"
```

### Запуск анализа

```bash
# Базовый анализ
python .kiro/specs/precleaner/discover_patterns.py --infile data/emails/2025-07-23/emails.ndjson --out ./patterns

# Анализ с ограничением (для быстрой проверки)
python .kiro/specs/precleaner/discover_patterns.py --infile data/emails/2025-07-23/emails.ndjson --out ./patterns --limit 1000

# Полный анализ всех писем
python .kiro/specs/precleaner/discover_patterns.py --infile data/emails/2025-07-23/emails.ndjson --out ./patterns
```

### Результаты анализа

```
patterns/
├── top_signature_patterns.csv    # Топовые подписи по доменам
├── top_disclaimer_patterns.csv  # Топовые дисклеймеры
├── top_quote_patterns.csv       # Топовые цитаты
└── REPORT_PATTERNS.md          # Сводный отчет
```

### Использование результатов

1. **Настройка паттернов PreCleaner** на основе реальных данных
2. **Идентификация проблемных доменов** с нестандартными форматами
3. **Оптимизация порогов** для определения подписей и цитат
4. **Создание кастомных правил** для специфических отправителей

```yaml
# Пример настройки на основе результатов анализа
precleaner:
  sig_markers:
    - "--"  # Общий маркер
    - "с уважением"  # Из анализа русских писем
    - "best regards"  # Из анализа английских писем
    - "с наилучшими пожеланиями"  # Найденный паттерн
  
  max_signature_lines: 6  # На основе медианы из анализа
  
  disclaimer_markers:
    - "confidentiality notice"  # Из анализа
    - "настоящее сообщение содержит конфиденциальную информацию"  # Русский паттерн
```

## 📈 Оптимизация

### Настройка паттернов

```yaml
# Для агрессивной очистки
precleaner:
  max_signature_lines: 3              # Меньше строк в подписи
  fold_quote_over_chars: 800         # Меньше порог для цитат
  
# Для консервативной очистки
precleaner:
  max_signature_lines: 8              # Больше строк в подписи
  fold_quote_over_chars: 2000        # Больше порог для цитат
```

### Производительность

```python
# Оптимизация кэша
adapter = PreCleanerAdapter()
adapter.reset_stats()  # Сброс статистики
adapter.save_stats()   # Сохранение промежуточных результатов
```

## 🚨 Важные замечания

1. **Обратная совместимость**: PreCleaner можно отключить через `enable_precleaner=False`
2. **Graceful degradation**: При ошибках PreCleaner используется базовая очистка
3. **Идемпотентность**: Повторная обработка тех же писем не создает дубликатов
4. **Безопасность**: Все операции с бэкапами подтверждаются пользователем

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи в `data/logs/precleaner/`
2. Ознакомьтесь с отчетами в `data/reports/precleaner/`
3. Используйте `--verbose` флаг для детального логирования
4. Создайте issue с описанием проблемы и логами

---

**Статус**: ✅ Production Ready  
**Версия**: 1.0  
**Дата**: 2025-10-10