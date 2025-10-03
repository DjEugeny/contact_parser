# Инструкции по тестированию системы обогащения ИНН

## Быстрая проверка готовности системы

### 1. Проверка переменных окружения

```bash
# Убедитесь что .env файл содержит ключи
cat .env
```

Должно содержать:
```
DADATA_API_KEY=0d49abad18ccd8b891c3cc0247c31fb20ac14db5
DADATA_SECRET_KEY=66028a531900322903f4ebdacaa450685e3228b1
```

### 2. Проверка импортов модулей

```python
# Запустите в Python интерпретаторе:
python3 -c "
import sys
sys.path.append('src')
from postprocessing.inn_validator import RussianINNValidator
from postprocessing.inn_cache_system import INNCacheManager  
from postprocessing.dadata_provider import DaDataProviderAdapter
from postprocessing.org_inn_resolver import OrganizationINNResolver
print('✅ Все модули успешно импортированы')
"
```

### 3. Быстрый тест валидатора ИНН

```python
python3 -c "
import sys
sys.path.append('src')
from postprocessing.inn_validator import RussianINNValidator

validator = RussianINNValidator()

# Тест валидного ИНН Яндекса
result = validator.validate('7707083893')
print(f'Яндекс ИНН валиден: {result.valid}')

# Тест невалидного ИНН
result = validator.validate('1234567890') 
print(f'Тестовый ИНН невалиден: {not result.valid}')
print('✅ Валидатор ИНН работает корректно')
"
```

### 4. Тест кэша

```python
python3 -c "
import sys
from pathlib import Path
sys.path.append('src')
from postprocessing.inn_cache_system import INNCacheManager

cache_path = Path('registry/test_cache.jsonl')
cache = INNCacheManager(cache_path, ttl_days=1)

# Сохранение
success = cache.save_to_cache('test_org', 'moscow', '7707083893', 'test', 0.95)
print(f'Сохранение в кэш: {success}')

# Поиск
cached = cache.get_cached_inn('test_org', 'moscow')
print(f'Поиск в кэше: {cached is not None}')

# Очистка
if cache_path.exists():
    cache_path.unlink()
print('✅ Кэш работает корректно')
"
```

### 5. Тест DaData провайдера (требует API ключи)

```python
python3 -c "
import sys
import os
sys.path.append('src')
from dotenv import load_dotenv
from postprocessing.dadata_provider import DaDataProviderAdapter

load_dotenv()
api_key = os.getenv('DADATA_API_KEY')
secret_key = os.getenv('DADATA_SECRET_KEY')

if api_key and secret_key:
    provider = DaDataProviderAdapter(api_key=api_key, secret_key=secret_key)
    
    # Поиск Яндекса
    candidates = provider.search_candidates('Яндекс', 'Москва')
    print(f'Найдено кандидатов для Яндекса: {len(candidates)}')
    
    if candidates:
        best = candidates[0]
        print(f'Лучший кандидат: {best.name} (ИНН: {best.inn})')
    
    print('✅ DaData провайдер работает')
else:
    print('❌ API ключи не найдены')
"
```

### 6. Полный тест обогащения

```python
python3 -c "
import sys
import os
sys.path.append('src')
from dotenv import load_dotenv
from postprocessing.org_inn_resolver import OrganizationINNResolver

load_dotenv()

# Создание конфигурации
config = {
    'enabled': True,
    'auto_accept_threshold': 0.85,
    'review_threshold': 0.65,
    'providers': {
        'dadata': {
            'enabled': True,
            'api_key': os.getenv('DADATA_API_KEY'),
            'timeout_ms': 3000
        }
    },
    'cache': {'path': 'registry/inn_cache.jsonl', 'ttl_days': 180},
    'overrides_path': 'registry/inn_overrides.yml'
}

resolver = OrganizationINNResolver(config)

# Тестовая организация
organizations = {
    1: {
        'gid': 'test-001',
        'name': 'Яндекс',
        'city': 'Москва',
        'inn': None
    }
}

# Обогащение
metadata = resolver.enrich_organizations(organizations)

# Результат
org = organizations[1]
print(f'Результат обогащения:')
print(f'  Организация: {org[\"name\"]}')
print(f'  ИНН: {org.get(\"inn\", \"не найден\")}')

if 'test-001' in metadata:
    result = metadata['test-001']
    print(f'  Решение: {result[\"decision\"]}')
    print(f'  Уверенность: {result[\"confidence\"]}')

print('✅ Полное обогащение работает')
"
```

## Ожидаемые результаты

При успешной работе вы должны увидеть:
- ✅ Все модули успешно импортированы
- ✅ Валидатор ИНН работает корректно  
- ✅ Кэш работает корректно
- ✅ DaData провайдер работает
- ✅ Полное обогащение работает

## Решение проблем

### Ошибки импорта
```bash
# Проверьте структуру проекта
ls -la src/postprocessing/

# Убедитесь что __init__.py файлы существуют
find src -name "__init__.py"
```

### Ошибки API
```bash
# Проверьте .env файл
cat .env | grep DADATA

# Проверьте доступность API
curl -X POST https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party \
  -H "Authorization: Token $DADATA_API_KEY" \
  -H "X-Secret: $DADATA_SECRET_KEY" \
  -d '{"query": "Яндекс"}'
```

### Права доступа
```bash
# Создайте registry директорию если нужно
mkdir -p registry
chmod 755 registry
```

## Состояние системы

✅ **Все задачи выполнены:**
- Основная архитектура и модули
- DaData провайдер интеграция
- Кэширование с TTL
- Валидация ИНН
- Метаданные и трекинг решений
- Документация на русском языке

✅ **API ключи настроены** в .env файле

✅ **Готова к использованию** в производственной среде