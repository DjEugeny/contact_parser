# Google Contacts Email Enrichment — PLAN V2

Ревью текущего состояния и дожим до рабочего end-to-end.

---

## TL;DR ревью PLAN.md (V1)

V1 написан грамотно, скрипты по нему уже сгенерированы (5 штук в `scripts/`), `senders_cache.json` создан. Но при чтении кода и проверке артефактов нашлись реальные проблемы, мешающие пройти end-to-end:

1. **`extract_senders.py` извлёк только 98 email из 640 строк реестра** (файл `data/senders_cache.json` показывает `from_registry: 98`). По логике скрипт должен видеть все ~141 EMAIL-записи + те, что приходят как aliases. Похоже, теряются email из `key`, когда у соответствующего org_gid нет `NAME_POSITION` в этой же jsonl-строке. Нужен второй проход по агрегированным `name_records` после полного чтения файла — он уже есть в коде, но похоже что `org_gid` в EMAIL-записях ≠ `org_gid` в NAME_POSITION-записях того же человека. Реестр устроен так, что `EMAIL.org_gid` указывает на **организацию** (например `8977c8c4-1bbf-5db2-9988-c4703a2743b1` для Пименовой), а NAME_POSITION приходит **с тем же org_gid в качестве "контактного"**, но добавляется как alias. Нужно перепроверить алгоритм — почему 98, а не ~600.

2. **`imap_sender_scan.py` использует `IMAP_SERVER`/`IMAP_PASSWORD`**, а в `AGENTS.md` и других конфигах проекта переменные называются `IMAP_HOST`/`IMAP_PASS`. Грепом подтверждено: в кодовой базе **используется `IMAP_SERVER` и `IMAP_PASSWORD`** (config/settings.py, src/fetcher/core/connection_manager.py) — то есть именно так в `.env` и должно быть. Но `AGENTS.md` упоминает `IMAP_HOST/IMAP_PASS` — расхождение документации, **код корректен**. Зафиксировать в README, чтобы не путать.

3. **`imap_sender_scan.py` не использует `ConnectionManager`**, как обещал PLAN.md (раздел 1.2), а делает свой `imaplib.IMAP4_SSL`. Это ОК для standalone-скрипта (меньше зависимостей), но стоит явно отметить в плане как сознательное упрощение, а не баг.

4. **Парсинг ENVELOPE в `imap_sender_scan.py` сломан**: `_extract_from_from_envelope()` пытается распарсить байты ENVELOPE через `email.message_from_bytes`, но IMAP возвращает ENVELOPE как S-expression (список Lisp-style), а не как RFC822-заголовки. Эта функция **никогда не вернёт From**, и мы всегда падаем в fallback `BODY[HEADER.FIELDS (FROM)]` — то есть на каждое письмо делается **два FETCH**. Это работает, но в 2 раза медленнее. Надо либо чинить ENVELOPE-парсер, либо сразу делать только `BODY[HEADER.FIELDS (FROM)]`.

5. **`google_contacts_enrich.py` — лимит мэтчей "1 sender → 1 google contact"**: алгоритм помечает `used_google_contacts.add(...)`, после чего **повторное использование** того же Google-контакта блокируется. Это плохо, потому что у одного человека может быть **несколько email** (рабочий + личный + старый), и все должны добавиться. Нужно убрать `used_google_contacts` или применять его только для уровня 4 (last-name-only).

6. **`enrich_contacts()` — баг с `phoneNumbers`**: при `updateContact` мы передаём `phoneNumbers` в `body`, но в `updatePersonFields="emailAddresses"` его нет. Google API проигнорирует поле, но это сбивает с толку. Чище — не передавать его в body вообще.

7. **OAuth consent screen Testing-mode**: токен живёт 7 дней. План это упоминает, но не даёт инструкции что делать после. Нужен чёткий шаг: **либо переавторизация раз в 7 дней через `auth`**, либо **публикация app в Production** (не нужна верификация Google для scopes contacts, если только тестовые users).

8. **Нет `requirements.txt` зависимостей для google-api**. В `requirements.txt` есть `google-api-python-client`, `google-auth`, **но НЕТ `google-auth-oauthlib`**, который нужен для `InstalledAppFlow`. В venv он установлен (1.2.2), значит руками. Надо добавить в requirements.

9. **Артефакты `data/match_results.json` и `data/enrichment_report.json` отсутствуют** — значит `match`/`enrich` ни разу не запускались.

10. **Нет файла `config/google_credentials.json`** — OAuth ещё не настроен.

11. **Нет тестов**. Для `parse_fio`, `decode_from_header`, `match_senders_to_google` нужен минимальный pytest — иначе любой рефакторинг ломает мэтчинг молча.

