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