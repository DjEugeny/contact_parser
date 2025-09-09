# 🧪 ФАЗА 7: ТЕСТИРОВАНИЕ И НАДЕЖНОСТЬ - НАЧАЛО РАБОТ

**Дата создания:** 2025-09-09 17:45 (UTC+07)
**Статус:** 🔄 АКТИВНАЯ ФАЗА
**Продолжительность:** 3-4 дня (план)
**Цель:** Полное unit и integration тестирование с реальными данными

---

## 🎯 Цели Фазы 7

### Основные направления тестирования:
1. **Unit тестирование** - модульные тесты для всех компонентов
2. **Integration тестирование** - тестирование с реальными API и данными
3. **Мониторинг и логирование** - метрики производительности и надежности

### Данные для тестирования:
- **26 реальных email файлов** из 2025-07-29
- **Реальные вложения** (PDF коммерческие предложения)
- **Разные типы контента** (технические письма, КП, переписка)
- **Реальные контакты** для валидации извлечения

---

## 📊 Структура данных для тестирования

### Email файлы (JSON):
```json
{
  "thread_id": "20250729_dna-technology_ru_6360137e",
  "from": "m.gogoleva@dna-technology.ru",
  "to": "ivak@millab.ru",
  "subject": "Re: ФБУЗ \"Центр Гигиены и Эпидемиологии в Республике Хакасия\"",
  "body": "Добрый день, Иван Алексеевич!\nКП во вложении...",
  "attachments": [
    {
      "filename": "Ком.пред.29.07.2025.pdf",
      "path": "attachments/2025-07-29/...",
      "size": 314173,
      "status": "saved"
    }
  ]
}
```

### Вложения:
- **Коммерческие предложения** (PDF)
- **Техническая документация**
- **Размер:** от 300KB до 1MB
- **Количество:** 4+ вложений на письмо

---

## 🧪 План реализации Фазы 7

### 7.1 Unit Тестирование (Сегодня, 2-3 часа)

#### Создание тестовой инфраструктуры:
```python
# tests/__init__.py
# tests/conftest.py (pytest fixtures)
# tests/fixtures/ (тестовые данные)
```

#### Основные тесты:
- **`test_extractor.py`** - тестирование ContactExtractor
- **`test_providers.py`** - тестирование LLM провайдеров
- **`test_validator.py`** - тестирование JSON Schema валидации
- **`test_config_validator.py`** - тестирование конфигурации
- **`test_phone_normalization.py`** - тестирование нормализации телефонов
- **`test_cache_manager.py`** - тестирование кэширования

#### Fixtures для тестов:
```python
# tests/fixtures/sample_emails.json
# tests/fixtures/mock_responses.json
# tests/fixtures/test_configs.json
```

### 7.2 Integration Тестирование (Сегодня, 3-4 часа)

#### Тестирование с реальными данными:
- **Тестирование на 26 email файлах** из 2025-07-29
- **Тестирование обработки вложений** (PDF с КП)
- **Тестирование fallback сценариев** между провайдерами
- **Нагрузочное тестирование** (параллельная обработка)
- **Тестирование circuit breaker** при ошибках API

#### Метрики производительности:
```python
# Измерение:
- Время обработки одного письма
- Количество извлеченных контактов
- Точность извлечения (precision/recall)
- Использование памяти
- Cache hit rate
- API response times
```

### 7.3 Мониторинг и Логирование (Завтра, 2-3 часа)

#### Структурированное логирование:
```python
import logging
import structlog

# Метрики производительности
from prometheus_client import Counter, Histogram

# Логирование по провайдерам
provider_metrics = {
    'openrouter_requests': Counter('openrouter_requests_total', 'Total requests to OpenRouter'),
    'groq_requests': Counter('groq_requests_total', 'Total requests to Groq'),
    'replicate_requests': Counter('replicate_requests_total', 'Total requests to Replicate'),
    'request_duration': Histogram('llm_request_duration_seconds', 'Request duration in seconds'),
    'tokens_used': Counter('tokens_used_total', 'Total tokens used'),
    'api_cost': Counter('api_cost_total', 'Total API cost')
}
```

