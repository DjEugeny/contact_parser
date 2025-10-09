# Circuit Breaker Fix - Quick Reference

## Что было исправлено?

Circuit Breaker теперь **различает ошибки модели и ошибки провайдера**.

## Типы ошибок

### 1. Rate Limit (ошибка модели)
- **Что происходит**: Модель достигла лимита запросов
- **Действие системы**: Переключение на следующую модель
- **Провайдер**: Остается доступным ✅
- **Пример**: `429 Too Many Requests`, `Rate limit exceeded`

### 2. Ошибка модели
- **Что происходит**: Проблема с конкретной моделью
- **Действие системы**: Переключение на следующую модель
- **Провайдер**: Остается доступным ✅
- **Примеры**:
  - `Data policy violation`
  - `Empty response`
  - `Context length exceeded`
  - `Model not found`

### 3. Критическая ошибка провайдера
- **Что происходит**: Провайдер недоступен
- **Действие системы**: После 15 ошибок блокирует провайдер
- **Провайдер**: Блокируется на 60 секунд ❌
- **Примеры**:
  - `Network error`
  - `Connection timeout`
  - `Authentication failed`

## Как это работает?

### Сценарий 1: Rate Limit
```
1. OpenRouter/Model1 → Rate limit (429)
2. Система переключается на OpenRouter/Model2
3. OpenRouter остается доступным
4. Обработка продолжается
```

### Сценарий 2: Все модели провайдера исчерпаны
```
1. OpenRouter/Model1 → Rate limit
2. OpenRouter/Model2 → Rate limit  
3. OpenRouter/Model3 → Rate limit
4. Все модели OpenRouter исчерпаны
5. Fallback на Replicate
```

### Сценарий 3: Критическая ошибка провайдера
```
1. OpenRouter → Network error (15 раз)
2. Circuit Breaker открывается
3. OpenRouter блокируется на 60 секунд
4. Fallback на Replicate
5. Через 60 секунд OpenRouter снова доступен
```

## Конфигурация

### Circuit Breaker параметры
```python
failure_threshold: 15        # Ошибок для блокировки провайдера
recovery_timeout: 60         # Секунд до попытки восстановления
half_open_max_calls: 3       # Вызовов в half-open состоянии
success_threshold: 2         # Успехов для закрытия circuit breaker
```

### ModelsManager параметры
```yaml
fallback:
  enabled: true
  max_retries_per_model: 3   # Попыток на модель перед переключением
  switch_on_errors:          # Ошибки для автопереключения
    - "data policy"
    - "rate limit"
    - "empty response"
```

## Тестирование

Запустите тест для проверки:
```bash
python test_circuit_breaker_fix.py
```

Ожидаемый результат:
```
✅ ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!
   ✓ Rate limit не блокирует провайдер
   ✓ Ошибки модели не блокируют провайдер
   ✓ Критические ошибки провайдера блокируют провайдер
```

## Логирование

### Rate Limit
```json
{
  "event": "⏳ Rate limit для модели в OpenRouter. Переключение на следующую модель. Провайдер остается доступным.",
  "level": "warning"
}
```

### Ошибка модели
```json
{
  "event": "⚠️ Ошибка модели в OpenRouter: Data policy error. Переключение на следующую модель. Провайдер остается доступным.",
  "level": "warning"
}
```

### Критическая ошибка
```json
{
  "event": "🚨 Circuit Breaker для OpenRouter открыт после 15 критических ошибок провайдера",
  "level": "error"
}
```

## Мониторинг

Проверить статус провайдеров:
```python
from src.config.config_manager import UnifiedConfigManager

config_manager = UnifiedConfigManager()
stats = config_manager.get_provider_stats_summary()

for provider, info in stats.items():
    print(f"{provider}:")
    print(f"  Circuit Breaker: {info['circuit_breaker_state']}")
    print(f"  Success Rate: {info['success_rate']}%")
    print(f"  Rate Limit Errors: {info['rate_limit_errors']}")
    print(f"  Available: {info['is_available']}")
```

## Troubleshooting

### Провайдер заблокирован после rate limit
**Проблема**: Старая версия кода  
**Решение**: Обновите код, удалите `__pycache__`

### Все модели быстро исчерпываются
**Проблема**: Слишком низкий `max_retries_per_model`  
**Решение**: Увеличьте в `config/models_config.yaml`

### Circuit Breaker не восстанавливается
**Проблема**: Слишком короткий `recovery_timeout`  
**Решение**: Увеличьте в конфигурации

## Дополнительная информация

См. полную документацию:
- `.kiro/specs/models-manager-regression-fix/TASK_2.5_SUMMARY.md`
- `.kiro/specs/models-manager-regression-fix/requirements.md`
- `.kiro/specs/models-manager-regression-fix/design.md`
