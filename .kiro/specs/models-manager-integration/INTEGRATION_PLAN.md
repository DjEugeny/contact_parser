# 🔧 План интеграции ModelsManager в существующий код

## 📋 Текущая ситуация

### Что есть сейчас:
- ✅ `UnifiedConfigManager` в `src/config/config_manager.py`
- ✅ Метод `get_llm_providers()` загружает модели из `.env`
- ✅ Модели жестко прописаны в коде:
  ```python
  model=os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat-v3.1:free')
  ```

### Что создано:
- ✅ `ModelsManager` в `src/config/models_manager.py`
- ✅ `config/models_config.yaml` с приоритетами моделей
- ✅ Автоматический fallback при ошибках

## 🎯 Цель интеграции

Заменить жесткие модели из `.env` на динамические из `models_config.yaml` с автоматическим fallback.

## 📝 План интеграции (3 шага)

### Шаг 1: Интеграция в UnifiedConfigManager

**Файл:** `src/config/config_manager.py`

**Изменения:**

```python
# В начале файла добавить импорт
from config.models_manager import ModelsManager

class UnifiedConfigManager:
    def __init__(self, config_dir: Optional[Path] = None):
        # ... существующий код ...
        
        # 🆕 ДОБАВИТЬ: Менеджер моделей
        self.models_manager = ModelsManager()
        
        # ... остальной код ...
    
    def get_llm_providers(self) -> List[LLMProviderConfig]:
        """🤖 Получить конфигурацию всех LLM провайдеров"""
        self._ensure_env_loaded()
        
        providers = []
        
        # 🆕 ИЗМЕНИТЬ: Получаем модель из ModelsManager
        if openrouter_key := os.getenv('OPENROUTER_API_KEY'):
            # Получаем текущую модель из менеджера
            or_model = self.models_manager.get_current_model('openrouter')
            
            providers.append(LLMProviderConfig(
                name="OpenRouter",
                api_key=openrouter_key,
                model=or_model.name if or_model else 'qwen/qwen3-235b-a22b:free',
                base_url=os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1/chat/completions'),
                priority=1,
                active=True
            ))
        
        # 🆕 ИЗМЕНИТЬ: Получаем модель из ModelsManager
        if replicate_key := os.getenv('REPLICATE_API_KEY'):
            # Получаем текущую модель из менеджера
            rep_model = self.models_manager.get_current_model('replicate')
            
            providers.append(LLMProviderConfig(
                name="Replicate",
                api_key=replicate_key,
                model=rep_model.name if rep_model else 'deepseek-ai/deepseek-v3.1',
                base_url="https://api.replicate.com/v1/predictions",
                priority=2,
                active=True
            ))
        
        # ... остальной код ...
        
        return providers
```

### Шаг 2: Добавить обработку ошибок с fallback

**Файл:** `src/providers/openrouter.py` (или где обрабатываются ошибки)

**Изменения:**

```python
async def make_request(self, data: dict) -> dict:
    """Выполнить запрос к OpenRouter с fallback"""
    try:
        response = await self._do_request(data)
        
        # 🆕 ДОБАВИТЬ: При успехе сбрасываем на первую модель
        if hasattr(self.config_manager, 'models_manager'):
            self.config_manager.models_manager.reset_to_first_model('openrouter')
        
        return response
        
    except Exception as e:
        error_message = str(e)
        
        # 🆕 ДОБАВИТЬ: Сообщаем об ошибке менеджеру
        if hasattr(self.config_manager, 'models_manager'):
            switched = self.config_manager.models_manager.report_error(
                'openrouter',
                error_message
            )
            
            if switched:
                # Модель переключена, обновляем конфигурацию
                new_model = self.config_manager.models_manager.get_current_model('openrouter')
                self.config.model = new_model.name
                
                logger.info(f"🔄 Переключились на модель: {new_model.name}")
                
                # Пробуем еще раз с новой моделью
                return await self._do_request(data)
        
        # Если не переключились, пробрасываем ошибку дальше
        raise
```

### Шаг 3: Добавить логирование статуса моделей

**Файл:** `src/api_pipeline_validator.py` (или главный файл)

**Изменения:**

```python
def main():
    # ... существующий код ...
    
    # 🆕 ДОБАВИТЬ: Показываем статус моделей при запуске
    if hasattr(config_manager, 'models_manager'):
        print("\n📊 СТАТУС МОДЕЛЕЙ:")
        config_manager.models_manager.print_status()
    
    # ... остальной код ...
```

## 🧪 Тестирование интеграции

