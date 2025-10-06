# Implementation Plan

## Обогащение телефонов контактов от связанных организаций

- [x] 1. Создать модуль ContactPhoneEnricher
  - Создать файл `src/postprocessing/contact_phone_enricher.py`
  - Реализовать класс `ContactPhoneEnricher` с методами инициализации
  - Добавить загрузку конфигурации из `config/settings.py`
  - Реализовать систему логирования и статистики
  - _Requirements: 1.1, 6.1, 7.1, 7.2_

- [x] 2. Реализовать систему scoring уверенности обогащения
  - [x] 2.1 Создать метод `_calculate_enrichment_confidence(contact, organization)`
    - Проверка корпоративного email (+0.3)
    - Проверка должности (+0.2)
    - Проверка role_in_message (+0.2)
    - Проверка совпадения города (+0.15)
    - Проверка value_score (+0.15)
    - Возврат итогового confidence score
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 2.2 Реализовать логику принятия решений на основе confidence
    - confidence < 0.5 → reject
    - 0.5 ≤ confidence < 0.75 → needs_review
    - confidence ≥ 0.75 → auto_accept
    - Логирование решений в метаданные
    - _Requirements: 2.6, 2.7, 2.8_

- [x] 3. Реализовать фильтрацию типов телефонов
  - [x] 3.1 Создать метод `_filter_organization_phones(org_phones)`
    - Фильтр по типам: main, office, fax
    - Исключение типа mobile
    - Обработка null типов как main с пониженным confidence
    - Возврат списка релевантных телефонов
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Реализовать защиту от дублирования телефонов
  - [x] 4.1 Создать метод `_check_phone_duplicate(contact_phones, new_phone)`
    - Проверка по полю normalized
    - Приоритет LLM-источника над org_enrichment
    - Логирование обнаруженных дубликатов
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 5. Реализовать основной метод обогащения
  - [x] 5.1 Создать метод `enrich_contacts_phones(contacts, organizations)`
    - Итерация по всем контактам
    - Проверка наличия organization_id
    - Получение организации по ID
    - Проверка наличия телефонов у организации
    - Вызов scoring и фильтрации
    - Добавление телефонов с метаданными
    - Обработка edge cases
    - _Requirements: 1.1, 1.3, 6.3, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 5.2 Добавить метаданные к обогащенным телефонам
    - Поле `source: "org_enrichment"`
    - Поле `org_gid: "<organization_gid>"`
    - Поле `confidence: <score>`
    - Поле `enriched_at: <timestamp>`
    - _Requirements: 1.5, 5.2_

- [x] 6. Реализовать систему метаданных и статистики
  - [x] 6.1 Создать структуру метаданных `contact_phone_enrichment`
    - Метаданные по каждому контакту: contact_gid, phones_added, phones_skipped
    - Причины пропуска: low_confidence, no_org_phones, already_has_phones, mobile_only
    - Confidence scores для каждого решения
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 6.2 Реализовать сбор статистики
    - contacts_enriched
    - phones_added_total
    - avg_confidence
    - phones_skipped_by_reason
    - _Requirements: 5.4_

- [x] 7. Интегрировать в PostProcessor
  - [x] 7.1 Добавить импорт ContactPhoneEnricher в postprocessor.py
    - Импортировать класс
    - Инициализировать в __init__
    - _Requirements: 6.1_

  - [x] 7.2 Добавить этап обогащения телефонов в пайплайн
    - Вставить после этапа "Разрешение конфликтов телефонов"
    - Вставить до этапа "Нормализация данных"
    - Обработка ошибок с продолжением пайплайна
    - _Requirements: 6.1, 6.2, 6.5_

  - [x] 7.3 Интегрировать метаданные в общий результат
    - Добавить секцию contact_phone_enrichment в postprocessing_metadata
    - Объединить статистику с общей статистикой
    - _Requirements: 5.1, 5.4_

  - [x] 7.4 Обеспечить нормализацию новых телефонов
    - Вызов DataNormalizer для обогащенных телефонов
    - UI-форматирование из E.164
    - Санитизация phone объектов
    - _Requirements: 6.4_

- [x] 8. Добавить конфигурацию
  - [x] 8.1 Создать секцию CONTACT_PHONE_ENRICHMENT_CONFIG в config/settings.py
    - enabled: bool (default True)
    - min_confidence_threshold: float (default 0.5)
    - review_threshold: float (default 0.75)
    - allowed_phone_types: list (default ["main", "office", "fax"])
    - enrichment_mode: str (default "balanced", options: "conservative", "balanced", "aggressive")
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 9. Создать тесты для модуля
  - [x] 9.1 Создать файл tests/test_contact_phone_enricher.py
    - Тест scoring системы с различными комбинациями факторов
    - Тест фильтрации типов телефонов
    - Тест защиты от дублирования
    - Тест обработки edge cases
    - Тест интеграции с PostProcessor
    - _Requirements: все_

- [x] 10. Обновить документацию
  - [x] 10.1 Добавить секцию в src/postprocessing/README_postprocessing.md
    - Описание модуля ContactPhoneEnricher
    - Алгоритм работы
    - Система scoring
    - Примеры использования
    - Конфигурация
    - _Requirements: все_