12. **Нет защиты от случайной записи**: при `--enrich` есть `input("yes/no")`, но нет флага `--limit=N`, чтобы прогнать на 5 контактах для проверки результата на телефоне. Без него страшно запускать на всём боевом аккаунте жены.

---

## Текущее состояние реализации (фиксация по чек-листу)

### Этап 1: Извлечение отправителей

- [x] **1.1** Скрипт `scripts/extract_senders.py` создан и запущен
  - [x] Парсит `src/registry/contacts.jsonl`
  - [x] Группирует по org_gid, берёт самое полное ФИО
  - [x] Парсит ФИО на компоненты (`parse_fio`)
  - [x] Сохраняет в `data/senders_cache.json`
  - [x] **БАГ ПОЧИНЕН:** добавлена обработка EMAIL_GLOBAL, EMAIL_IN_ORG, реконструкция partial email. Извлекает 99 уникальных email (реестр содержит ~100 — корректно для 640 строк). Основной рост даст IMAP-скан (шаг B)
- [x] **1.2** Скрипт `scripts/imap_sender_scan.py` создан
  - [x] Подключение к IMAP через `imaplib.IMAP4_SSL`
  - [x] Декодирование MIME-заголовков `From` → `(name, email)`
  - [x] Дедупликация по email
  - [x] Слияние с `senders_cache.json` (приоритет — registry)
  - [x] **БАГ ПОЧИНЕН:** удалён `_extract_from_from_envelope()`, используется только `BODY[HEADER.FIELDS (FROM)]`
  - [ ] Не запускался ни разу (артефакт `from_imap_only: 0` в кэше)
- [x] **1.3** Формат `senders_cache.json` соответствует плану

### Этап 2: Google People API — OAuth

- [ ] **2.1** Создание проекта в Google Cloud Console (**ручной шаг**)
  - [ ] Создать проект `mini-crm-contacts` на https://console.cloud.google.com/
  - [ ] Enable **Google People API** в `APIs & Services → Library`
  - [ ] Настроить **OAuth consent screen**:
    - User Type: **External**
    - App name: `mini-crm-contacts`
    - User support email: твой email
    - Scopes: `.../auth/contacts` (можно оставить пустым на этапе создания, потом добавить)
    - **Test users:** добавить email **жены** (с которого будут читаться её Google Contacts)
    - Publishing status: оставить **Testing** (этого хватит на 100 test users; токен будет жить 7 дней)
  - [ ] Создать OAuth 2.0 Client ID:
    - `Credentials → Create Credentials → OAuth client ID`
    - Application type: **Desktop app**
    - Name: `mini-crm-desktop`
    - Скачать JSON → положить в `config/google_credentials.json`
- [x] **2.2** Скрипт `scripts/google_auth_setup.py` создан
  - [x] OAuth flow через `InstalledAppFlow.run_local_server`
  - [x] Сохранение токена в `config/google_token.json`
  - [x] Автообновление токена по refresh_token
  - [x] Проверочный вызов `people.connections.list` (5 первых контактов)
  - [ ] Не запускался — нет credentials
- [ ] **2.3** Дополнить `.gitignore`:
  - [ ] `config/google_credentials.json`
  - [ ] `config/google_token.json`

### Этап 3: Сопоставление и обогащение

- [x] **3.1** Чтение Google Contacts (`fetch_google_contacts`)
  - [x] Пагинация через `pageToken`, размер страницы 500
  - [x] Throttling 0.2 сек между страницами
  - [x] Поля: `names, emailAddresses, phoneNumbers`
- [x] **3.2** Алгоритм мэтчинга
  - [x] Уровень 1: точное ФИО (фамилия + имя + отчество)
  - [x] Уровень 2: транслитерация точного ФИО (Иванов ↔ Ivanov)
  - [x] Уровень 3: фамилия + имя (без отчества)
  - [x] Уровень 4: только фамилия (если единственный кандидат)
  - [x] **БАГ ПОЧИНЕН:** `used_google_contacts` → `used_for_last_name_only`, уровни 1-3 разрешают несколько email на контакт
- [x] **3.3** Dry-run
  - [x] Таблица: Google-контакт | текущие email | добавляемый email | тип мэтча
  - [x] Статистика: добавим / пропустим / unmatched
  - [x] Добавлен флаг `--limit=N` и `--match-types=T1,T2`
