# Tasks: PLAN-005 Phone Extension Normalization

## Обзор
Чек-лист задач по реализации нормализации телефонов с добавочными номерами согласно PLAN-005.

**Статус**: 🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА (P0)
**Дата создания**: 2025-10-02

---

## 📋 Список задач

### 1. Анализ и спецификация ✅
- [x] Анализ проблемы (email_014, email_015 падают с `non-unique elements`)
- [x] Создание PLAN-005_Phone_Extension_Normalization.md
- [x] Создание requirements.md
- [x] Создание design.md (текущая и целевая архитектура)
- [x] Определение scope и зависимостей

### 2. Обновление JSON Schema в validator.py ⏳
- [ ] Изменить схему organizations.phones (строки 620-686)
- [ ] Изменить схему contacts.phones (строка 730)
- [ ] Добавить определение `phone_object` в definitions
- [ ] Убрать `uniqueItems: true` из phones (дедуп в PostProcessor)
- [ ] Добавить backward compatibility для строк

### 3. Исправление PhoneNormalizer ⏳
- [ ] Добавить метод `normalize_phone_to_object(phone_str: str) -> List[Dict]`
- [ ] Добавить метод `_extract_extension_new(phone: str) -> Tuple[str, Optional[str]]`
- [ ] Добавить метод `_split_compound_phones(phone: str, extension: str) -> List[str]`
- [ ] Добавить метод `_normalize_to_e164(phone: str) -> Tuple[str, str, str]`
- [ ] УДАЛИТЬ добавление extension в `formatted` в `normalize_contact_phone()`
- [ ] Поддержка всех форматов добавочных (доб., ext, x, вн. и т.д.)

### 4. Обновление LLM Prompt ⏳
- [ ] Добавить инструкции в `prompts/unified_contact_extraction_structured.txt`
- [ ] Запрет на включение добавочных в поле `number`
- [ ] Инструкции по парсингу множественных номеров `(48)`
- [ ] Примеры правильных и неправильных телефонов

### 5. Интеграция в PostProcessor ⏳
- [ ] Добавить метод `_normalize_all_phones()` в `postprocessor.py`
- [ ] Добавить метод `_deduplicate_phones()` для дедуп по `(normalized, extension, type)`
- [ ] Вызов нормализации после `_cleanup_organization_emails`
- [ ] Сбор статистики в `postprocessing_metadata.phone_normalization`
- [ ] Обработка ошибок с graceful degradation

### 6. Написание тестов ⏳
- [ ] Unit-тесты в `tests/test_phone_normalizer.py`
  - [ ] Тест парсинга добавочных
  - [ ] Тест множественных номеров
  - [ ] Тест E.164 нормализации
  - [ ] Тест дедупликации
- [ ] Интеграционные тесты в `tests/integration/test_email_014_015.py`
  - [ ] Тест обработки email_014 и email_015
  - [ ] Проверка структуры phones (объекты, extension отдельно)
  - [ ] Проверка отсутствия дубликатов

### 7. Интеграционное тестирование ⏳
- [ ] Запуск на email_014 и email_015
- [ ] Проверка отсутствия ошибок `non-unique elements`
- [ ] Валидация структуры данных
- [ ] Regression тестирование на всех письмах 2025-07-29
- [ ] Проверка метаданных `phone_normalization`

### 8. Создание отчёта ⏳
- [ ] Создать отчёт в `contact_parser/memory-bank/reports/`
- [ ] Документировать результаты тестирования
- [ ] Описать изменения в коде
- [ ] Зафиксировать метрики качества

---

## 📊 Метрики успеха

### Функциональные
- ✅ email_014 и email_015 обрабатываются без ошибок
- ✅ `phones` как массив объектов с полями `{type, number, normalized, original, extension}`
- ✅ `number` никогда не содержит добавочный
- ✅ `extension` только цифры или null
- ✅ Дедупликация по правильному ключу

### Качественные
- ✅ Валидация JSON Schema проходит
- ✅ Метаданные содержат статистику нормализации
- ✅ Backward compatibility с legacy данными
- ✅ Производительность не ухудшилась

---

## 🔗 Связи с другими задачами

### Upstream (блокирующие)
- ✅ PLAN-001: Email Classifier
- ✅ PLAN-004: Phone Ownership Disambiguation

### Downstream (зависят от этой)
- ⏸️ Global ID Registry (использует normalized)
- ⏸️ Database persistence (схема БД)
- ⏸️ Frontend UI (отображение телефонов)

---

## ⚠️ Риски и митигация

### Риски
- **Миграция данных**: Старые файлы с телефонами-строками
- **LLM compatibility**: Модель может вернуть строки вместо объектов
- **Performance**: Нормализация может замедлить обработку

### Митигация
- **Backward compatibility**: Автоконвертация строк в объекты
- **Graceful degradation**: Fallback для ошибок нормализации
- **Testing**: Полное покрытие edge cases

---

## 📝 Заметки

- **Приоритет**: P0 - блокирует обработку email_014 и email_015
- **Владелец**: AI Assistant
- **Ревьюер**: User
- **Дедлайн**: До релиза v1.1.0