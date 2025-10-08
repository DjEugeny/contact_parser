# План действий по устранению проблем Pipeline

**Дата последнего обновления:** 2025-10-08  
**Статус:** Обновлен после исследования

---

## 🔍 РЕЗУЛЬТАТЫ ИССЛЕДОВАНИЙ

### Исследование 1: Фильтр получателей (Пункт 5)

**Найдено:** `src/advanced_email_fetcher.py:346`
```python
if internal_recipients >= 10:
    return f"массовая внутренняя рассылка ({internal_recipients} получателей)"
```

**Проблема подтверждена:** Фильтр отсекает ВСЕ письма с 10+ получателями внутри домена `@dna-technology.ru`, даже если письмо пришло от внешнего отправителя.

**Требуемые изменения:**
1. Вынести порог `10` в `config/settings.py` как настройку
2. Изменить логику: фильтр должен срабатывать ТОЛЬКО если:
   - Отправитель `@dna-technology.ru` И
   - Все получатели `@dna-technology.ru` И  
   - Количество получателей >= порога
3. Если письмо от внешнего адреса → НЕ фильтровать по количеству получателей

### Исследование 2: JSON Schema валидация (Пункт 3)

**Текущая ситуация:**
- Автокоррекция работает и исправляет ошибки
- 6 из 30 писем (20%) требуют автокоррекции
- Типичные ошибки: `None` вместо integer, неправильные enum значения

**Риски если НЕ улучшать промпт:**
- ❌ Неправильные связи между сущностями (contact_id → organization_id)
- ❌ Потеря семантической точности (info_request → clarification)
- ❌ Накопление технического долга
- ❌ Сложность отладки при масштабировании

**Преимущества улучшения промпта:**
- ✅ Более точные данные с первого раза
- ✅ Меньше нагрузки на автокоррекцию
- ✅ Лучшая предсказуемость результатов
- ✅ Снижение с 20% до <5% ошибок

**Рекомендация:** Улучшить промпт (приоритет СРЕДНИЙ, не критично но желательно)

### Исследование 3: DaData API ключ (Пункт 8)

**Найдено:** Ключ присутствует в `.env`:
```
DADATA_API_KEY=...
DADATA_SECRET_KEY=...
```

**Проблема:** Модуль не читает ключ из окружения или неправильно инициализируется.

**Решение:** Проверить инициализацию DaData клиента и чтение переменных окружения.

---

## Фаза 1: Критические исправления (1-3 дня)

### Задача 1.1: Рефакторинг логики обработки OCR вложений
**Приоритет:** 🔴 КРИТИЧЕСКИЙ  
**Срок:** 2-3 дня  
**Ответственный:** Backend Developer / Architect

**Проблема:**  
Pipeline запускает полный OCR модуль для каждого вложения, даже если файл уже обработан. Это приводит к потере ~20-30 секунд на 30 писем и засорению логов.

**Шаги:**
1. Создать `OCRCacheManager` класс в Pipeline
2. Реализовать batch-проверку кэша для нескольких файлов
3. Добавить ленивую инициализацию OCR модуля
4. Упростить OCR модуль - убрать проверки кэша
5. Обновить логирование (убрать избыточные сообщения)
6. Добавить warm-up кэша при старте (опционально)
7. Протестировать на 30 письмах

**Код для реализации:**

