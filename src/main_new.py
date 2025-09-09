#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Новая точка входа Contact Parser
Фаза 5: Архитектурная оптимизация с Dependency Injection
"""

import sys
from pathlib import Path

# Добавление корневой директории проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.extractor_factory import ExtractorFactory
from src.config.config_validator import ConfigValidator
from src.cli.interactive_menu import InteractiveMenu
from src.services import EmailService, OCRService, ExportService


def main():
    """🏁 Основная функция приложения"""

    print("🎯 CONTACT PARSER v2.0 - Фаза 5")
    print("Архитектурная оптимизация с Dependency Injection")
    print("=" * 60)

    # Валидация зависимостей
    print("🔍 Валидация зависимостей...")
    if not ExtractorFactory.validate_dependencies():
        print("❌ Критические проблемы с зависимостями!")
        print("Пожалуйста, исправьте ошибки и запустите снова.")
        sys.exit(1)

    # Валидация конфигурации
    print("🔧 Валидация конфигурации...")
    validator = ConfigValidator()
    validation_result = validator.validate_all()

    if not validation_result.is_valid:
        print("❌ Критические проблемы с конфигурацией!")
        validator.print_validation_report(validation_result)
        print("\nПожалуйста, исправьте ошибки и запустите снова.")
        sys.exit(1)
    else:
        print("✅ Конфигурация валидна")

    # Определение режима запуска
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = 'interactive'

    if mode == 'interactive':
        # Интерактивный режим
        print("\n🎮 Запуск интерактивного режима...")
        menu = InteractiveMenu()
        menu.run()

    elif mode == 'test':
        # Тестовый режим
        print("\n🧪 Запуск тестового режима...")
        run_test_mode()

    elif mode == 'validate':
        # Только валидация
        print("\n🔍 Детальный отчет валидации:")
        validator.print_validation_report(validation_result)

    elif mode == 'full-pipeline':
        # Полный пайплайн обработки
        print("\n🔄 Запуск полного пайплайна обработки...")
        run_full_pipeline()

    else:
        print(f"❌ Неизвестный режим: {mode}")
        print("Доступные режимы:")
        print("  interactive - интерактивное меню (по умолчанию)")
        print("  test - тестовый запуск")
        print("  validate - только валидация конфигурации")
        print("  full-pipeline - полный пайплайн обработки")
        sys.exit(1)


def run_full_pipeline():
    """🔄 Демонстрация полного интегрированного пайплайна"""

    print("🚀 ПОЛНЫЙ ПАЙПЛАЙН ОБРАБОТКИ")
    print("=" * 50)

    # Шаг 1: Email Service
    print("\n📧 ШАГ 1: Email Service")
    email_service = EmailService()
    available_dates = email_service.get_available_dates()
    print(f"   📅 Доступные даты: {len(available_dates)}")
    if available_dates:
        print(f"   📅 Примеры: {available_dates[:3]}")

    # Шаг 2: OCR Service
    print("\n🔍 ШАГ 2: OCR Service")
    ocr_service = OCRService()
    ocr_dates = ocr_service.get_available_dates()
    print(f"   📅 Даты для OCR: {len(ocr_dates)}")

    # Шаг 3: LLM Extractor (новая архитектура)
    print("\n🤖 ШАГ 3: LLM Extractor")
    try:
        extractor = ExtractorFactory.create_extractor()
        print("   ✅ Экстрактор инициализирован")
        print("   📊 Статистика экстрактора:")
        stats = extractor.get_stats()
        if 'extractor_stats' in stats:
            ext_stats = stats['extractor_stats']
            print(f"      Запросов: {ext_stats.get('total_requests', 0)}")
            print(f"      Успешных: {ext_stats.get('successful_requests', 0)}")
    except Exception as e:
        print(f"   ❌ Ошибка инициализации: {e}")

    # Шаг 4: Export Service
    print("\n📊 ШАГ 4: Export Service")
    export_service = ExportService()
    export_dates = export_service.get_available_dates()
    print(f"   📅 Даты для экспорта: {len(export_dates)}")

    print("\n🎉 Демонстрация завершена!")
    print("Все сервисы успешно интегрированы в новую архитектуру.")


def run_test_mode():
    """🧪 Тестовый режим работы"""

    try:
        print("🏭 Создание экстрактора...")
        extractor = ExtractorFactory.create_test_extractor()

        # Тестовый текст
        test_text = """
        Здравствуйте!

        Меня зовут Анна Сидорова, руководитель отдела продаж в ООО "МедТех".
        Контактный телефон: 8-800-555-01-23 доб. 456
        Email: anna.sidorova@medtech.ru

        Предлагаем поставку медицинского оборудования:
        - Аппарат УЗИ экспертного класса - 2 500 000 руб.
        - Эндоскопическая стойка - 850 000 руб.

        Итого: 3 350 000 рублей.
        Условия оплаты: 50% предоплата, остаток после поставки.

        С уважением,
        Анна Сидорова
        """

        print("🤖 Тестирование извлечения контактов...")
        result = extractor.extract_all_data(test_text)

        print("\n✅ Результат теста:")
        print("=" * 50)
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))

        # Статистика
        print("\n📊 Статистика:")
        stats = extractor.get_stats()
        extractor_stats = stats.get('extractor_stats', {})
        print(f"   Запросов: {extractor_stats.get('total_requests', 0)}")
        print(f"   Успешных: {extractor_stats.get('successful_requests', 0)}")
        print(f"   Ошибок: {extractor_stats.get('failed_requests', 0)}")

        print("\n🎉 Тест завершен успешно!")

    except Exception as e:
        print(f"❌ Ошибка в тестовом режиме: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
