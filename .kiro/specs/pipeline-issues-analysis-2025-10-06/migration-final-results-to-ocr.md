# План миграции: data/final_results → data/ocr

## Обзор

**Цель:** Переименовать папку `data/final_results` в `data/ocr` для улучшения читаемости и понятности структуры проекта.

**Текущая структура:**
```
data/
├── final_results/
│   ├── texts/          # OCR результаты в .txt
│   │   └── YYYY-MM-DD/
│   └── reports/        # Отчёты OCR процессора
│       └── YYYY-MM-DD/
```

**Новая структура:**
```
data/
├── ocr/
│   ├── texts/          # OCR результаты в .txt
│   │   └── YYYY-MM-DD/
│   └── reports/        # Отчёты OCR процессора
│       └── YYYY-MM-DD/
```

---

## Затронутые модули

### 1. **src/ocr_processor.py** (КРИТИЧЕСКИЙ)
```python
# Строка 72-75
self.base_results_dir = self.data_dir / "final_results"  # ← ИЗМЕНИТЬ
self.texts_dir = self.base_results_dir / "texts"
self.reports_dir = self.base_results_dir / "reports"
```

### 2. **src/file_tokens.py** (КРИТИЧЕСКИЙ)
```python
# Строка 42
self.final_results_path = self.base_path / "final_results" / "texts"  # ← ИЗМЕНИТЬ

# Строка 114-128 - get_available_dates()
# Строка 278-281 - _find_ocr_file()
# Строка 347-349 - _process_date()
# Строка 529-531 - подсчёт OCR файлов
```

### 3. **src/postprocessing/attachment_evidence_extractor.py** (ВЫСОКИЙ)
```python
# Строка 214
ocr_text_path = Path(f"data/final_results/texts/{date_folder}/{txt_filename}")  # ← ИЗМЕНИТЬ

# Строка 287
ocr_text_path = Path(f"data/final_results/texts/{formatted_date}/{filename}")  # ← ИЗМЕНИТЬ
```

### 4. **scripts/commercial_proposal_collector/*.* (СРЕДНИЙ)
**scripts/commercial_proposal_collector.py (СРЕДНИЙ)
ТОЧНЕЕ ПРОВЕРЬ НА КАКИЕ ФАЙЛЫ ВЛИЯЕТ!



### 5. **Документация** (СРЕДНИЙ)
- `src/README_file_tokens.md` - строка 68
- `src/postprocessing/README_postprocessing.md` - строка 1329
- `.kiro/specs/attachment-evidence-org-location/README.md` - строки 49, 132
- `memory-bank/` - множество файлов (не критично)

---

## План безопасной миграции

### Фаза 1: Подготовка (30 минут)

#### Шаг 1.1: Создать резервную копию
```bash
# Создать backup текущей структуры
cp -r data/final_results data/final_results_backup_$(date +%Y%m%d_%H%M%S)

# Проверить размер
du -sh data/final_results
du -sh data/final_results_backup_*
```

#### Шаг 1.2: Проверить текущее состояние
```bash
# Подсчитать файлы
find data/final_results/texts -type f -name "*.txt" | wc -l
find data/final_results/reports -type f | wc -l

# Проверить последние изменения
ls -lt data/final_results/texts/*/  | head -20
```

#### Шаг 1.3: Создать конфигурационный файл
```python
# config/paths.py (НОВЫЙ ФАЙЛ)
from pathlib import Path

class DataPaths:
    """Централизованная конфигурация путей к данным"""
    
    BASE_DIR = Path("data")
    
    # OCR результаты
    OCR_DIR = BASE_DIR / "ocr"  # Новое название
    OCR_TEXTS_DIR = OCR_DIR / "texts"
    OCR_REPORTS_DIR = OCR_DIR / "reports"
    
    # Для обратной совместимости (временно)
    LEGACY_FINAL_RESULTS_DIR = BASE_DIR / "final_results"
    
    @classmethod
    def migrate_if_needed(cls):
        """Автоматическая миграция при первом запуске"""
        if cls.LEGACY_FINAL_RESULTS_DIR.exists() and not cls.OCR_DIR.exists():
            import shutil
            print(f"🔄 Миграция: {cls.LEGACY_FINAL_RESULTS_DIR} → {cls.OCR_DIR}")
            shutil.move(str(cls.LEGACY_FINAL_RESULTS_DIR), str(cls.OCR_DIR))
            print("✅ Миграция завершена")
```

---

### Фаза 2: Обновление кода (1-2 часа)

#### Шаг 2.1: Обновить ocr_processor.py
```python
# src/ocr_processor.py

# БЫЛО:
self.base_results_dir = self.data_dir / "final_results"

# СТАЛО:
from config.paths import DataPaths
DataPaths.migrate_if_needed()  # Автомиграция
self.base_results_dir = DataPaths.OCR_DIR
```

#### Шаг 2.2: Обновить file_tokens.py
```python
# src/file_tokens.py

# БЫЛО:
self.final_results_path = self.base_path / "final_results" / "texts"

# СТАЛО:
from config.paths import DataPaths
DataPaths.migrate_if_needed()
self.final_results_path = DataPaths.OCR_TEXTS_DIR

# Также обновить все упоминания в методах:
# - get_available_dates() - строка 124
# - _find_ocr_file() - строка 278
# - _process_date() - строка 347
# - подсчёт файлов - строка 529
```

