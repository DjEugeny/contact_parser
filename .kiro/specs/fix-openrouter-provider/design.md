# Design Document

## Overview

Проблема с OpenRouter провайдером заключается в несоответствии между прямыми тестами API (которые работают) и интеграцией в пайплайн (где возникают ошибки). Анализ логов показывает, что провайдер генерирует пустые ошибки, что приводит к активации Circuit Breaker после 5 неудачных попыток.

Основные проблемы:
1. Асинхронная реализация провайдера может иметь ошибки
2. Формат запросов может не соответствовать ожидаемому API
3. Circuit Breaker блокирует провайдер без возможности восстановления
4. Отсутствует детальная диагностика ошибок

## Architecture

### Компоненты системы

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Pipeline      │───▶│  LLM Manager     │───▶│  OpenRouter     │
│                 │    │                  │    │  Provider       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Circuit Breaker  │    │ OpenRouter API  │
                       │                  │    │                 │
                       └──────────────────┘    └─────────────────┘
```

### Поток данных

1. **Pipeline** отправляет request_data в LLM Manager
2. **LLM Manager** выбирает доступный провайдер
3. **OpenRouter Provider** формирует запрос к API
4. **Circuit Breaker** отслеживает успешность запросов
5. **OpenRouter API** возвращает ответ

## Components and Interfaces

### OpenRouter Provider

**Интерфейс:**
```python
class OpenRouterProvider(BaseProvider):
    async def make_request(self, request_data: Dict[str, Any], **kwargs) -> Dict[str, Any]
```

**Ключевые изменения:**
- Асинхронная реализация с aiohttp
- Правильное формирование URL (/chat/completions)
- Корректные заголовки (HTTP-Referer, X-Title)
- Детальное логирование ошибок

### Circuit Breaker Integration

**Текущая проблема:** Circuit Breaker в BaseProvider использует простую логику с флагом `in_circuit_break`

**Решение:** Интеграция с полноценным Circuit Breaker из error_handling модуля

### Error Handling

**Текущая проблема:** Пустые ошибки в логах не дают информации для диагностики

**Решение:**
- Детальное логирование всех исключений
- Сохранение контекста запроса при ошибках
- Типизация ошибок для лучшей обработки

## Data Models

### Request Data Format
```python
{
    "messages": [
        {"role": "user", "content": "..."}
    ],
    "temperature": 0.2,
    "max_tokens": 8000,
    "top_p": 0.95,
    "stream": False
}
```

### Response Format
```python
{
    "content": "...",
    "provider": "OpenRouter",
    "model": "deepseek/deepseek-chat-v3.1:free",
    "usage": {
        "prompt_tokens": 16,
        "completion_tokens": 9,
        "total_tokens": 25
    },
    "response_time": 1.23
}
```

### Error Context
```python
{
    "provider": "OpenRouter",
    "request_data": {...},
    "error_type": "http_error|network_error|unknown_error",
    "error_message": "...",
    "timestamp": "...",
    "attempt": 1
}
```

## Error Handling

### Типы ошибок

1. **HTTP Errors (400, 401, 429, 500+)**
   - Логирование статуса и тела ответа
   - Классификация по типу (client_error, server_error)
   - Специальная обработка rate limiting

2. **Network Errors**
   - Таймауты соединения
   - DNS ошибки
   - Проблемы с SSL

3. **Validation Errors**
   - Неправильный формат request_data
   - Отсутствующие обязательные поля
   - Неподдерживаемые параметры

4. **Unknown Errors**
   - Неожиданные исключения
   - Проблемы с парсингом ответа

### Circuit Breaker Strategy

```python
# Параметры Circuit Breaker
failure_threshold = 5      # Количество ошибок для открытия
recovery_timeout = 300     # 5 минут до попытки восстановления
half_open_max_calls = 3    # Количество тестовых вызовов
```

**Состояния:**
- **CLOSED**: Нормальная работа
- **OPEN**: Блокировка после превышения порога ошибок
- **HALF_OPEN**: Тестирование восстановления

## Testing Strategy

### Unit Tests
1. **Provider Creation**: Тест создания провайдера с различными конфигурациями
2. **Request Formatting**: Тест правильного формирования запросов к API
3. **Response Parsing**: Тест парсинга различных форматов ответов
4. **Error Handling**: Тест обработки различных типов ошибок

### Integration Tests
1. **Pipeline Integration**: Тест работы провайдера в реальном пайплайне
2. **Circuit Breaker**: Тест активации и восстановления Circuit Breaker
3. **Fallback Logic**: Тест переключения между провайдерами
4. **Load Balancing**: Тест балансировки нагрузки

### Manual Tests
1. **Direct API Test**: Прямой тест OpenRouter API
2. **Pipeline Test**: Тест обработки одного письма
3. **Stress Test**: Тест обработки множества писем
4. **Recovery Test**: Тест восстановления после сбоев

## Implementation Phases

### Phase 1: Fix Core Provider Issues
- Исправление асинхронной реализации
- Правильное формирование URL и заголовков
- Детальное логирование ошибок

### Phase 2: Circuit Breaker Integration
- Интеграция с полноценным Circuit Breaker
- Реализация принудительного сброса
- Мониторинг состояния провайдеров

### Phase 3: Enhanced Error Handling
- Типизация и классификация ошибок
- Контекстное логирование
- Улучшенная диагностика

### Phase 4: Testing and Validation
- Comprehensive testing suite
- Performance validation
- Production readiness check

## Monitoring and Diagnostics

### Metrics to Track
- Request success rate per provider
- Average response time
- Circuit breaker state changes
- Error distribution by type

### Logging Strategy
- Structured logging with JSON format
- Request/response correlation IDs
- Error context preservation
- Performance metrics

### Alerting
- Circuit breaker state changes
- High error rates
- Performance degradation
- Provider unavailability