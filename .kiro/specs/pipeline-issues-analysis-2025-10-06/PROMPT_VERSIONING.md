# Система версионирования промптов

**Дата:** 2025-10-08  
**Статус:** Спецификация

---

## 🎯 Цель

Создать систему версионирования промптов для:
- Отслеживания изменений
- A/B тестирования
- Быстрого отката к предыдущим версиям
- Документирования улучшений

---

## 📁 Структура файлов

### Текущая структура:
```
prompts/
├── unified_contact_extraction_structured.txt      # Текущий рабочий промпт
├── unified_contact_extraction_structured_work.txt # Рабочая копия
└── old_unified_contact_extraction_structured_old.txt # Старая версия
```

### Новая структура (после внедрения):
```
prompts/
├── version.json                                    # ✨ Метаданные версий
├── README.md                                       # ✨ Документация
├── unified_contact_extraction_structured.txt      # Fallback (старый)
├── unified_contact_extraction_v1.0.txt            # ✨ Baseline
├── unified_contact_extraction_v1.1.txt            # ✨ Улучшенный
└── unified_contact_extraction_v1.2.txt            # ✨ Будущие версии
```

---

## 🔧 Как это работает

### 1. Файл version.json

```json
{
  "current_version": "1.1",
  "default_file": "unified_contact_extraction_v1.1.txt",
  "versions": {
    "1.0": {
      "date": "2025-10-06",
      "description": "Baseline промпт",
      "validation_error_rate": 0.20,
      "file": "unified_contact_extraction_v1.0.txt",
      "status": "baseline"
    },
    "1.1": {
      "date": "2025-10-08",
      "description": "Улучшенный промпт с явными правилами JSON",
      "validation_error_rate": 0.05,
      "file": "unified_contact_extraction_v1.1.txt",
      "status": "active",
      "changes": [
        "Добавлены строгие правила для null значений",
        "Добавлены примеры enum значений",
        "Добавлены примеры правильного JSON"
      ]
    }
  }
}
```

### 2. Функция загрузки промпта

```python
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_prompt(version: str = None) -> str:
    """
    Загрузка промпта с поддержкой версионирования
    
    Args:
        version: Версия промпта (например "1.1"). 
                 Если None - загружается current_version из version.json
    
    Returns:
        Текст промпта
    
    Examples:
        # Загрузить текущую версию
        prompt = load_prompt()
        
        # Загрузить конкретную версию для A/B теста
        prompt_v10 = load_prompt("1.0")
        prompt_v11 = load_prompt("1.1")
    """
    version_file = Path("prompts/version.json")
    
    # Fallback на старый файл если версионирование не настроено
    if not version_file.exists():
        logger.warning("⚠️ version.json не найден, используется fallback")
        fallback_path = Path("prompts/unified_contact_extraction_structured.txt")
        return fallback_path.read_text(encoding='utf-8')
    
    # Загружаем метаданные версий
    with open(version_file, 'r', encoding='utf-8') as f:
        version_data = json.load(f)
    
    # Если версия не указана - берем текущую
    if version is None:
        version = version_data['current_version']
    
    # Проверяем существование версии
    if version not in version_data['versions']:
        logger.error(f"❌ Версия {version} не найдена в version.json")
        raise ValueError(f"Unknown prompt version: {version}")
    
    # Получаем имя файла для версии
    prompt_file = version_data['versions'][version]['file']
    prompt_path = Path("prompts") / prompt_file
    
    # Проверяем существование файла
    if not prompt_path.exists():
        logger.error(f"❌ Файл промпта не найден: {prompt_path}")
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    logger.info(f"📝 Загружен промпт версии {version}: {prompt_file}")
    return prompt_path.read_text(encoding='utf-8')


def get_prompt_version_info(version: str = None) -> dict:
    """Получить метаданные версии промпта"""
    version_file = Path("prompts/version.json")
    
    if not version_file.exists():
        return {"error": "version.json not found"}
    
    with open(version_file, 'r', encoding='utf-8') as f:
        version_data = json.load(f)
    
    if version is None:
        version = version_data['current_version']
    
    return version_data['versions'].get(version, {})
```

