# 🚨 СРОЧНЫЙ ПЛАН ИСПРАВЛЕНИЙ — 2025-10-16

## 📊 Проблема: Заявленные исправления не работают

**Статус**: 2 из 8 задач работают (25%), 3 регрессии обнаружены

**Критичность**: 🔴 **P0** — Система работает хуже, чем до "исправлений"

---

## 🔥 Критические находки

### 1. **JSON Schema НЕ обновлена для всех полей** 🔴

**Проблема**: 
В отчёте заявлено ✅, но код содержит **только частичные изменения**:

**Что исправлено**:
- ✅ `contacts[].organization_id`: `type: ["integer", "null"]` (строка 713-717)
- ✅ `interactions[].organization_id`: `type: ["integer", "null"]` (строка 954-958)

**Что НЕ исправлено** (❌ **РЕГРЕССИЯ**):
- ❌ `contacts[].contact_id`: `type: "integer"` (строка 702-706) — **НЕ РАЗРЕШАЕТ null!**
- ❌ `interactions[].contact_id`: `type: "integer"` (строка 949-953) — **НЕ РАЗРЕШАЕТ null!**

**Файл**: `/Users/evgenyzach/contact_parser/src/core/validator.py`

**Результат**: 3 новых ошибки валидации в последнем запуске.

---

### 2. **Фильтр excluded вложений НЕ реализован** 🟠

**Проблема**: 
В отчёте заявлено ✅, но код **не содержит проверки статуса**.

**Текущий код** (`api_pipeline_validator.py`, строки 710-724):
```python
def _get_attachment_text(self, attachment, email_data):
    # Проверка на готовый текст
    existing_text = attachment.get("content")
    if existing_text and isinstance(existing_text, str) and existing_text.strip():
        return existing_text

    # ❌ НЕТ ПРОВЕРКИ СТАТУСА!
    file_path = attachment.get("path") or attachment.get("file_path") or attachment.get("relative_path")
    if not file_path:
        print(f"⚠️ У вложения '{attachment.get('filename', 'unknown')}' отсутствует путь к файлу")
        return None
```

**Отсутствует**:
```python
# ✅ ДОЛЖНА БЫТЬ ПРОВЕРКА СТАТУСА ДО получения file_path!
status = attachment.get("status")
if status in ["excluded_by_filter", "excluded_by_size", "unsupported"]:
    return ""  # Тихо пропускаем excluded файлы
```

**Результат**: 73 повторяющихся warnings в каждом запуске.

---

### 3. **DaData ключи не передаются в код** 🟠

**Проблема**: 
В `.env` установлено `DADATA_ENABLED=true` и ключи предоставлены, но код всё равно выдаёт:
```
⚠️  DaData включен, но API ключ не предоставлен
```

**Root cause** (`org_inn_resolver.py`, строки 81-97):
```python
dadata_config = self.config.get('providers', {}).get('dadata', {})

if dadata_config.get('enabled', False):
    api_key = dadata_config.get('api_key')  # ❌ Пустое!
    secret_key = dadata_config.get('secret_key')  # ❌ Пустое!
```

Конфигурация `self.config` не содержит ключи из `.env`.

**Где загружается конфигурация**: Неизвестно, нужна диагностика.

**Результат**: DaData не работает, несмотря на валидные ключи.

---

### 4. **LogAggregator не используется** 🟡

**Проблема**: 
Класс создан (`src/utils/log_aggregator.py`), но **не импортируется** в `api_pipeline_validator.py`.

**Проверка**:
```bash
grep -E "from.*log_aggregator|import.*LogAggregator" src/api_pipeline_validator.py
# Результат: No results found
```

**Результат**: Логи не группируются, 73 повторяющихся warnings.

---

### 5. **ProcessingStatistics не используется** 🟡

**Проблема**: 
Класс создан (`src/core/processing_statistics.py`), но **не импортируется** в `api_pipeline_validator.py`.

**Проверка**:
```bash
grep -E "from.*processing_statistics|import.*ProcessingStatistics" src/api_pipeline_validator.py
# Результат: No results found
```