```python
# 1. OCRCacheManager
class OCRCacheManager:
    def __init__(self, results_dir="data/final_results"):
        self.results_dir = Path(results_dir)
        self._cache = {}  # In-memory кэш
    
    def check_batch(self, filenames: List[str]) -> Dict[str, Optional[str]]:
        """Batch-проверка кэша"""
        results = {}
        for filename in filenames:
            results[filename] = self.get_cached_result(filename)
        return results
    
    def get_cached_result(self, filename: str) -> Optional[str]:
        """Получить результат из кэша"""
        if filename in self._cache:
            return self._cache[filename]
        
        result_file = self.results_dir / f"{filename}.json"
        if result_file.exists():
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    text = data.get('extracted_text', '')
                    self._cache[filename] = text
                    return text
            except Exception as e:
                logger.warning(f"Ошибка чтения кэша: {e}")
        return None
    
    def warmup(self):
        """Предзагрузка кэша в память"""
        logger.info("🔥 Прогрев OCR кэша...")
        count = 0
        for result_file in self.results_dir.glob("*.json"):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    filename = result_file.stem
                    self._cache[filename] = data.get('extracted_text', '')
                    count += 1
            except Exception:
                pass
        logger.info(f"✅ Загружено {count} результатов в кэш")

# 2. Обновлённый EmailProcessor
class EmailProcessor:
    def __init__(self):
        self.ocr_cache = OCRCacheManager()
        self.ocr_cache.warmup()  # Опционально
        self.ocr_module = None  # Ленивая инициализация
    
    def process_attachments(self, attachments: List[dict]) -> List[str]:
        """Обработка вложений с проверкой кэша"""
        if not attachments:
            return []
        
        # Фаза 1: Batch-проверка кэша (быстро)
        filenames = [a.get('filename') for a in attachments if a.get('path')]
        cache_results = self.ocr_cache.check_batch(filenames)
        
        texts = []
        to_process = []
        
        for attachment in attachments:
            if not attachment.get('path'):
                logger.warning(f"⚠️ Вложение без пути: {attachment.get('filename')}")
                continue
            
            filename = attachment['filename']
            cached_text = cache_results.get(filename)
            
            if cached_text:
                logger.info(f"✅ OCR кэш: {filename} ({len(cached_text)} символов)")
                texts.append(cached_text)
            else:
                logger.info(f"⏳ Требуется OCR: {filename}")
                to_process.append(attachment)
        
        # Фаза 2: Обработка только необработанных
        if to_process:
            logger.info(f"🔍 Запуск OCR модуля для {len(to_process)} файлов")
            
            # Ленивая инициализация
            if self.ocr_module is None:
                self.ocr_module = OCRModule()
            
            for attachment in to_process:
                text = self.ocr_module.extract_text(attachment['path'])
                texts.append(text)
        
        return texts

# 3. Упрощённый OCR Module
class OCRModule:
    """Упрощённый OCR - только извлечение текста"""
    
    def __init__(self):
        self.vision_client = None
        logger.info("✅ OCR модуль инициализирован")
    
    def extract_text(self, filepath: str) -> str:
        """Извлечь текст (без проверки кэша)"""
        logger.info(f"🔍 OCR обработка: {Path(filepath).name}")
        
        if self.vision_client is None:
            self.vision_client = self._init_vision_client()
        
        text = self._do_ocr(filepath)
        self._save_result(filepath, text)
        
        logger.info(f"✅ Извлечено {len(text)} символов")
        return text
```

**Критерии успеха:**
- [ ] OCR модуль инициализируется только при необходимости
- [ ] Для уже обработанных файлов OCR модуль не запускается
- [ ] Логи стали чище (убраны избыточные сообщения)
- [ ] Время обработки 30 писем сократилось на 20-30 секунд
- [ ] Все unit-тесты проходят
- [ ] Добавлены тесты для OCRCacheManager

**Метрики до/после:**
- Инициализаций OCR: 12 → 0
- Время на проверки: ~20-30 сек → ~0.5-1 сек
- Строк в логах: ~100 → ~12

---

### Задача 1.2: Исследовать отказ email_035
Приоритет: 🔴 КРИТИЧЕСКИЙ
Срок: 1 день
Ответственный: Backend Developer

Шаги:

Прочитать исходный файл email_035_20250729_20250729_yandex_ru_f37d60ba.json
Проверить raw ответ LLM (если сохранён)
Воспроизвести ошибку локально
Добавить детальное логирование с traceback
Определить root cause
Исправить и протестировать
Критерии успеха:

[ ] email_035 успешно обрабатывается
[ ] Добавлено детальное логирование для подобных случаев
[ ] Написан unit-тест для воспроизведения проблемы
### Задача 1.3: Исправить сериализацию LocationEnrichmentMetadata
**Приоритет:** 🔴 КРИТИЧЕСКИЙ  
**Срок:** 1 день  
**Ответственный:** Backend Developer

**Шаги:**
1. Найти класс LocationEnrichmentMetadata в коде
2. Добавить метод сериализации (.dict() или __dict__)
3. Обновить код, который создаёт этот объект
4. Добавить custom JSON encoder если нужно
5. Протестировать на email_015

**Код для реализации:**
```python
# Вариант 1: Если это dataclass
from dataclasses import asdict
metadata_dict = asdict(location_metadata)

# Вариант 2: Если это Pydantic
metadata_dict = location_metadata.model_dump()

# Вариант 3: Custom encoder
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, LocationEnrichmentMetadata):
            return obj.__dict__
        return super().default(obj)
```

**Критерии успеха:**
- [ ] email_015 сохраняется без ошибок
- [ ] Все processed.json файлы корректно сериализуются
- [ ] Добавлен unit-тест для сериализации

