# АРХИТЕКТУРА СИСТЕМЫ
pattern: "Модульная 4-уровневая система"

core_modules:
  - "advanced_email_fetcher.py - Загрузчик писем"
  - "integrated_llm_processor_v3.py - LLM анализ" 
  - "test_improved_ocr_universal.py - Универсальный OCR"
  - "email_loader.py - Загрузчик данных"

data_flow: |
  Письма → OCR обработка → LLM анализ → Экспорт:
  data/emails_data/ → data/attachments/ → 
  data/llm_results/llm_analysis_YYYYMMDD.json

config_structure:
  - "config/ - настройки"
  - "prompts/ - LLM промпты" 
  - ".env - API ключи"