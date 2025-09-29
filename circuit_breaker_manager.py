#!/usr/bin/env python3
"""
🔄 Circuit Breaker Manager
Цель: Управление состоянием Circuit Breaker для провайдеров
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Добавляем src в путь для импорта
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

load_dotenv()

@dataclass
class ProviderStatus:
    """Статус провайдера"""
    name: str
    available: bool
    circuit_break: bool
    failure_count: int
    success_rate: float
    last_failure_time: Optional[float] = None

class CircuitBreakerManager:
    """🔄 Менеджер Circuit Breaker"""
    
    def __init__(self):
        self.providers_status: Dict[str, ProviderStatus] = {}
    
    def get_provider_status_direct(self) -> List[ProviderStatus]:
        """Получает статус провайдеров напрямую через API"""
        statuses = []
        
        # OpenRouter
        if os.getenv('OPENROUTER_API_KEY'):
            status = self._test_openrouter_availability()
            statuses.append(status)
        
        # Replicate
        if os.getenv('REPLICATE_API_KEY'):
            status = self._test_replicate_availability()
            statuses.append(status)
        
        return statuses
    
    def _test_openrouter_availability(self) -> ProviderStatus:
        """Тестирует доступность OpenRouter"""
        try:
            import aiohttp
            
            async def test():
                api_key = os.getenv('OPENROUTER_API_KEY')
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://localhost:3000',
                    'X-Title': 'Circuit Breaker Test'
                }
                
                payload = {
                    "model": "deepseek/deepseek-chat-v3.1:free",
                    "messages": [{"role": "user", "content": "Test"}],
                    "max_tokens": 10
                }
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            'https://openrouter.ai/api/v1/chat/completions',
                            json=payload,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            return response.status == 200
                except:
                    return False
            
            available = asyncio.run(test())
            
            return ProviderStatus(
                name="OpenRouter",
                available=available,
                circuit_break=not available,
                failure_count=0 if available else 1,
                success_rate=1.0 if available else 0.0
            )
            
        except Exception as e:
            return ProviderStatus(
                name="OpenRouter",
                available=False,
                circuit_break=True,
                failure_count=1,
                success_rate=0.0
            )
    
    def _test_replicate_availability(self) -> ProviderStatus:
        """Тестирует доступность Replicate (упрощенная версия)"""
        # Для Replicate сложнее тестировать из-за асинхронной природы API
        # Здесь упрощенная проверка наличия ключа
        api_key = os.getenv('REPLICATE_API_KEY')
        available = bool(api_key and len(api_key) > 10)
        
        return ProviderStatus(
            name="Replicate",
            available=available,
            circuit_break=not available,
            failure_count=0 if available else 1,
            success_rate=1.0 if available else 0.0
        )
    
    def get_provider_status_from_system(self) -> List[ProviderStatus]:
        """Получает статус провайдеров из системы (если возможно)"""
        try:
            # Попытка импорта системных компонентов
            from config.config_manager import UnifiedConfigManager
            
            config_manager = UnifiedConfigManager()
            providers = config_manager.get_llm_providers()
            
            statuses = []
            for provider in providers:
                if hasattr(config_manager, 'providers') and provider.name in config_manager.providers:
                    provider_obj = config_manager.providers[provider.name]
                    if hasattr(provider_obj, 'get_stats'):
                        stats = provider_obj.get_stats()
                        
                        status = ProviderStatus(
                            name=provider.name,
                            available=provider_obj.is_available() if hasattr(provider_obj, 'is_available') else True,
                            circuit_break=stats.get('in_circuit_break', False),
                            failure_count=stats.get('failure_count', 0),
                            success_rate=stats.get('success_rate', 0.0),
                            last_failure_time=getattr(provider_obj, 'last_failure_time', None)
                        )
                        statuses.append(status)
            
            return statuses
            
        except Exception as e:
            print(f"⚠️ Не удалось получить статус из системы: {e}")
            return self.get_provider_status_direct()
    
    def reset_circuit_breaker_memory(self):
        """Сброс Circuit Breaker через перезапуск процесса"""
        print("🔄 СБРОС CIRCUIT BREAKER")
        print("=" * 40)
        
        print("ℹ️ Circuit Breaker хранится в памяти процесса Python")
        print("✅ Новый процесс = автоматический сброс Circuit Breaker")
        
        current_time = time.strftime("%H:%M:%S")
        print(f"⏰ Текущее время: {current_time}")
        
        print("\n💡 Способы сброса:")
        print("   1. Запустить новый тест (новый процесс)")
        print("   2. Подождать 5+ минут (автоматическое восстановление)")
        print("   3. Использовать force_reset_providers() для принудительного сброса")
        
        return True
    
    def force_reset_providers(self) -> bool:
        """Принудительный сброс провайдеров через систему"""
        try:
            from config.config_manager import UnifiedConfigManager
            
            print("🔄 ПРИНУДИТЕЛЬНЫЙ СБРОС ПРОВАЙДЕРОВ")
            print("=" * 45)
            
            config_manager = UnifiedConfigManager()
            providers = config_manager.get_llm_providers()
            
            reset_count = 0
            for provider in providers:
                if hasattr(config_manager, 'providers') and provider.name in config_manager.providers:
                    provider_obj = config_manager.providers[provider.name]
                    
                    if hasattr(provider_obj, 'reset_stats'):
                        provider_obj.reset_stats()
                        print(f"✅ Сброшен {provider.name}")
                        reset_count += 1
                    else:
                        print(f"⚠️ {provider.name} не поддерживает reset_stats")
            
            print(f"\n📊 Сброшено провайдеров: {reset_count}/{len(providers)}")
            return reset_count > 0
            
        except Exception as e:
            print(f"❌ Ошибка принудительного сброса: {e}")
            print("💡 Используйте сброс через перезапуск процесса")
            return False
    
    def print_status_report(self, statuses: List[ProviderStatus]):
        """Выводит отчет о статусе провайдеров"""
        print("🤖 СТАТУС ПРОВАЙДЕРОВ")
        print("=" * 30)
        
        for status in statuses:
            icon = "✅" if status.available else "❌"
            circuit_status = "🔴 ОТКРЫТ" if status.circuit_break else "🟢 ЗАКРЫТ"
            
            print(f"{icon} {status.name}")
            print(f"   🔄 Circuit Breaker: {circuit_status}")
            print(f"   📊 Успешность: {status.success_rate:.1%}")
            print(f"   ❌ Ошибки подряд: {status.failure_count}")
            
            if status.last_failure_time:
                time_since = time.time() - status.last_failure_time
                print(f"   ⏰ Последняя ошибка: {time_since/60:.1f} мин назад")
        
        available_count = sum(1 for s in statuses if s.available)
        print(f"\n📈 Доступно: {available_count}/{len(statuses)} провайдеров")
    
    def diagnose_issues(self, statuses: List[ProviderStatus]):
        """Диагностирует проблемы с провайдерами"""
        print("\n🔍 ДИАГНОСТИКА ПРОБЛЕМ")
        print("=" * 25)
        
        issues_found = False
        
        for status in statuses:
            if not status.available:
                issues_found = True
                print(f"❌ {status.name} недоступен")
                
                if status.circuit_break:
                    print(f"   🔄 Circuit Breaker активен")
                    if status.last_failure_time:
                        time_since = time.time() - status.last_failure_time
                        if time_since < 300:  # 5 минут
                            wait_time = 300 - time_since
                            print(f"   ⏰ Подождите {wait_time/60:.1f} мин для автоматического восстановления")
                        else:
                            print(f"   ✅ Время ожидания прошло, можно сбросить")
                
                if status.failure_count >= 5:
                    print(f"   📊 Много ошибок подряд ({status.failure_count})")
                    print(f"   💡 Рекомендуется сброс Circuit Breaker")
        
        if not issues_found:
            print("✅ Проблем не обнаружено")
            print("🎉 Все провайдеры работают нормально")
    
    def suggest_actions(self, statuses: List[ProviderStatus]):
        """Предлагает действия для решения проблем"""
        print("\n💡 РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ")
        print("=" * 30)
        
        has_issues = any(not s.available for s in statuses)
        
        if not has_issues:
            print("✅ Никаких действий не требуется")
            return
        
        print("🔧 Для решения проблем:")
        print("   1. Запустите новый тест пайплайна (новый процесс)")
        print("   2. Используйте force_reset_providers() для принудительного сброса")
        print("   3. Проверьте API ключи в .env файле")
        print("   4. Подождите 5+ минут для автоматического восстановления")
        
        # Специфические рекомендации
        for status in statuses:
            if not status.available:
                if status.name == "OpenRouter":
                    print(f"\n🔧 Для {status.name}:")
                    print("   - Проверьте OPENROUTER_API_KEY")
                    print("   - Убедитесь в правильности заголовков")
                    print("   - Проверьте модель deepseek/deepseek-chat-v3.1:free")
                elif status.name == "Replicate":
                    print(f"\n🔧 Для {status.name}:")
                    print("   - Проверьте REPLICATE_API_KEY")
                    print("   - Убедитесь в доступности модели")

def main():
    """Основная функция управления Circuit Breaker"""
    print("🔄 CIRCUIT BREAKER MANAGER")
    print("=" * 40)
    
    manager = CircuitBreakerManager()
    
    # Получаем статус провайдеров
    print("📊 Получение статуса провайдеров...")
    statuses = manager.get_provider_status_from_system()
    
    if not statuses:
        print("⚠️ Не удалось получить статус провайдеров")
        print("💡 Попробуйте запустить из корневой директории проекта")
        return
    
    # Выводим отчет
    manager.print_status_report(statuses)
    
    # Диагностируем проблемы
    manager.diagnose_issues(statuses)
    
    # Предлагаем действия
    manager.suggest_actions(statuses)
    
    # Интерактивное меню
    print(f"\n🎛️ ДОСТУПНЫЕ ДЕЙСТВИЯ:")
    print("   1. Сброс через перезапуск (рекомендуется)")
    print("   2. Принудительный сброс провайдеров")
    print("   3. Повторная диагностика")
    print("   4. Выход")
    
    try:
        choice = input("\nВыберите действие (1-4): ").strip()
        
        if choice == "1":
            manager.reset_circuit_breaker_memory()
        elif choice == "2":
            manager.force_reset_providers()
        elif choice == "3":
            print("\n" + "="*50)
            main()  # Рекурсивный вызов для повторной диагностики
        elif choice == "4":
            print("👋 До свидания!")
        else:
            print("❌ Неверный выбор")
    
    except KeyboardInterrupt:
        print("\n👋 Выход по Ctrl+C")

if __name__ == "__main__":
    main()