# 🔄 Инструкция по переобработке письма 016

## Проблема
Файл `email_016_..._processed.json` был обработан **ДО** наших исправлений (дата: 2025-10-05T00:16:39).
Метаданные `org_location_from_attachments` пусты, потому что обработка была выполнена со старым кодом.

## Решение
Нужно **переобработать письмо заново** с нашими исправлениями.

## Шаг 1: Удалить старый обработанный файл

```bash
rm data/llm_results/2025-07-29/email_016_20250729_20250729_dna_technology_ru_6360137e_*_processed.json
```

Или переименовать для сохранения:
```bash
mv data/llm_results/2025-07-29/email_016_20250729_20250729_dna_technology_ru_6360137e_20251005_001450_001639_processed.json \
   data/llm_results/2025-07-29/email_016_20250729_20250729_dna_technology_ru_6360137e_20251005_001450_001639_processed.json.old
```

## Шаг 2: Запустить обработку заново

### Вариант 1: Через интерактивное меню
```bash
python src/main_new.py interactive
```

Затем выбрать опцию обработки писем и указать письмо 016.

### Вариант 2: Через полный пайплайн
```bash
python src/main_new.py full-pipeline
```

### Вариант 3: Напрямую через IntegratedLLMProcessor
Создать скрипт `reprocess_email_016.py`:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

# Настройка путей
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Импорт с правильными путями
import os
os.chdir(project_root)

from src.integrated_llm_processor import IntegratedLLMProcessor

# Создаем процессор
processor = IntegratedLLMProcessor(test_mode=False)

# Обрабатываем письмо
email_file = "data/emails/2025-07-29/email_016_20250729_20250729_dna-technology_ru_6360137e.json"
result = processor.process_single_email(email_file)

# Проверяем результат
organizations = result.get('processed_result', {}).get('organizations', [])
for org in organizations:
    if 'МИЛЛАБ' in org.get('name', ''):
        print(f"\nОрганизация МИЛЛАБ:")
        print(f"  city: {org.get('city')}")
        print(f"  address: {org.get('address')}")
```

Запустить:
```bash
python reprocess_email_016.py
```

## Шаг 3: Проверить результат

После обработки проверить новый файл:

```bash
python test_debug_location_enrichment.py
```

Должно показать:
- ✅ МИЛЛАБ имеет город: Москва
- ✅ Метаданные обогащения локации найдены

## Ожидаемый результат

В новом обработанном файле должно быть:

```json
{
  "processed_result": {
    "organizations": [
      {
        "name": "МИЛЛАБ",
        "city": "Москва",  // ← Должно появиться!
        ...
      }
    ],
    "postprocessing_metadata": {
      "enrichment": {
        "org_location_from_attachments": {
          "evidence_count": 7,
          "organizations_enriched": 1,
          "cities_added": 1,
          ...
        }
      }
    }
  }
}
```

## Если не работает

1. **Проверить логи** - должны появиться сообщения:
   - `🔍 DEBUG: email_data type:`
   - `🔍 Анализируем ВСЕ X вложений`
   - `📄 Обрабатываем вложение:`

2. **Проверить, что исправления применены**:
   ```bash
   python test_integration_fix.py
   ```

3. **Проверить, что тесты проходят**:
   ```bash
   python test_real_ocr_data.py
   ```

## Важно!

Наши исправления:
- ✅ `IntegratedLLMProcessor` передает полные данные о вложениях
- ✅ `AttachmentEvidenceExtractor` упрощен и работает корректно
- ✅ Добавлено детальное логирование

Все тесты показывают, что код работает. Просто нужно переобработать письмо с новым кодом!