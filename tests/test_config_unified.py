#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест унифицированного конфигурационного менеджера
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import UnifiedConfigManager

def test_unified_config():
    """🧪 Тест унифицированного конфигурационного менеджера"""
    print("🧪 ТЕСТИРОВАНИЕ УНИФИЦИРОВАННОГО КОНФИГУРАЦИОННОГО МЕНЕДЖЕРА")
    print("=" * 60)

    config_manager = UnifiedConfigManager()

    # Тест валидации
    print("\n1️⃣ ВАЛИДАЦИЯ КОНФИГУРАЦИИ:")
    validation = config_manager.validate_configuration()
    print(f"   Валидность: {'✅' if validation['valid'] else '❌'}")
    if validation['errors']:
        print("   Ошибки:")
        for error in validation['errors']:
            print(f"     ❌ {error}")
    if validation['warnings']:
        print("   Предупреждения:")
        for warning in validation['warnings']:
            print(f"     ⚠️  {warning}")

    # Тест провайдеров
    print("\n2️⃣ ТЕСТ ПРОВАЙДЕРОВ:")
    providers = config_manager.get_llm_providers()
    print(f"   Найдено провайдеров: {len(providers)}")
    for provider in providers:
        status = "✅ Активен" if provider.active else "❌ Отключен"
        print(f"   {provider.name}: {status} (приоритет {provider.priority})")
        print(f"     Модель: {provider.model}")
        print(f"     API ключ: {'✅ Настроен' if provider.api_key else '❌ Отсутствует'}")

    # Тест обработки
    print("\n3️⃣ ТЕСТ НАСТРОЕК ОБРАБОТКИ:")
    processing = config_manager.get_processing_config()
    print(f"   Диапазон дат: {processing.start_date} - {processing.end_date}")
    print(f"   Пропускать обработанные: {processing.skip_processed}")
    print(f"   Параллельность: {processing.max_parallel}")
    print(f"   Токен-based chunking: {processing.use_token_based_chunking}")
    print(f"   Макс. токенов на чанк: {processing.max_tokens_per_chunk}")

    # Тест экспорта
    print("\n4️⃣ ТЕСТ НАСТРОЕК ЭКСПОРТА:")
    export = config_manager.get_export_config()
    print(f"   Google Sheet: {export.google_sheet_name}")
    print(f"   Sheet ID: {'✅ Настроен' if export.google_sheet_id else '❌ Отсутствует'}")
    print(f"   Confidence threshold: {export.confidence_threshold}")
    print(f"   Data directory: {export.data_dir}")

    # Тест IMAP
    print("\n5️⃣ ТЕСТ IMAP НАСТРОЕК:")
    imap = config_manager.get_imap_config()
    print(f"   Сервер: {imap['server'] or '❌ Не задан'}")
    print(f"   Порт: {imap['port']}")
    print(f"   Пользователь: {'✅ Настроен' if imap['user'] else '❌ Отсутствует'}")
    print(f"   SSL: {imap['use_ssl']}")

    # Сводка конфигурации
    print("\n📋 СВОДКА КОНФИГУРАЦИИ:")
    config_manager.print_config_summary()

    print("\n" + "=" * 60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    test_unified_config()
