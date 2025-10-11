# План реализации SQLite-реестра вложений

## 🎯 Общие принципы
- Источник истины по вложениям — SQLite (`crm.db`).
- Каждый файл сохраняется один раз; дубли ищутся по SHA-256.
- Файловая система остаётся простым стореджем, метаданные и связи — в БД.
- Журнал событий фиксирует любые операции с вложениями для аудита.

---

## 1. Схема БД
- **Таблица `attachments`**
  - `id` INTEGER PK AUTOINCREMENT
  - `message_id` TEXT NOT NULL  → индекс + внешний ключ на будущую таблицу писем
  - `thread_id` TEXT NULL (для обратной совместимости)
  - `email_date` TEXT NOT NULL (YYYY-MM-DD)
  - `original_name` TEXT NOT NULL
  - `stored_name` TEXT NOT NULL UNIQUE
  - `content_type` TEXT
  - `file_size` INTEGER
  - `sha256` TEXT NOT NULL
  - `is_inline` INTEGER(0/1) DEFAULT 0
  - `status` TEXT DEFAULT 'saved'  (saved / excluded / duplicate / error)
  - `saved_at` TEXT DEFAULT CURRENT_TIMESTAMP
- **Индексы и ограничения**
  - UNIQUE(`message_id`, `original_name`)
  - UNIQUE(`message_id`, `sha256`)
  - INDEX `idx_attachments_sha256` (`sha256`)
  - INDEX `idx_attachments_message_date` (`message_id`, `email_date`)
  - `FOREIGN KEY(message_id)` → `emails(message_id)` (когда таблица появится)
- **Таблица `attachment_events`**
  - `id` INTEGER PK AUTOINCREMENT
  - `attachment_id` INTEGER NOT NULL REFERENCES attachments(id) ON DELETE CASCADE
  - `event_type` TEXT NOT NULL (created/duplicate_skipped/excluded/deleted/error)
  - `payload` TEXT NULL (JSON blob)
  - `process` TEXT NULL (fetcher/batch/deduper)
  - `occurred_at` TEXT DEFAULT CURRENT_TIMESTAMP
- **Вспомогательная таблица `attachment_hash_cache`** (опционально, если нужно хранить хеши до записи в основную таблицу)

## 2. Интеграция с fetcher
- Обновить `AttachmentRegistry`:
  1. После фильтров и перед сохранением считать SHA-256 payload’а.
  2. Проверять наличие записи с `message_id + sha256`:
     - **Есть** → не сохранять файл, создать `attachment_events` (duplicate_skipped) и вернуть метаданные существующего файла.
     - **Нет** → сохранить файл как сейчас, но имя брать из `_create_safe_filename` (можно оставить текущую схему), затем вставить строку в `attachments` и событие `created`.
  3. После успешной записи добавлять запись в JSON письма (для обратной совместимости) и возвращать ссылку из БД.
  4. Если файл исключён правилом — писать событие `excluded` с причиной в `payload`.
- В точках чтения (`get_attachments_for_message`, `check_email_processing_status`) брать данные из таблицы `attachments`, JSON использовать как fallback.
- Добавить асинхронный/синхронный слой БД (SQLAlchemy или легковесный репозиторий) внутри `src/fetcher/storage/`.

## 3. Дедупликация и очистка
- CLI `python -m src.cli.attachments_deduplicate`:
  - Идёт по группам `sha256` → если одна запись, пропускает.
  - Если несколько — выбирает «главную» (обычно самую раннюю), на остальные создаёт событие `duplicate_removed`, удаляет файл и обновляет STATUS = 'duplicate'.
- CLI `python -m src.cli.attachments_orphans`:
  - Сканирует папки `data/attachments/<date>` и ищет файлы, которых нет в БД → перемещает в `data/attachments/orphans/` и логирует.
- Все сервисные скрипты используют те же репозитории и события.

## 4. Журнал операций
- Ввести хелпер `log_event(attachment_id, type, payload=None, process='fetcher')`.
- Вызывать его при:
  - сохранении нового файла
  - пропуске дубликата
  - исключении/ошибке
  - ручном удалении/чистке
- CLI `python -m src.cli.attachments_audit --message-id <...> [--attachment-id ...]` выводит хронологию событий.

## 5. Интеграция с CRM / Drizzle
- Создать отдельный модуль доступа к БД (`src/db/attachments_repository.py`).
- На стороне CRM (Drizzle) использовать ту же SQLite (`crm.db`) → достаточно импортировать схемы, построить Drizzle-модели `attachments` и `attachment_events`.
- В будущем, если появится общая таблица emails, добавить внешний ключ; Drizzle легко мигрируется на Postgres при расширении.

## 6. Перезагрузка писем
1. Очистить `data/emails` и `data/attachments` (бэкап уже есть).
2. Применить миграции/DDL (`python scripts/db_init.py`).
3. Использовать CLI `python -m src.cli.email_fetcher_cli --start-date ... --end-date ...`: сначала точечные проверки (`--date 2025-07-28`, `--date 2025-07-29`), затем полный диапазон `2025-05-05` – `2025-10-07`.
4. После загрузки: провести выборочные проверки (`attachments` vs. фактические файлы), использовать аудит CLI.

---

## Ответ на вопрос про миграцию
- Поскольку планируется «чистая» перезагрузка писем, отдельный этап миграции старых вложений не требуется: новые загрузки сформируют таблицу `attachments` с корректными связями и хешами.
- Миграционный скрипт можно оставить в backlog для случаев, если понадобится подтянуть архивные вложения без повторной загрузки.

## Дальнейшие расширения (backlog)
- Автоматический экспорт вложений в S3 / объектное хранилище.
- UI-страницы в CRM для просмотра событий и состояния вложений.
- Асинхронная обработка: расчёт SHA-256 потоково или в фоне, если размеры файлов увеличатся.
