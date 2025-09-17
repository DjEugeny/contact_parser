"""Менеджер автоматического восстановления после ошибок."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from collections import defaultdict

from .exceptions import BaseProcessingError, ErrorCategory, ErrorSeverity


class RecoveryStrategy(Enum):
    """Стратегии восстановления."""
    RETRY = "retry"  # Повторная попытка
    FALLBACK = "fallback"  # Использование резервного метода
    SKIP = "skip"  # Пропуск проблемного элемента
    RESTART = "restart"  # Перезапуск компонента
    DEGRADE = "degrade"  # Деградация функциональности
    MANUAL = "manual"  # Требует ручного вмешательства


class RecoveryAction:
    """Действие восстановления."""
    
    def __init__(
        self,
        strategy: RecoveryStrategy,
        action: Callable,
        description: str,
        priority: int = 5,
        max_attempts: int = 3,
        timeout: float = 30.0,
        conditions: Optional[Dict[str, Any]] = None
    ):
        self.strategy = strategy
        self.action = action
        self.description = description
        self.priority = priority  # 1-10, где 1 - наивысший приоритет
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.conditions = conditions or {}
        self.attempts = 0
        self.last_attempt = None
        self.success_count = 0
        self.failure_count = 0


class RecoveryManager:
    """Менеджер автоматического восстановления."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = logging.getLogger(__name__)
        
        # Реестр стратегий восстановления
        self.recovery_strategies: Dict[str, List[RecoveryAction]] = defaultdict(list)
        
        # История восстановлений
        self.recovery_history: List[Dict[str, Any]] = []
        
        # Статистика восстановлений
        self.recovery_stats = {
            "total_recoveries": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "recoveries_by_strategy": defaultdict(int),
            "recoveries_by_component": defaultdict(int),
            "average_recovery_time": 0.0
        }
        
        # Инициализация базовых стратегий
        self._register_default_strategies()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию."""
        return {
            "max_recovery_attempts": 3,
            "recovery_timeout": 60.0,
            "enable_auto_recovery": True,
            "recovery_cooldown": 5.0,  # Пауза между попытками восстановления
            "max_concurrent_recoveries": 3,
            "recovery_history_limit": 1000,
            "enable_degraded_mode": True,
            "manual_intervention_threshold": 5  # Количество неудачных попыток до ручного вмешательства
        }
    
    def register_recovery_strategy(
        self,
        error_pattern: str,
        strategy: RecoveryStrategy,
        action: Callable,
        description: str,
        priority: int = 5,
        max_attempts: int = 3,
        timeout: float = 30.0,
        conditions: Optional[Dict[str, Any]] = None
    ):
        """Регистрация стратегии восстановления для определенного типа ошибок."""
        
        recovery_action = RecoveryAction(
            strategy=strategy,
            action=action,
            description=description,
            priority=priority,
            max_attempts=max_attempts,
            timeout=timeout,
            conditions=conditions
        )
        
        self.recovery_strategies[error_pattern].append(recovery_action)
        
        # Сортировка по приоритету (меньшее число = выше приоритет)
        self.recovery_strategies[error_pattern].sort(key=lambda x: x.priority)
        
        self.logger.info(
            f"Зарегистрирована стратегия восстановления: {error_pattern} -> {strategy.value}"
        )
    
    def _register_default_strategies(self):
        """Регистрация базовых стратегий восстановления."""
        
        # Стратегии для сетевых ошибок
        self.register_recovery_strategy(
            "NetworkError",
            RecoveryStrategy.RETRY,
            self._retry_with_backoff,
            "Повторная попытка с экспоненциальной задержкой",
            priority=1,
            max_attempts=3
        )
        
        self.register_recovery_strategy(
            "NetworkError",
            RecoveryStrategy.FALLBACK,
            self._use_cached_data,
            "Использование кэшированных данных",
            priority=2
        )
        
        # Стратегии для ошибок ресурсов
        self.register_recovery_strategy(
            "ResourceError",
            RecoveryStrategy.RESTART,
            self._restart_component,
            "Перезапуск компонента",
            priority=1
        )
        
        self.register_recovery_strategy(
            "ResourceError",
            RecoveryStrategy.DEGRADE,
            self._enable_degraded_mode,
            "Включение режима деградации",
            priority=3
        )
        
        # Стратегии для ошибок валидации
        self.register_recovery_strategy(
            "ValidationError",
            RecoveryStrategy.SKIP,
            self._skip_invalid_data,
            "Пропуск невалидных данных",
            priority=1
        )
        
        self.register_recovery_strategy(
            "ValidationError",
            RecoveryStrategy.FALLBACK,
            self._use_default_values,
            "Использование значений по умолчанию",
            priority=2
        )
        
        # Стратегии для критических ошибок
        self.register_recovery_strategy(
            "CriticalError",
            RecoveryStrategy.MANUAL,
            self._request_manual_intervention,
            "Запрос ручного вмешательства",
            priority=1
        )
    
    async def attempt_recovery(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None
    ) -> Dict[str, Any]:
        """Попытка автоматического восстановления после ошибки."""
        
        if not self.config.get("enable_auto_recovery", True):
            return {"recovered": False, "reason": "Auto recovery disabled"}
        
        start_time = datetime.now()
        
        # Определение типа ошибки
        error_type = type(error).__name__
        if isinstance(error, BaseProcessingError):
            error_category = error.category.value if error.category else "unknown"
        else:
            error_category = "unknown"
        
        # Поиск подходящих стратегий восстановления
        strategies = self._find_recovery_strategies(error_type, error_category, context)
        
        if not strategies:
            self.logger.warning(f"Не найдены стратегии восстановления для {error_type}")
            return {"recovered": False, "reason": "No recovery strategies found"}
        
        # Попытка восстановления
        recovery_result = await self._execute_recovery_strategies(
            strategies, error, context, component
        )
        
        # Запись в историю
        recovery_time = (datetime.now() - start_time).total_seconds()
        self._record_recovery_attempt(
            error, context, component, strategies, recovery_result, recovery_time
        )
        
        # Обновление статистики
        self._update_recovery_stats(recovery_result, recovery_time)
        
        return recovery_result
    
    def _find_recovery_strategies(
        self,
        error_type: str,
        error_category: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[RecoveryAction]:
        """Поиск подходящих стратегий восстановления."""
        
        strategies = []
        
        # Поиск по типу ошибки
        if error_type in self.recovery_strategies:
            strategies.extend(self.recovery_strategies[error_type])
        
        # Поиск по категории ошибки
        if error_category in self.recovery_strategies:
            strategies.extend(self.recovery_strategies[error_category])
        
        # Поиск общих стратегий
        if "*" in self.recovery_strategies:
            strategies.extend(self.recovery_strategies["*"])
        
        # Фильтрация по условиям
        if context:
            strategies = [
                strategy for strategy in strategies
                if self._check_strategy_conditions(strategy, context)
            ]
        
        # Сортировка по приоритету
        strategies.sort(key=lambda x: x.priority)
        
        return strategies
    
    def _check_strategy_conditions(
        self,
        strategy: RecoveryAction,
        context: Dict[str, Any]
    ) -> bool:
        """Проверка условий применимости стратегии."""
        
        if not strategy.conditions:
            return True
        
        for key, expected_value in strategy.conditions.items():
            if key not in context:
                return False
            
            context_value = context[key]
            
            # Проверка различных типов условий
            if isinstance(expected_value, dict):
                if "min" in expected_value and context_value < expected_value["min"]:
                    return False
                if "max" in expected_value and context_value > expected_value["max"]:
                    return False
                if "in" in expected_value and context_value not in expected_value["in"]:
                    return False
            elif context_value != expected_value:
                return False
        
        return True
    
    async def _execute_recovery_strategies(
        self,
        strategies: List[RecoveryAction],
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None
    ) -> Dict[str, Any]:
        """Выполнение стратегий восстановления."""
        
        for strategy in strategies:
            # Проверка лимита попыток
            if strategy.attempts >= strategy.max_attempts:
                continue
            
            # Проверка cooldown
            if (strategy.last_attempt and 
                datetime.now() - strategy.last_attempt < timedelta(seconds=self.config.get("recovery_cooldown", 5.0))):
                continue
            
            try:
                self.logger.info(f"Попытка восстановления: {strategy.description}")
                
                strategy.attempts += 1
                strategy.last_attempt = datetime.now()
                
                # Выполнение действия восстановления с таймаутом
                result = await asyncio.wait_for(
                    self._execute_recovery_action(strategy, error, context, component),
                    timeout=strategy.timeout
                )
                
                if result.get("success", False):
                    strategy.success_count += 1
                    self.logger.info(f"Восстановление успешно: {strategy.description}")
                    
                    return {
                        "recovered": True,
                        "strategy": strategy.strategy.value,
                        "description": strategy.description,
                        "attempts": strategy.attempts,
                        "result": result
                    }
                else:
                    strategy.failure_count += 1
                    self.logger.warning(
                        f"Восстановление неудачно: {strategy.description} - {result.get('reason', 'Unknown')}"
                    )
                    
            except asyncio.TimeoutError:
                strategy.failure_count += 1
                self.logger.error(f"Таймаут восстановления: {strategy.description}")
                
            except Exception as recovery_error:
                strategy.failure_count += 1
                self.logger.error(
                    f"Ошибка при восстановлении {strategy.description}: {recovery_error}"
                )
        
        return {
            "recovered": False,
            "reason": "All recovery strategies failed",
            "attempted_strategies": [s.description for s in strategies]
        }
    
    async def _execute_recovery_action(
        self,
        strategy: RecoveryAction,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None
    ) -> Dict[str, Any]:
        """Выполнение конкретного действия восстановления."""
        
        try:
            # Подготовка аргументов для действия
            action_args = {
                "error": error,
                "context": context or {},
                "component": component,
                "strategy": strategy
            }
            
            # Выполнение действия
            if asyncio.iscoroutinefunction(strategy.action):
                result = await strategy.action(**action_args)
            else:
                result = strategy.action(**action_args)
            
            return result if isinstance(result, dict) else {"success": bool(result)}
            
        except Exception as e:
            return {"success": False, "reason": str(e)}
    
    # Базовые действия восстановления
    
    async def _retry_with_backoff(self, **kwargs) -> Dict[str, Any]:
        """Повторная попытка с экспоненциальной задержкой."""
        
        strategy = kwargs.get("strategy")
        delay = min(2 ** (strategy.attempts - 1), 60)  # Максимум 60 секунд
        
        await asyncio.sleep(delay)
        
        return {"success": True, "action": "retry_scheduled", "delay": delay}
    
    async def _use_cached_data(self, **kwargs) -> Dict[str, Any]:
        """Использование кэшированных данных."""
        
        context = kwargs.get("context", {})
        
        # Проверка наличия кэшированных данных
        if "cache_key" in context:
            # Здесь должна быть логика получения данных из кэша
            return {"success": True, "action": "used_cache", "cache_key": context["cache_key"]}
        
        return {"success": False, "reason": "No cache available"}
    
    async def _restart_component(self, **kwargs) -> Dict[str, Any]:
        """Перезапуск компонента."""
        
        component = kwargs.get("component")
        
        if not component:
            return {"success": False, "reason": "No component specified"}
        
        # Здесь должна быть логика перезапуска компонента
        self.logger.info(f"Перезапуск компонента: {component}")
        
        return {"success": True, "action": "component_restarted", "component": component}
    
    async def _enable_degraded_mode(self, **kwargs) -> Dict[str, Any]:
        """Включение режима деградации."""
        
        if not self.config.get("enable_degraded_mode", True):
            return {"success": False, "reason": "Degraded mode disabled"}
        
        component = kwargs.get("component", "system")
        
        # Здесь должна быть логика включения режима деградации
        self.logger.warning(f"Включен режим деградации для {component}")
        
        return {"success": True, "action": "degraded_mode_enabled", "component": component}
    
    async def _skip_invalid_data(self, **kwargs) -> Dict[str, Any]:
        """Пропуск невалидных данных."""
        
        context = kwargs.get("context", {})
        data_id = context.get("data_id", "unknown")
        
        self.logger.info(f"Пропуск невалидных данных: {data_id}")
        
        return {"success": True, "action": "data_skipped", "data_id": data_id}
    
    async def _use_default_values(self, **kwargs) -> Dict[str, Any]:
        """Использование значений по умолчанию."""
        
        context = kwargs.get("context", {})
        field = context.get("field", "unknown")
        
        # Здесь должна быть логика подстановки значений по умолчанию
        default_value = context.get("default_value", None)
        
        return {
            "success": True,
            "action": "default_value_used",
            "field": field,
            "default_value": default_value
        }
    
    async def _request_manual_intervention(self, **kwargs) -> Dict[str, Any]:
        """Запрос ручного вмешательства."""
        
        error = kwargs.get("error")
        component = kwargs.get("component", "unknown")
        
        # Создание запроса на ручное вмешательство
        intervention_request = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "error": str(error),
            "error_type": type(error).__name__,
            "context": kwargs.get("context", {})
        }
        
        # Сохранение запроса (здесь может быть отправка уведомления)
        self.logger.critical(
            f"ТРЕБУЕТСЯ РУЧНОЕ ВМЕШАТЕЛЬСТВО: {component} - {error}",
            extra={"intervention_request": intervention_request}
        )
        
        return {
            "success": True,
            "action": "manual_intervention_requested",
            "request": intervention_request
        }
    
    def _record_recovery_attempt(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]],
        component: Optional[str],
        strategies: List[RecoveryAction],
        result: Dict[str, Any],
        recovery_time: float
    ):
        """Запись попытки восстановления в историю."""
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "component": component,
            "context": context,
            "strategies_attempted": [s.description for s in strategies],
            "result": result,
            "recovery_time": recovery_time,
            "recovered": result.get("recovered", False)
        }
        
        self.recovery_history.append(record)
        
        # Ограничение размера истории
        max_history = self.config.get("recovery_history_limit", 1000)
        if len(self.recovery_history) > max_history:
            self.recovery_history = self.recovery_history[-max_history//2:]
    
    def _update_recovery_stats(self, result: Dict[str, Any], recovery_time: float):
        """Обновление статистики восстановлений."""
        
        self.recovery_stats["total_recoveries"] += 1
        
        if result.get("recovered", False):
            self.recovery_stats["successful_recoveries"] += 1
            strategy = result.get("strategy", "unknown")
            self.recovery_stats["recoveries_by_strategy"][strategy] += 1
        else:
            self.recovery_stats["failed_recoveries"] += 1
        
        # Обновление среднего времени восстановления
        total_recoveries = self.recovery_stats["total_recoveries"]
        current_avg = self.recovery_stats["average_recovery_time"]
        
        self.recovery_stats["average_recovery_time"] = (
            (current_avg * (total_recoveries - 1) + recovery_time) / total_recoveries
        )
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Получение статистики восстановлений."""
        
        return {
            "total_recoveries": self.recovery_stats["total_recoveries"],
            "successful_recoveries": self.recovery_stats["successful_recoveries"],
            "failed_recoveries": self.recovery_stats["failed_recoveries"],
            "success_rate": (
                self.recovery_stats["successful_recoveries"] / 
                max(self.recovery_stats["total_recoveries"], 1) * 100
            ),
            "recoveries_by_strategy": dict(self.recovery_stats["recoveries_by_strategy"]),
            "recoveries_by_component": dict(self.recovery_stats["recoveries_by_component"]),
            "average_recovery_time": self.recovery_stats["average_recovery_time"],
            "registered_strategies": len(self.recovery_strategies)
        }
    
    def get_recovery_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение истории восстановлений."""
        
        return self.recovery_history[-limit:] if limit else self.recovery_history
    
    def clear_recovery_history(self):
        """Очистка истории восстановлений."""
        
        self.recovery_history.clear()
        self.logger.info("История восстановлений очищена")