- [x] **3.4** Запись обогащения
  - [x] `people.updateContact` с `updatePersonFields="emailAddresses"`
  - [x] Не перезаписывать существующие email (`action: skip_already_has`)
  - [x] Throttling 0.3 сек между запросами
  - [x] Подтверждение `yes/no` перед запуском
  - [x] Отчёт в `data/enrichment_report.json`
  - [x] **БАГ ПОЧИНЕН:** `phoneNumbers` убран из body `updateContact`
  - [ ] Не запускался

### Этап 4: CLI-оркестратор

- [x] **4.1** `scripts/enrich_google_contacts.py` создан
  - [x] Шаги: `extract`, `imap`, `auth`, `match`, `enrich`, `all`
  - [x] Помощь без аргументов
  - [x] Прерывание при ошибке шага в режиме `all`

### Зависимости / окружение

- [x] `google-api-python-client` в requirements.txt
- [x] `google-auth` в requirements.txt
- [x] **Добавить `google-auth-oauthlib>=1.2.0` в requirements.txt** (добавлено)
- [x] `python-dotenv` в requirements.txt

### Тесты ✅

- [x] `tests/test_google_enrichment.py` (47 тестов, все зелёные):
  - [x] `parse_fio` — 8 вариантов (full, two parts, initials, initials no space, last only, empty, double last name, imap same)
  - [x] `decode_from_header` — 6 вариантов (name+email, email only, empty, MIME-encoded, angle brackets, garbage)
  - [x] `_extract_from_from_header_response` — 4 варианта (tuple, bytes, no prefix, empty)
  - [x] `transliterate` — 4 варианта (basic, shch, yo, latin passthrough)
  - [x] `normalize_name` — 3 варианта (case, hyphen, extra spaces)
  - [x] `get_name_key` — 4 варианта (full, short, initials, last only)
  - [x] `match_senders_to_google` — 10 вариантов (level 1-4, no match, skip already has, multi-email same contact, level4 blocks reuse, level4 multiple candidates)
  - [x] `extract_senders_from_jsonl` — 7 вариантов (EMAIL key, EMAIL_GLOBAL, EMAIL_IN_ORG alias, partial email reconstruction, dedup longest fio, nonexistent file, skip non-CONTACT)

---

## Шаги дожима (V2 — что осталось сделать)

Порядок строгий — каждый шаг проверяется перед переходом дальше.

### Шаг A. Починить `extract_senders.py` (баг #1) ✅

- [x] Запустить ad-hoc анализ: пересечение org_gid EMAIL ↔ NAME_POSITION = 3 из 49. NAME_POSITION приходит через aliases, не через отдельные записи с тем же org_gid
- [x] Понять причину расхождения 98 vs ожидаемых ~600:
  - вариант (a): ✅ EMAIL_GLOBAL (8 записей) и EMAIL_IN_ORG алиасы не обрабатывались
  - вариант (b): ✅ 2 partial email (без `@`) отбрасывались — реконструированы через домен org_gid
- [x] Расширить алгоритм: EMAIL_GLOBAL, EMAIL_IN_ORG, partial email реконструкция
- [x] Перезапустить: 98 → 99 (EMAIL_GLOBAL оказались дубликатами EMAIL, 2 partial реконструированы). Реестр корректно содержит ~100 уникальных email
- [x] Обновить тесты на `parse_fio` — покрыто в `tests/test_google_enrichment.py`

### Шаг B. Зачистить `imap_sender_scan.py` ✅ (код), ⏳ (запуск)

