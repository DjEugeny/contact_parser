# 📚 Утилиты для оптимизации таймаутов и обработки ошибок

Этот документ описывает утилиты, созданные в рамках задач 9-10.1.

---

## 📦 Модули

### 1. `timeout_calculator.py` - Расчёт динамических таймаутов

Модуль для расчёта оптимальных таймаутов LLM запросов на основе характеристик письма.

#### Основные функции:

**`calculate_dynamic_timeout(text_length, attachments_count, has_ocr)`**
```python
from src.utils.timeout_calculator import calculate_dynamic_timeout

# Расчёт таймаута для письма
timeout = calculate_dynamic_timeout(
    text_length=10000,      # Длина текста в символах
    attachments_count=2,    # Количество вложений
    has_ocr=True           # Есть ли OCR текст
)
# Результат: 160 секунд
```

**`calculate_timeout_from_email_data(email_data)`**
```python
# Расчёт из данных письма
email_data = {
    'combined_text_length': 5000,
    'attachments_processed': 2,
    'has_ocr': True
}
timeout = calculate_timeout_from_email_data(email_data)
# Результат: 155 секунд
```

**`get_timeout_breakdown(text_length, attachments_count, has_ocr)`**
```python
# Детальная разбивка расчёта
breakdown = get_timeout_breakdown(5000, 2, True)
print(breakdown['breakdown_str'])
# Вывод: "60 (base) + 5 (text) + 60 (attachments) + 30 (OCR) = 155s"
```

#### Логика расчёта:
- **Базовый таймаут:** 60 секунд
- **Текст:** +1 сек на каждые 1000 символов
- **Вложения:** +30 сек на каждое вложение
- **OCR:** +30 сек если есть OCR текст
- **Максимум:** 300 секунд (5 минут)

---

### 2. `retry_with_backoff.py` - Retry с динамическим таймаутом

Модуль для выполнения запросов с автоматическими повторами и увеличением таймаута.

#### Основные функции:

**`retry_with_backoff_async(func, initial_timeout, config)`**
```python
from src.utils.retry_with_backoff import retry_with_backoff_async, RetryConfig

async def api_call(data, timeout=None):
    # Ваш API вызов
    return response

# Вызов с retry
result = await retry_with_backoff_async(
    api_call,
    data={'text': 'hello'},
    initial_timeout=120,
    config=RetryConfig(
        max_attempts=3,           # Максимум 3 попытки
        base_delay=2.0,           # Базовая задержка 2 сек
        timeout_multiplier=1.5,   # Увеличение таймаута на 50%
        exponential_base=2.0      # Exponential backoff (2, 4, 8 сек)
    )
)
```

**Декоратор `@with_retry_backoff()`**
```python
from src.utils.retry_with_backoff import with_retry_backoff, RetryConfig

@with_retry_backoff(
    initial_timeout=120,
    config=RetryConfig(max_attempts=3)
)
async def api_call(data):
    # Ваш API вызов
    return response

# Автоматический retry
result = await api_call(data={'text': 'hello'})
```

#### Логика работы:
1. Первая попытка с начальным таймаутом
2. При ошибке/таймауте:
   - Увеличение таймаута на 50%
   - Exponential backoff задержка (2, 4, 8 сек)
   - Повтор запроса
3. Максимум 3 попытки
4. Логирование каждой попытки

---

### 3. `error_logger.py` - Улучшенное логирование ошибок

Модуль для детального логирования ошибок обработки с сохранением debug данных.

#### Основные функции:

**`log_processing_error(error, email_file, input_data, llm_request, llm_response, context)`**
```python
from src.utils.error_logger import log_processing_error

try:
    # Обработка письма
    result = process_email(email_data)
except Exception as e:
    # Логирование ошибки с полным контекстом
    error_file = log_processing_error(
        error=e,
        email_file="email_035.json",
        input_data={
            'text_length': 5000,
            'attachments_count': 2,
            'has_ocr': True
        },
        llm_request={
            'provider': 'OpenRouter',
            'model': 'deepseek/deepseek-chat-v3.1:free',
            'timeout': 120
        },
        llm_response={
            'status_code': 200,
            'processing_time': 45.6,
            'response_length': 2345
        },
        context={
            'stage': 'postprocessing',
            'operation': 'location_enrichment'
        }
    )
    print(f"Debug данные сохранены: {error_file}")
```

#### Что сохраняется:
- **Информация об ошибке:** type, message, полный traceback
- **Контекст письма:** email_file, text_length, attachments_count
- **LLM запрос:** provider, model, timeout
- **LLM ответ:** status_code, processing_time, response_length
- **Дополнительный контекст:** любые custom данные

#### Формат сохранения:
```json
{
  "error_type": "ValueError",
  "error_message": "Invalid data format",
  "traceback": "Traceback (most recent call last)...",
  "timestamp": "2025-10-10T12:06:36",
  "email_file": "email_035.json",
  "input_data": {
    "text_length": 5000,
    "attachments_count": 2,
    "has_ocr": true
  },
  "llm_request": {
    "provider": "OpenRouter",
    "model": "deepseek/deepseek-chat-v3.1:free",
    "timeout": 120
  },
  "llm_response": {
    "status_code": 200,
    "processing_time": 45.6
  }
}
```

Файлы сохраняются в `data/errors/error_YYYYMMDD_HHMMSS_email_name.json`

---

## 🔧 Интеграция в существующий код

### Пример интеграции в `config_manager.py`:

```python
from src.utils.timeout_calculator import calculate_timeout_from_email_data
from src.utils.retry_with_backoff import retry_with_backoff_async, RetryConfig
from src.utils.error_logger import log_processing_error

async def make_request_async(self, provider, request_data, request_id=None):
    """Запрос к провайдеру с динамическим таймаутом и retry"""
    
    # Рассчитываем динамический таймаут
    initial_timeout = calculate_timeout_from_email_data(request_data)
    
    try:
        # Выполняем запрос с retry
        response = await retry_with_backoff_async(
            self._execute_provider_request,
            provider=provider,
            request_data=request_data,
            initial_timeout=initial_timeout,
            config=RetryConfig(max_attempts=3)
        )
        return response
        
    except Exception as e:
        # Логируем ошибку с полным контекстом
        log_processing_error(
            error=e,
            email_file=request_data.get('email_file'),
            input_data={
                'text_length': len(request_data.get('text', '')),
                'attachments_count': len(request_data.get('attachments', []))
            },
            llm_request={
                'provider': provider.name,
                'model': provider.model,
                'timeout': initial_timeout
            }
        )
        raise
```

---

## 📊 Преимущества

### Динамические таймауты:
- ✅ Оптимальное время ожидания для каждого письма
- ✅ Снижение количества таймаутов
- ✅ Более быстрая обработка простых писем
- ✅ Достаточное время для сложных писем

### Retry с backoff:
- ✅ Автоматические повторы при временных ошибках
- ✅ Увеличение таймаута при повторах
- ✅ Exponential backoff для снижения нагрузки
- ✅ Детальное логирование попыток

### Улучшенное логирование:
- ✅ Полный контекст ошибки
- ✅ Сохранение debug данных в JSON
- ✅ Легкая отладка проблем
- ✅ Структурированные логи

---

## 🧪 Тестирование

Запустите тесты:
```bash
python test_tasks_9_10_1.py
```

Все тесты должны пройти успешно ✅

---

**Дата создания:** 2025-10-10  
**Версия:** 1.0
