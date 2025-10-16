# 🔬 ROOT CAUSE ANALYSIS — API Pipeline Validator (Часть 2/2)
## План имплементации исправлений

---

## 🎯 ПОШАГОВЫЙ ПЛАН ИСПРАВЛЕНИЙ

### Этап 1: Быстрые wins (1.5 часа)

#### ✅ Задача 1.1: Исправить OCR кеш (1 час)

**Файл**: `src/core/ocr_cache_manager.py`

**Изменения**:
```python
def get_cached_result(self, filename: str, date: str) -> Optional[str]:
    """
    Поиск по оригинальному имени файла (суффикс после 'attach_')
    
    Было: 20250827_20081ed0_attach_file.pdf
    Ищем: *_attach_file.txt
    """
    self.stats['total_checks'] += 1
    
    # In-memory кеш
    cache_key = f"{date}:{filename}"
    if cache_key in self._cache:
        self.stats['cache_hits'] += 1
        return self._cache[cache_key]
    
    date_folder = self.results_dir / date
    if not date_folder.exists():
        self.stats['cache_misses'] += 1
        return None
    
    # Извлекаем оригинальное имя
    if '_attach_' in filename:
        original_name = filename.split('_attach_', 1)[1]
        original_name = original_name.rsplit('.', 1)[0]
    else:
        original_name = filename.rsplit('.', 1)[0]
    
    # Поиск по glob паттерну
    pattern = f"*_attach_{original_name}.txt"
    
    for txt_file in date_folder.glob(pattern):
        text = self._read_text_file(txt_file)
        if text:
            self._cache[cache_key] = text
            self.stats['cache_hits'] += 1
            self.logger.info(f"✅ OCR кеш найден: {txt_file.name} (для {filename})")
            return text
    
    self.stats['cache_misses'] += 1
    return None
```

**Тест**:
```bash
cd /Users/evgenyzach/contact_parser
python -c "
from src.core.ocr_cache_manager import OCRCacheManager
cache = OCRCacheManager()

# Тест с разными хешами
result = cache.get_cached_result(
    '20250827_20081ed0_005329_963544_attach_Ком.пред.27.08.2025 для Томск АССА....pdf',
    '2025-08-27'
)
print(f'✅ Найдено: {len(result)} символов' if result else '❌ Не найдено')
"
```

**Ожидаемый результат**: `✅ Найдено: 2707 символов`

---

#### ✅ Задача 1.2: Фильтровать excluded вложения (30 мин)

**Файл**: `src/api_pipeline_validator.py`

**Изменения**:

1. Метод `_compose_combined_text` (строка 667):
```python
def _compose_combined_text(self, email_data: Dict[str, Any], date: str) -> str:
    """📝 Собирает текст письма и извлечённые файлы вложений."""
    parts: List[str] = []
    
    # Извлечение body
    from src.utils.email_body_extractor import extract_body_with_fallback
    body, body_source = extract_body_with_fallback(
        email_data, prefer_clean=True, return_source=True
    )
    
    if body:
        parts.append(f"=== ТЕКСТ ПИСЬМА ===\n{body}")
    else:
        print(f"⚠️ Тело письма не найдено")

    attachments = email_data.get("attachments", [])
    if not attachments:
        return "\n\n".join(parts)
    
    # ✅ ФИЛЬТР: только сохранённые вложения
    saved_attachments = [
        att for att in attachments
        if att.get("status") == "saved" and att.get("file_path")
    ]
    
    if saved_attachments:
        print(f"📎 Обрабатываем {len(saved_attachments)} сохранённых вложений (всего: {len(attachments)})")
    else:
        print(f"📎 Нет сохранённых вложений (всего: {len(attachments)}, все excluded/unsupported)")
        return "\n\n".join(parts)

    for index, attachment in enumerate(saved_attachments, start=1):
        attachment_text = self._get_attachment_text(email_data, attachment, date)
        if attachment_text:
            name = attachment.get("original_filename") or attachment.get("saved_filename") or f"attachment_{index}"
            parts.append(f"\n=== ВЛОЖЕНИЕ {index}: {name} ===\n{attachment_text}")

    return "\n\n".join(parts)
```