**Результат**: Детальная статистика не выводится.

---

## 📋 СРОЧНЫЙ ПЛАН ДЕЙСТВИЙ

### 🔴 Приоритет 0: Исправление JSON Schema (1 час)

#### Задача 0.1: Разрешить null для contact_id в contacts

**Файл**: `src/core/validator.py`

**Строки**: 702-706

**Было**:
```python
"contact_id": {
    "type": "integer",
    "minimum": 1,
    "description": "Уникальный ID контакта в рамках письма"
},
```

**Должно быть**:
```python
"contact_id": {
    "type": ["integer", "null"],
    "minimum": 1,
    "description": "Уникальный ID контакта в рамках письма (null если не назначен)"
},
```

**Также обновить** `required` в `_create_contact_schema()` (строка ~695):
```python
"required": [
    "name",  # Только name обязательное!
    "role_in_message",
    "confidence"
],
```

---

#### Задача 0.2: Разрешить null для contact_id в interactions

**Файл**: `src/core/validator.py`

**Строки**: 949-953

**Было**:
```python
"contact_id": {
    "type": "integer",
    "minimum": 1,
    "description": "Ссылка на контакт"
},
```

**Должно быть**:
```python
"contact_id": {
    "type": ["integer", "null"],
    "minimum": 1,
    "description": "Ссылка на контакт (null если контакт не определён)"
},
```

**Также обновить** `required` в `_create_interaction_schema()` (строка ~935):
```python
"required": [
    "interaction_local_id",
    # "contact_id",  # ❌ УБРАТЬ из required!
    "role_in_message",
    "interaction_type",
    "summary",
    "confidence"
],
```

---

#### Задача 0.3: Убрать автокоррекцию contact_id

**Файл**: `src/core/safe_math_utils.py`

**Найти и удалить**:
```python
# Если есть блок вида:
if field == "contact_id" and value is None:
    corrected[field] = 1  # ❌ УДАЛИТЬ ЭТО!
```

**Проверить также** функции:
- `fix_none_values_in_data()`
- `fix_json_schema_validation_errors()`

---

### 🟠 Приоритет 1: Фильтр excluded вложений (20 минут)

**Файл**: `src/api_pipeline_validator.py`

**Строки**: 710-724

**Добавить проверку статуса**:

```python
def _get_attachment_text(self, attachment, email_data):
    """
    🔍 Получение текста вложения (из content, кеша или OCR)
    """
    # 1. Проверка на готовый текст в content
    existing_text = attachment.get("content")
    if existing_text and isinstance(existing_text, str) and existing_text.strip():
        return existing_text

    # 2. ✅ ФИЛЬТР EXCLUDED ВЛОЖЕНИЙ (ДОБАВИТЬ ЭТО!)
    status = attachment.get("status")
    if status in ["excluded_by_filter", "excluded_by_size", "unsupported", "failed"]:
        # Тихо пропускаем excluded файлы без warnings
        return ""

    # 3. Поиск пути к файлу
    file_path = attachment.get("path") or attachment.get("file_path") or attachment.get("relative_path")
    if not file_path:
        # ✅ Теперь это warning только для "saved" файлов без пути
        print(f"⚠️ У вложения '{attachment.get('filename', 'unknown')}' отсутствует путь к файлу")
        return None
    
    # ... остальной код без изменений
```

**Критерий успеха**:
```bash
# После исправления:
grep "отсутствует путь" data/logs/*.log | wc -l
# Ожидается: 0-5 (только реальные проблемы)
```

---

### 🟠 Приоритет 2: DaData конфигурация (ИСПРАВЛЕНО ✅)

#### ✅ Задача 2.1: Root cause найден

**Проблема**: В `config/settings.py` отсутствовал `load_dotenv()`, поэтому `os.getenv('DADATA_API_KEY')` возвращал `None`.

**Цепочка вызовов**:
1. `postprocessor.py:259` → `OrganizationINNResolver()` без параметров
2. `org_inn_resolver.py:49` → `self.config = config or INN_ENRICHMENT_CONFIG`
3. `org_inn_resolver.py:25` → `from config.settings import INN_ENRICHMENT_CONFIG`
4. `config/settings.py:87-88` → `'api_key': os.getenv('DADATA_API_KEY')` ❌ вернул `None`