- [x] Удалить нерабочий `_extract_from_from_envelope()`, сразу использовать `BODY[HEADER.FIELDS (FROM)]`
- [x] Уточнить документацию env: `IMAP_SERVER`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASSWORD` (как в codebase, **не** `IMAP_HOST/IMAP_PASS`)
- [x] Добавить `--folder=INBOX,Sent` для сканирования и Sent — там тоже могут быть отправители (а точнее, получатели = люди, с которыми переписывались)
- [x] Добавить чекпоинт `data/imap_scan_progress.json` чтобы можно было прервать и продолжить (на 19k писем это важно)
- [ ] Запустить сначала на 500 письмах: `python scripts/imap_sender_scan.py --max=500`
- [ ] Если ОК → запустить на полном архиве: `python scripts/imap_sender_scan.py --days=3650`

### Шаг C. Настроить Google OAuth (ручной шаг — нужны действия в браузере)

Инструкция, что я тебе подскажу когда дойдём:

1. **Открой** https://console.cloud.google.com/ под аккаунтом, с которого будешь администрировать (можно твой, не жены)
2. **Создай проект**: верхняя панель → выбор проекта → New Project → имя `mini-crm-contacts` → Create
3. **Подожди 30 сек**, пока проект подгрузится, переключись на него
4. **Включи People API**:
   - APIs & Services → Library → найти "Google People API" → Enable
5. **Настрой OAuth consent screen**:
   - APIs & Services → OAuth consent screen
   - User Type: **External** → Create
   - App name: `mini-crm-contacts`
   - User support email: твой email
   - Developer contact: твой email
   - Save & Continue
   - Scopes: пропустить (Save & Continue)
   - Test users: **Add users** → email **жены** (тот, с которым связаны Google Contacts на её телефоне) → Save & Continue
   - Summary → Back to Dashboard
6. **Создай Desktop OAuth Client**:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app**
   - Name: `mini-crm-desktop`
   - Create → появится popup → Download JSON
7. **Положи файл**: переименуй скачанный `client_secret_XXXX.json` → `config/google_credentials.json`
8. **Запусти**: `python scripts/google_auth_setup.py`
   - Откроется браузер
   - **Логинься аккаунтом жены** (это критично — не своим!)
   - Появится "Google hasn't verified this app" → Advanced → Go to mini-crm-contacts (unsafe)
   - Разреши доступ к контактам
   - Браузер скажет "The authentication flow has completed"
   - В терминале увидишь "✅ Авторизация успешна" + 5 первых её контактов

Чек-листом:

- [x] Проект создан в Google Cloud Console
- [x] Google People API включён
- [x] OAuth consent screen настроен (External, Testing, test user = email жены)
- [x] OAuth Client ID создан (Desktop app)
- [x] `config/google_credentials.json` положен
- [x] `python scripts/google_auth_setup.py` отработал, `config/google_token.json` создан
- [x] Тест-вывод показал реальные контакты жены (4389 контактов)

### Шаг D. Починить `google_contacts_enrich.py` (баги #5, #6) ✅

- [x] Убрать `used_google_contacts` для уровней 1-3 → переименован в `used_for_last_name_only`
- [x] Оставить `used_google_contacts` **только для уровня 4** (last-name-only) — `used_for_last_name_only`
- [x] Не передавать `phoneNumbers` в body `updateContact`
- [x] Добавить флаг `--limit=N`
- [x] Добавить флаг `--match-types=exact_fio,translit_fio`
- [x] **Доп. фикс:** уровень 2 (translit) теперь проверяет и `google_by_key` — латинские Google-контакты мэтчатся с кириллическими sender'ами

### Шаг E. Сухой прогон и верификация ⏳

- [x] `python scripts/google_contacts_enrich.py --dry-run` → выполнен
- [x] Результаты v2 (после фикса bilalov): 67 мэтчей, 64 добавления, 3 пропуска, 355 unsent, 4287 ungoogle
- [x] Фикс `extract_senders.py`: ФИО из собственных алиасов, не из org_gid-котла (bilalov → Билалов, не Клочкова)
- [x] IMAP-скан перезапущен: 422 отправителя (99 реестр + 323 IMAP)

### Шаг E1. Markdown-отчёт для сверки с женой ⏳

- [x] Создан `scripts/match_report.py` — генерация Markdown из `match_results.json`
- [x] Сортировка: приоритетные контакты dna → остальные dna → все остальные
- [x] Эмодзи-маркировка типов мэтча: 🟢 точное ФИО, 🔵 транслит, 🟡 фамилия+имя, 🔴 только фамилия
- [x] Отчёт сгенерирован: `data/match_report.md`
- [x] **Фикс: Google Contacts хранит ФИО криво** — familyName/givenName перепутаны. Решение: `alt_name_parts` из `displayName` + дедупликация кандидатов
- [x] **Фикс опечатки**: "эллина" → "элина" (Тишкова)
- [x] **Фикс дубликатов**: разрешаем last_first_only при дубликатах с одинаковым displayName
- [x] **Результаты v4**: **160 мэтчей**, 146 добавлений, 14 пропусков, 262 unsent
- [x] **new_contacts.json**: 218 контактов для создания (только люди, без ООО)
  - [x] Ивахнишина удалена (уже есть в Google)
  - [x] Чурочкина: добавлен email `torgi@dna-technology.ru`
  - [x] Шевырев: без email (введём позже)
- [x] ⏳ **ШАГ E1: Жена сверяет отчёт** `data/match_report.md`
  - [x] Особое внимание 🔴 `last_name_only` — опасные мэтчи ("Андрей", "Сергей", "Лаборатория", "МТС", "Юрий") - исключили и мэтча.
  - [x] Проверить: `medical@dna-technology.ru` → Иванова Анастасия (общая почта?) - да!
  - [x] Ложные мэтчи — записывай прямо в Markdown или сообщи мне
  - [x] Если есть отбраковки — я исключу их из JSON и перегенерирую
- [x] ⏳ Приоритетные, всё ещё не мэтчащиеся: Жданова (другой человек в Google), Иващук, Гоголева (нет в Google)
- [x] Если есть ложные мэтчи — фикси логику (шаг D), потом повтори dry-run + отчёт

📄 **Документация**: см. `README.md` в этой папке — описание всех модулей, файлов данных, зависимостей и типового рабочего процесса для интеграции в основной проект.

### Шаг E2. Нормализация ФИО + обогащение (комбо) ✅

**Основной скрипт: `scripts/enrich_and_normalize.py`**
- Объединяет обогащение email + нормализацию ФИО (familyName, givenName, middleName) в один проход
- middleName добавляется при пустом поле или только капитализации
- Организации фильтруются автоматически

**Точечный скрипт: `scripts/enrich_specific.py`**
- Для конкретных email (использует `searchContacts` по фамилии)
- Исправлен middleName-логика (добавляет при пустом поле)

**Результат точечного обогащения (5 контактов):**
- [x] Сучкова Наталья Александровна — familyName/givenName/middleName исправлены
- [x] Тишкова Элина — email добавлен
- [x] Ткаченко Виктория Олеговна — familyName/givenName перепутаны → исправлено, middleName добавлено
- [x] Фетисова Ирина Николаевна — уже корректна
- [x] Шпинькова Виктория Николаевна — email добавлен, middleName добавлено

### Шаг E2a. Нормализация ФИО в Google Contacts ✅

- [x] Создан `scripts/normalize_google_names.py`
- [x] Проверяет: familyName=Фамилия, givenName=Имя, middleName=Отчество
- [x] Обновляет только при явно перепутанных или пустых полях
- [x] `python scripts/normalize_google_names.py --update` — **4 контакта обновлено**:
  - [x] Кристина Бешатта (перепутаны familyName/givenName)
  - [x] Месмер Инесса (пустая фамилия)
  - [x] Егорова Татьяна (пустая фамилия)
  - [x] Олег Исаев (middleName капитализация)

### Шаг F. Точечный enrich (5 контактов для проверки на телефоне) ✅

- [x] `python scripts/enrich_specific.py --update` — 5 контактов обогащены
- [x] `python scripts/add_middle_names.py --update` — отчества добавлены
- [x] Ручная проверка в Google Contacts UI — подтверждено

### Шаг F1. Полный enrich + нормализация ✅

- [x] `python scripts/google_contacts_enrich.py --enrich --match-types=exact_fio,translit_fio,last_first_only` — **125 контактов**
- [x] `python scripts/enrich_and_normalize.py --update` — **54 контакта** ФИО нормализовано
- [x] Добавлена логика: отчество в familyName → перестановка, middleName при пустом поле
- [x] Исправлен body: передаём полные names (все 3 поля), иначе Google создаёт дубли
- [x] Добавлен retry при rate limit (429) и BrokenPipe

**Проблема обнаружена**: Google API создавал дубли при обновлении (передавались не все поля names).
Исправлено, но已有 дубли нужно почистить (шаг K).

### Шаг K. Дедупликация и объединение Google Contacts 🔴

**Проблема**: Google Contacts содержит ~1012 дублей (по данным Google UI) + дубли от нашего enrich.
Один контакт может иметь: полное ФИО в одном дубле + email/телефон в другом.

**Подзадачи**:

#### K1. Генерация отчёта о дублях (dry-run) ✅
- [x] Создан `scripts/google_contacts_dedup.py` — скрипт дедупликации
- [x] Загрузить все Google Contacts, сгруппировать по фамилии+имени
- [x] Фильтр: только реальные дубли (общий email/телефон или пустой дубль)
- [x] Генерировать Markdown-отчёт `data/dedup_report.md`
- [x] Пользователь ревьюит отчёт → подтверждает/правит

#### K2. Объединение дублей ✅
- [x] Логика объединения (merge):
  - **Мастер-контакт**: тот, у кого больше данных (email + телефон + org)
  - **Слейв-контакт**: переносим недостающие данные в мастер, затем удаляем
  - emailAddresses: объединяем (без дублей email)
  - phoneNumbers: объединяем (без дублей номеров)
  - organizations: берём из мастера
- [x] `python scripts/google_contacts_dedup.py --merge` — авто-объединение (51 группа) ✅
- [x] `python scripts/google_contacts_dedup.py --merge --all` — полный merge (304 группы) ✅
- [x] Rate limit: пауза 30с каждые 50 операций, retry на 429/BrokenPipe (3 попытки)
- [x] `--skip=N` для resume после краша
- [x] Результат: 304 группы объединены, 0 ошибок

#### K3. Очистка мусорных дублей (от enrich) ✅
- [x] Создан `scripts/dedup_and_fix.py` — удаляет дубли без данных, обновляет ФИО
- [x] Создан `scripts/cleanup_patronymic_duplicates.py` — удаляет контакты где displayName = отчество
- [x] Запущено: 51 пустой дубль удалён (auto-merge)

### Шаг L. Нормализация телефонов в Google Contacts ✅

**Цель**: привести все телефоны в Google Contacts к единому формату + типу (мобильный/городской).

**Переиспользуем**: `src/postprocessing/phone_normalizer.py` (PhoneNormalizer) — уже есть в проекте.

#### L1. Анализ телефонов ✅
- [x] Создан `scripts/google_contacts_phone_normalize.py` (отчёт + обновление)
- [x] Загрузить все Google Contacts с phoneNumbers
- [x] Для каждого телефона: нормализовать через PhoneNormalizer
- [x] Генерировать отчёт `data/phone_report.md`:
  - Контакт | Было | Стало | Тип | Доб.
- [x] Статистика: 4111 контактов, 3843 с телефонами (4788 номеров), 4620 требуют изменений
  - мобильных: 3168, неизвестных: 1508, коротких: 68, городских: 44

#### L2. Обновление телефонов ✅
- [x] Создан `scripts/google_contacts_phone_normalize.py` (--report / --update / --dedup-phones)
- [x] Для каждого контакта: обновить phoneNumbers нормализованными значениями
- [x] Тип телефона → Google phone type (mobile/work/home)
- [x] Формат отображения: `+7 (XXX) XXX-XX-XX`
- [x] `--report` / `--update` / `--dedup-phones` режимы
- [x] Rate limit: пауза 0.5с между операциями, 30с каждые 50, retry на 429/BrokenPipe
- [x] Запущен `--update`: 3087 обновлено, 10 ошибок, 482 без изменений

### Шаг M. Фикс ФИО в Google Contacts ✅

**Цель**: исправить перепутанные Фамилия/Имя, КАПС, отчество в неправильных полях, пустое имя.

#### M1. Анализ и отчёт ✅
- [x] Создан `scripts/google_contacts_export.py` — экспорт контактов с анализом ФИО
- [x] Детекция проблем: перепутаны Ф/И, отчество в фамилии/имени, КАПС, пустое имя, имя в отчестве
- [x] Словарь русских имён `RU_NAMES` для детекции перепутанных Ф/И
- [x] Генерация Markdown + CSV отчётов с проблемами и решениями

#### M2. Автофикс ✅
- [x] Создан `scripts/google_contacts_fix_names.py` (--report / --update / --skip=N)
- [x] Исправляет: перепутаны Ф/И, КАПС, отчество в fn/gn, пустое имя (fn=Имя+Фамилия), имя в mn
- [x] НЕ трогает: пустая фамилия (нет данных), displayName ≠ ФИО (не критично)
- [x] Прогон 1: 2074 контакта — перепутаны/отчество/КАПС/пустое имя → 0 ошибок (3 ошибки)
- [x] Прогон 2: 443 контакта — перепутаны по словарю/имя в mn/КАПС → 440 обновлено, 3 ошибки
- [x] Итого исправлено: ~2514 контактов

#### M3. Результат
- Было проблем: 3174 из 3214
- Стало проблем: 1473 из 2793 (пустая фамилия + displayName ≠ ФИО с org/должностями)
- Перепутанных Ф/И: 0 (было 1354)
- Отчеств в неправильных полях: 0 (было 720)
- КАПС: 3 (было 192)
- fn==gn дублей: 0 (было 599)
- displayName порядок: Фамилия Имя Отчество (было хаотичный)

### Шаг G. Полный enrich (повтор после дедупа)

- [ ] После завершения K, L, M — перезапустить `enrich_and_normalize.py --update`
- [ ] Проверить `data/enrichment_report.json` — нет ли ошибок
- [ ] Жена проверяет несколько контактов в Aquamail

### Шаг M4. Фикс fn==gn дублей ✅

**Проблема**: предыдущий автофикс (M2) создал дубли — familyName скопирован в givenName.
Например: fn='Надежда', gn='Надежда', mn='Мергеноловна' — 599 контактов.

- [x] Создан `scripts/google_contacts_fix_fn_gn_dup.py` (--report / --update)
- [x] Логика: извлечение имени из middleName (если «Имя Отчество»), очистка gn если fn=имя
- [x] Прогон: 599 обновлено, 0 ошибок
- [x] Результат: fn==gn дублей = 0

### Шаг M5. Фикс displayName ✅

**Проблема**: displayName не обновляется автоматически при изменении familyName/givenName/middleName.
Также: КАПС в displayName, дублирование слов, разный порядок.

- [x] Создан `scripts/google_contacts_fix_displaynames.py` (--report / --update)
- [x] Порядок: **Фамилия Имя Отчество** (единообразно для всех)
- [x] Детекция: КАПС, дублирование слов, неправильный порядок
- [x] Skip: контакты с лишними словами в displayName (должности, org)
- [x] Прогон 1: 647 обновлено (порядок Имя Отчество Фамилия)
- [x] Прогон 2: 926 обновлено (после fn==gn фикса)
- [x] Прогон 3: 865 обновлено (порядок → Фамилия Имя Отчество)
- [x] Прогон 4: 10 обновлено (КАПС + дубли)
- [x] Результат: displayName единообразный, порядок Фамилия Имя Отчество

### Шаг M6. Фикс mixed layout ✅

**Проблема**: латинские буквы в русских словах (AЛЕКСАНДРА) — визуально КАПС, но не детектируется.

- [x] Добавлена `fix_mixed_layout()` в `google_contacts_fix_names.py`
- [x] Применяется только если слово преимущественно русское (russian_count > latin_other_count)
- [x] Откат сломанных контактов через `scripts/rollback_mixed_layout.py` (10 восстановлено)
- [x] Результат: 1 контакт исправлен (AЛЕКСАНДРА → Александра), 10 нормальных откачены

### Шаг H. Документация и закрытие

- [x] Создать `docs/google-contacts-enrichment/README.md` — короткая инструкция как пере-запустить (например через год, когда добавятся новые контакты)
- [ ] Создать `docs/google-contacts-enrichment/RUNBOOK.md`:
  - как переавторизоваться через 7 дней (просто перезапустить `auth`)
  - как откатить обогащение (см. I)
  - как добавить нового sender вручную в `senders_cache.json` (формат записи)
- [x] Добавить `google-auth-oauthlib>=1.2.0` в `requirements.txt`
- [x] Закоммитить, проверить что `config/google_credentials.json` и `config/google_token.json` НЕ попали в коммит

### Шаг I. Скрипт отката (страховка)

- [ ] Создать `scripts/google_contacts_rollback.py`:
  - читает `data/enrichment_report.json`
  - для каждого `details[i].status == "success"`:
    - получает контакт по `resource_name`
    - удаляет email == `added_email` из `emailAddresses`
    - пишет назад через `updateContact`
  - формирует `data/rollback_report.json`
- [ ] Не обязателен на первом проходе, но **сильно желателен** перед шагом G

### Шаг J. Тесты ✅

- [x] `tests/test_google_enrichment.py` (47 тестов, все зелёные):
  - [x] `parse_fio` — 8 вариантов
  - [x] `decode_from_header` — 6 вариантов
  - [x] `transliterate` — 4 варианта (basic, shch, yo, latin passthrough)
  - [x] `get_name_key` — 4 варианта
  - [x] `match_senders_to_google` — 10 вариантов (все 4 уровня + multi-email + edge cases)
  - [x] `extract_senders_from_jsonl` — 7 вариантов (EMAIL_GLOBAL, EMAIL_IN_ORG, partial, dedup)

---

## Структура файлов (актуальная)

```
docs/google-contacts-enrichment/
  PLAN.md                                 # архив V1 (помечен как outdated)
  PLAN_V2.md                              # этот документ
  README.md                               # как пере-запускать
  RUNBOOK.md                              # переавторизация, откат

