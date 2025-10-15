# 🔍 Отчёт по аудиту: Использование email_data.get("body")

**Дата:** 2025-10-15 23:15 UTC+07:00  
**Задача:** 2.1 из tasks.md  
**Статус:** ✅ ЗАВЕРШЁН

---

## 📊 Сводка

**Найдено файлов с устаревшим доступом:** 3  
**Приоритет исправления:**
- 🔴 Высокий: 2 файла
- 🟡 Средний: 1 файл (уже исправлен правильно)

---

## 📁 Найденные файлы

### ✅ 1. `src/utils/file_tokens.py` (УЖЕ ПРАВИЛЬНО)

**Строки:** 206-217  
**Метод:** `_extract_email_body()`  
**Статус:** ✅ **УЖЕ ИСПОЛЬЗУЕТ FALLBACK ЛОГИКУ**

**Код:**
```python
def _extract_email_body(self, email_data: Dict[str, Any]) -> str:
    """📝 Извлекает тело письма с учётом возможных вариантов полей."""
    body_candidates = [
        email_data.get("body"),
        email_data.get("body_clean"),
        email_data.get("body_plain"),
        email_data.get("body_text"),
        email_data.get("text"),
        email_data.get("body_raw"),
    ]
    
    for candidate in body_candidates:
        if candidate and isinstance(candidate, str) and candidate.strip():
            return candidate
    return ""
```

**Оценка:** ✅ **НЕ ТРЕБУЕТ ИСПРАВЛЕНИЯ** - уже реализована правильная fallback логика.

---

### 🔴 2. `src/postprocessing/org_email_enricher.py` (ТРЕБУЕТ ИСПРАВЛЕНИЯ)

**Строки:** 193-194  
**Метод:** `_extract_emails_from_signature()`  
**Приоритет:** 🔴 **ВЫСОКИЙ**

**Проблемный код:**
```python
# Ищем в body и plain_text
text_sources = []
if email_data.get('body'):              # ❌ Только legacy поле
    text_sources.append(email_data['body'])
if email_data.get('plain_text'):
    text_sources.append(email_data['plain_text'])
```

**Проблема:**
- Ищет только `'body'` (legacy формат)
- Не поддерживает `'body_clean'` и `'body_raw'` (NEW формат)
- Может пропустить данные из новых писем

**Влияние:**
- Модуль: Обогащение организаций email-адресами
- Критичность: ВЫСОКАЯ (потеря email-адресов из подписей)

**Рекомендуемое исправление:**
```python
# ✅ ИСПРАВЛЕНИЕ: Поддержка всех форматов
text_sources = []

# Извлекаем body с fallback логикой
body_candidates = [
    email_data.get('body'),
    email_data.get('body_clean'),
    email_data.get('body_raw'),
]
for body in body_candidates:
    if body and isinstance(body, str) and body.strip():
        text_sources.append(body)
        break

# Добавляем plain_text если есть
if email_data.get('plain_text'):
    text_sources.append(email_data['plain_text'])
```

---

### 🔴 3. `src/core/contact_enricher.py` (ТРЕБУЕТ ИСПРАВЛЕНИЯ)

**Строки:** 301-302  
**Метод:** `_extract_website_from_email()`  
**Приоритет:** 🔴 **ВЫСОКИЙ**

**Проблемный код:**
```python
# 1. Извлечение из тела письма
if email_data and email_data.get('body'):     # ❌ Только legacy поле
    websites = self.website_extractor.extract_from_email_body(email_data['body'])
    if websites:
        return websites[0]  # Возвращаем самый уверенный
```

**Проблема:**
- Ищет только `'body'` (legacy формат)
- Не поддерживает `'body_clean'` и `'body_raw'` (NEW формат)
- Может пропустить сайты из новых писем

**Влияние:**
- Модуль: Обогащение контактов сайтами
- Критичность: ВЫСОКАЯ (потеря информации о сайтах)

**Рекомендуемое исправление:**
```python
# ✅ ИСПРАВЛЕНИЕ: Поддержка всех форматов
if email_data:
    # Извлекаем body с fallback логикой
    body_candidates = [
        email_data.get('body'),
        email_data.get('body_clean'),
        email_data.get('body_raw'),
    ]
    
    for body in body_candidates:
        if body and isinstance(body, str) and body.strip():
            websites = self.website_extractor.extract_from_email_body(body)
            if websites:
                return websites[0]
            break
```

---

### ✅ 4. `src/api_pipeline_validator.py` (УЖЕ ИСПРАВЛЕН)

**Строки:** 674-691  
**Метод:** `_compose_combined_text()`  
**Статус:** ✅ **УЖЕ ИСПРАВЛЕН В ФАЗЕ 1**

**Код:**
```python
body_candidates = [
    email_data.get("body"),          # legacy
    email_data.get("body_clean"),    # NEW (приоритет)
    email_data.get("body_raw"),      # NEW (fallback)
    email_data.get("body_plain"),
    email_data.get("body_text"),
    email_data.get("text"),
]
```

**Оценка:** ✅ **УЖЕ ИСПРАВЛЕН** - fallback логика реализована.

---

## 📋 Приоритизация исправлений

### 🔴 Высокий приоритет (требуют немедленного исправления)

1. **`src/postprocessing/org_email_enricher.py`**
   - Метод: `_extract_emails_from_signature()`
   - Строки: 193-194
   - Влияние: Потеря email-адресов из подписей

2. **`src/core/contact_enricher.py`**
   - Метод: `_extract_website_from_email()`
   - Строки: 301-302
   - Влияние: Потеря информации о сайтах

### ✅ Уже исправлены / не требуют исправления

3. **`src/api_pipeline_validator.py`** ✅
   - Исправлен в Фазе 1

4. **`src/utils/file_tokens.py`** ✅
   - Уже использует правильную логику

---

## 🎯 План исправлений

### Вариант 1: Прямое исправление (быстро)

Исправить каждый файл напрямую, добавив fallback логику.

**Преимущества:**
- Быстро (15-20 минут)
- Минимальные изменения

**Недостатки:**
- Дублирование кода
- Сложнее поддерживать

### Вариант 2: Централизованная утилита (рекомендуется)

1. Создать `src/utils/email_body_extractor.py`
2. Вынести fallback логику в функцию
3. Использовать во всех модулях

**Преимущества:**
- Единая точка изменений
- Легче поддерживать
- Консистентность

**Недостатки:**
- Требует больше времени (1 час)
- Больше изменений в коде

---

## 📊 Статистика

**Всего файлов проверено:** ~50 Python файлов в `src/`  
**Найдено с прямым доступом к "body":** 4 файла  
**Требуют исправления:** 2 файла  
**Уже исправлены/правильные:** 2 файла

**Покрытие проблемы:** 50% (2 из 4 уже исправлены)

---

## ✅ Рекомендации

### Немедленно (P1)

1. ✅ Создать централизованную утилиту `email_body_extractor.py`
2. ✅ Исправить `org_email_enricher.py`
3. ✅ Исправить `contact_enricher.py`
4. ✅ Добавить unit-тесты

### В ближайшее время (P2)

5. Провести повторный аудит после исправлений
6. Добавить линтер-правило для предотвращения прямого доступа
7. Обновить документацию для разработчиков

---

## 🔗 Связанные файлы

- **План задач:** `tasks.md`
- **Анализ проблемы:** `README.md`
- **Changelog:** `CHANGELOG.md`

---

**Статус:** ✅ **АУДИТ ЗАВЕРШЁН**  
**Следующий шаг:** Задача 2.2 - Создание централизованной утилиты
