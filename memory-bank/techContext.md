# Технический стек

**Языки и окружение**

* Python 3.13
* IDE: VS Code + Cursor AI

**OCR**

* easyocr
* pytesseract
* transformers (TrOCR)

**Парсинг документов**

* PyMuPDF (fitz)
* python-docx
* openpyxl, xlrd

**LLM-доступ**

* OpenRouter API (qwen3-235b-a22b\:free; альтернативы: llama, phi-3)
* Groq API (llama3-8b-8192) - fallback провайдер
* Replicate API (Llama 3-8b-instruct)

**Интеграции**

* Почта: imaplib
* Gmail API (опционально)
* Экспорт: gspread + Google Sheets API, Google Contacts API

**CI/CD и тестирование**

* GitHub Actions
* pytest + coverage

**Логирование**

* встроенный logging
* emoji/цветовое форматирование

---

### Required .env

```env
# OpenRouter (основной провайдер)
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=qwen/qwen3-235b-a22b:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Groq (fallback провайдер)
GROQ_API_KEY=...
GROQ_MODEL=llama3-8b-8192
GROQ_BASE_URL=https://api.groq.com/openai/v1

# Replicate
REPLICATE_API_KEY=...
REPLICATE_MODEL=meta/meta-llama-3-8b-instruct

# Почта
IMAP_EMAIL=s.voronova@dna-technology.ru
IMAP_PASSWORD=...
IMAP_SERVER=...
IMAP_PORT=143
```

### Fallback система LLM

* **Приоритет 1**: OpenRouter (основной)
* **Приоритет 2**: Groq (fallback при ошибках)
* **Автоматическое переключение**: При rate limits, квотах, таймаутах
* **Максимум попыток**: 2 для избежания зацикливания
* **Мониторинг**: Отслеживание здоровья провайдеров