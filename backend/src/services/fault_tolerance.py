"""
Comprehensive Fault Tolerance Service.
Implements retry patterns, bulkheads, timeouts, and other resilience patterns.
"""

import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
import structlog

from .circuit_breaker import CircuitBreakerManager, get_circuit_breaker_manager, FallbackType

logger = structlog.get_logger()


class RetryStrategy(Enum):
    """Retry strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    RANDOM_JITTER = "random_jitter"


class BulkheadType(Enum):
    """Bulkhead isolation types."""
    THREAD_POOL = "thread_pool"
    SEMAPHORE = "semaphore"
    QUEUE = "queue"


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    jitter: bool = True
    retry_on_exceptions: List[type] = field(default_factory=lambda: [Exception])
    backoff_multiplier: float = 2.0


@dataclass
class TimeoutConfig:
    """Timeout configuration."""
    total_timeout: float = 30.0
    read_timeout: float = 10.0
    connect_timeout: float = 5.0


@dataclass
class BulkheadConfig:
    """Bulkhead configuration."""
    type: BulkheadType = BulkheadType.SEMAPHORE
    max_concurrent: int = 10
    queue_size: int = 100
    timeout_seconds: float = 30.0


@dataclass
class FaultToleranceStats:
    """Fault tolerance statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    retried_calls: int = 0
    timeout_calls: int = 0
    circuit_breaker_calls: int = 0
    bulkhead_rejections: int = 0
    fallback_executions: int = 0
    avg_response_time: float = 0.0
    success_rate: float = 0.0


class RetryService:
    """Service for handling retries with different strategies."""
    
    def __init__(self):
        self.retry_stats: Dict[str, Dict[str, int]] = {}
    
    async def retry_with_backoff(self, func: Callable, config: RetryConfig, 
                               service_name: str = "unknown", *args, **kwargs) -> Any:
        """Execute function with retry and backoff."""
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                start_time = time.time()
                result = await self._safe_call(func, *args, **kwargs)
                
                # Record successful retry if it was attempted before
                if attempt > 0:
                    self._record_retry_success(service_name, attempt)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry this exception
                if not any(isinstance(e, exc_type) for exc_type in config.retry_on_exceptions):
                    raise e
                
                # Don't retry on the last attempt
                if attempt == config.max_attempts - 1:
                    break
                
                # Calculate backoff delay
                delay = self._calculate_backoff_delay(config, attempt)
                
                logger.warning(f"Retry attempt {attempt + 1} failed",
                             service=service_name, 
                             error=str(e),
                             delay=delay)
                
                # Record retry attempt
                self._record_retry_attempt(service_name, attempt)
                
                # Wait before retrying
                await asyncio.sleep(delay)
        
        # All retries exhausted
        self._record_retry_failure(service_name, config.max_attempts)
        raise last_exception

    async def _safe_call(self, func: Callable, *args, **kwargs):
        """Safely execute a function call."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    def _calculate_backoff_delay(self, config: RetryConfig, attempt: int) -> float:
        """Calculate backoff delay based on strategy."""
        if config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
            
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * (attempt + 1)
            
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_multiplier ** attempt)
            
        elif config.strategy == RetryStrategy.RANDOM_JITTER:
            delay = config.base_delay + random.uniform(0, config.base_delay)
        
        # Apply jitter if enabled
        if config.jitter and config.strategy != RetryStrategy.RANDOM_JITTER:
            jitter = random.uniform(0.1, 1.0)
            delay *= jitter
        
        # Ensure delay doesn't exceed maximum
        return min(delay, config.max_delay)

    def _record_retry_attempt(self, service_name: str, attempt: int):
        """Record retry attempt."""
        if service_name not in self.retry_stats:
            self.retry_stats[service_name] = {"attempts": 0, "successes": 0, "failures": 0}
        
        self.retry_stats[service_name]["attempts"] += 1

    def _record_retry_success(self, service_name: str, final_attempt: int):
        """Record successful retry."""
        if service_name not in self.retry_stats:
            self.retry_stats[service_name] = {"attempts": 0, "successes": 0, "failures": 0}
        
        self.retry_stats[service_name]["successes"] += 1

    def _record_retry_failure(self, service_name: str, max_attempts: int):
        """Record failed retry."""
        if service_name not in self.retry_stats:
            self.retry_stats[service_name] = {"attempts": 0, "successes": 0, "failures": 0}
        
        self.retry_stats[service_name]["failures"] += 1


class TimeoutService:
    """Service for handling timeouts."""
    
    async def with_timeout(self, func: Callable, config: TimeoutConfig, *args, **kwargs) -> Any:
        """Execute function with timeout protection."""
        try:
            return await asyncio.wait_for(
                self._safe_call(func, *args, **kwargs),
                timeout=config.total_timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Function call timed out", 
                         timeout=config.total_timeout,
                         function=func.__name__ if hasattr(func, '__name__') else str(func))
            raise

    async def _safe_call(self, func: Callable, *args, **kwargs):
        """Safely execute a function call."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)


