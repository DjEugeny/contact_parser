# Технические детали проблем

## 1. Детальный анализ ошибок валидации JSON Schema

### Паттерны ошибок

#### Тип 1: None вместо integer для связей
```python
# Ошибка
"contact_id": None  # в interactions
"organization_id": None  # в contacts

# Ожидается
"contact_id": 1
"organization_id": 1
```

**Затронутые письма:** email_002, email_017, email_018, email_019

**Автокоррекция:**
```python
# Система автоматически устанавливает значение по умолчанию
if contact_id is None:
    contact_id = 1  # первый контакт по умолчанию
```

**Проблема:** Это может привести к неправильным связям между сущностями.

---

#### Тип 2: Недопустимые значения enum
```python
# Ошибка
"interaction_type": "info_request"

# Допустимые значения
['requested_quote', 'sent_quote', 'follow_up', 'clarification', 
 'complaint', 'invoice_sent', 'invoice_paid', 'contract_sent', 
 'contract_signed', 'delivery', 'support', 'other']
```

**Затронутые письма:** email_008, email_019

**Автокоррекция:**
```python
# Система маппит на ближайшее допустимое значение
"info_request" -> "clarification"  # или "other"
```

---

#### Тип 3: None вместо string
```python
# Ошибка в email_015
field: None

# Ожидается
field: ""  # пустая строка или валидное значение
```

---

### Рекомендации по улучшению промпта

```markdown
ВАЖНО: Строгие требования к JSON:

1. НИКОГДА не используйте null/None для обязательных полей:
   - contact_id: ВСЕГДА целое число (1, 2, 3...)
   - organization_id: ВСЕГДА целое число (1, 2, 3...)
   - Если значение неизвестно, используйте 1 (первая организация/контакт)

2. interaction_type ДОЛЖЕН быть ТОЛЬКО одним из:
   - 'requested_quote' - запрос коммерческого предложения
   - 'sent_quote' - отправка КП
   - 'follow_up' - последующий контакт
   - 'clarification' - уточнение деталей
   - 'complaint' - жалоба
   - 'invoice_sent' - отправка счёта
   - 'invoice_paid' - оплата счёта
   - 'contract_sent' - отправка договора
   - 'contract_signed' - подписание договора
   - 'delivery' - доставка
   - 'support' - техподдержка
   - 'other' - прочее (если не подходит ни один вариант)

3. Для строковых полей используйте "" вместо null

ПРИМЕРЫ ПРАВИЛЬНОГО JSON:
[Добавить 2-3 полных примера]
```

---

## 2. Анализ ошибки LocationEnrichmentMetadata

### Структура проблемы

```python
# Где возникает
Ошибка обогащения организации 1: 'LocationEnrichmentMetadata' object has no attribute 'get'

# Затем при сериализации
Object of type LocationEnrichmentMetadata is not JSON serializable
```

### Возможные причины

1. **LocationEnrichmentMetadata - это класс/dataclass:**
```python
@dataclass
class LocationEnrichmentMetadata:
    source: str
    confidence: float
    method: str
    # ...
```

2. **Объект добавляется напрямую в dict:**
```python
# Неправильно
organization["enrichment_metadata"] = LocationEnrichmentMetadata(...)

# Правильно
organization["enrichment_metadata"] = asdict(LocationEnrichmentMetadata(...))
```

### Решение

```python
# Вариант 1: Custom JSON Encoder
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, LocationEnrichmentMetadata):
            return obj.__dict__  # или asdict(obj)
        return super().default(obj)

# Использование
json.dumps(data, cls=CustomJSONEncoder)

# Вариант 2: Pydantic
class LocationEnrichmentMetadata(BaseModel):
    source: str
    confidence: float
    method: str
    
    class Config:
        json_encoders = {...}

# Использование
metadata.model_dump()  # или .dict() для старых версий

# Вариант 3: Преобразование перед сериализацией
def prepare_for_json(obj):
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    elif hasattr(obj, 'dict'):
        return obj.dict()
    return obj
```

---

## 3. Анализ неэффективной логики OCR

### Текущая архитектура (ПРОБЛЕМНАЯ)

```python
# Pipeline
def process_email(email_data):
    for attachment in email_data['attachments']:
        # Сразу запускает OCR модуль
        text = ocr_module.extract_text(attachment['path'])  # ❌
        
# OCR Module
def extract_text(filepath):
    # Полная инициализация каждый раз
    self._init_vision_client()
    self._load_cache()
    self._scan_results_dir()
    
    # Только здесь проверяет кэш
    if self._is_cached(filepath):
        return self._load_from_cache(filepath)  # ⏭️ Пропускаю
    
    # Фактическая обработка
    return self._do_ocr(filepath)
```

