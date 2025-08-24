"""
Strategic caching service for Financial Nomad.
"""
import asyncio
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union, List, Callable
from dataclasses import dataclass
import weakref

import structlog
from ..config import get_settings
from ..middleware.monitoring import metrics_collector

logger = structlog.get_logger()


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    expires_at: float
    created_at: float
    access_count: int = 0
    last_accessed: float = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() > self.expires_at
    
    def is_stale(self, stale_threshold: float = 0.8) -> bool:
        """Check if cache entry is stale (near expiration)."""
        now = time.time()
        total_ttl = self.expires_at - self.created_at
        elapsed = now - self.created_at
        return (elapsed / total_ttl) > stale_threshold
    
    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()


class InMemoryCache:
    """In-memory cache with TTL and size limits."""
    
    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: int = 300
    ):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                if entry.is_expired():
                    del self._cache[key]
                    self.misses += 1
                    metrics_collector.record_cache_operation("get", "miss_expired")
                    return None
                
                entry.touch()
                self.hits += 1
                metrics_collector.record_cache_operation("get", "hit")
                return entry.data
            
            self.misses += 1
            metrics_collector.record_cache_operation("get", "miss")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        async with self._lock:
            ttl = ttl or self.default_ttl
            now = time.time()
            expires_at = now + ttl
            
            # Serialize to calculate size
            try:
                serialized = json.dumps(value, default=str)
                size_bytes = len(serialized.encode('utf-8'))
            except (TypeError, ValueError):
                # If can't serialize, estimate size
                size_bytes = len(str(value)) * 2
            
            entry = CacheEntry(
                data=value,
                expires_at=expires_at,
                created_at=now,
                size_bytes=size_bytes
            )
            
            # Check if we need to evict
            await self._ensure_capacity(size_bytes)
            
            self._cache[key] = entry
            metrics_collector.record_cache_operation("set", "success")
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                metrics_collector.record_cache_operation("delete", "success")
                return True
            
            metrics_collector.record_cache_operation("delete", "miss")
            return False
    
    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            metrics_collector.record_cache_operation("clear", "success")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            memory_usage_percent = (total_size / self.max_memory_bytes * 100) if self.max_memory_bytes > 0 else 0
            
            return {
                "entries": len(self._cache),
                "max_size": self.max_size,
                "memory_usage_bytes": total_size,
                "memory_usage_percent": round(memory_usage_percent, 2),
                "max_memory_bytes": self.max_memory_bytes,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self.evictions
            }
    
    async def _ensure_capacity(self, new_entry_size: int):
        """Ensure cache has capacity for new entry."""
        current_size = len(self._cache)
        current_memory = sum(entry.size_bytes for entry in self._cache.values())
        
        # Check size limit
        if current_size >= self.max_size:
            await self._evict_lru()
        
        # Check memory limit
        if current_memory + new_entry_size > self.max_memory_bytes:
            await self._evict_by_memory(new_entry_size)
    
    async def _evict_lru(self):
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed or self._cache[k].created_at
        )
        
        del self._cache[lru_key]
        self.evictions += 1
        metrics_collector.record_cache_operation("evict", "lru")
    
    async def _evict_by_memory(self, required_bytes: int):
        """Evict entries to free memory."""
        current_memory = sum(entry.size_bytes for entry in self._cache.values())
        target_memory = self.max_memory_bytes - required_bytes
        
        if target_memory <= 0:
            # Required size is too large, clear cache
            await self.clear()
            return
        
        # Sort entries by access frequency and age
        entries_by_priority = sorted(
            self._cache.items(),
            key=lambda x: (
                x[1].access_count,
                x[1].last_accessed or x[1].created_at
            )
        )
        
        # Evict until we have enough memory
        evicted = 0
        for key, entry in entries_by_priority:
            current_memory -= entry.size_bytes
            del self._cache[key]
            evicted += 1
            
            if current_memory <= target_memory:
                break
        
        self.evictions += evicted
        metrics_collector.record_cache_operation("evict", f"memory_{evicted}")
    
    async def _cleanup_expired(self):
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                async with self._lock:
                    expired_keys = [
                        key for key, entry in self._cache.items()
                        if entry.is_expired()
                    ]
                    
                    for key in expired_keys:
                        del self._cache[key]
                    
                    if expired_keys:
                        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                        metrics_collector.record_cache_operation("cleanup", f"expired_{len(expired_keys)}")
                
            except Exception as e:
                logger.error("Cache cleanup failed", error=str(e))


