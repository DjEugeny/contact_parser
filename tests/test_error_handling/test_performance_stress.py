"""Тесты производительности и нагрузочные тесты системы обработки ошибок.

Тест создан: 2024-12-19 18:47 (UTC+07)
Этап 13: Создание надежной системы обработки ошибок и автоматического восстановления
"""

import asyncio
import time
import threading
import pytest
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

# Импорт тестируемых компонентов
from src.core.error_handling import (
    ErrorHandler,
    RetryManager,
    CircuitBreaker,
    RecoveryManager,
    ErrorReporter,
    NetworkError,
    ProcessingError,
    ValidationError,
    ResourceError,
    BackoffStrategy,
    CircuitState,
    RecoveryStrategy
)


class TestPerformanceBenchmarks:
    """Бенчмарки производительности системы обработки ошибок."""
    
    @pytest.fixture
    def performance_system(self):
        """Фикстура для системы с оптимизированной конфигурацией."""
        
        config = {
            "log_level": "ERROR",  # Минимальное логирование для производительности
            "include_stack_trace": False,
            "enable_recovery": True,
            "default_max_attempts": 3,
            "default_base_delay": 0.001,  # Минимальные задержки
            "default_max_delay": 0.1,
            "default_failure_threshold": 5,
            "default_recovery_timeout": 0.1,
            "enable_metrics": True,
            "batch_size": 100  # Пакетная обработка для производительности
        }
        
        error_handler = ErrorHandler()
        error_handler.error_reporter = AsyncMock()
        error_handler.recovery_manager = AsyncMock()
        
        return {
            "error_handler": error_handler,
            "retry_manager": RetryManager(config=config),
            "circuit_breaker": CircuitBreaker(failure_threshold=5, recovery_timeout=0.1),
            "recovery_manager": RecoveryManager(config=config)
        }
    
    @pytest.mark.asyncio
    async def test_single_error_handling_speed(self, performance_system):
        """Тест скорости обработки одной ошибки."""
        
        error_handler = performance_system["error_handler"]
        
        # Настройка быстрого восстановления
        error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={"recovered": True, "strategy": "fast_recovery"}
        )
        
        error = NetworkError("Test error")
        
        # Измерение времени обработки одной ошибки
        start_time = time.perf_counter()
        
        result = await error_handler.handle_error(
            error,
            component="performance_test"
        )
        
        end_time = time.perf_counter()
        processing_time = end_time - start_time
        
        assert result["handled"] is True
        assert processing_time < 0.01  # Менее 10ms на одну ошибку
        
        print(f"Single error processing time: {processing_time*1000:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_batch_error_handling_throughput(self, performance_system):
        """Тест пропускной способности при пакетной обработке ошибок."""
        
        error_handler = performance_system["error_handler"]
        
        # Настройка быстрого восстановления
        error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={"recovered": True, "strategy": "batch_recovery"}
        )
        
        # Создание пакета ошибок
        batch_size = 1000
        errors = [
            NetworkError(f"Batch error {i}")
            for i in range(batch_size)
        ]
        
        start_time = time.perf_counter()
        
        # Параллельная обработка ошибок
        tasks = [
            error_handler.handle_error(error, component="batch_test")
            for error in errors
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        throughput = batch_size / total_time
        
        assert len(results) == batch_size
        assert all(result["handled"] for result in results)
        assert throughput > 100  # Более 100 ошибок в секунду
        
        print(f"Batch throughput: {throughput:.0f} errors/second")
        print(f"Total time for {batch_size} errors: {total_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_retry_manager_performance(self, performance_system):
        """Тест производительности RetryManager."""
        
        retry_manager = performance_system["retry_manager"]
        
        call_count = 0
        
        async def fast_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Temporary failure")
            return "success"
        
        start_time = time.perf_counter()
        
        result = await retry_manager.async_retry(
            fast_failing_function,
            max_attempts=3,
            backoff_strategy=BackoffStrategy.FIXED,
            base_delay=0.001  # Минимальная задержка
        )
        
        end_time = time.perf_counter()
        retry_time = end_time - start_time
        
        assert result == "success"
        assert call_count == 3
        assert retry_time < 0.1  # Менее 100ms для 3 попыток
        
        print(f"Retry operation time: {retry_time*1000:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_performance(self, performance_system):
        """Тест производительности CircuitBreaker."""
        
        circuit_breaker = performance_system["circuit_breaker"]
        
        async def fast_function():
            return "success"
        
        # Измерение времени успешных вызовов
        iterations = 1000
        start_time = time.perf_counter()
        
        for _ in range(iterations):
            result = await circuit_breaker.async_call(fast_function)
            assert result == "success"
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        calls_per_second = iterations / total_time
        
        assert calls_per_second > 1000  # Более 1000 вызовов в секунду
        
        print(f"Circuit breaker throughput: {calls_per_second:.0f} calls/second")


class TestStressTests:
    """Стресс-тесты системы обработки ошибок."""
    
    @pytest.fixture
    def stress_system(self):
        """Фикстура для стресс-тестирования."""
        
        error_handler = ErrorHandler()
        error_handler.error_reporter = AsyncMock()
        error_handler.recovery_manager = AsyncMock()
        
        return {
            "error_handler": error_handler,
            "retry_manager": Mock(),
            "circuit_breaker": Mock(),
            "recovery_manager": Mock(),
            "error_reporter": Mock()
        }
    
    @pytest.mark.asyncio
    async def test_high_concurrency_error_handling(self, stress_system):
        """Тест обработки ошибок при высокой конкурентности."""
        
        error_handler = stress_system["error_handler"]
        
        # Настройка восстановления
        error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={"recovered": True, "strategy": "concurrent_recovery"}
        )
        
        # Создание множества конкурентных задач
        concurrency_level = 100
        errors_per_task = 10
        
        async def error_generation_task(task_id):
            """Задача генерации и обработки ошибок."""
            results = []
            for i in range(errors_per_task):
                error = ProcessingError(
                    f"Concurrent error {task_id}-{i}",
                    context={"task_id": task_id, "error_index": i}
                )
                
                result = await error_handler.handle_error(
                    error,
                    component=f"concurrent_task_{task_id}"
                )
                results.append(result)
            
            return results
        
        start_time = time.perf_counter()
        
        # Запуск конкурентных задач
        tasks = [
            error_generation_task(task_id)
            for task_id in range(concurrency_level)
        ]
        
        all_results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Проверка результатов
        total_errors = concurrency_level * errors_per_task
        flattened_results = [result for task_results in all_results for result in task_results]
        
        assert len(flattened_results) == total_errors
        assert all(result["handled"] for result in flattened_results)
        
        throughput = total_errors / total_time
        print(f"High concurrency throughput: {throughput:.0f} errors/second")
        print(f"Processed {total_errors} errors in {total_time:.2f}s with {concurrency_level} concurrent tasks")
    
    @pytest.mark.asyncio
    async def test_memory_stress_test(self, stress_system):
        """Стресс-тест использования памяти."""
        
        error_handler = stress_system["error_handler"]
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Создание ошибок с большим контекстом
        large_context_size = 10000  # 10KB контекст
        num_errors = 500
        
        memory_samples = []
        
        for i in range(num_errors):
            # Создание ошибки с большим контекстом
            large_context = {
                "large_data": "x" * large_context_size,
                "error_id": i,
                "timestamp": datetime.now().isoformat(),
                "metadata": {f"key_{j}": f"value_{j}" for j in range(100)}
            }
            
            error = ResourceError(
                f"Memory stress error {i}",
                context=large_context
            )
            
            await error_handler.handle_error(
                error,
                component="memory_stress_test"
            )
            
            # Сэмплирование памяти каждые 50 ошибок
            if i % 50 == 0:
                current_memory = process.memory_info().rss
                memory_samples.append(current_memory)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        max_memory_increase = max(sample - initial_memory for sample in memory_samples)
        
        # Проверка разумного использования памяти
        max_allowed_increase = 100 * 1024 * 1024  # 100MB
        assert memory_increase < max_allowed_increase
        
        print(f"Memory increase: {memory_increase / 1024 / 1024:.2f} MB")
        print(f"Max memory increase: {max_memory_increase / 1024 / 1024:.2f} MB")
        print(f"Processed {num_errors} errors with {large_context_size} byte contexts")
    
    def test_thread_safety_stress(self, stress_system):
        """Стресс-тест потокобезопасности."""
        
        error_handler = stress_system["error_handler"]
        
        # Настройка синхронного восстановления для тестирования потоков
        error_handler.recovery_manager.attempt_recovery = Mock(
            return_value={"recovered": True, "strategy": "thread_safe_recovery"}
        )
        
        num_threads = 10
        errors_per_thread = 50
        results = []
        
        def thread_worker(thread_id):
            """Рабочая функция потока."""
            thread_results = []
            
            for i in range(errors_per_thread):
                error = ValidationError(
                    f"Thread {thread_id} error {i}",
                    context={"thread_id": thread_id, "error_index": i}
                )
                
                # Синхронная обработка ошибки
                result = asyncio.run(
                    error_handler.handle_error(
                        error,
                        component=f"thread_{thread_id}"
                    )
                )
                thread_results.append(result)
            
            return thread_results
        
        start_time = time.perf_counter()
        
        # Запуск потоков
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_thread = {
                executor.submit(thread_worker, thread_id): thread_id
                for thread_id in range(num_threads)
            }
            
            for future in as_completed(future_to_thread):
                thread_id = future_to_thread[future]
                try:
                    thread_results = future.result()
                    results.extend(thread_results)
                except Exception as exc:
                    print(f"Thread {thread_id} generated an exception: {exc}")
                    raise
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Проверка результатов
        total_errors = num_threads * errors_per_thread
        assert len(results) == total_errors
        assert all(result["handled"] for result in results)
        
        throughput = total_errors / total_time
        print(f"Thread safety throughput: {throughput:.0f} errors/second")
        print(f"Processed {total_errors} errors across {num_threads} threads in {total_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_error_storm_resilience(self, stress_system):
        """Тест устойчивости к шторму ошибок."""
        
        error_handler = stress_system["error_handler"]
        circuit_breaker = stress_system["circuit_breaker"]
        
        # Имитация шторма одинаковых ошибок
        storm_error = NetworkError(
            "Service unavailable - error storm",
            context={"service": "external_api", "storm_id": "storm_001"}
        )
        
        storm_size = 1000
        handled_count = 0
        blocked_count = 0
        
        start_time = time.perf_counter()
        
        # Генерация шторма ошибок
        for i in range(storm_size):
            try:
                # Использование circuit breaker для защиты
                result = await circuit_breaker.async_call(
                    lambda: error_handler.handle_error(
                        storm_error,
                        component="storm_test"
                    )
                )
                
                if result and result.get("handled"):
                    handled_count += 1
                    
            except Exception:
                blocked_count += 1
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Проверка защиты от шторма
        assert blocked_count > 0  # Circuit breaker должен сработать
        assert handled_count + blocked_count == storm_size
        
        # Circuit breaker должен быть открыт или полуоткрыт
        assert circuit_breaker.state in [CircuitState.OPEN, CircuitState.HALF_OPEN]
        
        print(f"Error storm results:")
        print(f"  Total errors: {storm_size}")
        print(f"  Handled: {handled_count}")
        print(f"  Blocked by circuit breaker: {blocked_count}")
        print(f"  Processing time: {total_time:.2f}s")
        print(f"  Circuit breaker state: {circuit_breaker.state}")


class TestResourceUtilization:
    """Тесты использования ресурсов системой обработки ошибок."""
    
    @pytest.mark.asyncio
    async def test_cpu_utilization_under_load(self):
        """Тест использования CPU под нагрузкой."""
        
        error_handler = ErrorHandler()
        error_handler.error_reporter = AsyncMock()
        error_handler.recovery_manager = AsyncMock()
        
        # Настройка восстановления с вычислительной нагрузкой
        async def cpu_intensive_recovery(**kwargs):
            # Имитация CPU-интенсивного восстановления
            result = sum(i * i for i in range(1000))
            return {"recovered": True, "strategy": "cpu_intensive", "result": result}
        
        error_handler.recovery_manager.attempt_recovery = cpu_intensive_recovery
        
        # Мониторинг CPU
        process = psutil.Process(os.getpid())
        cpu_samples = []
        
        async def cpu_monitor():
            """Мониторинг использования CPU."""
            for _ in range(10):
                cpu_percent = process.cpu_percent()
                cpu_samples.append(cpu_percent)
                await asyncio.sleep(0.1)
        
        # Запуск мониторинга и обработки ошибок
        monitor_task = asyncio.create_task(cpu_monitor())
        
        # Генерация нагрузки
        errors = [
            ProcessingError(f"CPU test error {i}")
            for i in range(50)
        ]
        
        error_tasks = [
            error_handler.handle_error(error, component="cpu_test")
            for error in errors
        ]
        
        # Выполнение задач
        results, _ = await asyncio.gather(
            asyncio.gather(*error_tasks),
            monitor_task
        )
        
        # Анализ использования CPU
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0
        
        assert len(results) == 50
        assert all(result["handled"] for result in results)
        
        print(f"CPU utilization - Average: {avg_cpu:.1f}%, Max: {max_cpu:.1f}%")
    
    @pytest.mark.asyncio
    async def test_io_performance_under_error_load(self):
        """Тест производительности I/O при обработке ошибок."""
        
        import tempfile
        import aiofiles
        
        error_handler = ErrorHandler()
        error_handler.error_reporter = AsyncMock()
        error_handler.recovery_manager = AsyncMock()
        
        # Создание временного файла для I/O тестов
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            # Настройка восстановления с I/O операциями
            async def io_intensive_recovery(**kwargs):
                # Имитация I/O интенсивного восстановления
                async with aiofiles.open(temp_file_path, 'a') as f:
                    await f.write(f"Recovery log: {datetime.now()}\n")
                return {"recovered": True, "strategy": "io_intensive"}
            
            error_handler.recovery_manager.attempt_recovery = io_intensive_recovery
            
            # Генерация ошибок с I/O нагрузкой
            num_errors = 100
            errors = [
                ResourceError(f"I/O test error {i}")
                for i in range(num_errors)
            ]
            
            start_time = time.perf_counter()
            
            # Обработка ошибок с I/O операциями
            tasks = [
                error_handler.handle_error(error, component="io_test")
                for error in errors
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # Проверка результатов
            assert len(results) == num_errors
            assert all(result["handled"] for result in results)
            
            # Проверка I/O производительности
            io_throughput = num_errors / total_time
            assert io_throughput > 10  # Минимум 10 I/O операций в секунду
            
            print(f"I/O performance: {io_throughput:.1f} operations/second")
            print(f"Total I/O time: {total_time:.2f}s for {num_errors} operations")
            
        finally:
            # Очистка временного файла
            os.unlink(temp_file_path)


if __name__ == "__main__":
    # Запуск тестов производительности
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "not slow",  # Исключение медленных тестов по умолчанию
        "--disable-warnings"
    ])