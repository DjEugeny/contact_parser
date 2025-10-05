#!/bin/bash
echo "🔄 Быстрая переобработка письма 016"
python src/api_pipeline_validator.py --mode first10 --start "email_016_20250729_20250729_dna-technology_ru_6360137e.json" --count 1 2>&1 | tail -50