scripts/
  extract_senders.py                      ✅ баг #1 починен
  imap_sender_scan.py                     ✅ баг #4 починен, не запускался
  google_auth_setup.py                    ✅ создан, не запускался (нет credentials)
  google_contacts_enrich.py               ✅ баги #5, #6 починены, + translit фикс
  enrich_google_contacts.py               ✅ создан (CLI-оркестратор)
  enrich_and_normalize.py                 ✅ **основной скрипт** (комбо: email + ФИО)
  enrich_specific.py                      ✅ точечное обогащение конкретных email
  normalize_google_names.py               ✅ отдельная нормализация ФИО
  add_middle_names.py                     ✅ добавление отчеств
  dedup_and_fix.py                        ✅ дедупликация + фикс ФИО (searchContacts)
  cleanup_patronymic_duplicates.py        ✅ удаление мусорных дублей (отчество как displayName)
  match_report.py                         ✅ генерация Markdown-отчёта мэтчей
  quick_name_check.py                     ✅ быстрый отчёт ФИО (searchContacts)
  name_changes_report.py                  ✅ полный отчёт было→стало (грузит все контакты)
  create_missing_contacts.py              ✅ создание новых контактов из шаблона
  update_phones.py                        ✅ обновление телефонов по email/имени
  google_contacts_dedup.py                ✅ K: дедуп + merge (304 группы объединены)
  google_contacts_phone_normalize.py      ✅ L: нормализация телефонов (3087 обновлено)
  google_contacts_export.py               ✅ M: экспорт + анализ ФИО
  google_contacts_fix_names.py            ✅ M: автофикс ФИО (~2514 исправлено)
  google_contacts_fix_fn_gn_dup.py       ✅ M4: фикс fn==gn дублей (599 исправлено)
  google_contacts_fix_displaynames.py    ✅ M5: фикс displayName (порядок ФИО, КАПС, дубли)
  rollback_mixed_layout.py               ✅ M6: откат сломанных mixed-layout контактов
  google_contacts_rollback.py             ❌ ещё не написан (страховка)

