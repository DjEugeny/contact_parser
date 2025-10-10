# Система версионирования промптов

## 📋 Обзор

Эта папка содержит версионированные промпты для извлечения контактов и организаций из деловой переписки.

## 📁 Структура файлов

```
prompts/
├── version.json                                    # Метаданные версий
├── README.md                                       # Эта документация
├── unified_contact_extraction_structured.txt      # Fallback (старый файл)
├── unified_contact_extraction_v1.0.txt            # Baseline версия
└── unified_contact_extraction_v1.1.txt            # Улучшенная версия (будет создана)
```

## 🔧 Использование

### Загрузка текущей версии промпта

```python
from prompt_loader import load_prompt

# Загрузить текущую версию (указана в version.json)
prompt = load_prompt()
```

### Загрузка конкретной версии

```python
# Для A/B тестирования или отката
prompt_v10 = load_prompt("1.0")
prompt_v11 = load_prompt("1.1")
```

### Получение информации о версии

```python
from prompt_loader import get_prompt_version_info

# Получить метаданные текущей версии
info = get_prompt_version_info()
print(f"Версия: {info['version']}")
print(f"Описание: {info['description']}")
print(f"Validation error rate: {info['validation_error_rate']}")
```

## 📝 История версий

### v1.0 (2025-10-06) - Baseline
- Исходная версия промпта
- Базовые правила извлечения контактов и организаций
- Поддержка коммерческих предложений
- Правила для телефонов и адресов
- **Validation error rate:** 20%
- **Статус:** baseline

### v1.1 (2025-10-10) - Улучшенная версия
- Добавлены строгие правила для null значений в обязательных полях
- Добавлен полный список допустимых значений interaction_type с запретом 'info_request'
- Добавлены 3 примера правильного JSON с разными сценариями
- Добавлены примеры неправильного JSON с объяснением ошибок
- Добавлена финальная проверка перед отправкой (7 пунктов)
- Улучшены инструкции по обязательным связям между сущностями
- **Целевой validation error rate:** <5%
- **Статус:** active (требуется тестирование)

## 🚀 Создание новой версии

### Шаг 1: Создать файл промпта
```bash
cp prompts/unified_contact_extraction_v1.0.txt \
   prompts/unified_contact_extraction_v1.1.txt
```

### Шаг 2: Внести изменения
Отредактируйте новый файл `unified_contact_extraction_v1.1.txt`

### Шаг 3: Обновить version.json
Добавьте новую версию в `version.json`:

```json
{
  "current_version": "1.1",
  "default_file": "unified_contact_extraction_v1.1.txt",
  "versions": {
    "1.0": { ... },
    "1.1": {
      "date": "2025-10-08",
      "description": "Улучшенный промпт с явными правилами JSON",
      "validation_error_rate": 0.05,
      "file": "unified_contact_extraction_v1.1.txt",
      "status": "active",
      "changes": [
        "Добавлены строгие правила для null значений",
        "Добавлены примеры enum значений"
      ]
    }
  }
}
```

### Шаг 4: Протестировать
```python
# Код автоматически загрузит новую версию
prompt = load_prompt()
```

### Шаг 5: Откатиться при необходимости
Просто измените `current_version` в `version.json` на предыдущую версию.

## 🧪 A/B тестирование

```python
def ab_test_prompts():
    """Сравнение двух версий промптов"""
    
    # Загружаем обе версии
    prompt_v10 = load_prompt("1.0")
    prompt_v11 = load_prompt("1.1")
    
    # Обрабатываем одни и те же письма
    results_v10 = process_emails(emails, prompt_v10)
    results_v11 = process_emails(emails, prompt_v11)
    
    # Сравниваем метрики
    metrics_v10 = calculate_metrics(results_v10)
    metrics_v11 = calculate_metrics(results_v11)
    
    print(f"v1.0 validation errors: {metrics_v10['validation_error_rate']}")
    print(f"v1.1 validation errors: {metrics_v11['validation_error_rate']}")
```

## ✅ Преимущества системы

1. **Отслеживание изменений:** Все версии сохранены с метаданными
2. **Быстрый откат:** Просто изменить `current_version` в JSON
3. **A/B тестирование:** Легко сравнить разные версии
4. **Документация:** История изменений в `version.json`
5. **Безопасность:** Старые версии не удаляются
6. **Гибкость:** Можно загрузить любую версию программно

## 📊 Метрики качества

| Версия | Validation Error Rate | Статус |
|--------|----------------------|--------|
| v1.0   | 20%                  | baseline |
| v1.1   | не измерен (цель <5%) | active (требуется тестирование) |

## 🔗 Связанные файлы

- `.kiro/specs/pipeline-issues-analysis-2025-10-06/PROMPT_VERSIONING.md` - Детальная спецификация
- `.kiro/specs/pipeline-issues-analysis-2025-10-06/tasks.md` - План задач
- `.kiro/specs/pipeline-issues-analysis-2025-10-06/analysis-report.md` - Анализ проблем

---

**Дата создания:** 2025-10-10  
**Последнее обновление:** 2025-10-10
