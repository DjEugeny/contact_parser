# Анализ и план интеграции PreCleaner с Email Fetcher

## 📊 Анализ текущей архитектуры

### Email Fetcher (обновленный)
- **Модуль**: `src/fetcher/utils/enhanced_text_cleaner.py`
- **Ключевая функция**: `extract_meaningful_content()` с опциональной обрезкой
- **Преимущества**: Сохраняет полные тексты, configurable обрезка
- **Проблема**: Нет интеллектуальной очистки от цитат, подписей, дисклеймеров

### PreCleaner (новый модуль)
- **Модуль**: `.kiro/specs/precleaner/precleaner/core.py`
- **Ключевая функция**: `preclean_email_for_llm()`
- **Преимущества**: Умная сегментация, кэширование паттернов, удаление мусора
- **Проблема**: MVP версия, требует интеграции в основной пайплайн

## 🔄 Точки интеграции

### 1. Замена/дополнение EnhancedTextCleaner
**Текущий процесс**:
```
Email Fetcher → EnhancedTextCleaner → Сохранение в JSON
```

**Новый процесс**:
```
Email Fetcher → EnhancedTextCleaner → PreCleaner → Сохранение в JSON
```

### 2. Архитектурные решения

#### Вариант А: Последовательная обработка (рекомендуется)
```python
# В src/fetcher/utils/enhanced_text_cleaner.py
from .precleaner_adapter import PreCleanerAdapter

class EnhancedTextCleaner:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.precleaner = PreCleanerAdapter(logger)
    
    def extract_meaningful_content(self, text, max_length=None):
        # Базовая очистка HTML
        cleaned_text = self.clean_html_aggressively(text)
        
        # Применяем PreCleaner для интеллектуальной очистки
        precleaned_result = self.precleaner.preclean_text(
            cleaned_text, 
            thread_id="unknown", 
            sender_email="unknown"
        )
        
        # Сохраняем статистику
        self.log_precleaning_stats(precleaned_result)
        
        return precleaned_result.body_clean_llm
```

#### Вариант Б: Замена EnhancedTextCleaner
Полная замена модуля на PreCleaner с адаптером для обратной совместимости.

## 📋 План миграции обрезанных писем

### Шаг 1: Поиск обрезанных писем
Создать скрипт `find_truncated_emails.py`:
- Сканирует все JSON файлы в `data/emails/`
- Ищет пометку "ТЕКСТ ОБРЕЗАН ДЛЯ ЭКОНОМИИ ТОКЕНОВ"
- Создает отчет в Markdown и JSON форматах
- Показывает статистику по датам и отправителям

### Шаг 2: CLI утилита для миграции
Создать `migrate_truncated_emails.py` с меню:
1. Найти обрезанные письма (создать отчет)
2. Удалить обрезанные письма (с бэкапом)
3. Выход

### Шаг 3: Перес загрузка полных текстов
- Бэкап папки `data/emails/`
- Удаление обрезанных писем через CLI
- Перезапуск Email Fetcher с новым модулем PreCleaner

## 🧠 Улучшения PreCleaner

### 1. Интеграция с кэшированием
```python
class ThreadCache:
    """Кэш паттернов для тредов"""
    def __init__(self):
        self.cache = {}
    
    def get_pattern_count(self, thread_id, pattern_hash):
        return self.cache.get(thread_id, {}).get(pattern_hash, 0)
    
    def increment_pattern(self, thread_id, pattern_hash):
        if thread_id not in self.cache:
            self.cache[thread_id] = {}
        self.cache[thread_id][pattern_hash] = self.cache[thread_id].get(pattern_hash, 0) + 1
```

### 2. Улучшенная статистика
```python
@dataclass
class PrecleanStats:
    original_length: int
    cleaned_length: int
    removed_signatures: int
    removed_quotes: int
    removed_disclaimers: int
    tokens_saved: int
    processing_time: float
```

## 📈 Система статистики

### Метрики эффективности
1. **Сокращение размера**: % уменьшения текста
2. **Экономия токенов**: Расчетная экономия для LLM
3. **Сохранение контента**: % важной информации сохранено
4. **Скорость обработки**: Время на письмо

### Отчеты
- `data/logs/precleaner_stats_YYYYMMDD.json` - детальная статистика
- `data/logs/precleaner_summary_YYYYMMDD.md` - сводный отчет

## 🔧 Техническая реализация

### 1. Адаптер PreCleaner
```python
# src/fetcher/utils/precleaner_adapter.py
class PreCleanerAdapter:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.thread_cache = ThreadCache()
        self.sender_cache = SenderCache()
        self.config = self.load_config()
    
    def preclean_text(self, text, thread_id, sender_email):
        """Адаптер для интеграции с Email Fetcher"""
        from .precleaner.core import preclean_email_for_llm
        
        caches = {
            'thread': self.thread_cache,
            'sender': self.sender_cache
        }
        
        result = preclean_email_for_llm(
            text, thread_id, sender_email, self.config, caches
        )
        
        return result
```

### 2. Модификация Email Fetcher
```python
# В src/fetcher/core/email_processor.py
def process_email_content(self, raw_text, thread_id, sender_email):
    # Базовая очистка через EnhancedTextCleaner
    base_cleaned = self.text_cleaner.clean_html_aggressively(raw_text)
    
    # Интеллектуальная пред-очистка через PreCleaner
    preclean_result = self.text_cleaner.precleaner.preclean_text(
        base_cleaned, thread_id, sender_email
    )
    
    # Сохраняем статистику
    self.save_precleaning_stats(preclean_result)
    
    return preclean_result.body_clean_llm
```

## 🧪 Тестирование

### 1. Unit тесты
- Тестирование сегментации текста
- Тестирование кэширования паттернов
- Тестирование сохранения важного контента

### 2. Интеграционные тесты
- Тестирование на реальных письмах (100-1000 шт)
- Сравнение качества до/после PreCleaner
- Проверка экономии токенов

## 📅 План внедрения

### Фаза 1: Подготовка (1-2 дня)
1. Создание адаптера PreCleaner
2. Интеграция в EnhancedTextCleaner
3. Базовое тестирование

### Фаза 2: Миграция (2-3 дня)
1. Создание скрипта поиска обрезанных писем
2. Разработка CLI утилиты миграции
3. Бэкап и перес загрузка данных

### Фаза 3: Оптимизация (2-3 дня)
1. Сбор статистики работы PreCleaner
2. Настройка паттернов под конкретные данные
3. Оптимизация производительности

### Фаза 4: Продакшн (1 день)
1. Финальное тестирование
2. Развертывание в production
3. Мониторинг работы

## 🎯 Ожидаемые результаты

1. **Экономия токенов**: 30-50% сокращение размера текстов
2. **Сохранение контента**: 95%+ важной информации сохранено
3. **Улучшение качества LLM**: Более точное извлечение сущностей
4. **Снижение стоимости**: Экономия на API вызовах LLM

## 🔄 Обратная совместимость

- Сохранение старого API EnhancedTextCleaner
- Возможность отключения PreCleaner через конфиг
- Graceful fallback при ошибках PreCleaner

## 📝 Документация

1. **README_PRECLEANER.md** - руководство по использованию
2. **API_REFERENCE.md** - описание API
3. **PERFORMANCE_REPORT.md** - отчет по производительности
4. **MIGRATION_GUIDE.md** - руководство миграции

---

**Статус**: План готов к реализации  
**Следующие шаги**: Создание адаптера и интеграция