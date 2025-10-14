# Tasks

- [x] Подготовить миграцию SQLite: создать таблицы `attachments`, `attachment_events`, индексы.
- [x] Реализовать `attachments_repository.py` с методами insert/get/deduplicate и хелпером `log_event`.
- [x] Обновить `AttachmentRegistry` для работы с SQLite, расчёта SHA-256 и учёта дубликатов.
- [x] Добавить CLI/скрипты: `attachments_deduplicate.py`, `attachments_orphans.py`, `attachments_audit.py`.
- [x] Обновить unit-тесты/интеграционные тесты fetcher для нового реестра (добавлен unit-тест репозитория и регистратора).
- [x] Запустить очистку орфанных файлов (`python -m src.cli.attachments_orphans --move`) и дедупликацию (`python -m src.cli.attachments_deduplicate`).
- [x] Перенести CLI запуска fetcher (`python -m src.cli.email_fetcher_cli`).
- [x] Очистить каталоги `data/emails` и `data/attachments`, выполнить тестовые прогоны за 2025-07-28 и 2025-07-29, убедиться в корректности данных.
- [x] Добавить reconciliation статусов вложений при чтении JSON (обновление `status`/`reason`, повторная маркировка исключений).
- [x] Автоматически пересохранять JSON писем после reconciliation (`needs_resync` для сценария `skip_all`).
- [x] Очистить каталоги `data/emails` и `data/attachments`, запустить чистую загрузку за 2025-05-05…2025-10-07.
- [ ] Провести пост-обработку: аудит записей, выборочная проверка вложений, отчет.
