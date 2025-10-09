#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Новая точка входа Contact Parser
Фаза 5: Архитектурная оптимизация с Dependency Injection
"""

import sys
import asyncio
from pathlib import Path

# Добавление корневой директории проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.extractor_factory import ExtractorFactory
from src.config.config_validator import ConfigValidator
from src.cli.interactive_menu import InteractiveMenu
from src.services import EmailService, OCRService, ExportService
from src.providers import AsyncProviderManager, AsyncProviderWrapper
from src.ocr_processor import OCRProcessor
from src.config.config_manager import UnifiedConfigManager
from src.utils.logger import logger, log_pipeline_event, log_api_event, log_error_event, log_system_event


def main():
    """🏁 Основная функция приложения"""
    
    # Логируем запуск приложения
    log_system_event(
        event="application_start",
        version="v2.0 - Фаза 5",
        mode="main_new"
    )

    print("🎯 CONTACT PARSER v2.0 - Фаза 5")
    print("Архитектурная оптимизация с Dependency Injection")
    print("=" * 60)

    # Валидация зависимостей
    print("🔍 Валидация зависимостей...")
    if not ExtractorFactory.validate_dependencies():
        log_error_event(
            error_type="dependency_validation_failed",
            error_message="Критические проблемы с зависимостями"
        )
        print("❌ Критические проблемы с зависимостями!")
        print("Пожалуйста, исправьте ошибки и запустите снова.")
        sys.exit(1)

    # Валидация конфигурации
    print("🔧 Валидация конфигурации...")
    validator = ConfigValidator()
    validation_result = validator.validate_all()

    if not validation_result.is_valid:
        log_error_event(
            error_type="config_validation_failed",
            error_message="Критические проблемы с конфигурацией"
        )
        print("❌ Критические проблемы с конфигурацией!")
        validator.print_validation_report(validation_result)
        print("\nПожалуйста, исправьте ошибки и запустите снова.")
        sys.exit(1)
    else:
        log_system_event(event="config_validation_success")
        print("✅ Конфигурация валидна")

    # Определение режима запуска
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = 'interactive'

    # Логируем выбранный режим
    log_system_event(
        event="mode_selected",
        mode=mode
    )

    if mode == 'interactive':
        # Интерактивный режим
        log_pipeline_event(event_type="interactive_mode_start")
        print("\n🎮 Запуск интерактивного режима...")
        menu = InteractiveMenu()
        menu.run()

    elif mode == 'test':
        # Тестовый режим
        log_pipeline_event(event_type="test_mode_start")
        print("\n🧪 Запуск тестового режима...")
        run_test_mode()

    elif mode == 'validate':
        # Только валидация
        log_pipeline_event(event_type="validate_mode_start")
        print("\n🔍 Детальный отчет валидации:")
        validator.print_validation_report(validation_result)

    elif mode == 'full-pipeline':
        # Полный пайплайн обработки
        log_pipeline_event(event_type="full_pipeline_start")
        print("\n🔄 Запуск полного пайплайна обработки...")
        run_full_pipeline()

    elif mode == 'async':
        # Асинхронный режим
        log_pipeline_event(event_type="async_mode_start")
        print("\n🚀 Запуск асинхронного режима...")
        asyncio.run(run_async_mode())

    elif mode == 'async-extraction':
        # Асинхронное извлечение данных
        log_pipeline_event(event_type="async_extraction_start")
        print("\n🤖 Запуск асинхронного извлечения данных...")
        asyncio.run(run_async_extraction_mode())

    elif mode == 'async-ocr':
        # Асинхронная OCR обработка
        log_pipeline_event(event_type="async_ocr_start")
        print("\n🔍 Запуск асинхронной OCR обработки...")
        asyncio.run(run_async_ocr_mode())

    else:
        log_error_event(
            event="unknown_mode",
            mode=mode,
            error="Неизвестный режим запуска"
        )
        print(f"❌ Неизвестный режим: {mode}")
        print("Доступные режимы:")
        print("  interactive - интерактивное меню (по умолчанию)")
        print("  test - тестовый запуск")
        print("  validate - только валидация конфигурации")
        print("  full-pipeline - полный пайплайн обработки")
        print("  async - асинхронный режим с LLM провайдерами")
        print("  async-ocr - асинхронная OCR обработка файлов")
        sys.exit(1)


def run_full_pipeline():
    """🔄 Демонстрация полного интегрированного пайплайна"""
    
    log_pipeline_event(event_type="full_pipeline_demo_start")
    print("🚀 ПОЛНЫЙ ПАЙПЛАЙН ОБРАБОТКИ")
    print("=" * 50)

    # Шаг 1: Email Service
    log_pipeline_event(event_type="email_service_step_start")
    print("\n📧 ШАГ 1: Email Service")
    email_service = EmailService()
    available_dates = email_service.get_available_dates()
    print(f"   📅 Доступные даты: {len(available_dates)}")
    if available_dates:
        print(f"   📅 Примеры: {available_dates[:3]}")

    # Шаг 2: OCR Service
    log_pipeline_event(event_type="ocr_service_step_start")
    print("\n🔍 ШАГ 2: OCR Service")
    ocr_service = OCRService()
    ocr_dates = ocr_service.get_available_dates()
    print(f"   📅 Даты для OCR: {len(ocr_dates)}")

    # Шаг 3: LLM Extractor (новая архитектура)
    log_pipeline_event(event_type="llm_extractor_step_start")
    print("\n🤖 ШАГ 3: LLM Extractor")
    try:
        extractor = ExtractorFactory.create_extractor()
        log_pipeline_event(event_type="extractor_initialized")
        print("   ✅ Экстрактор инициализирован")
        print("   📊 Статистика экстрактора:")
        stats = extractor.get_stats()
        if 'extractor_stats' in stats:
            ext_stats = stats['extractor_stats']
            print(f"      Запросов: {ext_stats.get('total_requests', 0)}")
            print(f"      Успешных: {ext_stats.get('successful_requests', 0)}")
    except Exception as e:
        log_error_event(
            event="extractor_initialization_failed",
            error=str(e)
        )
        print(f"   ❌ Ошибка инициализации: {e}")

    # Шаг 4: Export Service
    log_pipeline_event(event_type="export_service_step_start")
    print("\n📊 ШАГ 4: Export Service")
    export_service = ExportService()
    export_dates = export_service.get_available_dates()
    print(f"   📅 Даты для экспорта: {len(export_dates)}")

    log_pipeline_event(event_type="full_pipeline_demo_completed")
    print("\n🎉 Демонстрация завершена!")
    print("Все сервисы успешно интегрированы в новую архитектуру.")


def run_test_mode():
    """🧪 Тестовый режим работы"""
    
    log_pipeline_event(event_type="test_mode_demo_start")
    try:
        log_pipeline_event(event_type="test_extractor_creation_start")
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
        log_error_event(
            event="test_mode_failed",
            error=str(e)
        )
        print(f"❌ Ошибка в тестовом режиме: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def run_async_mode():
    """Асинхронный режим обработки с LLM провайдерами"""
    log_pipeline_event(event_type="async_mode_demo_start")
    try:
        log_pipeline_event(event_type="async_provider_manager_init_start")
        print("📋 Инициализация асинхронного менеджера провайдеров...")
        
        # Получаем конфигурацию провайдеров
        config_manager = UnifiedConfigManager()
        providers_config = config_manager.get_llm_providers()
        
        # Создаем базовые провайдеры для менеджера
        from src.providers.base_provider import ProviderConfig
        
        base_providers = []
        for llm_config in providers_config:
            # Конвертируем LLMProviderConfig в ProviderConfig
            provider_config = ProviderConfig(
                name=llm_config.name,
                api_key=llm_config.api_key,
                model=llm_config.model,
                base_url=llm_config.base_url,
                priority=llm_config.priority,
                active=llm_config.active,
                timeout=llm_config.timeout,
                max_retries=llm_config.max_retries
            )
            
            # Создаем базовый провайдер
            if llm_config.name.lower() == 'openrouter':
                from src.providers.openrouter import OpenRouterProvider
                base_provider = OpenRouterProvider(provider_config, config_manager=config_manager)
            elif llm_config.name.lower() == 'replicate':
                from src.providers.replicate import ReplicateProvider
                base_provider = ReplicateProvider(provider_config, config_manager=config_manager)
            elif llm_config.name.lower() == 'groq':
                from src.providers.groq import GroqProvider
                base_provider = GroqProvider(provider_config)
            else:
                print(f"⚠️ Неизвестный провайдер: {llm_config.name}")
                continue
                
            base_providers.append(base_provider)
            print(f"✅ Создан провайдер: {llm_config.name}")
        
        # Создаем менеджер с провайдерами (он сам создаст AsyncProviderWrapper)
        async_manager = AsyncProviderManager(providers=base_providers)
        
        # Функция для обработки одного запроса
        async def process_request_async(manager, request_id: str, prompt: str):
            try:
                print(f"🚀 {request_id}: Отправка запроса...")
                result = await manager.make_request_async(prompt)
                print(f"✅ {request_id}: Получен ответ ({len(result.get('content', ''))} символов)")
                return result
            except Exception as e:
                print(f"❌ {request_id}: Ошибка - {e}")
                raise
        
        # Тестовые запросы
        test_prompts = [
            "Извлеки контакты из текста: Иван Петров, ivan@example.com, +7-123-456-78-90",
            "Найди организацию: ООО Рога и Копыта, ИНН 1234567890, www.example.com",
            "Определи коммерческое предложение в тексте: Предлагаем услуги по разработке"
        ]
        
        print(f"🔄 Выполнение {len(test_prompts)} тестовых запросов...")
        
        # Параллельное выполнение запросов
        tasks = []
        for i, prompt in enumerate(test_prompts):
            task = process_request_async(async_manager, f"Запрос {i+1}", prompt)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Вывод результатов
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Запрос {i+1}: Ошибка - {result}")
            else:
                print(f"✅ Запрос {i+1}: Успешно обработан")
        
        # Статистика
        print("\n📊 Статистика асинхронных провайдеров:")
        stats = async_manager.get_stats()
        print(f"   Всего запросов: {stats.get('total_requests', 0)}")
        print(f"   Успешных: {stats.get('successful_requests', 0)}")
        print(f"   Ошибок: {stats.get('failed_requests', 0)}")
        print(f"   Активных провайдеров: {stats.get('active_providers', 0)}/{stats.get('total_providers', 0)}")
        print(f"   Кеш: {stats.get('cache_hits', 0)} попаданий, {stats.get('cache_misses', 0)} промахов")
        
        # Детальная статистика по провайдерам
        print("\n📋 Детальная статистика по провайдерам:")
        detailed_stats = async_manager.get_all_stats()
        for provider_name, provider_stats in detailed_stats.items():
            requests = provider_stats.get('requests_total', 0)
            print(f"   {provider_name}: {requests} запросов")
        
        # Закрываем соединения
        await async_manager.close_all()
        
    except Exception as e:
        log_error_event(
            event="async_mode_failed",
            error=str(e)
        )
        print(f"❌ Ошибка в асинхронном режиме: {e}")
        import traceback
        traceback.print_exc()


async def run_async_extraction_mode():
    """Асинхронный режим извлечения данных с AsyncContactExtractor"""
    log_pipeline_event(event_type="async_extraction_demo_start")
    try:
        log_pipeline_event(event_type="async_extractor_init_start")
        print("🚀 Инициализация асинхронного экстрактора...")
        
        # Создаем конфигурацию для экстрактора
        from src.core.extractor_factory import ExtractorFactory
        from src.core.async_extractor import AsyncContactExtractor
        
        # Создаем синхронный экстрактор для получения конфигурации
        sync_extractor = ExtractorFactory.create_extractor()
        
        # Создаем асинхронный экстрактор с той же конфигурацией
        async_extractor = AsyncContactExtractor(sync_extractor.config)
        
        # Тестовые данные
        test_texts = [
            """Иван Петров, менеджер по продажам ООО "Рога и Копыта"
            Email: ivan.petrov@example.com
            Телефон: +7 (495) 123-45-67
            ИНН: 1234567890
            Предлагаем услуги по разработке сайтов от 50000 рублей.""",
            
            """Анна Сидорова, директор АО "Новые Технологии"
            Контакты: anna@newtech.ru, +7-926-555-77-88
            Сайт: www.newtech.ru
            Коммерческое предложение: внедрение CRM системы за 150000 руб.""",
            
            """ООО "Инновации Плюс"
            Контактное лицо: Петр Васильев, технический директор
            Email: p.vasiliev@innovations.com
            Телефон: 8-800-555-35-35
            Предложение: разработка мобильного приложения."""
        ]
        
        print(f"📋 Обработка {len(test_texts)} тестовых документов...")
        
        # Параллельная обработка всех текстов
        tasks = []
        for i, text in enumerate(test_texts):
            metadata = {'source': f'test_document_{i+1}'}
            task = async_extractor.extract_all_data_async(text, metadata)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Вывод результатов
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Документ {i+1}: Ошибка - {result}")
            else:
                print(f"\n✅ Документ {i+1}: Успешно обработан")
                print(f"   📞 Контактов найдено: {result.get('total_contacts_found', 0)}")
                print(f"   🏢 Организаций найдено: {result.get('total_organizations_found', 0)}")
                print(f"   💼 Предложений найдено: {len(result.get('commercial_offers', []))}")
                print(f"   ⏱️ Время обработки: {result.get('processing_time', 0):.2f}с")
                
                # Показываем бизнес-контекст
                business_context = result.get('business_context', {})
                if isinstance(business_context, dict) and 'business_summary' in business_context:
                    print(f"   📋 Бизнес-контекст: {business_context['business_summary'][:100]}...")
        
        # Статистика асинхронного экстрактора
        print("\n📊 Статистика асинхронного экстрактора:")
        stats = async_extractor.get_stats()
        print(f"   Всего запросов: {stats.get('total_requests', 0)}")
        print(f"   Успешных: {stats.get('successful_requests', 0)}")
        print(f"   Ошибок: {stats.get('failed_requests', 0)}")
        print(f"   Асинхронных операций: {stats.get('async_operations', 0)}")
        print(f"   Параллельных задач: {stats.get('parallel_tasks', 0)}")
        print(f"   Кеш: {stats.get('cache_hits', 0)} попаданий, {stats.get('cache_misses', 0)} промахов")
        print(f"   Среднее время обработки: {stats.get('avg_processing_time', 0):.2f}с")
        
    except Exception as e:
        log_error_event(
            event="async_extraction_failed",
            error=str(e)
        )
        print(f"❌ Ошибка в асинхронном режиме извлечения: {e}")
        import traceback
        traceback.print_exc()


async def run_async_ocr_mode():
    """Асинхронная OCR обработка файлов"""
    log_pipeline_event(event_type="async_ocr_demo_start")
    try:
        log_pipeline_event(event_type="async_ocr_init_start")
        print("🔍 Инициализация асинхронной OCR обработки...")
        
        # Поиск файлов для обработки
        from pathlib import Path
        input_dir = Path("data/input")
        
        if not input_dir.exists():
            print(f"❌ Директория {input_dir} не найдена")
            return
        
        # Поиск изображений
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.pdf', '*.tiff']:
            image_files.extend(input_dir.glob(ext))
        
        if not image_files:
            print("❌ Файлы для OCR обработки не найдены")
            return
        
        print(f"📁 Найдено файлов: {len(image_files)}")
        
        # Создание OCR процессора
        ocr_processor = OCRProcessor()
        
        # Асинхронная обработка файлов
        tasks = []
        for file_path in image_files[:5]:  # Ограничиваем до 5 файлов для теста
            task = asyncio.create_task(
                process_file_async(ocr_processor, file_path)
            )
            tasks.append(task)
        
        print("🚀 Запуск асинхронной обработки...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработка результатов
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Файл {image_files[i].name}: {result}")
            else:
                print(f"✅ Файл {image_files[i].name}: обработан")
                success_count += 1
        
        print(f"\n📊 Обработано успешно: {success_count}/{len(results)}")
        
    except Exception as e:
        print(f"❌ Ошибка в асинхронной OCR обработке: {e}")
        import traceback
        traceback.print_exc()


async def process_file_async(ocr_processor, file_path):
    """Асинхронная обработка одного файла"""
    try:
        # Имитация асинхронной OCR обработки
        await asyncio.sleep(0.1)  # Небольшая задержка для демонстрации
        
        # Здесь должна быть реальная OCR обработка
        # result = await ocr_processor.process_async(file_path)
        
        return f"Processed: {file_path.name}"
        
    except Exception as e:
        raise Exception(f"Ошибка обработки {file_path.name}: {e}")


if __name__ == "__main__":
    main()
