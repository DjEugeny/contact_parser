# План исправления проблемы с некорректным определением вложений

## Обзор

Проблема: вложения из одного письма в thread цепочке некорректно приписываются другим письмам в той же цепочке. 

**Корневая причина**: система использует `thread_id` вместо `message_id` для определения принадлежности вложений к письмам.

## Влияние на существующие модули

### OCR Processor (`src/ocr_processor.py`)
- **Проблема**: Использует имена вложений для поиска уже обработанных OCR-файлов
- **Риск**: При изменении схемы именования вложений существующий кэш OCR-файлов станет невалидным
- **Критичность**: Высокая

### File Tokens (`src/file_tokens.py`)
- **Проблема**: Анализирует связи между письмами и вложениями
- **Риск**: Неправильное сопоставление вложений приведет к неверной статистике токенов
- **Критичность**: Средняя

### Contact Phone Enrichment
- **Проблема**: Извлекает телефоны из вложений
- **Риск**: Телефоны могут быть извлечены из неправильных файлов
- **Критичность**: Средняя

## Комплексный план решения

### Фаза 1: Краткосрочное исправление (1-2 дня)

#### Шаг 1: Модификация имени файла вложения

Изменить метод [`save_attachment_or_inline()`](src/advanced_email_fetcher.py:1318) для включения Message-ID в имя файла:

```python
# Текущий код (строка ~1622):
unique_filename = f"{thread_id}_{timestamp}_{prefix}_{safe_filename}"

# Новый код:
message_id_hash = hashlib.md5(message_id.encode()).hexdigest()[:8]
unique_filename = f"{thread_id}_{message_id_hash}_{timestamp}_{prefix}_{safe_filename}"
```

#### Шаг 2: Обновление логики поиска вложений

Изменить метод [`check_email_processing_status()`](src/advanced_email_fetcher.py:2569):

```python
# Текущий код (строки ~2605-2610):
if thread_id:
    # Ищем файлы с префиксом thread_id
    attachment_files = list(
        attachments_path.glob(f"*{thread_id}*")
    )

# Новый код:
if thread_id and message_id:
    message_id_hash = hashlib.md5(message_id.encode()).hexdigest()[:8]
    # Ищем файлы с префиксом thread_id и message_id_hash
    attachment_files = list(
        attachments_path.glob(f"*{thread_id}_{message_id_hash}_*")
    )
```

#### Шаг 3: Обновление логики восстановления вложений

Изменить метод [`process_single_email()`](src/advanced_email_fetcher.py:1663) в сценарии `download_json`:

```python
# Текущий код (строки ~2104-2107):
attachment_files = list(
    attachments_path.glob(f"*{thread_id}*")
)

# Новый код:
message_id_hash = hashlib.md5(message_id.encode()).hexdigest()[:8]
attachment_files = list(
    attachments_path.glob(f"*{thread_id}_{message_id_hash}_*")
)
```

### Фаза 2: Создание реестра вложений (2-3 дня)

#### Шаг 1: Создание класса AttachmentRegistry

Создать новый файл `src/attachment_registry.py`:

```python
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class AttachmentRegistry:
    """Централизованный реестр для отслеживания связей между письмами и вложениями"""
    
    def __init__(self, data_dir: Path, logger=None):
        self.data_dir = data_dir
        self.logger = logger
        self.registry_file = data_dir / "registry" / "attachment_registry.json"
        self.registry_file.parent.mkdir(exist_ok=True)
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Загрузка реестра из файла"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                if self.logger:
                    self.logger.warning(f"Ошибка загрузки реестра вложений: {self.registry_file}")
        
        return {
            "version": "1.0", 
            "created_at": datetime.now().isoformat(), 
            "attachments": {}
        }
    
    def register_attachment(self, message_id: str, attachment_filename: str, 
                           attachment_path: str, thread_id: str = None) -> str:
        """Регистрация вложения с уникальным ID"""
        attachment_id = f"{message_id}_{attachment_filename}"
        
        self.registry["attachments"][attachment_id] = {
            "message_id": message_id,
            "attachment_filename": attachment_filename,
            "attachment_path": attachment_path,
            "thread_id": thread_id,
            "registered_at": datetime.now().isoformat()
        }
        
        self._save_registry()
        return attachment_id
    
    def get_attachment_by_message(self, message_id: str) -> List[Dict]:
        """Получение всех вложений для конкретного письма"""
        return [
            att for att in self.registry["attachments"].values()
            if att["message_id"] == message_id
        ]
    
    def get_attachment_info(self, attachment_filename: str, message_id: str) -> Optional[Dict]:
        """Получение информации о конкретном вложении"""
        attachment_id = f"{message_id}_{attachment_filename}"
        return self.registry["attachments"].get(attachment_id)
    
    def _save_registry(self):
        """Сохранение реестра в файл"""
        try:
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, ensure_ascii=False, indent=2)
        except IOError as e:
            if self.logger:
                self.logger.error(f"Ошибка сохранения реестра вложений: {e}")
    
    def cleanup_orphaned_attachments(self):
        """Очистка реестра от несуществующих файлов"""
        orphaned = []
        
        for attachment_id, attachment_info in self.registry["attachments"].items():
            attachment_path = Path(attachment_info["attachment_path"])
            if not attachment_path.exists():
                orphaned.append(attachment_id)
        
        for attachment_id in orphaned:
            del self.registry["attachments"][attachment_id]
        
        if orphaned:
            self._save_registry()
            if self.logger:
                self.logger.info(f"Удалено {len(orphaned)} несуществующих вложений из реестра")
        
        return len(orphaned)
```

