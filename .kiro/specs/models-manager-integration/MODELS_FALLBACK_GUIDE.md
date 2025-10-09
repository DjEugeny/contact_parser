# 🔄 Руководство по системе Fallback моделей

## 📋 Что это?

Система автоматического переключения между моделями LLM при ошибках.

### Возможности:
- ✅ Автоматическое переключение на следующую модель при ошибках
- ✅ Приоритизация моделей (1, 2, 3, 4, 5...)
- ✅ Отдельные списки для OpenRouter и Replicate
- ✅ Логирование всех переключений
- ✅ Информация о требованиях приватности для каждой модели

## 📁 Структура

```
config/
  └── models_config.yaml       # Конфигурация моделей
src/
  └── config/
      └── models_manager.py    # Менеджер моделей
data/
  └── logs/
      └── model_fallback.log   # Лог переключений
```

## ⚙️ Конфигурация

### Файл `config/models_config.yaml`

```yaml
openrouter:
  models:
    - name: "qwen/qwen3-235b-a22b:free"
      priority: 1
      description: "Qwen 235B - работает без публикации промптов"
      requires_prompt_publication: false  # 🔓 Не требует
      
    - name: "deepseek/deepseek-chat-v3.1:free"
      priority: 2
      description: "DeepSeek Chat v3.1"
      requires_prompt_publication: true   # 🔒 Требует!
```

### Поля модели:

- **name** - полное имя модели
- **priority** - приоритет (1 = первая, 2 = вторая и т.д.)
- **description** - описание модели
- **requires_prompt_publication** - требует ли публикацию промптов

### Настройки fallback:

```yaml
fallback:
  enabled: true
  max_retries_per_model: 3  # Попыток перед переключением
  switch_on_errors:
    - "404"           # Модель недоступна
    - "429"           # Rate limit
    - "data policy"   # Проблемы с приватностью
```

## 🚀 Использование

### 1. Базовое использование

```python
from config.models_manager import ModelsManager

# Создаем менеджер
manager = ModelsManager()

# Получаем текущую модель
model = manager.get_current_model('openrouter')
print(f"Текущая модель: {model.name}")

# Делаем запрос к LLM...
# Если ошибка:
manager.report_error('openrouter', 'HTTP 404: data policy error')
# Автоматически переключится на следующую модель!
```

### 2. Проверка статуса

```python
# Показать статус всех моделей
manager.print_status()

# Или получить как dict
status = manager.get_status()
print(status['openrouter']['current_model'])
```

### 3. Получение всех моделей

```python
# Все модели OpenRouter
models = manager.get_all_models('openrouter')
for model in models:
    print(f"{model.name} - {model.description}")
    if model.requires_prompt_publication:
        print("  ⚠️ Требует публикацию промптов!")
```

### 4. Сброс на первую модель

```python
# После успешного запроса можно вернуться к первой модели
manager.reset_to_first_model('openrouter')
```

## 🔍 Логирование

Все переключения моделей логируются в `data/logs/model_fallback.log`:

```
============================================================
Timestamp: 2025-10-08T15:30:45.123456
Provider: openrouter
Old Model: qwen/qwen3-235b-a22b:free (priority 1)
New Model: deepseek/deepseek-chat-v3.1:free (priority 2)
Reason: Max retries exceeded
```

## 🧪 Тестирование

```bash
# Тест менеджера моделей
python test_models_manager.py
```

Вывод покажет:
- ✅ Текущие модели для каждого провайдера
- ✅ Симуляцию ошибок и переключений
- ✅ Список всех доступных моделей
- ✅ Информацию о требованиях приватности

## 📊 Интеграция с существующим кодом

### В `config_manager.py`:

```python
from config.models_manager import ModelsManager

class ConfigManager:
    def __init__(self):
        # Создаем менеджер моделей
        self.models_manager = ModelsManager()
        
        # Получаем текущие модели
        or_model = self.models_manager.get_current_model('openrouter')
        rep_model = self.models_manager.get_current_model('replicate')
        
        # Используем их в конфигурации
        self.openrouter_model = or_model.name
        self.replicate_model = rep_model.name
```

### В провайдере при ошибке:

```python
async def make_request(self, data):
    try:
        response = await self._do_request(data)
        return response
    except Exception as e:
        # Сообщаем об ошибке менеджеру
        switched = self.models_manager.report_error(
            'openrouter', 
            str(e)
        )
        
        if switched:
            # Модель переключена, пробуем еще раз
            new_model = self.models_manager.get_current_model('openrouter')
            self.config.model = new_model.name
            return await self._do_request(data)
        else:
            raise
```

## 🎯 Сценарии использования

### Сценарий 1: Проблема с приватностью

```
1. Пробуем qwen/qwen3-235b-a22b:free
2. Ошибка "data policy" → переключаемся
3. Пробуем deepseek/deepseek-chat-v3.1:free
4. Работает! ✅
```

### Сценарий 2: Rate limit

```
1. Пробуем первую модель
2. Ошибка 429 (rate limit) → переключаемся
3. Пробуем вторую модель
4. Работает! ✅
```

### Сценарий 3: Все модели исчерпаны

```
1. Пробуем модель 1 → ошибка
2. Пробуем модель 2 → ошибка
3. Пробуем модель 3 → ошибка
4. Пробуем модель 4 → ошибка
5. Пробуем модель 5 → ошибка
6. ❌ Все модели исчерпаны!
7. Переключаемся на другой провайдер (Replicate)
```

## 🔒 О требованиях приватности

### Модели с `requires_prompt_publication: false` (🔓)
Работают с настройками:
- ✅ "Enable free endpoints that may train on inputs" = ON

### Модели с `requires_prompt_publication: true` (🔒)
Требуют дополнительно:
- ✅ "Enable free endpoints that may publish prompts" = ON

**Рекомендация:** Используйте модели с `false` если не хотите публиковать промпты.

## 📝 Добавление новых моделей

### 1. Откройте `config/models_config.yaml`

### 2. Добавьте модель в нужный раздел:

```yaml
openrouter:
  models:
    # ... существующие модели ...
    
    - name: "новая/модель:free"
      priority: 6  # Следующий приоритет
      description: "Описание новой модели"
      requires_prompt_publication: false
```

### 3. Сохраните файл

### 4. Перезапустите приложение

Модель автоматически появится в списке fallback!

## 🎉 Преимущества

1. **Надежность** - автоматическое переключение при ошибках
2. **Гибкость** - легко добавлять/удалять модели
3. **Прозрачность** - все переключения логируются
4. **Безопасность** - информация о требованиях приватности
5. **Простота** - конфигурация в одном YAML файле

## 🔗 Связанные файлы

- `config/models_config.yaml` - конфигурация моделей
- `src/config/models_manager.py` - менеджер моделей
- `test_models_manager.py` - тесты
- `.env` - API ключи (не трогаем!)

---

**Создано:** 08.10.2025  
**Версия:** 1.0  
**Статус:** ✅ Готово к использованию
