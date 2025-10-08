# Анализ асинхронности в OCR-экстракторе (ocr_processor.py)

Дата анализа: 2025-06-10

## Резюме

OCR-процессор имеет **гибридную архитектуру** с поддержкой как синхронной, так и асинхронной обработки файлов. Асинхронные методы реализованы через `asyncio` с использованием `loop.run_in_executor()` для параллельного выполнения синхронных операций.

## 1. Использование asyncio

### Найденные импорты
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
```

### Асинхронные методы

#### 1.1 `test_files_by_date_async()` (строка 3497)
- **Назначение**: Асинхронное тестирование файлов за конкретную дату
- **Параметры**: 
  - `max_workers: int = 4` - количество параллельных потоков
- **Механизм параллелизма**: `asyncio.Semaphore(max_workers)`
- **Паттерн**: Создает задачи для каждого файла и выполняет их через `asyncio.gather()`

```python
async def test_files_by_date_async(self, date: str, files_to_test: List[Path], 
                                   limit: int = None, max_workers: int = 4):
    semaphore = asyncio.Semaphore(max_workers)
    tasks = []
    
    for i, file_path in enumerate(files_to_test, 1):
        task = self._process_file_async(file_path, normalized_date, i, 
                                        total_files, stats, semaphore)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

#### 1.2 `_process_file_async()` (строка 3558)
- **Назначение**: Асинхронная обработка одного файла
- **Механизм**: Использует `loop.run_in_executor(None, ...)` для выполнения синхронных операций
- **Операции в executor**:
  - `self._check_existing_results()` - проверка существующих результатов
  - `self._get_error_files_for_path()` - получение файлов с ошибками
  - `self.extract_text_from_file()` - основная обработка файла
  - `self._verify_saved_result()` - верификация результата

```python
async def _process_file_async(self, file_path: Path, date: str, 
                              file_index: int, total_files: int, 
                              stats: Dict, semaphore: asyncio.Semaphore):
    async with semaphore:
        loop = asyncio.get_event_loop()
        
        # Все синхронные операции выполняются через executor
        existing_check = await loop.run_in_executor(
            None, self._check_existing_results, file_path, date)
        
        result = await loop.run_in_executor(
            None, self.extract_text_from_file, file_path, date)
        
        verification_result = await loop.run_in_executor(
            None, self._verify_saved_result, result, date)
```

#### 1.3 `extract_text_from_files_async()` (строка 3661)
- **Назначение**: Асинхронное извлечение текста из множества файлов
- **Параметры**: `max_workers: int = 4`
- **Механизм**: Аналогичен `test_files_by_date_async()`

```python
async def extract_text_from_files_async(self, file_paths: List[Path], 
                                        date: str = None, max_workers: int = 4):
    semaphore = asyncio.Semaphore(max_workers)
    tasks = []
    
    for file_path in file_paths:
        task = self._extract_text_single_async(file_path, normalized_date, semaphore)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

#### 1.4 `_extract_text_single_async()` (строка 3692)
- **Назначение**: Асинхронная обработка одного файла (упрощенная версия)
- **Механизм**: Делегирует синхронный метод в executor

```python
async def _extract_text_single_async(self, file_path: Path, date: str, 
                                     semaphore: asyncio.Semaphore):
    async with semaphore:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.extract_text_from_file, 
                                         file_path, date)
```

#### 1.5 `_auto_retry_error_files_async()` (строка 3653)
- **Назначение**: Асинхронная обертка для повторной обработки файлов с ошибками
- **Механизм**: Делегирует синхронный метод в executor

## 2. Параллельная обработка файлов

### Текущая реализация

**ДА**, есть параллельная обработка файлов через асинхронные методы:

1. **Контроль параллелизма**: `asyncio.Semaphore(max_workers)` ограничивает количество одновременно обрабатываемых файлов (по умолчанию 4)

2. **Паттерн обработки**:
   - Создается список задач для всех файлов
   - Задачи запускаются параллельно через `asyncio.gather()`
   - Semaphore контролирует максимальное количество одновременных операций

3. **Обработка ошибок**: `return_exceptions=True` позволяет продолжить обработку даже при ошибках в отдельных файлах

### Ограничения

- Параллелизм реализован только на уровне файлов, не на уровне страниц PDF
- Внутри каждого файла обработка последовательная (см. `_process_pdf_sequential`)

## 3. Анализ методов extract_text и process_file

### 3.1 `extract_text_from_file()` (строка 2527)

**Тип**: Синхронный метод

**Характеристики**:
- Основной метод извлечения текста из файла
- Полностью синхронный, без использования async/await
- Поддерживает форматы: PDF, DOCX, DOC, XLSX, XLS, PNG, JPG, JPEG, TIFF
- Использует кэширование результатов через `_check_existing_results()`

**Логика обработки**:
```python
def extract_text_from_file(self, file_path: Path, date: str = None) -> Dict:
    # 1. Проверка кэша
    if normalized_date and self._check_existing_results(file_path, normalized_date):
        return self._get_existing_result(file_path, normalized_date)
    
    # 2. Обработка по типу файла
    if ext == ".pdf":
        # Анализ структуры PDF
        # Извлечение текстового слоя или OCR
    elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
        # Google Vision OCR
    # ... другие форматы
