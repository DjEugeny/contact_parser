# Отчет: Исправление фильтрации персональных email (2025-10-02)

## 📋 Метаданные
- **Дата/время:** 2025-10-02 16:27 (UTC+7)
- **Версия кода:** main branch (после обновления промпта)
- **Связанная спецификация:** [`.kiro/specs/contact-email-filter`](.kiro/specs/contact-email-filter/)
- **Статус задачи:** ⚠️ Частично решено, требуется перезапуск обработки

## 🐛 Обнаруженная проблема

### Симптомы
Несмотря на реализованную фильтрацию email в постпроцессоре, в processed файлах (`data/llm_results/2025-07-29/`) для организации ДНК-Технология остаются персональные адреса сотрудников:
- `m.gogoleva@dna-technology.ru`
- `prisyazhnyuk@dna-technology.ru`

**Проблемные файлы:**
- `email_024_20250729_..._processed.json`
- `email_025_20250729_..._processed.json`
- `email_026_20250729_..._processed.json`

### Корневая причина (двухуровневая)

#### 1. Проблема на стороне LLM модели
**Что происходит:**
- LLM модель изначально помещает персональные корпоративные адреса в `organizations[].emails`
- Проверка RAW файлов показала, что проблема возникает **до** постобработки

**Почему происходит:**
- В промпте ([`prompts/unified_contact_extraction_structured.txt`](../../prompts/unified_contact_extraction_structured.txt)) отсутствовали явные инструкции о разделении personal/shared email
- Модель видела корпоративный домен `@dna-technology.ru` и считала любой адрес на этом домене "организационным"

#### 2. Проблема применения постобработки
**Что происходит:**
- В processed файлах отсутствует секция `postprocessing_metadata.email_classification`
- Персональные адреса не были отфильтрованы

**Почему происходит:**
- Файлы были обработаны **до реализации** функции фильтрации email
- Постпроцессор с фильтрацией был добавлен позже
- Переобработка не была выполнена

## ✅ Реализованное решение

### 1. Обновление промпта LLM
**Файл:** [`prompts/unified_contact_extraction_structured.txt`](../../prompts/unified_contact_extraction_structured.txt:12-19)

**Изменения:**
Добавлен раздел с явными инструкциями о классификации email:

```markdown
3. 📧 **КРИТИЧЕСКИ ВАЖНО для EMAILS:**
   - ✅ ВКЛЮЧАЙ в `organizations.emails` ТОЛЬКО:
     * Общие/ролевые ящики: info@, sales@, support@, torgi@, mail@, hotline@
     * Департаментные: team@, marketing@, finance@, accounting@, buh@
     * Технические: noreply@, robot@, do-not-reply@
     * Групповые алиасы: *-all@, *-team@, *-group@
   - ❌ НЕ ВКЛЮЧАЙ в `organizations.emails`:
     * Персональные адреса: имя.фамилия@, и.фамилия@, фамилия@
     * Даже на корпоративном домене, персональный адрес только в contacts[].email
```

### 2. Создан скрипт для перезапуска обработки
**Файл:** [`scripts/reprocess_problematic_emails.py`](../../scripts/reprocess_problematic_emails.py)

**Возможности:**
- Автопоиск писем с персональными адресами в organizations.emails
- Перезапуск обработки конкретных писем
- Режим dry-run для тестирования

**Использование:**
```bash
# Автопоиск и перезапуск всех проблемных писем
python scripts/reprocess_problematic_emails.py --date 2025-07-29 --all-dna-tech

# Перезапуск конкретных писем
python scripts/reprocess_problematic_emails.py --date 2025-07-29 --emails email_024 email_025 email_026

# Тестовый режим
python scripts/reprocess_problematic_emails.py --date 2025-07-29 --all-dna-tech --dry-run
```

### 3. Обновлена документация

**Обновленные файлы:**
- [`.kiro/specs/contact-email-filter/PLAN-001_Email_Classifier_and_OrgEmails_Cleanup.md`](../../.kiro/specs/contact-email-filter/PLAN-001_Email_Classifier_and_OrgEmails_Cleanup.md:12-37) - добавлен статус и описание проблемы
- [`.kiro/specs/contact-email-filter/requirements.md`](../../.kiro/specs/contact-email-filter/requirements.md:7-26) - добавлен анализ и решение
- [`.kiro/specs/contact-email-filter/tasks.md`](../../.kiro/specs/contact-email-filter/tasks.md:10-27) - добавлена Фаза 2 с задачами исправления

