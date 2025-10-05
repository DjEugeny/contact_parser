#!/bin/bash
# Скрипт для переобработки письма 016 с новым кодом

echo "🔄 Переобработка письма 016"
echo "="

# Шаг 1: Сохраняем старый файл
echo "📦 Сохранение старого обработанного файла..."
OLD_FILE="data/llm_results/2025-07-29/email_016_20250729_20250729_dna_technology_ru_6360137e_20251005_001450_001639_processed.json"
if [ -f "$OLD_FILE" ]; then
    mv "$OLD_FILE" "${OLD_FILE}.old"
    echo "✅ Старый файл сохранен как ${OLD_FILE}.old"
else
    echo "⚠️ Старый файл не найден: $OLD_FILE"
fi

# Шаг 2: Запускаем обработку через api_pipeline_validator
echo ""
echo "🚀 Запуск обработки письма 016..."
echo "="
python src/api_pipeline_validator.py --mode first10 --start "email_016_20250729_20250729_dna-technology_ru_6360137e.json" --count 1

# Шаг 3: Проверяем результат
echo ""
echo "="
echo "🔍 Проверка результата..."
python test_debug_location_enrichment.py
