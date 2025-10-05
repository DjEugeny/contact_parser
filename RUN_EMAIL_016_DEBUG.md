# 🚀 Инструкция по запуску обработки письма 016 с отладкой

## Цель
Запустить обработку письма 016 заново с включенным DEBUG-логированием, чтобы выявить, почему организация МИЛЛАБ не получает city=Москва из вложения.

## Подготовка

### 1. Проверить, что исправления применены
```bash
python test_integration_fix.py
```

Должно показать:
- ✅ Исправление в IntegratedLLMProcessor применено
- ✅ Проверка типов в AttachmentEvidenceExtractor реализована
- ✅ AttachmentEvidenceExtractor импортирован в PostProcessor

### 2. Включить DEBUG-логирование
Создать файл `logging_config.py` или изменить настройки логирования в `src/integrated_llm_processor.py`:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Запуск обработки

### Вариант 1: Через основной пайплайн
```bash
# Найти команду для обработки одного письма
# Обычно это что-то вроде:
python src/main_new.py process-email data/emails/2025-07-29/email_016_20250729_20250729_dna-technology_ru_6360137e.json
```

### Вариант 2: Через IntegratedLLMProcessor напрямую
Создать скрипт `run_email_016.py`:

```python
#!/usr/bin/env python3
import sys
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from integrated_llm_processor import IntegratedLLMProcessor

# Создаем процессор
processor = IntegratedLLMProcessor(test_mode=False)

# Обрабатываем письмо 016
email_file = "data/emails/2025-07-29/email_016_20250729_20250729_dna-technology_ru_6360137e.json"
result = processor.process_single_email(email_file)

print("\n" + "="*80)
print("РЕЗУЛЬТАТ ОБРАБОТКИ")
print("="*80)

# Проверяем организацию МИЛЛАБ
organizations = result.get('processed_result', {}).get('organizations', [])
for org in organizations:
    if 'МИЛЛАБ' in org.get('name', ''):
        print(f"\nОрганизация МИЛЛАБ:")
        print(f"  city: {org.get('city')}")
        print(f"  address: {org.get('address')}")

# Проверяем метаданные обогащения
metadata = result.get('processed_result', {}).get('postprocessing_metadata', {})
enrichment = metadata.get('enrichment', {})
location_enrichment = enrichment.get('org_location_from_attachments', {})

print(f"\nМетаданные обогащения локации:")
if location_enrichment:
    print(f"  ✅ Найдены: {location_enrichment}")
else:
    print(f"  ❌ Пусты!")
```

Запустить:
```bash
python run_email_016.py 2>&1 | tee email_016_debug.log
```

## Что искать в логах

### 1. Вызов PostProcessor
```
INFO - Начало постобработки ответа LLM
```

### 2. Передача email_data
```
DEBUG - email_data type: <class 'dict'>
DEBUG - email_data keys: ['from', 'to', 'cc', 'subject', 'date', 'thread_id', 'has_attachments', 'attachments_count', 'attachments']
DEBUG - attachments type: <class 'list'>, value: list of 4 items
```

### 3. Начало обогащения локации
```
INFO - Starting location enrichment from attachments
```

### 4. Обработка вложений
```
INFO - Анализируем ВСЕ 4 вложений для извлечения локации
DEBUG - First attachment keys: ['original_filename', 'status', ...]
```

### 5. Обработка каждого вложения
```
DEBUG - Обрабатываем вложение: Ком.пред.14.03.2025 для Москва Компания МИЛЛАБ...
DEBUG - Найдено организаций в тексте: X
```

### 6. Найденные доказательства
```
INFO - Found X location evidence items
DEBUG - Найдено доказательство для МИЛЛАБ: Москва
```

### 7. Применение обогащения
```
INFO - Обогащаем X организаций из Y доказательств
INFO - Обогащено X организаций
```

## Анализ результатов

### Если логи отсутствуют полностью
❌ **Проблема:** PostProcessor не вызывается или вызывается без email_data
- Проверить, что IntegratedLLMProcessor действительно вызывает `postprocessor.process_llm_response(llm_result, email_metadata)`

### Если логи есть, но "No attachments found"
❌ **Проблема:** email_data не содержит attachments или содержит неправильный тип
- Проверить, что `email_metadata['attachments']` - это список
- Проверить, что список не пустой

### Если логи есть, но "No location evidence found"
❌ **Проблема:** AttachmentEvidenceExtractor не находит доказательства
- Проверить, что OCR-текст читается корректно
- Проверить, что организации находятся в тексте
- Проверить, что локация извлекается

### Если доказательства найдены, но не применены
❌ **Проблема:** OrgLocationEnrichment не сопоставляет доказательства с организациями
- Проверить fuzzy matching
- Проверить нормализацию названий
- Проверить конфигурацию `apply_if_empty_only`

### Если все работает, но город не появляется
❌ **Проблема:** Обогащение применяется, но не сохраняется в финальный результат
- Проверить, что организации обновляются in-place
- Проверить, что метаданные записываются корректно

## Ожидаемый результат

После успешной обработки:
```
Организация МИЛЛАБ:
  city: Москва
  address: None (или адрес из КП)

Метаданные обогащения локации:
  ✅ Найдены: {
    'evidence_count': 1+,
    'organizations_enriched': 1+,
    'cities_added': 1+,
    ...
  }
```

## Следующие шаги

1. Запустить обработку с логированием
2. Сохранить логи в файл
3. Проанализировать логи по чек-листу выше
4. Определить точное место, где происходит сбой
5. Исправить проблему