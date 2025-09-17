"""Централизованная система отчетности и логирования ошибок."""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict, deque

from .exceptions import BaseProcessingError, ErrorCategory, ErrorSeverity


class ErrorReporter:
    """Централизованный репортер ошибок с метриками и аналитикой."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = logging.getLogger(__name__)
        
        # Инициализация хранилища метрик
        self.metrics_file = Path(self.config.get("metrics_file", "logs/error_metrics.json"))
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Буфер для недавних ошибок (для анализа трендов)
        self.recent_errors = deque(maxlen=1000)
        
        # Счетчики и метрики
        self.metrics = {
            "total_errors": 0,
            "errors_by_category": defaultdict(int),
            "errors_by_severity": defaultdict(int),
            "errors_by_hour": defaultdict(int),
            "errors_by_component": defaultdict(int),
            "error_trends": [],
            "last_updated": datetime.now().isoformat()
        }
        
        # Загрузка существующих метрик
        self._load_metrics()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию."""
        return {
            "log_level": "INFO",
            "include_stack_trace": True,
            "max_context_size": 1000,
            "enable_metrics": True,
            "metrics_file": "logs/error_metrics.json",
            "alert_thresholds": {
                "error_rate_per_hour": 50,
                "critical_errors_per_hour": 5,
                "component_error_rate": 10
            },
            "retention_days": 30
        }
    
    def report_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Основной метод для отчета об ошибке."""
        
        # Преобразование в BaseProcessingError если необходимо
        if not isinstance(error, BaseProcessingError):
            error = self._convert_to_processing_error(error, context)
        
        # Создание записи об ошибке
        error_record = self._create_error_record(
            error, context, component, additional_data
        )
        
        # Добавление в буфер недавних ошибок
        self.recent_errors.append(error_record)
        
        # Обновление метрик
        self._update_metrics(error_record)
        
        # Логирование ошибки
        self._log_error(error_record)
        
        # Проверка на превышение порогов и алерты
        self._check_alert_thresholds(error_record)
        
        # Сохранение метрик
        if self.config.get("enable_metrics", True):
            self._save_metrics()
        
        return error_record
    
    def _convert_to_processing_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> BaseProcessingError:
        """Преобразование стандартного исключения в BaseProcessingError."""
        from .exceptions import (
            NetworkError, ProcessingError, ValidationError,
            ResourceError, ConfigurationError, AuthenticationError, TimeoutError
        )
        
        error_message = str(error)
        error_type = type(error).__name__
        
        # Определение типа ошибки по содержимому сообщения
        if any(keyword in error_message.lower() for keyword in ["network", "connection", "socket"]):
            return NetworkError(error_message, context=context)
        elif "timeout" in error_message.lower():
            return TimeoutError(error_message, context=context)
        elif any(keyword in error_message.lower() for keyword in ["permission", "auth", "credential"]):
            return AuthenticationError(error_message, context=context)
        elif any(keyword in error_message.lower() for keyword in ["memory", "disk", "resource"]):
            return ResourceError(error_message, context=context)
        elif any(keyword in error_message.lower() for keyword in ["config", "setting", "parameter"]):
            return ConfigurationError(error_message, context=context)
        elif any(keyword in error_message.lower() for keyword in ["valid", "format", "parse"]):
            return ValidationError(error_message, context=context)
        else:
            return ProcessingError(f"{error_type}: {error_message}", context=context)
    
    def _create_error_record(
        self,
        error: BaseProcessingError,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Создание записи об ошибке."""
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "error": error.to_dict(),
            "component": component or "unknown",
            "context": context or {},
            "additional_data": additional_data or {},
            "error_id": self._generate_error_id()
        }
        
        # Ограничение размера контекста
        max_context_size = self.config.get("max_context_size", 1000)
        context_str = json.dumps(record["context"])
        if len(context_str) > max_context_size:
            record["context"] = {"truncated": True, "size": len(context_str)}
        
        return record
    
    def _generate_error_id(self) -> str:
        """Генерация уникального ID ошибки."""
        import hashlib
        import time
        
        timestamp = str(time.time())
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
    
    def _update_metrics(self, error_record: Dict[str, Any]):
        """Обновление метрик ошибок."""
        
        self.metrics["total_errors"] += 1
        
        error_data = error_record["error"]
        category = error_data.get("category", "unknown")
        severity = error_data.get("severity", "medium")
        component = error_record.get("component", "unknown")
        
        # Обновление счетчиков
        self.metrics["errors_by_category"][category] += 1
        self.metrics["errors_by_severity"][severity] += 1
        self.metrics["errors_by_component"][component] += 1
        
        # Обновление почасовой статистики
        current_hour = datetime.now().strftime("%Y-%m-%d %H:00")
        self.metrics["errors_by_hour"][current_hour] += 1
        
        # Обновление трендов
        self._update_error_trends()
        
        self.metrics["last_updated"] = datetime.now().isoformat()
    
    def _update_error_trends(self):
        """Обновление трендов ошибок."""
        
        # Анализ последних 100 ошибок для выявления трендов
        recent_errors_list = list(self.recent_errors)[-100:]
        
        if len(recent_errors_list) < 10:
            return
        
        # Группировка по временным интервалам (последние 10 минут)
        now = datetime.now()
        intervals = []
        
        for i in range(10):
            interval_start = now - timedelta(minutes=i+1)
            interval_end = now - timedelta(minutes=i)
            
            count = sum(
                1 for error in recent_errors_list
                if interval_start <= datetime.fromisoformat(error["timestamp"]) < interval_end
            )
            
            intervals.append({
                "interval": f"{interval_start.strftime('%H:%M')}-{interval_end.strftime('%H:%M')}",
                "count": count
            })
        
        # Определение тренда (растущий, падающий, стабильный)
        recent_counts = [interval["count"] for interval in intervals[:5]]
        older_counts = [interval["count"] for interval in intervals[5:]]
        
        recent_avg = sum(recent_counts) / len(recent_counts) if recent_counts else 0
        older_avg = sum(older_counts) / len(older_counts) if older_counts else 0
        
        if recent_avg > older_avg * 1.5:
            trend = "increasing"
        elif recent_avg < older_avg * 0.5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        self.metrics["error_trends"].append({
            "timestamp": now.isoformat(),
            "trend": trend,
            "recent_avg": recent_avg,
            "older_avg": older_avg,
            "intervals": intervals
        })
        
        # Ограничение размера истории трендов
        if len(self.metrics["error_trends"]) > 100:
            self.metrics["error_trends"] = self.metrics["error_trends"][-50:]
    
    def _log_error(self, error_record: Dict[str, Any]):
        """Логирование ошибки."""
        
        error_data = error_record["error"]
        severity = error_data.get("severity", "medium")
        message = error_data.get("message", "Unknown error")
        component = error_record.get("component", "unknown")
        
        log_message = f"[{component}] {message}"
        
        # Выбор уровня логирования
        if severity == "critical":
            self.logger.critical(log_message, extra={"error_record": error_record})
        elif severity == "high":
            self.logger.error(log_message, extra={"error_record": error_record})
        elif severity == "medium":
            self.logger.warning(log_message, extra={"error_record": error_record})
        else:
            self.logger.info(log_message, extra={"error_record": error_record})
    
    def _check_alert_thresholds(self, error_record: Dict[str, Any]):
        """Проверка превышения порогов для алертов."""
        
        thresholds = self.config.get("alert_thresholds", {})
        current_hour = datetime.now().strftime("%Y-%m-%d %H:00")
        
        # Проверка общего количества ошибок в час
        hourly_errors = self.metrics["errors_by_hour"].get(current_hour, 0)
        if hourly_errors >= thresholds.get("error_rate_per_hour", 50):
            self._send_alert(
                "high_error_rate",
                f"Высокая частота ошибок: {hourly_errors} ошибок в час",
                {"hourly_errors": hourly_errors, "threshold": thresholds["error_rate_per_hour"]}
            )
        
        # Проверка критических ошибок
        error_data = error_record["error"]
        if error_data.get("severity") == "critical":
            critical_errors_hour = sum(
                1 for error in self.recent_errors
                if (datetime.fromisoformat(error["timestamp"]).strftime("%Y-%m-%d %H:00") == current_hour
                    and error["error"].get("severity") == "critical")
            )
            
            if critical_errors_hour >= thresholds.get("critical_errors_per_hour", 5):
                self._send_alert(
                    "critical_errors",
                    f"Много критических ошибок: {critical_errors_hour} в час",
                    {"critical_errors": critical_errors_hour}
                )
        
        # Проверка ошибок по компонентам
        component = error_record.get("component", "unknown")
        component_errors = self.metrics["errors_by_component"].get(component, 0)
        if component_errors >= thresholds.get("component_error_rate", 10):
            self._send_alert(
                "component_errors",
                f"Много ошибок в компоненте {component}: {component_errors}",
                {"component": component, "errors": component_errors}
            )
    
    def _send_alert(self, alert_type: str, message: str, data: Dict[str, Any]):
        """Отправка алерта."""
        
        alert_record = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "message": message,
            "data": data
        }
        
        # Пока что просто логируем алерт
        self.logger.critical(f"ALERT: {message}", extra={"alert": alert_record})
        
        # Здесь можно добавить отправку в внешние системы мониторинга
    
    def _load_metrics(self):
        """Загрузка метрик из файла."""
        
        if not self.metrics_file.exists():
            return
        
        try:
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                saved_metrics = json.load(f)
                
            # Объединение с текущими метриками
            for key, value in saved_metrics.items():
                if key in self.metrics:
                    if isinstance(value, dict):
                        self.metrics[key].update(value)
                    elif isinstance(value, (int, float)):
                        self.metrics[key] += value
                    else:
                        self.metrics[key] = value
                        
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить метрики: {e}")
    
    def _save_metrics(self):
        """Сохранение метрик в файл."""
        
        try:
            # Преобразование defaultdict в обычные dict для JSON
            metrics_to_save = {
                "total_errors": self.metrics["total_errors"],
                "errors_by_category": dict(self.metrics["errors_by_category"]),
                "errors_by_severity": dict(self.metrics["errors_by_severity"]),
                "errors_by_hour": dict(self.metrics["errors_by_hour"]),
                "errors_by_component": dict(self.metrics["errors_by_component"]),
                "error_trends": self.metrics["error_trends"],
                "last_updated": self.metrics["last_updated"]
            }
            
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_to_save, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Не удалось сохранить метрики: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение текущих метрик."""
        return {
            "total_errors": self.metrics["total_errors"],
            "errors_by_category": dict(self.metrics["errors_by_category"]),
            "errors_by_severity": dict(self.metrics["errors_by_severity"]),
            "errors_by_hour": dict(self.metrics["errors_by_hour"]),
            "errors_by_component": dict(self.metrics["errors_by_component"]),
            "error_trends": self.metrics["error_trends"][-10:],  # Последние 10 трендов
            "last_updated": self.metrics["last_updated"],
            "recent_errors_count": len(self.recent_errors)
        }
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Получение сводки ошибок за указанный период."""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_errors_in_period = [
            error for error in self.recent_errors
            if datetime.fromisoformat(error["timestamp"]) >= cutoff_time
        ]
        
        if not recent_errors_in_period:
            return {"period_hours": hours, "total_errors": 0}
        
        # Анализ ошибок за период
        categories = defaultdict(int)
        severities = defaultdict(int)
        components = defaultdict(int)
        
        for error in recent_errors_in_period:
            error_data = error["error"]
            categories[error_data.get("category", "unknown")] += 1
            severities[error_data.get("severity", "medium")] += 1
            components[error.get("component", "unknown")] += 1
        
        return {
            "period_hours": hours,
            "total_errors": len(recent_errors_in_period),
            "errors_by_category": dict(categories),
            "errors_by_severity": dict(severities),
            "errors_by_component": dict(components),
            "error_rate_per_hour": len(recent_errors_in_period) / hours,
            "most_common_category": max(categories.items(), key=lambda x: x[1])[0] if categories else None,
            "most_affected_component": max(components.items(), key=lambda x: x[1])[0] if components else None
        }
    
    def reset_metrics(self):
        """Сброс всех метрик."""
        
        self.metrics = {
            "total_errors": 0,
            "errors_by_category": defaultdict(int),
            "errors_by_severity": defaultdict(int),
            "errors_by_hour": defaultdict(int),
            "errors_by_component": defaultdict(int),
            "error_trends": [],
            "last_updated": datetime.now().isoformat()
        }
        
        self.recent_errors.clear()
        
        # Удаление файла метрик
        if self.metrics_file.exists():
            self.metrics_file.unlink()
        
        self.logger.info("Метрики ошибок сброшены")