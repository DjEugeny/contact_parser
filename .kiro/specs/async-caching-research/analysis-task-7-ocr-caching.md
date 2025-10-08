# Анализ кэширования в OCR-процессоре

## Обзор

Дата анализа: 2025-01-07
Файл: `src/ocr_processor.py`
Связанные файлы: `src/core/ocr_manager.py`, `data/cache/`

## 1. Использование _pdf_structure_cache в ocr_processor.py

### 1.1 Инициализация кэша

**Местоположение:** `OCRProcessor.__init__()` (строки 84-88)

```python
# Инициализация кэша структурного анализа PDF
self._pdf_structure_cache = {}
self._cache_dir = self.data_dir / "cache" / "pdf_analysis"
self._cache_dir.mkdir(parents=True, exist_ok=True)
self._load_pdf_structure_cache()
```

**Характеристики:**
- Кэш хранится в памяти как словарь `self._pdf_structure_cache`
- Директория кэша: `data/cache/pdf_analysis/`
- Файл кэша: `pdf_structure_cache.json`
- Автоматическое создание директории при инициализации

### 1.2 Точки использования кэша

Кэш используется в следующих местах:

1. **Загрузка при старте:** `_load_pdf_structure_cache()` (строка 88)
2. **Проверка кэша:** `_analyze_pdf_structure()` (строки 516-522)
3. **Сохранение результата:** `_analyze_pdf_structure()` (строки 712-713)

## 2. Методы работы с кэшем

### 2.1 Метод _load_pdf_structure_cache()

**Местоположение:** Строки 145-163

**Функциональность:**
```python
def _load_pdf_structure_cache(self):
    """💾 Загрузка кэша структурного анализа PDF"""
    cache_file = self._cache_dir / "pdf_structure_cache.json"
    try:
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                self._pdf_structure_cache = json.load(f)
            # Преобразуем списки обратно в множества
            for key, value in self._pdf_structure_cache.items():
                if isinstance(value, dict) and 'font_types' in value:
                    if isinstance(value['font_types'], list):
                        value['font_types'] = set(value['font_types'])
            self.logger.info(f"💾 Загружен кэш PDF анализа: {len(self._pdf_structure_cache)} записей")
        else:
            self._pdf_structure_cache = {}
            self.logger.info("💾 Создан новый кэш PDF анализа")
    except Exception as e:
        self.logger.error(f"❌ Ошибка загрузки кэша PDF анализа: {e}")
        self._pdf_structure_cache = {}
```

**Особенности:**
- Загружает кэш из JSON файла при старте
- Преобразует списки обратно в множества для `font_types`
- Обрабатывает ошибки с fallback на пустой кэш
- Логирует количество загруженных записей

### 2.2 Метод _save_pdf_structure_cache()

**Местоположение:** Строки 164-183

**Функциональность:**
```python
def _save_pdf_structure_cache(self):
    """💾 Сохранение кэша структурного анализа PDF"""
    cache_file = self._cache_dir / "pdf_structure_cache.json"
    try:
        # Преобразуем множества в списки для сериализации
        serializable_cache = {}
        for key, value in self._pdf_structure_cache.items():
            if isinstance(value, dict):
                serializable_cache[key] = value.copy()
                if 'font_types' in serializable_cache[key]:
                    if isinstance(serializable_cache[key]['font_types'], set):
                        serializable_cache[key]['font_types'] = list(...)
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_cache, f, ensure_ascii=False, indent=2)
        self.logger.debug(f"💾 Кэш PDF анализа сохранен: {len(self._pdf_structure_cache)} записей")
    except Exception as e:
        self.logger.error(f"❌ Ошибка сохранения кэша PDF анализа: {e}")
```

**Особенности:**
- Преобразует множества в списки для JSON сериализации
- Создает копию данных для безопасного преобразования
- Сохраняет с форматированием (indent=2) и поддержкой Unicode
- Обрабатывает ошибки без прерывания работы

### 2.3 Метод _get_pdf_cache_key()

**Местоположение:** Строки 185-194