**Root cause**: `.env` не был загружен до использования `os.getenv()`.

---

#### ✅ Задача 2.2: Исправление применено

**Файл**: `config/settings.py`

**Добавлено** (строки 9-12):
```python
from dotenv import load_dotenv

# 🔐 Загрузка переменных окружения из .env
load_dotenv()
```

**Теперь**:
- `os.getenv('DADATA_API_KEY')` → `'0d49abad18ccd8b891c3cc0247c31fb20ac14db5'` ✅
- `os.getenv('DADATA_SECRET_KEY')` → `'66028a531900322903f4ebdacaa450685e3228b1'` ✅
- `os.getenv('DADATA_ENABLED')` → `'true'` (но не используется, т.к. в settings.py жёстко `'enabled': True`)

**Примечание**: В `settings.py:86` флаг `enabled` жёстко установлен в `True`, что **правильно** для вашего случая.

---

### 🟡 Приоритет 3: Использование LogAggregator (30 минут)

**Файл**: `src/api_pipeline_validator.py`

**Добавить импорт** (в начало файла):
```python
from src.utils.log_aggregator import LogAggregator, aggregate_logs
```

**Использовать в _get_attachment_text()**:

**Вариант A (простой)**: Группировка в конце обработки всех писем
```python
# В методе process_date() или аналогичном
with aggregate_logs(logger) as agg:
    for email in emails:
        # ... обработка письма
        for attachment in email.get("attachments", []):
            text = self._get_attachment_text(attachment, email)
            if text is None:
                agg.add_warning(
                    "missing_file_path",
                    f"У вложения '{attachment.get('filename', 'unknown')}' отсутствует путь"
                )
# Автоматически выведет: "⚠️ missing_file_path: 73 предупреждения"
```

**Вариант B (продвинутый)**: Накопление в классе
```python
# В __init__() класса ApiPipelineValidator:
self.log_aggregator = LogAggregator(logger)

# В _get_attachment_text():
if not file_path:
    self.log_aggregator.add_warning(
        "missing_file_path",
        f"У вложения '{attachment.get('filename', 'unknown')}' отсутствует путь"
    )
    return None

# В конце обработки:
self.log_aggregator.flush()
```

**Критерий успеха**:
```
Вместо:
⚠️ У вложения 'unknown' отсутствует путь к файлу (x73)

Должно быть:
⚠️ missing_file_path: 73 предупреждения
  - У вложения 'unknown' отсутствует путь к файлу (показать 5 первых)
```

---

### 🟡 Приоритет 4: Использование ProcessingStatistics (1 час)

**Файл**: `src/api_pipeline_validator.py`

**Добавить импорт** (в начало файла):
```python
from src.core.processing_statistics import ProcessingStatistics
```

**Использовать в конце обработки**:

```python
def process_date(self, date: str, emails: List[Dict]):
    """Обработка писем за дату"""
    # Инициализация статистики
    stats = ProcessingStatistics()
    
    # ... обработка писем
    for email in emails:
        result = self.process_email(email)
        
        # Обновление статистики
        stats.add_email(success=result['success'])
        if 'organizations' in result:
            for org in result['organizations']:
                stats.add_organization(has_inn=bool(org.get('inn')))
        if 'contacts' in result:
            for contact in result['contacts']:
                stats.add_contact(
                    has_organization=bool(contact.get('organization_id'))
                )
        # ... и т.д.
    
    # ✅ Вывод детальной статистики в конце
    stats.print_summary()
```

**Ожидаемый вывод**:
```
═══════════════════════════════════════════════
📊 ИТОГОВАЯ СТАТИСТИКА ОБРАБОТКИ
═══════════════════════════════════════════════
📧 Письма:           9 / 9 (100%)
👥 Контакты:         18 (17 с орг, 1 без)
🏢 Организации:      8 (2 с ИНН)
📄 КП:               3 (все валидные)
📎 Вложения:         12 (10 OCR успех, 1 ошибка, 1 пропущено)
⏱️  Время:           125.3s (13.9s/письмо)
═══════════════════════════════════════════════
```