#### Шаг 2: Интеграция реестра в advanced_email_fetcher.py

Модифицировать класс `AdvancedEmailFetcherV2`:

```python
def __init__(self, logger):
    # ... существующий код ...
    
    # Инициализация реестра вложений
    self.attachment_registry = AttachmentRegistry(self.data_dir, self.logger)

def save_attachment_or_inline_updated(self, part, thread_id: str, date_folder: str, 
                                     message_id: str, is_inline: bool = False):
    """Обновленный метод сохранения вложений с учетом Message-ID"""
    
    # ... существующий код до сохранения файла ...
    
    # Регистрируем вложение в реестре
    attachment_id = self.attachment_registry.register_attachment(
        message_id=message_id,
        attachment_filename=filename,
        attachment_path=str(attachment_path),
        thread_id=thread_id
    )
    
    # Сохраняем вложение с новым форматом имени, включающим attachment_id
    unique_filename = f"{attachment_id}_{timestamp}_{prefix}_{safe_filename}"
    
    # ... остальной код сохранения вложения ...
    
    return {
        "original_filename": filename,
        "saved_filename": unique_filename,
        "file_path": str(attachment_path),
        "relative_path": f"attachments/{date_folder}/{unique_filename}",
        "file_size": file_size,
        "file_type": SUPPORTED_ATTACHMENTS.get(file_ext, "unknown"),
        "content_type": content_type,
        "saved_at": self.get_local_time().isoformat(),
        "status": "saved",
        "is_inline": is_inline,
        "attachment_id": attachment_id,
    }
```

### Фаза 3: Адаптация существующих модулей (1-2 дня)

#### OCR Processor Adapter

Создать файл `src/adapters/ocr_processor_adapter.py`:

```python
from pathlib import Path
from typing import Optional
from ..attachment_registry import AttachmentRegistry
from ..ocr_processor import OCRProcessor

class OCRProcessorAdapter:
    """Адаптер для OCR Processor, обеспечивающий совместимость с новым реестром"""
    
    def __init__(self, data_dir: Path, logger=None):
        self.data_dir = data_dir
        self.logger = logger
        self.attachment_registry = AttachmentRegistry(data_dir, logger)
        self.ocr_processor = OCRProcessor(logger)
    
    def find_attachment_for_email(self, message_id: str, attachment_filename: str) -> Optional[Path]:
        """Поиск вложения для конкретного письма с использованием реестра"""
        attachments = self.attachment_registry.get_attachment_by_message(message_id)
        
        for attachment in attachments:
            if attachment["attachment_filename"] == attachment_filename:
                return Path(attachment["attachment_path"])
        
        return None
    
    def check_existing_results(self, file_path: Path, date: str, message_id: str = None) -> bool:
        """Обновленный метод проверки существующих результатов с использованием реестра"""
        if message_id:
            # Используем реестр для определения правильного вложения
            attachment = self.attachment_registry.get_attachment_info(file_path.name, message_id)
            if attachment:
                # Проверяем существование результатов на основе attachment_id
                attachment_id = attachment.get("attachment_id")
                return self._check_existing_results_by_id(attachment_id, date)
        
        # Fallback к старой логике, если message_id не определен
        return self._check_existing_results_legacy(file_path, date)
    
    def _check_existing_results_by_id(self, attachment_id: str, date: str) -> bool:
        """Проверка результатов по attachment_id"""
        # Реализация проверки на основе attachment_id
        results_path = self.data_dir / "ocr_results" / date / f"{attachment_id}.json"
        return results_path.exists()
    
    def _check_existing_results_legacy(self, file_path: Path, date: str) -> bool:
        """Легаси проверка для обратной совместимости"""
        # Вызов оригинального метода OCRProcessor
        return self.ocr_processor.check_existing_results(file_path, date)
```

#### File Tokens Adapter