**Функциональность:**
```python
def _get_pdf_cache_key(self, pdf_path: Path) -> str:
    """🔑 Генерация ключа кэша для PDF файла"""
    try:
        # Используем путь, размер файла и время модификации для уникальности
        stat = pdf_path.stat()
        cache_data = f"{pdf_path.name}_{stat.st_size}_{stat.st_mtime}"
        return hashlib.md5(cache_data.encode('utf-8')).hexdigest()
    except Exception as e:
        self.logger.error(f"❌ Ошибка генерации ключа кэша для {pdf_path}: {e}")
        return hashlib.md5(str(pdf_path).encode('utf-8')).hexdigest()
```

**Механизм генерации ключа:**
- Использует имя файла, размер и время модификации
- Генерирует MD5 хеш для уникальности
- Fallback на хеш пути при ошибках

## 3. Что кэшируется

### 3.1 Структура кэшируемых данных

Кэш хранит результаты структурного анализа PDF документов. Каждая запись содержит:

```python
result = {
    'has_text_layer': bool,              # Наличие текстового слоя
    'text_to_image_ratio': float,        # Соотношение текста к изображениям
    'has_embedded_fonts': bool,          # Наличие встроенных шрифтов
    'text_objects_count': int,           # Количество текстовых объектов
    'image_objects_count': int,          # Количество изображений
    'total_objects': int,                # Общее количество объектов
    'font_types': set,                   # Множество типов шрифтов
    'text_confidence': float,            # Уверенность в качестве текста
    'structure_score': float,            # Оценка структуры (0-100)
    'page_count': int,                   # Количество страниц
    'text_density': float,               # Плотность текста
    'font_diversity': float,             # Разнообразие шрифтов
    'has_vector_text': bool,             # Наличие векторного текста
    'text_quality_indicators': {         # Индикаторы качества
        'significant_text': bool,
        'reasonable_density': bool,
        'low_image_ratio': bool,
        'good_object_ratio': bool,
        'vector_text': bool,
        'embedded_fonts': bool,
        'font_diversity': bool
    }
}
```

### 3.2 Использование в _analyze_pdf_structure()

**Проверка кэша (строки 516-522):**
```python
# Проверяем кэш
cache_key = self._get_pdf_cache_key(pdf_path)
if cache_key in self._pdf_structure_cache:
    cached_result = self._pdf_structure_cache[cache_key]
    # Преобразуем set обратно из списка для font_types
    if 'font_types' in cached_result and isinstance(cached_result['font_types'], list):
        cached_result['font_types'] = set(cached_result['font_types'])
    self.logger.debug(f"💾 Использован кэш PDF анализа для {pdf_path.name}")
    return cached_result
```

**Сохранение результата (строки 712-713):**
```python
# Сохраняем результат в кэш
cache_key = self._get_pdf_cache_key(pdf_path)
self._pdf_structure_cache[cache_key] = result
self._save_pdf_structure_cache()
```

## 4. Механизм инвалидации кэша

### 4.1 Инвалидация по хешу файла

**Принцип работы:**
- Ключ кэша генерируется на основе: `имя_файла + размер + время_модификации`
- При изменении файла меняется `st_mtime` (время модификации)
- Новый хеш не совпадает со старым → кэш промах → повторный анализ

**Преимущества:**
- Автоматическая инвалидация при изменении файла
- Не требует явного удаления устаревших записей
- Работает на уровне файловой системы

**Недостатки:**
- Старые записи остаются в кэше (нет автоматической очистки)
- Кэш может расти неограниченно
- Нет TTL (time-to-live) для записей

### 4.2 Отсутствие явной очистки

**Текущее состояние:**
- Нет метода для очистки устаревших записей
- Нет ограничения на размер кэша
- Нет периодической очистки

**Потенциальные проблемы:**
- Рост размера файла кэша со временем
- Накопление устаревших записей
- Потенциальные проблемы с памятью при большом количестве файлов

## 5. Дополнительное кэширование в OCR Manager

### 5.1 Кэш результатов OCR (ВРЕМЕННО ОТКЛЮЧЕН)

**Файл:** `src/core/ocr_manager.py`
**Статус:** Отключен для отладки

**Структура:**
```python
self._cache = {}  # Словарь в памяти
self._cache_file = Path("data/cache/ocr_cache.json")  # Файл на диске
```

**Что кэшируется:**
- Результаты OCR обработки файлов
- Извлеченный текст из документов
- Метаданные обработки (время, статус)

