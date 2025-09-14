# Руководство по управлению Groq провайдером

**Дата:** 2025-09-13 21:09 (UTC+07) *(Обновлено: 2025-09-13 21:06)*  
**Статус:** 📋 РУКОВОДСТВО  
**Фаза:** 11.3 - Настройка провайдеров LLM

## 🎯 Цель документа

Данное руководство описывает процедуру временного отключения и последующего включения Groq провайдера в системе Contact Parser.

**⚠️ ВАЖНОЕ ОБНОВЛЕНИЕ:** Руководство исправлено для работы с новой архитектурой `UnifiedConfigManager`

## ⚠️ Причины отключения Groq

1. **Нестабильность API** - периодические сбои соединения
2. **Ограничения rate limiting** - частые превышения лимитов запросов  
3. **Приоритизация DeepSeek V3.1** - фокус на более стабильном провайдере
4. **Оптимизация ресурсов** - снижение количества fallback попыток

## Текущий статус
**Groq провайдер временно отключен** для тестирования DeepSeek V3.1

## 🔧 Процедура отключения

### Шаг 1: Настройка через .env файл

**Файл:** `/Users/evgenyzach/contact_parser/.env`

Для отключения Groq провайдера:
```bash
# Отключение Groq провайдера
# GROQ_API_KEY=your_groq_api_key_here  # Закомментировать или удалить

# Основной провайдер остается активным
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### Шаг 2: Проверка активных провайдеров

```bash
cd /Users/evgenyzach/contact_parser
python -c "from src.config.config_manager import UnifiedConfigManager; ucm = UnifiedConfigManager(); providers = ucm.get_llm_providers(); print('Активные провайдеры:', [p.name for p in providers])"
```

**Ожидаемый результат:** `Активные провайдеры: ['deepseek']`

## Как включить Groq провайдер обратно

### Шаг 1: Восстановление в .env файле

```bash
# Включение Groq провайдера
GROQ_API_KEY=your_groq_api_key_here  # Раскомментировать и указать ключ

# Основной провайдер остается активным
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### Шаг 2: Тестирование восстановленного провайдера

```bash
cd /Users/evgenyzach/contact_parser
python -c "from src.config.config_manager import UnifiedConfigManager; ucm = UnifiedConfigManager(); providers = ucm.get_llm_providers(); print('Активные провайдеры:', [p.name for p in providers])"
```

**Ожидаемый результат:** `Активные провайдеры: ['deepseek', 'groq']`

## Причина отключения
Groq провайдер был временно отключен для:
- Тестирования оптимизированных настроек DeepSeek V3.1
- Избежания конфликтов в fallback цепочке
- Фокусировки на двух основных провайдерах (OpenRouter и Replicate)

## Приоритет провайдеров (когда Groq включен)
1. **OpenRouter** (приоритет 1) - основной провайдер
2. **Replicate** (приоритет 2) - первый fallback
3. **Groq** (приоритет 3) - резервный fallback

## Проверка статуса
Для проверки статуса провайдеров запустите:
```bash
python src/main_new.py --check-providers
```

---
*Отчет создан: 2025-09-13 21:06(UTC+07)*
*Автор: IMPLEMENT агент*