2. Метод `_get_attachment_text` (строка 703):
```python
def _get_attachment_text(self, email: Dict[str, Any], attachment: Dict[str, Any], date: str) -> Optional[str]:
    """📎 Извлекает текст вложения, используя готовый OCR или fallback."""
    
    # ✅ ПРОВЕРКА статуса (на всякий случай)
    status = attachment.get("status")
    if status != "saved":
        self.logger.debug(f"Вложение {attachment.get('original_filename')} имеет статус {status}, пропускаем")
        return None
    
    # Проверяем content в JSON
    existing_text = attachment.get("content")
    if existing_text and isinstance(existing_text, str) and existing_text.strip():
        return existing_text

    # Получаем путь к файлу
    attachment_path = self.portable_paths.normalize_attachment_path(attachment)
    if not attachment_path:
        print(f"⚠️ У вложения '{attachment.get('original_filename', 'unknown')}' отсутствует путь к файлу")
        return None
    
    if not attachment_path.exists():
        recovered_path = self.loader.get_attachment_file_path(email, attachment)
        attachment_path = recovered_path if recovered_path else attachment_path

    # Проверяем OCR кеш
    filename = attachment_path.name
    cached_text = self.ocr_cache.get_cached_result(filename, date)
    
    if cached_text:
        print(f"✅ OCR кеш: {filename} ({len(cached_text)} символов)")
        return cached_text
    
    # OCR модуль (только если нет кеша)
    print(f"📎 OCR кеш промах для {filename}, запускаем обработку")
    # ... остальная логика OCR ...
```

**Тест**:
```bash
python -m src.api_pipeline_validator --mode=batch --date=2025-08-27 --count=1 --dry-run
```

**Ожидаемый результат**: Нет сообщений `⚠️ У вложения 'unknown' отсутствует путь`

---

### Этап 2: Исправление organization_id (2-3 часа)

#### ✅ Задача 2.1: Обновить JSON Schema (30 мин)

**Файл**: `src/core/validator.py` (или где хранится schema)

**Изменения**:
```json
{
  "properties": {
    "contacts": {
      "type": "array",
      "items": {
        "properties": {
          "organization_id": {
            "anyOf": [
              {"type": "integer", "minimum": 1},
              {"type": "null"}
            ],
            "description": "ID организации (null если не принадлежит организации)"
          }
        }
      }
    },
    "interactions": {
      "type": "array",
      "items": {
        "properties": {
          "organization_id": {
            "anyOf": [
              {"type": "integer", "minimum": 1},
              {"type": "null"}
            ]
          }
        }
      }
    }
  }
}
```

---

#### ✅ Задача 2.2: Обновить промпт v1.1 (30 мин)

**Файл**: `prompts/unified_contact_extraction_v1.1.txt`

**Изменения** (строки 11-21):
```diff
🚨 **СТРОГИЕ ПРАВИЛА ДЛЯ ОБЯЗАТЕЛЬНЫХ ПОЛЕЙ:**
-- ❌ **НИКОГДА не используй `null` для обязательных ID полей:**
-  - `contact_id` - ВСЕГДА число (1, 2, 3...)
-  - `organization_id` - ВСЕГДА число (1, 2, 3...)
-  - `interaction_local_id` - ВСЕГДА число (1, 2, 3...)
+
+- ✅ **ПРАВИЛА ДЛЯ organization_id:**
+  - Если контакт принадлежит организации из блока organizations[] → укажи её organization_id (1, 2, 3...)
+  - Если организации НЕТ в письме (личная переписка, публичные email) → используй `null`
+  - ❌ НИКОГДА не придумывай несуществующие организации!
+  - ❌ НИКОГДА не используй organization_id=1 если нет organizations с таким ID!
+
+- ✅ **ПРАВИЛА ДЛЯ других ID полей:**
+  - `contact_id` - ВСЕГДА число (1, 2, 3...), уникальное в пределах письма
+  - `interaction_local_id` - ВСЕГДА число (1, 2, 3...), если есть interactions
+
- ❌ **НИКОГДА не используй `null` для обязательных строковых полей:**
+- ❌ **НИКОГДА не используй `null` для обязательных строковых полей:**
  - `name` (для контактов и организаций) - ВСЕГДА строка
  - `interaction_type` - ВСЕГДА одно из допустимых значений enum
+
- ✅ **Используй `null` ТОЛЬКО для опциональных полей:**
+- ✅ **Используй `null` для опциональных полей:**
+  - `organization_id` (для контактов) - `null` если нет организации
  - `city`, `address`, `website`, `inn` - могут быть `null`
  - `extension` (для телефонов) - может быть `null`
```