---

### Задача 1.4: Исправить фильтр получателей для внешних писем
**Приоритет:** 🟠 ВЫСОКИЙ  
**Срок:** 1-2 дня  
**Ответственный:** Backend Developer

**Проблема:**  
Текущий фильтр отсекает ВСЕ письма с 10+ получателями `@dna-technology.ru`, даже если письмо пришло от внешнего отправителя. Это неправильно - внешние письма где s.voronova@dna-technology.ru один из многих получателей должны обрабатываться.

**Шаги:**
1. Добавить настройку в `config/settings.py`:
```python
EMAIL_FILTERS_CONFIG = {
    'mass_mailing': {
        'enabled': True,
        'max_internal_recipients': 10,  # Порог для внутренних рассылок
        'apply_to_external_senders': False  # НЕ применять к внешним отправителям
    }
}
```

2. Обновить логику в `src/advanced_email_fetcher.py` (класс `EmailFilters`, метод `is_internal_mass_mailing`):
```python
def is_internal_mass_mailing(self, from_addr: str, to_addrs: List[str], cc_addrs: List[str] = None) -> Optional[str]:
    """🚫 Проверка на внутреннюю массовую рассылку"""
    
    # Получаем настройки из config
    max_recipients = EMAIL_FILTERS_CONFIG['mass_mailing']['max_internal_recipients']
    apply_to_external = EMAIL_FILTERS_CONFIG['mass_mailing']['apply_to_external_senders']
    
    # Проверяем домен отправителя
    is_internal_sender = from_addr and f"@{COMPANY_DOMAIN}" in from_addr.lower()
    
    # Если отправитель внешний и фильтр не применяется к внешним - пропускаем
    if not is_internal_sender and not apply_to_external:
        return None
    
    # Если отправитель внешний - НЕ фильтруем по количеству получателей
    if not is_internal_sender:
        return None
    
    # Для внутренних отправителей - считаем внутренних получателей
    all_recipients = []
    all_recipients.extend(to_addrs or [])
    all_recipients.extend(cc_addrs or [])
    
    internal_recipients = 0
    for recipient in all_recipients:
        if f"@{COMPANY_DOMAIN}" in recipient.lower():
            internal_recipients += 1
    
    if internal_recipients >= max_recipients:
        return f"массовая внутренняя рассылка ({internal_recipients} получателей)"
    
    return None
```

3. Добавить unit-тесты:
```python
def test_external_sender_not_filtered():
    """Внешний отправитель с 15 получателями НЕ должен фильтроваться"""
    filters = EmailFilters(config_dir, logger)
    
    from_addr = "partner@external-company.com"
    to_addrs = [f"user{i}@dna-technology.ru" for i in range(15)]
    
    result = filters.is_internal_mass_mailing(from_addr, to_addrs)
    assert result is None  # НЕ фильтруется

def test_internal_sender_filtered():
    """Внутренний отправитель с 15 получателями ДОЛЖЕН фильтроваться"""
    filters = EmailFilters(config_dir, logger)
    
    from_addr = "admin@dna-technology.ru"
    to_addrs = [f"user{i}@dna-technology.ru" for i in range(15)]
    
    result = filters.is_internal_mass_mailing(from_addr, to_addrs)
    assert result is not None  # Фильтруется
```

4. Протестировать на реальных данных

**Критерии успеха:**
- [ ] Настройка вынесена в `config/settings.py`
- [ ] Внешние письма с 10+ получателями НЕ фильтруются
- [ ] Внутренние рассылки с 10+ получателями фильтруются
- [ ] Добавлены unit-тесты
- [ ] Обновлена документация

---

## Фаза 2: Высокоприоритетные улучшения (3-5 дней)

### Задача 1.5: Добавить CLI меню для выбора диапазона дат в advanced_email_fetcher
**Приоритет:** 🟠 ВЫСОКИЙ  
**Срок:** 1-2 дня  
**Ответственный:** Backend Developer

**Требования:**
1. Добавить интерактивное CLI меню для выбора режима работы:
   - Диапазон дат (от-до)
   - Одна конкретная дата
   - Весь месяц текущего года
2. Поддержка различных форматов ввода дат:
   - `2025-07-12` (ISO формат)
   - `12.07.2025` (точки)
   - `12-7-25` (короткий формат)
   - `12 июля 25` (текстовый формат на русском)
3. Валидация введенных дат
4. Удобный интерфейс с подсказками

**Шаги:**
1. Создать функцию парсинга различных форматов дат
2. Создать CLI меню с выбором режима
3. Добавить валидацию введенных данных
4. Интегрировать в основной скрипт
5. Добавить примеры использования в документацию

**Код для реализации:**
```python
import argparse
from datetime import datetime
import re

def parse_date_flexible(date_str: str) -> datetime:
    """Парсинг даты в различных форматах"""
    date_str = date_str.strip()
    
    # Формат: 2025-07-12
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        pass
    
    # Формат: 12.07.2025
    try:
        return datetime.strptime(date_str, '%d.%m.%Y')
    except ValueError:
        pass
    
    # Формат: 12-7-25
    try:
        dt = datetime.strptime(date_str, '%d-%m-%y')
        # Корректируем год (25 → 2025)
        if dt.year < 2000:
            dt = dt.replace(year=dt.year + 2000)
        return dt
    except ValueError:
        pass
    
    # Формат: 12 июля 25
    months_ru = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
    }
    
    pattern = r'(\d{1,2})\s+(\w+)\s+(\d{2,4})'
    match = re.match(pattern, date_str.lower())
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))
        
        if month_name in months_ru:
            month = months_ru[month_name]
            if year < 100:
                year += 2000
            return datetime(year, month, day)
    
    raise ValueError(f"Не удалось распознать формат даты: {date_str}")

def cli_menu():
    """Интерактивное CLI меню"""
    print("="*70)
    print("📧 ADVANCED EMAIL FETCHER - Выбор диапазона дат")
    print("="*70)
    print()
    print("Выберите режим работы:")
    print("  1. Диапазон дат (от-до)")
    print("  2. Одна конкретная дата")
    print("  3. Весь месяц текущего года")
    print()
    
    choice = input("Ваш выбор (1-3): ").strip()
    
    if choice == '1':
        print("\nВведите начальную дату:")
        print("  Примеры: 2025-07-12, 12.07.2025, 12-7-25, 12 июля 25")
        start_str = input("Начальная дата: ").strip()
        start_date = parse_date_flexible(start_str)
        
        print("\nВведите конечную дату:")
        end_str = input("Конечная дата: ").strip()
        end_date = parse_date_flexible(end_str)
        
        if start_date > end_date:
            print("❌ Ошибка: начальная дата больше конечной!")
            return None, None
        
        return start_date, end_date
    
    elif choice == '2':
        print("\nВведите дату:")
        print("  Примеры: 2025-07-12, 12.07.2025, 12-7-25, 12 июля 25")
        date_str = input("Дата: ").strip()
        date = parse_date_flexible(date_str)
        return date, date
    
    elif choice == '3':
        print("\nВведите месяц (1-12):")
        month = int(input("Месяц: ").strip())
        if month < 1 or month > 12:
            print("❌ Ошибка: месяц должен быть от 1 до 12!")
            return None, None
        
        year = datetime.now().year
        start_date = datetime(year, month, 1)
        
        # Последний день месяца
        if month == 12:
            end_date = datetime(year, 12, 31)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        return start_date, end_date
    
    else:
        print("❌ Неверный выбор!")
        return None, None

# Интеграция в main
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Advanced Email Fetcher')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Интерактивный режим выбора дат')
    parser.add_argument('--start-date', type=str,
                       help='Начальная дата (формат: YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='Конечная дата (формат: YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    if args.interactive:
        start_date, end_date = cli_menu()
        if not start_date:
            sys.exit(1)
    elif args.start_date and args.end_date:
        start_date = parse_date_flexible(args.start_date)
        end_date = parse_date_flexible(args.end_date)
    else:
        print("Используйте --interactive или укажите --start-date и --end-date")
        sys.exit(1)
    
    print(f"\n✅ Выбран диапазон: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    
    # Запуск обработки
    fetcher = AdvancedEmailFetcherV2(logger)
    fetcher.fetch_emails(start_date, end_date)
```

**Критерии успеха:**
- [ ] CLI меню работает интерактивно
- [ ] Поддерживаются все требуемые форматы дат
- [ ] Валидация дат работает корректно
- [ ] Можно выбрать диапазон, одну дату или месяц
- [ ] Добавлены примеры в документацию
- [ ] Добавлены unit-тесты для парсинга дат

---

### Задача 2.1: Улучшить промпт для снижения ошибок валидации (с версионированием)
**Приоритет:** 🟡 СРЕДНИЙ (не критично, автокоррекция работает)  
**Срок:** 3 дня  
**Ответственный:** ML Engineer / Prompt Engineer

**Обоснование приоритета:**  
После исследования выяснилось, что автокоррекция успешно исправляет ошибки. Однако улучшение промпта даст:
- Более точные данные с первого раза
- Снижение нагрузки на автокоррекцию
- Лучшую предсказуемость результатов
- Снижение ошибок с 20% до <5%

**Риски если НЕ делать:**
- Неправильные связи между сущностями (низкий риск, автокоррекция исправляет)
- Потеря семантической точности (средний риск)
- Накопление технического долга (низкий риск)

**Шаги:**
1. **Сохранить текущий промпт** `unified_contact_extraction_structured.txt` как `unified_contact_extraction_v1.0.txt`
2. Создать `prompts/version.json` с метаданными версий
3. Создать функцию `load_prompt(version)` для загрузки промптов
4. Обновить модуль, который использует промпт, для работы с версионированием
5. Проанализировать все 6 случаев ошибок валидации
6. Создать улучшенную версию `unified_contact_extraction_v1.1.txt` с:
   - Строгими правилами для null значений
   - Примерами корректных значений
   - Всеми допустимыми enum значениями
   - Примерами правильного JSON
7. Обновить `version.json`: установить `current_version: "1.1"`
8. Протестировать на проблемных письмах
9. Запустить A/B тест: 30 писем с v1.0 vs 30 писем с v1.1
10. Документировать результаты в `version.json` и `README.md`

**Важно:** После внедрения версионирования:
- Модуль будет автоматически загружать версию из `current_version`
- Для создания v1.2 просто создайте файл и обновите `version.json`
- Старый файл `unified_contact_extraction_structured.txt` можно оставить как fallback
**Структура версионирования:**
```
prompts/
├── version.json                                    # Метаданные версий
├── unified_contact_extraction_structured.txt      # Текущий промпт (будет переименован)
├── unified_contact_extraction_v1.0.txt            # Baseline (копия текущего)
├── unified_contact_extraction_v1.1.txt            # Улучшенный промпт
├── unified_contact_extraction_v1.2.txt            # Будущие версии...
└── README.md                                       # Документация изменений
```

**Логика работы:**
1. **Текущий файл** `unified_contact_extraction_structured.txt` сохраняется как `v1.0` (baseline)
2. **Модуль загрузки** будет читать `version.json` и загружать файл из поля `current_version`
3. **При создании v1.2** просто обновляем `current_version` в `version.json`
4. **Старые версии** остаются для A/B тестирования и отката

**version.json:**
```json
{
  "current_version": "1.1",
  "default_file": "unified_contact_extraction_v1.1.txt",
  "versions": {
    "1.0": {
      "date": "2025-10-06",
      "description": "Baseline промпт (исходный unified_contact_extraction_structured.txt)",
      "validation_error_rate": 0.20,
      "file": "unified_contact_extraction_v1.0.txt",
      "status": "baseline"
    },
    "1.1": {
      "date": "2025-10-08",
      "description": "Улучшенный промпт с явными правилами JSON",
      "validation_error_rate": 0.05,
      "file": "unified_contact_extraction_v1.1.txt",
      "status": "active",
      "changes": [
        "Добавлены строгие правила для null значений",
        "Добавлены примеры enum значений",
        "Добавлены примеры правильного JSON"
      ]
    }
  }
}
```

**Функция загрузки промпта:**
```python
def load_prompt(version: str = None) -> str:
    """Загрузка промпта с поддержкой версионирования"""
    version_file = Path("prompts/version.json")
    
    if not version_file.exists():
        # Fallback на старый файл если версионирование не настроено
        return Path("prompts/unified_contact_extraction_structured.txt").read_text()
    
    with open(version_file, 'r') as f:
        version_data = json.load(f)
    
    # Если версия не указана - берем текущую
    if version is None:
        version = version_data['current_version']
    
    # Получаем имя файла для версии
    prompt_file = version_data['versions'][version]['file']
    prompt_path = Path("prompts") / prompt_file
    
    logger.info(f"📝 Загружен промпт версии {version}: {prompt_file}")
    return prompt_path.read_text()
```

**Обновления промпта v1.1:**

КРИТИЧЕСКИ ВАЖНО - Правила JSON:

1. НИКОГДА не используйте null для:
   - contact_id (используйте 1, 2, 3...)
   - organization_id (используйте 1, 2, 3...)
   - Если связь неясна, используйте 1