class CacheKeyBuilder:
    """Helper for building consistent cache keys."""
    
    @staticmethod
    def user_key(user_id: str, suffix: str) -> str:
        """Build user-specific cache key."""
        return f"user:{user_id}:{suffix}"
    
    @staticmethod
    def query_key(collection: str, filters: Dict[str, Any]) -> str:
        """Build query cache key."""
        # Create deterministic hash of filters
        filter_str = json.dumps(filters, sort_keys=True, default=str)
        filter_hash = hashlib.md5(filter_str.encode()).hexdigest()[:8]
        return f"query:{collection}:{filter_hash}"
    
    @staticmethod
    def computation_key(operation: str, params: Dict[str, Any]) -> str:
        """Build computation cache key."""
        params_str = json.dumps(params, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"compute:{operation}:{params_hash}"


class CacheService:
    """High-level caching service with different cache strategies."""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        
        # Different cache instances for different use cases
        self.query_cache = InMemoryCache(
            max_size=500,
            max_memory_mb=50,
            default_ttl=300  # 5 minutes
        )
        
        self.user_session_cache = InMemoryCache(
            max_size=1000,
            max_memory_mb=20,
            default_ttl=1800  # 30 minutes
        )
        
        self.computation_cache = InMemoryCache(
            max_size=200,
            max_memory_mb=30,
            default_ttl=3600  # 1 hour
        )
        
        # Cache for API responses
        self.api_response_cache = InMemoryCache(
            max_size=300,
            max_memory_mb=25,
            default_ttl=180  # 3 minutes
        )
    
    # Query result caching
    async def get_cached_query(self, collection: str, filters: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Get cached query results."""
        key = CacheKeyBuilder.query_key(collection, filters)
        return await self.query_cache.get(key)
    
    async def cache_query_result(
        self,
        collection: str,
        filters: Dict[str, Any],
        result: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ):
        """Cache query results."""
        key = CacheKeyBuilder.query_key(collection, filters)
        await self.query_cache.set(key, result, ttl)
    
    # User session caching
    async def get_cached_user_data(self, user_id: str, data_type: str) -> Optional[Any]:
        """Get cached user data."""
        key = CacheKeyBuilder.user_key(user_id, data_type)
        return await self.user_session_cache.get(key)
    
    async def cache_user_data(
        self,
        user_id: str,
        data_type: str,
        data: Any,
        ttl: Optional[int] = None
    ):
        """Cache user data."""
        key = CacheKeyBuilder.user_key(user_id, data_type)
        await self.user_session_cache.set(key, data, ttl)
    
    async def invalidate_user_cache(self, user_id: str, data_type: Optional[str] = None):
        """Invalidate user cache."""
        if data_type:
            key = CacheKeyBuilder.user_key(user_id, data_type)
            await self.user_session_cache.delete(key)
        else:
            # Invalidate all user data - we'd need to track keys for this
            # For now, just log
            logger.info("User cache invalidation requested", user_id=user_id)
    
    # Computation caching
    async def get_cached_computation(self, operation: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached computation result."""
        key = CacheKeyBuilder.computation_key(operation, params)
        return await self.computation_cache.get(key)
    
    async def cache_computation_result(
        self,
        operation: str,
        params: Dict[str, Any],
        result: Any,
        ttl: Optional[int] = None
    ):
        """Cache computation result."""
        key = CacheKeyBuilder.computation_key(operation, params)
        await self.computation_cache.set(key, result, ttl)
    
    # API response caching
    async def get_cached_api_response(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached API response."""
        key = f"api:{endpoint}:{hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]}"
        return await self.api_response_cache.get(key)
    
    async def cache_api_response(
        self,
        endpoint: str,
        params: Dict[str, Any],
        response: Any,
        ttl: Optional[int] = None
    ):
        """Cache API response."""
        key = f"api:{endpoint}:{hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]}"
        await self.api_response_cache.set(key, response, ttl)
    
    # Statistics and monitoring
    async def get_all_cache_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches."""
        return {
            "query_cache": await self.query_cache.get_stats(),
            "user_session_cache": await self.user_session_cache.get_stats(),
            "computation_cache": await self.computation_cache.get_stats(),
            "api_response_cache": await self.api_response_cache.get_stats()
        }
    
    async def clear_all_caches(self):
        """Clear all caches."""
        await asyncio.gather(
            self.query_cache.clear(),
            self.user_session_cache.clear(),
            self.computation_cache.clear(),
            self.api_response_cache.clear()
        )
        
        logger.info("All caches cleared")


# Cache decorators
def cached_query(ttl: int = 300):
    """Decorator for caching query results."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Extract cache key from arguments
            # This is a simplified implementation
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            cached_result = await cache_service.query_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await func(*args, **kwargs)
            await cache_service.query_cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def cached_computation(ttl: int = 3600):
    """Decorator for caching computation results."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            cached_result = await cache_service.computation_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await func(*args, **kwargs)
            await cache_service.computation_cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


# Global cache service instance
cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the global cache service instance."""
    global cache_service
    if cache_service is None:
        cache_service = CacheService()
    return cache_service