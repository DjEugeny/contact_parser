# 📋 Факты проекта и файловая структура Contact Parser

**Дата создания:** 2025-08-24 11:04 (UTC+07)  
**Версия:** 1.0  
**Статус:** Полная документация структуры проекта

---

## 🎯 Ключевые факты проекта

### Общая информация:
- **Название:** Contact Parser
- **Тип:** Система автоматизированного извлечения контактов
- **Язык:** Python 3.x
- **Архитектура:** Модульная система с четким разделением ответственности
- **Основная цель:** Извлечение контактной информации из email-писем и вложений

### Технологический стек:
- **Backend:** Python 3.x
- **OCR:** Google Cloud Vision API
- **LLM:** OpenRouter, Groq, Replicate
- **Email:** IMAP протокол
- **Export:** Google Sheets API
- **Data Storage:** JSON файлы, локальная файловая система

### Ключевые возможности:
- ✅ Загрузка писем с IMAP серверов
- ✅ OCR обработка изображений и документов
- ✅ LLM анализ для извлечения контактов
- ✅ Экспорт в Google Sheets
- ✅ Система фильтрации спама
- ✅ Обработка множественных форматов файлов
- ✅ Rate limiting и fallback механизмы

### Статистика кода:
- **Основных модулей:** 7
- **Строк кода в ключевых файлах:**
  - `advanced_email_fetcher.py`: 2079 строк
  - `google_sheets_exporter.py`: 702 строки
  - `google_sheets_bridge.py`: 782 строки
  - `ocr_processor.py`: 593 строки
  - `integrated_llm_processor.py`: ~300+ строк
  - `email_loader.py`: 182 строки
  - `llm_extractor.py`: ~400+ строк

---

## 📁 Полная файловая структура проекта

```
contact_parser/
├── 📁 src/                              # Исходный код
│   ├── 📄 advanced_email_fetcher.py     # Загрузка писем с IMAP (2079 строк)
│   ├── 📄 google_sheets_exporter.py     # Экспорт в Google Sheets (702 строки)
│   ├── 📄 google_sheets_bridge.py       # Мост LLM-Sheets (782 строки)
│   ├── 📄 integrated_llm_processor.py   # Центральный процессор
│   ├── 📄 llm_extractor.py             # LLM извлечение контактов
│   ├── 📄 ocr_processor.py             # OCR обработка (593 строки)
│   ├── 📄 email_loader.py              # Загрузчик писем (182 строки)
│   └── 📄 local_exporter.py            # Локальный экспорт
│
├── 📁 data/                             # Данные проекта
│   ├── 📁 emails/                       # Обработанные письма
│   │   └── 📁 YYYY-MM-DD/              # Папки по датам
│   │       ├── 📄 email_001.json       # JSON файлы писем
│   │       ├── 📄 email_002.json
│   │       └── 📄 ...
│   │
│   ├── 📁 attachments/                  # Вложения писем
│   │   └── 📁 YYYY-MM-DD/              # Папки по датам
│   │       ├── 📁 thread_001/          # Папки по потокам
│   │       │   ├── 📄 document.pdf
│   │       │   ├── 📄 image.png
│   │       │   └── 📄 spreadsheet.xlsx
│   │       └── 📁 thread_002/
│   │           └── 📄 ...
│   │
│   ├── 📁 final_results/               # Результаты обработки
│   │   ├── 📁 texts/                   # OCR результаты
│   │   │   └── 📁 YYYY-MM-DD/
│   │   │       ├── 📄 ocr_results_001.json
│   │   │       └── 📄 ocr_results_002.json
│   │   │
│   │   ├── 📁 reports/                 # OCR отчеты
│   │   │   └── 📁 YYYY-MM-DD/
│   │   │       └── 📄 ocr_summary.json
│   │   │
│   │   └── 📁 llm_analysis/            # LLM анализ
│   │       └── 📁 YYYY-MM-DD/
│   │           ├── 📄 analysis_results.json
│   │           ├── 📄 contacts_extracted.json
│   │           └── 📄 processing_stats.json
│   │
│   ├── 📁 logs/                        # Логи системы
│   │   ├── 📄 email_processing_*.log   # Логи загрузки писем
│   │   ├── 📄 ocr_processing_*.log     # Логи OCR
│   │   └── 📄 llm_processing_*.log     # Логи LLM
│   │
│   └── 📁 skipped/                     # Пропущенные письма
│       ├── 📄 skipped_emails.json      # Реестр пропущенных
│       └── 📄 dead_letters.json        # Проблемные письма
│
├── 📁 prompts/                         # Промпты для LLM
│   ├── 📄 contact_extraction.txt       # Основной промпт
│   └── 📄 backup_contact_extraction.txt # Резервный промпт
│
├── 📁 config/                          # Конфигурация
│   └── 📁 filters/                     # Фильтры писем
│       ├── 📄 subject_blacklist.txt    # Черный список тем
│       ├── 📄 sender_blacklist.txt     # Черный список отправителей
│       └── 📄 filename_blacklist.txt   # Черный список файлов
│
├── 📁 memory-bank/                     # База знаний
│   ├── 📁 reports/                     # Отчеты и анализ
│   │   ├── 📄 project_architecture_analysis.md
│   │   └── 📄 project_facts_and_structure.md
│   │
│   ├── 📁 decisions/                   # Архитектурные решения
│   └── 📁 progress/                    # Прогресс разработки
│
├── 📄 .env                             # Переменные окружения
├── 📄 .env.example                     # Пример переменных
├── 📄 service_account.json             # Google API ключи
├── 📄 requirements.txt                 # Python зависимости
├── 📄 README.md                        # Документация проекта
└── 📄 tasks.md                         # Задачи и планы
```

