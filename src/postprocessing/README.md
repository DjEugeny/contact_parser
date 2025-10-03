# Модуль постобработки данных LLM

**Версия:** 1.0.0  
**Дата создания:** 2025-09-13  
**Автор:** Contact Parser Team  

## Описание

Модуль постобработки реализует полный алгоритм обработки ответов LLM согласно мини-ТЗ. Обеспечивает дедупликацию организаций, фильтрацию ценных контактов, обогащение данных и нормализацию в соответствии с новой структурой `organizations`/`contacts`.

## Архитектура

```
src/postprocessing/
├── __init__.py                      # Экспорт модулей
├── postprocessor.py                 # Главный координатор
├── organization_deduplicator.py     # Дедупликация организаций
├── contact_filter.py                # Фильтрация ценных контактов
├── data_enricher.py                 # Обогащение данных
├── data_normalizer.py               # Нормализация данных
├── advanced_contact_deduplicator.py # Продвинутая дедупликация контактов
├── org_inn_resolver.py              # Система обогащения ИНН
├── inn_validator.py                 # Валидатор ИНН
├── inn_search_normalizer.py         # Нормализатор для поиска ИНН
├── inn_cache_system.py              # Кэш и переопределения ИНН
├── dadata_provider.py               # Провайдер DaData API
├── inn_data_types.py                # Структуры данных ИНН
└── README.md                        # Документация
```

## Компоненты

### 1. PostProcessor

**Файл:** `postprocessor.py`  
**Назначение:** Главный координатор всех этапов постобработки

**Этапы обработки:**
1. Дедупликация и объединение организаций (п.3.a мини-ТЗ)
2. Обновление organization_id в контактах (п.3.b)
3. Фильтрация ценных контактов (п.3.c)
4. Обогащение полей city/address (п.3.e)
5. Нормализация данных (п.3.f)

**Использование:**
```python
from postprocessing import PostProcessor

postprocessor = PostProcessor()
processed_result = postprocessor.process_llm_response(llm_result, email_data)
```

### 2. OrganizationDeduplicator

**Файл:** `organization_deduplicator.py`  
**Назначение:** Дедупликация организаций с глобальными ID

**Алгоритм:**
- Поиск дубликатов по названию (fuzzy matching), ИНН, сайту
- Объединение данных (emails, phones, address)
- Создание маппинга локальных → глобальных ID
- Система автоинкремента для новых организаций

**Использование:**
```python
from postprocessing import OrganizationDeduplicator

deduplicator = OrganizationDeduplicator()
mapping = deduplicator.process_organizations(llm_organizations)
all_orgs = deduplicator.get_all_organizations()
```

### 3. ContactFilter

**Файл:** `contact_filter.py`  
**Назначение:** Фильтрация ценных контактов по функции `evaluate_contact_value`

**Система баллов (согласно мини-ТЗ):**
- `name`: +3 балла
- `organization_id`: +2 балла
- `position`: +2 балла
- `email`: +2 балла
- `phones` (непустой массив): +2 балла
- `city`: +1 балл
- `inn`: +1 балл

**Порог:** score ≥ 4

**Использование:**
```python
from postprocessing import ContactFilter

contact_filter = ContactFilter(min_score=4)
valuable, updated_orgs = contact_filter.filter_valuable_contacts(contacts, organizations)
```

### 4. DataEnricher

**Файл:** `data_enricher.py`  
**Назначение:** Обогащение контактов дополнительными данными

**Функции:**
- Валидация ИНН организаций и контактов
- Извлечение сайтов компаний
- Обогащение полей `city`/`address` из организаций
- Корпоративная разведка по email доменам

**Использование:**
```python
from postprocessing import DataEnricher

enricher = DataEnricher()
enriched_contacts = enricher.enrich_contacts(contacts, organizations, email_data)
```

### 5. DataNormalizer

**Файл:** `data_normalizer.py`  
**Назначение:** Нормализация телефонов, email и других данных