config/
  google_credentials.json                 ❌ нужно скачать вручную
  google_token.json                       ❌ создастся при первой авторизации

data/
  senders_cache.json                      ✅ есть (422 записи: 99 реестр + 323 IMAP)
  match_results.json                      ✅ создан (160 мэтчей)
  enrichment_report.json                  ✅ создан (125 обогащено)
  imap_scan_progress.json                 ❌ создастся для возобновления IMAP-скана
  contacts_export_problems.md             ✅ M: отчёт проблем ФИО
  contacts_export.csv                     ✅ M: CSV экспорт
  fix_fn_gn_dup_report.md                 ✅ M4: отчёт fn==gn дублей
  fix_names_report.md                     ✅ M: отчёт автофикса ФИО

tests/
  test_google_enrichment.py               ✅ 47 тестов (все зелёные)
```

---

## Риски и mitigation (обновлено)

| Риск | Mitigation в V2 |
|------|----------------|
| 98 senders вместо ~600 | Шаг A — отладка `extract_senders.py`, добавление IMAP-добора через шаг B |
| ENVELOPE-парсер сломан → 2x медленнее | Шаг B — переход только на `BODY[HEADER]` |
| Один Google-контакт ↔ много email теряется | Шаг D — убрать `used_google_contacts` для уровней 1-3 |
| Ложные срабатывания last-name-only | Шаг E — отдельный визуальный ревью; шаг G — раскатывать отдельно |
| Случайно перезаписали 100+ контактов мусором | Шаг F — `--limit=5` пилотный прогон + шаг I — скрипт отката |
| OAuth токен истекает через 7 дней (Testing mode) | RUNBOOK: повторный `auth` (1 минута) при необходимости |
| API quota 300 req/min | Throttling 0.3 сек уже есть, плюс batched read через `connections.list` (500 за запрос) |
| credentials.json/token.json утекут в git | Дополнить `.gitignore` (шаг 2.3), проверить перед коммитом |

---

## Команды для быстрого старта (V2)

```bash
# 0. Подготовка (один раз)
echo "config/google_credentials.json" >> .gitignore
echo "config/google_token.json" >> .gitignore
pip install google-auth-oauthlib

