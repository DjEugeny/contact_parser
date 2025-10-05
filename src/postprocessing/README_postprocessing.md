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
├── data_enricher.py                 # Обогащение данных (с защитой от HQ-протечек)
├── data_normalizer.py               # Нормализация данных
├── advanced_contact_deduplicator.py # Продвинутая дедупликация контактов
├── org_email_enricher.py            # Обогащение email организаций (TASK-007B)
├── email_classifier.py              # Классификация email по типам
├── org_inn_resolver.py              # Система обогащения ИНН
├── inn_validator.py                 # Валидатор ИНН
├── inn_search_normalizer.py         # Нормализатор для поиска ИНН
├── inn_cache_system.py              # Кэш и переопределения ИНН
├── dadata_provider.py               # Провайдер DaData API
├── inn_data_types.py                # Структуры данных ИНН
├── attachment_evidence_extractor.py # Извлечение локации из вложений (TASK-008A)
├── org_location_enrichment.py       # Обогащение локации организаций (TASK-008A)
├── contact_location_safety.py       # Безопасность локации контактов (TASK-008B)
└── README.md                        # Документация
```

# Компоненты

## 1. PostProcessor

**Файл:** `postprocessor.py`  
**Назначение:** Главный координатор всех этапов постобработки

**Этапы обработки:**
1. Дедупликация и объединение организаций (п.3.a мини-ТЗ)
2. Обновление organization_id в контактах (п.3.b)
3. Фильтрация ценных контактов (п.3.c)
4. Назначение глобальных идентификаторов (GID)
5. Обогащение ИНН организаций (п.3.1)
6. **Обогащение email-адресов организаций (п.3.2, TASK-007B)**
7. **Обогащение локации организаций из вложений (TASK-008A)**
8. **Безопасное обогащение локации контактов (TASK-008B)** - извлечение персональных локационных сигналов
9. Разрешение конфликтов телефонов
10. **Защищенное обогащение city/address контактов (TASK-008B)** - применяется только при наличии персональной локации
11. Нормализация данных (п.3.f)
12. Очистка email организаций

**Использование:**
```python
from postprocessing import PostProcessor

postprocessor = PostProcessor()
processed_result = postprocessor.process_llm_response(llm_result, email_data)
```

## 2. OrganizationDeduplicator

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

## 3. ContactFilter

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
- **Безопасное обогащение полей `city`/`address` из организаций (с защитой от HQ-протечек)**
- Корпоративная разведка по email доменам

**Защита от HQ-протечек (TASK-008B):**
- Обогащение локации применяется **только** если у контакта уже есть персональная локация (city или address)
- Если оба поля пустые - обогащение **не применяется**, предотвращая ложное копирование HQ-адресов
- Логирование всех решений для отладки

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

## 6. AdvancedContactDeduplicator

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

## 7. Phone Disambiguation (PLAN-004)
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
- ✅ OrganizationEmailEnricher: извлечение и классификация email адресов
- ✅ EmailClassifier: классификация по типам mailbox
- ✅ Email cleanup: фильтрация персональных адресов

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
  'organizations_email_enriched': 18,  # Новая метрика
  'organization_deduplicator': {...},
  'contact_filter': {...},
  'data_enricher': {...},
  'data_normalizer': {...},
  'org_email_enricher': {              # Новые метрики
    'organizations_processed': 25,
    'emails_added': 42,
    'emails_skipped': 15,
    'from_headers': 30,
    'from_signature': 8,
    'from_attachments': 4
  }
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

## 9. Система обогащения email-адресов организаций (TASK-007B)

**Файл:** `org_email_enricher.py`  
**Назначение:** Автоматическое обогащение организаций email-адресами из заголовков, подписей и вложений письма

### Архитектура системы email обогащения

```
📧 Email Enrichment System
├── 🏢 Основной обогатитель (org_email_enricher.py)
├── 🔍 Классификатор email (email_classifier.py)
├── ⚙️ Конфигурация (config/org_profile.yml)
└── 🧪 Система тестирования
```

### Принципы работы

- **Многоисточниковое извлечение:** Email адреса извлекаются из заголовков письма, подписей и OCR-текста вложений
- **Умная классификация:** Разделение на организационные и персональные адреса по паттернам
- **Защита от перекрестного обогащения:** Исключение наших доменов из сторонних организаций
- **Дедупликация:** Автоматическое удаление дубликатов с сохранением порядка
- **Прозрачность:** Детальные метаданные о источниках и процессе обогащения

### Алгоритм обогащения

1. **Сбор кандидатов** из всех источников:
   - Заголовки письма (From, To, Cc, Reply-To, Sender)
   - Подпись письма (body и plain_text)
   - OCR-текст вложений с фильтрацией по релевантности

2. **Классификация email** по типам:
   - `SHARED_ORG`: Общие ящики (info@, mail@, sales@, support@)
   - `DEPARTMENT`: Департаментные (marketing@, hr@, finance@)
   - `TECHNICAL`: Технические (noreply@, robot@)
   - `GROUP_ALIAS`: Групповые (-team@, -all@)
   - `PERSONAL_INTERNAL`: Персональные корпоративные
   - `PERSONAL_EXTERNAL`: Персональные внешние

3. **Фильтрация и защита:**
   - Проверка принадлежности к организации по домену
   - Исключение наших доменов из сторонних организаций
   - Валидация формата email адресов

4. **Добавление в организацию:**
   - Только организационные типы (SHARED_ORG, DEPARTMENT, TECHNICAL, GROUP_ALIAS)
   - Дедупликация с существующими адресами
   - Сохранение метаданных об источниках

### Конфигурация классификации

```yaml
# config/org_profile.yml
shared_mailboxes_prefixes:
  - info
  - mail      # ← Исправлено: добавлен mail@ префикс
  - sales
  - support
  - service
  - office
  - torgi
  - hotline