**Функции:**
- Нормализация телефонов в новом формате `phones[]`
- Интеграция с `phone_normalizer.py`
- Валидация и нормализация email адресов
- Очистка и стандартизация имен, должностей
- Определение типов телефонов (mobile, office, fax)

**Использование:**
```python
from postprocessing import DataNormalizer

normalizer = DataNormalizer()
normalized_contacts = normalizer.normalize_contacts(contacts)
normalized_orgs = normalizer.normalize_organizations(organizations)
```

### 6. AdvancedContactDeduplicator

**Файл:** `advanced_contact_deduplicator.py`  
**Назначение:** Продвинутая дедупликация контактов с семантическим анализом

**Особенности:**
- Адаптирован для новой структуры `phones[]`
- Семантическое сравнение имен и организаций
- Обработка цепочек пересылок
- Fuzzy matching для сложных случаев

**Использование:**
```python
from postprocessing import AdvancedContactDeduplicator

deduplicator = AdvancedContactDeduplicator()
unique_contacts = deduplicator.deduplicate_contacts(contacts)
```

### 7. Phone Disambiguation (PLAN-004)
**Файл:** `postprocessor.py` (метод `_resolve_phone_conflicts`)
**Назначение:** Разделение телефонов между организациями, защита от HQ-утечек (LLM дублирует номера, напр. +7(383) МЕД КОНГРЕСС в ДНК-Технология).

**Эвристики (приоритет: city > domain > contact):**
- `area_match` (city_weight=100): код города номера (+7(383) → Новосибирск) совпадает с org.city
- `domain_match` (domain_weight=50): домен email/website org содержит поддомен/сопадает с источником (извлекается из emails/website)
- `contact_match` (contact_weight=20): номер привязан к контактам этой org

**Логика разрешения:**
- Группировка телефонов по нормализованному ключу (E.164)
- Scoring владельцев, winner если max_score > sum(others) + 0.1
- Unresolved при равенстве/низкой уверенности
- Overrides из `registry/phone_overrides.yml` имеют приоритет (reason="override")

**Метаданные:** `postprocessing_metadata.phone_conflicts = {'resolved': [...], 'unresolved': [...]}`
- Каждый: `{'phone': '+7...', 'status': 'resolved', 'kept_gid': '...', 'removed_gids': [...], 'reason': 'area_match'}`

**DevOps инструкции:**
- **Просмотр конфликтов:** В логах/метаданных: `processed['postprocessing_metadata']['phone_conflicts']`. Unresolved — для ручного вмешательства.
- **Добавление overrides:** Редактируйте `registry/phone_overrides.yml` (E.164 номер → owner_gid). Запустите `python scripts/check_registry_health.py` для валидации (дубли, GID existence).
- **Мониторинг:** В health-check отчёт по overrides count/duplicates. После прогона проверяйте DoD: в email_018/019 телефоны разделены правильно.

## 8. Система обогащения ИНН (PLAN-006)

**Файлы:** `org_inn_resolver.py`, `inn_validator.py`, `inn_search_normalizer.py`, `inn_cache_system.py`, `dadata_provider.py`  
**Назначение:** Автоматическое обогащение организаций ИНН с приоритетом официального источника ФНС

### Архитектура системы ИНН

```
🏛️ INN Enrichment System
├── 📊 Структуры данных (inn_data_types.py)
├── 🔍 Валидатор ИНН (inn_validator.py) 
├── 🔧 Нормализатор (inn_search_normalizer.py)
├── 🌐 DaData провайдер (dadata_provider.py)
├── 💾 Кэш и переопределения (inn_cache_system.py)
└── 🎯 Основной резолвер (org_inn_resolver.py)
```

### Основные принципы

