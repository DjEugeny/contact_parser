# Тест интеграции валидации и постпроцессинга

**Дата:** 2025-01-17 15:00 (UTC+07)  
**Статус:** Создан  
**Цель:** Проверить корректную работу интегрированного пайплайна валидации и постпроцессинга

## 🧪 Тест-кейсы

### 1. Валидный ответ LLM с дублирующимися организациями

**Входные данные:**
```json
{
  "organizations": [
    {
      "organization_id": 1,
      "name": "ДНК-Технология",
      "inn": "1901066506",
      "city": "Москва",
      "emails": ["info@dna-technology.ru"],
      "phones": ["8 800 200-75-15"]
    },
    {
      "organization_id": 2,
      "name": "ДНК-Технология",
      "inn": "1901066506",
      "city": "Москва",
      "emails": ["info@dna-technology.ru"],
      "phones": ["8 800 200-75-15"]
    }
  ],
  "contacts": [
    {
      "name": "Гоголева Мария",
      "organization_id": 1,
      "email": "m.gogoleva@dna-technology.ru",
      "phones": [
        {
          "type": "main",
          "number": "+7(495) 640-17-71"
        }
      ],
      "confidence": 0.95
    },
    {
      "name": "Петров Иван",
      "organization_id": 2,
      "email": "i.petrov@dna-technology.ru",
      "phones": [
        {
          "type": "mobile",
          "number": "+7(926) 123-45-67"
        }
      ],
      "confidence": 0.85
    }
  ]
}
```

**Ожидаемый результат:**
- ✅ Валидация пройдена
- ✅ Дублирующиеся организации объединены
- ✅ organization_id в контактах обновлены
- ✅ Контакты отфильтрованы по ценности
- ✅ Телефоны нормализованы

### 2. Ответ с ошибками валидации

**Входные данные:**
```json
{
  "organizations": [
    {
      "organization_id": 1,
      "name": "ТестКомпания",
      "inn": "invalid_inn",
      "city": "Москва"
      // Отсутствуют обязательные поля emails и phones
    }
  ],
  "contacts": [
    {
      "name": "Тестовый Контакт",
      "organization_id": 1,
      "email": "invalid-email",
      "confidence": 1.5  // Некорректное значение
    }
  ]
}
```

**Ожидаемый результат:**
- ⚠️ Автокоррекция применена
- ✅ Добавлены обязательные поля
- ✅ Исправлены некорректные значения
- ✅ Постпроцессинг применён к исправленным данным

### 3. Критически невалидный ответ

**Входные данные:**
```json
{
  "invalid_structure": true,
  "random_data": [1, 2, 3]
}
```

**Ожидаемый результат:**
- ❌ Валидация не пройдена
- 🛡️ Graceful degradation применён
- ✅ Возвращена минимально валидная структура
- ❌ Постпроцессинг НЕ применён

## 🔧 Код теста

```python
def test_validation_postprocessing_integration():
    """Тест интеграции валидации и постпроцессинга"""
    from src.core.validator import LLMResponseValidator
    
    validator = LLMResponseValidator()
    
    # Тест 1: Валидные данные с дублями
    test_data_1 = {
        "organizations": [
            {
                "organization_id": 1,
                "name": "ДНК-Технология",
                "inn": "1901066506",
                "city": "Москва",
                "emails": ["info@dna-technology.ru"],
                "phones": ["8 800 200-75-15"]
            },
            {
                "organization_id": 2,
                "name": "ДНК-Технология",
                "inn": "1901066506",
                "city": "Москва",
                "emails": ["info@dna-technology.ru"],
                "phones": ["8 800 200-75-15"]
            }
        ],
        "contacts": [
            {
                "name": "Гоголева Мария",
                "organization_id": 1,
                "email": "m.gogoleva@dna-technology.ru",
                "phones": [
                    {
                        "type": "main",
                        "number": "+7(495) 640-17-71"
                    }
                ],
                "confidence": 0.95
            }
        ]
    }
    
    result_1 = validator.validate_and_postprocess(test_data_1)
    
    # Проверки
    assert "organizations" in result_1
    assert "contacts" in result_1
    assert len(result_1["organizations"]) == 1  # Дубли объединены
    
    print("✅ Тест 1 пройден: валидные данные обработаны")
    
    # Тест 2: Невалидные данные
    test_data_2 = {
        "invalid_structure": True,
        "random_data": [1, 2, 3]
    }
    
    result_2 = validator.validate_and_postprocess(test_data_2)
    
    # Проверки graceful degradation
    assert "organizations" in result_2
    assert "contacts" in result_2
    assert isinstance(result_2["organizations"], list)
    assert isinstance(result_2["contacts"], list)
    
    print("✅ Тест 2 пройден: graceful degradation работает")
    
    print("🎉 Все тесты интеграции пройдены успешно!")

if __name__ == "__main__":
    test_validation_postprocessing_integration()
```

## 📊 Метрики успеха

- ✅ Валидные данные проходят валидацию и постпроцессинг
- ✅ Дублирующиеся организации объединяются
- ✅ Контакты фильтруются по ценности
- ✅ Телефоны и email нормализуются
- ✅ Невалидные данные обрабатываются graceful degradation
- ✅ Ошибки постпроцессинга не ломают пайплайн
- ✅ Производительность остается приемлемой

## 🚀 Запуск теста

```bash
cd /Users/evgenyzach/contact_parser
python tests/test_validation_postprocessing_integration_20250117_1500.py
```

---

**Создан:** 2025-01-17 15:00 (UTC+07)  
**Статус:** Готов к запуску