**Проблемы:**
1. OCR модуль инициализируется для каждого вложения
2. Проверка кэша происходит ВНУТРИ OCR модуля
3. Избыточное сканирование папок и загрузка конфигурации
4. Засорение логов

### Правильная архитектура

```python
# Pipeline с OCRCacheManager
class EmailProcessor:
    def __init__(self):
        self.ocr_cache = OCRCacheManager()
        self.ocr_module = None  # Ленивая инициализация
    
    def process_email(self, email_data):
        attachments = email_data['attachments']
        
        # Фаза 1: Batch-проверка кэша (быстро)
        cache_results = self.ocr_cache.check_batch([a['filename'] for a in attachments])
        
        texts = []
        to_process = []
        
        for attachment in attachments:
            cached_text = cache_results.get(attachment['filename'])
            if cached_text:
                logger.info(f"✅ OCR кэш: {attachment['filename']}")
                texts.append(cached_text)
            else:
                to_process.append(attachment)
        
        # Фаза 2: Обработка только необработанных (если есть)
        if to_process:
            if self.ocr_module is None:
                self.ocr_module = OCRModule()  # Инициализация только при необходимости
            
            for attachment in to_process:
                text = self.ocr_module.extract_text(attachment['path'])
                texts.append(text)
        
        return texts

# OCRCacheManager
class OCRCacheManager:
    def __init__(self, results_dir="data/final_results"):
        self.results_dir = Path(results_dir)
        self._cache = {}  # In-memory кэш для быстрого доступа
    
    def check_batch(self, filenames: List[str]) -> Dict[str, Optional[str]]:
        """Batch-проверка кэша для нескольких файлов"""
        results = {}
        for filename in filenames:
            results[filename] = self.get_cached_result(filename)
        return results
    
    def get_cached_result(self, filename: str) -> Optional[str]:
        """Получить результат из кэша"""
        # Проверяем in-memory кэш
        if filename in self._cache:
            return self._cache[filename]
        
        # Проверяем файловый кэш
        result_file = self.results_dir / f"{filename}.json"
        if result_file.exists():
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    text = data.get('extracted_text', '')
                    self._cache[filename] = text  # Кэшируем в памяти
                    return text
            except Exception as e:
                logger.warning(f"Ошибка чтения кэша: {e}")
        
        return None

# Упрощённый OCR Module (без проверок кэша)
class OCRModule:
    def __init__(self):
        self.vision_client = None
        logger.info("OCR модуль инициализирован")
    
    def extract_text(self, filepath: str) -> str:
        """Извлечь текст (без проверки кэша)"""
        logger.info(f"🔍 OCR обработка: {Path(filepath).name}")
        
        if self.vision_client is None:
            self.vision_client = self._init_vision_client()
        
        text = self._do_ocr(filepath)
        self._save_result(filepath, text)
        
        logger.info(f"✅ Извлечено {len(text)} символов")
        return text
```

### Сравнение производительности

| Метрика | Текущий подход | Оптимизированный | Улучшение |
|---------|----------------|------------------|-----------|
| Инициализаций OCR | 12 | 0 | 100% |
| Проверок кэша | 12 (медленных) | 12 (быстрых) | ~10x |
| Время на проверки | ~20-30 сек | ~0.5-1 сек | ~30x |
| Строк в логах | ~100 | ~12 | ~8x |

### Логи: До и После

**До (текущий):**
```
📎 Попытка извлечения текста из вложения: unknown
   Путь к файлу: data/attachments/...
   Файл существует: True
   🔍 Запуск OCR для файла: ...
2025-10-06 20:39:43 | ERROR | ❌ Ошибка загрузки кэша PDF анализа
📋 ВОЗМОЖНОСТИ СИСТЕМЫ:
   ☁️ Google Cloud Vision: ✅ Доступен
   📄 Локальные форматы: PDF ✅ | DOCX ✅ | XLSX ✅
======================================================================
🎯 OCR ТЕСТЕР С GOOGLE CLOUD VISION v13 🎯
📁 Исходные файлы: data/attachments
🗂️  Результаты в папке: data/final_results
💾 Кэш PDF анализа: data/cache/pdf_analysis
======================================================================
   ⏭️ Вложение ... уже обработано. Пропускаю.
   ✅ OCR успешно: извлечено 1387 символов
```