#### Мониторинг метрик:
- **Успешность запросов** по провайдерам
- **Время ответа API**
- **Количество ошибок** и таймаутов
- **Использование токенов**
- **Стоимость API** запросов

---

## 🔧 Реализация Unit Тестирования

### Создание базовой структуры тестов:
```python
# tests/test_extractor.py
import pytest
from src.core.extractor_factory import ExtractorFactory

class TestContactExtractor:
    """Тестирование ContactExtractor"""

    @pytest.fixture
    def extractor(self):
        """Фикстура для создания экстрактора"""
        return ExtractorFactory.create_extractor()

    @pytest.fixture
    def sample_email_data(self):
        """Фикстура с тестовыми данными email"""
        return {
            'text': 'Контакт: Иван Иванов, тел: +7(999)123-45-67, email: ivan@test.com',
            'metadata': {'source': 'test'}
        }

    def test_extract_contacts_basic(self, extractor, sample_email_data):
        """Тест базового извлечения контактов"""
        result = extractor.extract_all_data(
            sample_email_data['text'],
            sample_email_data['metadata']
        )

        assert 'contacts' in result
        assert len(result['contacts']) > 0
        assert result['contacts'][0]['name'] == 'Иван Иванов'

    def test_phone_normalization(self, extractor):
        """Тест нормализации телефонов"""
        text = 'Телефон: 8(495)123-45-67 доб.123'
        result = extractor.extract_all_data(text)

        contacts = result.get('contacts', [])
        assert len(contacts) > 0
        assert 'normalized_phone' in contacts[0]
        assert contacts[0]['normalized_phone'] == '74951234567'

    def test_cache_functionality(self, extractor):
        """Тест работы кэширования"""
        text = 'Тестовый текст для кэширования'

        # Первый запрос
        result1 = extractor.extract_all_data(text)

        # Второй запрос (должен использовать кэш)
        result2 = extractor.extract_all_data(text)

        # Проверяем, что результаты одинаковые
        assert result1['contacts'] == result2['contacts']

        # Проверяем статистику кэша
        cache_stats = extractor.cache.get_cache_stats()
        assert cache_stats['total_requests'] > 0
```

### Создание mock объектов:
```python
# tests/conftest.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_provider():
    """Mock для LLM провайдера"""
    mock = Mock()
    mock.make_request.return_value = {
        'content': '{"contacts": [], "business_context": "test", "commercial_offers": []}',
        'provider': 'mock',
        'response_time': 0.1
    }
    return mock

@pytest.fixture
def mock_llm_response():
    """Mock ответ от LLM"""
    return {
        'content': '''{
            "contacts": [
                {
                    "name": "Иван Петров",
                    "phone": "+7(999)123-45-67",
                    "email": "ivan@test.com",
                    "organization": "Тестовая компания",
                    "position": "Менеджер",
                    "confidence": 0.95
                }
            ],
            "business_context": "Запрос информации о продукте",
            "commercial_offers": []
        }''',
        'provider': 'openrouter',
        'response_time': 1.5
    }
```

---

## 🚀 Реализация Integration Тестирования

### Тестирование на реальных данных:
```python
# tests/test_integration_real_data.py
import pytest
from pathlib import Path
import json

class TestIntegrationRealData:
    """Integration тесты на реальных данных"""

    @pytest.fixture
    def real_email_files(self):
        """Фикстура с реальными email файлами"""
        email_dir = Path('data/emails/2025-07-29')
        return list(email_dir.glob('*.json'))[:5]  # Первые 5 файлов

    def test_process_real_emails(self, extractor, real_email_files):
        """Тест обработки реальных email файлов"""
        results = []

        for email_file in real_email_files:
            # Загружаем данные
            with open(email_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)

            # Обрабатываем текст
            text = email_data.get('body', '')[:3000]  # Ограничиваем для теста
            result = extractor.extract_all_data(text, {
                'file_name': email_file.name,
                'source': 'real_data_test'
            })

            results.append(result)

            # Проверяем структуру ответа
            assert 'contacts' in result
            assert 'business_context' in result
            assert 'commercial_offers' in result
            assert 'processing_time' in result

        # Агрегируем результаты
        total_contacts = sum(len(r.get('contacts', [])) for r in results)
        avg_processing_time = sum(r.get('processing_time', 0) for r in results) / len(results)

        print(f"📊 Обработано {len(results)} писем")
        print(f"👥 Извлечено {total_contacts} контактов")
        print(".2f"
### Тестирование fallback сценариев:
```python
def test_provider_fallback(self, extractor):
    """Тест fallback между провайдерами"""
    # Имитируем ошибку первого провайдера
    extractor.config.provider_manager.providers['openrouter'].is_available.return_value = False

    text = "Тестовый текст для fallback"
    result = extractor.extract_all_data(text)

    # Проверяем, что использовался fallback провайдер
    assert result['provider_used'] in ['groq', 'replicate']
    assert 'contacts' in result