## 📊 Ожидаемые результаты после перезапуска

### До исправления (текущее состояние)
```json
{
  "organizations": [{
    "organization_id": 1,
    "name": "ДНК-Технология",
    "emails": [
      "m.gogoleva@dna-technology.ru",     // ❌ персональный
      "prisyazhnyuk@dna-technology.ru"    // ❌ персональный
    ]
  }]
}
```

### После исправления (ожидаемое)
```json
{
  "organizations": [{
    "organization_id": 1,
    "name": "ДНК-Технология",
    "emails": []  // ✅ персональные адреса удалены
  }],
  "postprocessing_metadata": {
    "email_classification": {
      "1": {
        "kept": [],
        "removed": [
          "m.gogoleva@dna-technology.ru",
          "prisyazhnyuk@dna-technology.ru"
        ],
        "removed_types": {
          "m.gogoleva@dna-technology.ru": "personal_internal",
          "prisyazhnyuk@dna-technology.ru": "personal_internal"
        }
      }
    }
  }
}
```

## 🔄 Следующие шаги

### Обязательные действия
1. ✅ **Выполнено:** Обновлен промпт LLM
2. ✅ **Выполнено:** Создан скрипт перезапуска
3. ⏳ **Требуется:** Запустить перезапуск обработки:
   ```bash
   python scripts/reprocess_problematic_emails.py --date 2025-07-29 --all-dna-tech
   ```
4. ⏳ **Требуется:** Проверить результаты:
   - Убедиться, что `organizations.emails` не содержит персональных адресов
   - Проверить наличие `postprocessing_metadata.email_classification`
   - Сверить статистику фильтрации

### Рекомендации
1. **Тестирование на новых данных:**
   - Обработать несколько новых писем с обновленным промптом
   - Проверить, что LLM сразу правильно классифицирует email

2. **Мониторинг:**
   - Добавить в диагностику проверку на персональные адреса в organizations
   - Алертить, если обнаружены после обработки

3. **Расширение конфига:**
   - Добавить в [`config/org_profile.yml`](../../config/org_profile.yml) больше известных префиксов
   - Настроить под другие корпоративные домены при необходимости

## 📝 Технические детали

### Затронутые компоненты
1. **Промпт:** [`prompts/unified_contact_extraction_structured.txt`](../../prompts/unified_contact_extraction_structured.txt:12-19)
2. **Классификатор:** [`src/postprocessing/email_classifier.py`](../../src/postprocessing/email_classifier.py:65-112)
3. **Постпроцессор:** [`src/postprocessing/postprocessor.py`](../../src/postprocessing/postprocessor.py:324-397)
4. **Конфиг:** [`config/org_profile.yml`](../../config/org_profile.yml)

### Проверенные настройки
- ✅ Флаг `POSTPROCESSOR_KEEP_ONLY_SHARED_ORG_EMAILS` = `True` (по умолчанию)
- ✅ Флаг `POSTPROCESSOR_DEMOTE_PERSONAL_ORG_EMAILS` = `True` (по умолчанию)
- ✅ Конфиг классификатора: `config/org_profile.yml` существует и настроен

### Механизм работы фильтрации
1. Постпроцессор загружает конфиг из `org_profile.yml`
2. Для каждого email в `organizations[].emails` вызывается `classify_mailbox()`
3. Классификатор определяет тип: PERSONAL_INTERNAL/SHARED_ORG/DEPARTMENT/etc.
4. Оставляются только: SHARED_ORG, DEPARTMENT, GROUP_ALIAS, TECHNICAL
5. Персональные адреса (PERSONAL_INTERNAL, PERSONAL_EXTERNAL) удаляются
6. Результат логируется в `postprocessing_metadata.email_classification`

## 🎯 Критерии успеха

### Обязательные
- [x] Промпт обновлен с явными инструкциями
- [ ] Перезапущена обработка проблемных писем
- [ ] В `organizations.emails` для ДНК-Технология отсутствуют персональные адреса
- [ ] Присутствует `postprocessing_metadata.email_classification` с логом фильтрации

### Дополнительные
- [ ] Новые письма обрабатываются корректно сразу (LLM не помещает personal в org)
- [ ] Статистика показывает удаленные персональные адреса
- [ ] Диагностика не показывает предупреждений

