# Анализ кэширования в LLM-процессоре

## Обзор

Данный документ содержит анализ реализации кэширования LLM-ответов в системе обработки писем.

## 1. AsyncProviderWrapper - кэш ответов LLM

### Расположение
`src/providers/async_provider_wrapper.py`

### Наличие кэша
✅ **Да, кэш реализован**

### Инициализация кэша
```python
def __init__(self, provider: BaseProvider, max_concurrent: int = 5, enable_cache: bool = True):
    self.enable_cache = enable_cache
    self.cache = MultiLevelCache() if enable_cache else None
```

**Параметры:**
- `enable_cache` - флаг включения/выключения кэширования (по умолчанию `True`)
- Если кэш включен, создается экземпляр `MultiLevelCache`
- Если кэш выключен, `self.cache = None`

### Статистика кэширования
```python
@dataclass
class AsyncProviderStats(ProviderStats):
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
```

## 2. Использование флага enable_cache

### Места использования

**1. В AsyncProviderWrapper.__init__:**
```python
self.enable_cache = enable_cache
self.cache = MultiLevelCache() if enable_cache else None
```

**2. В make_request_async (проверка кэша):**
```python
if self.enable_cache and self.cache:
    cache_key = self._generate_cache_key(prompt, **kwargs)
    cached_response = self.cache.get_llm_response(
        cache_key, 
        self.provider.config.name
    )
```

**3. В make_request_async (сохранение в кэш):**
```python
if self.enable_cache and self.cache and cache_key:
    self.cache.set_llm_response(cache_key, self.provider.config.name, result)
```

### Значение по умолчанию
- **По умолчанию: `True`** - кэш включен
- Можно отключить при создании wrapper: `AsyncProviderWrapper(provider, enable_cache=False)`

## 3. Метод генерации ключа кэша

### Метод _generate_cache_key
```python
def _generate_cache_key(self, prompt: str, **kwargs) -> str:
    """Генерация ключа кеша для запроса"""
    import hashlib
    import json
    
    cache_data = {
        'prompt': prompt,
        'kwargs': {k: v for k, v in kwargs.items() if k not in ['stream', 'callback']}
    }
    
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_str.encode()).hexdigest()
```

### Логика генерации ключа
1. **Входные данные:**
   - Текст промпта (`prompt`)
   - Дополнительные параметры (`kwargs`), исключая `stream` и `callback`

2. **Процесс:**
   - Создается словарь с промптом и параметрами
   - Словарь сериализуется в JSON с сортировкой ключей
   - Вычисляется MD5 хэш от JSON-строки

3. **Результат:**
   - 32-символьный MD5 хэш (например: `a1b2c3d4e5f6...`)

### Особенности
- Исключаются параметры `stream` и `callback` (не влияют на результат)
- `sort_keys=True` обеспечивает одинаковый хэш для одинаковых данных
- MD5 используется для скорости (не для безопасности)

## 4. Хранилище кэша

### Тип хранилища
**Двухуровневое (гибридное):**
1. **In-memory кэш** (быстрый доступ)
2. **Файловый кэш** (персистентное хранение)

### Реализация: MultiLevelCache

**Расположение:** `src/core/cache_manager.py`

### Уровень 1: Memory Cache (LRU)

```python
def __init__(self, cache_dir: Optional[Path] = None, max_memory_items: int = 100):
    self.memory_cache: Dict[str, Dict[str, Any]] = {}
    self.max_memory_items = max_memory_items
```

**Характеристики:**
- Хранится в словаре Python (`Dict`)
- Максимум 100 элементов по умолчанию
- Используется декоратор `@lru_cache(maxsize=50)` для промптов
- Быстрый доступ (O(1))
- Данные теряются при перезапуске

### Уровень 2: File Cache (Persistent)

```python
def __init__(self, cache_dir: Optional[Path] = None, max_memory_items: int = 100):
    self.cache_dir = cache_dir or Path("cache")
    self.cache_dir.mkdir(exist_ok=True)
```

**Характеристики:**
- Директория: `cache/` (по умолчанию)
- Формат файлов: JSON
- Структура: `cache/{первые_2_символа_хэша}/{полный_хэш}.json`
- Пример: `cache/a1/a1b2c3d4e5f6...json`
- Персистентное хранение (сохраняется между запусками)

### Алгоритм работы кэша

**При запросе (get_llm_response):**
1. Проверка в memory cache
   - Если найдено и не устарело → возврат
   - Если устарело → удаление из памяти
2. Проверка в file cache
   - Если найдено и не устарело → загрузка в память + возврат
   - Если не найдено → cache miss
3. Обновление статистики (hits/misses)

**При сохранении (set_llm_response):**
1. Сохранение в файл (JSON)
2. Добавление в memory cache
3. Обновление статистики размера