```

---

## 📈 Реализация Мониторинга

### Структурированное логирование:
```python
# src/core/monitoring.py
import logging
import structlog
from prometheus_client import Counter, Histogram, Gauge
import time

class LLMMetricsCollector:
    """Сборщик метрик для LLM операций"""

    def __init__(self):
        # Счетчики запросов
        self.requests_total = Counter(
            'llm_requests_total',
            'Total LLM requests',
            ['provider', 'status']
        )

        # Гистограмма времени ответа
        self.request_duration = Histogram(
            'llm_request_duration_seconds',
            'Request duration in seconds',
            ['provider']
        )

        # Калибровка использования токенов
        self.tokens_used = Counter(
            'llm_tokens_used_total',
            'Total tokens used',
            ['provider', 'operation']
        )

        # Стоимость API
        self.api_cost = Counter(
            'llm_api_cost_total',
            'Total API cost in USD',
            ['provider']
        )

        # Активные соединения
        self.active_connections = Gauge(
            'llm_active_connections',
            'Number of active connections',
            ['provider']
        )

    def record_request(self, provider: str, duration: float,
                      tokens: int = 0, cost: float = 0.0,
                      status: str = 'success'):
        """Запись метрик запроса"""
        self.requests_total.labels(provider=provider, status=status).inc()
        self.request_duration.labels(provider=provider).observe(duration)

        if tokens > 0:
            self.tokens_used.labels(provider=provider, operation='extraction').inc(tokens)

        if cost > 0:
            self.api_cost.labels(provider=provider).inc(cost)

    def get_metrics_summary(self):
        """Получение сводки метрик"""
        return {
            'total_requests': self.requests_total._value,
            'avg_response_time': self.request_duration._sum / self.request_duration._count,
            'total_tokens': self.tokens_used._value,
            'total_cost': self.api_cost._value
        }
```

---

## 📋 План выполнения

### День 1: Unit Тестирование (Сегодня)
- [ ] Создать структуру папки `tests/`
- [ ] Реализовать базовые unit тесты
- [ ] Создать fixtures с тестовыми данными
- [ ] Протестировать основные компоненты

### День 2: Integration Тестирование (Сегодня)
- [ ] Тестирование на реальных email файлах
- [ ] Тестирование обработки вложений
- [ ] Тестирование fallback сценариев
- [ ] Нагрузочное тестирование

### День 3: Мониторинг и Финализация
- [ ] Реализовать структурированное логирование
- [ ] Добавить метрики производительности
- [ ] Создать отчет по результатам тестирования
- [ ] Обновить документацию

---

## 🎯 Ожидаемые результаты

### Метрики качества:
- **Coverage unit тестов:** > 80%
- **Точность извлечения контактов:** > 90% (precision/recall)
- **Время обработки письма:** < 5 сек
- **Успешность API запросов:** > 95%
- **Cache hit rate:** > 50%

### Надежность:
- **Обработка ошибок:** Graceful degradation
- **Fallback система:** Автоматическое переключение
- **Мониторинг:** Полная видимость состояния
- **Логирование:** Структурированные логи

---

**Начало Фазы 7: Тестирование и Надежность**
**Дата:** 2025-09-08 17:45
**Статус:** 🔄 В ПРОЦЕССЕ