- **Источник истины — ФНС (ЕГРЮЛ/ЕГРИП):** Приоритет официального источника
- **Агрегатор (DaData):** Используется как ускоритель кандидатов
- **Двухпороговая логика принятия решений:**
  - `score ≥ 0.85` и единственный кандидат → auto-accept
  - `0.65–0.85` или несколько кандидатов → needs-review
  - `< 0.65` → reject
- **Один ИНН на GID:** ИНН хранится в карточке организации и переиспользуется
- **Прозрачность:** Полное отслеживание решений в метаданных

### Алгоритм обогащения

1. **Skip-rule:** Пропуск организаций с валидным ИНН
2. **Overrides:** Проверка ручных переопределений
3. **Cache:** Поиск в кэше с TTL
4. **Providers:** Параллельный запрос к провайдерам (DaData)
5. **Scoring:** Оценка кандидатов по множественным критериям
6. **Decision:** Принятие решения по двухпороговой логике
7. **Provenance:** Сохранение метаданных решения

### Конфигурация

```python
# config/settings.py
INN_ENRICHMENT_CONFIG = {
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
    'cache': {
        'path': 'registry/inn_cache.jsonl',
        'ttl_days': 180
    },
    'overrides_path': 'registry/inn_overrides.yml'
}
```

### Использование

```python
from postprocessing import OrganizationINNResolver

resolver = OrganizationINNResolver()
metadata = resolver.enrich_organizations(organizations)
```

### Структура метаданных

```json
"postprocessing_metadata": {
  "enrichment": {
    "org_inn": {
      "<org_gid>": {
        "decision": "auto_accept",
        "inn": "7701234567",
        "confidence": 0.91,
        "source": "dadata",
        "method": "name_city_search",
        "score": 0.91,
        "candidates": [{...}],
        "checked_at": "2025-10-03T10:10:00Z"
      }
    }
  }
}
```

### Система кэширования

- **Файл:** `registry/inn_cache.jsonl` (append-only)
- **TTL:** 180 дней (настраиваемо)
- **Ключ:** `md5(name_norm|city_norm|domain)`
- **Атомарные операции:** Блокировка файлов, fsync

### Ручные переопределения

```yaml
# registry/inn_overrides.yml
org_overrides:
  - org_gid: "58a49494-b44e-5b2f-9263-0ce9005f10e3"
    inn: "7723537840"
    reason: "ручное подтверждение через ЕГРЮЛ"
    confirmed_by: "user@example.com"
    confirmed_at: "2025-10-03T10:30:00Z"
```

### Провайдеры

#### DaData API
- **Поиск компаний:** По названию, городу, адресу
- **Лукап по ИНН:** Валидация существующих ИНН
- **Лимиты:** 10,000 запросов/день (бесплатный тариф)
- **Таймауты:** 3 секунды (настраиваемо)

#### ФНС (будущее)
- **Официальный источник:** ЕГРЮЛ/ЕГРИП
- **Системная интеграция:** API доступ
- **Публичный поиск:** egrul.nalog.ru (резерв)

### Нормализация данных

- **Названия:** Удаление юр. форм, кавычек, спецсимволов
- **Города:** Синонимы (СПб→санкт-петербург), префиксы
- **Адреса:** Извлечение улицы+дома без корпусов/офисов
- **Домены:** e2LD извлечение, punycode

### Валидация ИНН

- **10 цифр:** ИНН юридического лица (контрольная сумма)
- **12 цифр:** ИНН физического лица/ИП (две контрольные суммы)
- **Алгоритм:** Проверка по стандартным коэффициентам

### Мониторинг и отладка

```python
# Получение статистики
stats = cache_manager.get_cache_stats()
validation = override_manager.validate_overrides()

# Логи
self.logger.info(f"INN enriched: {count} organizations")
self.logger.debug(f"DaData candidates: {len(candidates)}")
```

### Настройка провайдеров

#### Конфигурация DaData API

Для работы с DaData API необходимо добавить ключи в файл `.env`:

