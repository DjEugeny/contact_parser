# Tasks — Simplified Strategy Phone Sanitizer Fix

- [x] Дополнить санитайзер `LLMResponseValidator` преобразованием строковых полей и телефонов в строки, собрать статистику `converted_to_string`.
- [x] Привести PostProcessor к использованию `as_text`/`as_float` для строковых полей контактов, организаций, interactions, КП.
- [x] Добавить/обновить юнит-тесты санитайзера и постпроцессора (кейс с числовым телефоном).
- [x] Обновить документацию (PLAN-002 и дизайн постпроцессинга) с упоминанием типизации строковых полей.
- [x] Прогнать `api_pipeline_validator.py --mode first10` и убедиться, что письмо `email_016_20250729_20250729_dna-technology_ru_6360137e.json` проходит без ошибки `expected string or bytes-like object`.
- [x] Зафиксировать результаты прогонов в отчёте `memory-bank/reports/`.