```

**Асинхронность**: НЕТ прямой асинхронности, но метод вызывается из асинхронных оберток через `loop.run_in_executor()`

### 3.2 Метод `process_file`

**Статус**: Отдельного метода `process_file` не найдено

Вместо этого используется:
- `_process_file_async()` - асинхронная обертка
- `extract_text_from_file()` - основной метод обработки

## 4. Использование ThreadPoolExecutor

### Результаты поиска

**НЕТ** прямого использования `ThreadPoolExecutor` в коде:
- Импорт присутствует: `from concurrent.futures import ThreadPoolExecutor, as_completed`
- Но нигде не создается экземпляр `ThreadPoolExecutor()`
- Не используется паттерн `with ThreadPoolExecutor() as executor:`

### Механизм параллелизма

Вместо явного ThreadPoolExecutor используется:
- `asyncio.get_event_loop().run_in_executor(None, ...)` 
- При передаче `None` в качестве executor, asyncio использует **дефолтный ThreadPoolExecutor**
- Это стандартный паттерн для выполнения синхронных операций в асинхронном коде

## 5. Пул потоков для OCR операций

### Текущее состояние

**ДА**, используется пул потоков, но неявно:

1. **Дефолтный ThreadPoolExecutor**:
   - Создается автоматически asyncio при вызове `run_in_executor(None, ...)`
   - Размер пула по умолчанию: `min(32, os.cpu_count() + 4)`

2. **Контроль параллелизма**:
   - Через `asyncio.Semaphore(max_workers)` (по умолчанию 4)
   - Это ограничивает количество одновременных файлов, но не потоков

3. **OCR операции**:
   - Google Vision API вызовы выполняются в пуле потоков
   - Локальная обработка (PDF text extraction, DOCX, etc.) также в пуле

### Потенциальные проблемы

- Нет явного контроля над размером ThreadPoolExecutor
- Может быть неэффективно для I/O-bound операций (API calls)
- Для CPU-bound операций (обработка изображений) может быть недостаточно

## 6. Документирование текущего состояния асинхронности

### Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    OCR Processor                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Синхронный уровень (основная логика):                      │
│  ├─ extract_text_from_file()                                │
│  ├─ _process_excel_file()                                   │
│  ├─ _analyze_pdf_structure()                                │
│  ├─ run_google_vision_ocr()                                 │
│  └─ _check_existing_results()                               │
│                                                               │
│  Асинхронный уровень (параллелизм):                         │
│  ├─ test_files_by_date_async()                              │
│  │   └─ _process_file_async()                               │
│  │       └─ loop.run_in_executor(None, extract_text...)     │
│  │                                                            │
│  └─ extract_text_from_files_async()                         │
│      └─ _extract_text_single_async()                        │
│          └─ loop.run_in_executor(None, extract_text...)     │
│                                                               │
│  Контроль параллелизма:                                      │
│  └─ asyncio.Semaphore(max_workers=4)                        │
│                                                               │
│  Пул потоков:                                                │
│  └─ Дефолтный ThreadPoolExecutor (неявный)                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Паттерны использования

1. **Для обработки одного файла**:
   ```python
   # Синхронный вариант
   result = processor.extract_text_from_file(file_path, date)
   
   # Асинхронный вариант (не используется напрямую)
   # Вызывается через _extract_text_single_async
   ```

2. **Для обработки множества файлов**:
   ```python
   # Синхронный вариант
   processor.test_files_by_date(date, files)
   
   # Асинхронный вариант (параллельная обработка)
   await processor.test_files_by_date_async(date, files, max_workers=4)
   ```

### Преимущества текущей реализации

✅ Гибкость: поддержка синхронного и асинхронного API
✅ Простота: использование стандартных asyncio паттернов
✅ Контроль: Semaphore ограничивает нагрузку
✅ Обработка ошибок: `return_exceptions=True` в gather

### Недостатки и ограничения

❌ Нет явного контроля над ThreadPoolExecutor
❌ Дефолтный размер пула может быть неоптимальным
❌ Нет параллелизма внутри обработки одного PDF
❌ Импорт ThreadPoolExecutor не используется (мертвый код)
❌ Нет асинхронных API вызовов (Google Vision через синхронный клиент)

## 7. Выводы и рекомендации

### Текущее состояние асинхронности: ⭐⭐⭐ (3/5)

**Что работает хорошо**:
- Параллельная обработка множества файлов
- Контроль параллелизма через Semaphore
- Обработка ошибок

**Что можно улучшить**:
1. Использовать явный ThreadPoolExecutor с настраиваемым размером пула
2. Рассмотреть ProcessPoolExecutor для CPU-bound операций
3. Добавить асинхронный клиент для Google Vision API
4. Реализовать параллельную обработку страниц внутри PDF
5. Удалить неиспользуемый импорт или начать использовать ThreadPoolExecutor

### Соответствие требованиям

- **Требование 1.1** (Анализ асинхронности): ✅ Выполнено
- **Требование 1.3** (Определение узких мест): ✅ Выполнено

### Следующие шаги

1. Провести анализ кэширования (следующая задача)
2. Оценить производительность текущей реализации
3. Разработать план оптимизации на основе найденных узких мест