### 3. Использование в коде

**До (старый способ):**
```python
# Где-то в коде
prompt_path = Path("prompts/unified_contact_extraction_structured.txt")
prompt = prompt_path.read_text()
```

**После (с версионированием):**
```python
from prompt_loader import load_prompt

# Загрузить текущую версию
prompt = load_prompt()

# Или для A/B теста
prompt_v10 = load_prompt("1.0")
prompt_v11 = load_prompt("1.1")
```

---

## 📝 Как создать новую версию (например v1.2)

### Шаг 1: Создать файл промпта
```bash
cp prompts/unified_contact_extraction_v1.1.txt \
   prompts/unified_contact_extraction_v1.2.txt
```

### Шаг 2: Внести изменения в v1.2
Отредактируйте `unified_contact_extraction_v1.2.txt`

### Шаг 3: Обновить version.json
```json
{
  "current_version": "1.2",  // ← Изменить на новую версию
  "default_file": "unified_contact_extraction_v1.2.txt",
  "versions": {
    "1.0": { ... },
    "1.1": { ... },
    "1.2": {  // ← Добавить новую версию
      "date": "2025-10-15",
      "description": "Дальнейшие улучшения",
      "validation_error_rate": 0.03,
      "file": "unified_contact_extraction_v1.2.txt",
      "status": "active",
      "changes": [
        "Улучшена обработка edge cases",
        "Добавлены примеры для сложных сценариев"
      ]
    }
  }
}
```

### Шаг 4: Протестировать
```python
# Код автоматически загрузит v1.2
prompt = load_prompt()
```

### Шаг 5: Откатиться если нужно
```json
{
  "current_version": "1.1",  // ← Просто вернуть на предыдущую
  ...
}
```

---

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
    
    # Обновляем version.json с результатами
    update_version_metrics("1.0", metrics_v10)
    update_version_metrics("1.1", metrics_v11)
```

---

## ✅ Преимущества системы

1. **Отслеживание изменений:** Все версии сохранены с метаданными
2. **Быстрый откат:** Просто изменить `current_version` в JSON
3. **A/B тестирование:** Легко сравнить разные версии
4. **Документация:** История изменений в `version.json`
5. **Безопасность:** Старые версии не удаляются
6. **Гибкость:** Можно загрузить любую версию программно

---

## 🚀 План внедрения

1. ✅ Создать спецификацию (этот файл)
2. [ ] Скопировать текущий промпт как v1.0
3. [ ] Создать version.json
4. [ ] Создать функцию load_prompt()
5. [ ] Обновить код, который использует промпт
6. [ ] Создать улучшенный v1.1
7. [ ] Провести A/B тест
8. [ ] Документировать результаты

---

## 📚 Дополнительные возможности

### Автоматическое логирование версии
```python
def process_email_with_logging(email_data):
    version_info = get_prompt_version_info()
    logger.info(f"Processing with prompt v{version_info['version']}")
    
    prompt = load_prompt()
    result = llm.process(email_data, prompt)
    
    # Сохраняем версию промпта в результате
    result['prompt_version'] = version_info['version']
    return result
```

### Статистика по версиям
```python
def get_version_stats():
    """Получить статистику по всем версиям"""
    version_file = Path("prompts/version.json")
    with open(version_file, 'r') as f:
        data = json.load(f)
    
    for version, info in data['versions'].items():
        print(f"v{version}: {info['description']}")
        print(f"  Error rate: {info.get('validation_error_rate', 'N/A')}")
        print(f"  Status: {info.get('status', 'unknown')}")
```

---

**Дата создания:** 2025-10-08  
**Автор:** Kiro AI Assistant