class BulkheadService:
    """Service for implementing bulkhead isolation pattern."""
    
    def __init__(self):
        self.semaphores: Dict[str, asyncio.Semaphore] = {}
        self.queues: Dict[str, asyncio.Queue] = {}
        self.stats: Dict[str, Dict[str, int]] = {}
    
    def get_or_create_semaphore(self, service_name: str, max_concurrent: int) -> asyncio.Semaphore:
        """Get or create semaphore for service."""
        if service_name not in self.semaphores:
            self.semaphores[service_name] = asyncio.Semaphore(max_concurrent)
        return self.semaphores[service_name]
    
    async def execute_with_bulkhead(self, func: Callable, config: BulkheadConfig,
                                  service_name: str, *args, **kwargs) -> Any:
        """Execute function with bulkhead isolation."""
        if config.type == BulkheadType.SEMAPHORE:
            return await self._execute_with_semaphore(func, config, service_name, *args, **kwargs)
        elif config.type == BulkheadType.QUEUE:
            return await self._execute_with_queue(func, config, service_name, *args, **kwargs)
        else:
            # Default to semaphore
            return await self._execute_with_semaphore(func, config, service_name, *args, **kwargs)
    
    async def _execute_with_semaphore(self, func: Callable, config: BulkheadConfig,
                                    service_name: str, *args, **kwargs) -> Any:
        """Execute with semaphore-based bulkhead."""
        semaphore = self.get_or_create_semaphore(service_name, config.max_concurrent)
        
        try:
            # Try to acquire semaphore with timeout
            await asyncio.wait_for(semaphore.acquire(), timeout=config.timeout_seconds)
            
            try:
                result = await self._safe_call(func, *args, **kwargs)
                self._record_bulkhead_success(service_name)
                return result
            finally:
                semaphore.release()
                
        except asyncio.TimeoutError:
            self._record_bulkhead_rejection(service_name)
            raise Exception(f"Bulkhead rejection: {service_name} max concurrency reached")
    
    async def _execute_with_queue(self, func: Callable, config: BulkheadConfig,
                                service_name: str, *args, **kwargs) -> Any:
        """Execute with queue-based bulkhead."""
        if service_name not in self.queues:
            self.queues[service_name] = asyncio.Queue(maxsize=config.queue_size)
        
        queue = self.queues[service_name]
        
        try:
            # Add task to queue
            task = (func, args, kwargs)
            await asyncio.wait_for(queue.put(task), timeout=config.timeout_seconds)
            
            # Process task from queue
            task_item = await queue.get()
            func, args, kwargs = task_item
            
            result = await self._safe_call(func, *args, **kwargs)
            self._record_bulkhead_success(service_name)
            queue.task_done()
            return result
            
        except asyncio.TimeoutError:
            self._record_bulkhead_rejection(service_name)
            raise Exception(f"Bulkhead queue full: {service_name}")

    async def _safe_call(self, func: Callable, *args, **kwargs):
        """Safely execute a function call."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    def _record_bulkhead_success(self, service_name: str):
        """Record successful bulkhead execution."""
        if service_name not in self.stats:
            self.stats[service_name] = {"successes": 0, "rejections": 0}
        self.stats[service_name]["successes"] += 1

    def _record_bulkhead_rejection(self, service_name: str):
        """Record bulkhead rejection."""
        if service_name not in self.stats:
            self.stats[service_name] = {"successes": 0, "rejections": 0}
        self.stats[service_name]["rejections"] += 1


class FaultToleranceService:
    """Comprehensive fault tolerance service."""
    
    def __init__(self):
        self.retry_service = RetryService()
        self.timeout_service = TimeoutService()
        self.bulkhead_service = BulkheadService()
        self.circuit_breaker_manager = get_circuit_breaker_manager()
        self.stats: Dict[str, FaultToleranceStats] = {}
    
    async def execute_with_fault_tolerance(self, 
                                         func: Callable,
                                         service_name: str,
                                         retry_config: Optional[RetryConfig] = None,
                                         timeout_config: Optional[TimeoutConfig] = None,
                                         bulkhead_config: Optional[BulkheadConfig] = None,
                                         circuit_breaker_config: Optional[dict] = None,
                                         fallback_type: Optional[FallbackType] = None,
                                         *args, **kwargs) -> Any:
        """Execute function with comprehensive fault tolerance."""
        
        start_time = time.time()
        service_stats = self._get_or_create_stats(service_name)
        service_stats.total_calls += 1
        
        try:
            # Create the execution chain
            execution_func = func
            
            # Apply timeout if configured
            if timeout_config:
                async def timeout_wrapper(*a, **kw):
                    return await self.timeout_service.with_timeout(execution_func, timeout_config, *a, **kw)
                execution_func = timeout_wrapper
            
            # Apply bulkhead if configured  
            if bulkhead_config:
                async def bulkhead_wrapper(*a, **kw):
                    return await self.bulkhead_service.execute_with_bulkhead(
                        execution_func, bulkhead_config, service_name, *a, **kw
                    )
                execution_func = bulkhead_wrapper
            
            # Apply circuit breaker if configured
            if circuit_breaker_config:
                circuit_breaker = self.circuit_breaker_manager.get_circuit_breaker(
                    service_name, circuit_breaker_config
                )
                async def circuit_breaker_wrapper(*a, **kw):
                    result = await circuit_breaker.call(execution_func, *a, fallback_type=fallback_type, **kw)
                    if result.fallback_used:
                        service_stats.fallback_executions += 1
                    if not result.success:
                        service_stats.circuit_breaker_calls += 1
                    return result.response
                execution_func = circuit_breaker_wrapper
            
            # Apply retry if configured
            if retry_config:
                async def retry_wrapper(*a, **kw):
                    return await self.retry_service.retry_with_backoff(
                        execution_func, retry_config, service_name, *a, **kw
                    )
                execution_func = retry_wrapper
            
            # Execute with fault tolerance
            result = await execution_func(*args, **kwargs)
            
            # Record success
            duration = time.time() - start_time
            self._record_success(service_name, duration)
            
            return result
            
        except asyncio.TimeoutError:
            service_stats.timeout_calls += 1
            self._record_failure(service_name, time.time() - start_time)
            raise
            
        except Exception as e:
            self._record_failure(service_name, time.time() - start_time)
            raise

    def _get_or_create_stats(self, service_name: str) -> FaultToleranceStats:
        """Get or create stats for service."""
        if service_name not in self.stats:
            self.stats[service_name] = FaultToleranceStats()
        return self.stats[service_name]

    def _record_success(self, service_name: str, duration: float):
        """Record successful execution."""
        stats = self._get_or_create_stats(service_name)
        stats.successful_calls += 1
        self._update_avg_response_time(stats, duration)
        self._update_success_rate(stats)

    def _record_failure(self, service_name: str, duration: float):
        """Record failed execution."""
        stats = self._get_or_create_stats(service_name)
        stats.failed_calls += 1
        self._update_avg_response_time(stats, duration)
        self._update_success_rate(stats)

    def _update_avg_response_time(self, stats: FaultToleranceStats, duration: float):
        """Update average response time."""
        if stats.total_calls == 1:
            stats.avg_response_time = duration
        else:
            # Exponential moving average
            alpha = 0.1
            stats.avg_response_time = (alpha * duration) + ((1 - alpha) * stats.avg_response_time)

    def _update_success_rate(self, stats: FaultToleranceStats):
        """Update success rate."""
        if stats.total_calls > 0:
            stats.success_rate = (stats.successful_calls / stats.total_calls) * 100

    def get_service_stats(self, service_name: str) -> Optional[FaultToleranceStats]:
        """Get statistics for a service."""
        return self.stats.get(service_name)

    def get_all_stats(self) -> Dict[str, FaultToleranceStats]:
        """Get statistics for all services."""
        return self.stats.copy()

    def reset_stats(self, service_name: Optional[str] = None):
        """Reset statistics."""
        if service_name:
            if service_name in self.stats:
                self.stats[service_name] = FaultToleranceStats()
        else:
            self.stats.clear()


# Global fault tolerance service
_fault_tolerance_service = None


def get_fault_tolerance_service() -> FaultToleranceService:
    """Get global fault tolerance service."""
    global _fault_tolerance_service
    if _fault_tolerance_service is None:
        _fault_tolerance_service = FaultToleranceService()
    return _fault_tolerance_service


# Decorator for easy fault tolerance usage
def fault_tolerant(service_name: str, 
                  retry_config: Optional[RetryConfig] = None,
                  timeout_config: Optional[TimeoutConfig] = None,
                  bulkhead_config: Optional[BulkheadConfig] = None,
                  circuit_breaker_config: Optional[dict] = None,
                  fallback_type: Optional[FallbackType] = None):
    """Decorator for fault tolerant function execution."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            service = get_fault_tolerance_service()
            return await service.execute_with_fault_tolerance(
                func, service_name, retry_config, timeout_config, 
                bulkhead_config, circuit_breaker_config, fallback_type,
                *args, **kwargs
            )
        return wrapper
    return decorator


# Common configurations
EXTERNAL_API_FAULT_TOLERANCE = {
    "retry_config": RetryConfig(max_attempts=3, base_delay=1.0, strategy=RetryStrategy.EXPONENTIAL_BACKOFF),
    "timeout_config": TimeoutConfig(total_timeout=10.0),
    "bulkhead_config": BulkheadConfig(max_concurrent=5),
    "fallback_type": FallbackType.CACHED_RESPONSE
}

DATABASE_FAULT_TOLERANCE = {
    "retry_config": RetryConfig(max_attempts=2, base_delay=0.5),
    "timeout_config": TimeoutConfig(total_timeout=5.0),
    "bulkhead_config": BulkheadConfig(max_concurrent=20),
    "fallback_type": FallbackType.STATIC_RESPONSE
}

CACHE_FAULT_TOLERANCE = {
    "retry_config": RetryConfig(max_attempts=2, base_delay=0.1),
    "timeout_config": TimeoutConfig(total_timeout=1.0),
    "bulkhead_config": BulkheadConfig(max_concurrent=50),
    "fallback_type": FallbackType.DEGRADED_SERVICE
}