### 1. Создать тестовый файл

**Файл:** `test_integration.py`

```python
#!/usr/bin/env python3
"""Тест интеграции ModelsManager"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.config_manager import UnifiedConfigManager

def test_integration():
    print("🧪 ТЕСТ ИНТЕГРАЦИИ MODELS MANAGER")
    print("=" * 50)
    
    # Создаем config manager
    config = UnifiedConfigManager()
    
    # Проверяем наличие models_manager
    if hasattr(config, 'models_manager'):
        print("✅ ModelsManager интегрирован")
        
        # Показываем статус
        config.models_manager.print_status()
        
        # Получаем провайдеров
        providers = config.get_llm_providers()
        print(f"\n📋 Провайдеры ({len(providers)}):")
        for p in providers:
            print(f"   {p.priority}. {p.name}: {p.model}")
        
        print("\n✅ Интеграция работает!")
    else:
        print("❌ ModelsManager не найден")

if __name__ == "__main__":
    test_integration()
```

### 2. Запустить тест

```bash
python test_integration.py
```

Ожидаемый вывод:
```
✅ ModelsManager интегрирован
📊 СТАТУС МОДЕЛЕЙ:
   OpenRouter: qwen/qwen3-235b-a22b:free
   Replicate: deepseek-ai/deepseek-v3.1
✅ Интеграция работает!
```

## 📊 Преимущества после интеграции

### До интеграции:
- ❌ Модели жестко прописаны в `.env`
- ❌ При ошибке модели нужно вручную менять `.env`
- ❌ Нет автоматического fallback
- ❌ Нет логирования переключений

### После интеграции:
- ✅ Модели в отдельном конфиге `models_config.yaml`
- ✅ Автоматическое переключение при ошибках
- ✅ Приоритизация моделей (1, 2, 3, 4, 5)
- ✅ Логирование всех переключений
- ✅ Информация о требованиях приватности
- ✅ Легко добавлять новые модели

## 🔄 Обратная совместимость

Система полностью обратно совместима:

1. Если `models_config.yaml` не найден → используются модели из `.env`
2. Если `ModelsManager` не инициализирован → работает как раньше
3. Можно постепенно мигрировать провайдеры

## 📝 Чеклист интеграции

- [ ] Шаг 1: Добавить `ModelsManager` в `UnifiedConfigManager.__init__()`
- [ ] Шаг 2: Изменить `get_llm_providers()` для использования `ModelsManager`
- [ ] Шаг 3: Добавить обработку ошибок с fallback в провайдерах
- [ ] Шаг 4: Добавить логирование статуса моделей при запуске
- [ ] Шаг 5: Создать и запустить `test_integration.py`
- [ ] Шаг 6: Протестировать на реальных данных
- [ ] Шаг 7: Проверить логи переключений в `data/logs/model_fallback.log`

## 🎯 Следующие шаги

### Сейчас (минимальная интеграция):
1. Добавить `ModelsManager` в `UnifiedConfigManager`
2. Использовать модели из `models_config.yaml`
3. Протестировать базовую работу

### Потом (полная интеграция):
1. Добавить автоматический fallback при ошибках
2. Интегрировать во все провайдеры
3. Добавить мониторинг переключений

### В будущем (расширенные возможности):
1. Веб-интерфейс для управления моделями
2. Статистика использования моделей
3. Автоматическая оптимизация приоритетов

## 🔗 Связанные файлы

- `src/config/config_manager.py` - основной конфиг (изменить)
- `src/config/models_manager.py` - менеджер моделей (готов)
- `config/models_config.yaml` - конфигурация моделей (готов)
- `src/providers/openrouter.py` - провайдер OpenRouter (изменить)
- `src/providers/replicate.py` - провайдер Replicate (изменить)

---

## ❓ Вопросы?

### Q: Нужно ли удалять модели из `.env`?
**A:** Нет, оставьте для обратной совместимости. Они будут использоваться как fallback.

### Q: Что если `models_config.yaml` не найден?
**A:** Система автоматически использует модели из `.env` (как сейчас).

### Q: Можно ли использовать только для одного провайдера?
**A:** Да, можно интегрировать постепенно (сначала OpenRouter, потом Replicate).

### Q: Как откатиться назад?
**A:** Просто удалите строку `self.models_manager = ModelsManager()` из `__init__`.

---

**Готово к интеграции:** ✅  
**Время интеграции:** ~30 минут  
**Риск:** Низкий (обратная совместимость)  
**Польза:** Высокая (автоматический fallback)