2. interaction_type - ТОЛЬКО эти значения:
   - 'clarification' - для запросов информации
   - 'requested_quote' - для запросов КП
   - 'sent_quote' - для отправки КП
   - 'follow_up' - для последующих контактов
   - 'other' - если не подходит ни один вариант
   
   НЕ используйте: 'info_request', 'information', 'question'

3. Для пустых строк используйте "" вместо null

ПРИМЕР ПРАВИЛЬНОГО JSON:
{
  "contacts": [
    {
      "contact_id": 1,
      "organization_id": 1,
      "name": "Иванов Иван",
      "email": "ivan@example.com"
    }
  ],
  "interactions": [
    {
      "contact_id": 1,
      "organization_id": 1,
      "interaction_type": "clarification"
    }
  ]
}
**Критерии успеха:**
- [ ] Текущий промпт сохранен как v1.0
- [ ] Создана структура версионирования промптов
- [ ] Создан улучшенный промпт v1.1
- [ ] Проведено A/B тестирование v1.0 vs v1.1
- [ ] Ошибки валидации снизились с 20% до <5%
- [ ] Автокоррекция требуется в <5% случаев
- [ ] Все 30 писем обрабатываются корректно
- [ ] Документированы изменения и результаты
---

### Задача 2.2: Добавить pre-validation перед основной валидацией
Приоритет: 🟠 ВЫСОКИЙ
Срок: 2 дня
Ответственный: Backend Developer

Шаги:

Создать функцию pre-валидации
Проверять типичные ошибки до JSON Schema
Автоматически исправлять простые проблемы
Логировать все исправления
Интегрировать в pipeline
Код:

def pre_validate_llm_response(data: dict) -> dict:
    """Предварительная валидация и исправление типичных ошибок"""
    corrections = []
    
    # Исправление 1: None в contact_id
    for interaction in data.get('interactions', []):
        if interaction.get('contact_id') is None:
            interaction['contact_id'] = 1
            corrections.append('interaction.contact_id: None -> 1')
    
    # Исправление 2: None в organization_id
    for contact in data.get('contacts', []):
        if contact.get('organization_id') is None:
            contact['organization_id'] = 1
            corrections.append('contact.organization_id: None -> 1')
    
    # Исправление 3: Недопустимые interaction_type
    type_mapping = {
        'info_request': 'clarification',
        'information': 'clarification',
        'question': 'clarification',
        'request': 'other'
    }
    
    for interaction in data.get('interactions', []):
        itype = interaction.get('interaction_type')
        if itype in type_mapping:
            interaction['interaction_type'] = type_mapping[itype]
            corrections.append(f'interaction_type: {itype} -> {type_mapping[itype]}')
    
    if corrections:
        logger.info(f"Pre-validation corrections: {corrections}")
    
    return data
Критерии успеха:

[ ] Pre-validation ловит 80%+ типичных ошибок
[ ] Основная валидация проходит чаще
[ ] Все исправления логируются
---

## Фаза 3: Средние улучшения (1-2 недели)

### Задача 3.1: Исправить обработку путей к вложениям
Приоритет: 🟡 СРЕДНИЙ
Срок: 3 дня
Ответственный: Backend Developer

Шаги:

Найти код парсинга вложений из писем
Добавить валидацию наличия путей
Реализовать восстановление путей по имени файла
Проверить существование файлов
Логировать отсутствующие вложения на этапе парсинга
Код:

def fix_attachment_path(attachment: dict, email_id: str, date: str) -> dict:
    """Восстановление пути к вложению"""
    if attachment.get('path'):
        return attachment
    
    filename = attachment.get('filename', 'unknown')
    if filename == 'unknown':
        logger.warning(f"Cannot reconstruct path for unknown attachment in {email_id}")
        return attachment
    
    # Попытка восстановить путь
    base_dir = f"data/attachments/{date}"
    pattern = f"{email_id}_*_{filename}"
    
    matches = glob.glob(os.path.join(base_dir, pattern))
    if matches:
        attachment['path'] = matches[0]
        logger.info(f"Reconstructed path: {matches[0]}")
    else:
        logger.error(f"Could not find attachment file: {pattern}")
    
    return attachment
Критерии успеха:

[ ] Все вложения имеют корректные пути
[ ] Предупреждения появляются на этапе парсинга, а не обработки
[ ] Добавлена статистика по отсутствующим вложениям
---

### Задача 3.2: Оптимизировать таймауты LLM
Приоритет: 🟡 СРЕДНИЙ
Срок: 2 дня
Ответственный: Backend Developer

