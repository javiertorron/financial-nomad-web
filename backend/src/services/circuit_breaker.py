"""
Circuit Breaker and Fault Tolerance Service.
Implements circuit breaker pattern for external service calls and fault tolerance mechanisms.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from threading import Lock
import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Circuit is open, failing fast
    HALF_OPEN = "half_open" # Testing if service is back


class FallbackType(Enum):
    """Types of fallback strategies."""
    STATIC_RESPONSE = "static_response"
    CACHED_RESPONSE = "cached_response"
    DEGRADED_SERVICE = "degraded_service"
    QUEUE_FOR_LATER = "queue_for_later"
    ALTERNATIVE_SERVICE = "alternative_service"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Number of failures to open circuit
    success_threshold: int = 2          # Successes needed to close from half-open
    timeout_seconds: int = 60           # Time before trying half-open
    recovery_timeout: int = 300         # Max time to stay in half-open
    slow_call_threshold: float = 5.0    # Seconds to consider a call slow
    slow_call_rate_threshold: float = 0.5  # Percentage of slow calls to trigger
    minimum_calls: int = 5              # Minimum calls before evaluating failure rate
    evaluation_window: int = 60         # Time window for evaluation (seconds)


@dataclass
class CallResult:
    """Result of a circuit breaker protected call."""
    success: bool
    response: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    fallback_used: bool = False
    fallback_type: Optional[FallbackType] = None


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    state: CircuitState
    failure_count: int
    success_count: int
    total_calls: int
    last_failure_time: Optional[datetime]
    state_changed_time: datetime
    success_rate: float
    average_response_time: float
    slow_call_rate: float


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state_changed_time = datetime.utcnow()
        self.lock = Lock()
        
        # Call history for statistics
        self.call_history: List[CallResult] = []
        self.max_history = 1000
        
        # Fallback strategies
        self.fallback_strategies: Dict[FallbackType, Callable] = {}
        
        logger.info("Circuit breaker initialized", 
                   name=name, config=config.__dict__)

    def register_fallback(self, fallback_type: FallbackType, strategy: Callable):
        """Register a fallback strategy."""
        self.fallback_strategies[fallback_type] = strategy
        logger.info("Fallback strategy registered", 
                   name=self.name, fallback_type=fallback_type.value)

    async def call(self, func: Callable, *args, fallback_type: Optional[FallbackType] = None, **kwargs) -> CallResult:
        """Execute a function with circuit breaker protection."""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    # Fast fail - use fallback if available
                    return await self._execute_fallback(fallback_type, *args, **kwargs)
            
            elif self.state == CircuitState.HALF_OPEN:
                if self.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
                elif (datetime.utcnow() - self.state_changed_time).total_seconds() > self.config.recovery_timeout:
                    self._transition_to_open()
                    return await self._execute_fallback(fallback_type, *args, **kwargs)
        
        # Attempt the actual call
        start_time = time.time()
        try:
            result = await self._safe_call(func, *args, **kwargs)
            duration = time.time() - start_time
            
            call_result = CallResult(
                success=True,
                response=result,
                duration=duration,
                timestamp=datetime.utcnow()
            )
            
            self._record_success(call_result)
            return call_result
            
        except Exception as e:
            duration = time.time() - start_time
            
            call_result = CallResult(
                success=False,
                error=e,
                duration=duration,
                timestamp=datetime.utcnow()
            )
            
            self._record_failure(call_result)
            
            # Try fallback if available
            fallback_result = await self._execute_fallback(fallback_type, *args, **kwargs)
            if fallback_result.success:
                return fallback_result
            
            # If no fallback or fallback failed, raise original exception
            raise e

    async def _safe_call(self, func: Callable, *args, **kwargs):
        """Safely execute a function call."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    async def _execute_fallback(self, fallback_type: Optional[FallbackType], *args, **kwargs) -> CallResult:
        """Execute fallback strategy."""
        if not fallback_type or fallback_type not in self.fallback_strategies:
            return CallResult(
                success=False,
                error=Exception(f"Circuit breaker open and no fallback available for {self.name}")
            )
        
        try:
            strategy = self.fallback_strategies[fallback_type]
            result = await self._safe_call(strategy, *args, **kwargs)
            
            return CallResult(
                success=True,
                response=result,
                fallback_used=True,
                fallback_type=fallback_type,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return CallResult(
                success=False,
                error=e,
                fallback_used=True,
                fallback_type=fallback_type,
                timestamp=datetime.utcnow()
            )

    def _record_success(self, call_result: CallResult):
        """Record a successful call."""
        with self.lock:
            self.success_count += 1
            if self.state == CircuitState.HALF_OPEN and self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
            
            self._add_to_history(call_result)

    def _record_failure(self, call_result: CallResult):
        """Record a failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            elif self.state == CircuitState.CLOSED:
                if self._should_open_circuit():
                    self._transition_to_open()
            
            self._add_to_history(call_result)

    def _should_open_circuit(self) -> bool:
        """Determine if circuit should be opened."""
        # Check minimum calls threshold
        recent_calls = self._get_recent_calls()
        if len(recent_calls) < self.config.minimum_calls:
            return False
        
        # Check failure rate
        failed_calls = [c for c in recent_calls if not c.success]
        failure_rate = len(failed_calls) / len(recent_calls)
        
        if failure_rate >= 0.5:  # 50% failure rate
            return True
        
        # Check slow call rate
        slow_calls = [c for c in recent_calls if c.duration >= self.config.slow_call_threshold]
        slow_call_rate = len(slow_calls) / len(recent_calls)
        
        if slow_call_rate >= self.config.slow_call_rate_threshold:
            return True
        
        # Check absolute failure count
        return self.failure_count >= self.config.failure_threshold

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from OPEN state."""
        if not self.last_failure_time:
            return True
        
        time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.timeout_seconds

    def _transition_to_open(self):
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.state_changed_time = datetime.utcnow()
        self.success_count = 0
        logger.warning("Circuit breaker opened", name=self.name)

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.state_changed_time = datetime.utcnow()
        self.success_count = 0
        self.failure_count = 0
        logger.info("Circuit breaker half-open", name=self.name)

    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.state_changed_time = datetime.utcnow()
        self.failure_count = 0
        self.success_count = 0
        logger.info("Circuit breaker closed", name=self.name)

    def _add_to_history(self, call_result: CallResult):
        """Add call result to history."""
        self.call_history.append(call_result)
        if len(self.call_history) > self.max_history:
            self.call_history.pop(0)

    def _get_recent_calls(self) -> List[CallResult]:
        """Get recent calls within the evaluation window."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.config.evaluation_window)
        return [call for call in self.call_history if call.timestamp > cutoff_time]

    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        recent_calls = self._get_recent_calls()
        total_calls = len(recent_calls)
        
        if total_calls == 0:
            return CircuitBreakerStats(
                state=self.state,
                failure_count=self.failure_count,
                success_count=self.success_count,
                total_calls=0,
                last_failure_time=self.last_failure_time,
                state_changed_time=self.state_changed_time,
                success_rate=0.0,
                average_response_time=0.0,
                slow_call_rate=0.0
            )
        
        successful_calls = [c for c in recent_calls if c.success]
        failed_calls = [c for c in recent_calls if not c.success]
        slow_calls = [c for c in recent_calls if c.duration >= self.config.slow_call_threshold]
        
        success_rate = len(successful_calls) / total_calls * 100
        avg_response_time = sum(c.duration for c in recent_calls) / total_calls
        slow_call_rate = len(slow_calls) / total_calls * 100
        
        return CircuitBreakerStats(
            state=self.state,
            failure_count=len(failed_calls),
            success_count=len(successful_calls),
            total_calls=total_calls,
            last_failure_time=self.last_failure_time,
            state_changed_time=self.state_changed_time,
            success_rate=success_rate,
            average_response_time=avg_response_time,
            slow_call_rate=slow_call_rate
        )

    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self.lock:
            self._transition_to_closed()
            self.call_history.clear()
            logger.info("Circuit breaker manually reset", name=self.name)


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.default_config = CircuitBreakerConfig()
        
    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.circuit_breakers:
            breaker_config = config or self.default_config
            self.circuit_breakers[name] = CircuitBreaker(name, breaker_config)
        
        return self.circuit_breakers[name]
    
    def register_fallbacks(self):
        """Register common fallback strategies."""
        # Static response fallbacks
        async def static_response_fallback(*args, **kwargs):
            return {"status": "service_unavailable", "message": "Service temporarily unavailable"}
        
        # Cache fallback
        async def cached_response_fallback(*args, **kwargs):
            # Would integrate with cache service
            return {"status": "cached", "message": "Returned cached response"}
        
        # Degraded service fallback
        async def degraded_service_fallback(*args, **kwargs):
            return {"status": "degraded", "message": "Limited functionality available"}
        
        # Register fallbacks for all circuit breakers
        for breaker in self.circuit_breakers.values():
            breaker.register_fallback(FallbackType.STATIC_RESPONSE, static_response_fallback)
            breaker.register_fallback(FallbackType.CACHED_RESPONSE, cached_response_fallback)
            breaker.register_fallback(FallbackType.DEGRADED_SERVICE, degraded_service_fallback)
    
    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get stats for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self.circuit_breakers.items()}
    
    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self.circuit_breakers.values():
            breaker.reset()


# Global manager instance
_circuit_breaker_manager = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager."""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
        _circuit_breaker_manager.register_fallbacks()
    return _circuit_breaker_manager


# Decorator for easy circuit breaker usage
def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None, 
                   fallback_type: Optional[FallbackType] = None):
    """Decorator to protect functions with circuit breaker."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            breaker = manager.get_circuit_breaker(name, config)
            result = await breaker.call(func, *args, fallback_type=fallback_type, **kwargs)
            
            if not result.success and not result.fallback_used:
                raise result.error
            
            return result.response
        
        return wrapper
    return decorator


# Common circuit breaker configurations
EXTERNAL_API_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    success_threshold=2,
    timeout_seconds=30,
    slow_call_threshold=3.0,
    minimum_calls=3
)

DATABASE_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=3,
    timeout_seconds=60,
    slow_call_threshold=2.0,
    minimum_calls=5
)

CACHE_CONFIG = CircuitBreakerConfig(
    failure_threshold=2,
    success_threshold=1,
    timeout_seconds=10,
    slow_call_threshold=0.5,
    minimum_calls=2
)