## 📚 Связанные документы
- Исходная спецификация: [PLAN-001](.kiro/specs/contact-email-filter/PLAN-001_Email_Classifier_and_OrgEmails_Cleanup.md)
- Требования: [requirements.md](.kiro/specs/contact-email-filter/requirements.md)
- Дизайн: [design.md](.kiro/specs/contact-email-filter/design.md)
- План задач: [tasks.md](.kiro/specs/contact-email-filter/tasks.md)
- Основная документация: [AGENTS.md](../../AGENTS.md)

## 🔧 Дополнительная информация

### Примеры правильной классификации

| Email | Тип | Где должен быть |
|-------|-----|-----------------|
| `info@dna-technology.ru` | SHARED_ORG | organizations.emails ✅ |
| `torgi@dna-technology.ru` | SHARED_ORG | organizations.emails ✅ |
| `hotline@dna-technology.ru` | SHARED_ORG | organizations.emails ✅ |
| `m.gogoleva@dna-technology.ru` | PERSONAL_INTERNAL | только contacts.email ✅ |
| `prisyazhnyuk@dna-technology.ru` | PERSONAL_INTERNAL | только contacts.email ✅ |
| `s.voronova@dna-technology.ru` | PERSONAL_INTERNAL | только contacts.email ✅ |
| `noreply@dna-technology.ru` | TECHNICAL | organizations.emails ✅ |
| `sales-team@dna-technology.ru` | GROUP_ALIAS | organizations.emails ✅ |

### Логика классификации (упрощенно)
```python
def classify_mailbox(address, display_name, corp_domains, cfg):
    if domain in corp_domains:
        if matches_pattern("имя.фамилия" or "и.фамилия"):
            return PERSONAL_INTERNAL
        if starts_with(shared_prefixes):  # info, sales, torgi
            return SHARED_ORG
        if starts_with(technical_prefixes):  # noreply, robot
            return TECHNICAL
    else:
        if looks_like_person(display_name or local_part):
            return PERSONAL_EXTERNAL
    return UNKNOWN
```

## ⚠️ Важные замечания

1. **Двухуровневая защита:**
   - Уровень 1 (LLM): Модель должна сразу правильно классифицировать
   - Уровень 2 (Постпроцессор): Фильтр на случай ошибки LLM

2. **Обратная совместимость:**
   - Старые processed файлы требуют переобработки
   - Новые файлы должны обрабатываться корректно сразу

3. **Проверка результатов:**
   - После перезапуска обязательно проверить наличие `email_classification` в метаданных
   - Убедиться, что персональные адреса действительно удалены
   - Проверить, что контакты остались с правильными email

## 📞 Команды для выполнения

### 1. Автопоиск и перезапуск всех проблемных писем
```bash
cd /Users/evgenyzach/contact_parser
python scripts/reprocess_problematic_emails.py --date 2025-07-29 --all-dna-tech
```

### 2. Перезапуск конкретных писем (если известны)
```bash
python scripts/reprocess_problematic_emails.py --date 2025-07-29 --emails email_024 email_025 email_026
```

### 3. Тестовый запуск (без записи в БД)
```bash
python scripts/reprocess_problematic_emails.py --date 2025-07-29 --all-dna-tech --dry-run
```

### 4. Проверка результата одного письма
```bash
# После перезапуска проверить файл:
cat data/llm_results/2025-07-29/email_024_*_processed.json | jq '.processed_result.postprocessing_metadata.email_classification'
```

## 📈 Метрики успеха

### Ожидаемые показатели после перезапуска:
- **Писем обработано:** 3+ (минимум проблемные)
- **Организаций с чистыми emails:** 100%
- **Персональных адресов удалено:** ~6-9 (по 2-3 на письмо)
- **Ошибок валидации:** 0
- **Наличие метаданных фильтрации:** 100%

### Проверочные запросы:
```bash
# Подсчитать сколько организаций ДНК-Технология имеют персональные адреса
grep -r "m.gogoleva@dna-technology.ru" data/llm_results/2025-07-29/*_processed.json | wc -l

# Проверить наличие метаданных фильтрации
grep -r "email_classification" data/llm_results/2025-07-29/*_processed.json | wc -l
```

## 🔗 Ссылки
- Основная задача в Kilocode: `.kiro/specs/contact-email-filter/`
- Конфигурация классификатора: `config/org_profile.yml`
- Реализация фильтрации: `src/postprocessing/email_classifier.py`
- Интеграция в пайплайн: `src/postprocessing/postprocessor.py`
- Скрипт перезапуска: `scripts/reprocess_problematic_emails.py`

---

**Автор:** AI Assistant  
**Дата создания:** 2025-10-02 16:27 UTC+7  
**Статус:** Решение готово, требуется выполнение перезапуска