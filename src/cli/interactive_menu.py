#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🖥️ Интерактивное меню для Contact Parser
Фаза 5: Архитектурная оптимизация
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from ..core.extractor_factory import ExtractorFactory
from ..core.extractor import ContactExtractor
from ..config.config_validator import ConfigValidator
from ..config.paths import PROJECT_ROOT, get_config_path


class InteractiveMenu:
    """🖥️ Интерактивное меню для управления Contact Parser"""

    def __init__(self):
        self.extractor: Optional[ContactExtractor] = None
        self.config_validator = ConfigValidator()

    def run(self):
        """🚀 Запуск интерактивного меню"""
        print("🎯 CONTACT PARSER - ИНТЕРАКТИВНОЕ МЕНЮ")
        print("=" * 50)
        print("Фаза 5: Архитектурная оптимизация")
        print("=" * 50)

        while True:
            self._show_main_menu()
            choice = input("\nВыберите действие (1-8): ").strip()

            if choice == '1':
                self._validate_configuration()
            elif choice == '2':
                self._initialize_extractor()
            elif choice == '3':
                self._run_extraction_test()
            elif choice == '4':
                self._show_statistics()
            elif choice == '5':
                self._run_batch_processing()
            elif choice == '6':
                self._manage_providers()
            elif choice == '7':
                self._system_diagnostics()
            elif choice == '8':
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Попробуйте еще раз.")

            input("\nНажмите Enter для продолжения...")

    def _show_main_menu(self):
        """📋 Отображение главного меню"""
        print("\n" + "=" * 50)
        print("ГЛАВНОЕ МЕНЮ")
        print("=" * 50)
        print("1. 🔍 Валидация конфигурации")
        print("2. 🚀 Инициализация экстрактора")
        print("3. 🧪 Тест извлечения контактов")
        print("4. 📊 Просмотр статистики")
        print("5. 📦 Пакетная обработка")
        print("6. ⚙️  Управление провайдерами")
        print("7. 🔧 Системная диагностика")
        print("8. 🚪 Выход")
        print("=" * 50)

        if self.extractor:
            print("✅ Экстрактор инициализирован")
        else:
            print("❌ Экстрактор не инициализирован")

    def _validate_configuration(self):
        """🔍 Валидация конфигурации"""
        print("\n🔍 ВАЛИДАЦИЯ КОНФИГУРАЦИИ")
        print("-" * 30)

        result = self.config_validator.validate_all()
        self.config_validator.print_validation_report(result)

        if result.is_valid:
            print("\n🎉 Конфигурация валидна! Можно инициализировать экстрактор.")
        else:
            print("\n⚠️  Исправьте критические ошибки перед продолжением.")

    def _initialize_extractor(self):
        """🚀 Инициализация экстрактора"""
        print("\n🚀 ИНИЦИАЛИЗАЦИЯ ЭКСТРАКТОРА")
        print("-" * 30)

        # Сначала валидация
        result = self.config_validator.validate_all()
        if not result.is_valid:
            print("❌ Невозможно инициализировать экстрактор: конфигурация невалидна")
            return

        try:
            print("🏭 Создание экстрактора с Dependency Injection...")
            self.extractor = ExtractorFactory.create_extractor()
            print("✅ Экстрактор успешно инициализирован!")
        except Exception as e:
            print(f"❌ Ошибка инициализации экстрактора: {e}")

    def _run_extraction_test(self):
        """🧪 Тест извлечения контактов"""
        print("\n🧪 ТЕСТ ИЗВЛЕЧЕНИЯ КОНТАКТОВ")
        print("-" * 30)

        if not self.extractor:
            print("❌ Экстрактор не инициализирован")
            return

        # Пример текста для тестирования
        test_text = """
        Добрый день!

        Меня зовут Иван Петров, я менеджер по продажам в компании ООО "ТехноСервис".
        Мой телефон: +7 (495) 123-45-67, дополнительный: доб. 123.
        Email: ivan.petrov@technoservice.ru

        Мы предлагаем поставку лабораторного оборудования:
        1. Амплификатор DNA - 150 000 руб.
        2. Центрифуга - 75 000 руб.

        Общая сумма: 225 000 руб.
        Срок поставки: 30 дней.

        С уважением,
        Иван Петров
        """

        print("📝 Тестовый текст:")
        print("-" * 50)
        print(test_text[:200] + "..." if len(test_text) > 200 else test_text)
        print("-" * 50)

        try:
            print("\n🤖 Запуск извлечения...")
            start_time = datetime.now()

            result = self.extractor.extract_all_data(test_text)

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            print("\n✅ Результат:")
            print("-" * 50)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("-" * 50)
            print(f"⏱️  Время обработки: {processing_time:.2f} сек")
        except Exception as e:
            print(f"❌ Ошибка извлечения: {e}")

    def _show_statistics(self):
        """📊 Просмотр статистики"""
        print("\n📊 СТАТИСТИКА СИСТЕМЫ")
        print("-" * 30)

        if not self.extractor:
            print("❌ Экстрактор не инициализирован")
            return

        try:
            stats = self.extractor.get_stats()

            print("📈 Статистика экстрактора:")
            extractor_stats = stats.get('extractor_stats', {})
            for key, value in extractor_stats.items():
                if isinstance(value, dict):
                    print(f"   {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"     {sub_key}: {sub_value}")
                else:
                    print(f"   {key}: {value}")

            print("\n📊 Статистика провайдеров:")
            provider_stats = stats.get('provider_stats', {})
            for provider_name, provider_data in provider_stats.items():
                print(f"   {provider_name}:")
                print(f"     Запросов: {provider_data.get('requests_total', 0)}")
                print(f"     Успешность: {provider_data.get('success_rate', 0):.2%}")
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")

    def _run_batch_processing(self):
        """📦 Пакетная обработка"""
        print("\n📦 ПАКЕТНАЯ ОБРАБОТКА")
        print("-" * 30)
        print("Функционал пакетной обработки будет реализован в следующей фазе.")

    def _manage_providers(self):
        """⚙️ Управление провайдерами"""
        print("\n⚙️ УПРАВЛЕНИЕ ПРОВАЙДЕРАМИ")
        print("-" * 30)

        if not self.extractor:
            print("❌ Экстрактор не инициализирован")
            return

        try:
            provider_stats = self.extractor.config.provider_manager.get_stats()

            print("Текущие провайдеры:")
            for name, stats in provider_stats.items():
                status = "✅ Активен" if stats.get('active') else "❌ Отключен"
                priority = stats.get('priority', 'N/A')
                requests = stats.get('requests_total', 0)
                print(f"   {name}: {status} (Приоритет: {priority}, Запросов: {requests})")

            print("\nОпции управления:")
            print("1. Перезагрузить конфигурацию")
            print("2. Сбросить статистику")
            print("3. Назад")

            choice = input("\nВыберите действие: ").strip()

            if choice == '1':
                self.extractor.config.provider_manager.reload_config()
                print("✅ Конфигурация провайдеров перезагружена")
            elif choice == '2':
                self.extractor.config.provider_manager.reset_all_stats()
                print("✅ Статистика провайдеров сброшена")
            elif choice == '3':
                return
            else:
                print("❌ Неверный выбор")

        except Exception as e:
            print(f"❌ Ошибка управления провайдерами: {e}")

    def _system_diagnostics(self):
        """🔧 Системная диагностика"""
        print("\n🔧 СИСТЕМНАЯ ДИАГНОСТИКА")
        print("-" * 30)

        # Диагностика памяти
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        print(f"💾 Использование памяти: {memory_mb:.1f} MB")
        # Диагностика Python
        import sys
        print(f"🐍 Python версия: {sys.version}")

        # Диагностика зависимостей
        print("\n📦 Проверка ключевых зависимостей:")
        deps = ['requests', 'jsonschema', 'phonenumbers', 'pathlib']
        for dep in deps:
            try:
                __import__(dep)
                print(f"   ✅ {dep}")
            except ImportError:
                print(f"   ❌ {dep}")

        # Диагностика файлов
        print("\n📁 Проверка файлов:")
        files_to_check = [
            ("prompts/unified_contact_extraction_structured.txt", PROJECT_ROOT / "prompts" / "unified_contact_extraction_structured.txt"),
            ("config/providers.json", get_config_path("providers.json")),
            (".env", PROJECT_ROOT / ".env"),
        ]

        for label, full_path in files_to_check:
            if full_path.exists():
                size = full_path.stat().st_size
                print(f"   ✅ {label} ({size} байт)")
            else:
                print(f"   ❌ {label} (отсутствует)")


def main():
    """🏁 Точка входа для CLI"""
    try:
        menu = InteractiveMenu()
        menu.run()
    except KeyboardInterrupt:
        print("\n👋 Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