### 5.2 Двухуровневая система кэширования

**Уровни:**
1. **Старая система** - простой JSON кэш (`ocr_cache.json`)
2. **Новая система** - продвинутое кэширование с TTL и сжатием (отключена)

**Генерация ключа для OCR кэша:**
```python
def _generate_cache_key(self, file_path: str, date: str = None) -> str:
    key_data = f"{file_path}:{date or 'no_date'}"
    return hashlib.md5(key_data.encode()).hexdigest()

def _generate_file_hash(self, file_path: str) -> str:
    file_stat = Path(file_path).stat()
    hash_data = f"{file_path}:{file_stat.st_mtime}:{file_stat.st_size}"
    return hashlib.md5(hash_data.encode()).hexdigest()
```

### 5.3 Валидация OCR кэша

```python
def _is_cache_valid(self, cache_entry: Dict, file_path: str) -> bool:
    # Проверяем существование файла
    if not os.path.exists(file_path):
        return False
    
    # Проверяем время модификации файла
    file_mtime = os.path.getmtime(file_path)
    cache_mtime = cache_entry.get('file_mtime', 0)
    
    return file_mtime <= cache_mtime
```

## 6. Текущая реализация кэширования - Итоги

### 6.1 PDF Structure Cache (АКТИВЕН)

**Назначение:** Кэширование результатов структурного анализа PDF

**Характеристики:**
- ✅ Активен и работает
- ✅ Автоматическая инвалидация по хешу файла
- ✅ Персистентное хранение в JSON
- ✅ Обработка ошибок
- ❌ Нет ограничения размера
- ❌ Нет автоматической очистки
- ❌ Нет TTL

**Производительность:**
- Значительно ускоряет повторный анализ PDF
- Особенно эффективен для больших документов
- Анализ структуры может занимать 1-5 секунд на документ

### 6.2 OCR Results Cache (ОТКЛЮЧЕН)

**Назначение:** Кэширование результатов OCR обработки

**Статус:** Временно отключен для отладки

**Причины отключения:**
- Отладка системы
- Тестирование производительности без кэша
- Разработка новой системы кэширования

**Код отключения:**
```python
self.logger.info("💾 OCR КЭШИРОВАНИЕ ОТКЛЮЧЕНО ДЛЯ ОТЛАДКИ")
self.logger.info("💾 OCR СТАРЫЙ КЭШ ОТКЛЮЧЕН ДЛЯ ОТЛАДКИ")
```

## 7. Рекомендации по улучшению

### 7.1 Для PDF Structure Cache

1. **Добавить автоматическую очистку:**
   - Удаление записей старше N дней
   - Ограничение максимального размера кэша
   - Периодическая очистка при старте

2. **Добавить метрики:**
   - Счетчик cache hits/misses
   - Время экономии за счет кэша
   - Размер кэша

3. **Оптимизация хранения:**
   - Сжатие данных
   - Использование более эффективного формата (pickle, msgpack)

### 7.2 Для OCR Results Cache

1. **Включить кэширование:**
   - Завершить отладку
   - Активировать новую систему кэширования

2. **Добавить TTL:**
   - Автоматическое истечение записей
   - Настраиваемое время жизни

3. **Реализовать миграцию:**
   - Перенос данных из старого кэша в новый
   - Постепенный переход

## 8. Связь с требованиями

**Requirements: 2.1, 2.3, 9.6**

- **2.1** - Анализ текущей реализации кэширования ✅
- **2.3** - Документирование механизмов инвалидации ✅
- **9.6** - Оценка эффективности кэширования ✅

## 9. Выводы

1. **PDF Structure Cache** - хорошо реализован и активно используется
2. **Механизм инвалидации** - работает на основе хеша файла (имя + размер + mtime)
3. **OCR Results Cache** - временно отключен, требует доработки
4. **Отсутствует** - автоматическая очистка, ограничение размера, TTL
5. **Производительность** - кэш значительно ускоряет повторную обработку

## 10. Файлы кэша

```
data/cache/
├── pdf_analysis/
│   └── pdf_structure_cache.json    # Кэш структурного анализа PDF (АКТИВЕН)
└── ocr_cache.json                  # Кэш результатов OCR (ОТКЛЮЧЕН)
```