**После (оптимизированный):**
```
📎 Вложение: document.pdf
✅ OCR кэш: извлечено 1387 символов
```

### Дополнительные оптимизации

#### 1. Предварительная проверка перед обработкой письма
```python
def precheck_attachments(self, email_data: dict) -> dict:
    """Статистика по вложениям"""
    attachments = email_data.get('attachments', [])
    cache_results = self.ocr_cache.check_batch([a['filename'] for a in attachments])
    
    stats = {
        'total': len(attachments),
        'cached': sum(1 for v in cache_results.values() if v),
        'to_process': sum(1 for v in cache_results.values() if not v),
        'missing_path': sum(1 for a in attachments if not a.get('path'))
    }
    
    logger.info(f"📎 Вложений: {stats['total']} | Кэш: {stats['cached']} | Обработать: {stats['to_process']}")
    return stats
```

#### 2. Warm-up кэша при старте
```python
def warmup_cache(self):
    """Предзагрузка кэша в память при старте"""
    logger.info("🔥 Прогрев OCR кэша...")
    count = 0
    for result_file in self.results_dir.glob("*.json"):
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
                filename = result_file.stem
                self._cache[filename] = data.get('extracted_text', '')
                count += 1
        except Exception:
            pass
    logger.info(f"✅ Загружено {count} результатов OCR в кэш")
```

---

## 4. Анализ проблемы с вложениями

### Структура данных вложений

```json
{
  "attachments": [
    {
      "filename": "unknown",
      "path": null,  // ← ПРОБЛЕМА
      "content_type": "application/pdf",
      "size": 12345
    }
  ]
}
```

### Где должен быть путь

```json
{
  "attachments": [
    {
      "filename": "document.pdf",
      "path": "data/attachments/2025-07-29/20250729_dna-technology_ru_6e851453_234744_attach_document.pdf",
      "content_type": "application/pdf",
      "size": 12345
    }
  ]
}
```

### Проверка в коде парсера

```python
# Добавить валидацию
def validate_attachment(attachment):
    if not attachment.get('path'):
        logger.warning(f"Attachment {attachment.get('filename')} has no path")
        # Попытка восстановить путь
        if attachment.get('filename'):
            attachment['path'] = reconstruct_path(attachment['filename'])
    
    # Проверить существование файла
    if attachment['path'] and not os.path.exists(attachment['path']):
        logger.error(f"Attachment file not found: {attachment['path']}")
        attachment['path'] = None
    
    return attachment
```

---

## 5. Анализ таймаутов LLM

### Статистика времени ответа

```
Письмо 1:  47.55 сек ✅
Письмо 2:  35.14 сек ✅
Письмо 3:  95.52 сек ✅
Письмо 4: 119.71 сек ⚠️ (с OCR)
...
Письмо 17: 348.16 сек ❌ (2 неудачные попытки + успех)
  - Попытка 1: TypeError
  - Попытка 2: Timeout (>120 сек)
  - Попытка 3: Успех
```

### Факторы, влияющие на время

1. **Размер текста письма**
2. **Наличие OCR вложений** (добавляет 1000-4000 символов)
3. **Количество контактов/организаций** (сложность ответа)
4. **Нагрузка на API провайдера**

### Рекомендации

```python
# Динамический таймаут
def calculate_timeout(email_data):
    base_timeout = 60
    text_length = len(email_data.get('text', ''))
    attachments_count = len(email_data.get('attachments', []))
    
    # +1 сек на каждые 100 символов
    timeout = base_timeout + (text_length // 100)
    
    # +30 сек на каждое вложение с OCR
    timeout += attachments_count * 30
    
    # Максимум 300 сек (5 минут)
    return min(timeout, 300)

# Стратегия повторов
retry_strategy = {
    'max_attempts': 3,
    'backoff_factor': 2,  # 2, 4, 8 секунд
    'timeout_multiplier': 1.5  # увеличивать таймаут на 50% при повторе
}
```

---

## 6. Структура данных для отладки

### Что сохранять для анализа ошибок

