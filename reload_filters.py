#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔄 Утилита для перезагрузки фильтров из конфигурационных файлов
"""

import os
import sys
from pathlib import Path
import logging

from src.config.paths import CONFIG_DIR, ensure_config_structure

# Настраиваем простой логгер
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FilterReloader")

def reload_filters():
    """Перезагружает фильтры из конфигурационных файлов"""
    
    ensure_config_structure()
    config_dir = CONFIG_DIR
    
    # Проверяем наличие конфигурационных файлов
    filters = {
        "filename_excludes": config_dir / "attachment_filename_excludes.txt",
        "subject_filters": config_dir / "filters.txt",
        "blacklist": config_dir / "blacklist.txt"
    }
    
    for filter_name, file_path in filters.items():
        if not file_path.exists():
            logger.error(f"⚠️ Файл {file_path} не найден!")
            continue
            
        # Подсчитываем количество активных правил (не комментариев)
        active_rules = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    active_rules += 1
        
        logger.info(f"✅ {filter_name}: загружено {active_rules} активных правил из {file_path}")
    
    # Проверяем правила для презентаций
    presentation_rules = ["Презентация*", "Sales*"]
    filename_excludes_path = filters["filename_excludes"]
    
    if filename_excludes_path.exists():
        with open(filename_excludes_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        for rule in presentation_rules:
            if rule in content:
                logger.info(f"✅ Правило '{rule}' найдено в {filename_excludes_path}")
            else:
                logger.warning(f"⚠️ Правило '{rule}' НЕ НАЙДЕНО в {filename_excludes_path}")
    
    logger.info(f"\n👉 Перезагрузите программу, чтобы фильтры вступили в силу!")
    logger.info(f"👉 Выполните 'python test_email_run.py' для проверки работы фильтров")

if __name__ == "__main__":
    reload_filters()