**Обновить version.json**:
```json
{
  "current_version": "1.2",
  "versions": {
    "1.2": {
      "date": "2025-10-16",
      "file": "unified_contact_extraction_v1.2.txt",
      "status": "active",
      "changes": [
        "Разрешён null для organization_id если организации нет",
        "Запрет на несуществующие organization_id",
        "Уточнены правила для личной переписки"
      ]
    }
  }
}
```

---

#### ✅ Задача 2.3: Убрать автокоррекцию (30 мин)

**Файл**: `src/core/safe_math_utils.py`

**Изменения** (строки 168-173):
```python
def fix_none_values_in_data(data, numeric_fields=None, integer_fields=None):
    # ...
    
    for key, value in list(data.items()):
        if key in numeric_fields and value is None:
            if key == "confidence":
                data[key] = 0.0
            else:
                data[key] = 0.0
            logger.debug(f"fix_none_values_in_data: исправлено {key}: None → 0.0")
        
        # ✅ УДАЛЕНО: хардкод organization_id=1
        # elif key in integer_fields and value is None:
        #     data[key] = 1
        
        elif isinstance(value, (dict, list)):
            fix_none_values_in_data(value, numeric_fields, integer_fields)
```

**Изменения** (строки 281-285):
```python
def fix_json_schema_validation_errors(data):
    # ...
    
    if "interactions" in data:
        for interaction in data["interactions"]:
            if isinstance(interaction, dict):
                # ✅ УДАЛЕНО: автоисправление organization_id
                # if 'organization_id' in interaction and interaction['organization_id'] is None:
                #     interaction['organization_id'] = 1
                
                # Исправляем contact_id только если не null
                if 'contact_id' in interaction and interaction['contact_id'] is None:
                    interaction['contact_id'] = 1
                    logger.warning("fix_json_schema_validation_errors: исправлено contact_id: None → 1")
```

---

#### ✅ Задача 2.4: Обработка null в постобработке (1 час)

**Файл**: `src/postprocessing/postprocessor.py`

**Изменения в методе обогащения**:
```python
def _enrich_contacts(self, contacts, organizations):
    """Обогащение контактов"""
    for contact in contacts:
        org_id = contact.get('organization_id')
        
        # ✅ НОВОЕ: обработка контактов без организации
        if org_id is None:
            self.logger.info(f"Контакт {contact.get('name')} не связан с организацией, пропускаем org-based enrichment")
            contact['enrichment_skipped'] = True
            contact['enrichment_reason'] = 'no_organization'
            continue
        
        # Остальная логика для контактов с организациями
        org = organizations.get(org_id)
        if not org:
            self.logger.warning(f"Организация {org_id} не найдена для контакта {contact.get('name')}")
            contact['enrichment_skipped'] = True
            contact['enrichment_reason'] = f'organization_{org_id}_not_found'
            continue
        
        # ... обогащение ...
```

---

### Этап 3: GID для контактов без организаций (2-3 часа)

#### ✅ Задача 3.1: Поддержка независимых GID

**Файл**: `src/registry/global_registry.py`

**Добавить namespace**:
```python
# Существующие
ORG_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
CONTACT_NS = uuid.UUID("b2c3d4e5-f678-90ab-cdef-1234567890ab")

# ✅ НОВЫЙ: для независимых контактов
INDEPENDENT_CONTACT_NS = uuid.UUID("c3d4e5f6-7890-abcd-ef12-34567890abcd")
```

