"""Комплексные тесты системы обработки ошибок.

Тест создан: 2024-12-19 18:45 (UTC+07)
Этап 13: Создание надежной системы обработки ошибок и автоматического восстановления
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Импорт тестируемых компонентов
from src.core.error_handling import (
    ErrorHandler,
    RetryManager,
    CircuitBreaker,
    RecoveryManager,
    ErrorReporter,
    BaseProcessingError,
    NetworkError,
    ProcessingError,
    ValidationError,
    ResourceError,
    ErrorCategory,
    ErrorSeverity,
    BackoffStrategy,
    CircuitState,
    RecoveryStrategy,
    handle_errors,
    retry,
    circuit_breaker,
    create_error_handling_system,
    get_default_config
)


class TestExceptions:
    """Тесты базовых исключений."""
    
    def test_base_processing_error_creation(self):
        """Тест создания базового исключения."""
        
        error = BaseProcessingError(
            "Test error",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.HIGH,
            context={"key": "value"}
        )
        
        assert str(error) == "Test error"
        assert error.category == ErrorCategory.PROCESSING
        assert error.severity == ErrorSeverity.HIGH
        assert error.context == {"key": "value"}
        assert error.timestamp is not None
    
    def test_error_to_dict(self):
        """Тест преобразования ошибки в словарь."""
        
        error = NetworkError(
            "Connection failed",
            context={"host": "example.com", "port": 80}
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["message"] == "Connection failed"
        assert error_dict["category"] == "network"
        assert error_dict["severity"] == "high"
        assert error_dict["context"] == {"host": "example.com", "port": 80}
        assert "timestamp" in error_dict
        assert "error_type" in error_dict
    
    def test_specific_error_types(self):
        """Тест специфических типов ошибок."""
        
        # NetworkError
        net_error = NetworkError("Network issue")
        assert net_error.category == ErrorCategory.NETWORK
        assert net_error.severity == ErrorSeverity.HIGH
        
        # ValidationError
        val_error = ValidationError("Invalid data")
        assert val_error.category == ErrorCategory.VALIDATION
        assert val_error.severity == ErrorSeverity.MEDIUM
        
        # ResourceError
        res_error = ResourceError("Out of memory")
        assert res_error.category == ErrorCategory.RESOURCE
        assert res_error.severity == ErrorSeverity.HIGH


class TestErrorHandler:
    """Тесты ErrorHandler."""
    
    @pytest.fixture
    def error_handler(self):
        """Фикстура для создания ErrorHandler."""
        
        config = {
            "log_level": "INFO",
            "include_stack_trace": True,
            "max_context_size": 1000,
            "enable_recovery": True
        }
        
        mock_reporter = Mock()
        mock_recovery = Mock()
        
        return ErrorHandler()
    
    def test_error_handler_creation(self, error_handler):
        """Тест создания ErrorHandler."""
        
        assert error_handler.config["log_level"] == "INFO"
        assert error_handler.config["enable_recovery"] is True
        assert error_handler.error_reporter is not None
        assert error_handler.recovery_manager is not None
    
    @pytest.mark.asyncio
    async def test_handle_error_with_recovery(self, error_handler):
        """Тест обработки ошибки с восстановлением."""
        
        # Настройка мока для восстановления
        error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={"recovered": True, "strategy": "retry"}
        )
        
        error = NetworkError("Connection failed")
        context = {"operation": "data_fetch"}
        
        result = await error_handler.handle_error(error, context, "test_component")
        
        assert result["handled"] is True
        assert result["recovered"] is True
        assert result["recovery_strategy"] == "retry"
        
        # Проверка вызовов
        error_handler.error_reporter.report_error.assert_called_once()
        error_handler.recovery_manager.attempt_recovery.assert_called_once()
    
    def test_handle_errors_decorator(self):
        """Тест декоратора handle_errors."""
        
        @handle_errors()
        def test_function():
            raise ValueError("Test error")
        
        # Функция должна выполниться без исключения
        result = test_function()
        assert result is None  # Ошибка обработана
    
    def test_handle_errors_decorator_with_return_on_error(self):
        """Тест декоратора с возвратом значения при ошибке."""
        
        @handle_errors(return_on_error="default_value")
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        assert result == "default_value"


class TestRetryManager:
    """Тесты RetryManager."""
    
    @pytest.fixture
    def retry_manager(self):
        """Фикстура для создания RetryManager."""
        
        config = {
            "default_max_attempts": 3,
            "default_backoff_strategy": "exponential",
            "default_base_delay": 0.1,  # Быстрые тесты
            "default_max_delay": 1.0,
            "default_jitter": False  # Предсказуемые задержки для тестов
        }
        
        return RetryManager(config)
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failure(self, retry_manager):
        """Тест успешного выполнения после неудач."""
        
        call_count = 0
        
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Temporary failure")
            return "success"
        
        result = await retry_manager.async_retry(
            failing_function,
            max_attempts=3,
            backoff_strategy=BackoffStrategy.FIXED,
            base_delay=0.01
        )
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self, retry_manager):
        """Тест превышения максимального количества попыток."""
        
        call_count = 0
        
        async def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise NetworkError("Persistent failure")
        
        with pytest.raises(NetworkError):
            await retry_manager.async_retry(
                always_failing_function,
                max_attempts=3,
                backoff_strategy=BackoffStrategy.FIXED,
                base_delay=0.01
            )
        
        assert call_count == 3
    
    def test_retry_decorator(self):
        """Тест декоратора retry."""
        
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 3
    
    def test_backoff_strategies(self, retry_manager):
        """Тест различных стратегий задержки."""
        
        # Фиксированная задержка
        delay = retry_manager._calculate_delay(BackoffStrategy.FIXED, 2, 1.0, 10.0, False)
        assert delay == 1.0
        
        # Линейная задержка
        delay = retry_manager._calculate_delay(BackoffStrategy.LINEAR, 2, 1.0, 10.0, False)
        assert delay == 2.0
        
        # Экспоненциальная задержка
        delay = retry_manager._calculate_delay(BackoffStrategy.EXPONENTIAL, 2, 1.0, 10.0, False)
        assert delay == 2.0  # 1.0 * 2^1
        
        # Проверка максимальной задержки
        delay = retry_manager._calculate_delay(BackoffStrategy.EXPONENTIAL, 10, 1.0, 5.0, False)
        assert delay == 5.0  # Ограничено max_delay


class TestCircuitBreaker:
    """Тесты CircuitBreaker."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Фикстура для создания CircuitBreaker."""
        
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=0.1  # Быстрое восстановление для тестов
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_normal_operation(self, circuit_breaker):
        """Тест нормальной работы circuit breaker."""
        
        async def successful_function():
            return "success"
        
        result = await circuit_breaker.async_call(successful_function)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, circuit_breaker):
        """Тест открытия circuit breaker при неудачах."""
        
        async def failing_function():
            raise ValueError("Test failure")
        
        # Выполняем неудачные вызовы до достижения порога
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.async_call(failing_function)
        
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self, circuit_breaker):
        """Тест восстановления через состояние HALF_OPEN."""
        
        async def failing_function():
            raise ValueError("Test failure")
        
        async def successful_function():
            return "success"
        
        # Открываем circuit breaker
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.async_call(failing_function)
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Ждем timeout для перехода в HALF_OPEN
        await asyncio.sleep(0.15)
        
        # Успешный вызов должен закрыть circuit breaker
        result = await circuit_breaker.async_call(successful_function)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
    
    def test_circuit_breaker_decorator(self):
        """Тест декоратора circuit_breaker."""
        
        @circuit_breaker(failure_threshold=2, recovery_timeout=0.1)
        def test_function(should_fail=False):
            if should_fail:
                raise ValueError("Test failure")
            return "success"
        
        # Нормальная работа
        result = test_function()
        assert result == "success"
        
        # Неудачи до открытия
        with pytest.raises(ValueError):
            test_function(should_fail=True)
        with pytest.raises(ValueError):
            test_function(should_fail=True)
        
        # Circuit breaker должен быть открыт
        # Следующий вызов должен быть заблокирован
        from src.core.error_handling.circuit_breaker import CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            test_function()


