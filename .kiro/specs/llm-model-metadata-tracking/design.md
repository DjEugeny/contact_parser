# Design Document

## Overview

Эта функция добавляет отслеживание конкретных моделей LLM в метаданные результатов обработки. Текущая реализация уже возвращает информацию о модели из провайдеров, но она теряется при сохранении в финальный JSON. Решение заключается в минимальных изменениях в `api_pipeline_validator.py` для сохранения поля `model` и улучшении логирования в `ModelsManager`.

## Architecture

### Текущий поток данных

```
Provider (OpenRouter/Replicate)
  ↓ возвращает: {content, provider, model, usage, response_time}
api_pipeline_validator.process_email()
  ↓ создает llm_metadata: {provider, response_time, timestamp}
  ↓ теряет информацию о model!
Сохранение в JSON
  ↓ финальный результат: только provider, без model
```

### Новый поток данных

```
Provider (OpenRouter/Replicate)
  ↓ возвращает: {content, provider, model, usage, response_time}
api_pipeline_validator.process_email()
  ↓ создает llm_metadata: {provider, model, response_time, timestamp}
  ↓ сохраняет информацию о model!
Сохранение в JSON
  ↓ финальный результат: provider + model
```

## Components and Interfaces

### 1. Provider Response Format (уже существует)

Оба провайдера уже возвращают правильный формат:

```python
# OpenRouter и Replicate уже возвращают:
{
    'content': str,
    'provider': str,  # 'OpenRouter' или 'Replicate'
    'model': str,     # полное имя модели
    'usage': dict,
    'response_time': float
}
```

**Изменения:** Не требуются, провайдеры уже работают правильно.

### 2. API Pipeline Validator (требует изменений)

**Файл:** `src/api_pipeline_validator.py`

**Текущая реализация (строки ~1088-1096):**
```python
# Добавляем метаданные LLM
result['llm_metadata'] = {
    'provider': llm_response.get('provider', 'Unknown'),
    'response_time': llm_response.get('response_time', 0),
    'timestamp': datetime.now().isoformat()
}

# Добавляем usage если есть
if 'usage' in llm_response:
    result['llm_metadata']['usage'] = llm_response['usage']
```

**Новая реализация:**
```python
# Добавляем метаданные LLM
result['llm_metadata'] = {
    'provider': llm_response.get('provider', 'Unknown'),
    'model': llm_response.get('model', 'Unknown'),  # ← ДОБАВИТЬ ЭТУ СТРОКУ
    'response_time': llm_response.get('response_time', 0),
    'timestamp': datetime.now().isoformat()
}

# Добавляем usage если есть
if 'usage' in llm_response:
    result['llm_metadata']['usage'] = llm_response['usage']
```

**Изменения:**
- Добавить одну строку: `'model': llm_response.get('model', 'Unknown')`
- Это минимальное изменение, которое решает основную проблему

### 3. ModelsManager Logging (улучшение)

**Файл:** `src/config/models_manager.py`

**Текущая реализация (метод `get_current_model`):**
```python
def get_current_model(self, provider: str) -> Optional[Dict[str, Any]]:
    """Получить текущую активную модель для провайдера"""
    if provider not in self.provider_models:
        return None
    
    current_index = self.current_model_index.get(provider, 0)
    models = self.provider_models[provider]
    
    if 0 <= current_index < len(models):
        return models[current_index]
    
    return None
```

**Новая реализация:**
```python
def get_current_model(self, provider: str) -> Optional[Dict[str, Any]]:
    """Получить текущую активную модель для провайдера"""
    if provider not in self.provider_models:
        return None
    
    current_index = self.current_model_index.get(provider, 0)
    models = self.provider_models[provider]
    
    if 0 <= current_index < len(models):
        model = models[current_index]
        # Логируем выбранную модель для отладки
        logger.info(f"🎯 ModelsManager: {provider} использует модель {model['name']} (priority {model['priority']})")
        return model
    
    return None
```

**Изменения:**
- Добавить логирование выбранной модели с эмодзи для видимости
- Показывать провайдер, имя модели и приоритет

### 4. Provider Logging (опционально)

**Файлы:** `src/providers/openrouter.py`, `src/providers/replicate_provider.py`

**Опциональное улучшение:** Добавить логирование перед запросом к API:

```python
# В методе generate() перед вызовом API
logger.info(f"🤖 {self.config.provider}: запрос к модели {self.config.model}")
```

Это поможет видеть в логах последовательность использования моделей.

## Data Models

### LLM Metadata Structure

**Старый формат (без model):**
```json
{
  "llm_metadata": {
    "provider": "Replicate",
    "response_time": 18.52,
    "timestamp": "2025-10-08T22:21:00.123456Z",
    "usage": {
      "prompt_tokens": 1234,
      "completion_tokens": 567,
      "total_tokens": 1801
    }
  }
}
```

**Новый формат (с model):**
```json
{
  "llm_metadata": {
    "provider": "OpenRouter",
    "model": "google/gemini-2.0-flash-exp:free",
    "response_time": 45.2,
    "timestamp": "2025-10-08T22:21:00.123456Z",
    "usage": {
      "prompt_tokens": 1234,
      "completion_tokens": 567,
      "total_tokens": 1801
    }
  }
}
```

**Примеры значений model:**
- OpenRouter: `"google/gemini-2.0-flash-exp:free"`, `"meta-llama/llama-3.3-70b-instruct:free"`, `"deepseek/deepseek-chat-v3.1:free"`
- Replicate: `"deepseek-ai/deepseek-v3.1"`, `"anthropic/claude-3.5-sonnet"`

## Error Handling

### Отсутствие информации о модели

**Сценарий:** Провайдер не вернул поле `model` (маловероятно, но возможно)

**Решение:**
```python
'model': llm_response.get('model', 'Unknown')
```

Если поле отсутствует, используется значение `"Unknown"`.

### Обратная совместимость

**Сценарий:** Чтение старых результатов без поля `model`

**Решение:** Код, который читает результаты, должен использовать `.get('model', 'Unknown')` при доступе к метаданным:

```python
# Безопасное чтение
model = result['llm_metadata'].get('model', 'Unknown')
provider = result['llm_metadata'].get('provider', 'Unknown')
```

Старые файлы останутся валидными, просто будут показывать `"Unknown"` для модели.

## Testing Strategy

### Unit Tests

**Не требуются** - изменения минимальны и не меняют логику.

### Integration Tests

**Тест 1: Проверка сохранения model в метаданных**

```python
# После обработки письма
result = process_email(email_data)
assert 'model' in result['llm_metadata']
assert result['llm_metadata']['model'] != 'Unknown'
assert result['llm_metadata']['provider'] in ['OpenRouter', 'Replicate']
```

**Тест 2: Проверка формата model**

```python
# Для OpenRouter
if result['llm_metadata']['provider'] == 'OpenRouter':
    assert '/' in result['llm_metadata']['model']  # должен быть namespace
    
# Для Replicate
if result['llm_metadata']['provider'] == 'Replicate':
    assert '-' in result['llm_metadata']['model']  # обычно содержит дефисы
```

### Manual Testing

**Тест 3: Обработка реальных писем**

1. Запустить обработку писем за 2025-07-23
2. Проверить, что в логах видно:
   ```
   🎯 ModelsManager: OpenRouter использует модель google/gemini-2.0-flash-exp:free (priority 1)
   ```
3. Открыть результат в JSON и проверить:
   ```json
   "llm_metadata": {
     "provider": "OpenRouter",
     "model": "google/gemini-2.0-flash-exp:free",
     ...
   }
   ```

**Тест 4: Переключение моделей**

1. Создать ситуацию, когда первая модель падает (например, rate limit)
2. Проверить в логах последовательность:
   ```
   🎯 ModelsManager: OpenRouter использует модель google/gemini-2.0-flash-exp:free (priority 1)
   ⚠️ Модель google/gemini-2.0-flash-exp:free упала, переключаемся...
   🎯 ModelsManager: OpenRouter использует модель meta-llama/llama-3.3-70b-instruct:free (priority 2)
   ```
3. Проверить, что в результате сохранена модель, которая успешно обработала письмо

## Implementation Notes

### Минимальность изменений

Решение требует изменения **всего одной строки кода** в основном файле:
- `src/api_pipeline_validator.py`: добавить `'model': llm_response.get('model', 'Unknown')`

Дополнительные изменения (логирование) являются опциональными улучшениями.

### Приоритет изменений

1. **Критично:** Добавить `model` в `llm_metadata` (api_pipeline_validator.py)
2. **Важно:** Добавить логирование в ModelsManager (models_manager.py)
3. **Опционально:** Добавить логирование в провайдеры

### Влияние на производительность

**Нулевое** - мы только сохраняем уже существующее значение, не добавляем новых вычислений или запросов.

### Влияние на размер данных

**Минимальное** - добавляется одно строковое поле (~30-50 символов) на каждый результат.

Пример увеличения размера:
- Было: `"provider": "OpenRouter"` (24 символа)
- Стало: `"provider": "OpenRouter", "model": "google/gemini-2.0-flash-exp:free"` (73 символа)
- Увеличение: ~49 символов ≈ 0.05 KB на письмо

Для 1000 писем: ~50 KB дополнительных данных (незначительно).
