#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для диагностики подключения к почтовому серверу.
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.fetcher.utils.connection_diagnostic import main
    
    if __name__ == "__main__":
        main()
except ImportError as e:
    print(f"❌ Ошибка импорта модуля диагностики: {e}")
    print("Убедитесь что файл src/fetcher/utils/connection_diagnostic.py существует")
    sys.exit(1)