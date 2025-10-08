# 17_DEPLOYMENT_OPTIONS — Варианты автоматического запуска и размещения

**Дата:** 2025-06-10  
**Статус:** Актуально

## 1. Обзор

Система обработки писем должна запускаться автоматически для ежедневной обработки новых писем. Рассмотрим варианты от простого локального запуска до полноценного облачного размещения.

## 2. Вариант 1: Локальный запуск на macOS (самый простой)

### 2.1. Через cron
**Преимущества:**
- Простая настройка
- Не требует дополнительных сервисов
- Бесплатно

**Недостатки:**
- Компьютер должен быть включен
- Нет мониторинга выполнения
- Ручное управление логами

**Настройка:**
```bash
# Редактирование crontab
crontab -e

# Добавить строку для запуска каждый день в 2:00 ночи
0 2 * * * cd /path/to/project && /path/to/venv/bin/python api_pipeline_validator.py --date yesterday >> /path/to/logs/cron.log 2>&1
### 2.2. Через launchd (рекомендуется для macOS)

**Преимущества:**
- Нативный для macOS
- Автоматический перезапуск при ошибках
- Лучшее логирование

**Недостатки:**
- Чуть сложнее настройка
- Компьютер должен быть включен

**Настройка:**

Создать файл ~/Library/LaunchAgents/com.minicrm.daily-sync.plist:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.minicrm.daily-sync</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>/path/to/project/api_pipeline_validator.py</string>
        <string>--date</string>
        <string>yesterday</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/path/to/project</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/path/to/logs/minicrm-sync.log</string>
    
    <key>StandardErrorPath</key>
    <string>/path/to/logs/minicrm-sync-error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

Загрузить и запустить:

```bash
# Загрузить задачу
launchctl load ~/Library/LaunchAgents/com.minicrm.daily-sync.plist

# Проверить статус
launchctl list | grep minicrm

# Запустить вручную для теста
launchctl start com.minicrm.daily-sync

# Остановить
launchctl stop com.minicrm.daily-sync

# Выгрузить задачу
launchctl unload ~/Library/LaunchAgents/com.minicrm.daily-sync.plist
```

## 3. Вариант 2: Облачные платформы (рекомендуется для продакшена)

### 3.1. Railway.app

**Преимущества:**
- Простое развертывание из GitHub
- $5/месяц бесплатного кредита
- Автоматические деплои при push
- Встроенный cron через Railway Cron Jobs

**Недостатки:**
- Платно после бесплатного кредита (~$5-10/месяц)

**Настройка:**

1. Создать аккаунт на railway.app
2. Подключить GitHub репозиторий
3. Добавить переменные окружения
4. Создать Cron Job:
   ```bash
   # В Railway Dashboard -> Cron Jobs
   Schedule: 0 2 * * *
   Command: python api_pipeline_validator.py --date yesterday
   ```

Dockerfile для Railway:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "api_pipeline_validator.py", "--date", "yesterday"]
```

### 3.2. Render.com

**Преимущества:**
- Бесплатный тариф для cron jobs
- Простая настройка
- Автоматические деплои

**Недостатки:**
- Бесплатный тариф засыпает после 15 минут неактивности
- Ограничения по CPU/памяти

**Настройка:**

1. Создать аккаунт на render.com
2. Создать новый Cron Job
3. Подключить GitHub репозиторий
4. Настроить расписание: `0 2 * * *`
5. Команда: `python api_pipeline_validator.py --date yesterday`

### 3.3. Fly.io

**Преимущества:**
- Бесплатный тариф (3 shared-cpu VMs)
- Быстрое развертывание
- Поддержка cron через fly-cron

**Недостатки:**
- Требует кредитную карту
- Чуть сложнее настройка

**Настройка:**

```bash
# Установка Fly CLI
brew install flyctl

# Логин
flyctl auth login

# Инициализация проекта
flyctl launch

# Добавить секреты
flyctl secrets set SUPABASE_URL=xxx SUPABASE_SERVICE_KEY=xxx

# Деплой
flyctl deploy
```

fly.toml:

```toml
app = "minicrm-sync"

[build]
  dockerfile = "Dockerfile"

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    port = 80

[deploy]
  release_command = "python api_pipeline_validator.py --date yesterday"

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

### 3.4. DigitalOcean App Platform

**Преимущества:**
- $5/месяц за базовый worker
- Простая настройка cron jobs
- Хорошая документация

**Недостатки:**
- Платно с первого дня
- Нет бесплатного тарифа

**Настройка:**

1. Создать App из GitHub репозитория
2. Выбрать тип: Worker
3. Добавить переменные окружения
4. Настроить cron в app.yaml:

```yaml
name: minicrm-sync
workers:
- name: daily-sync
  github:
    repo: your-username/mini-crm
    branch: main
  run_command: python api_pipeline_validator.py --date yesterday
  envs:
  - key: SUPABASE_URL
    value: ${SUPABASE_URL}
  - key: SUPABASE_SERVICE_KEY
    value: ${SUPABASE_SERVICE_KEY}
  
jobs:
- name: daily-email-sync
  kind: CRON
  schedule: "0 2 * * *"
  run_command: python api_pipeline_validator.py --date yesterday
```

## 4. Вариант 3: AWS Lambda + EventBridge (для масштабирования)

**Преимущества:**
- Serverless — платите только за выполнение
- Автоматическое масштабирование
- Бесплатный тариф: 1M запросов/месяц

**Недостатки:**
- Сложная настройка
- Ограничение по времени выполнения (15 минут)
- Требует упаковки зависимостей

**Настройка:**

1. Упаковать код в Lambda-совместимый формат
2. Создать Lambda функцию
3. Настроить EventBridge rule для ежедневного запуска
4. Добавить переменные окружения

handler.py для Lambda:

```python
import json
import os
from api_pipeline_validator import run_pipeline

def lambda_handler(event, context):
    """AWS Lambda handler для ежедневной синхронизации"""
    
    try:
        # Запуск конвейера
        result = run_pipeline(date='yesterday')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Pipeline completed successfully',
                'result': result
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Pipeline failed',
                'error': str(e)
            })
        }
```

EventBridge Rule (через AWS CLI):

```bash
aws events put-rule \
  --name minicrm-daily-sync \
  --schedule-expression "cron(0 2 * * ? *)"

aws events put-targets \
  --rule minicrm-daily-sync \
  --targets "Id"="1","Arn"="arn:aws:lambda:region:account:function:minicrm-sync"
```

## 5. Вариант 4: GitHub Actions (простой и бесплатный)

**Преимущества:**
- Полностью бесплатно для публичных репозиториев
- 2000 минут/месяц для приватных
- Простая настройка через YAML
- Встроенные секреты

**Недостатки:**
- Ограничение по времени выполнения (6 часов)
- Не подходит для очень частых запусков

**Настройка:**

Создать .github/workflows/daily-sync.yml:

```yaml
name: Daily Email Sync

on:
  schedule:
    # Запуск каждый день в 2:00 UTC
    - cron: '0 2 * * *'
  workflow_dispatch: # Ручной запуск

jobs:
  sync:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run pipeline
      env:
        SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
        SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
        IMAP_HOST: ${{ secrets.IMAP_HOST }}
        IMAP_USER: ${{ secrets.IMAP_USER }}
        IMAP_PASS: ${{ secrets.IMAP_PASS }}
        GOOGLE_VISION_KEY: ${{ secrets.GOOGLE_VISION_KEY }}
        LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
      run: |
        python api_pipeline_validator.py --date yesterday
    
    - name: Upload logs
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: sync-logs
        path: logs/
```

Добавить секреты в GitHub:

Settings -> Secrets and variables -> Actions
Добавить все необходимые переменные окружения

## 6. Сравнительная таблица

| Вариант | Стоимость | Сложность | Надежность | Мониторинг | Рекомендация |
|---------|-----------|-----------|------------|------------|--------------|
| cron (macOS) | Бесплатно | Низкая | Низкая | Нет | Для тестирования |
| launchd (macOS) | Бесплатно | Средняя | Средняя | Базовый | Для локальной разработки |
| GitHub Actions | Бесплатно* | Низкая | Высокая | Встроенный | Рекомендуется для старта |
| Railway | $5-10/мес | Низкая | Высокая | Встроенный | Для продакшена |
| Render | Бесплатно/Платно | Низкая | Средняя | Встроенный | Альтернатива Railway |
| Fly.io | Бесплатно* | Средняя | Высокая | Встроенный | Для масштабирования |
| DigitalOcean | $5/мес | Средняя | Высокая | Встроенный | Для стабильности |
| AWS Lambda | ~$0-5/мес | Высокая | Высокая | CloudWatch | Для enterprise |

*Бесплатно с ограничениями

## 7. Рекомендуемый путь развития

### Этап 1: Разработка (сейчас)
- Локальный запуск через launchd на macOS
- Ручное тестирование и отладка
- Проверка работы с Supabase

### Этап 2: MVP (после завершения разработки)
- GitHub Actions для автоматического ежедневного запуска
- Бесплатно и надежно
- Простая настройка через YAML
- Встроенное логирование

### Этап 3: Продакшен (при активном использовании)
- Railway или Render для постоянного размещения
- Добавить веб-интерфейс (FastAPI + React в Orchids.app)
- Настроить мониторинг и алерты
- Автоматические бэкапы

### Этап 4: Масштабирование (при росте нагрузки)
- AWS Lambda или Fly.io для serverless архитектуры
- Параллельная обработка писем
- CDN для статики
- Кэширование запросов

## 8. Мониторинг и алерты

### 8.1. Базовый мониторинг

Добавить в конец скрипта отправку уведомлений:

```python
import requests
from datetime import datetime

def send_notification(status, message):
    """Отправка уведомления о результате выполнения"""
    
    # Telegram Bot
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if telegram_token and telegram_chat_id:
        text = f"🤖 Mini-CRM Sync\n\n"
        text += f"Status: {status}\n"
        text += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"Message: {message}"
        
        requests.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            json={"chat_id": telegram_chat_id, "text": text}
        )

# В конце api_pipeline_validator.py
if __name__ == "__main__":
    try:
        result = run_pipeline()
        send_notification("✅ SUCCESS", f"Processed {result['emails_count']} emails")
    except Exception as e:
        send_notification("❌ ERROR", str(e))
        raise
```

### 8.2. Продвинутый мониторинг
- Sentry для отслеживания ошибок
- Datadog или New Relic для метрик
- UptimeRobot для проверки доступности

## 9. Следующие шаги

- ✅ Выбрать вариант запуска (рекомендуется: launchd для разработки, GitHub Actions для MVP)
- ⏳ Настроить выбранный вариант
- ⏳ Протестировать автоматический запуск
- ⏳ Настроить уведомления о результатах
- ⏳ Добавить мониторинг ошибок
- ⏳ Документировать процесс для команды

## 10. Чеклист перед запуском в продакшен

- [ ] Все переменные окружения настроены
- [ ] Supabase подключение работает
- [ ] IMAP доступ проверен
- [ ] LLM API ключи валидны
- [ ] Логирование настроено
- [ ] Уведомления работают
- [ ] Бэкапы настроены
- [ ] Тестовый запуск успешен
- [ ] Документация обновлена
- [ ] Команда проинформирована