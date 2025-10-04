# TASK-007B: Organization Emails Backfill - Детальный план выполнения

## Цель
Реализовать модуль для извлечения, классификации и добавления email-адресов организаций из заголовков письма, подписей и вложений в поле `organizations[].emails`.

## Кейс для тестирования
- **Файл:** `email_017_20250729_20250729_dna-technology_ru_ee04f823.json`
- **Проблема:** адрес `mail@medcongress.ru` организации "Медконгресс" не попал в `organizations[].emails`
- **Ожидаемый результат:** адрес должен быть добавлен в поле `organizations[].emails`

## Этапы выполнения

### Этап 1: Анализ текущей структуры кода ✅
- [x] Создать папку для задачи
- [x] Перенести PLAN документ
- [x] Изучить структуру `src/postprocessing/`
- [x] Изучить файл `postprocessor.py` - основной файл постобработки
- [x] Изучить `organization_deduplicator.py` - логика дедупликации организаций
- [x] Найти где происходит обработка поля `organizations[]`

### Этап 2: Создание модуля сбора email-адресов ✅
- [x] Создать `src/postprocessing/org_email_enricher.py`
- [x] Реализовать функцию `extract_emails_from_headers()` - сбор из From, To, Cc, Reply-To
- [x] Реализовать функцию `extract_emails_from_signature()` - парсинг подписи письма
- [x] Реализовать функцию `extract_emails_from_attachments()` - парсинг OCR-текста вложений
- [x] Создать конфигурационные списки для классификации

### Этап 3: Создание классификатора email-адресов ✅
- [x] Реализовать функцию `classify_email_type()` 
- [x] Создать whitelist роль/общих ящиков: info@, mail@, sales@, office@, contact@, support@, admin@, order@, service@, pr@, hr@, marketing@, accounting@, billing@, tender@, export@, import@, help@, it@
- [x] Создать black-hints для персональных: firstname.lastname@, @gmail/@yahoo/@mail.ru, инициалы, номера телефонов
- [x] Логика определения принадлежности email к организации (e2LD домена)

### Этап 4: Интеграция в пайплайн постобработки ✅
- [x] Найти точку интеграции в `postprocessor.py` после assign gid
- [x] Добавить вызов обогащения email в основной пайплайн
- [x] Реализовать сохранение метаданных в `postprocessing_metadata.org_email_enrichment`
- [x] Обеспечить дедупликацию по lowercase адресу

### Этап 5: Создание утилит и конфигурации ✅
- [x] Создать функцию для извлечения e2LD домена
- [x] Создать функцию для безопасного добавления в organizations[].emails
- [x] Защита от добавления адресов @dna-technology.ru в сторонние организации
- [x] Логирование и отладочная информация

### Этап 6: Тестирование на кейсе ✅
- [x] Найти тестовый файл `email_017_20250729_20250729_dna-technology_ru_ee04f823.json`
- [x] Запустить обработку с новым модулем
- [x] Проверить что `mail@medcongress.ru` попал в `organizations[].emails` для Медконгресс
- [x] Проверить что персональные адреса не попали в организации
- [x] Проверить метаданные в `postprocessing_metadata.org_email_enrichment`

### Этап 7: Создание backfill утилиты ✅
- [x] Создать скрипт для массовой обработки архива JSON файлов
- [x] Реализовать пройти все существующие файлы и обогатить organizations.emails
- [x] Создать отчет по добавленным/пропущенным адресам
- [x] Обеспечить идемпотентность повторных запусков

### Этап 8: Финальное тестирование и валидация ✅
- [x] Тестирование на различных типах писем
- [x] Проверка что схема не падает
- [x] Проверка что organizations[].emails остается массивом строк
- [x] Валидация дедупликации
- [x] Проверка трассировки источников в метаданных

## Технические детали

### Место в пайплайне
```
sanitize → org dedup → assign gid → **collect_org_emails** → classify_role_mail → add to organizations[].emails → normalization/dedup → cross‑links
```

### Алгоритм
```python
candidates = emails_from_headers | emails_from_signature | emails_from_attachments
for email in candidates:
    if e2ld(domain(email)) == org.e2ld and is_role_mail(email):
        organizations[gid].emails.add(lowercase(email))
    else:
        skip_or_review(email)
```

### Структура метаданных
```json
"postprocessing_metadata": {
  "org_email_enrichment": {
    "<org_gid>": {
      "added": ["mail@medcongress.ru"],
      "skipped": ["ivan.petrov@medcongress.ru"],
      "source": {"mail@medcongress.ru": "headers"}
    }
  }
}
```

## Критерии готовности (DoD) ✅
- [x] Задача 007B независима от задач 008A/008B
- [x] Для письма 017 адрес `mail@medcongress.ru` добавлен в `organizations[].emails`
- [x] ФИО-подобные адреса НЕ попадают в `organizations[].emails`
- [x] Повторный прогон идемпотентен (дедуп работает)
- [x] Схема не падает, `organizations[].emails` — массив строк
- [x] В `postprocessing_metadata.org_email_enrichment` есть трассировка источника
- [x] Создана утилита для backfill архива

## Файлы для создания/изменения ✅
- ✅ `/src/postprocessing/org_email_enricher.py` - новый модуль
- ✅ `/src/postprocessing/postprocessor.py` - интеграция в пайплайн  
- ✅ `/scripts/backfill_org_emails.py` - утилита для массовой обработки
- ✅ `/test_org_email_enrichment.py` - тесты для модуля

## Результаты тестирования ✅

### Основные тесты пройдены:

1. **Кейс Медконгресс**: `mail@medcongress.ru` и `info@medcongress.ru` успешно добавлены, персональные отфильтрованы
2. **Классификация**: Роль/общие адреса добавляются, персональные отклоняются  
3. **Защита доменов**: Адреса @dna-technology.ru НЕ попадают в сторонние организации
4. **Вложения**: Email извлекаются из OCR-текста с правильной фильтрацией
5. **Метаданные**: Полная трассировка источников (headers/signature/attachments)
6. **Backfill**: Создана утилита для массовой обработки архива

### Статистика успешного выполнения:
- Организаций обогащено: 100% в тестах
- Email добавлено: Только роль/общие адреса
- Email отклонено: Все персональные и сторонние домены
- Метаданные: Полная трассировка по всем источникам