### Время жизни кэша

```python
def get_llm_response(self, prompt_hash: str, provider: str,
                    max_age_seconds: int = 3600) -> Optional[Dict[str, Any]]:
```

**Параметры TTL:**
- **По умолчанию: 3600 секунд (1 час)** для LLM ответов
- **24 часа (86400 секунд)** для общих данных
- Автоматическая очистка устаревших файлов при инициализации

### Сжатие больших ответов

```python
def set_llm_response(self, prompt_hash: str, provider: str,
                    response: Dict[str, Any], compress_large: bool = True):
    response_size = len(json.dumps(response, ensure_ascii=False))
    
    if compress_large and response_size > 100000:
        import gzip
        compressed_data = gzip.compress(...)
```

**Логика сжатия:**
- Ответы > 100 KB сжимаются с помощью gzip
- Добавляются метаданные: `_compressed=True`, `_original_size`

## 5. Текущая реализация кэширования

### Архитектура

```
IntegratedLLMProcessor
    └── ContactExtractor (через ExtractorFactory)
        └── UnifiedConfigManager
            └── Providers (OpenRouter, Replicate, Groq)
                └── AsyncProviderWrapper (с кэшем)
                    └── MultiLevelCache
                        ├── Memory Cache (Dict)
                        └── File Cache (JSON files)
```

### Инициализация в системе

**1. UnifiedConfigManager._initialize_providers():**
```python
def _initialize_providers(self):
    provider_classes = {
        'Replicate': ReplicateProvider,
        'Groq': GroqProvider,
        'OpenRouter': OpenRouterProvider
    }
    
    for provider_config in providers_config:
        provider_class = provider_classes[provider_config.name]
        self.providers[provider_config.name] = provider_class(base_config)
```

**2. AsyncProviderManager.add_provider():**
```python
def add_provider(self, name: str, provider: BaseProvider):
    wrapper = AsyncProviderWrapper(provider, self.max_concurrent_per_provider)
    # enable_cache=True по умолчанию
    self.async_providers.append(wrapper)
```

### Статистика кэширования

**Доступна через get_stats():**
```python
async_stats = {
    'cache_hits': self.async_stats.cache_hits,
    'cache_misses': self.async_stats.cache_misses,
    'cache_hit_rate': round(self.async_stats.cache_hit_rate * 100, 2)
}
```

**Агрегированная статистика (AsyncProviderManager):**
```python
return {
    'cache_hits': cache_hits,
    'cache_misses': cache_misses,
    'cache_hit_rate': round(cache_hit_rate, 2),
    ...
}
```

## 6. Ключевые выводы

### ✅ Что реализовано

1. **Двухуровневое кэширование:**
   - In-memory для быстрого доступа
   - Файловое для персистентности

2. **Умная генерация ключей:**
   - MD5 хэш от промпта + параметров
   - Исключение нерелевантных параметров

3. **Управление временем жизни:**
   - TTL по умолчанию 1 час
   - Автоматическая очистка устаревших данных

4. **Статистика:**
   - Отслеживание hits/misses
   - Расчет cache hit rate
   - Мониторинг размера кэша

5. **Оптимизации:**
   - Сжатие больших ответов (>100KB)
   - LRU для промптов
   - Структурированное хранение файлов

### 🎯 Конфигурация

**Включение/выключение кэша:**
```python
# Включить кэш (по умолчанию)
AsyncProviderWrapper(provider, enable_cache=True)

# Выключить кэш
AsyncProviderWrapper(provider, enable_cache=False)
```

**Настройка TTL:**
```python
# При получении из кэша
cache.get_llm_response(key, provider, max_age_seconds=7200)  # 2 часа
```

### 📊 Производительность

**Преимущества кэширования:**
- Снижение количества API запросов
- Экономия токенов и денег
- Ускорение повторных запросов
- Работа при недоступности API

**Метрики:**
- Memory hit rate: % попаданий в память
- File hit rate: % попаданий в файлы
- Overall hit rate: общий % попаданий

## 7. Рекомендации

### Текущее состояние
✅ Кэширование **включено по умолчанию** во всех провайдерах

### Когда отключать кэш
- Тестирование с чистыми данными
- Динамические запросы (время, случайность)
- Отладка LLM ответов

### Когда использовать кэш
- Повторная обработка одних и тех же писем
- Статические промпты
- Продакшн среда для экономии

### Мониторинг
Регулярно проверять:
```python
stats = provider.get_stats()
print(f"Cache hit rate: {stats['async_stats']['cache_hit_rate']}%")
```

## Соответствие требованиям

**Requirements 2.1:** ✅ Проанализирована архитектура кэширования  
**Requirements 2.4:** ✅ Задокументирована текущая реализация

---

**Дата анализа:** 2025-01-07  
**Статус:** Завершено