---

## 🔧 Детали модулей

### 1. `advanced_email_fetcher.py` (2079 строк)
**Назначение:** Первичная загрузка писем с IMAP сервера

**Ключевые классы:**
- `EmailFilters` - фильтрация спама и нежелательных писем
- `AdvancedEmailFetcherV2` - основной класс загрузки

**Основные функции:**
- Подключение к IMAP серверу
- Загрузка писем за диапазон дат
- Скачивание и сохранение вложений
- Фильтрация по черным спискам
- Обработка больших файлов
- Retry логика и обработка ошибок

**Поддерживаемые форматы вложений:**
- Документы: PDF, DOC, DOCX, TXT
- Таблицы: XLS, XLSX, XLSM
- Изображения: JPG, JPEG, PNG, BMP, TIFF, WEBP

---

### 2. `google_sheets_exporter.py` (702 строки)
**Назначение:** Экспорт результатов в Google Sheets

**Основные функции:**
- Инициализация Google Sheets API
- Создание новых таблиц
- Экспорт контактов, коммерческих предложений
- Интерактивное меню пользователя
- Статистика и отчетность

**Структура экспорта:**
- Лист "Контакты" - извлеченные контакты
- Лист "Коммерческие предложения" - найденные предложения
- Лист "Статистика" - метрики обработки

---

### 3. `google_sheets_bridge.py` (782 строки)
**Назначение:** Интеграционный слой между обработкой и экспортом

**Ключевые функции:**
- Координация между модулями
- Автоматическая загрузка писем при отсутствии
- Fallback механизмы
- Локальный экспорт как резерв

---

### 4. `integrated_llm_processor.py`
**Назначение:** Центральный процессор для LLM анализа

**Основные функции:**
- Загрузка обработанных писем
- Интеграция с OCR процессором
- Вызов LLM для извлечения контактов
- Сбор и сохранение статистики
- Rate limiting и управление нагрузкой

---

### 5. `llm_extractor.py`
**Назначение:** Извлечение контактов через LLM

**LLM провайдеры:**
- **OpenRouter** (основной) - доступ к множеству моделей
- **Groq** (резервный) - быстрые инференсы
- **Replicate** (резервный) - облачные модели

