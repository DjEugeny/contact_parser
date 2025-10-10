#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тестирование задач 9-10.1
- Задача 9.1: calculate_dynamic_timeout
- Задача 9.2: retry_with_backoff
- Задача 10.1: log_processing_error
"""

import asyncio
import time
from src.utils.timeout_calculator import (
    calculate_dynamic_timeout,
    calculate_timeout_from_email_data,
    get_timeout_breakdown
)
from src.utils.retry_with_backoff import (
    retry_with_backoff_async,
    RetryConfig,
    with_retry_backoff
)
from src.utils.error_logger import log_processing_error


def test_timeout_calculator():
    """🧪 Тест расчёта динамического таймаута"""
    print("\n" + "=" * 80)
    print("🧪 ТЕСТ 1: Расчёт динамического таймаута")
    print("=" * 80)
    
    # Тест 1: Простое письмо без вложений
    timeout1 = calculate_dynamic_timeout(5000, 0, False)
    print(f"\n📧 Письмо: 5000 символов, 0 вложений, без OCR")
    print(f"   ⏱️  Таймаут: {timeout1}с (ожидается: 65с)")
    assert timeout1 == 65, f"Ожидалось 65, получено {timeout1}"
    print("   ✅ Тест пройден")
    
    # Тест 2: Письмо с вложениями и OCR
    timeout2 = calculate_dynamic_timeout(10000, 2, True)
    print(f"\n📧 Письмо: 10000 символов, 2 вложения, с OCR")
    print(f"   ⏱️  Таймаут: {timeout2}с (ожидается: 160с)")
    # 60 (base) + 10 (text) + 60 (2 attachments) + 30 (OCR) = 160
    assert timeout2 == 160, f"Ожидалось 160, получено {timeout2}"
    print("   ✅ Тест пройден")
    
    # Тест 3: Очень большое письмо (проверка ограничения)
    timeout3 = calculate_dynamic_timeout(100000, 5, True)
    print(f"\n📧 Письмо: 100000 символов, 5 вложений, с OCR")
    print(f"   ⏱️  Таймаут: {timeout3}с (ожидается: 300с - максимум)")
    assert timeout3 == 300, f"Ожидалось 300, получено {timeout3}"
    print("   ✅ Тест пройден")
    
    # Тест 4: Расчёт из данных письма
    email_data = {
        'combined_text_length': 5000,
        'attachments_processed': 2,
        'has_ocr': True
    }
    timeout4 = calculate_timeout_from_email_data(email_data)
    print(f"\n📧 Письмо из данных: {email_data}")
    print(f"   ⏱️  Таймаут: {timeout4}с (ожидается: 155с)")
    # 60 (base) + 5 (text) + 60 (2 attachments) + 30 (OCR) = 155
    assert timeout4 == 155, f"Ожидалось 155, получено {timeout4}"
    print("   ✅ Тест пройден")
    
    # Тест 5: Детальная разбивка
    breakdown = get_timeout_breakdown(5000, 2, True)
    print(f"\n📊 Детальная разбивка таймаута:")
    print(f"   {breakdown['breakdown_str']}")
    print(f"   Базовый: {breakdown['base_timeout']}с")
    print(f"   Текст: +{breakdown['text_overhead']}с")
    print(f"   Вложения: +{breakdown['attachments_overhead']}с")
    print(f"   OCR: +{breakdown['ocr_overhead']}с")
    print(f"   Итого: {breakdown['total_timeout']}с")
    print(f"   Ограничен: {breakdown['capped']}")
    print("   ✅ Тест пройден")
    
    print("\n✅ Все тесты расчёта таймаута пройдены!")


async def test_retry_with_backoff():
    """🧪 Тест retry с backoff"""
    print("\n" + "=" * 80)
    print("🧪 ТЕСТ 2: Retry с exponential backoff")
    print("=" * 80)
    
    # Тест 1: Успешное выполнение с первой попытки
    print("\n📝 Тест 2.1: Успешное выполнение с первой попытки")
    
    async def successful_func():
        await asyncio.sleep(0.1)
        return "success"
    
    result = await retry_with_backoff_async(
        successful_func,
        initial_timeout=10,
        config=RetryConfig(max_attempts=3)
    )
    assert result == "success"
    print("   ✅ Тест пройден")
    
    # Тест 2: Успешное выполнение со второй попытки
    print("\n📝 Тест 2.2: Успешное выполнение со второй попытки")
    
    attempt_counter = {'count': 0}
    
    async def fail_once_func():
        attempt_counter['count'] += 1
        if attempt_counter['count'] == 1:
            raise Exception("Первая попытка неудачна")
        await asyncio.sleep(0.1)
        return "success_after_retry"
    
    result = await retry_with_backoff_async(
        fail_once_func,
        initial_timeout=10,
        config=RetryConfig(max_attempts=3, base_delay=0.5)
    )
    assert result == "success_after_retry"
    assert attempt_counter['count'] == 2
    print(f"   Попыток сделано: {attempt_counter['count']}")
    print("   ✅ Тест пройден")
    
    # Тест 3: Таймаут с увеличением
    print("\n📝 Тест 2.3: Таймаут с увеличением")
    
    timeout_values = []
    
    async def timeout_func(timeout=None):
        if timeout:
            timeout_values.append(timeout)
        await asyncio.sleep(0.1)
        if len(timeout_values) < 2:
            raise asyncio.TimeoutError("Таймаут")
        return "success_after_timeout"
    
    result = await retry_with_backoff_async(
        timeout_func,
        initial_timeout=60,
        config=RetryConfig(max_attempts=3, base_delay=0.5, timeout_multiplier=1.5)
    )
    
    print(f"   Таймауты: {timeout_values}")
    print(f"   Первый таймаут: {timeout_values[0]}с")
    print(f"   Второй таймаут: {timeout_values[1]}с (увеличен на 50%)")
    assert timeout_values[1] == int(timeout_values[0] * 1.5)
    print("   ✅ Тест пройден")
    
    # Тест 4: Использование декоратора
    print("\n📝 Тест 2.4: Использование декоратора")
    
    @with_retry_backoff(initial_timeout=10, config=RetryConfig(max_attempts=2, base_delay=0.5))
    async def decorated_func():
        await asyncio.sleep(0.1)
        return "decorated_success"
    
    result = await decorated_func()
    assert result == "decorated_success"
    print("   ✅ Тест пройден")
    
    print("\n✅ Все тесты retry с backoff пройдены!")


def test_error_logger():
    """🧪 Тест логирования ошибок"""
    print("\n" + "=" * 80)
    print("🧪 ТЕСТ 3: Логирование ошибок обработки")
    print("=" * 80)
    
    # Тест 1: Простое логирование ошибки
    print("\n📝 Тест 3.1: Простое логирование ошибки")
    
    try:
        # Симулируем ошибку
        raise ValueError("Тестовая ошибка валидации")
    except Exception as e:
        error_file = log_processing_error(
            error=e,
            email_file="test_email_001.json",
            input_data={
                'text_length': 5000,
                'attachments_count': 2,
                'has_ocr': True
            },
            llm_request={
                'provider': 'OpenRouter',
                'model': 'deepseek/deepseek-chat-v3.1:free',
                'timeout': 120
            }
        )
        print(f"   📁 Debug данные сохранены: {error_file}")
        print("   ✅ Тест пройден")
    
    # Тест 2: Логирование с LLM ответом
    print("\n📝 Тест 3.2: Логирование с LLM ответом")
    
    try:
        # Симулируем ошибку парсинга JSON
        raise json.JSONDecodeError("Expecting value", "doc", 0)
    except Exception as e:
        error_file = log_processing_error(
            error=e,
            email_file="test_email_002.json",
            input_data={
                'text_length': 10000,
                'attachments_count': 0,
                'has_ocr': False
            },
            llm_request={
                'provider': 'Replicate',
                'model': 'meta/llama-2-70b-chat',
                'timeout': 180
            },
            llm_response={
                'status_code': 200,
                'processing_time': 45.6,
                'response_length': 2345
            }
        )
        print(f"   📁 Debug данные сохранены: {error_file}")
        print("   ✅ Тест пройден")
    
    # Тест 3: Логирование с дополнительным контекстом
    print("\n📝 Тест 3.3: Логирование с дополнительным контекстом")
    
    try:
        # Симулируем ошибку сериализации
        raise TypeError("Object of type LocationEnrichmentMetadata is not JSON serializable")
    except Exception as e:
        error_file = log_processing_error(
            error=e,
            email_file="test_email_003.json",
            input_data={
                'text_length': 3000,
                'attachments_count': 1,
                'has_ocr': True
            },
            context={
                'stage': 'postprocessing',
                'operation': 'location_enrichment',
                'organization_id': 1
            }
        )
        print(f"   📁 Debug данные сохранены: {error_file}")
        print("   ✅ Тест пройден")
    
    print("\n✅ Все тесты логирования ошибок пройдены!")


def main():
    """🚀 Запуск всех тестов"""
    print("\n" + "=" * 80)
    print("🚀 ЗАПУСК ТЕСТОВ ЗАДАЧ 9-10.1")
    print("=" * 80)
    
    # Тест 1: Расчёт таймаута
    test_timeout_calculator()
    
    # Тест 2: Retry с backoff
    asyncio.run(test_retry_with_backoff())
    
    # Тест 3: Логирование ошибок
    test_error_logger()
    
    print("\n" + "=" * 80)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 80)
    print("\n📊 Итоги:")
    print("   ✅ Задача 9.1: calculate_dynamic_timeout - реализована и протестирована")
    print("   ✅ Задача 9.2: retry_with_backoff - реализована и протестирована")
    print("   ✅ Задача 10.1: log_processing_error - реализована и протестирована")
    print("\n🎉 Задачи 9-10.1 выполнены!")


if __name__ == "__main__":
    import json  # Для теста JSONDecodeError
    main()