```python
error_debug_data = {
    "timestamp": "2025-10-06T21:22:42",
    "email_file": "email_035_...",
    "error_type": "UnknownError",
    "error_message": "...",
    "traceback": "...",
    "input_data": {
        "text_length": 1234,
        "attachments_count": 2,
        "has_ocr": True
    },
    "llm_request": {
        "provider": "OpenRouter",
        "model": "deepseek/deepseek-chat-v3.1:free",
        "prompt_length": 5678,
        "timeout": 120
    },
    "llm_response": {
        "status_code": 200,
        "response_length": 2345,
        "processing_time": 45.6,
        "raw_response": "..." # первые 1000 символов
    },
    "validation_errors": [
        {
            "field": "contact.organization_id",
            "error": "None is not of type 'integer'",
            "auto_corrected": True,
            "correction": "Set to 1"
        }
    ]
}
```

---

## 7. Метрики для мониторинга

### Ключевые метрики

```python
metrics = {
    # Производительность
    "processing_time_avg": 90.0,
    "processing_time_p95": 120.0,
    "processing_time_p99": 200.0,
    
    # Качество
    "success_rate": 0.967,
    "validation_error_rate": 0.20,
    "auto_correction_rate": 0.20,
    "complete_failure_rate": 0.033,
    
    # LLM
    "llm_timeout_rate": 0.033,
    "llm_retry_rate": 0.033,
    "llm_avg_response_time": 75.0,
    
    # Данные
    "avg_contacts_per_email": 2.8,
    "avg_organizations_per_email": 2.37,
    "ocr_usage_rate": 0.40,
    
    # Ошибки
    "serialization_errors": 1,
    "missing_attachment_paths": 15,
    "cache_errors": 1
}
```

### Алерты

```python
alerts = {
    "critical": {
        "success_rate < 0.95": "Критическое падение успешности",
        "complete_failure_rate > 0.05": "Слишком много полных отказов"
    },
    "warning": {
        "validation_error_rate > 0.30": "Высокий процент ошибок валидации",
        "llm_timeout_rate > 0.10": "Частые таймауты LLM",
        "processing_time_p95 > 180": "Медленная обработка"
    }
}
```

---

## 8. План тестирования исправлений

### Unit тесты

```python
def test_location_enrichment_serialization():
    """Тест сериализации LocationEnrichmentMetadata"""
    metadata = LocationEnrichmentMetadata(
        source="attachment",
        confidence=0.9,
        method="ocr"
    )
    
    # Должно сериализоваться без ошибок
    json_str = json.dumps({"metadata": metadata}, cls=CustomJSONEncoder)
    assert json_str is not None
    
    # Должно десериализоваться обратно
    data = json.loads(json_str)
    assert data["metadata"]["source"] == "attachment"

def test_json_schema_validation_with_none():
    """Тест автокоррекции None значений"""
    invalid_data = {
        "contact_id": None,
        "organization_id": None
    }
    
    corrected = auto_correct_schema_errors(invalid_data)
    assert corrected["contact_id"] == 1
    assert corrected["organization_id"] == 1

def test_attachment_path_reconstruction():
    """Тест восстановления путей к вложениям"""
    attachment = {
        "filename": "document.pdf",
        "path": None
    }
    
    fixed = fix_attachment_path(attachment, email_id="email_001")
    assert fixed["path"] is not None
    assert "document.pdf" in fixed["path"]
```

### Integration тесты

```python
def test_full_pipeline_with_problematic_email():
    """Тест обработки проблемного письма"""
    # Использовать email_035 как тестовый случай
    result = process_email("email_035_20250729_20250729_yandex_ru_f37d60ba.json")
    
    assert result["success"] == True
    assert "error" not in result
    assert len(result["contacts"]) > 0

def test_llm_timeout_handling():
    """Тест обработки таймаутов"""
    with mock.patch('llm_provider.request', side_effect=TimeoutError):
        result = process_email_with_retry("test_email.json")
        
        # Должно быть несколько попыток
        assert result["attempts"] > 1
        # В итоге должно либо успешно обработаться, либо корректно упасть
        assert result["status"] in ["success", "failed"]
```

---

## 9. Чеклист перед деплоем исправлений

- [ ] Все unit тесты проходят
- [ ] Integration тесты проходят
- [ ] email_035 успешно обрабатывается
- [ ] Ошибки валидации снизились до <5%
- [ ] LocationEnrichmentMetadata корректно сериализуется
- [ ] Пути к вложениям восстанавливаются
- [ ] Таймауты настроены динамически
- [ ] Добавлено детальное логирование ошибок
- [ ] Метрики и алерты настроены
- [ ] Документация обновлена
- [ ] Проведён smoke test на 100 письмах
- [ ] Проведён load test на 1000 письмах

---

**Последнее обновление:** 2025-10-06