Создать файл `src/adapters/file_tokens_adapter.py`:

```python
from typing import Dict, List
from ..attachment_registry import AttachmentRegistry

class FileTokensAdapter:
    """Адаптер для File Tokens с поддержкой реестра вложений"""
    
    def __init__(self, data_dir: Path, logger=None):
        self.data_dir = data_dir
        self.logger = logger
        self.attachment_registry = AttachmentRegistry(data_dir, logger)
    
    def get_attachment_relationships(self, message_id: str) -> List[Dict]:
        """Получение точных связей между письмом и вложениями"""
        return self.attachment_registry.get_attachment_by_message(message_id)
    
    def get_attachment_stats(self, message_id: str) -> Dict:
        """Получение статистики по вложениям для письма"""
        attachments = self.get_attachment_relationships(message_id)
        
        return {
            "total": len(attachments),
            "inline": len([a for a in attachments if a.get("is_inline", False)]),
            "regular": len([a for a in attachments if not a.get("is_inline", False)]),
            "total_size": sum(a.get("file_size", 0) for a in attachments)
        }
```

### Фаза 4: Миграция существующих данных (1-2 дня)

#### Скрипт миграции

Создать файл `scripts/migrate_attachments.py`:

```python
import json
from pathlib import Path
from datetime import datetime
from src.attachment_registry import AttachmentRegistry

class AttachmentMigration:
    """Скрипт миграции существующих данных в новую схему"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.attachment_registry = AttachmentRegistry(data_dir)
        self.emails_dir = data_dir / "emails"
        
    def migrate_existing_attachments(self):
        """Миграция существующих вложений в новую схему"""
        migrated_count = 0
        errors = []
        
        # Проходим по всем папкам с датами
        for date_folder in self.emails_dir.iterdir():
            if not date_folder.is_dir():
                continue
                
            print(f"Обработка папки: {date_folder.name}")
            
            # Обрабатываем все JSON файлы писем за эту дату
            for email_file in date_folder.glob("*.json"):
                try:
                    with open(email_file, 'r', encoding='utf-8') as f:
                        email_data = json.load(f)
                    
                    message_id = email_data.get("message_id")
                    thread_id = email_data.get("thread_id")
                    
                    if not message_id:
                        errors.append(f"Missing message_id in {email_file}")
                        continue
                    
                    # Обрабатываем вложения в письме
                    attachments = email_data.get("attachments", [])
                    for attachment in attachments:
                        attachment_filename = attachment.get("saved_filename")
                        
                        if not attachment_filename:
                            continue
                        
                        # Определяем путь к вложению
                        attachment_path = self.data_dir / "attachments" / date_folder.name / attachment_filename
                        
                        if attachment_path.exists():
                            # Регистрируем вложение в реестре
                            attachment_id = self.attachment_registry.register_attachment(
                                message_id=message_id,
                                attachment_filename=attachment_filename,
                                attachment_path=str(attachment_path),
                                thread_id=thread_id
                            )
                            
                            # Обновляем информацию в письме
                            attachment["attachment_id"] = attachment_id
                            attachment["registered_at"] = datetime.now().isoformat()
                            
                            migrated_count += 1
                    
                    # Сохраняем обновленные данные письма
                    with open(email_file, 'w', encoding='utf-8') as f:
                        json.dump(email_data, f, ensure_ascii=False, indent=2)
                        
                except Exception as e:
                    errors.append(f"Error processing {email_file}: {e}")
        
        # Очистка реестра от несуществующих файлов
        orphaned_count = self.attachment_registry.cleanup_orphaned_attachments()
        
        return {
            "migrated_count": migrated_count,
            "errors": errors,
            "orphaned_count": orphaned_count
        }
    
    def create_backup(self):
        """Создание резервной копии данных"""
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.data_dir / f"backup_before_migration_{timestamp}"
        
        # Копируем папки с письмами и вложениями
        if (self.data_dir / "emails").exists():
            shutil.copytree(self.data_dir / "emails", backup_dir / "emails")
        
        if (self.data_dir / "attachments").exists():
            shutil.copytree(self.data_dir / "attachments", backup_dir / "attachments")
        
        print(f"Резервная копия создана: {backup_dir}")
        return backup_dir

if __name__ == "__main__":
    data_dir = Path("data")
    migration = AttachmentMigration(data_dir)
    
    print("Создание резервной копии...")
    backup_dir = migration.create_backup()
    
    print("Запуск миграции...")
    result = migration.migrate_existing_attachments()
    
    print(f"Миграция завершена:")
    print(f"  - Сопоставлено вложений: {result['migrated_count']}")
    print(f"  - Удалено неработающих ссылок: {result['orphaned_count']}")
    print(f"  - Ошибок: {len(result['errors'])}")
    
    if result['errors']:
        print("Ошибки миграции:")
        for error in result['errors'][:10]:  # Показываем первые 10 ошибок
            print(f"  - {error}")
```

