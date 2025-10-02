#!/usr/bin/env python3
"""
🧪 Изолированный тестер провайдеров
Цель: Тестирование провайдеров без проблем с импортами и в изоляции от основной системы
"""

import asyncio
import aiohttp
import json
import time
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

@dataclass
class ProviderConfig:
    """Конфигурация провайдера"""
    name: str
    api_key: str
    model: str
    base_url: str
    headers: Dict[str, str]
    timeout: int = 30

@dataclass
class TestResult:
    """Результат теста провайдера"""
    provider_name: str
    success: bool
    response_time: float
    error_message: Optional[str] = None
    response_content: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None

class IsolatedProviderTester:
    """🧪 Изолированный тестер провайдеров"""
    
    def __init__(self):
        self.providers = self._initialize_providers()
    
    def _initialize_providers(self) -> Dict[str, ProviderConfig]:
        """Инициализация конфигураций провайдеров"""
        providers = {}
        
        # OpenRouter
        if openrouter_key := os.getenv('OPENROUTER_API_KEY'):
            providers['OpenRouter'] = ProviderConfig(
                name="OpenRouter",
                api_key=openrouter_key,
                model="deepseek/deepseek-chat-v3.1:free",
                base_url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    'Authorization': f'Bearer {openrouter_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://localhost:3000',
                    'X-Title': 'Isolated Provider Test'
                }
            )
        
        # Replicate (для сравнения)
        if replicate_key := os.getenv('REPLICATE_API_KEY'):
            providers['Replicate'] = ProviderConfig(
                name="Replicate",
                api_key=replicate_key,
                model="deepseek-ai/deepseek-v3.1",
                base_url="https://api.replicate.com/v1/predictions",
                headers={
                    'Authorization': f'Bearer {replicate_key}',
                    'Content-Type': 'application/json'
                }
            )
        
        return providers
    
    async def test_openrouter(self, request_data: Dict[str, Any]) -> TestResult:
        """Тест OpenRouter провайдера"""
        if 'OpenRouter' not in self.providers:
            return TestResult(
                provider_name="OpenRouter",
                success=False,
                response_time=0,
                error_message="OpenRouter API key not found"
            )
        
        config = self.providers['OpenRouter']
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config.base_url,
                    json=request_data,
                    headers=config.headers,
                    timeout=aiohttp.ClientTimeout(total=config.timeout)
                ) as response:
                    
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if 'choices' in result and result['choices']:
                            content = result['choices'][0]['message']['content']
                            usage = result.get('usage', {})
                            
                            return TestResult(
                                provider_name="OpenRouter",
                                success=True,
                                response_time=response_time,
                                response_content=content,
                                usage=usage
                            )
                        else:
                            return TestResult(
                                provider_name="OpenRouter",
                                success=False,
                                response_time=response_time,
                                error_message=f"Invalid response format: {result}"
                            )
                    else:
                        error_text = await response.text()
                        return TestResult(
                            provider_name="OpenRouter",
                            success=False,
                            response_time=response_time,
                            error_message=f"HTTP {response.status}: {error_text}"
                        )
        
        except Exception as e:
            return TestResult(
                provider_name="OpenRouter",
                success=False,
                response_time=time.time() - start_time,
                error_message=f"Exception: {str(e)}"
            )
    
    async def test_replicate(self, request_data: Dict[str, Any]) -> TestResult:
        """Тест Replicate провайдера (упрощенная версия)"""
        if 'Replicate' not in self.providers:
            return TestResult(
                provider_name="Replicate",
                success=False,
                response_time=0,
                error_message="Replicate API key not found"
            )
        
        # Для Replicate нужен другой формат запроса
        # Здесь упрощенная реализация для демонстрации
        return TestResult(
            provider_name="Replicate",
            success=False,
            response_time=0,
            error_message="Replicate test not implemented in isolated tester"
        )
    
    def create_pipeline_request(self, content: str) -> Dict[str, Any]:
        """Создает запрос в формате как в пайплайне"""
        return {
            "model": "deepseek/deepseek-chat-v3.1:free",
            "messages": [
                {"role": "user", "content": content}
            ],
            "temperature": 0.2,
            "max_tokens": 1000,
            "top_p": 0.95,
            "stream": False
        }
    
    def create_extraction_request(self, text: str) -> Dict[str, Any]:
        """Создает запрос для извлечения контактов как в пайплайне"""
        prompt = f"""Извлеки контактную информацию из следующего текста и верни в JSON формате:

{text}

Верни результат в следующем JSON формате:
{{
  "organizations": [
    {{
      "organization_id": 1,
      "name": "Название организации",
      "inn": "ИНН если есть",
      "website": "сайт если есть",
      "city": "город",
      "address": "адрес"
    }}
  ],
  "contacts": [
    {{
      "contact_id": 1,
      "organization_id": 1,
      "name": "Имя контакта",
      "position": "должность",
      "email": "email",
      "phone": {{"number": "телефон", "type": "mobile"}},
      "city": "город"
    }}
  ]
}}"""
        
        return self.create_pipeline_request(prompt)
    
    async def run_comprehensive_test(self) -> Dict[str, TestResult]:
        """Запускает комплексный тест всех провайдеров"""
        results = {}
        
        # Тестовые данные
        test_cases = [
            {
                "name": "simple_request",
                "content": "Привет! Ответь кратко на русском языке."
            },
            {
                "name": "contact_extraction",
                "content": """
                Компания: ООО "Тестовая Компания"
                Адрес: г. Москва, ул. Тестовая, д. 123
                Телефон: +7 (495) 123-45-67
                Email: test@example.com
                Контактное лицо: Иванов Иван Иванович
                """
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🧪 Тест: {test_case['name']}")
            print("=" * 40)
            
            # Создаем запрос
            if test_case['name'] == 'contact_extraction':
                request_data = self.create_extraction_request(test_case['content'])
            else:
                request_data = self.create_pipeline_request(test_case['content'])
            
            # Тестируем OpenRouter
            print("🚀 Тестирование OpenRouter...")
            openrouter_result = await self.test_openrouter(request_data)
            results[f"{test_case['name']}_openrouter"] = openrouter_result
            
            self._print_test_result(openrouter_result)
            
            # Небольшая пауза между тестами
            await asyncio.sleep(1)
        
        return results
    
    def _print_test_result(self, result: TestResult):
        """Выводит результат теста"""
        status = "✅ Успех" if result.success else "❌ Ошибка"
        print(f"   {status} | {result.provider_name}")
        print(f"   ⏱️ Время: {result.response_time:.2f}с")
        
        if result.success:
            if result.usage:
                print(f"   📊 Токены: {result.usage}")
            if result.response_content:
                content_preview = result.response_content[:100] + "..." if len(result.response_content) > 100 else result.response_content
                print(f"   📝 Ответ: {content_preview}")
        else:
            print(f"   ❌ Ошибка: {result.error_message}")
    
    def print_summary(self, results: Dict[str, TestResult]):
        """Выводит сводку результатов"""
        print(f"\n📊 СВОДКА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
        print("=" * 50)
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results.values() if r.success)
        
        print(f"Всего тестов: {total_tests}")
        print(f"Успешных: {successful_tests}")
        print(f"Неудачных: {total_tests - successful_tests}")
        print(f"Успешность: {successful_tests/total_tests*100:.1f}%")
        
        # Группировка по провайдерам
        by_provider = {}
        for test_name, result in results.items():
            provider = result.provider_name
            if provider not in by_provider:
                by_provider[provider] = []
            by_provider[provider].append(result)
        
        print(f"\n📈 По провайдерам:")
        for provider, provider_results in by_provider.items():
            successful = sum(1 for r in provider_results if r.success)
            total = len(provider_results)
            avg_time = sum(r.response_time for r in provider_results) / total
            
            print(f"   {provider}: {successful}/{total} ({successful/total*100:.1f}%) | Среднее время: {avg_time:.2f}с")

async def main():
    """Основная функция тестирования"""
    print("🧪 ИЗОЛИРОВАННЫЙ ТЕСТЕР ПРОВАЙДЕРОВ")
    print("=" * 60)
    
    tester = IsolatedProviderTester()
    
    # Проверяем доступные провайдеры
    print(f"🔧 Доступные провайдеры: {list(tester.providers.keys())}")
    
    if not tester.providers:
        print("❌ Нет доступных провайдеров. Проверьте переменные окружения.")
        return
    
    # Запускаем тесты
    results = await tester.run_comprehensive_test()
    
    # Выводим сводку
    tester.print_summary(results)
    
    print(f"\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main())