---

## ✅ Критерии успеха (после всех исправлений)

### Запустить тест:
```bash
cd /Users/evgenyzach/contact_parser
python -m src.api_pipeline_validator
# Выбрать дату 2025-08-28, обработать все 9 писем
```

### Проверить логи:
```bash
# 1. JSON Schema ошибки (должно быть 0)
grep "JSON Schema валидация не прошла" data/logs/api_pipeline_validator_*.log | tail -20
# Ожидается: НЕТ новых ошибок (только старые из предыдущих запусков)

# 2. Warnings 'unknown' (должно быть 0-5)
grep "отсутствует путь" data/logs/api_pipeline_validator_*.log | tail -20 | wc -l
# Ожидается: 0-5 (только реальные проблемы)

# 3. DaData (должно быть "успешно инициализирован")
grep "DaData" data/logs/api_pipeline_validator_*.log | tail -10
# Ожидается: "✅ DaData provider успешно инициализирован"

# 4. Группировка логов (должна быть сводка)
grep "предупреждения\|warnings" data/logs/api_pipeline_validator_*.log | tail -10
# Ожидается: "⚠️ missing_file_path: X предупреждений"

# 5. Детальная статистика (должна быть таблица)
grep "ИТОГОВАЯ СТАТИСТИКА" data/logs/api_pipeline_validator_*.log
# Ожидается: ASCII таблица с метриками
```

---

## 📊 Сводная таблица исправлений

| # | Задача | Файл | Время | Приоритет | Статус |
|---|--------|------|-------|-----------|--------|
| 0.1 | contact_id null в contacts | `validator.py` | 15 мин | 🔴 P0 | ⏳ TODO |
| 0.2 | contact_id null в interactions | `validator.py` | 15 мин | 🔴 P0 | ⏳ TODO |
| 0.3 | Убрать автокоррекцию contact_id | `safe_math_utils.py` | 15 мин | 🔴 P0 | ⏳ TODO |
| 1 | Фильтр excluded вложений | `api_pipeline_validator.py` | 20 мин | 🟠 P1 | ⏳ TODO |
| ~~2.1~~ | ~~Диагностика DaData config~~ | ~~Разные файлы~~ | ~~15 мин~~ | ~~🟠 P1~~ | ✅ **ГОТОВО** |
| ~~2.2~~ | ~~Исправить передачу ключей~~ | `config/settings.py` | ~~15 мин~~ | ~~🟠 P1~~ | ✅ **ГОТОВО** |
| 3 | Использовать LogAggregator | `api_pipeline_validator.py` | 30 мин | 🟡 P2 | ⏳ TODO |
| 4 | Использовать ProcessingStatistics | `api_pipeline_validator.py` | 1 час | 🟡 P2 | ⏳ TODO |

**Общее время**: 
- 🔴 P0: 45 минут (критично)
- 🟠 P1: ~~50 минут~~ → **20 минут** (важно, DaData уже исправлен)
- 🟡 P2: 1.5 часа (опционально)

**Итого**: ~~2.5-3 часа~~ → **2 часа для всех исправлений** (с учётом DaData fix)

---

## 🚨 ВАЖНО

**Проблема не в промпте v1.2** (он работает корректно) и **не в OCR кеше** (он работает отлично).

**Проблема в неполной реализации**:
1. JSON Schema обновлена частично (2 из 4 полей)
2. Фильтр excluded вообще не добавлен в код
3. LogAggregator и ProcessingStatistics не используются
4. DaData конфигурация не подключена к .env

**Рекомендация**: 
1. **Сначала исправить P0** (45 мин) → устранить регрессию
2. **Затем P1** (50 мин) → очистить логи и настроить DaData
3. **P2 опционально** (1.5 часа) → улучшить UX

---

**Дата создания**: 2025-10-16 16:00  
**Аналитик**: Cascade AI  
**Статус**: ⏳ Готов к реализации