class TestRecoveryManager:
    """Тесты RecoveryManager."""
    
    @pytest.fixture
    def recovery_manager(self):
        """Фикстура для создания RecoveryManager."""
        
        config = {
            "max_recovery_attempts": 3,
            "recovery_timeout": 1.0,
            "enable_auto_recovery": True,
            "recovery_cooldown": 0.1
        }
        
        return RecoveryManager(config)
    
    @pytest.mark.asyncio
    async def test_recovery_strategy_registration(self, recovery_manager):
        """Тест регистрации стратегий восстановления."""
        
        async def test_recovery_action(**kwargs):
            return {"success": True, "action": "test_recovery"}
        
        recovery_manager.register_recovery_strategy(
            "TestError",
            RecoveryStrategy.RETRY,
            test_recovery_action,
            "Test recovery strategy"
        )
        
        assert "TestError" in recovery_manager.recovery_strategies
        assert len(recovery_manager.recovery_strategies["TestError"]) == 1
    
    @pytest.mark.asyncio
    async def test_successful_recovery(self, recovery_manager):
        """Тест успешного восстановления."""
        
        async def successful_recovery(**kwargs):
            return {"success": True, "action": "recovered"}
        
        recovery_manager.register_recovery_strategy(
            "ValueError",
            RecoveryStrategy.RETRY,
            successful_recovery,
            "Test recovery",
            priority=1
        )
        
        error = ValueError("Test error")
        result = await recovery_manager.attempt_recovery(error)
        
        assert result["recovered"] is True
        assert result["strategy"] == "retry"
    
    @pytest.mark.asyncio
    async def test_recovery_failure(self, recovery_manager):
        """Тест неудачного восстановления."""
        
        async def failing_recovery(**kwargs):
            return {"success": False, "reason": "Recovery failed"}
        
        recovery_manager.register_recovery_strategy(
            "ValueError",
            RecoveryStrategy.RETRY,
            failing_recovery,
            "Failing recovery"
        )
        
        error = ValueError("Test error")
        result = await recovery_manager.attempt_recovery(error)
        
        assert result["recovered"] is False
        assert "All recovery strategies failed" in result["reason"]
    
    def test_recovery_stats(self, recovery_manager):
        """Тест статистики восстановлений."""
        
        # Имитация восстановлений
        recovery_manager.recovery_stats["total_recoveries"] = 10
        recovery_manager.recovery_stats["successful_recoveries"] = 7
        recovery_manager.recovery_stats["failed_recoveries"] = 3
        
        stats = recovery_manager.get_recovery_stats()
        
        assert stats["total_recoveries"] == 10
        assert stats["successful_recoveries"] == 7
        assert stats["failed_recoveries"] == 3
        assert stats["success_rate"] == 70.0


