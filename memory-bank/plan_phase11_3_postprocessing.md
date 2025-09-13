# План этапа 11.3: Реализация постобработки данных

**Дата создания:** 2025-09-13 18:20 (UTC+07)  
**Основание:** Мини-ТЗ п.3 - Постобработка: полный алгоритм  
**Приоритет:** ВЫСОКИЙ  
**Статус:** 🎯 В ПЛАНАХ  

## Цель этапа

Реализовать полный алгоритм постобработки данных согласно мини-ТЗ для:
- Дедупликации и объединения организаций
- Назначения глобальных organization_id
- Фильтрации ценных контактов
- Обогащения полей city и address
- Нормализации телефонов и email

## Подэтапы реализации

### 11.3.1 Дедупликация и объединение организаций

**Задачи:**
1. Создать класс `OrganizationDeduplicator`
2. Реализовать алгоритм поиска дубликатов по:
   - Название (strict/fuzzy сравнение)
   - ИНН (точное совпадение)
   - Сайт (точное совпадение)
3. Создать систему глобальных organization_id
4. Реализовать объединение данных (emails, phones, address)

**Код:**
```python
class OrganizationDeduplicator:
    def __init__(self):
        self.global_organizations = {}  # {global_id: organization_data}
        self.next_global_id = 1
        
    def process_organizations(self, llm_organizations):
        """Обработка организаций из LLM ответа"""
        local_to_global_mapping = {}
        
        for org in llm_organizations:
            global_id = self._find_or_create_organization(org)
            local_to_global_mapping[org['organization_id']] = global_id
            
        return local_to_global_mapping
```

### 11.3.2 Обновление organization_id в контактах

**Задачи:**
1. Создать функцию обновления ссылок
2. Заменить локальные organization_id на глобальные
3. Валидировать целостность связей

**Код:**
```python
def update_contact_organization_ids(contacts, mapping):
    """Обновление organization_id в контактах"""
    for contact in contacts:
        local_id = contact.get('organization_id')
        if local_id in mapping:
            contact['organization_id'] = mapping[local_id]
    return contacts
```

### 11.3.3 Фильтрация ценных контактов

**Задачи:**
1. Реализовать функцию `evaluate_contact_value`
2. Применить фильтрацию к массиву contacts
3. Перенести "неценные" контакты в organizations

**Код:**
```python
def evaluate_contact_value(contact):
    """Оценка ценности контакта согласно мини-ТЗ"""
    score = 0
    if contact.get('name'): score += 3
    if contact.get('organization_id'): score += 2
    if contact.get('position'): score += 2
    if contact.get('email'): score += 2
    if contact.get('phones') and len(contact['phones']) > 0: score += 2
    if contact.get('city'): score += 1
    if contact.get('inn'): score += 1
    return score >= 4  # Минимальный порог
```

### 11.3.4 Обогащение полей city и address

**Задачи:**
1. Создать функцию обогащения контактов
2. Копировать city/address из организации при отсутствии
3. Сохранять индивидуальные данные контакта

**Код:**
```python
def enrich_contact_location(contact, organizations):
    """Обогащение полей city и address"""
    org_id = contact.get('organization_id')
    if org_id in organizations:
        org = organizations[org_id]
        
        if not contact.get('city') and org.get('city'):
            contact['city'] = org['city']
            
        if not contact.get('address') and org.get('address'):
            contact['address'] = org['address']
    
    return contact
```

### 11.3.5 Нормализация телефонов и email

**Задачи:**
1. Интегрировать `phone_normalizer.py`
2. Нормализовать телефоны в новом формате phones[]
3. Валидировать email адреса
4. Очистить и стандартизировать имена

**Код:**
```python
from phone_normalizer import normalize_phone

def normalize_contact_data(contact):
    """Нормализация данных контакта"""
    # Нормализация телефонов
    if contact.get('phones'):
        for phone_obj in contact['phones']:
            phone_obj['normalized'] = normalize_phone(phone_obj['number'])
    
    # Валидация email
    if contact.get('email'):
        contact['email_valid'] = validate_email(contact['email'])
    
    return contact
```

### 11.3.6 Интеграция в IntegratedLLMProcessor

**Задачи:**
1. Обновить `IntegratedLLMProcessor` для работы с новой структурой
2. Добавить вызов алгоритмов постобработки
3. Обновить валидацию JSON схемы
4. Протестировать на реальных данных

**Изменения в коде:**
```python
class IntegratedLLMProcessor:
    def __init__(self):
        self.org_deduplicator = OrganizationDeduplicator()
        self.contact_filter = ContactFilter()
        
    def process_llm_response(self, llm_result):
        """Обработка ответа LLM с постобработкой"""
        # 1. Дедупликация организаций
        mapping = self.org_deduplicator.process_organizations(
            llm_result['organizations']
        )
        
        # 2. Обновление organization_id в контактах
        contacts = update_contact_organization_ids(
            llm_result['contacts'], mapping
        )
        
        # 3. Фильтрация ценных контактов
        valuable_contacts = self.contact_filter.filter_valuable_contacts(contacts)
        
        # 4. Обогащение полей
        enriched_contacts = [
            enrich_contact_location(contact, self.org_deduplicator.global_organizations)
            for contact in valuable_contacts
        ]
        
        # 5. Нормализация данных
        normalized_contacts = [
            normalize_contact_data(contact)
            for contact in enriched_contacts
        ]
        
        return {
            'organizations': list(self.org_deduplicator.global_organizations.values()),
            'contacts': normalized_contacts,
            'business_context': llm_result['business_context'],
            'summary': llm_result['summary'],
            'key_points': llm_result['key_points'],
            'commercial_offers': llm_result['commercial_offers']
        }
```

## Файлы для создания/изменения

### Новые файлы:
1. `src/core/organization_deduplicator.py` - дедупликация организаций
2. `src/core/contact_filter.py` - фильтрация контактов
3. `src/core/data_enricher.py` - обогащение данных
4. `src/core/data_normalizer.py` - нормализация данных
5. `tests/test_postprocessing.py` - тесты постобработки

### Изменяемые файлы:
1. `src/integrated_llm_processor.py` - интеграция постобработки
2. `src/core/validator.py` - обновление JSON схемы
3. `src/google_sheets_bridge.py` - поддержка новой структуры

## Критерии успеха

### Функциональные:
- ✅ Корректная дедупликация организаций по названию, ИНН, сайту
- ✅ Успешное назначение глобальных organization_id
- ✅ Фильтрация контактов по функции evaluate_contact_value
- ✅ Обогащение полей city и address из организаций
- ✅ Нормализация телефонов и email

### Качественные:
- ✅ Сохранение >95% ценных контактов
- ✅ Устранение дубликатов организаций
- ✅ Корректные связи между контактами и организациями
- ✅ Валидная JSON структура на выходе

### Технические:
- ✅ Покрытие тестами >90%
- ✅ Производительность <2 сек на письмо
- ✅ Совместимость с существующим кодом

## Временные рамки

- **День 1:** Создание классов дедупликации и фильтрации
- **День 2:** Реализация обогащения и нормализации данных
- **День 3:** Интеграция в IntegratedLLMProcessor
- **День 4:** Тестирование и отладка
- **День 5:** Валидация на полном датасете

## Зависимости

- ✅ Обновленный промпт (этап 11.2) - завершен
- ✅ Тестирование промпта (этап 11.2) - в процессе
- ✅ Обновление JSON схемы валидации
- ✅ Интеграция с phone_normalizer.py

---

**Готов к началу реализации после завершения тестирования промпта!**

2025-09-13 18:20 (UTC+07)