Шаги:

Реализовать динамический расчёт таймаута
Учитывать размер текста и количество вложений
Увеличивать таймаут при повторных попытках
Добавить метрики времени ответа
Настроить алерты для медленных запросов
Код:

def calculate_dynamic_timeout(email_data: dict) -> int:
    """Динамический расчёт таймаута"""
    base = 60  # базовый таймаут
    
    # Учитываем размер текста
    text_length = len(email_data.get('text', ''))
    text_factor = text_length // 1000  # +1 сек на каждые 1000 символов
    
    # Учитываем вложения
    attachments = email_data.get('attachments', [])
    attachment_factor = len(attachments) * 30  # +30 сек на вложение
    
    # Учитываем OCR
    has_ocr = any(att.get('ocr_text') for att in attachments)
    ocr_factor = 30 if has_ocr else 0
    
    timeout = base + text_factor + attachment_factor + ocr_factor
    
    # Ограничиваем максимум
    return min(timeout, 300)

def retry_with_backoff(func, max_attempts=3, timeout_multiplier=1.5):
    """Повторные попытки с увеличением таймаута"""
    timeout = calculate_dynamic_timeout(email_data)
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func(timeout=timeout)
        except TimeoutError:
            if attempt < max_attempts:
                timeout = int(timeout * timeout_multiplier)
                logger.warning(f"Timeout, retry {attempt+1} with timeout={timeout}")
                time.sleep(2 ** attempt)  # exponential backoff
            else:
                raise
Критерии успеха:

[ ] Таймауты снизились с 3.3% до <1%
[ ] Среднее время обработки уменьшилось
[ ] Нет ложных таймаутов для больших писем
---

### Задача 3.3: Улучшить обработку ошибок и логирование
Приоритет: 🟡 СРЕДНИЙ
Срок: 2 дня
Ответственный: Backend Developer

Шаги:

Добавить полный traceback для всех исключений
Сохранять debug данные для проблемных писем
Структурировать логи (JSON format)
Добавить уровни логирования
Настроить ротацию логов
Код:

import traceback
import json
from datetime import datetime

def log_processing_error(email_file: str, error: Exception, context: dict):
    """Детальное логирование ошибок"""
    error_data = {
        "timestamp": datetime.now().isoformat(),
        "email_file": email_file,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context
    }
    
    # Сохраняем в отдельный файл для отладки
    error_file = f"data/errors/{email_file}_error.json"
    with open(error_file, 'w') as f:
        json.dump(error_data, f, indent=2, ensure_ascii=False)
    
    logger.error(f"Processing failed: {email_file}", extra=error_data)
Критерии успеха:

[ ] Все ошибки имеют полный traceback
[ ] Debug данные сохраняются для анализа
[ ] Логи структурированы и легко парсятся
---

## Фаза 4: Долгосрочные улучшения (1 месяц)

### Задача 4.1: Настроить мониторинг и алерты
Приоритет: 🟢 НИЗКИЙ
Срок: 5 дней
Ответственный: DevOps / Backend Developer

Метрики для отслеживания:

Success rate
Validation error rate
Processing time (avg, p95, p99)
LLM timeout rate
Serialization errors
Алерты:

Success rate < 95% → Critical
Validation errors > 30% → Warning
Processing time p95 > 180s → Warning
---

### Задача 4.2: Оптимизировать производительность
Приоритет: 🟢 НИЗКИЙ
Срок: 1 неделя
Ответственный: Backend Developer

Направления:

Включить кэширование после отладки
Параллельная обработка писем
Оптимизация OCR
Batch processing для LLM
Целевые метрики:

Среднее время: 90 сек → 60 сек
Throughput: 30 писем/45 мин → 30 писем/30 мин
---

### Задача 4.3: Настроить DaData или отключить
**Приоритет:** 🟢 НИЗКИЙ  
**Срок:** 1 час  
**Ответственный:** Backend Developer

**Результат исследования:**  
API ключ DaData уже присутствует в `.env`:
```
DADATA_API_KEY=...
DADATA_SECRET_KEY=...
```

**Проблема:** Модуль не читает ключ из окружения или неправильно инициализируется.

**Шаги:**
1. Проверить инициализацию DaData клиента
2. Убедиться что переменные окружения читаются правильно
3. Добавить логирование при инициализации DaData
4. Протестировать обогащение с DaData