#### Шаг 2.3: Обновить attachment_evidence_extractor.py
```python
# src/postprocessing/attachment_evidence_extractor.py

# БЫЛО:
ocr_text_path = Path(f"data/final_results/texts/{date_folder}/{txt_filename}")

# СТАЛО:
from config.paths import DataPaths
ocr_text_path = DataPaths.OCR_TEXTS_DIR / date_folder / txt_filename

# Аналогично для строки 287
```

#### Шаг 2.4: Обновить документацию
```bash
# Автоматическая замена в документации
find . -name "*.md" -type f -exec sed -i '' 's/final_results/ocr/g' {} +

# Проверить изменения
git diff --name-only | grep "\.md$"
```

---

### Фаза 3: Физическая миграция (5-10 минут)

#### Вариант A: Автоматическая миграция (РЕКОМЕНДУЕТСЯ)
```python
# Добавить в начало main скриптов
from config.paths import DataPaths
DataPaths.migrate_if_needed()
```

Это автоматически переименует папку при первом запуске.

#### Вариант B: Ручная миграция
```bash
# Переименовать папку
mv data/final_results data/ocr

# Проверить
ls -la data/ocr/
ls -la data/ocr/texts/
ls -la data/ocr/reports/
```

---

### Фаза 4: Тестирование (30-60 минут)

#### Тест 1: Проверка OCR процессора
```bash
# Запустить OCR процессор на тестовой дате
python src/ocr_processor.py

# Проверить, что файлы создаются в data/ocr/texts/
ls -la data/ocr/texts/2025-07-29/
```

#### Тест 2: Проверка file_tokens
```bash
# Запустить подсчёт токенов
python src/file_tokens.py

# Проверить, что OCR файлы находятся
# Проверить отчёт в data/file_tokens/
```

#### Тест 3: Проверка attachment_evidence_extractor
```bash
# Запустить обработку письма с вложениями
python -c "
from src.postprocessing.attachment_evidence_extractor import AttachmentEvidenceExtractor
extractor = AttachmentEvidenceExtractor()
# Тестовый запуск
"
```

#### Тест 4: Проверка Pipeline
```bash
# Запустить полный pipeline на 1-2 письмах
python api_pipeline_validator.py
# Выбрать дату 2025-07-29, первые 2 письма
```

---

### Фаза 5: Очистка (10 минут)

#### После успешного тестирования:
```bash
# Удалить backup (если всё работает)
rm -rf data/final_results_backup_*

# Удалить старые упоминания из .gitignore
sed -i '' 's/final_results/ocr/g' .gitignore

# Коммит изменений
git add .
git commit -m "Migrate: data/final_results → data/ocr for better clarity"
```

---

## Чеклист миграции

### Подготовка
- [ ] Создана резервная копия `data/final_results`
- [ ] Подсчитано количество файлов (для проверки после)
- [ ] Создан `config/paths.py` с централизованными путями
- [ ] Добавлена функция автомиграции

### Обновление кода
- [ ] Обновлён `src/ocr_processor.py`
- [ ] Обновлён `src/file_tokens.py` (все 4 места)
- [ ] Обновлён `src/postprocessing/attachment_evidence_extractor.py` (2 места)
- [ ] Обновлена документация (*.md файлы)
- [ ] Обновлён `.gitignore`

### Миграция данных
- [ ] Папка переименована: `data/final_results` → `data/ocr`
- [ ] Проверена структура: `data/ocr/texts/` и `data/ocr/reports/`
- [ ] Количество файлов совпадает с исходным

### Тестирование
- [ ] OCR процессор работает корректно
- [ ] file_tokens находит OCR файлы
- [ ] attachment_evidence_extractor находит тексты
- [ ] Pipeline обрабатывает письма без ошибок
- [ ] Логи не содержат упоминаний `final_results`

### Очистка
- [ ] Удалён backup (после подтверждения)
- [ ] Обновлён .gitignore
- [ ] Сделан git commit
- [ ] Обновлена документация проекта

---

## Откат (если что-то пошло не так)

```bash
# Вернуть backup
rm -rf data/ocr
mv data/final_results_backup_* data/final_results

# Откатить изменения в коде
git checkout -- src/
git checkout -- .gitignore
```

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Потеря данных при переименовании | Низкая | Критическое | Резервная копия перед миграцией |
| Пропущенные упоминания в коде | Средняя | Высокое | Grep поиск + тестирование |
| Сломается Pipeline | Средняя | Высокое | Поэтапное тестирование |
| Проблемы с правами доступа | Низкая | Среднее | Проверка прав перед миграцией |

---

## Оценка времени

| Фаза | Время | Критичность |
|------|-------|-------------|
| Подготовка | 30 мин | Высокая |
| Обновление кода | 1-2 часа | Критическая |
| Физическая миграция | 5-10 мин | Критическая |
| Тестирование | 30-60 мин | Критическая |
| Очистка | 10 мин | Низкая |
| **ИТОГО** | **2.5-3.5 часа** | |

---

## Рекомендации

1. **Выполнять миграцию в нерабочее время** (когда Pipeline не запущен)
2. **Использовать автомиграцию** через `DataPaths.migrate_if_needed()`
3. **Тестировать поэтапно** - сначала один модуль, потом следующий
4. **Не удалять backup** до полного подтверждения работоспособности
5. **Обновить README проекта** с новой структурой папок

---

**Дата создания:** 2025-10-06  
**Статус:** Готов к выполнению  
**Приоритет:** 🟡 СРЕДНИЙ (не критично, но улучшает читаемость)
