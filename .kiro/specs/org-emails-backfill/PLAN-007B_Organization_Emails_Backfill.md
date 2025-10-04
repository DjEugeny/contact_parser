
# TASK-007B: Organization Emails — извлечение, классификация и backfill

## Преамбула и кейс (письмо 017 «Медконгресс»)

**Проблема:** у организации **Медконгресс** в исходниках есть адрес `mail@medcongress.ru`, но он **не попал** в `organizations[].emails` после обработки письма.

**Файлы для воспроизведения:**
- Оригинал: `email_017_20250729_20250729_dna-technology_ru_ee04f823.json`
- RAW LLM: `email_017_20250729_20250729_dna_technology_ru_ee04f823_20251003_224947_230813_raw.json`
- Processed: `email_017_20250729_20250729_dna_technology_ru_ee04f823_20251003_224947_230813_processed.json`

**Симптом:** общий корпоративный ящик `mail@medcongress.ru` не извлечён в карточку организации. Нужен модуль, который собирает организационные e‑mail из заголовков, подписи и вложений, классифицирует их как «общие/роль» vs «персональные» и дописывает в `organizations[].emails` (с дедупом и метаданными).

---

## Место в пайплайне

`sanitize → org dedup → assign gid → **collect_org_emails (headers+signature+attachments) → classify_role_mail → add to organizations[].emails** → normalization/dedup → cross‑links`

> Задача **007B** независима от задач 008A/008B (которые про города/адреса).

---

## 1) Источники e‑mail для организаций

- **Заголовки письма:** `From`, `To`, `Cc`, `Reply‑To` — собрать все адреса и домены.
- **Блок подписи организации** в теле (LLM‑парсинг или собственные сигнатуры).
- **Вложения (реквизиты/КП)** — если в OCR‑тексте встречается e‑mail, связанный с названием организации.

**Правило привязки:** адрес попадает в `organizations[].emails`, если:
1) e2LD домена адреса == домену организации **и** локальная часть похожа на «роль/общий ящик», **или**  
2) адрес явно упомянут **рядом** с названием организации в подписи/вложении.

---

## 2) Классификатор «общий ящик» vs «персональный»

- **Whitelists (роль/общие):** `info@`, `mail@`, `sales@`, `office@`, `contact@`, `support@`, `admin@`, `order@`, `service@`, `pr@`, `hr@`, `marketing@`, `accounting@`, `billing@`, `tender@`, `export@`, `import@`, `help@`, `it@` …
- **Black‑hints (персональные):** паттерны `firstname.lastname@`, одиночные инициалы, `@gmail/@yahoo/@mail.ru`, локальная часть, содержащая ФИО/инициалы или номер телефона.
- При сомнении — **не добавлять** в итог, поставить `needs_review` в служебные метаданные.

---

## 3) Алгоритм

```
sanitize → org dedup → assign gid
→ collect_org_emails (headers+signature+attachments OCR‑txt)
→ classify_role_mail
→ add to organizations[gid].emails
→ normalization/dedup
```

Псевдокод:
```python
candidates = emails_from_headers | emails_from_signature | emails_from_attachments
for e in candidates:
    if e2ld(domain(e)) == org.e2ld and is_role_mail(e):
        organizations[gid].emails.add(lowercase(e))
    else:
        skip_or_review(e)
```

- Дедуп по **lowercased** адресу (множество/словарь).  
- **Никогда** не переносить адреса **нашей** компании (напр. `@dna-technology.ru`) в карточки **сторонних** организаций.  
- Для вложений использовать OCR‑текст (`.txt`) как источник (см. TASK‑008A подход к OCR).

---

## 4) Метаданные

Сохранять служебные метаданные в корневом `postprocessing_metadata`:

```json
"postprocessing_metadata": {
  "org_email_enrichment": {
    "<org_gid>": {
      "added": ["mail@medcongress.ru"],
      "skipped": ["ivan.petrov@medcongress.ru"],
      "source": {"mail@medcongress.ru":"headers"}
    }
  }
}
```

- `added` — какие адреса реально вписали в карточку организации.  
- `skipped` — что отбросили (персональные/сомнительные).  
- `source` — откуда взяли (headers/signature/attachments).

---

## 5) Миграция / backfill

- Пройти архив JSON‑файлов: для каждой организации собрать кандидатов из заголовков/подписей/вложений, пропустить через классификатор, пополнить `organizations[].emails`.
- Сформировать отчёт: `added/skipped/review` по организациям и общее количество.

---

## 6) Тест‑план / DoD

- Для письма 017 («Медконгресс») адрес `mail@medcongress.ru` добавлен в `organizations[].emails`.
- ФИО‑подобные адреса **не** попадают в `organizations[].emails`.
- Повторный прогон идемпотентен (дедуп не даёт дублей).
- Схема не падает, `organizations[].emails` — массив **строк**, без посторонних полей.
- В `postprocessing_metadata.org_email_enrichment` есть трассировка источника.

---

## Out of scope

> Любые операции с **городом/адресом** (city/address) организаций и **защита контактов** от HQ‑адресов — это задачи **008A** и **008B**. В 007B мы работаем **только с e‑mail адресами организаций**.

---

## Порядок запуска задач агенту (рекомендация)

1) **TASK‑007B (этот модуль)** — изоляция и простая интеграция, быстро закрывает «Медконгресс» и подобные кейсы; не зависит от 008A/008B.  
2) **TASK‑008B (Contact Location Safety)** — сразу защищаем контакты от протечек HQ‑адресов/городов.  
3) **TASK‑008A (Attachment Evidence → Org City/Address)** — используем OCR‑тексты вложений для обогащения локаций организаций.

> Такой порядок минимизирует риск регресса и даёт быстрый «видимый» результат по e‑mail, затем — безопасность контактов, затем — полноценное обогащение локаций.