**Изменить resolve_contact**:
```python
def resolve_contact(self, contact: Dict[str, Any], org_gid: str = None) -> ResolutionResult:
    """
    Разрешение контакта с поддержкой независимых (без организации)
    
    Args:
        contact: Данные контакта
        org_gid: GID организации (None если контакт без организации)
    """
    with self._lock:
        if org_gid is None:
            # ✅ Независимый контакт
            keys = self._generate_independent_contact_keys(contact)
            namespace = INDEPENDENT_CONTACT_NS
        else:
            # С организацией
            keys = list(iter_contact_keys(contact, org_gid))
            namespace = CONTACT_NS
        
        if not keys:
            raise ValueError("Contact object does not contain identification data")
        
        # Проверка overrides
        override_result = self._check_overrides(keys, "contact")
        if override_result:
            return override_result
        
        # Поиск существующего
        for key in keys:
            gid = self.key_index.get(key)
            if gid:
                alias_added, _ = self._ensure_aliases(gid, keys, bucket="contacts")
                return ResolutionResult(
                    gid=gid,
                    match_rule=key[1],
                    key_tuple=key,
                    alias_added=alias_added
                )
        
        # Создание нового
        primary = keys[0]
        gid = self._generate_gid(primary, namespace=namespace)
        aliases = [alias for alias in keys[1:] if alias != primary]
        self._create_record(
            bucket="contacts",
            gid=gid,
            primary_key=primary,
            aliases=aliases,
            source="new_independent" if org_gid is None else "new"
        )
        return ResolutionResult(
            gid=gid,
            match_rule=primary[1],
            key_tuple=primary,
            alias_added=bool(aliases),
            source="new"
        )

def _generate_independent_contact_keys(self, contact: Dict[str, Any]) -> List[Tuple]:
    """Генерация ключей для независимых контактов (без org_gid)"""
    keys = []
    
    email = norm_email(contact.get("email"))
    if email:
        keys.append(("CONTACT", "EMAIL_IND", email))
    
    phones = contact.get("phones", [])
    if phones:
        for phone in phones[:2]:  # Первые 2 телефона
            e164 = norm_e164(phone.get("number"))
            if e164:
                keys.append(("CONTACT", "PHONE_IND", e164))
    
    name = norm_contact_name(contact.get("name"))
    if name:
        keys.append(("CONTACT", "NAME_IND", name))
    
    return keys
```

---

## 📝 ЧЕКЛИСТ ТЕСТИРОВАНИЯ

### После Этапа 1:
- [ ] OCR кеш находит результаты с разными хешами
- [ ] Нет сообщений "У вложения 'unknown' отсутствует путь"
- [ ] Обрабатываются только saved вложения

### После Этапа 2:
- [ ] Письма без организаций: `organization_id: null` в JSON
- [ ] Нет автокоррекции на `organization_id: 1`
- [ ] Контакты без организаций помечены `enrichment_skipped: true`

### После Этапа 3:
- [ ] Контактам без организаций назначаются GID
- [ ] GID формата `c3d4e5f6-...` (INDEPENDENT_CONTACT_NS)
- [ ] `gid.assigned` содержит записи для всех контактов

---

## 🎯 ФИНАЛЬНАЯ ПРОВЕРКА

```bash
# Запуск на тестовой дате
python -m src.api_pipeline_validator --mode=batch --date=2025-08-28 --count=9

# Ожидаемые результаты:
# ✅ 0 ошибок "organization_id: None is not of type 'integer'"
# ✅ 0 ошибок "Организация 1 не найдена"
# ✅ 9/9 контактов с назначенными GID
# ✅ OCR кеш: 100% hit rate для файлов с результатами
# ✅ 0 warnings "У вложения 'unknown' отсутствует путь"
```

---

**Общее время исправлений**: 5-7 часов (в зависимости от тестирования)
