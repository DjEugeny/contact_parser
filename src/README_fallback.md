# 🔄 Fallback система для LLM экстрактора

## Обзор

Система автоматического переключения между LLM провайдерами для обеспечения надежности и непрерывности работы.

## Провайдеры

### 1. OpenRouter (Приоритет 1)
- **Модель**: qwen/qwen3-235b-a22b:free
- **Лимиты**: 50 запросов/день, 1 запрос/мин
- **Fallback**: При достижении лимитов

### 2. Groq (Приоритет 2 - Fallback)
- **Модель**: llama3-8b-8192
- **Лимиты**: Зависит от плана
- **Fallback**: При ошибках OpenRouter

## Конфигурация

Добавьте в `.env` файл:

```bash
# OpenRouter (основной)
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=qwen/qwen3-235b-a22b:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Groq (fallback)
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama3-8b-8192
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

## Логика Fallback

### Автоматическое переключение при:
- Rate limit exceeded (429)
- Quota exceeded
- Service unavailable
- Timeout errors
- Connection errors

### Максимум попыток: 2

## Тестирование

```python
from llm_extractor import ContactExtractor

# Создание в тестовом режиме
extractor = ContactExtractor(test_mode=True)

# Проверка здоровья системы
health = extractor.get_provider_health()

# Симуляция отказа провайдера
extractor.simulate_provider_failure('openrouter')

# Сброс состояния
extractor.reset_system_state()
```

## Мониторинг

- Статус каждого провайдера
- Количество попыток fallback
- Общее здоровье системы
- Рекомендации по улучшению

## Преимущества

✅ **Надежность**: Автоматическое переключение при ошибках
✅ **Эффективность**: Приоритетная система провайдеров  
✅ **Мониторинг**: Детальная диагностика состояния
✅ **Тестирование**: Симуляция отказов для проверки логики
✅ **Гибкость**: Легко добавлять новых провайдеров