**Критерии успеха:**
- [ ] DaData инициализируется без предупреждений
- [ ] API ключ читается из .env
- [ ] Обогащение работает корректно

---

### Задача 4.4: Миграция data/final_results → data/ocr
**Приоритет:** 🟡 СРЕДНИЙ (улучшает читаемость)  
**Срок:** 2-3 часа  
**Ответственный:** Backend Developer

**Цель:** Переименовать папку `data/final_results` в `data/ocr` для улучшения понятности структуры проекта.

**Детальный план:** См. `.kiro/specs/pipeline-issues-analysis-2025-10-06/migration-final-results-to-ocr.md`

**Краткие шаги:**
1. Создать резервную копию `data/final_results`
2. Создать `config/paths.py` с централизованными путями
3. Обновить код в затронутых модулях:
   - `src/ocr_processor.py` (КРИТИЧЕСКИЙ)
   - `src/file_tokens.py` (КРИТИЧЕСКИЙ)
   - `src/postprocessing/attachment_evidence_extractor.py` (ВЫСОКИЙ)
   - `scripts/commercial_proposal_collector.py` (СРЕДНИЙ)
4. Физически переименовать папку: `mv data/final_results data/ocr`
5. Протестировать все модули
6. Удалить backup после подтверждения

**Затронутые файлы:**
- `src/ocr_processor.py` - строка 72-75
- `src/file_tokens.py` - строки 42, 114-128, 278-281, 347-349, 529-531
- `src/postprocessing/attachment_evidence_extractor.py` - строки 214, 287
- Документация (множество .md файлов)

**Критерии успеха:**
- [ ] Папка переименована без потери данных
- [ ] Все модули работают с новым путем
- [ ] OCR процессор находит результаты
- [ ] file_tokens корректно подсчитывает токены
- [ ] Pipeline обрабатывает письма без ошибок
- [ ] Обновлена документация

**Оценка времени:** 2-3 часа

---

## Чеклист готовности к продакшену

### Перед деплоем
- [ ] Все критические задачи выполнены
- [ ] Рефакторинг OCR завершён и протестирован
- [ ] Фильтр получателей исправлен и протестирован
- [ ] Внешние письма с 10+ получателями обрабатываются
- [ ] Success rate > 99%
- [ ] Validation errors < 5%
- [ ] Все unit тесты проходят
- [ ] Integration тесты проходят
- [ ] email_035 обрабатывается успешно
- [ ] DaData инициализируется корректно
- [ ] Миграция data/final_results → data/ocr выполнена (опционально)
- [ ] Smoke test на 100 письмах пройден
- [ ] Load test на 1000 письмах пройден
- [ ] Документация обновлена
- [ ] Мониторинг настроен
### После деплоя
- [ ] Мониторинг метрик в течение 24 часов
- [ ] Проверка алертов
- [ ] Анализ новых ошибок
- [ ] Обновление документации по результатам
- [ ] Подтверждение улучшения производительности
---

## Оценка времени

| Фаза | Задачи | Время | Приоритет |
|------|--------|-------|-----------|
| Фаза 1 | 5 задач | 5-8 дней | 🔴 Критический |
| Фаза 2 | 2 задачи | 5 дней | 🟠 Высокий |
| Фаза 3 | 3 задачи | 7 дней | 🟡 Средний |
| Фаза 4 | 4 задачи | 2 недели | 🟢 Низкий |
| **ИТОГО** | **14 задач** | **~1 месяц** | |

**Новые задачи после исследования и уточнений:**
- Задача 1.4: Исправить фильтр получателей (1-2 дня, ВЫСОКИЙ)
- Задача 1.5: CLI меню для выбора дат (1-2 дня, ВЫСОКИЙ)
- Задача 2.1: Версионирование промптов (обновлено)
- Задача 4.4: Миграция data/final_results → data/ocr (2-3 часа, СРЕДНИЙ)

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Рефакторинг OCR сломает существующую функциональность | Средняя | Высокое | Полное тестирование, постепенный rollout |
| Не удастся воспроизвести ошибку email_035 | Средняя | Высокое | Детальное логирование, сохранение debug данных |
| LLM продолжит давать ошибки валидации | Средняя | Среднее | Улучшение промпта + pre-validation |
| Таймауты не исчезнут | Низкая | Среднее | Переход на другого провайдера |
| Производительность не улучшится | Низкая | Низкое | Профилирование и точечная оптимизация |

---

**Дата создания:** 2025-10-06  
**Последнее обновление:** 2025-10-06  
**Статус:** Готов к выполнению