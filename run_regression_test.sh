#!/bin/bash
# Wrapper для запуска регрессионного теста с таймаутом

echo "🚀 Запуск регрессионного теста..."
echo "⏱️  Максимальное время: 5 минут"
echo ""

# Запускаем тест в фоне
python test_regression_fix.py &
PID=$!

# Ждем максимум 300 секунд (5 минут)
TIMEOUT=300
ELAPSED=0

while kill -0 $PID 2>/dev/null; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo ""
        echo "⏰ Таймаут! Убиваем процесс..."
        kill -9 $PID 2>/dev/null
        echo "❌ Тест прерван по таймауту"
        exit 1
    fi
    
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    
    # Показываем прогресс каждые 30 секунд
    if [ $((ELAPSED % 30)) -eq 0 ]; then
        echo "⏳ Прошло ${ELAPSED} секунд..."
    fi
done

# Проверяем код возврата
wait $PID
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Тест завершен успешно!"
else
    echo "❌ Тест завершен с ошибками (код: $EXIT_CODE)"
fi

exit $EXIT_CODE