```bash
# DaData API ключи для обогащения ИНН
DADATA_API_KEY=0d49abad18ccd8b891c3cc0247c31fb20ac14db5
DADATA_SECRET_KEY=66028a531900322903f4ebdacaa450685e3228b1
```

**Формат ключей:**
- `DADATA_API_KEY` — основной API ключ DaData
- `DADATA_SECRET_KEY` — секретный ключ для подписи запросов

**Получение ключей:**
1. Зарегистрируйтесь на [dadata.ru](https://dadata.ru)
2. Перейдите в личный кабинет → API → Ключи
3. Скопируйте API ключ и секретный ключ
4. Добавьте их в `.env` файл проекта

### Тестирование системы ИНН

#### Подготовка к тестированию

1. **Убедитесь, что DaData ключи настроены:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env с вашими ключами
   ```

2. **Установите зависимости:**
   ```bash
   pip install requests
   ```

#### Тестирование с реальными данными

Используйте специальный скрипт для тестирования:

```bash
python test_inn_enrichment_real.py
```

**Что тестирует скрипт:**
- ✅ Валидация ИНН (корректные и некорректные)
- ✅ Работа кэша (создание, поиск, TTL)
- ✅ DaData API (поиск организаций)
- ✅ Полный цикл обогащения для тестовых организаций

**Тестовые организации:**
- **Яндекс** (Москва) — ожидается автоматическое принятие
- **Сбербанк** (Москва) — ожидается автоматическое принятие  
- **Газпром** (Санкт-Петербург) — ожидается автоматическое принятие
- **Неизвестная компания** — ожидается отклонение

#### Интерпретация результатов

**Успешное тестирование должно показать:**
```
🔍 Тестирование валидатора ИНН...
✅ Валидный ИНН 7707083893 прошёл проверку
❌ Невалидный ИНН 1234567890 не прошёл проверку

💾 Тестирование кэша...
✅ Кэш работает корректно

🌐 Тестирование DaData провайдера...
✅ Найдено 3 кандидатов для 'Яндекс' в 'Москва'

🎯 Тестирование полного обогащения...
🏢 Тестирование: Яндекс (Москва)
  └─ Результат: auto_accept, ИНН: 7707083893, Уверенность: 0.95

🏢 Тестирование: Сбербанк (Москва)  
  └─ Результат: auto_accept, ИНН: 7707083893, Уверенность: 0.91

✅ Все тесты прошли успешно!
```

**Возможные проблемы:**
- `HTTP 403`: Неверные API ключи DaData
- `HTTP 429`: Превышен лимит запросов (подождите или используйте платный тариф)
- `ConnectionError`: Проблемы с сетью
- `Timeout`: Медленное соединение с API

#### Ручное тестирование

```python
from src.postprocessing.org_inn_resolver import OrganizationINNResolver

# Создание резолвера
resolver = OrganizationINNResolver()

# Тестовые данные
organizations = [
    {
        "organization_id": "test_001",
        "name": "Яндекс",
        "city": "Москва",
        "inn": None
    }
]

# Обогащение
metadata = resolver.enrich_organizations(organizations)

# Проверка результата
print(f"ИНН: {organizations[0].get('inn')}")
print(f"Метаданные: {metadata}")
```

#### Мониторинг производительности

**Проверка кэша:**
```python
from src.postprocessing.inn_cache_system import INNCacheManager

cache = INNCacheManager()
stats = cache.get_cache_stats()
print(f"Записей в кэше: {stats['total_entries']}")
print(f"Просроченных: {stats['expired_entries']}")
```

**Логирование запросов:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Включит детальные логи всех запросов к DaData
```

### Решение проблем

#### Частые ошибки

1. **"Invalid API key"**
   - Проверьте корректность ключей в `.env`
   - Убедитесь, что файл `.env` находится в корне проекта

2. **"Rate limit exceeded"**
   - Подождите несколько минут
   - Рассмотрите переход на платный тариф DaData

3. **"No candidates found"**
   - Проверьте корректность названия организации
   - Убедитесь, что город указан правильно
   - Организация может отсутствовать в базе DaData

4. **Медленная работа**
   - Проверьте настройки таймаутов в конфигурации
   - Убедитесь, что кэш работает корректно

#### Отладочные команды

```bash
# Проверка конфигурации
python -c "from src.postprocessing.org_inn_resolver import OrganizationINNResolver; print(OrganizationINNResolver().config)"

# Очистка кэша
rm registry/inn_cache.jsonl

# Проверка ключей API
curl -X POST \
  https://dadata.ru/api/v2/suggest/party \
  -H "Authorization: Token YOUR_API_KEY" \
  -H "X-Secret: YOUR_SECRET_KEY" \
  -d '{"query": "Яндекс"}'
```

## Новая структура данных

### Входной формат (от LLM)

```json
{
  "organizations": [
    {
      "organization_id": 1,
      "name": "ДНК-Технология",
      "inn": "1901066506",
      "website": "dna-technology.ru",
      "city": "Москва",
      "address": "ул. Академика Королёва, д. 12",
      "emails": ["info@dna-technology.ru"],
      "phones": ["8 800 200-75-15"]
    }
  ],
  "contacts": [
    {
      "contact_id": 101,
      "name": "Гоголева Мария",
      "organization_id": 1,
      "position": "Менеджер по продажам",
      "email": "m.gogoleva@dna-technology.ru",
      "phones": [
        {
          "type": "main",
          "number": "+7(495) 640-17-71"
        }
      ],
      "city": "Москва",
      "address": null,
      "confidence": 0.95
    }
  ],
  "business_context": "Запрос коммерческого предложения",
  "summary": {...},
  "key_points": [...],
  "commercial_offers": [...]
}
```

### Выходной формат (после постобработки)

```json
{
  "organizations": [
    {
      "organization_id": 1001,  // Глобальный ID
      "name": "ДНК-Технология",
      "inn": "1901066506",
      "inn_validated": true,
      "website": "dna-technology.ru",
      "website_confidence": 0.95,
      "city": "Москва",
      "address": "ул. Академика Королёва, д. 12",
      "emails": ["info@dna-technology.ru", "sales@dna-technology.ru"],
      "phones": ["+7800200751", "+74956401771"]
    }
  ],
  "contacts": [
    {
      "contact_id": 101,
      "name": "Гоголева Мария",
      "organization_id": 1001,  // Обновленный глобальный ID
      "position": "Менеджер по продажам",
      "email": "m.gogoleva@dna-technology.ru",
      "email_valid": true,
      "phones": [
        {
          "type": "main",
          "number": "+7(495) 640-17-71",
          "normalized": "+74956401771",
          "original": "+7(495) 640-17-71"
        }
      ],
      "city": "Москва",  // Обогащено из организации
      "address": "ул. Академика Королёва, д. 12",  // Обогащено
      "confidence": 0.95,
      "value_score": 12  // Оценка ценности
    }
  ],
  "postprocessing_metadata": {
    "processed_at": "2025-01-27T18:30:00",
    "stats": {...},
    "version": "1.0.0"
  }
}
```

## Интеграция с существующими модулями

### phone_normalizer.py

```python
# Автоматический импорт в DataNormalizer
from phone_normalizer import normalize_phone

# Fallback при отсутствии модуля
if not phone_normalizer_available:
    self.normalize_phone = self._fallback_normalize_phone
```

### core/inn_validator.py и core/website_extractor.py

```python
# Интеграция в DataEnricher
from ..core.inn_validator import RussianINNValidator
from ..core.website_extractor import WebsiteExtractor

# Dependency injection
self.inn_validator = inn_validator or RussianINNValidator()
self.website_extractor = website_extractor or WebsiteExtractor()
```

## Тестирование

**Файл тестов:** `tests/test_postprocessing.py`

**Запуск тестов:**
```bash
cd /Users/evgenyzach/contact_parser
python -m pytest tests/test_postprocessing.py -v
```

**Покрытие тестами:**
- ✅ OrganizationDeduplicator: дедупликация по ИНН, сайту, названию
- ✅ ContactFilter: функция evaluate_contact_value, фильтрация
- ✅ DataNormalizer: нормализация телефонов, email, организаций
- ✅ PostProcessor: полный пайплайн постобработки
- ✅ AdvancedContactDeduplicator: семантическая дедупликация

## Статистика и мониторинг

```python
# Получение статистики
stats = postprocessor.get_processing_stats()

# Пример статистики
{
  'processed_emails': 15,
  'total_organizations_processed': 25,
  'total_contacts_processed': 45,
  'organizations_deduplicated': 8,
  'contacts_filtered': 12,
  'contacts_enriched': 33,
  'data_normalized': 78,
  'organization_deduplicator': {...},
  'contact_filter': {...},
  'data_enricher': {...},
  'data_normalizer': {...}
}
```

## Производительность

**Ожидаемые показатели:**
- Обработка одного письма: < 2 секунды
- Дедупликация 100 организаций: < 1 секунды
- Фильтрация 200 контактов: < 0.5 секунды
- Нормализация данных: < 0.3 секунды

**Оптимизации:**
- Кэширование нормализованных значений
- Индексирование по ИНН и сайтам
- Batch обработка для больших объемов
- Lazy loading компонентов

## Обработка ошибок

**Принципы:**
- Graceful degradation: при ошибке возвращается оригинальный результат
- Детальное логирование всех этапов
- Валидация входных данных
- Изоляция ошибок между компонентами

**Логирование:**
```python
import logging
logging.basicConfig(level=logging.INFO)

# Логи постобработки
# 🔄 Начало постобработки ответа LLM
# 🏢 Этап 1: Обработка 2 организаций
# 👤 Этап 2: Обновление organization_id в 3 контактах
# 🔍 Этап 3: Фильтрация 3 контактов
# 💎 Этап 4: Обогащение 2 контактов
# 🔧 Этап 5: Нормализация данных
# ✅ Постобработка завершена успешно
```

## Расширение функциональности

### Добавление нового компонента

1. Создать новый файл в `src/postprocessing/`
2. Реализовать класс с методом обработки
3. Добавить в `__init__.py`
4. Интегрировать в `PostProcessor`
5. Написать тесты

### Пример нового компонента

```python
# src/postprocessing/custom_processor.py
class CustomProcessor:
    def process_data(self, data):
        # Кастомная логика
        return processed_data

# Интеграция в PostProcessor
class PostProcessor:
    def __init__(self, custom_processor=None):
        self.custom_processor = custom_processor or CustomProcessor()
    
    def process_llm_response(self, llm_result):
        # ... существующие этапы ...
        
        # Новый этап
        custom_result = self.custom_processor.process_data(enriched_data)
        
        return custom_result
```

## Совместимость

**Поддерживаемые форматы:**
- ✅ Новая структура `phones[]` (приоритет)
- ✅ Старая структура `phone` (совместимость)
- ✅ Глобальные `organization_id`
- ✅ Локальные `organization_id` (с маппингом)

**Версионирование:**
- Семантическое версионирование (SemVer)
- Обратная совместимость в рамках мажорной версии
- Миграционные скрипты при breaking changes

## Заключение

Модуль постобработки обеспечивает полную реализацию требований мини-ТЗ с модульной архитектурой, высокой производительностью и надежностью. Каждый компонент решает конкретную задачу и может использоваться независимо или в составе полного пайплайна.

**Ключевые преимущества:**
- 🎯 Полное соответствие мини-ТЗ
- 🔧 Модульная архитектура
- 📊 Детальная статистика и мониторинг
- 🧪 Полное покрытие тестами
- 🚀 Высокая производительность
- 🔄 Обратная совместимость
- 📝 Подробная документация