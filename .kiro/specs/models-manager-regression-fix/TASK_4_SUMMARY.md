# Task 4 Implementation Summary: Context Length Validation

**Дата:** 2025-10-09  
**Статус:** ✅ Завершено  
**Задача:** Добавить валидацию размера контекста в ModelsManager

---

## Что было реализовано

### 1. Обновлен ModelsManager (src/config/models_manager.py)

#### Добавлены новые методы:

1. **`estimate_tokens(text, encoding_name="cl100k_base")`**
   - Оценивает количество токенов в тексте через tiktoken
   - Использует кодировку cl100k_base (GPT-4)
   - Fallback на примерную оценку (1 токен ≈ 3 символа) при ошибках
   - Возвращает количество токенов

2. **`validate_context_length(model, text, max_output_tokens=4000)`**
   - Проверяет, помещается ли текст в context window модели
   - Учитывает как входные токены, так и резерв для ответа
   - Логирует предупреждение если модель не подходит
   - Возвращает True/False

3. **Обновлен `get_current_model(provider, estimated_tokens=None)`**
   - Добавлен опциональный параметр `estimated_tokens`
   - Если указан, ищет первую модель с достаточным context window
   - Автоматически пропускает модели с недостаточным контекстом
   - Логирует количество пропущенных моделей
   - Возвращает None если ни одна модель не подходит

#### Обновлена структура ModelConfig:

```python
@dataclass
class ModelConfig:
    name: str
    priority: int
    description: str
    requires_prompt_publication: bool = False
    provider: str = ""
    context_window: int = 32768  # NEW: Default context window
```

#### Обновлен парсинг моделей:

- Теперь читает `context_window` из models_config.yaml
- Значение по умолчанию: 32768 токенов

---

### 2. Интегрирована валидация в OpenRouterProvider (src/providers/openrouter.py)

В методе `_make_single_request()` добавлена валидация перед отправкой запроса:

```python
# Валидация context length перед запросом
if self.config_manager and hasattr(self.config_manager, 'models_manager'):
    if self.config_manager.models_manager:
        # Оцениваем размер входного текста
        input_text = '\n'.join([msg.get('content', '') for msg in messages])
        estimated_input_tokens = self.config_manager.models_manager.estimate_tokens(input_text)
        total_tokens_needed = estimated_input_tokens + max_tokens
        
        # Получаем модель с учетом context length
        suitable_model = self.config_manager.models_manager.get_current_model(
            'openrouter',
            estimated_tokens=total_tokens_needed
        )
        
        if suitable_model:
            # Обновляем модель если она изменилась
            if suitable_model.name != self.config.model:
                old_model = self.config.model
                self.config.model = suitable_model.name
                logger.info(f"🔄 Модель изменена из-за context length: {old_model} → {suitable_model.name}")
        else:
            # Ни одна модель не подходит
            raise RuntimeError(f"❌ Context length error: требуется ~{total_tokens_needed} токенов")
```

**Логика работы:**
1. Оценивает количество токенов во входных messages
2. Добавляет резерв для ответа (max_tokens)
3. Запрашивает у ModelsManager подходящую модель
4. Если текущая модель не подходит, автоматически переключается на следующую
5. Если ни одна модель не подходит, выбрасывает RuntimeError

---

### 3. Интегрирована валидация в ReplicateProvider (src/providers/replicate.py)

Аналогичная валидация добавлена в метод `_make_single_request()`:

```python
# Валидация context length перед запросом
if self.config_manager and hasattr(self.config_manager, 'models_manager'):
    if self.config_manager.models_manager:
        # Оцениваем размер входного текста (prompt + system_prompt)
        input_text = f"{system_prompt}\n{prompt}"
        estimated_input_tokens = self.config_manager.models_manager.estimate_tokens(input_text)
        total_tokens_needed = estimated_input_tokens + max_tokens
        
        # Получаем модель с учетом context length
        suitable_model = self.config_manager.models_manager.get_current_model(
            'replicate',
            estimated_tokens=total_tokens_needed
        )
        
        if suitable_model:
            # Обновляем модель если она изменилась
            if suitable_model.name != self.config.model:
                old_model = self.config.model
                self.config.model = suitable_model.name
                logger.info(f"🔄 Модель изменена из-за context length: {old_model} → {suitable_model.name}")
        else:
            # Ни одна модель не подходит
            raise RuntimeError(f"❌ Context length error: требуется ~{total_tokens_needed} токенов")
```