## Порядок внедрения исправлений

### Фаза 1: Краткосрочное исправление (1-2 дня)
1. Внести изменения в метод `save_attachment_or_inline()`
2. Обновить метод `check_email_processing_status()`
3. Изменить логику в `process_single_email()` для сценария `download_json`
4. Протестировать на новых письмах
5. Создать скрипт миграции для существующих вложений (опционально)

### Фаза 2: Создание реестра (2-3 дня)
1. Разработать класс `AttachmentRegistry`
2. Интегрировать реестр в `AdvancedEmailFetcherV2`
3. Обновить методы сохранения вложений
4. Провести тестирование на новых письмах

### Фаза 3: Адаптация модулей (1-2 дня)
1. Создать адаптер для OCR Processor
2. Создать адаптер для File Tokens
3. Обновить Contact Phone Enrichment
4. Провести тестирование адаптеров

### Фаза 4: Миграция данных (1-2 дня)
1. Разработать скрипт миграции
2. Создать резервные копии данных
3. Провести миграцию на копии данных
4. Провести валидацию результатов миграции
5. Применить миграцию к рабочим данным

## Тестирование исправлений

### Тест-кейс 1: Письма без вложений
- Проверить, что письма без вложений не показывают вложения от других писем

### Тест-кейс 2: Письма с вложениями
- Проверить, что письма с вложениями показывают только свои вложения

### Тест-кейс 3: Цепочки писем
- Проверить, что в thread с несколькими письмами каждое письмо показывает только свои вложения

### Тест-кейс 4: Обратная совместимость
- Проверить, что старые письма продолжают работать корректно

### Тест-кейс 5: OCR Processor
- Проверить, что OCR-обработка работает с новым реестром
- Проверить, что существующий кэш OCR-файлов остается доступным

### Тест-кейс 6: File Tokens
- Проверить, что статистика токенов рассчитывается корректно
- Проверить, что связи между письмами и вложениями определяются правильно

### Тест-кейс 7: Contact Phone Enrichment
- Проверить, что телефоны извлекаются из правильных вложений
- Проверить, что обогащение контактов работает корректно

## Риски и митигация

### Риск 1: Потеря существующих вложений
- **Митигация**: Создать резервную копию перед миграцией
- **Митигация**: Реализовать скрипт миграции с проверкой целостности

### Риск 2: Увеличение времени обработки
- **Митигация**: Оптимизировать поиск вложений по индексу
- **Митигация**: Кешировать результаты поиска вложений

### Риск 3: Проблемы с обратной совместимостью
- **Митигация**: Создать адаптеры для существующих модулей
- **Митигация**: Реализовать fallback к старой логике при необходимости

### Риск 4: Ошибки миграции данных
- **Митигация**: Проводить миграцию на копии данных сначала
- **Митигация**: Реализовать валидацию результатов миграции
- **Митигация**: Сохранять детальные логи миграции

## Критерии успеха

1. ✅ Каждое письмо показывает только свои вложения
2. ✅ Цепочки писем работают корректно
3. ✅ Обработка новых писем работает без ошибок
4. ✅ Существующие данные доступны после миграции
5. ✅ OCR Processor работает без сбоев
6. ✅ File Tokens рассчитывает корректную статистику
7. ✅ Contact Phone Enrichment извлекает данные из правильных вложений
8. ✅ Производительность не ухудшилась значительно

## Временные рамки

- **Фаза 1 (краткосрочное исправление)**: 1-2 дня разработки + 1 день тестирования
- **Фаза 2 (создание реестра)**: 2-3 дня разработки + 1 день тестирования
- **Фаза 3 (адаптация модулей)**: 1-2 дня разработки + 1 день тестирования
- **Фаза 4 (миграция данных)**: 1-2 дня разработки + 1 день тестирования

**Общее время**: 5-10 дней + 3-4 дня тестирования

## Необходимые ресурсы

- 1 разработчик для краткосрочного исправления
- 1 разработчик + 1 тестировщик для полного решения
- Время для миграции данных (около 1-2 часов для ~1000 вложений)
- Дополнительное время для тестирования адаптеров

## Заключение

Предложенный план обеспечивает комплексное решение проблемы с вложениями, учитывающее все существующие зависимости в системе. Поэтапный подход позволяет минимизировать риски и обеспечить плавный переход к новой архитектуре.

Ключевые преимущества решения:
- Точное сопоставление вложений с письмами
- Сохранение функциональности существующих модулей
- Возможность отката изменений при необходимости
- Масштабируемость для будущих улучшений