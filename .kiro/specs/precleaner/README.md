# precleaner package (MVP)

## Состав
- `LM-Agent-Preclean-Instructions.md` — укороченная версия ТЗ.
- `discover_patterns.py` — пакетный анализ 4-месячного массива писем (поиск повторов).
- `precleaner/`
  - `core.py` — ядро пред-очистки.
  - `cli.py` — CLI (`run`, `discover`, `eval`).
  - `config.yaml` — дефолтные настройки.

## Быстрый старт
```bash
# 1) Анализ паттернов
python discover_patterns.py --infile emails.ndjson --out ./reports --limit 10000

# 2) Пред-очистка датасета
python -m precleaner.cli run --infile emails.ndjson --out clean.ndjson

# 3) (Опционально) Обёртка discover из пакета
python -m precleaner.cli discover --infile emails.ndjson --out ./reports
```

### Формат `emails.ndjson`
По строке на письмо:
```json
{"message_id":"...", "thread_id":"...", "from":"alice@example.com", "date":"2025-09-01T10:00:00Z", "body_text":"...", "attachments":[...]}
```

## Примечания
- Зависимости — стандартная библиотека Python 3.9+.
- Метрики `eval` заглушены — подключите свою проверку извлечения сущностей.
