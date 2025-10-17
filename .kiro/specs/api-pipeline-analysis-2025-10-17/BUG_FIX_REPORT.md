# 🐛 ОТЧЁТ ОБ ИСПРАВЛЕНИИ БАГА — Фильтр 15K токенов

**Дата:** 2025-10-17  
**Статус:** ✅ Исправлено  
**Приоритет:** 🔴 P0 КРИТИЧНО

---

## ❌ ПРОБЛЕМА

Фильтр 15K токенов для вложений **НЕ РАБОТАЛ**.

### Доказательства из логов:

| Письмо | Вложение | Токенов | Отправлено в LLM | Должно быть |
|--------|----------|---------|------------------|-------------|
| email_023 (2025-07-11) | D043-02_ПРОБА-МЧ-РАПИД-II | **27,771** | ✅ 28,618 | ❌ Отброшено |
| email_015 (2025-07-09) | AmpliSens ARVI-screen-short | **41,902** | ✅ 43,878 | ❌ Отброшено |
| email_013 (2025-05-12) | 579-2_HLA-эксперт_IVD_b | **57,374** | ✅ 58,631 | ❌ Отброшено |

**Все три вложения >15K токенов были отправлены в LLM!**

---

## 🔍 КОРНЕВАЯ ПРИЧИНА

### Анализ кода (до исправления):

```python
# src/api_pipeline_validator.py, строка 794-798

cached_text = self.ocr_cache.get_cached_result(filename, date)

if cached_text:
    print(f"✅ OCR кеш: {filename} ({len(cached_text)} символов)")
    return cached_text  # ❌ ВОЗВРАТ БЕЗ ПРОВЕРКИ ТОКЕНОВ!
```

**Проблема:** После нахождения OCR кеша код **сразу возвращал текст** без проверки размера в токенах!

### Логи подтверждают:

```
✅ OCR кеш: ...ПРОБА-МЧ-РАПИД-II... (57082 символов)
✅ OCR кеш: ...AmpliSens ARVI... (83658 символов)
✅ OCR кеш: ...579-2_HLA... (116922 символов)
```

**НИ ОДНОГО** сообщения `⚠️ ФИЛЬТР: Вложение слишком большое`!

---

## ✅ ИСПРАВЛЕНИЕ

### Изменение 1: Проверка токенов после OCR кеша

**Файл:** `src/api_pipeline_validator.py` (строки 796-820)

```python
if cached_text:
    print(f"✅ OCR кеш: {original_filename} ({len(cached_text)} символов)")
    
    # ✅ ФИЛЬТР БОЛЬШИХ ВЛОЖЕНИЙ: проверка кешированного текста
    token_count = self._count_tokens(cached_text)
    if token_count > 15000:
        orig_filename = attachment.get('original_filename') or attachment.get('filename', 'unknown')
        print(f"⚠️ ФИЛЬТР: Вложение '{orig_filename}' слишком большое ({token_count:,} токенов > 15,000)")
        print(f"   💡 Причина: Бизнес-правило - вложения >15K токенов нерелевантны")
        print(f"   🚫 Вложение отброшено для защиты от засорения базы")
        
        # Логирование в статистику
        if not hasattr(self, 'large_attachments_filtered'):
            self.large_attachments_filtered = []
        
        self.large_attachments_filtered.append({
            'filename': orig_filename,
            'tokens': token_count,
            'email_subject': email.get('subject', 'unknown'),
            'date': date
        })
        
        return None  # Отбрасываем большое вложение
    
    return cached_text
```

### Изменение 2: Проверка токенов после OCR обработки

**Файл:** `src/api_pipeline_validator.py` (строки 840-863)

```python
if ocr_result.get("success") and ocr_result.get("text"):
    extracted_text = ocr_result["text"]
    print(f"   ✅ OCR успешно: извлечено {len(extracted_text)} символов")
    
    # ✅ ФИЛЬТР БОЛЬШИХ ВЛОЖЕНИЙ: проверка размера после OCR
    token_count = self._count_tokens(extracted_text)
    if token_count > 15000:
        orig_filename = attachment.get('original_filename') or attachment.get('filename', 'unknown')
        print(f"   ⚠️ ФИЛЬТР: Вложение '{orig_filename}' слишком большое ({token_count:,} токенов > 15,000)")
        print(f"   💡 Причина: Бизнес-правило - вложения >15K токенов нерелевантны")
        print(f"   🚫 Вложение отброшено для защиты от засорения базы")
        
        # Логирование в статистику
        if not hasattr(self, 'large_attachments_filtered'):
            self.large_attachments_filtered = []
        
        self.large_attachments_filtered.append({
            'filename': orig_filename,
            'tokens': token_count,
            'email_subject': email.get('subject', 'unknown'),
            'date': date
        })
        
        return None  # Отбрасываем большое вложение
    
    # Показываем превью извлеченного текста
    preview = extracted_text[:200].replace('\n', ' ')
    print(f"   📄 Превью: {preview}...")
    return extracted_text
```

### Изменение 3: Использование оригинального имени файла

**Файл:** `src/api_pipeline_validator.py` (строки 791-794)

```python
# Фаза 1: Проверка кеша БЕЗ инициализации OCR модуля
# Используем ОРИГИНАЛЬНОЕ имя файла для поиска в кеше
original_filename = attachment.get('original_filename') or attachment.get('filename') or attachment_path.name
cached_text = self.ocr_cache.get_cached_result(original_filename, date)
```

**Причина:** OCR кеш ищет файлы по паттерну `*_attach_{original_name}.txt`, поэтому нужно передавать оригинальное имя, а не полный путь.

---

## 📊 РЕЗУЛЬТАТ

### До исправления:
- ❌ Вложения >15K токенов отправлялись в LLM
- ❌ Нет фильтрации
- ❌ Засорение базы нерелевантными данными
- ❌ Избыточные API запросы

### После исправления:
- ✅ Вложения >15K токенов отбрасываются
- ✅ Детальное логирование фильтрации
- ✅ Статистика отфильтрованных вложений
- ✅ Защита от засорения базы

---

## 🧪 ТЕСТИРОВАНИЕ

### Команда:
```bash
python -m src.api_pipeline_validator --date=2025-07-11 --count=1
```

### Ожидаемый результат:
```
✅ OCR кеш: D043-02_ПРОБА-МЧ-РАПИД-II_2025-03-07.pdf (57,082 символов)
⚠️ ФИЛЬТР: Вложение 'D043-02_ПРОБА-МЧ-РАПИД-II_2025-03-07.pdf' слишком большое (27,771 токенов > 15,000)
   💡 Причина: Бизнес-правило - вложения >15K токенов нерелевантны
   🚫 Вложение отброшено для защиты от засорения базы

🚫 ОТФИЛЬТРОВАНО БОЛЬШИХ ВЛОЖЕНИЙ: 1
📊 Общий объём отброшенного текста: 27,771 токенов
```

---

**Статус:** ✅ Готово к тестированию  
**Автор:** Cascade AI  
**Дата:** 2025-10-17
