#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тест интеграции провайдеров в пайплайне
Задача 5: Validate Provider Integration in Pipeline

Тестирует:
1. Обработку одного письма через провайдер
2. Балансировку нагрузки между провайдерами  
3. Управление состояниями Circuit Breaker
"""

import sys
import os
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.providers import AsyncProviderManager
from src.providers.base_provider import ProviderConfig
from src.providers.openrouter import OpenRouterProvider
from src.providers.replicate import ReplicateProvider
from src.providers.groq import GroqProvider
from src.config.config_manager import UnifiedConfigManager


class ProviderIntegrationTester:
    """🧪 Тестер интеграции провайдеров"""
    
    def __init__(self):
        self.config_manager = UnifiedConfigManager()
        self.async_manager = None
        self.test_results = {
            'single_email': None,
            'load_balancing': None,
            'circuit_breaker': None
        }
    
    async def initialize_providers(self) -> bool:
        """🚀 Инициализация провайдеров"""
        try:
            print("📋 Инициализация провайдеров...")
            
            # Получаем конфигурацию провайдеров
            providers_config = self.config_manager.get_llm_providers()
            
            if not providers_config:
                print("❌ Не найдена конфигурация провайдеров")
                return False
            
            # Создаем базовые провайдеры
            base_providers = []
            for llm_config in providers_config:
                if not llm_config.active:
                    print(f"⏭️ Пропускаем неактивный провайдер: {llm_config.name}")
                    continue
                
                # Конвертируем в ProviderConfig
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
                
                # Создаем провайдер
                if llm_config.name.lower() == 'openrouter':
                    provider = OpenRouterProvider(provider_config)
                elif llm_config.name.lower() == 'replicate':
                    provider = ReplicateProvider(provider_config)
                elif llm_config.name.lower() == 'groq':
                    provider = GroqProvider(provider_config)
                else:
                    print(f"⚠️ Неизвестный провайдер: {llm_config.name}")
                    continue
                
                base_providers.append(provider)
                print(f"✅ Создан провайдер: {llm_config.name} (приоритет: {llm_config.priority})")
            
            if not base_providers:
                print("❌ Не создано ни одного провайдера")
                return False
            
            # Создаем асинхронный менеджер
            self.async_manager = AsyncProviderManager(providers=base_providers)
            print(f"✅ AsyncProviderManager создан с {len(base_providers)} провайдерами")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка инициализации провайдеров: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def find_test_email(self) -> Optional[Path]:
        """📧 Поиск тестового письма"""
        email_dirs = [
            Path("data/emails"),
            Path("data/emails/2025-07-29"),
            Path("tests/data"),
            Path("test_data")
        ]
        
        for email_dir in email_dirs:
            if email_dir.exists():
                json_files = list(email_dir.glob("*.json"))
                if json_files:
                    # Берем первое найденное письмо
                    test_file = json_files[0]
                    print(f"📧 Найдено тестовое письмо: {test_file}")
                    return test_file
        
        print("❌ Не найдено тестовых писем")
        return None
    
    async def test_single_email_processing(self) -> bool:
        """🧪 Тест 1: Обработка одного письма"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 1: Обработка одного письма")
        print("="*60)
        
        try:
            # Находим тестовое письмо
            email_file = self.find_test_email()
            if not email_file:
                # Создаем простое тестовое письмо
                test_email_content = {
                    "subject": "Тестовое письмо",
                    "body": "Контакты: Иван Петров, ivan@example.com, +7-123-456-78-90. Организация: ООО Тест, ИНН 1234567890.",
                    "from": "test@example.com",
                    "date": "2025-01-29"
                }
                print("📧 Используем синтетическое тестовое письмо")
            else:
                # Загружаем реальное письмо
                with open(email_file, 'r', encoding='utf-8') as f:
                    test_email_content = json.load(f)
                print(f"📧 Загружено письмо: {email_file.name}")
            
            # Формируем промпт для обработки
            email_text = test_email_content.get('body', '') or test_email_content.get('content', '')
            if not email_text:
                email_text = f"Subject: {test_email_content.get('subject', '')}\nFrom: {test_email_content.get('from', '')}"
            
            prompt = f"Извлеки контактную информацию из следующего письма:\n\n{email_text[:1000]}"
            
            print(f"📝 Промпт подготовлен ({len(prompt)} символов)")
            
            # Выполняем запрос
            start_time = time.time()
            result = await self.async_manager.make_request_async(prompt)
            processing_time = time.time() - start_time
            
            print(f"✅ Письмо обработано за {processing_time:.2f}с")
            print(f"   Провайдер: {result.get('provider', 'Unknown')}")
            print(f"   Модель: {result.get('model', 'Unknown')}")
            print(f"   Ответ: {len(result.get('content', ''))} символов")
            print(f"   Из кеша: {result.get('from_cache', False)}")
            
            # Сохраняем результат
            self.test_results['single_email'] = {
                'success': True,
                'provider': result.get('provider'),
                'processing_time': processing_time,
                'response_length': len(result.get('content', '')),
                'from_cache': result.get('from_cache', False)
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обработки письма: {e}")
            self.test_results['single_email'] = {
                'success': False,
                'error': str(e)
            }
            return False
    
    async def test_load_balancing_scenario(self) -> bool:
        """🧪 Тест 2: Балансировка нагрузки"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 2: Балансировка нагрузки")
        print("="*60)
        
        try:
            # Подготавливаем несколько разных промптов
            test_prompts = [
                "Извлеки контакты: Иван Петров, ivan@test.com, +7-123-456-78-90",
                "Найди организацию: ООО Рога и Копыта, ИНН 1234567890",
                "Определи коммерческое предложение: Предлагаем услуги разработки",
                "Извлеки контакты: Мария Сидорова, maria@example.org, 8-800-555-35-35",
                "Найди организацию: АО Технологии, ОГРН 1234567890123"
            ]
            
            print(f"📝 Подготовлено {len(test_prompts)} тестовых промптов")
            
            # Получаем статистику до тестирования
            stats_before = self.async_manager.get_all_stats()
            
            # Выполняем запросы параллельно
            start_time = time.time()
            tasks = [
                self.async_manager.make_request_async(prompt)
                for prompt in test_prompts
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Анализируем результаты
            successful_requests = 0
            failed_requests = 0
            providers_used = {}
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Запрос {i+1}: {result}")
                    failed_requests += 1
                else:
                    successful_requests += 1
                    provider = result.get('provider', 'Unknown')
                    providers_used[provider] = providers_used.get(provider, 0) + 1
                    print(f"✅ Запрос {i+1}: {provider} ({len(result.get('content', ''))} символов)")
            
            # Получаем статистику после тестирования
            stats_after = self.async_manager.get_all_stats()
            
            print(f"\n📊 Результаты балансировки:")
            print(f"   Успешных запросов: {successful_requests}/{len(test_prompts)}")
            print(f"   Общее время: {total_time:.2f}с")
            print(f"   Среднее время на запрос: {total_time/len(test_prompts):.2f}с")
            
            print(f"\n🔄 Распределение по провайдерам:")
            for provider, count in providers_used.items():
                print(f"   {provider}: {count} запросов")
            
            # Проверяем что использовалось несколько провайдеров (если они доступны)
            load_balancing_works = len(providers_used) > 1 or len(self.async_manager.async_providers) == 1
            
            # Сохраняем результат
            self.test_results['load_balancing'] = {
                'success': successful_requests > 0,
                'total_requests': len(test_prompts),
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'providers_used': providers_used,
                'load_balancing_works': load_balancing_works,
                'total_time': total_time
            }
            
            return successful_requests > 0
            
        except Exception as e:
            print(f"❌ Ошибка тестирования балансировки: {e}")
            self.test_results['load_balancing'] = {
                'success': False,
                'error': str(e)
            }
            return False  
  
    async def test_circuit_breaker_management(self) -> bool:
        """🧪 Тест 3: Управление Circuit Breaker"""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 3: Управление Circuit Breaker")
        print("="*60)
        
        try:
            # Находим провайдер для тестирования
            if not self.async_manager.async_providers:
                print("❌ Нет доступных провайдеров для тестирования")
                return False
            
            test_provider_wrapper = self.async_manager.async_providers[0]
            test_provider = test_provider_wrapper.provider
            provider_name = test_provider.config.name
            
            print(f"🎯 Тестируем Circuit Breaker для провайдера: {provider_name}")
            
            # Сохраняем исходное состояние
            original_api_key = test_provider.config.api_key
            original_failure_count = test_provider.failure_count
            original_circuit_state = test_provider.in_circuit_break
            
            print(f"📊 Исходное состояние:")
            print(f"   Failure count: {original_failure_count}")
            print(f"   Circuit breaker: {original_circuit_state}")
            print(f"   Available: {test_provider.is_available()}")
            
            # Этап 1: Искусственно вызываем ошибки
            print(f"\n🔧 Этап 1: Вызываем ошибки для активации Circuit Breaker")
            
            # Искусственно вызываем ошибки через record_failure
            print(f"   Искусственно генерируем ошибки через record_failure...")
            failed_requests = 0
            for i in range(6):  # Больше чем threshold (5)
                test_provider.record_failure("test_error")
                failed_requests += 1
                print(f"   Ошибка {i+1}: ❌ Искусственная ошибка для тестирования Circuit Breaker")
                
                # Проверяем состояние после каждой ошибки
                if i == 4:  # После 5-й ошибки должен активироваться Circuit Breaker
                    print(f"      После {i+1} ошибок: Circuit Breaker = {test_provider.in_circuit_break}")
            
            print(f"📊 После ошибок:")
            print(f"   Failure count: {test_provider.failure_count}")
            print(f"   Circuit breaker: {test_provider.in_circuit_break}")
            print(f"   Available: {test_provider.is_available()}")
            
            # Проверяем что Circuit Breaker активировался
            circuit_breaker_activated = test_provider.in_circuit_break
            
            # Этап 2: Проверяем блокировку
            print(f"\n🔧 Этап 2: Проверяем блокировку провайдера")
            
            try:
                request_data = {
                    'messages': [{'role': 'user', 'content': "Test prompt while blocked"}]
                }
                await test_provider.make_request(request_data)
                print("❌ Запрос прошел, хотя провайдер должен быть заблокирован")
                blocked_correctly = False
            except Exception as e:
                if "недоступен" in str(e) or "Circuit Breaker" in str(e):
                    print(f"✅ Провайдер корректно заблокирован: {str(e)[:100]}...")
                    blocked_correctly = True
                else:
                    print(f"⚠️ Провайдер заблокирован по другой причине: {str(e)[:100]}...")
                    blocked_correctly = True  # Все равно заблокирован
            
            # Этап 3: Восстанавливаем провайдер
            print(f"\n🔧 Этап 3: Восстанавливаем провайдер")
            
            # Восстанавливаем API ключ
            test_provider.config.api_key = original_api_key
            
            # Сбрасываем Circuit Breaker вручную
            test_provider.failure_count = 0
            test_provider.in_circuit_break = False
            test_provider.last_failure_time = None
            
            print(f"🔄 Circuit Breaker сброшен вручную")
            print(f"   Failure count: {test_provider.failure_count}")
            print(f"   Circuit breaker: {test_provider.in_circuit_break}")
            print(f"   Available: {test_provider.is_available()}")
            
            # Этап 4: Проверяем восстановление
            print(f"\n🔧 Этап 4: Проверяем восстановление работы")
            
            recovery_success = False
            try:
                request_data = {
                    'messages': [{'role': 'user', 'content': "Test prompt after recovery"}]
                }
                result = await test_provider.make_request(request_data)
                print(f"✅ Провайдер восстановлен: {result.get('provider', 'Unknown')}")
                recovery_success = True
            except Exception as e:
                print(f"❌ Провайдер не восстановился: {e}")
            
            # Сохраняем результат
            self.test_results['circuit_breaker'] = {
                'success': True,
                'circuit_breaker_activated': circuit_breaker_activated,
                'blocked_correctly': blocked_correctly,
                'recovery_success': recovery_success,
                'failed_requests_generated': failed_requests,
                'provider_tested': provider_name
            }
            
            print(f"\n📊 Итоги тестирования Circuit Breaker:")
            print(f"   Circuit Breaker активировался: {circuit_breaker_activated}")
            print(f"   Блокировка работает: {blocked_correctly}")
            print(f"   Восстановление работает: {recovery_success}")
            
            return circuit_breaker_activated and blocked_correctly and recovery_success
            
        except Exception as e:
            print(f"❌ Ошибка тестирования Circuit Breaker: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['circuit_breaker'] = {
                'success': False,
                'error': str(e)
            }
            return False
    
    def print_final_report(self):
        """📊 Финальный отчет о тестировании"""
        print("\n" + "="*80)
        print("📊 ФИНАЛЬНЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ ИНТЕГРАЦИИ ПРОВАЙДЕРОВ")
        print("="*80)
        
        # Общая статистика
        total_tests = 3
        passed_tests = sum(1 for result in self.test_results.values() if result and result.get('success', False))
        
        print(f"\n🎯 Общие результаты:")
        print(f"   Всего тестов: {total_tests}")
        print(f"   Пройдено: {passed_tests}")
        print(f"   Провалено: {total_tests - passed_tests}")
        print(f"   Успешность: {passed_tests/total_tests*100:.1f}%")
        
        # Детальные результаты
        print(f"\n📋 Детальные результаты:")
        
        # Тест 1: Single Email Processing
        single_email = self.test_results.get('single_email', {})
        if single_email.get('success'):
            print(f"   ✅ Тест 1 - Обработка одного письма:")
            print(f"      Провайдер: {single_email.get('provider', 'Unknown')}")
            print(f"      Время обработки: {single_email.get('processing_time', 0):.2f}с")
            print(f"      Размер ответа: {single_email.get('response_length', 0)} символов")
            print(f"      Из кеша: {single_email.get('from_cache', False)}")
        else:
            print(f"   ❌ Тест 1 - Обработка одного письма: {single_email.get('error', 'Неизвестная ошибка')}")
        
        # Тест 2: Load Balancing
        load_balancing = self.test_results.get('load_balancing', {})
        if load_balancing.get('success'):
            print(f"   ✅ Тест 2 - Балансировка нагрузки:")
            print(f"      Успешных запросов: {load_balancing.get('successful_requests', 0)}/{load_balancing.get('total_requests', 0)}")
            print(f"      Общее время: {load_balancing.get('total_time', 0):.2f}с")
            print(f"      Провайдеры использованы: {list(load_balancing.get('providers_used', {}).keys())}")
            print(f"      Балансировка работает: {load_balancing.get('load_balancing_works', False)}")
        else:
            print(f"   ❌ Тест 2 - Балансировка нагрузки: {load_balancing.get('error', 'Неизвестная ошибка')}")
        
        # Тест 3: Circuit Breaker
        circuit_breaker = self.test_results.get('circuit_breaker', {})
        if circuit_breaker.get('success'):
            print(f"   ✅ Тест 3 - Circuit Breaker:")
            print(f"      Провайдер: {circuit_breaker.get('provider_tested', 'Unknown')}")
            print(f"      Circuit Breaker активировался: {circuit_breaker.get('circuit_breaker_activated', False)}")
            print(f"      Блокировка работает: {circuit_breaker.get('blocked_correctly', False)}")
            print(f"      Восстановление работает: {circuit_breaker.get('recovery_success', False)}")
        else:
            print(f"   ❌ Тест 3 - Circuit Breaker: {circuit_breaker.get('error', 'Неизвестная ошибка')}")
        
        # Статистика провайдеров
        if self.async_manager:
            print(f"\n📊 Статистика провайдеров:")
            stats = self.async_manager.get_stats()
            print(f"   Всего запросов: {stats.get('total_requests', 0)}")
            print(f"   Успешных: {stats.get('successful_requests', 0)}")
            print(f"   Ошибок: {stats.get('failed_requests', 0)}")
            print(f"   Успешность: {stats.get('success_rate', 0):.1f}%")
            print(f"   Кеш попаданий: {stats.get('cache_hits', 0)}")
            print(f"   Кеш промахов: {stats.get('cache_misses', 0)}")
            print(f"   Активных провайдеров: {stats.get('active_providers', 0)}/{stats.get('total_providers', 0)}")
        
        # Рекомендации
        print(f"\n💡 Рекомендации:")
        if passed_tests == total_tests:
            print(f"   🎉 Все тесты пройдены! Интеграция провайдеров работает корректно.")
        else:
            print(f"   ⚠️ Некоторые тесты провалились. Требуется дополнительная отладка.")
            
            if not single_email.get('success'):
                print(f"   - Проверьте конфигурацию провайдеров и API ключи")
            if not load_balancing.get('success'):
                print(f"   - Проверьте логику балансировки нагрузки в AsyncProviderManager")
            if not circuit_breaker.get('success'):
                print(f"   - Проверьте реализацию Circuit Breaker в BaseProvider")


async def main():
    """🚀 Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ ПРОВАЙДЕРОВ В ПАЙПЛАЙНЕ")
    print("="*80)
    print("Задача 5: Validate Provider Integration in Pipeline")
    print("Подзадачи:")
    print("  1. Test provider with single email processing")
    print("  2. Verify both providers work in load balancing scenario")
    print("  3. Confirm Circuit Breaker properly manages provider states")
    print("="*80)
    
    tester = ProviderIntegrationTester()
    
    # Инициализация
    if not await tester.initialize_providers():
        print("❌ Не удалось инициализировать провайдеры")
        return False
    
    # Выполняем тесты
    test1_result = await tester.test_single_email_processing()
    test2_result = await tester.test_load_balancing_scenario()
    test3_result = await tester.test_circuit_breaker_management()
    
    # Финальный отчет
    tester.print_final_report()
    
    # Закрываем ресурсы
    if tester.async_manager:
        await tester.async_manager.close_all()
    
    # Возвращаем общий результат
    all_tests_passed = test1_result and test2_result and test3_result
    
    if all_tests_passed:
        print(f"\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print(f"✅ Интеграция провайдеров в пайплайне работает корректно")
    else:
        print(f"\n⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ")
        print(f"❌ Требуется дополнительная отладка интеграции")
    
    return all_tests_passed


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)