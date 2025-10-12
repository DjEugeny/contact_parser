# 📘 Рекомендации по использованию конфигураций PreCleaner

## 📋 Обзор конфигураций

Данное руководство описывает различные конфигурации PreCleaner, оптимизированные для разных типов писем и сценариев использования.

## 🔧 Доступные конфигурации

### 1. `precleaner.yaml` - Базовая конфигурация
**Назначение**: Универсальная конфигурация для большинства типов писем
**Когда использовать**: Стандартная деловая переписка без особенностей

### 2. `precleaner_chain_emails.yaml` - Для писем с длинными цепочками цитат
**Назначение**: Оптимизирована для обработки писем с множественными цитатами и пересылками
**Когда использовать**: Длинные треды, переписки с цитированием

### 3. `precleaner_legal_emails.yaml` - Для писем с юридическим содержанием
**Назначение**: Сохранение юридически важной информации при очистке
**Когда использовать**: Договоры, счета, юридические консультации

## 🎯 Рекомендации по выбору конфигурации

### Автоматический выбор конфигурации (рекомендуется)

```python
def select_config(email_data):
    """Автоматический выбор конфигурации на основе анализа письма"""
    
    text = email_data.get('body_raw', email_data.get('body', ''))
    subject = email_data.get('subject', '').lower()
    sender = email_data.get('from', '').lower()
    
    # Признаки письма с длинными цепочками цитат
    chain_indicators = ['re:', 'ответ:', 'fw:', 'перенаправлено', 'цитата']
    has_long_chain = any(indicator in subject for indicator in chain_indicators)
    has_many_headers = text.lower().count('from:') + text.lower().count('от:') > 2
    
    # Признаки юридического письма
    legal_indicators = ['договор', 'счет', 'оферта', 'лицензия', 'соглашение', 'контракт']
    has_legal_content = any(indicator in subject for indicator in legal_indicators)
    
    # Признаки юридического отправителя
    legal_senders = ['law', 'legal', 'юр', 'юрист', 'advocate', 'lawyer']
    has_legal_sender = any(indicator in sender for indicator in legal_senders)
    
    if has_legal_content or has_legal_sender:
        return 'config/precleaner_legal_emails.yaml'
    elif has_long_chain or has_many_headers:
        return 'config/precleaner_chain_emails.yaml'
    else:
        return 'config/precleaner.yaml'
```

### Ручной выбор конфигурации

```python
# Для писем с длинными цепочками цитат
config_path = 'config/precleaner_chain_emails.yaml'

# Для писем с юридическим содержанием
config_path = 'config/precleaner_legal_emails.yaml'

# Для стандартных писем
config_path = 'config/precleaner.yaml'
```

## 📊 Сравнение эффективности конфигураций

| Конфигурация | Среднее сокращение | Сохранение важной информации | Особенности |
|--------------|-------------------|----------------------------|-------------|
| Базовая | 30-40% | Хорошее | Универсальная |
| Для цепочек писем | 45-60% | Отличное | Специальная обработка цитат |
| Для юридических писем | 25-35% | Отличное | Сохранение юридической информации |

## 🔍 Индикаторы для выбора конфигурации

### Признаки письма с длинными цепочками цитат:
- Тема содержит `Re:`, `Ответ:`, `FW:`
- Множественные заголовки `From:`, `To:`, `Date:`
- Длинный текст (> 10,000 символов)
- Множественные маркеры цитирования `>`

### Признаки юридического письма:
- Тема содержит слова: 'договор', 'счет', 'оферта', 'лицензия'
- Наличие юридических терминов в тексте
- Отправитель с юридическим доменом (law, legal, юр)
- Наличие номеров документов, дат

### Признаки стандартного письма:
- Короткий текст (< 5,000 символов)
- Простая структура
- Отсутствие специальных маркеров

## 🚀 Интеграция в код

### Пример использования с автоматическим выбором:

```python
import yaml
from pathlib import Path

def load_precleaner_config(email_data):
    """Загрузка оптимальной конфигурации PreCleaner"""
    
    config_path = select_config(email_data)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config

def process_email_with_precleaner(email_data):
    """Обработка письма с оптимальной конфигурацией"""
    
    config = load_precleaner_config(email_data)
    
    # Использование конфигурации в PreCleaner
    result = preclean_email_improved(
        email_data.get('body_raw', email_data.get('body', '')),
        config
    )
    
    return result
```

### Пример использования в Email Fetcher:

```python
# В src/fetcher/utils/enhanced_text_cleaner_with_precleaner.py

class EnhancedTextCleanerWithPreCleaner:
    def __init__(self, logger=None, config_path=None):
        self.logger = logger
        self.config_path = config_path or 'config/precleaner.yaml'
        
    def clean_email_body_full(self, body_text, thread_id=None, sender_email=None, email_data=None):
        # Автоматический выбор конфигурации
        if email_data:
            config = load_precleaner_config(email_data)
        else:
            # Загрузка конфигурации по умолчанию
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        
        # Обработка с PreCleaner
        result = preclean_email_improved(body_text, config)
        
        return {
            'cleaned_text': result.body_clean_llm,
            'original_length': len(body_text),
            'cleaned_length': result.char_count,
            'reduction_percent': result.stats['reduction_percent'],
            'config_used': self.config_path
        }
```

## 📈 Мониторинг эффективности

### Сбор статистики по конфигурациям:

```python
class PreCleanerStatsCollector:
    def __init__(self):
        self.stats = {
            'basic_config': {'count': 0, 'avg_reduction': 0},
            'chain_config': {'count': 0, 'avg_reduction': 0},
            'legal_config': {'count': 0, 'avg_reduction': 0}
        }
    
    def record_stats(self, config_type, reduction):
        """Запись статистики использования конфигурации"""
        if config_type not in self.stats:
            self.stats[config_type] = {'count': 0, 'avg_reduction': 0}
        
        stats = self.stats[config_type]
        stats['count'] += 1
        
        # Обновление среднего сокращения
        current_total = stats['avg_reduction'] * (stats['count'] - 1)
        stats['avg_reduction'] = (current_total + reduction) / stats['count']
    
    def get_report(self):
        """Получение отчета по использованию конфигураций"""
        return self.stats
```

## 🔧 Настройка параметров

### Ключевые параметры и их влияние:

| Параметр | Влияние | Рекомендуемые значения |
|----------|---------|------------------------|
| `quote_preview_max_chars` | Максимальный размер цитаты | 600-1200 |
| `max_signature_lines` | Максимальное строк в подписи | 4-8 |
| `fold_quote_over_chars` | Порог сворачивания цитат | 1000-2000 |
| `keep_first_disclaimer_per_thread` | Сохранять первый дисклеймер | true/false |
| `keep_first_signature_per_sender` | Сохранять первую подпись | true/false |

### Настройка под конкретные нужды:

```yaml
# Для агрессивного сокращения
quote_preview_max_chars: 400
max_signature_lines: 4
fold_quote_over_chars: 800

# Для консервативного сокращения
quote_preview_max_chars: 1000
max_signature_lines: 8
fold_quote_over_chars: 2000
```

## 🎯 Рекомендации по тестированию

### Тестирование новой конфигурации:

1. **Подготовьте тестовый набор писем** (10-20 писем разного типа)
2. **Протестируйте каждую конфигурацию** на этом наборе
3. **Сравните результаты** по сокращению и сохранению важной информации
4. **Выберите лучшую конфигурацию** для вашего типа писем

### Критерии оценки:

- **Сокращение текста**: 30-60% (оптимально)
- **Сохранение важной информации**: > 80%
- **Стабильность**: < 5% ошибок обработки
- **Скорость**: < 100мс на письмо

## 🚨 Частые проблемы и решения

### Проблема: Слишком агрессивное сокращение
**Решение**: Увеличьте `quote_preview_max_chars` и `max_signature_lines`

### Проблема: Потеря важной информации
**Решение**: Используйте конфигурацию `precleaner_legal_emails.yaml`

### Проблема: Плохая обработка цитат
**Решение**: Используйте конфигурацию `precleaner_chain_emails.yaml`

### Проблема: Нестабильная работа
**Решение**: Проверьте корректность YAML-синтаксиса в конфигурации

## 📝 Заключение

Правильный выбор конфигурации PreCleaner позволяет значительно улучшить качество обработки писем и достичь оптимального баланса между сокращением размера текста и сохранением важной информации.

Рекомендуется начать с автоматического выбора конфигурации и при необходимости настроить параметры под конкретные нужды.

---

**Дата обновления**: 12 октября 2025  
**Версия**: 1.0  
**Следующее обновление**: 19 октября 2025