class TestErrorReporter:
    """Тесты ErrorReporter."""
    
    @pytest.fixture
    def error_reporter(self):
        """Фикстура для создания ErrorReporter."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "log_level": "INFO",
                "include_stack_trace": True,
                "max_context_size": 1000,
                "enable_metrics": True,
                "metrics_file": str(Path(temp_dir) / "test_metrics.json")
            }
            
            yield ErrorReporter(config)
    
    def test_error_reporting(self, error_reporter):
        """Тест отчета об ошибке."""
        
        error = NetworkError("Connection failed")
        context = {"host": "example.com"}
        
        report = error_reporter.report_error(
            error,
            context=context,
            component="network_client"
        )
        
        assert report["error"]["message"] == "Connection failed"
        assert report["context"] == context
        assert report["component"] == "network_client"
        assert "timestamp" in report
        assert "error_id" in report
    
    def test_metrics_update(self, error_reporter):
        """Тест обновления метрик."""
        
        # Отчет о нескольких ошибках
        errors = [
            NetworkError("Network error 1"),
            NetworkError("Network error 2"),
            ValidationError("Validation error 1")
        ]
        
        for error in errors:
            error_reporter.report_error(error, component="test_component")
        
        metrics = error_reporter.get_metrics()
        
        assert metrics["total_errors"] == 3
        assert metrics["errors_by_category"]["network"] == 2
        assert metrics["errors_by_category"]["validation"] == 1
        assert metrics["errors_by_component"]["test_component"] == 3
    
    def test_error_summary(self, error_reporter):
        """Тест сводки ошибок."""
        
        # Добавление ошибок
        for i in range(5):
            error_reporter.report_error(
                NetworkError(f"Error {i}"),
                component="test_component"
            )
        
        summary = error_reporter.get_error_summary(hours=24)
        
        assert summary["total_errors"] == 5
        assert summary["most_common_category"] == "network"
        assert summary["most_affected_component"] == "test_component"
        assert summary["error_rate_per_hour"] > 0


class TestIntegration:
    """Интеграционные тесты системы обработки ошибок."""
    
    def test_create_error_handling_system(self):
        """Тест создания полной системы обработки ошибок."""
        
        system = create_error_handling_system()
        
        assert "error_handler" in system
        assert "retry_manager" in system
        assert "circuit_breaker" in system
        assert "recovery_manager" in system
        assert "error_reporter" in system
        assert "config" in system
        
        # Проверка типов компонентов
        assert isinstance(system["error_handler"], ErrorHandler)
        assert isinstance(system["retry_manager"], RetryManager)
        assert isinstance(system["circuit_breaker"], CircuitBreaker)
        assert isinstance(system["recovery_manager"], RecoveryManager)
        assert isinstance(system["error_reporter"], ErrorReporter)
    
    def test_get_default_config(self):
        """Тест получения конфигурации по умолчанию."""
        
        config = get_default_config()
        
        assert "error_handler" in config
        assert "retry" in config
        assert "circuit_breaker" in config
        assert "recovery" in config
        assert "reporting" in config
        
        # Проверка значений по умолчанию
        assert config["retry"]["default_max_attempts"] == 3
        assert config["circuit_breaker"]["default_failure_threshold"] == 5
        assert config["recovery"]["enable_auto_recovery"] is True
    
    @pytest.mark.asyncio
    async def test_full_error_handling_flow(self):
        """Тест полного потока обработки ошибок."""
        
        system = create_error_handling_system()
        error_handler = system["error_handler"]
        
        # Имитация ошибки с контекстом
        error = NetworkError("Connection timeout")
        context = {
            "operation": "data_fetch",
            "url": "https://api.example.com/data",
            "timeout": 30
        }
        
        # Настройка мока для восстановления
        error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={"recovered": True, "strategy": "retry"}
        )
        
        # Обработка ошибки
        result = await error_handler.handle_error(
            error,
            context=context,
            component="api_client"
        )
        
        # Проверка результата
        assert result["handled"] is True
        assert result["recovered"] is True
        
        # Проверка вызовов компонентов
        error_handler.error_reporter.report_error.assert_called_once()
        error_handler.recovery_manager.attempt_recovery.assert_called_once()
    
    def test_combined_decorators(self):
        """Тест комбинирования декораторов."""
        
        call_count = 0
        
        @handle_errors(return_on_error="error_handled")
        @retry(max_attempts=2, base_delay=0.01)
        @circuit_breaker(failure_threshold=3, recovery_timeout=0.1)
        def test_function(should_fail=False):
            nonlocal call_count
            call_count += 1
            
            if should_fail and call_count < 2:
                raise ValueError("Temporary failure")
            
            return "success"
        
        # Успешное выполнение после одной неудачи
        result = test_function(should_fail=True)
        assert result == "success"
        assert call_count == 2  # Одна неудача + успех


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ])