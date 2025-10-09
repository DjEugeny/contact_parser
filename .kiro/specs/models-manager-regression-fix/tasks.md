# Implementation Plan - Models Manager Regression Fix

**Дата создания:** 2025-10-09  
**Статус:** Готов к выполнению  
**Цель:** Исправить регресс после внедрения ModelsManager, вернуть стабильную работу системы

---

## Фаза 1: Критические исправления конфигурации моделей

- [x] 1. Обновить приоритеты моделей в config/models_config.yaml
  - Переместить deepseek/deepseek-chat-v3.1:free на первую позицию (priority: 1)
  - Переместить google/gemini-2.0-flash-exp:free на вторую позицию (priority: 2)
  - Переместить qwen/qwen-2.5-72b-instruct:free на третью позицию (priority: 3)
  - Переместить qwen/qwen3-235b-a22b:free на четвертую позицию (priority: 4)
  - Добавить метаданные о context window для каждой модели
  - Обновить описания моделей с реальным статусом работы
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 1.1 Добавить информацию о context window в models_config.yaml
  - deepseek/deepseek-chat-v3.1:free: context_window: 64000
  - google/gemini-2.0-flash-exp:free: context_window: 1000000
  - qwen/qwen-2.5-72b-instruct:free: context_window: 32768
  - qwen/qwen3-235b-a22b:free: context_window: 32768
  - _Requirements: 4.2, 4.3_

- [x] 2. Исправить TypeError в organization_deduplicator.py
  - Найти метод _merge_organization_data (строка ~250)
  - Изменить обработку phones: извлекать строки из dict перед созданием set
  - Добавить функцию _extract_phone_strings для нормализации phones
  - Обработать случаи когда phones это list[str] или list[dict]
  - Сохранить метаданные телефонов при объединении
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2.1 Создать вспомогательную функцию _extract_phone_strings
  - Принимает phones: List[Any]
  - Возвращает List[str] с номерами телефонов
  - Обрабатывает dict формат: извлекает 'number' или 'phone' поле
  - Обрабатывает str формат: возвращает как есть
  - Фильтрует пустые значения
  - _Requirements: 2.1, 2.4_

- [x] 2.2 Обновить _merge_organization_data для безопасной работы с phones
  - Использовать _extract_phone_strings для existing_phones
  - Использовать _extract_phone_strings для new_phones
  - Создавать set только из строк
  - Объединять уникальные номера
  - _Requirements: 2.1, 2.2, 2.5_

## Фаза 2: Исправление Circuit Breaker логики

- [x] 2.5 Исправить Circuit Breaker - не блокировать весь провайдер при rate limit
  - Circuit Breaker должен блокировать провайдер только при критических ошибках
  - При rate limit на модели - переключаться на следующую модель, не блокировать провайдер
  - Обновить логику в config_manager.py
  - Различать ошибки модели vs ошибки провайдера
  - _Requirements: 3.2, 3.3, 3.4_

- [x] 2.6 Обновить ModelsManager для правильного переключения при rate limit
  - При rate limit на модели - report_error должен переключить на следующую
  - Не увеличивать счетчик ошибок провайдера при rate limit модели
  - Логировать переключение модели отдельно от блокировки провайдера
  - _Requirements: 3.2, 3.3_

## Фаза 2.1: Улучшение обработки ошибок OpenRouter

- [x] 2.3 Улучшить обработку ошибок в OpenRouterProvider
  - Добавить проверку наличия ключа 'error' в ответе (даже при HTTP 200)
  - Специальная обработка для data policy errors
  - Детальное логирование ошибок с metadata
  - Создать документацию по настройке приватности
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2.4 Создать документацию по настройкам приватности OpenRouter
  - Документ docs/openrouter-privacy-settings.md
  - Инструкции по включению "Enable free endpoints"
  - Альтернативные решения
  - Troubleshooting guide
  - _Requirements: 6.1_

## Фаза 3: Улучшение обработки пустых ответов LLM

- [x] 3. Добавить детекцию пустых ответов в провайдерах
  - Найти OpenRouterProvider и ReplicateProvider
  - После получения ответа проверять длину response
  - Если response пустой или 0 символов - выбрасывать исключение
  - Логировать пустые ответы как error_type: "empty_response"
  - Передавать ошибку в ModelsManager для переключения модели
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3.1 Обновить OpenRouterProvider для детекции пустых ответов
  - В методе generate() после получения response
  - Проверить if not response or len(response.strip()) == 0
  - Выбросить EmptyResponseError с деталями
  - Логировать с контекстом (model, request_id, input_length)
  - _Requirements: 3.1, 3.3_

- [x] 3.2 Обновить ReplicateProvider для детекции пустых ответов
  - В методе generate() после получения response
  - Проверить if not response or len(response.strip()) == 0
  - Выбросить EmptyResponseError с деталями
  - Логировать с контекстом (model, request_id, input_length)
  - _Requirements: 3.1, 3.3_

- [x] 3.3 Создать класс EmptyResponseError
  - Создать в src/exceptions.py или src/providers/exceptions.py
  - Наследовать от Exception
  - Хранить model_name, request_id, input_length
  - Метод __str__ для читаемого сообщения
  - _Requirements: 3.1_

## Фаза 3: Валидация context length перед запросом