department_prefixes:
  - marketing
  - hr
  - finance
  - accounting
  - buh

technical_prefixes:
  - noreply
  - no-reply
  - robot
  - do-not-reply

group_alias_suffixes:
  - -all
  - -team
  - -group
```

### Использование

```python
from postprocessing import OrganizationEmailEnricher

# Создание обогатителя
enricher = OrganizationEmailEnricher()

# Обогащение организаций
metadata = enricher.enrich_organizations_emails(organizations, email_data)

# Получение статистики
stats = enricher.get_stats()
```

### Структура метаданных

```json
"postprocessing_metadata": {
  "org_email_enrichment": {
    "<org_gid>": {
      "added": ["mail@company.ru", "info@company.ru"],
      "skipped": ["personal@company.ru"],
      "source": {
        "mail@company.ru": "headers",
        "info@company.ru": "signature"
      }
    }
  }
}
```

### Место в цепочке обработки

Обогащение email выполняется на **этапе 6** после назначения глобальных идентификаторов и обогащения ИНН:

```
1. Дедупликация организаций
2. Обновление organization_id в контактах  
3. Фильтрация ценных контактов
4. Назначение глобальных идентификаторов (GID)
5. Обогащение ИНН организаций
6. 📧 Обогащение email организаций ← НОВЫЙ ЭТАП
7. Разрешение конфликтов телефонов
8. Обогащение полей city/address
9. Нормализация данных
10. Очистка email организаций
```

### Интеграция с email-классификатором

После обогащения email адресов система выполняет **очистку email организаций** (этап 10), которая:

- Классифицирует все email в `organizations[].emails`
- Оставляет только организационные типы (SHARED_ORG, DEPARTMENT, TECHNICAL, GROUP_ALIAS)
- Удаляет персональные адреса (PERSONAL_INTERNAL, PERSONAL_EXTERNAL)
- Логирует все изменения в `postprocessing_metadata.email_classification`

### Статистика и мониторинг

```python
# Получение статистики обогащения
stats = enricher.get_stats()
# {
#   'organizations_processed': 5,
#   'emails_added': 12,
#   'emails_skipped': 8,
#   'from_headers': 15,
#   'from_signature': 4,
#   'from_attachments': 1
# }
```

### Отладка и тестирование

**Создание тестового файла:**
```python
# test_email_enrichment.py
from postprocessing import OrganizationEmailEnricher

enricher = OrganizationEmailEnricher()
result = enricher.enrich_organizations_emails(test_organizations, test_email_data)
```

**Проверка классификации:**
```python
from postprocessing.email_classifier import classify_mailbox, MailboxType

# Тестирование классификации конкретного адреса
result = classify_mailbox('mail@company.ru', None, corp_domains, config)
print(f"mail@company.ru -> {result.value}")
```

### Исправленные проблемы

#### Проблема: mail@ адреса удалялись из организаций

**Симптомы:**
- `mail@medcongress.ru` присутствовал в оригинальном ответе LLM
- В финальном результате email отсутствовал в организации
- Ошибка классификации как `UNKNOWN` типа

**Причина:**
- Префикс `mail` отсутствовал в конфигурации `shared_mailboxes_prefixes`
- Адреса типа `mail@` классифицировались как `UNKNOWN`
- Система очистки email удаляла все `UNKNOWN` адреса

**Решение:**
- Добавлен префикс `mail` в `config/org_profile.yml`
- Теперь `mail@company.ru` классифицируется как `SHARED_ORG`
- Email корректно сохраняется в организации

#### Проблема: 'int' object is not iterable

**Симптомы:**
- Ошибка при выполнении обогащения email
- Обработка завершалась успешно, но с предупреждением

**Причина:**
- Повреждение структуры данных в pipeline
- Организации содержали целые числа вместо словарей

**Решение:**
- Добавлена защитная проверка типов данных
- Логирование отладочной информации
- Graceful обработка поврежденных данных

```python
# Защитный код в org_email_enricher.py
if not isinstance(org_data, dict):
    self.logger.warning(f"Organization {org_id} is not a dict, skipping")
    continue
```

### Производительность

- **Обогащение одной организации:** < 50ms
- **Извлечение из заголовков:** < 10ms  
- **Классификация email:** < 5ms
- **Обработка OCR вложений:** < 100ms


## 10. Система безопасности локации контактов (TASK-008B)

**Файлы:** `contact_location_safety.py`, `data_enricher.py`, `postprocessor.py`  
**Назначение:** Предотвращение ложного обогащения контактов локационными данными (city/address) из HQ-блоков организаций

### Проблема

В исходном пайплайне контакты получали HQ-адрес/город организации (из блока реквизитов), как будто это их личные данные. Например:
- Сотрудник из Новосибирска получал адрес московского офиса компании
- Контакты без email получали HQ-локацию автоматически

### Решение

Контакты получают локационные данные **только** при наличии явных персональных сигналов с достаточным уровнем уверенности (confidence).

### Архитектура системы

```
🔒 Contact Location Safety System
├── 📍 Извлечение персональных сигналов (contact_location_safety.py)
├── 🛡️ Защита в data_enricher (data_enricher.py)
└── 🛡️ Защита в postprocessor (postprocessor.py)
```

### Принципы работы

1. **Персональные сигналы:** Локация извлекается только из персональных контекстов (подпись с ФИО/должностью, маркеры "представитель в г. X")
2. **HQ-блоки:** Адреса рядом с юридическими реквизитами (ИНН, ОГРН, р/с) считаются корпоративными и **не копируются** в контакты
3. **Confidence scoring:** Оценка уверенности в персональности сигнала (0.0-1.0)
4. **Двухуровневая защита:** Проверка как при извлечении, так и при backfill

### Алгоритм работы

#### Этап 1: Извлечение персональных сигналов

**Модуль:** `contact_location_safety.py`

**Источники персональных сигналов:**
- Блок подписи с ФИО/должностью контакта
- Маркеры: "г.", "город", "регион", "представитель", "офис в", "территориальный менеджер"
- Контекст рядом с упоминанием имени контакта в теле письма

**Определение HQ-блоков:**
- Наличие юридических маркеров: ИНН, ОГРН, р/с, к/с, БИК, ОКПО
- Адрес рядом с названием организации без персонального контекста

**Confidence scoring (0.0-1.0):**
- **0.9-1.0:** Сильные персональные маркеры ("представитель в", "офис в")
- **0.8-0.9:** Подпись с ФИО и должностью
- **0.7-0.8:** Подпись с локационными маркерами
- **0.6-0.7:** Упоминание в теле без контекста
- **0.0:** HQ-блок (не применяется)

**Пример:**
```python
# Персональный сигнал
"Воронова Светлана Сергеевна
Региональный представитель в г. Новосибирск"
→ city="Новосибирск", confidence=0.9

# HQ-блок
"ООО «ДНК-Технология»
ИНН: 7728469349
Адрес: г. Москва, Варшавское шоссе..."
→ НЕ применяется к контактам
```

#### Этап 2: Применение персональной локации

**Правила:**
- Применяется только если confidence >= min_confidence (по умолчанию 0.7)
- Не перезаписывает существующие значения city/address
- Для внутренних доменов требуется сильный сигнал (confidence >= 0.8)

#### Этап 3: Защита от backfill (двухуровневая)

**Место 1: `data_enricher._enrich_location_from_organization`**

Проверяет наличие персональной локации **перед** обогащением:

```python
has_personal_location = (
    _has_value(contact.get('city')) or 
    _has_value(contact.get('address'))
)

if not has_personal_location:
    # НЕ применяем обогащение - предотвращаем HQ-протечку
    return contact
```

**Место 2: `postprocessor._backfill_contact_city_address`**

Аналогичная проверка на этапе backfill:

```python
has_personal_location = (
    self._has_value(contact.get('city')) or 
    self._has_value(contact.get('address'))
)

allow_backfill = has_personal_location

if not allow_backfill:
    # Backfill запрещен
    provenance['backfill_skipped'] = 'no_personal_location_signal'
```

### Логика принятия решений

| Ситуация | city | address | Backfill | Причина |
|----------|------|---------|----------|---------|
| Нет персонального сигнала | `null` | `null` | ❌ ЗАПРЕЩЕН | Предотвращение HQ-протечки |
| Есть персональный город | `"Новосибирск"` | `null` | ✅ РАЗРЕШЕН | Может дополнить address |
| Есть персональный адрес | `null` | `"ул. Ленина, 10"` | ✅ РАЗРЕШЕН | Может дополнить city |
| Оба поля заполнены | `"Москва"` | `"ул. Ленина, 10"` | ✅ РАЗРЕШЕН | Но не перезапишет |
| Пустые строки | `""` | `"   "` | ❌ ЗАПРЕЩЕН | Считается как отсутствие данных |

### Конфигурация

```json
// config/processing_config.json
{
  "contact_location_safety": {
    "enabled": true,
    "min_confidence": 0.7,
    "internal_domains": ["dna-technology.ru"],
    "personal_markers": [
      "г.", "город", "регион", "представитель", 
      "офис в", "территориальный менеджер"
    ],
    "hq_markers": ["ИНН", "ОГРН", "р/с", "к/с", "БИК", "ОКПО"]
  }
}
```

### Метаданные

```json
"postprocessing_metadata": {
  "location_evidence": {
    "<contact_gid>": {
      "applied": true,
      "city": "Новосибирск",
      "address": null,
      "snippet": "Региональный представитель в г. Новосибирск",
      "confidence": 0.9,
      "source_type": "signature",
      "matched_patterns": ["представитель", "г."]
    }
  }
}
```

### Место в цепочке обработки

```
7. Обогащение локации организаций из вложений
8. 🔒 Безопасное обогащение локации контактов ← НОВЫЙ ЭТАП
   8.1. Извлечение персональных сигналов
   8.2. Применение локации с проверкой confidence
9. Разрешение конфликтов телефонов
10. 🛡️ Защищенное обогащение city/address ← ЗАЩИТА
    10.1. data_enricher: проверка персональной локации
    10.2. postprocessor: проверка перед backfill
11. Нормализация данных
```

### Примеры работы

#### Пример 1: Контакт без персональной локации

**Входные данные (от LLM):**
```json
{
  "name": "Клочкова-Абельянц Сатеник Аршавиловна",
  "organization_id": 1,
  "email": null,
  "city": null,
  "address": null
}
```

**Результат:**
```json
{
  "name": "Клочкова-Абельянц Сатеник Аршавиловна",
  "organization_id": 1,
  "email": null,
  "city": null,  // ✅ Не получила HQ-адрес
  "address": null  // ✅ Не получила HQ-адрес
}
```

**Лог:**
```
🔒 Контакт Клочкова-Абельянц без персональной локации. 
   Обогащение HQ-локации пропущено (TASK-008B).
```

#### Пример 2: Контакт с персональным сигналом

**Входные данные (от LLM):**
```json
{
  "name": "Воронова Светлана Сергеевна",
  "organization_id": 1,
  "position": "региональный представитель в СФО",
  "email": "s.voronova@dna-technology.ru",
  "city": "Новосибирск",  // Извлечено из подписи
  "address": null
}
```

**Результат:**
```json
{
  "name": "Воронова Светлана Сергеевна",
  "organization_id": 1,
  "position": "региональный представитель в СФО",
  "email": "s.voronova@dna-technology.ru",
  "city": "Новосибирск",  // ✅ Персональный сигнал сохранен
  "address": null  // ✅ Не получила HQ-адрес (города не совпадают)
}
```

**Лог:**
```
✅ Применена локация city='Новосибирск' для контакта <gid> 
   (confidence=0.90, source=signature)
```

### Статистика и мониторинг

```python
# Получение статистики
stats = contact_location_safety.get_stats()
# {
#   'contacts_processed': 10,
#   'locations_applied': 3,
#   'locations_rejected': 7,
#   'hq_blocks_detected': 5
# }
```

### Отладка

**Проверка логов:**
```bash
grep 'TASK-008B' data/logs/*.log | tail -30
```

**Ожидаемые сообщения:**
```
🔍 TASK-008B: _apply_contact_location_safety вызван для X контактов
🔍 TASK-008B: _enrich_location_from_organization вызван для контакта ...
🔍 TASK-008B: _backfill_contact_city_address вызван для X контактов
🔒 Контакт ... без персональной локации. Обогащение HQ-локации пропущено
✅ Применена локация city='...' для контакта ... (confidence=0.XX)
```

### Граничные случаи

**1. Несколько городов в подписи:**
- Выбирается город с наивысшим приоритетом (по контексту роли)
- Или первый упомянутый при равных приоритетах

**2. Города с дефисом (Санкт-Петербург):**
- Корректно извлекаются с помощью улучшенных регулярных выражений

**3. Внутренние сотрудники без персонального сигнала:**
- Остаются с city=null, address=null
- Не получают HQ-локацию автоматически

**4. Конфликт с существующими данными:**
- Существующие данные **не перезаписываются**
- Новые данные применяются только к пустым полям

## 11. Система обогащения локации организаций из вложений (TASK-008A)

**Файлы:** `attachment_evidence_extractor.py`, `org_location_enrichment.py`  
**Назначение:** Автоматическое обогащение организаций данными о местоположении (city/address) из реальных вложений

### Архитектура системы обогащения локации

```
📍 Location Enrichment System
├── 📎 Извлечение доказательств (attachment_evidence_extractor.py)
├── 🏢 Обогащение организаций (org_location_enrichment.py)
└── 🛡️ Защита от мусора (фильтры в обоих компонентах)
```

### Принципы работы

- **Гибридный подход:** Промпт LLM + постобработка с фильтрами
- **Контекстная близость:** Город/адрес принадлежит организации только если находится в её контекстном блоке (2-3 строки)
- **Защита от копирования:** Город/адрес одной организации не копируется другим
- **Фильтрация мусора:** Индексы без полного адреса (например, "117587") отклоняются
- **Прозрачность:** Полное отслеживание источников в метаданных

### Алгоритм обогащения

#### 1. Промпт LLM (первая линия защиты)

**Инструкции в промпте:**
- Текст вложений отделен разделителем "=== ВЛОЖЕНИЕ N: [имя файла] ==="
- Город/адрес принадлежит организации ТОЛЬКО если находится в её контекстном блоке
- Город/адрес в блоке "Кому:" или "для [город] Компания" → получатель
- Город/адрес рядом с реквизитами (ИНН, банк) → владелец реквизитов
- НЕ копировать город/адрес между организациями
- Индекс без города и улицы → НЕ является полным адресом

**Примеры в промпте:**
```
=== ВЛОЖЕНИЕ 1: Ком.пред.14.03.2025.pdf ===

ООО "ДНК-Технология"
ИНН: 7728469349
Адрес: 117587, г. Москва, Варшавское шоссе, д. 125Ж...

Кому: для г. Москва, Компания МИЛЛАБ

Конечный пользователь: ФБУЗ "...", г. Абакан

✅ ПРАВИЛЬНО:
- ДНК-Технология: city="Москва", address="117587, г. Москва..."
- МИЛЛАБ: city="Москва", address=null (город из "Кому:", адрес не указан)
- ФБУЗ: city="Абакан", address=null (город из блока, адрес не указан)

❌ НЕПРАВИЛЬНО:
- МИЛЛАБ: address="117587" (это адрес ДНК-Технология!)
```

#### 2. AttachmentEvidenceExtractor (извлечение доказательств)

**Обработка вложений:**
- Берем ВСЕ вложения из письма
- Ищем OCR-тексты в `data/final_results/texts/YYYY-MM-DD/`
- Анализируем тексты на предмет организаций и их локации
- Применяем фильтры к найденным адресам

**Фильтры при извлечении:**
```python
# 🛡️ Фильтр "только индекс"
if address and re.match(r'^\d{6}$', address.strip()):
    self.logger.debug(f"Отклонен адрес-индекс: {address}")
    address = None

# 🛡️ Фильтр "короткий адрес без города"
if address and len(address) < 20 and not city:
    self.logger.debug(f"Отклонен короткий адрес без города: {address}")
    address = None
```

**Паттерны поиска:**
- Города: `г\.\s*([А-ЯЁ][а-яё\-\s]+)`, `город\s+([А-ЯЁ][а-яё\-\s]+)`
- Адреса: `(?:Адрес|Юридический адрес|Фактический адрес):\s*(.+)`

#### 3. OrgLocationEnrichment (применение обогащения)

**Матчинг организаций:**
- Fuzzy matching по названию (порог 0.9)
- Нормализация названий (удаление юр. форм, кавычек)
- Сопоставление с доказательствами из вложений

**Фильтры при обогащении:**
```python
# 🛡️ Фильтр "только индекс"
if re.match(r'^\d{6}$', address_value.strip()):
    self.logger.debug(f"Отклонен адрес-индекс при обогащении: {address_value}")
    address_value = None

# 🛡️ Фильтр "короткий адрес без города"
if address_value and len(address_value) < 20 and not enriched_org.get('city'):
    self.logger.debug(f"Отклонен короткий адрес без города при обогащении: {address_value}")
    address_value = None
```

**Правила применения:**
- Заполняются только пустые поля (`apply_if_empty_only=True`)
- Не перезаписываются данные, заполненные LLM
- Обработка конфликтов (несколько разных городов) → `needs_review=true`

### Место в цепочке обработки

Обогащение локации выполняется на **этапе 7** после обогащения email:

```
1. Дедупликация организаций
2. Обновление organization_id в контактах
3. Фильтрация ценных контактов
4. Назначение глобальных идентификаторов (GID)
5. Обогащение ИНН организаций
6. Обогащение email организаций
7. 📍 Обогащение локации из вложений ← НОВЫЙ ЭТАП
   7.1. Извлечение доказательств (AttachmentEvidenceExtractor)
   7.2. Применение обогащения (OrgLocationEnrichment)
8. Разрешение конфликтов телефонов
9. Обогащение полей city/address (из организаций в контакты)
10. Нормализация данных
11. Очистка email организаций
```

### Использование

```python
from postprocessing import AttachmentEvidenceExtractor, OrgLocationEnrichment

# Извлечение доказательств
extractor = AttachmentEvidenceExtractor()
evidence_list = extractor.extract(email_data)

# Обогащение организаций
enrichment = OrgLocationEnrichment()
metadata = {}
enriched_orgs = enrichment.enrich_organizations(
    organizations, evidence_list, metadata
)
```

### Структура метаданных

```json
"postprocessing_metadata": {
  "enrichment": {
    "org_location_from_attachments": {
      "evidence_count": 3,
      "organizations_enriched": 1,
      "cities_added": 1,
      "addresses_added": 0,
      "conflicts_detected": 0,
      "location_evidence": {
        "<org_gid>": {
          "applied": true,
          "city": "Москва",
          "address": null,
          "source": {
            "type": "attachment",
            "filename": "Ком.пред.14.03.2025.pdf",
            "method": "context_proximity"
          },
          "confidence": 0.9
        }
      }
    }
  }
}
```

### Результат тестирования (письмо 016)

**До улучшений:**
```
МИЛЛАБ: city="Москва", address="117587" ❌ (индекс ДНК-Технология)
ФБУЗ: city="Абакан", address="117587" ❌ (индекс ДНК-Технология)
```

**После улучшений:**
```
ДНК-Технология:
  city: "Москва" ✅
  address: "117587, г. Москва, Варшавское шоссе, д. 125Ж..." ✅

МИЛЛАБ:
  city: "Москва" ✅ (из "для Москва Компания МИЛЛАБ")
  address: null ✅ (было "117587" - исправлено!)

ФБУЗ "Центр Гигиены и Эпидемиологии в Республике Хакасия":
  city: "Абакан" ✅ (из "для Абакан ЦГиЭ")
  address: null ✅ (было "117587" - исправлено!)
```

### Ключевые улучшения

#### 1. Промпт LLM
- Добавлены инструкции о разделителях вложений
- Правила принадлежности города/адреса по контексту
- Примеры с правильными и неправильными результатами
- **Результат:** LLM правильно возвращает `address: null` для МИЛЛАБ и ФБУЗ

#### 2. Фильтры в постобработке
- Фильтр "только индекс" (^\d{6}$)
- Фильтр "короткий адрес без города" (< 20 символов)
- Двухуровневая защита (extraction + enrichment)
- **Результат:** Постобработка не добавляет мусорные адреса

### Конфигурация

```python
# AttachmentEvidenceConfig
config = AttachmentEvidenceConfig(
    enabled=True,
    max_snippet_len=240,
    fuzzy_ratio_threshold=0.9
)

# OrgLocationEnrichmentConfig
config = OrgLocationEnrichmentConfig(
    enabled=True,
    apply_if_empty_only=True,  # Не перезаписывать заполненные поля
    fuzzy_ratio_threshold=0.9
)
```

### Статистика и мониторинг

```python
# Получение статистики
stats = enrichment.get_stats()
# {
#   'organizations_enriched': 1,
#   'cities_added': 1,
#   'addresses_added': 0,
#   'conflicts_detected': 0
# }
```

### Производительность

- **Извлечение доказательств:** < 100ms на вложение
- **Обогащение организации:** < 50ms
- **Fuzzy matching:** < 10ms на организацию
- **Общее время:** < 200ms на письмо с 1-3 вложениями

### Отладка и тестирование

**Тестовый файл:** `test_standalone_attachment_evidence.py`

```bash
python test_standalone_attachment_evidence.py
```

**Проверка на реальном письме:**
```bash
python src/api_pipeline_validator.py --mode first10 \
  --start "email_016_20250729_20250729_dna-technology_ru_6360137e.json" \
  --count 1
```

### Решение проблем

#### Проблема: Индексы копируются всем организациям

**Симптомы:**
- МИЛЛАБ и ФБУЗ получают address="117587"
- Это индекс ДНК-Технология из шапки документа

**Причина:**
- Постобработка извлекала "117587" как адрес
- Применяла его ко всем организациям без фильтрации

**Решение:**
- Добавлены фильтры "только индекс" и "короткий адрес"
- Двухуровневая защита (extraction + enrichment)
- **Результат:** Индексы больше не копируются

#### Проблема: LLM копирует адреса между организациями

**Симптомы:**
- LLM возвращает один и тот же адрес для разных организаций

**Причина:**
- Недостаточно четкие инструкции в промпте
- Отсутствие примеров с правильным поведением

**Решение:**
- Добавлены инструкции о контекстной близости
- Добавлены примеры с реальным случаем МИЛЛАБ
- Правило: "Лучше пропустить, чем присвоить чужой адрес"
- **Результат:** LLM правильно возвращает `address: null`

## 11. Обработка ошибок

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

## 12. Расширение функциональности

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

## 13. Совместимость

**Поддерживаемые форматы:**
- ✅ Новая структура `phones[]` (приоритет)
- ✅ Старая структура `phone` (совместимость)
- ✅ Глобальные `organization_id`
- ✅ Локальные `organization_id` (с маппингом)

**Версионирование:**
- Семантическое версионирование (SemVer)
- Обратная совместимость в рамках мажорной версии
- Миграционные скрипты при breaking changes

## 14. Заключение

Модуль постобработки обеспечивает полную реализацию требований мини-ТЗ с модульной архитектурой, высокой производительностью и надежностью. Каждый компонент решает конкретную задачу и может использоваться независимо или в составе полного пайплайна.

**Ключевые преимущества:**
- 🎯 Полное соответствие мини-ТЗ
- 🔧 Модульная архитектура
- 📊 Детальная статистика и мониторинг
- 🧪 Полное покрытие тестами
- 🚀 Высокая производительность
- 🔄 Обратная совместимость
- 📝 Подробная документация