# Исправление ошибки 'NoneType' object is not subscriptable в OCR модуле

## Проблема
В OCR модуле возникала ошибка `'NoneType' object is not subscriptable` при обработке изображений с адаптивным сжатием.

## Анализ
Проблема была обнаружена в методе `run_google_vision_ocr_with_smart_compression` на строке 2433. Код пытался обратиться к индексам результата (`result[0]` и `result[1]`) без предварительной проверки на `None`.

## Исправление
Добавлена проверка на `None` перед обращением к индексам:

```python
# Было:
if result[0]:  # Если есть текст
    self._log_ocr_quality_metrics(result[0], result[1], method="google_vision_compressed")

# Стало:
if result and result[0]:  # Проверяем что result не None и есть текст
    self._log_ocr_quality_metrics(result[0], result[1], method="google_vision_compressed")
```

## Результат
- Устранена потенциальная ошибка при обработке изображений
- Улучшена стабильность OCR модуля
- Добавлена защита от обращения к None объекту

## Файлы изменены
- `/Users/evgenyzach/contact_parser/src/ocr_processor.py` (строка 2433)

---
*Отчет создан: 2025-01-17 14:30 (UTC+07)*