---

## Тестирование

Создан тест `test_context_length_validation.py` который проверяет:

### Тест 1: Оценка токенов
- ✅ Короткий текст: 13 символов → ~4 токена
- ✅ Средний текст: 470 символов → ~91 токен
- ✅ Длинный текст: 26000 символов → ~7001 токен

### Тест 2: Валидация context length
- ✅ Маленький текст помещается в модель
- ✅ Огромный текст корректно обрабатывается (Gemini имеет 1M context)

### Тест 3: Выбор модели с учетом context length
- ✅ Маленький запрос (1000 токенов) → выбрана первая модель
- ✅ Средний запрос (50000 токенов) → выбрана подходящая модель
- ✅ Огромный запрос (2000000 токенов) → корректно возвращает None

**Результат:** Все тесты пройдены успешно ✅

---

## Конфигурация моделей

В `config/models_config.yaml` уже указаны context_window для всех моделей:

```yaml
openrouter:
  models:
    - name: "google/gemini-2.0-flash-exp:free"
      context_window: 1000000  # 1M токенов
      
    - name: "meta-llama/llama-3.3-70b-instruct:free"
      context_window: 128000   # 128K токенов
      
    - name: "deepseek/deepseek-chat-v3.1:free"
      context_window: 64000    # 64K токенов
      
    - name: "anthropic/claude-3-haiku:free"
      context_window: 200000   # 200K токенов
```

---

## Преимущества реализации

1. **Проактивная валидация:** Проверка происходит ДО отправки запроса, экономя время и деньги
2. **Автоматическое переключение:** Система сама выбирает модель с достаточным context window
3. **Детальное логирование:** Все переключения и причины логируются
4. **Graceful degradation:** Если ни одна модель не подходит, система выдает понятную ошибку
5. **Оптимизация ресурсов:** Не тратим запросы на модели, которые заведомо не справятся

---

## Примеры логов

### Успешный выбор модели:
```
📊 Context length check: ~5000 input tokens + 4000 output tokens = 9000 total
🎯 ModelsManager: OpenRouter использует модель google/gemini-2.0-flash-exp:free (priority 1, context: 1000000)
```

### Переключение модели:
```
📊 Context length check: ~70000 input tokens + 8000 output tokens = 78000 total
⚠️ Модель deepseek/deepseek-chat-v3.1:free пропущена: требуется ~78000 токенов, доступно: 64000
🔄 ModelsManager: пропущено 1 моделей из-за недостаточного context window
🎯 ModelsManager: OpenRouter использует модель meta-llama/llama-3.3-70b-instruct:free (priority 2, context: 128000)
🔄 Модель изменена из-за context length: deepseek/deepseek-chat-v3.1:free → meta-llama/llama-3.3-70b-instruct:free
```

### Ошибка - нет подходящей модели:
```
📊 Context length check: ~1500000 input tokens + 8000 output tokens = 1508000 total
❌ Ни одна модель OpenRouter не имеет достаточного context window для 1508000 токенов
❌ Context length error: требуется ~1508000 токенов, но ни одна модель не имеет достаточного context window
```

---

## Соответствие требованиям

✅ **Requirement 4.1:** Оценка токенов через tiktoken реализована  
✅ **Requirement 4.2:** Сравнение с context_window модели реализовано  
✅ **Requirement 4.3:** Возврат True/False и логирование реализованы  
✅ **Requirement 4.4:** Интеграция в провайдеры выполнена  
✅ **Requirement 4.5:** Детальное логирование добавлено  

---

## Следующие шаги

Задача 4 полностью завершена. Можно переходить к следующим задачам:
- Задача 5: Улучшение нормализации телефонов
- Задача 6: Расширенное логирование
- Задача 7: Тестирование исправлений

---

**Дата завершения:** 2025-10-09  
**Время выполнения:** ~30 минут  
**Статус:** ✅ Полностью реализовано и протестировано