**Функции:**
- Инициализация провайдеров
- Система fallback
- Парсинг JSON ответов
- Обработка ошибок API

---

### 6. `ocr_processor.py` (593 строки)
**Назначение:** OCR обработка документов и изображений

**Технологии:**
- **Google Cloud Vision** - основной OCR движок
- **PyMuPDF** - извлечение текста из PDF
- **python-docx** - обработка DOCX
- **openpyxl/xlrd** - чтение Excel файлов

**Возможности:**
- Умное сжатие изображений
- Обработка больших файлов
- Нормализация имен файлов
- Кэширование результатов

---

### 7. `email_loader.py` (182 строки)
**Назначение:** Загрузка и фильтрация обработанных писем

**Функции:**
- Сканирование папок с письмами
- Загрузка JSON файлов
- Фильтрация писем с вложениями
- Проверка статуса обработки

---

## 📊 Форматы данных

### Email JSON структура:
```json
{
  "message_id": "unique-message-id",
  "thread_id": "thread-identifier",
  "from": "sender@example.com",
  "to": ["recipient@example.com"],
  "subject": "Email subject",
  "date": "2025-01-24T10:30:00+07:00",
  "body_text": "Email content...",
  "attachments": [
    {
      "filename": "document.pdf",
      "file_path": "path/to/file",
      "status": "saved",
      "size": 1024000
    }
  ]
}
```

### OCR результат:
```json
{
  "file_path": "path/to/file",
  "extracted_text": "Recognized text...",
  "confidence": 0.95,
  "processing_time": 2.5,
  "method": "google_vision",
  "timestamp": "2025-01-24T10:30:00+07:00"
}
```

### LLM анализ:
```json
{
  "contacts": [
    {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890",
      "company": "Example Corp"
    }
  ],
  "commercial_offers": [
    {
      "type": "service",
      "description": "Web development services",
      "price": "$5000"
    }
  ],
  "processing_stats": {
    "total_emails": 10,
    "processed_emails": 8,
    "contacts_found": 15,
    "processing_time": 120.5
  }
}
```

---

## 🔐 Безопасность и конфиденциальность

### Обработка чувствительных данных:
- 🔑 API ключи в переменных окружения
- 📧 Локальное хранение писем
- 🚫 Фильтрация персональных данных
- 🔒 Безопасное подключение к IMAP (SSL/TLS)

### Файлы конфигурации:
- `.env` - переменные окружения (не в git)
- `service_account.json` - Google API ключи (не в git)
- `config/filters/` - правила фильтрации

---

## 📈 Производительность

### Оптимизации:
- 📦 Batch обработка писем
- ⏱️ Rate limiting для API
- 💾 Кэширование OCR результатов
- 🔄 Retry логика с экспоненциальной задержкой
- 📊 Умное сжатие изображений

### Ограничения:
- 📧 Batch размер: 50 писем
- 🖼️ Максимальный размер изображения: 19MB
- ⏰ Таймаут запросов: 300 секунд
- 🔄 Максимальные повторы: 5 попыток

---

## 🛠️ Зависимости

### Основные библиотеки:
```
# Email и IMAP
imaplib, email

# OCR и обработка документов
google-cloud-vision
PyMuPDF (fitz)
python-docx
openpyxl, xlrd
Pillow (PIL)

# LLM провайдеры
requests (для API)

# Google Sheets
gspread
google-auth

# Утилиты
python-dotenv
pathlib
json
logging
```

---

## 🚀 Развертывание

### Требования к системе:
- Python 3.8+
- Доступ к интернету
- Google Cloud Vision API
- Google Sheets API
- IMAP доступ к почтовому серверу

### Шаги установки:
1. Клонирование репозитория
2. Установка зависимостей: `pip install -r requirements.txt`
3. Настройка `.env` файла
4. Настройка Google API ключей
5. Запуск: `python src/google_sheets_exporter.py`

---

**Конец документации**