- [x] 4. Добавить валидацию размера контекста в ModelsManager
  - Создать метод validate_context_length(provider, text, max_output_tokens)
  - Оценивать количество токенов в тексте (через tiktoken)
  - Сравнивать с context_window модели из конфига
  - Возвращать True если помещается, False если нет
  - Логировать когда модель пропускается из-за размера
  - _Requirements: 4.1, 4.2, 4.3, 4.5_

- [x] 4.1 Обновить ModelsManager.get_current_model для учета context length
  - Добавить параметр estimated_tokens: Optional[int] = None
  - Если estimated_tokens указан, проверять context_window
  - Пропускать модели с недостаточным context window
  - Возвращать первую подходящую модель
  - Логировать пропущенные модели
  - _Requirements: 4.2, 4.3, 4.5_

- [x] 4.2 Интегрировать валидацию в провайдеры
  - В OpenRouterProvider перед запросом оценивать tokens
  - Вызывать models_manager.get_current_model(estimated_tokens=...)
  - Если модель не подходит, пробовать следующую
  - Логировать выбор модели с учетом context length
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

## Фаза 4: Улучшение нормализации телефонов

- [ ] 5. Исправить предупреждения о телефонах без normalized поля
  - Найти где генерируется "Телефон без normalized поля"
  - Проверить порядок: LLM → нормализация → валидация → сохранение
  - Убедиться что нормализация вызывается ДО проверки
  - Для невалидных телефонов (типа "28-54-83") логировать как invalid, не missing
  - Добавить метаданные о причине невалидности
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 5.1 Найти и исправить порядок обработки телефонов
  - Найти PhoneNormalizer и места его вызова
  - Убедиться что normalize() вызывается сразу после извлечения LLM
  - Перед любыми проверками на наличие normalized поля
  - Обновить логирование: различать "не нормализован" vs "невалидный"
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 5.2 Улучшить обработку коротких номеров
  - Для номеров типа "28-54-83" (без кода страны/города)
  - Попытаться извлечь контекст из email/организации
  - Если контекст недоступен, пометить как "incomplete_number"
  - Сохранить оригинал с флагом needs_manual_review: true
  - _Requirements: 5.2, 5.4_

## Фаза 5: Расширенное логирование

- [ ] 6. Улучшить логирование переключений моделей
  - Обновить ModelsManager.report_error для детального логирования
  - Логировать: timestamp, provider, old_model, new_model, error_type, error_message
  - Для empty_response логировать input_length и response_length
  - Для context_length логировать estimated_tokens и model_limit
  - Записывать в data/logs/model_fallback.log
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 6.1 Создать структурированный формат лога переключений
  - JSON формат для каждой записи
  - Поля: timestamp, event_type, provider, old_model, new_model, reason, details
  - details содержит специфичную информацию (tokens, error, etc.)
  - Добавить rotation для лог файла (max 10MB, keep 5 files)
  - _Requirements: 6.1, 6.5_

- [ ] 6.2 Добавить summary логирование при завершении обработки
  - После обработки batch писем выводить статистику
  - Сколько раз переключались модели
  - Какие модели использовались и сколько раз
  - Какие ошибки встречались чаще всего
  - Success rate по каждой модели
  - _Requirements: 6.5_

## Фаза 6: Тестирование исправлений

- [x] 7. Протестировать с исправленной конфигурацией
  - Запустить обработку писем от 2025-07-28 (7 писем)
  - Проверить что нет пустых ответов
  - Проверить что нет TypeError в постобработке
  - Проверить что success rate > 90%
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 7.1 Создать тестовый скрипт test_regression_fix.py
  - Загрузить 7 писем от 2025-07-28
  - Обработать через pipeline
  - Собрать метрики: success_rate, empty_responses, errors
  - Проверить что все письма обработаны
  - Вывести детальный отчет
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 7.2 Запустить тест и проверить результаты
  - Выполнить python test_regression_fix.py
  - Проверить логи на отсутствие TypeError
  - Проверить логи на отсутствие empty_response
  - Проверить что deepseek используется первым
  - Проверить success rate >= 90%
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 7.3 Протестировать большие письма с вложениями
  - Найти письмо с большим количеством OCR текста (email_006)
  - Проверить что context length валидация работает
  - Проверить что система выбирает модель с достаточным context
  - Проверить что нет HTTP 400 ошибок
  - _Requirements: 7.3, 4.1, 4.2, 4.3_

---

## Итоговая статистика

**Всего задач:** 7 основных + 16 подзадач  
**Критических:** 2 задачи (Фаза 1)  
**Высоких:** 2 задачи (Фаза 2-3)  
**Средних:** 2 задачи (Фаза 4-5)  
**Тестирование:** 1 задача (Фаза 6)  

**Оценка времени:** 2-3 часа

**Приоритет выполнения:**
1. Задача 1 - Обновить models_config.yaml (5 минут)
2. Задача 2 - Исправить TypeError (30 минут)
3. Задача 7 - Протестировать (15 минут)
4. Остальные задачи - по необходимости

---

**Дата последнего обновления:** 2025-10-09  
**Статус:** Готов к выполнению

## Быстрый старт

Для немедленного исправления регресса выполните в первую очередь:

1. **Обновите config/models_config.yaml** - поменяйте приоритеты моделей
2. **Исправьте organization_deduplicator.py** - строка 250, метод _merge_organization_data
3. **Запустите тест** - проверьте что регресс устранен

Остальные задачи можно выполнить постепенно для улучшения стабильности.
