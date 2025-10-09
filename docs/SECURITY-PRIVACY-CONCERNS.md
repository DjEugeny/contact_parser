# 🔒 Безопасность и конфиденциальность данных

## ⚠️ КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ

**Бесплатные модели OpenRouter с суффиксом `:free` публикуют ваши данные в публичные датасеты!**

### Что публикуется:

- ✅ Промпты (системные инструкции)
- ❌ **ДАННЫЕ ИЗ ПИСЕМ** (контакты, телефоны, email, организации)
- ❌ **ПЕРЕПИСКА КЛИЕНТОВ**
- ❌ **КОММЕРЧЕСКИЕ ПРЕДЛОЖЕНИЯ**
- ❌ **ПЕРСОНАЛЬНЫЕ ДАННЫЕ**

### Модели которые ПУБЛИКУЮТ данные:

- `deepseek/deepseek-chat-v3.1:free` ⚠️
- `qwen/qwen3-235b-a22b:free` ⚠️
- `qwen/qwen-2.5-72b-instruct:free` ⚠️
- Любые модели с суффиксом `:free` на OpenRouter ⚠️

## ✅ Безопасные альтернативы

### Вариант 1: Replicate (РЕКОМЕНДУЕТСЯ)

**Преимущества:**
- ✅ НЕ публикует данные
- ✅ Стабильная работа
- ✅ Хорошее качество (DeepSeek v3.1)
- ✅ Разумные лимиты

**Настройка:**
```bash
# В .env уже настроено:
REPLICATE_API_KEY=r8_...
REPLICATE_MODEL=deepseek-ai/deepseek-v3.1
```

**Использование:**
- Replicate уже настроен как резервный провайдер
- Работает автоматически при fallback
- Можно сделать основным провайдером

### Вариант 2: Google Gemini 2.0 Flash (OpenRouter)

**Преимущества:**
- ✅ НЕ требует публикации промптов
- ✅ Огромный context window (1M токенов)
- ✅ Бесплатная
- ⚠️ Иногда rate limits

**Настройка:**
```yaml
# config/models_config.yaml
openrouter:
  models:
    - name: "google/gemini-2.0-flash-exp:free"
      priority: 1
      requires_prompt_publication: false
```

### Вариант 3: Платные модели OpenRouter

**Преимущества:**
- ✅ НЕ публикуют данные
- ✅ Высокое качество
- ✅ Стабильная работа
- ❌ Требуют оплаты

**Примеры:**
- `deepseek/deepseek-chat-v3.1` (без `:free`)
- `anthropic/claude-3-sonnet`
- `openai/gpt-4o`

### Вариант 4: Локальные модели (Ollama)

**Преимущества:**
- ✅ Полная конфиденциальность
- ✅ Нет лимитов
- ✅ Бесплатно
- ❌ Требует мощное железо
- ❌ Медленнее облачных

## 🎯 Рекомендуемая конфигурация

### Для продакшена (с реальными данными):

```yaml
# config/models_config.yaml
openrouter:
  models:
    - name: "google/gemini-2.0-flash-exp:free"
      priority: 1
      requires_prompt_publication: false
      
replicate:
  models:
    - name: "deepseek-ai/deepseek-v3.1"
      priority: 1
```

### Для тестирования (без реальных данных):

```yaml
# config/models_config.yaml
openrouter:
  models:
    - name: "deepseek/deepseek-chat-v3.1:free"
      priority: 1
      requires_prompt_publication: true
      notes: "⚠️ Только для тестов!"
```

## 📋 Чеклист безопасности

Перед запуском в продакшен:

- [ ] Проверить что НЕ используются модели с `:free` от DeepSeek/Qwen
- [ ] Убедиться что `requires_prompt_publication: false` для всех моделей
- [ ] Настроить Replicate как основной или резервный провайдер
- [ ] Отключить настройку "Enable free endpoints that may publish prompts" в OpenRouter
- [ ] Проверить что в логах нет предупреждений о публикации данных

## 🔍 Как проверить текущую конфигурацию

```bash
# Проверить какие модели используются
python -c "from src.config.config_manager import UnifiedConfigManager; cm = UnifiedConfigManager(); cm.print_config_summary()"

# Проверить статус моделей
python src/api_pipeline_validator.py
# Смотрим раздел "СТАТУС МОДЕЛЕЙ (ModelsManager)"
```

## 📞 Что делать если данные уже опубликованы

1. **Немедленно отключить бесплатные модели**
2. **Связаться с OpenRouter support** - попросить удалить данные
3. **Уведомить клиентов** о возможной утечке (если требуется по GDPR)
4. **Сменить API ключи** если они были в промптах
5. **Провести аудит** - какие данные могли быть опубликованы

## 🔗 Полезные ссылки

- OpenRouter Privacy Policy: https://openrouter.ai/privacy
- OpenRouter Settings: https://openrouter.ai/settings/integrations
- Replicate Docs: https://replicate.com/docs
- GDPR Compliance: https://gdpr.eu/

## ⚖️ Юридические аспекты

**GDPR (Европа):**
- Публикация персональных данных без согласия - нарушение
- Штрафы до 4% от годового оборота или €20M

**ФЗ-152 (Россия):**
- Передача ПДн третьим лицам без согласия - нарушение
- Штрафы до 75,000₽ для юрлиц

**Рекомендация:** Используйте только безопасные провайдеры для обработки реальных данных клиентов.