- [x] 11. Исправить нормализацию названий организаций (Issue #2)
  - [x] 11.1 Найти модуль нормализации названий организаций
    - Поиск функции trim_org_name или аналогичной
    - Проверка текущей логики удаления юридических форм
    - _Requirements: Issue #2_

  - [x] 11.2 Добавить "ООО" в список удаляемых префиксов
    - Обновить список legal_forms или prefixes
    - Добавить тесты для проверки удаления "ООО"
    - Проверить работу на примере "ООО Экомед" → "Экомед"
    - _Requirements: Issue #2_

  - [x] 11.3 Протестировать нормализацию на реальных данных
    - Запустить обработку email_004 с исправлением
    - Проверить, что "ООО Экомед" нормализуется корректно
    - _Requirements: Issue #2_

- [x] 12. Исправить баг с индексацией организаций (Critical Bug Fix)
  - [x] 12.1 Исправить создание индекса организаций в ContactPhoneEnricher
    - Изменить индексацию с `gid` на `organization_id`
    - Обеспечить корректный поиск организаций по числовому ID
    - Добавить логирование для отладки индексации
    - Исправить логику проверки корпоративного email (использовать website вместо domain)
    - _Requirements: 1.1, 8.2_

  - [x] 12.2 Протестировать исправление на реальных данных
    - Запустить обработку email_004 с исправлением
    - Проверить, что Тарасова Ирина получает телефон от Компании Хеликон (✅ получила +7 (800) 770-71-21)
    - Проверить, что Пашов Виктор НЕ получает mobile телефон от Экомед (✅ не получил из-за низкого confidence)
    - _Requirements: 1.1, 3.2_

- [x] 13. Добавить поддержку mobile обогащения с гибкой конфигурацией
  - [x] 13.1 Обновить конфигурацию в config/settings.py
    - Добавить секцию `mobile_enrichment` с флагом `enabled` (default: False)
    - Добавить `min_confidence_threshold` для mobile (default: 0.3)
    - Добавить `require_name_in_attachment` (default: False)
    - Добавить `proximity_boost` (default: True)
    - Добавить секцию `scoring_factors` с весами всех факторов
    - Добавить комментарии с инструкциями по настройке
    - _Requirements: 7.1, 7.5_

  - [x] 13.2 Расширить систему scoring в ContactPhoneEnricher
    - Добавить метод `_check_name_in_attachment()` для проверки имени во вложении
    - Добавить метод `_check_phone_proximity()` для проверки близости телефона к имени
    - Обновить `_calculate_enrichment_confidence()` с новыми факторами:
      * name_in_attachment (+0.3)
      * phone_proximity (+0.2)
    - Сделать веса факторов конфигурируемыми через `scoring_factors`
    - Добавить детальное логирование каждого фактора
    - _Requirements: 2.1-2.5_

  - [x] 13.3 Обновить метод фильтрации телефонов
    - Обновить `_filter_organization_phones()` для учета `mobile_enrichment.enabled`
    - Разрешать mobile телефоны при `enabled=True`
    - Применять специальный порог confidence для mobile
    - Логировать решения о включении/исключении mobile телефонов
    - Обновить статистику `phones_skipped_by_reason`
    - _Requirements: 3.1-3.4_

  - [x] 13.4 Добавить UI метаданные для иконок источника
    - Добавить поле `ui_metadata` в метод `_create_enriched_phone()`
    - Включить в `ui_metadata`:
      * `source_type`: "organization" (для иконки здания)
      * `source_name`: название организации (для tooltip)
      * `enrichment_method`: "postprocessing"
      * `icon`: "building" (тип иконки)
    - Обеспечить, что `ui_metadata` попадает в финальный JSON
    - Добавить примеры в документацию
    - _Requirements: 1.5, 5.2_

  - [x] 13.5 Улучшить LLM промпт (опционально)
    - Добавить инструкции о proximity телефонов к именам во вложениях
    - Уточнить правила присвоения телефонов из вложений контактам
    - Вставить после существующего пункта 5 о телефонах
    - НЕ менять JSON схему - никаких новых полей
    - _Requirements: 1.1_

  - [x] 13.6 Создать документацию по конфигурации
    - Добавить раздел в tasks.md с инструкциями по настройке
    - Описать все флаги и их влияние на обогащение
    - Привести примеры конфигураций для разных сценариев
    - Объяснить, как настраивать пороги confidence
    - Добавить troubleshooting для типичных проблем
    - _Requirements: 7.1-7.5_

  - [x] 13.7 Протестировать на кейсе Пашова Виктора
    - Включить `mobile_enrichment.enabled=True` в config
    - Запустить обработку email_004
    - Проверить, что Пашов Виктор получает телефон +7 (905) 088-88-82
    - Проверить наличие `ui_metadata` в структуре телефона
    - Проверить, что `source="org_enrichment"` и `icon="building"`
    - Проверить статистику в `postprocessing_metadata`
    - _Requirements: 1.1, 3.2, 5.2_

---

## 📖 Инструкции по конфигурации обогащения телефонов

### Файл конфигурации: `config/settings.py`

#### Основные настройки:

```python
CONTACT_PHONE_ENRICHMENT_CONFIG = {
    # Включение/выключение всего модуля обогащения
    'enabled': True,  # False - полностью отключить обогащение
    
    # Пороги confidence для обычных телефонов (main, office, fax)
    'min_confidence_threshold': 0.5,  # Минимальный порог для обогащения
    'review_threshold': 0.75,  # Порог для автоматического принятия
    
    # Разрешенные типы телефонов (без mobile)
    'allowed_phone_types': ['main', 'office', 'fax'],
    
    # Режим обогащения
    'enrichment_mode': 'balanced',  # 'conservative' | 'balanced' | 'aggressive'
}
```

#### Настройки mobile обогащения:

```python
CONTACT_PHONE_ENRICHMENT_CONFIG = {
    # ... основные настройки ...
    
    # Обогащение мобильными телефонами организаций
    'mobile_enrichment': {
        # ГЛАВНЫЙ ФЛАГ: включить/выключить mobile обогащение
        'enabled': False,  # True - разрешить обогащение mobile телефонами
        
        # Пониженный порог confidence для mobile (т.к. это более рискованно)
        'min_confidence_threshold': 0.3,  # Ниже, чем для обычных телефонов
        
        # Требовать упоминание имени контакта во вложении
        'require_name_in_attachment': False,  # True - строже, False - мягче
        
        # Учитывать близость телефона к имени во вложении
        'proximity_boost': True,  # True - добавляет +0.2 к confidence
    },
    
    # Веса факторов для расчета confidence (сумма может быть > 1.0)
    'scoring_factors': {
        'corporate_email': 0.3,      # Корпоративный email с доменом организации
        'position': 0.2,              # Наличие должности
        'role_in_message': 0.2,       # Роль в сообщении (sender, recipient)
        'city_match': 0.15,           # Совпадение города
        'high_value_score': 0.15,     # Высокий value_score (≥ 7)
        'name_in_attachment': 0.3,    # Имя найдено во вложении
        'phone_proximity': 0.2,       # Телефон рядом с именем во вложении
    }
}
```

### Сценарии использования:

#### Сценарий 1: Консервативный (только офисные телефоны)
```python
CONTACT_PHONE_ENRICHMENT_CONFIG = {
    'enabled': True,
    'enrichment_mode': 'conservative',
    'min_confidence_threshold': 0.75,  # Высокий порог
    'mobile_enrichment': {
        'enabled': False,  # Мобильные запрещены
    }
}
```

#### Сценарий 2: Сбалансированный (офисные + избранные mobile)
```python
CONTACT_PHONE_ENRICHMENT_CONFIG = {
    'enabled': True,
    'enrichment_mode': 'balanced',
    'min_confidence_threshold': 0.5,
    'mobile_enrichment': {
        'enabled': True,  # Мобильные разрешены
        'min_confidence_threshold': 0.4,  # Средний порог
        'require_name_in_attachment': False,
        'proximity_boost': True,
    }
}
```

#### Сценарий 3: Агрессивный (максимум обогащения)
```python
CONTACT_PHONE_ENRICHMENT_CONFIG = {
    'enabled': True,
    'enrichment_mode': 'aggressive',
    'min_confidence_threshold': 0.3,  # Низкий порог
    'mobile_enrichment': {
        'enabled': True,
        'min_confidence_threshold': 0.2,  # Очень низкий порог
        'require_name_in_attachment': False,
        'proximity_boost': True,
    }
}
```

### Как настроить для конкретного кейса:

**Задача**: Пашов Виктор должен получить mobile телефон от Экомед

**Решение**:
1. Установить `mobile_enrichment.enabled = True`
2. Установить `mobile_enrichment.min_confidence_threshold = 0.3` (или ниже)
3. Включить `proximity_boost = True` для учета близости телефона к имени
4. Перезапустить обработку

**Ожидаемый результат**:
- Confidence поднимется за счет факторов:
  - `name_in_attachment` (+0.3) - имя "Пашов Виктор" найдено в КП
  - `phone_proximity` (+0.2) - телефон рядом с именем в КП
  - Итого: 0.5+ (выше порога 0.3)
- Телефон будет добавлен с `ui_metadata.icon = "building"`

### Troubleshooting:

**Проблема**: Контакт не получает телефон
- Проверить `enabled = True` в основной конфигурации
- Проверить `mobile_enrichment.enabled = True` для mobile телефонов
- Проверить логи: какой confidence был рассчитан
- Понизить `min_confidence_threshold` если confidence близок к порогу

**Проблема**: Слишком много обогащений (ложные срабатывания)
- Повысить `min_confidence_threshold`
- Установить `enrichment_mode = 'conservative'`
- Для mobile: установить `require_name_in_attachment = True`

**Проблема**: UI не показывает иконку источника
- Проверить наличие поля `ui_metadata` в телефоне
- Проверить, что `ui_metadata.icon = "building"`
- Проверить, что UI читает это поле из JSON
