"""Тесты специфических сценариев обработки ошибок.

Тест создан: 2024-12-19 18:46 (UTC+07)
Этап 13: Создание надежной системы обработки ошибок и автоматического восстановления
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

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
    ErrorCategory,
    ErrorSeverity,
    BackoffStrategy,
    CircuitState,
    RecoveryStrategy,
    handle_errors,
    retry,
    async_retry,
    circuit_breaker,
    async_circuit_breaker
)


class TestNetworkErrorScenarios:
    """Тесты сценариев сетевых ошибок."""
    
    @pytest.fixture
    def network_error_handler(self):
        """Фикстура для обработчика сетевых ошибок."""

        error_reporter = AsyncMock()
        recovery_manager = AsyncMock()

        # Настройка восстановления для сетевых ошибок
        recovery_manager.attempt_recovery = AsyncMock(
            return_value={"recovered": True, "strategy": "retry_with_backoff"}
        )

        handler = ErrorHandler()
        handler.error_reporter = error_reporter
        handler.recovery_manager = recovery_manager

        return handler
    
    @pytest.mark.asyncio
    async def test_connection_timeout_recovery(self, network_error_handler):
        """Тест восстановления после таймаута соединения."""
        
        error = NetworkError(
            "Connection timeout",
            context={
                "host": "api.example.com",
                "port": 443,
                "timeout": 30,
                "operation": "GET /api/data"
            }
        )
        
        result = await network_error_handler.handle_error(
            error,
            context={"retry_count": 0},
            component="http_client"
        )
        
        assert result["handled"] is True
        assert result["recovered"] is True
        assert result["recovery_strategy"] == "retry_with_backoff"
        
        # Проверка вызова восстановления
        network_error_handler.recovery_manager.attempt_recovery.assert_called_once_with(
            error,
            {"retry_count": 0},
            "http_client"
        )
    
    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self, network_error_handler):
        """Тест обработки ошибки разрешения DNS."""
        
        error = NetworkError(
            "DNS resolution failed",
            context={
                "hostname": "nonexistent.example.com",
                "dns_servers": ["8.8.8.8", "1.1.1.1"]
            }
        )
        
        # Настройка неудачного восстановления для DNS ошибок
        network_error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={"recovered": False, "reason": "DNS server unreachable"}
        )
        
        result = await network_error_handler.handle_error(
            error,
            component="dns_resolver"
        )
        
        assert result["handled"] is True
        assert result["recovered"] is False
        assert "DNS server unreachable" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_ssl_certificate_error(self, network_error_handler):
        """Тест обработки ошибки SSL сертификата."""
        
        error = NetworkError(
            "SSL certificate verification failed",
            context={
                "host": "expired-cert.example.com",
                "cert_error": "certificate has expired",
                "cert_expiry": "2023-01-01"
            }
        )
        
        result = await network_error_handler.handle_error(
            error,
            component="ssl_client"
        )
        
        assert result["handled"] is True
        # SSL ошибки обычно требуют ручного вмешательства
        network_error_handler.error_reporter.report_error.assert_called_once()


class TestResourceErrorScenarios:
    """Тесты сценариев ресурсных ошибок."""
    
    @pytest.fixture
    def resource_error_handler(self):
        """Фикстура для обработчика ресурсных ошибок."""
        
        config = {
            "memory_threshold": 0.8,  # 80% использования памяти
            "disk_threshold": 0.9,    # 90% использования диска
            "enable_resource_monitoring": True
        }
        
        error_reporter = AsyncMock()
        recovery_manager = AsyncMock()
        
        handler = ErrorHandler()
        handler.error_reporter = error_reporter
        handler.recovery_manager = recovery_manager
        
        return handler
    
    @pytest.mark.asyncio
    async def test_memory_exhaustion_recovery(self, resource_error_handler):
        """Тест восстановления при исчерпании памяти."""
        
        error = ResourceError(
            "Out of memory",
            context={
                "memory_usage": "95%",
                "available_memory": "512MB",
                "process_memory": "8GB",
                "operation": "large_file_processing"
            }
        )
        
        # Настройка восстановления с очисткой памяти
        resource_error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={
                "recovered": True,
                "strategy": "memory_cleanup",
                "freed_memory": "2GB"
            }
        )
        
        result = await resource_error_handler.handle_error(
            error,
            component="file_processor"
        )
        
        assert result["handled"] is True
        assert result["recovered"] is True
        assert result["recovery_strategy"] == "memory_cleanup"
    
    @pytest.mark.asyncio
    async def test_disk_space_exhaustion(self, resource_error_handler):
        """Тест обработки исчерпания дискового пространства."""
        
        error = ResourceError(
            "No space left on device",
            context={
                "disk_usage": "100%",
                "available_space": "0MB",
                "required_space": "500MB",
                "mount_point": "/tmp"
            }
        )
        
        # Настройка восстановления с очисткой диска
        resource_error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={
                "recovered": True,
                "strategy": "disk_cleanup",
                "freed_space": "1GB"
            }
        )
        
        result = await resource_error_handler.handle_error(
            error,
            component="temp_file_manager"
        )
        
        assert result["handled"] is True
        assert result["recovered"] is True
    
    @pytest.mark.asyncio
    async def test_file_descriptor_exhaustion(self, resource_error_handler):
        """Тест обработки исчерпания файловых дескрипторов."""
        
        error = ResourceError(
            "Too many open files",
            context={
                "open_files": 1024,
                "max_files": 1024,
                "process_id": 12345
            }
        )
        
        result = await resource_error_handler.handle_error(
            error,
            component="file_manager"
        )
        
        assert result["handled"] is True
        resource_error_handler.error_reporter.report_error.assert_called_once()


class TestProcessingErrorScenarios:
    """Тесты сценариев ошибок обработки."""
    
    @pytest.fixture
    def processing_error_handler(self):
        """Фикстура для обработчика ошибок обработки."""
        
        config = {
            "processing_timeout": 300,  # 5 минут
            "max_file_size": "100MB",
            "supported_formats": ["pdf", "docx", "txt"]
        }
        
        error_reporter = AsyncMock()
        recovery_manager = AsyncMock()
        
        handler = ErrorHandler()
        handler.error_reporter = error_reporter
        handler.recovery_manager = recovery_manager
        
        return handler
    
    @pytest.mark.asyncio
    async def test_file_corruption_error(self, processing_error_handler):
        """Тест обработки поврежденного файла."""
        
        error = ProcessingError(
            "File appears to be corrupted",
            context={
                "file_path": "/data/documents/corrupted.pdf",
                "file_size": "5MB",
                "corruption_type": "invalid_header",
                "bytes_read": 1024
            }
        )
        
        # Настройка восстановления с альтернативным парсером
        processing_error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={
                "recovered": True,
                "strategy": "alternative_parser",
                "parser_used": "fallback_pdf_parser"
            }
        )
        
        result = await processing_error_handler.handle_error(
            error,
            component="pdf_parser"
        )
        
        assert result["handled"] is True
        assert result["recovered"] is True
        assert result["recovery_strategy"] == "alternative_parser"
    
    @pytest.mark.asyncio
    async def test_unsupported_format_error(self, processing_error_handler):
        """Тест обработки неподдерживаемого формата."""
        
        error = ProcessingError(
            "Unsupported file format",
            context={
                "file_path": "/data/documents/file.xyz",
                "detected_format": "xyz",
                "supported_formats": ["pdf", "docx", "txt"]
            }
        )
        
        result = await processing_error_handler.handle_error(
            error,
            component="format_detector"
        )
        
        assert result["handled"] is True
        # Неподдерживаемые форматы обычно не восстанавливаются
        processing_error_handler.error_reporter.report_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_processing_timeout_error(self, processing_error_handler):
        """Тест обработки таймаута обработки."""
        
        error = ProcessingError(
            "Processing timeout exceeded",
            context={
                "file_path": "/data/documents/large_file.pdf",
                "file_size": "150MB",
                "processing_time": 320,  # секунд
                "timeout_limit": 300
            }
        )
        
        # Настройка восстановления с увеличенным таймаутом
        processing_error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={
                "recovered": True,
                "strategy": "extended_timeout",
                "new_timeout": 600
            }
        )
        
        result = await processing_error_handler.handle_error(
            error,
            component="document_processor"
        )
        
        assert result["handled"] is True
        assert result["recovered"] is True


class TestValidationErrorScenarios:
    """Тесты сценариев ошибок валидации."""
    
    @pytest.fixture
    def validation_error_handler(self):
        """Фикстура для обработчика ошибок валидации."""
        
        config = {
            "strict_validation": True,
            "auto_correction": True,
            "validation_rules": {
                "email": r"^[\w\.-]+@[\w\.-]+\.\w+$",
                "phone": r"^\+?[1-9]\d{1,14}$"
            }
        }
        
        error_reporter = AsyncMock()
        recovery_manager = AsyncMock()
        
        handler = ErrorHandler()
        handler.error_reporter = error_reporter
        handler.recovery_manager = recovery_manager
        
        return handler
    
    @pytest.mark.asyncio
    async def test_invalid_email_format(self, validation_error_handler):
        """Тест обработки неверного формата email."""
        
        error = ValidationError(
            "Invalid email format",
            context={
                "field": "email",
                "value": "invalid-email",
                "expected_format": "user@domain.com",
                "validation_rule": "email_regex"
            }
        )
        
        # Настройка восстановления с автокоррекцией
        validation_error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={
                "recovered": True,
                "strategy": "auto_correction",
                "corrected_value": "user@example.com"
            }
        )
        
        result = await validation_error_handler.handle_error(
            error,
            component="email_validator"
        )
        
        assert result["handled"] is True
        assert result["recovered"] is True
        assert result["recovery_strategy"] == "auto_correction"
    
    @pytest.mark.asyncio
    async def test_missing_required_field(self, validation_error_handler):
        """Тест обработки отсутствующего обязательного поля."""
        
        error = ValidationError(
            "Required field is missing",
            context={
                "field": "name",
                "record_id": "contact_123",
                "required_fields": ["name", "email", "phone"]
            }
        )
        
        # Настройка восстановления с значением по умолчанию
        validation_error_handler.recovery_manager.attempt_recovery = AsyncMock(
            return_value={
                "recovered": True,
                "strategy": "default_value",
                "default_value": "Unknown"
            }
        )
        
        result = await validation_error_handler.handle_error(
            error,
            component="field_validator"
        )
        
        assert result["handled"] is True
        assert result["recovered"] is True
    
    @pytest.mark.asyncio
    async def test_data_type_mismatch(self, validation_error_handler):
        """Тест обработки несоответствия типа данных."""
        
        error = ValidationError(
            "Data type mismatch",
            context={
                "field": "age",
                "expected_type": "integer",
                "actual_type": "string",
                "value": "twenty-five"
            }
        )
        
        result = await validation_error_handler.handle_error(
            error,
            component="type_validator"
        )
        
        assert result["handled"] is True
        validation_error_handler.error_reporter.report_error.assert_called_once()


class TestComplexErrorScenarios:
    """Тесты сложных сценариев с множественными ошибками."""
    
    @pytest.fixture
    def complex_error_handler(self):
        """Фикстура для обработчика сложных ошибок."""
        
        error_reporter = AsyncMock()
        recovery_manager = AsyncMock()
        
        handler = ErrorHandler()
        handler.error_reporter = error_reporter
        handler.recovery_manager = recovery_manager
        
        return handler
    
    @pytest.mark.asyncio
    async def test_cascading_errors(self, complex_error_handler):
        """Тест обработки каскадных ошибок."""
        
        # Первичная ошибка
        primary_error = NetworkError(
            "Database connection lost",
            context={"database": "contacts_db", "connection_id": "conn_123"}
        )
        
        # Вторичные ошибки
        secondary_errors = [
            ProcessingError(
                "Cannot save contact",
                context={"contact_id": "contact_456", "cause": "db_unavailable"}
            ),
            ValidationError(
                "Cannot validate against database",
                context={"validation_type": "uniqueness_check"}
            )
        ]
        
        # Обработка первичной ошибки
        result = await complex_error_handler.handle_error(
            primary_error,
            component="database_client"
        )
        
        assert result["handled"] is True
        
        # Обработка вторичных ошибок
        for error in secondary_errors:
            secondary_result = await complex_error_handler.handle_error(
                error,
                component="contact_processor"
            )
            assert secondary_result["handled"] is True
    
    @pytest.mark.asyncio
    async def test_batch_processing_errors(self, complex_error_handler):
        """Тест обработки ошибок при пакетной обработке."""
        
        batch_errors = [
            ProcessingError(
                f"Failed to process file {i}",
                context={"file_id": f"file_{i}", "batch_id": "batch_001"}
            )
            for i in range(5)
        ]
        
        results = []
        for error in batch_errors:
            result = await complex_error_handler.handle_error(
                error,
                component="batch_processor"
            )
            results.append(result)
        
        # Все ошибки должны быть обработаны
        assert all(result["handled"] for result in results)
        
        # Проверка количества вызовов репортера
        assert complex_error_handler.error_reporter.report_error.call_count == 5
    
    @pytest.mark.asyncio
    async def test_error_storm_protection(self, complex_error_handler):
        """Тест защиты от шторма ошибок."""
        
        # Имитация множественных одинаковых ошибок
        storm_error = NetworkError(
            "Service unavailable",
            context={"service": "external_api", "endpoint": "/api/validate"}
        )
        
        # Настройка circuit breaker для защиты
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=0.1
        )
        
        # Имитация множественных вызовов
        failure_count = 0
        for i in range(10):
            try:
                await circuit_breaker.async_call(
                    lambda: complex_error_handler.handle_error(
                        storm_error,
                        component="api_client"
                    )
                )
            except Exception:
                failure_count += 1
        
        # Circuit breaker должен сработать и предотвратить часть вызовов
        assert circuit_breaker.state in [CircuitState.OPEN, CircuitState.HALF_OPEN]


class TestErrorHandlingPerformance:
    """Тесты производительности системы обработки ошибок."""
    
    @pytest.mark.asyncio
    async def test_high_volume_error_handling(self):
        """Тест обработки большого количества ошибок."""
        
        error_handler = ErrorHandler()
        
        # Создание множества ошибок
        errors = [
            NetworkError(f"Error {i}")
            for i in range(100)
        ]
        
        start_time = datetime.now()
        
        # Обработка всех ошибок
        tasks = [
            error_handler.handle_error(error, component="performance_test")
            for error in errors
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Проверка результатов
        assert len(results) == 100
        assert all(result["handled"] for result in results)
        
        # Проверка производительности (должно быть быстро)
        assert processing_time < 5.0  # Менее 5 секунд для 100 ошибок
        
        print(f"Processed 100 errors in {processing_time:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_error_handling(self):
        """Тест использования памяти при обработке ошибок."""
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        error_handler = ErrorHandler()
        
        # Создание и обработка множества ошибок с большим контекстом
        for i in range(50):
            large_context = {
                "data": "x" * 1000,  # 1KB строка
                "iteration": i,
                "timestamp": datetime.now().isoformat()
            }
            
            error = ProcessingError(
                f"Large context error {i}",
                context=large_context
            )
            
            await error_handler.handle_error(
                error,
                component="memory_test"
            )
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Проверка, что увеличение памяти разумно (менее 50MB)
        assert memory_increase < 50 * 1024 * 1024
        
        print(f"Memory increase: {memory_increase / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ])