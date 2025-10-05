#!/bin/bash
# Скрипт для перезапуска процесса обработки писем

echo "🔍 Поиск запущенных процессов обработки..."
PIDS=$(ps aux | grep -i "python.*api_pipeline_validator\|python.*main_new\|python.*process" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "⚠️  Процессы обработки не найдены"
    echo ""
    echo "Для запуска обработки используйте:"
    echo "  python src/api_pipeline_validator.py"
    echo "  или"
    echo "  python src/main_new.py"
    exit 0
fi

echo "📋 Найдены процессы: $PIDS"
echo ""
echo "⚠️  ВНИМАНИЕ: Сейчас будут остановлены следующие процессы:"
for PID in $PIDS; do
    ps -p $PID -o pid,command | tail -1
done

echo ""
read -p "Продолжить? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Отменено"
    exit 1
fi

echo ""
echo "🛑 Остановка процессов..."
for PID in $PIDS; do
    echo "  Останавливаем PID $PID..."
    kill -15 $PID 2>/dev/null
done

echo "⏳ Ожидание завершения процессов (5 сек)..."
sleep 5

# Проверяем, что процессы завершились
REMAINING=$(ps aux | grep -i "python.*api_pipeline_validator\|python.*main_new\|python.*process" | grep -v grep | awk '{print $2}')
if [ ! -z "$REMAINING" ]; then
    echo "⚠️  Некоторые процессы не завершились. Принудительная остановка..."
    for PID in $REMAINING; do
        echo "  Убиваем PID $PID..."
        kill -9 $PID 2>/dev/null
    done
    sleep 2
fi

echo ""
echo "✅ Процессы остановлены"
echo ""
echo "📝 Для запуска обработки писем 016 и 017 используйте:"
echo ""
echo "  cd /Users/evgenyzach/contact_parser"
echo "  python src/api_pipeline_validator.py"
echo ""
echo "После запуска проверьте логи:"
echo "  grep 'TASK-008B' data/logs/*.log | tail -20"
echo ""
