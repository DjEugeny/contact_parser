# 📞 Документация: Обогащение телефонов контактов

## Описание

Модуль `ContactPhoneEnricher` автоматически обогащает контакты телефонами от связанных организаций с использованием интеллектуальной системы scoring и гибкой конфигурации.

## Файл конфигурации

Настройки находятся в `config/settings.py` в секции `CONTACT_PHONE_ENRICHMENT_CONFIG`.

---

## 🎛️ Параметры конфигурации

### Основные настройки

```python
CONTACT_PHONE_ENRICHMENT_CONFIG = {
    # Включение/выключение всего модуля обогащения
    'enabled': True,  # False - полностью отключить обогащение
    
    # Пороги confidence для обычных телефонов (main, office, fax)
    'min_confidence_threshold': 0.5,  # Минимальный порог для обогащения (0.0-1.0)
    'review_threshold': 0.75,  # Порог для автоматического принятия без проверки
    
    # Разрешенные типы телефонов для обогащения (без mobile по умолчанию)
    'allowed_phone_types': ['main', 'office', 'fax'],
    
    # Режим обогащения (влияет на пороги confidence)
    'enrichment_mode': 'balanced',  # 'conservative' | 'balanced' | 'aggressive'
}
```

### Mobile обогащение

```python
'mobile_enrichment': {
    # ГЛАВНЫЙ ФЛАГ: разрешить обогащение мобильными телефонами организаций
    'enabled': False,  # True - разрешить добавление mobile телефонов контактам
    
    # Пониженный порог confidence для mobile (т.к. это более рискованно)
    'min_confidence_threshold': 0.3,  # Рекомендуется 0.3-0.5
    
    # Требовать упоминание имени контакта во вложении для mobile обогащения
    'require_name_in_attachment': False,  # True - строже, False - мягче
    
    # Учитывать близость телефона к имени во вложении (proximity boost)
    'proximity_boost': True,  # True - добавляет +0.2 к confidence
}
```

### Веса факторов scoring

```python
'scoring_factors': {
    'corporate_email': 0.3,      # Корпоративный email с доменом организации
    'position': 0.2,              # Наличие должности у контакта
    'role_in_message': 0.2,       # Активная роль (sender, recipient)
    'city_match': 0.15,           # Совпадение города контакта и организации
    'high_value_score': 0.15,     # Высокий value_score (≥ 7)
    'name_in_attachment': 0.3,    # Имя контакта найдено во вложении
    'phone_proximity': 0.2,       # Телефон рядом с именем во вложении (2-3 строки)
}
```

---

## 📊 Система scoring

### Как рассчитывается confidence?

Для каждого контакта система проверяет несколько факторов и суммирует их веса:

| Фактор | Вес | Условие |
|--------|-----|---------|
| Корпоративный email | 0.3 | Email контакта содержит домен организации |
| Должность | 0.2 | У контакта указана должность |
| Роль в сообщении | 0.2 | Контакт - sender или recipient |
| Совпадение города | 0.15 | Город контакта совпадает с городом организации |
| Высокий value_score | 0.15 | value_score контакта ≥ 7 |
| Имя во вложении | 0.3 | Имя контакта найдено в тексте вложения |
| Proximity телефона | 0.2 | Телефон находится рядом с именем во вложении |

**Максимальный confidence**: 1.55 (если все факторы применяются)

### Пороги принятия решений

- **confidence < 0.5** (или mobile_min_confidence для mobile) → **REJECT** (обогащение отклонено)
- **0.5 ≤ confidence < 0.75** → **NEEDS_REVIEW** (требуется проверка)
- **confidence ≥ 0.75** → **AUTO_ACCEPT** (автоматическое принятие)

---

## 🎯 Сценарии использования

### Сценарий 1: Консервативный (только офисные телефоны)

**Цель**: Максимальная безопасность, только проверенные офисные телефоны

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

**Результат**: Обогащаются только контакты с высоким confidence (≥0.75), mobile телефоны исключены.

---

### Сценарий 2: Сбалансированный (офисные + избранные mobile)

**Цель**: Баланс между полнотой данных и безопасностью

```python
CONTACT_PHONE_ENRICHMENT_CONFIG = {
    'enabled': True,
    'enrichment_mode': 'balanced',
    'min_confidence_threshold': 0.5,
    'mobile_enrichment': {
        'enabled': True,  # Мобильные разрешены
        'min_confidence_threshold': 0.3,  # Средний порог для mobile
        'require_name_in_attachment': False,
        'proximity_boost': True,
    }
}
```

**Результат**: Офисные телефоны при confidence ≥0.5, mobile телефоны при confidence ≥0.3.

---

### Сценарий 3: Агрессивный (максимум обогащения)

**Цель**: Максимальное обогащение данных

```python
CONTACT_PHONE_ENRICHMENT_CONFIG = {
    'enabled': True,
    'enrichment_mode': 'aggressive',
    'min_confidence_threshold': 0.3,  # Низкий порог
    'mobile_enrichment': {
        'enabled': True,
        'min_confidence_threshold': 0.0,  # Очень низкий порог
        'require_name_in_attachment': False,
        'proximity_boost': True,
    }
}
```

**Результат**: Максимальное количество обогащений, возможны ложные срабатывания.

---

## 🔧 Настройка для конкретных задач

### Задача: Обогатить контакт без email и должности

**Проблема**: Контакт имеет низкий confidence из-за отсутствия email и должности.

**Решение**:
1. Включить `mobile_enrichment.enabled = True`
2. Понизить `mobile_enrichment.min_confidence_threshold` до 0.0-0.2
3. Убедиться, что имя контакта есть во вложении (добавит +0.3 к confidence)

```python
'mobile_enrichment': {
    'enabled': True,
    'min_confidence_threshold': 0.0,  # Разрешить даже при низком confidence
}
```

---

### Задача: Обогащать только при наличии имени во вложении

**Цель**: Дополнительная проверка для mobile телефонов.

**Решение**:
```python
'mobile_enrichment': {
    'enabled': True,
    'min_confidence_threshold': 0.3,
    'require_name_in_attachment': True,  # Строгое требование
}
```

---

## 🎨 UI метаданные

Каждый обогащенный телефон содержит поле `ui_metadata` для отображения в интерфейсе:

```json
{
  "type": "mobile",
  "number": "+7 (905) 088-88-82",
  "source": "org_enrichment",
  "confidence": 0.5,
  "ui_metadata": {
    "source_type": "organization",
    "source_name": "Экомед",
    "enrichment_method": "postprocessing",
    "icon": "building",
    "is_mobile_enrichment": true
  }
}
```

### Использование в UI

```javascript
// Пример использования в React/Vue
if (phone.ui_metadata) {
  const icon = phone.ui_metadata.icon; // "building"
  const tooltip = `Телефон от организации: ${phone.ui_metadata.source_name}`;
  const isMobile = phone.ui_metadata.is_mobile_enrichment;
  
  // Показать иконку здания справа от телефона
  // При наведении показать tooltip с названием организации
}
```

---

## 🐛 Troubleshooting

### Проблема: Контакт не получает телефон

**Диагностика**:
1. Проверить `enabled = True` в основной конфигурации
2. Проверить `mobile_enrichment.enabled = True` для mobile телефонов
3. Посмотреть логи: какой confidence был рассчитан
4. Проверить метаданные в `postprocessing_metadata.contact_phone_enrichment`

**Решение**:
- Понизить `min_confidence_threshold` если confidence близок к порогу
- Для mobile: понизить `mobile_enrichment.min_confidence_threshold`
- Проверить, что у организации есть телефоны нужного типа

---

### Проблема: Слишком много обогащений (ложные срабатывания)

**Решение**:
1. Повысить `min_confidence_threshold` до 0.6-0.75
2. Установить `enrichment_mode = 'conservative'`
3. Для mobile: установить `require_name_in_attachment = True`
4. Повысить `mobile_enrichment.min_confidence_threshold` до 0.5

---

### Проблема: UI не показывает иконку источника

**Диагностика**:
1. Проверить наличие поля `ui_metadata` в телефоне
2. Проверить, что `ui_metadata.icon = "building"`
3. Убедиться, что UI читает это поле из JSON

**Решение**:
- Обновить код UI для чтения `phone.ui_metadata`
- Проверить версию модуля обогащения (должна быть ≥1.1.0)

---

## 📈 Мониторинг и статистика

### Метаданные в результате обработки

После обработки в `postprocessing_metadata` доступна секция `contact_phone_enrichment`:

```json
{
  "contact_phone_enrichment": {
    "statistics": {
      "contacts_processed": 10,
      "contacts_enriched": 7,
      "phones_added_total": 12,
      "avg_confidence": 0.68,
      "phones_skipped_by_reason": {
        "low_confidence": 2,
        "no_org_phones": 1,
        "mobile_only": 0,
        "duplicate": 0
      }
    }
  }
}
```

### Ключевые метрики

- **contacts_enriched / contacts_processed** - процент успешных обогащений
- **avg_confidence** - средний уровень уверенности (оптимально 0.6-0.8)
- **phones_skipped_by_reason** - причины пропуска (для оптимизации настроек)

---

## 🔐 Безопасность

### Защита персональных данных

1. **Mobile телефоны** по умолчанию исключены (требуют явного включения)
2. **Приоритет LLM-источника**: если LLM уже присвоил телефон контакту, обогащение не перезаписывает его
3. **Проверка дубликатов**: по normalized полю (E.164 формат)
4. **Метаданные источника**: каждый обогащенный телефон помечен `source: "org_enrichment"`

### Рекомендации

- Для продакшена используйте `enrichment_mode: 'balanced'` или `'conservative'`
- Включайте `mobile_enrichment` только если уверены в качестве данных
- Регулярно проверяйте метрику `avg_confidence` (должна быть ≥0.5)
- Мониторьте `phones_skipped_by_reason` для выявления проблем

---

## 📚 Дополнительные ресурсы

- **Спецификация**: `.kiro/specs/contact-phone-enrichment/`
- **Исходный код**: `src/postprocessing/contact_phone_enricher.py`
- **Тесты**: `tests/test_contact_phone_enricher.py`
- **Документация постобработки**: `src/postprocessing/README_postprocessing.md`

---

## 🆕 История изменений

### v1.1.0 (2025-10-06)
- ✅ Добавлена поддержка mobile обогащения с гибкой конфигурацией
- ✅ Новые факторы scoring: name_in_attachment, phone_proximity
- ✅ UI метаданные для иконок источника
- ✅ Конфигурируемые веса факторов
- ✅ Улучшенная логика принятия решений для mobile телефонов

### v1.0.0 (2025-01-10)
- ✅ Первая версия модуля обогащения
- ✅ Базовая система scoring с 5 факторами
- ✅ Фильтрация по типам телефонов
- ✅ Защита от дублирования

---

**Версия документации**: 1.1.0  
**Дата обновления**: 2025-10-06