# A. Починить extract (после фикса бага #1)
python scripts/extract_senders.py
jq '.stats' data/senders_cache.json   # должно быть >>98

# B. IMAP-добор (после фикса бага #4)
python scripts/imap_sender_scan.py --max=500     # пилот
python scripts/imap_sender_scan.py --days=3650   # полный

# C. OAuth (вручную в Google Console + потом)
python scripts/google_auth_setup.py

# E. Dry-run
python scripts/google_contacts_enrich.py --dry-run

# F. Пилот на 5 контактах
python scripts/google_contacts_enrich.py --enrich --limit=5 --match-types=exact_fio

# G. Полный прогон
python scripts/google_contacts_enrich.py --enrich --match-types=exact_fio,translit_fio,last_first_only
```

---

## Итог ревью V1 → V2

V1 как высокоуровневый план — хороший, скрипты по нему написаны корректно по структуре. Но реальный прогон выявит описанные 12 проблем. V2 — это пошаговый дожим: сначала чиним баги (A, B, D), потом проходим OAuth-настройку (C), потом сухой прогон с верификацией (E), пилотный enrich на 5 контактах (F), полный (G), и закрываем документацией и страховкой (H, I, J).

Главное: **не запускать `--enrich` без шага D** (баг с `used_google_contacts`), иначе у людей с двумя email второй email не добавится.
