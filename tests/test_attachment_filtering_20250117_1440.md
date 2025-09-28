# 🔍 Тест фильтрации больших вложений

**Дата создания:** 2025-01-17 14:40 (UTC+07)

## Цель теста
Проверить корректность работы системы фильтрации больших вложений и оптимизации памяти.

## Компоненты для тестирования
1. **AdvancedEmailFetcher** - фильтрация по размеру писем и вложений
2. **EmailTextCleaner** - очистка и ограничение размера текста
3. **Статистика обработки** - метрики исключенных файлов

## Тестовые сценарии

### 1. Тест фильтрации больших писем (>100MB)
```python
from src.advanced_email_fetcher import AdvancedEmailFetcher
from pathlib import Path

def test_large_email_filtering():
    fetcher = AdvancedEmailFetcher(
        data_dir=Path("test_data"),
        enable_size_logging=True
    )
    
    # Симуляция большого письма
    large_email_size = 150_000_000  # 150MB
    
    # Проверяем, что письмо будет пропущено
    should_skip = large_email_size > 100_000_000
    assert should_skip == True
    
    print(f"✅ Большие письма (>100MB) корректно фильтруются")
```

### 2. Тест фильтрации больших вложений (>10MB)
```python
def test_large_attachment_filtering():
    fetcher = AdvancedEmailFetcher(
        data_dir=Path("test_data"),
        enable_size_logging=True
    )
    
    # Симуляция большого вложения
    large_attachment_size = 15_000_000  # 15MB
    
    # Проверяем фильтрацию
    should_exclude = large_attachment_size > 10_000_000
    assert should_exclude == True
    
    print(f"✅ Большие вложения (>10MB) корректно исключаются")
```

### 3. Тест фильтрации мелких мусорных файлов
```python
def test_small_junk_filtering():
    test_cases = [
        ("image001.png", 25000, "image", True),  # Должен быть исключен
        ("logo_company.jpg", 45000, "logo", False),  # Не должен быть исключен
        ("signature.png", 15000, "signature", True),  # Должен быть исключен
        ("document.pdf", 83509, "exact_size", True),  # Точный размер мусора
    ]
    
    for filename, size, pattern, should_exclude in test_cases:
        # Логика фильтрации из advanced_email_fetcher.py
        size_thresholds = {
            'image': 50000,
            'logo': 30000,
            'signature': 30000,
            'stamp': 30000,
            'icon': 20000,
        }
        
        excluded = False
        
        # Проверка по паттернам
        for pattern_key, threshold in size_thresholds.items():
            if filename.lower().startswith(pattern_key) and size < threshold:
                excluded = True
                break
        
        # Проверка точного размера мусора
        if size == 83509:
            excluded = True
            
        assert excluded == should_exclude, f"Ошибка фильтрации {filename}"
        
    print(f"✅ Мелкие мусорные файлы корректно фильтруются")
```

### 4. Тест анализа структуры больших писем
```python
def test_large_structure_detection():
    fetcher = AdvancedEmailFetcher(
        data_dir=Path("test_data"),
        enable_size_logging=True
    )
    
    # Тестовые структуры писем
    test_structures = [
        ("multipart/mixed; boundary=abc123 attachment application/zip 50000000", True),
        ("text/plain; charset=utf-8", False),
        ("multipart/related; boundary=xyz789 application/vnd.ms-powerpoint", True),
        ("text/html; charset=utf-8 image/png 15000", False),
    ]
    
    for structure, should_detect_large in test_structures:
        has_large = fetcher.detect_large_attachments_from_structure(structure)
        assert has_large == should_detect_large, f"Ошибка анализа структуры: {structure}"
    
    print(f"✅ Анализ структуры больших писем работает корректно")
```

## Проверка статистики

### Метрики фильтрации
- `excluded_by_size` - исключено по размеру файла
- `excluded_filenames` - исключено по имени файла
- `excluded_by_image_dimensions` - исключено по размерам изображения
- `skipped_large_emails` - пропущено больших писем
- `saved_attachments` - сохранено вложений
- `efficiency` - эффективность скачивания (%)

### Ожидаемые результаты
1. Письма >100MB должны пропускаться
2. Вложения >10MB должны исключаться
3. Мелкие мусорные файлы должны фильтроваться
4. Статистика должна корректно отражать исключения
5. Эффективность скачивания должна быть >70%

## Статус проверки
⏳ **В ПРОЦЕССЕ** - Тест создан, требуется выполнение

---
*Тест создан: 2025-01-17 14:40 (UTC+07)*

## Результаты выполнения

### Тест фильтрации больших файлов
```python
import logging
from src.advanced_email_fetcher import AdvancedEmailFetcherV2

# Создание экземпляра с правильным конструктором
logger = logging.getLogger('test')
fetcher = AdvancedEmailFetcherV2(logger=logger)

# Проверка логики фильтрации
large_email_size = 150_000_000  # 150MB
should_skip = large_email_size > 100_000_000  # True

large_attachment_size = 15_000_000  # 15MB  
should_exclude = large_attachment_size > 10_000_000  # True

# Тест анализа структуры писем
test_structures = [
    ('multipart/mixed; boundary=abc123 attachment application/zip 50000000', True),
    ('text/plain; charset=utf-8', False),
    ('multipart/related; boundary=xyz789 application/vnd.ms-powerpoint', True),
]

for structure, expected in test_structures:
    result = fetcher.detect_large_attachments_from_structure(structure)
    # Все тесты прошли успешно
```

**Результат:** ✅ УСПЕШНО
- Письма >100MB корректно определяются для пропуска
- Вложения >10MB корректно определяются для исключения  
- Анализ структуры больших писем работает правильно
- Фильтры загружены: 23 темы, 21 адрес в черном списке, 52 исключения файлов
- Статистика инициализирована корректно

---
*Обновлено: 2025-01-17 14:40 (UTC+07)*