#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📧 Тестовый запуск исправленного IMAP-парсера с подробным логированием
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
import logging
from src.advanced_email_fetcher import setup_logging, AdvancedEmailFetcherV2, EXCLUDED_EXTENSIONS

def run_test():
    """Тестовый запуск с ограниченным временным диапазоном"""
    
    # Настройка временного диапазона
    end_date = datetime.now()  # Сегодня
    start_date = end_date - timedelta(days=1)  # 1 день назад
    
    # Настраиваем логирование с подробным выводом
    logs_dir = Path("data/logs")
    logger = setup_logging(logs_dir, start_date, end_date)
    
    # Информация о фильтрах
    logger.info("🔎 ТЕСТОВЫЙ ЗАПУСК ПАРСЕРА С ПРОВЕРКОЙ ФИЛЬТРАЦИИ:")
    logger.info(f"🚫 Исключаемые расширения: {', '.join(sorted(EXCLUDED_EXTENSIONS))}")
    
    # Создаем экземпляр парсера
    fetcher = AdvancedEmailFetcherV2(logger)
    
    # Включаем подробное логирование размеров
    fetcher.enable_size_logging = True
    
    # Выводим список специфических исключений
    if hasattr(fetcher, 'specific_excluded_files'):
        logger.info(f"🚫 Специальные исключения: {', '.join(sorted(fetcher.specific_excluded_files))}")
    
    # Запускаем загрузку писем
    try:
        emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
        
        # Выводим статистику
        logger.info("📊 СТАТИСТИКА ФИЛЬТРАЦИИ:")
        logger.info(f"✉️  Всего обработано писем: {fetcher.stats['processed']}")
        logger.info(f"✅ Сохранено писем: {fetcher.stats['saved']}")
        logger.info(f"📎 Сохранено вложений: {fetcher.stats['saved_attachments']}")
        logger.info(f"🖼️  Сохранено встроенных изображений: {fetcher.stats['saved_inline_images']}")
        logger.info(f"🚫 Исключено по расширению: {fetcher.stats['excluded_attachments']}")
        logger.info(f"🚫 Исключено по имени файла: {fetcher.stats['excluded_filenames']}")
        logger.info(f"🚫 Исключено по размеру: {fetcher.stats['excluded_by_size']}")
        logger.info(f"🚫 Исключено по размерам изображения: {fetcher.stats['excluded_by_image_dimensions']}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")
    finally:
        fetcher.close()
        logger.info("🏁 ЗАВЕРШЕНИЕ ТЕСТОВОГО ЗАПУСКА")

if __name__ == "__main__":
    run_test()
