import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class RequestResult(Enum):
    """Результат выполнения запроса к LLM"""
    SUCCESS = "success"
    RATE_LIMIT_ERROR = "rate_limit_error"
    OTHER_ERROR = "other_error"
    TIMEOUT = "timeout"

@dataclass
class RequestStats:
    """Статистика запроса"""
    timestamp: float
    result: RequestResult
    delay_used: float
    provider: Optional[str] = None

class RateLimitManager:
    """Адаптивный менеджер rate limit для LLM запросов"""
    
    def __init__(self, 
                 initial_delay: float = 30.0,
                 min_delay: float = 10.0,
                 max_delay: float = 120.0,
                 increase_factor: float = 1.5,
                 decrease_factor: float = 0.8,
                 stable_period: int = 5):
        """
        Инициализация менеджера rate limit
        
        Args:
            initial_delay: Начальная задержка в секундах
            min_delay: Минимальная задержка в секундах
            max_delay: Максимальная задержка в секундах
            increase_factor: Коэффициент увеличения при ошибках
            decrease_factor: Коэффициент уменьшения при успехе
            stable_period: Количество успешных запросов для сброса к базовой задержке
        """
        self.initial_delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.increase_factor = increase_factor
        self.decrease_factor = decrease_factor
        self.stable_period = stable_period
        
        self.current_delay = initial_delay
        self.last_request_time: Optional[float] = None
        self.request_history: list[RequestStats] = []
        self.consecutive_successes = 0
        self.consecutive_errors = 0
        
        self.logger = logging.getLogger(__name__)
        
    def calculate_delay(self) -> float:
        """Вычисляет необходимую задержку до следующего запроса"""
        if self.last_request_time is None:
            return 0.0
            
        time_since_last = time.time() - self.last_request_time
        remaining_delay = max(0, self.current_delay - time_since_last)
        
        self.logger.debug(f"Текущая задержка: {self.current_delay:.1f}с, "
                         f"прошло: {time_since_last:.1f}с, "
                         f"осталось ждать: {remaining_delay:.1f}с")
        
        return remaining_delay
    
    def wait_if_needed(self) -> float:
        """Ожидает необходимое время и возвращает фактическое время ожидания"""
        delay = self.calculate_delay()
        if delay > 0:
            self.logger.info(f"Ожидание {delay:.1f} секунд перед следующим LLM запросом")
            time.sleep(delay)
        return delay
    
    def record_request(self, result: str, provider: Optional[str] = None):
        """Записывает результат запроса и корректирует задержки"""
        current_time = time.time()
        
        # Записываем статистику
        stats = RequestStats(
            timestamp=current_time,
            result=RequestResult(result),
            delay_used=self.current_delay,
            provider=provider
        )
        self.request_history.append(stats)
        
        # Обновляем время последнего запроса
        self.last_request_time = current_time
        
        # Корректируем задержки на основе результата
        self._adjust_delay(result)
        
        # Ограничиваем историю последними 50 запросами
        if len(self.request_history) > 50:
            self.request_history = self.request_history[-50:]
            
        self.logger.info(f"Запрос завершен: {result}, "
                        f"новая задержка: {self.current_delay:.1f}с, "
                        f"провайдер: {provider or 'неизвестен'}")
    
    def _adjust_delay(self, result: str):
        """Корректирует текущую задержку на основе результата запроса"""
        if result == "success":
            self.consecutive_successes += 1
            self.consecutive_errors = 0
            
            # Уменьшаем задержку при каждом успешном запросе
            self.current_delay = max(
                self.min_delay,
                self.current_delay * self.decrease_factor
            )
            
            # Сброс к базовой задержке после периода стабильной работы
            if self.consecutive_successes >= self.stable_period:
                self.current_delay = self.initial_delay
                self.consecutive_successes = 0
                
        elif result == "rate_limit_error":
            self.consecutive_errors += 1
            self.consecutive_successes = 0
            
            # Увеличиваем задержку при rate limit ошибках
            # Экспоненциальный backoff при повторных ошибках
            multiplier = self.increase_factor ** min(self.consecutive_errors, 3)
            self.current_delay = min(
                self.max_delay,
                self.current_delay * multiplier
            )
            
        elif result in ["other_error", "timeout"]:
            self.consecutive_errors += 1
            self.consecutive_successes = 0
            
            # Небольшое увеличение при других ошибках
            if self.consecutive_errors >= 2:
                self.current_delay = min(
                    self.max_delay,
                    self.current_delay * 1.2
                )
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику работы менеджера"""
        if not self.request_history:
            return {
                "total_requests": 0,
                "current_delay": self.current_delay,
                "consecutive_successes": self.consecutive_successes,
                "consecutive_errors": self.consecutive_errors
            }
        
        recent_requests = self.request_history[-10:]  # Последние 10 запросов
        success_rate = sum(1 for r in recent_requests if r.result == RequestResult.SUCCESS) / len(recent_requests)
        
        avg_delay = sum(r.delay_used for r in recent_requests) / len(recent_requests)
        
        return {
            "total_requests": len(self.request_history),
            "current_delay": self.current_delay,
            "consecutive_successes": self.consecutive_successes,
            "consecutive_errors": self.consecutive_errors,
            "recent_success_rate": success_rate,
            "average_delay": avg_delay,
            "last_request_time": self.last_request_time
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Алиас для get_stats для совместимости с тестами"""
        return self.get_stats()
    
    def reset(self):
        """Сбрасывает состояние менеджера к начальным значениям"""
        self.current_delay = self.initial_delay
        self.last_request_time = None
        self.consecutive_successes = 0
        self.consecutive_errors = 0
        self.request_history = []  # Очищаем историю запросов
        self.logger.info("RateLimitManager сброшен к начальным значениям")